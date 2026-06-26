
import asyncio
import hashlib
import json
from collections.abc import AsyncGenerator
from datetime import datetime
from time import perf_counter
from typing import Any

from agno.session.team import TeamSession
from agno.team.team import Team
from redis.asyncio import Redis

from app.api.v1.module_system.dept.service import DeptService
from app.common.request import PaginationService
from app.config.setting import settings
from app.core.base_schema import AuthSchema
from app.core.dependencies import require_superadmin
from app.core.exceptions import CustomException
from app.core.logger import logger
from app.utils.hash_bcrpy_util import AESCipher

from .audit import AiCallAuditRecord, record_ai_call_audit
from .crud import ChatSessionCRUD
from .platform_crud import DatabaseAiConfigRepository
from .schema import (
    AiModelConfigSchema,
    AiModelConfigUpdateSchema,
    ChatQuerySchema,
    ChatSessionCreateSchema,
    ChatSessionQueryParam,
    ChatSessionUpdateSchema,
)
from .utils import AgnoFactory


async def _format_session_data(session: TeamSession, auth: AuthSchema | None = None) -> dict[str, Any]:
    """格式化会话数据，添加前端需要的字段"""
    if hasattr(session, "to_dict"):
        session_dict = session.to_dict()
    else:
        session_dict = {
            "session_id": getattr(session, "session_id", ""),
            "agent_id": getattr(session, "agent_id", None),
            "team_id": getattr(session, "team_id", None),
            "workflow_id": getattr(session, "workflow_id", None),
            "user_id": getattr(session, "user_id", None),
            "session_data": getattr(session, "session_data", None),
            "agent_data": getattr(session, "agent_data", None),
            "team_data": getattr(session, "team_data", None),
            "workflow_data": getattr(session, "workflow_data", None),
            "metadata": getattr(session, "metadata", None),
            "runs": getattr(session, "runs", []),
            "summary": getattr(session, "summary", None),
            "created_at": getattr(session, "created_at", None),
            "updated_at": getattr(session, "updated_at", None),
        }

    session_data = session_dict.get("session_data") or {}
    runs = session_dict.get("runs") or []
    messages = _extract_messages(runs)

    # 从 session_data 中获取 session_name 作为标题
    session_name = session_data.get("session_name") if session_data else None

    result = {
        **session_dict,
        "id": session_dict.get("session_id"),
        "title": session_name or session_dict.get("session_id", "")[:8] or "未命名会话",
        "created_time": _unix_to_datetime(session_dict.get("created_at")),
        "updated_time": _unix_to_datetime(session_dict.get("updated_at")),
        "message_count": len(messages),
        "messages": messages,
    }

    # 如果有 auth，查询部门名称
    if auth and session_dict.get("team_id"):
        try:
            team_id = session_dict.get("team_id")
            if isinstance(team_id, str):
                dept_name = await DeptService(auth).detail(id=int(team_id))
                result["team_name"] = dept_name.get("name")
            elif isinstance(team_id, int):
                dept_name = await DeptService(auth).detail(id=team_id)
                result["team_name"] = dept_name.get("name")
            else:
                result["team_name"] = None
        except Exception:
            result["team_name"] = None
    else:
        result["team_name"] = None

    # 如果 summary 是 SessionSummary 对象，提取 summary 字段
    summary = session_dict.get("summary")
    if summary:
        if isinstance(summary, dict):
            result["summary"] = summary.get("summary")
        else:
            result["summary"] = str(summary)

    return result


def _unix_to_datetime(timestamp: int | None) -> str | None:
    """将Unix时间戳转换为日期时间字符串"""
    if timestamp is None:
        return None
    try:
        dt = datetime.fromtimestamp(timestamp)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError, OSError):
        return None


def _extract_messages(runs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """从 runs 中提取消息"""
    messages = []
    if not runs:
        return messages
    for run in runs:
        if not isinstance(run, dict):
            continue
        run_messages = run.get("messages", [])
        if run_messages and isinstance(run_messages, list):
            for msg in run_messages:
                if isinstance(msg, dict):
                    role = msg.get("role")
                    if role in ("user", "assistant"):
                        messages.append(
                            {
                                "id": msg.get("id"),
                                "role": role,
                                "content": msg.get("content", ""),
                                "created_at": msg.get("created_at"),
                            }
                        )
    return messages


class ChatService:
    """聊天会话管理模块服务层"""

    def __init__(self, auth: AuthSchema) -> None:
        self.auth = auth

    async def chat_query(
        self,
        query: ChatQuerySchema,
        stop_event: asyncio.Event | None = None,
        model_config: dict[str, Any] | None = None,
    ) -> AsyncGenerator[str, None]:
        """流式 AI 对话"""
        try:
            crud = ChatSessionCRUD(self.auth)

            session_id = query.session_id
            if not session_id:
                import uuid

                session_id = str(uuid.uuid4())
                session: TeamSession | None = await crud.create_crud(data=ChatSessionCreateSchema(title="新对话"))
                if not session:
                    raise CustomException(msg="创建会话失败")
                session_id = session.session_id

            agno_factory = AgnoFactory()
            dept_id = str(self.auth.user.dept_id) if self.auth and self.auth.user and hasattr(self.auth.user, "dept_id") and self.auth.user.dept_id else "default"
            agent = agno_factory.create_agent(
                user_id=self.auth.user.username if self.auth and self.auth.user else "user",
                dept_id=dept_id,
                session_id=session_id,
                db=crud.db,
                model_config=model_config,
            )

            message = (query.message or "").strip()
            if not message:
                yield "请输入消息内容"
                return

            logger.info("开始流式生成: session_id={} message={!r}", session_id, message[:80])
            chunk_count = 0
            try:
                stream = agent.arun(input=message, stream=True)
                logger.info("agent.arun 返回对象类型: {}", type(stream).__name__)
                if hasattr(stream, "__aiter__"):
                    async for chunk in stream:
                        if stop_event is not None and stop_event.is_set():
                            logger.info("用户主动停止生成: session_id={}", session_id)
                            return
                        if chunk and getattr(chunk, "content", None):
                            chunk_count += 1
                            yield chunk.content
                        else:
                            logger.debug("空 chunk 跳过: {}", type(chunk).__name__ if chunk else None)
                else:
                    # 兼容非流式直接返回结果的场景
                    logger.warning("agent.arun 未返回异步迭代器，尝试按单次结果处理")
                    if stream and getattr(stream, "content", None):
                        chunk_count += 1
                        yield stream.content
            except asyncio.CancelledError:
                logger.info("生成任务被取消: session_id={}", session_id)
                return

            logger.info("流式生成结束: session_id={} chunk_count={}", session_id, chunk_count)

        except Exception as e:
            logger.error(f"聊天查询失败: {e}", exc_info=True)
            yield f"抱歉，处理您的请求时出现错误：{str(e)}"

    async def chat_non_stream(
        self,
        message: str,
        session_id: str | None,
        redis: Redis | None = None,
        model_config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """非流式 AI 对话"""
        effective_model_config: dict[str, Any] | None = None
        try:
            crud = ChatSessionCRUD(self.auth)

            if not session_id:
                import uuid

                session_id = str(uuid.uuid4())
                session: TeamSession | None = await crud.create_crud(data=ChatSessionCreateSchema(title="新对话"))
                if not session:
                    raise CustomException(msg="创建会话失败")
                session_id = session.session_id

            response_content = ""
            if model_config is None:
                runtime = AiRuntimeService(self.auth, audit_enabled=False)
                effective_model_config = await resolve_effective_model_config(redis, self.auth)
                response_content = await runtime.chat(
                    message,
                    source_module="module_ai",
                    source_feature="chat_non_stream",
                    system_prompt="你是企业管理系统中的中文 AI 助手，请用简洁、可执行的方式回答。",
                )
            else:
                agno_factory = AgnoFactory()
                dept_id = str(self.auth.user.dept_id) if self.auth and self.auth.user and hasattr(self.auth.user, "dept_id") and self.auth.user.dept_id else "default"
                effective_model_config = model_config
                agent: Team = agno_factory.create_agent(
                    user_id=self.auth.user.username if self.auth and self.auth.user else "user",
                    dept_id=dept_id,
                    session_id=session_id,
                    db=crud.db,
                    model_config=effective_model_config,
                )
                response = await agent.arun(input=message)
                if response and response.content:
                    response_content = response.content

            response_text = ""
            action = None

            if response_content:
                response_text = response_content
                try:
                    if response_text.strip().startswith("{") and response_text.strip().endswith("}"):
                        action = json.loads(response_text)
                    elif "```json" in response_text:
                        json_start = response_text.find("```json") + 7
                        json_end = response_text.find("```", json_start)
                        if json_end > json_start:
                            json_str = response_text[json_start:json_end].strip()
                            action = json.loads(json_str)
                except (json.JSONDecodeError, Exception):
                    pass

                if not action:
                    action = self._parse_action_from_response(response_text)

            result = {
                "response": response_text,
                "session_id": session_id,
                "function_calls": None,
                "action": action,
            }
            await record_ai_call_audit(
                redis,
                AiCallAuditRecord(
                    user_id=getattr(self.auth.user, "id", None) if self.auth and self.auth.user else None,
                    tenant_id=self.auth.tenant_id if self.auth else None,
                    session_id=session_id,
                    message=message,
                    model_config=effective_model_config,
                    status="success",
                ),
            )
            return result

        except Exception as e:
            logger.error(f"聊天查询失败: {e}")
            await record_ai_call_audit(
                redis,
                AiCallAuditRecord(
                    user_id=getattr(self.auth.user, "id", None) if self.auth and self.auth.user else None,
                    tenant_id=self.auth.tenant_id if self.auth else None,
                    session_id=session_id,
                    message=message,
                    model_config=effective_model_config,
                    status="error",
                    error=str(e),
                ),
            )
            return {
                "response": f"抱歉，处理您的请求时出现错误：{str(e)}",
                "session_id": session_id,
                "function_calls": None,
                "action": None,
            }

    @staticmethod
    def _parse_action_from_response(response_text: str) -> dict[str, Any] | None:
        """从响应文本中解析操作建议"""

        route_config = {
            "用户管理": {"path": "/system/user", "name": "用户管理"},
            "角色管理": {"path": "/system/role", "name": "角色管理"},
            "菜单管理": {"path": "/system/menu", "name": "菜单管理"},
            "部门管理": {"path": "/system/dept", "name": "部门管理"},
            "字典管理": {"path": "/system/dict", "name": "字典管理"},
            "系统日志": {"path": "/system/log", "name": "系统日志"},
        }

        navigation_keywords = ["跳转", "打开", "进入", "前往", "去", "浏览", "查看"]
        has_navigation = any(keyword in response_text for keyword in navigation_keywords)

        if not has_navigation:
            return None

        for page_name, route_info in route_config.items():
            if page_name in response_text:
                return {
                    "type": "navigate",
                    "path": route_info["path"],
                    "name": route_info["name"],
                }

        keyword_mapping = {
            "用户": {"path": "/system/user", "name": "用户管理"},
            "角色": {"path": "/system/role", "name": "角色管理"},
            "菜单": {"path": "/system/menu", "name": "菜单管理"},
            "部门": {"path": "/system/dept", "name": "部门管理"},
            "字典": {"path": "/system/dict", "name": "字典管理"},
            "日志": {"path": "/system/log", "name": "系统日志"},
        }

        for keyword, route_info in keyword_mapping.items():
            if keyword in response_text:
                return {
                    "type": "navigate",
                    "path": route_info["path"],
                    "name": route_info["name"],
                }

        return None

    async def get_session(self, session_id: str) -> dict[str, Any] | None:
        crud = ChatSessionCRUD(self.auth)
        session: TeamSession | None = await crud.get_by_id_crud(session_id=session_id)
        if session:
            return await _format_session_data(session, self.auth)
        return None

    async def create(self, data: ChatSessionCreateSchema) -> dict[str, Any] | None:
        crud = ChatSessionCRUD(self.auth)
        session = await crud.create_crud(data=data)
        if session:
            return await _format_session_data(session, self.auth)
        return None

    async def page(
        self,
        page_no: int,
        page_size: int,
        search: ChatSessionQueryParam,
        order_by: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        crud = ChatSessionCRUD(self.auth)
        sessions = await crud.list_crud()
        items = [await _format_session_data(s, self.auth) for s in sessions]
        return await PaginationService.paginate(
            data_list=items,
            page_no=page_no,
            page_size=page_size,
        )

    async def update(self, session_id: str, data: ChatSessionUpdateSchema) -> bool:
        crud = ChatSessionCRUD(self.auth)
        return await crud.update_crud(session_id=session_id, data=data)

    async def delete(self, session_ids: list[str]) -> None:
        await ChatSessionCRUD(self.auth).delete_crud(session_ids=session_ids)


# ================================================= #
# ************* 平台级 AI / LLM 模型配置 ************ #
# ================================================= #


def _mask_api_key(api_key: str | None) -> str | None:
    if not api_key:
        return None
    if len(api_key) <= 4:
        return "****"
    return f"****{api_key[-4:]}"


def _ai_cipher() -> AESCipher:
    return AESCipher(hashlib.sha256(settings.SECRET_KEY.encode("utf-8")).hexdigest())


def encrypt_api_key(api_key: str) -> str:
    return _ai_cipher().encrypt(api_key).hex()


def decrypt_api_key(api_key_cipher: str) -> str:
    return _ai_cipher().decrypt(api_key_cipher)


def _public_model_config(item: dict[str, Any], *, include_sensitive: bool = False) -> dict[str, Any]:
    api_key = None
    api_key_cipher = item.get("api_key_cipher")
    if api_key_cipher:
        try:
            api_key = decrypt_api_key(api_key_cipher)
        except Exception:
            logger.warning("AI 模型配置 API Key 解密失败: id={}", item.get("id"))
    result = {
        "id": item.get("id"),
        "provider_type": item.get("provider_type") or "openai_compatible",
        "name": item.get("name"),
        "base_url": item.get("base_url"),
        "model_id": item.get("model_id"),
        "temperature": item.get("temperature"),
        "max_tokens": item.get("max_tokens"),
        "timeout_seconds": item.get("timeout_seconds") or 60,
        "enabled": bool(item.get("enabled", True)),
        "is_default": bool(item.get("is_default", False)),
        "description": item.get("description"),
        "created_time": item.get("created_time"),
        "has_api_key": bool(api_key),
        "api_key_masked": _mask_api_key(api_key),
    }
    if include_sensitive:
        result["api_key"] = api_key
    return result


def _runtime_model_config(item: dict[str, Any], *, auth: AuthSchema | None = None, source: str = "platform_default") -> dict[str, Any]:
    public = _public_model_config(item, include_sensitive=True)
    return {
        "base_url": public.get("base_url"),
        "api_key": public.get("api_key"),
        "model_id": public.get("model_id"),
        "temperature": public.get("temperature"),
        "max_tokens": public.get("max_tokens"),
        "timeout_seconds": public.get("timeout_seconds") or 60,
        "config_id": public.get("id"),
        "provider_type": public.get("provider_type"),
        "source": source,
        "tenant_id": auth.tenant_id if auth else None,
        "user_id": getattr(auth.user, "id", None) if auth and auth.user else None,
    }


class PlatformAiModelConfigService:
    """平台级 AI 模型配置业务服务。"""

    decrypt_api_key = staticmethod(decrypt_api_key)

    def __init__(self, auth: AuthSchema, redis: Redis | None = None, *, repository: Any | None = None) -> None:
        self.auth = auth
        self.redis = redis
        self.repository = repository or DatabaseAiConfigRepository(auth)

    @require_superadmin
    async def list(self) -> dict[str, Any]:
        items = [_public_model_config(item) for item in await self.repository.list()]
        default = next((item for item in items if item.get("is_default")), None)
        default_id = default.get("id") if default else None
        return {"items": items, "active_id": default_id, "default_id": default_id}

    async def get_active(self) -> dict[str, Any] | None:
        return await self.repository.get_default()

    @require_superadmin
    async def create(self, config: AiModelConfigSchema) -> dict[str, Any]:
        data = config.model_dump()
        api_key = data.pop("api_key")
        data["api_key_cipher"] = encrypt_api_key(api_key)
        if not await self.repository.list():
            data["is_default"] = True
        if data.get("is_default"):
            await self.repository.clear_default()
        item = await self.repository.create(data)
        logger.info("已新增平台 AI 模型配置: name={} id={}", config.name, item.get("id"))
        return _public_model_config(item)

    @require_superadmin
    async def update(self, config_id: int | str, config: AiModelConfigUpdateSchema) -> dict[str, Any] | None:
        target_id = self._normalize_id(config_id)
        existing = await self.repository.get(target_id)
        if existing is None:
            raise CustomException(msg="模型配置不存在", code=10404, status_code=404)
        data = config.model_dump(exclude_none=True)
        api_key = data.pop("api_key", None)
        if api_key:
            data["api_key_cipher"] = encrypt_api_key(api_key)
        if existing.get("is_default") and data.get("enabled") is False:
            raise CustomException(msg="默认模型不能停用，请先切换默认模型", code=10422, status_code=422)
        if existing.get("is_default") and data.get("is_default") is False:
            data.pop("is_default", None)
        if data.get("is_default"):
            await self.repository.clear_default()
        result = await self.repository.update(target_id, data)
        if result is None:
            raise CustomException(msg="模型配置不存在", code=10404, status_code=404)
        return _public_model_config(result)

    @require_superadmin
    async def delete(self, config_id: int | str) -> None:
        target_id = self._normalize_id(config_id)
        existing = await self.repository.get(target_id)
        if existing is None:
            raise CustomException(msg="模型配置不存在", code=10404, status_code=404)
        if existing.get("is_default"):
            raise CustomException(msg="默认模型不能删除，请先切换默认模型", code=10422, status_code=422)
        ok = await self.repository.delete(target_id)
        if not ok:
            raise CustomException(msg="模型配置不存在", code=10404, status_code=404)

    @require_superadmin
    async def set_default(self, config_id: int | str) -> None:
        target_id = self._normalize_id(config_id)
        existing = await self.repository.get(target_id)
        if existing is None:
            raise CustomException(msg="模型配置不存在", code=10404, status_code=404)
        if not existing.get("enabled"):
            raise CustomException(msg="停用的模型不能设为默认", code=10422, status_code=422)
        await self.repository.clear_default()
        await self.repository.update(target_id, {"is_default": True})

    async def set_active(self, config_id: int | str) -> None:
        """兼容旧接口：现在切换的是平台默认模型，不再按用户激活。"""
        await self.set_default(config_id)

    @staticmethod
    def _normalize_id(config_id: int | str) -> int:
        try:
            return int(config_id)
        except (TypeError, ValueError):
            raise CustomException(msg="模型配置 ID 无效", code=10422, status_code=422)


AiModelConfigService = PlatformAiModelConfigService


async def resolve_default_model_config(auth: AuthSchema, *, repository: Any | None = None) -> dict[str, Any]:
    repo = repository or DatabaseAiConfigRepository(auth)
    default = await repo.get_default()
    if default:
        return _runtime_model_config(default, auth=auth, source="platform_default")
    if settings.OPENAI_BASE_URL and settings.OPENAI_API_KEY and settings.OPENAI_MODEL:
        return {
            "base_url": settings.OPENAI_BASE_URL,
            "api_key": settings.OPENAI_API_KEY,
            "model_id": settings.OPENAI_MODEL,
            "temperature": AgnoFactory.AGENT_TEMPERATURE,
            "max_tokens": None,
            "timeout_seconds": 60,
            "config_id": None,
            "provider_type": "openai_compatible",
            "source": "env_default",
            "tenant_id": auth.tenant_id if auth else None,
            "user_id": getattr(auth.user, "id", None) if auth and auth.user else None,
        }
    raise CustomException(msg="未配置平台默认 AI 模型", code=10422, status_code=422)


async def resolve_effective_model_config(redis: Redis | None, auth: AuthSchema) -> dict[str, Any]:
    """兼容旧调用名：所有用户统一使用平台默认模型。"""
    return await resolve_default_model_config(auth)


async def _langchain_chat_runner(
    *,
    model_config: dict[str, Any],
    message: str,
    system_prompt: str | None = None,
    response_format: Any | None = None,
) -> Any:
    from langchain_core.messages import HumanMessage, SystemMessage
    from langchain_openai import ChatOpenAI

    kwargs: dict[str, Any] = {
        "model": model_config["model_id"],
        "api_key": model_config["api_key"],
        "base_url": model_config["base_url"],
        "temperature": model_config.get("temperature", 0.7),
        "timeout": model_config.get("timeout_seconds", 60),
    }
    if model_config.get("max_tokens"):
        kwargs["max_tokens"] = model_config["max_tokens"]

    llm = ChatOpenAI(**kwargs)
    runnable = llm.with_structured_output(response_format) if response_format is not None else llm
    messages: list[Any] = []
    if system_prompt:
        messages.append(SystemMessage(content=system_prompt))
    messages.append(HumanMessage(content=message))
    result = await runnable.ainvoke(messages)
    if response_format is not None:
        return result
    if isinstance(result, str):
        return result
    content = getattr(result, "content", None)
    if isinstance(content, str):
        return content
    return json.dumps(result, ensure_ascii=False)


class AiRuntimeService:
    """基于平台默认模型的 LangChain 运行时。"""

    def __init__(
        self,
        auth: AuthSchema,
        *,
        repository: Any | None = None,
        chat_runner: Any | None = None,
        redis: Redis | None = None,
        audit_enabled: bool = True,
    ) -> None:
        self.auth = auth
        self.repository = repository
        self.chat_runner = chat_runner or _langchain_chat_runner
        self.redis = redis
        self.audit_enabled = audit_enabled

    async def chat(
        self,
        message: str,
        *,
        source_module: str,
        source_feature: str,
        system_prompt: str | None = None,
        prompt_key: str | None = None,
        business_id: str | None = None,
    ) -> str:
        model_config: dict[str, Any] | None = None
        started_at = perf_counter()
        try:
            model_config = await resolve_default_model_config(self.auth, repository=self.repository)
            response = await self.chat_runner(model_config=model_config, message=message, system_prompt=system_prompt)
            duration_ms = int((perf_counter() - started_at) * 1000)
            if self.audit_enabled:
                await record_ai_call_audit(
                    self.redis,
                    AiCallAuditRecord(
                        user_id=getattr(self.auth.user, "id", None) if self.auth and self.auth.user else None,
                        tenant_id=self.auth.tenant_id if self.auth else None,
                        message=message,
                        model_config=model_config,
                        source_module=source_module,
                        source_feature=source_feature,
                        runtime="langchain",
                        provider="openai-compatible",
                        prompt_key=prompt_key,
                        business_id=business_id,
                        duration_ms=duration_ms,
                        status="success",
                    ),
                )
            return str(response)
        except Exception as exc:
            duration_ms = int((perf_counter() - started_at) * 1000)
            if self.audit_enabled:
                await record_ai_call_audit(
                    self.redis,
                    AiCallAuditRecord(
                        user_id=getattr(self.auth.user, "id", None) if self.auth and self.auth.user else None,
                        tenant_id=self.auth.tenant_id if self.auth else None,
                        message=message,
                        model_config=model_config,
                        source_module=source_module,
                        source_feature=source_feature,
                        runtime="langchain",
                        provider="openai-compatible",
                        prompt_key=prompt_key,
                        business_id=business_id,
                        duration_ms=duration_ms,
                        status="error",
                        error=str(exc),
                    ),
                )
            raise

    async def json_generate(
        self,
        prompt: str,
        *,
        response_format: Any,
        source_module: str,
        source_feature: str,
    ) -> str:
        result = await self.structured_generate(
            prompt,
            response_format=response_format,
            source_module=source_module,
            source_feature=source_feature,
        )
        if isinstance(result, str):
            return result
        if hasattr(result, "model_dump"):
            return json.dumps(result.model_dump(), ensure_ascii=False, default=str)
        return json.dumps(result, ensure_ascii=False, default=str)

    async def structured_generate(
        self,
        prompt: str,
        *,
        response_format: Any,
        source_module: str,
        source_feature: str,
        prompt_key: str | None = None,
        business_id: str | None = None,
        system_prompt: str | None = None,
    ) -> Any:
        model_config: dict[str, Any] | None = None
        started_at = perf_counter()
        try:
            model_config = await resolve_default_model_config(self.auth, repository=self.repository)
            result = await self.chat_runner(
                model_config=model_config,
                message=prompt,
                system_prompt=system_prompt,
                response_format=response_format,
            )
            duration_ms = int((perf_counter() - started_at) * 1000)
            if self.audit_enabled:
                await record_ai_call_audit(
                    self.redis,
                    AiCallAuditRecord(
                        user_id=getattr(self.auth.user, "id", None) if self.auth and self.auth.user else None,
                        tenant_id=self.auth.tenant_id if self.auth else None,
                        message=prompt,
                        model_config=model_config,
                        source_module=source_module,
                        source_feature=source_feature,
                        runtime="langchain",
                        provider="openai-compatible",
                        prompt_key=prompt_key,
                        business_id=business_id,
                        duration_ms=duration_ms,
                        status="success",
                    ),
                )
            return result
        except Exception as exc:
            duration_ms = int((perf_counter() - started_at) * 1000)
            if self.audit_enabled:
                await record_ai_call_audit(
                    self.redis,
                    AiCallAuditRecord(
                        user_id=getattr(self.auth.user, "id", None) if self.auth and self.auth.user else None,
                        tenant_id=self.auth.tenant_id if self.auth else None,
                        message=prompt,
                        model_config=model_config,
                        source_module=source_module,
                        source_feature=source_feature,
                        runtime="langchain",
                        provider="openai-compatible",
                        prompt_key=prompt_key,
                        business_id=business_id,
                        duration_ms=duration_ms,
                        status="error",
                        error=str(exc),
                    ),
                )
            raise
