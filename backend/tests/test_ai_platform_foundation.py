from types import SimpleNamespace
from typing import Any

import pytest
from pydantic import BaseModel

from app.core.base_schema import AuthSchema
from app.core.exceptions import CustomException
from app.plugin.module_ai.chat.audit import AiCallAuditRecord
from app.plugin.module_ai.chat.registry import default_ai_registry
from app.plugin.module_ai.chat.schema import AiModelConfigSchema, AiModelConfigUpdateSchema
from app.plugin.module_ai.chat.service import AiRuntimeService, PlatformAiModelConfigService, resolve_default_model_config


class MemoryAiConfigRepository:
    def __init__(self) -> None:
        self.items: list[dict[str, Any]] = []
        self.next_id = 1

    async def list(self) -> list[dict[str, Any]]:
        return [item.copy() for item in self.items]

    async def get(self, config_id: int) -> dict[str, Any] | None:
        item = next((item for item in self.items if item["id"] == config_id), None)
        return item.copy() if item else None

    async def create(self, data: dict[str, Any]) -> dict[str, Any]:
        item = {**data, "id": self.next_id, "created_time": "2026-01-01 00:00:00"}
        self.next_id += 1
        self.items.append(item)
        return item.copy()

    async def update(self, config_id: int, data: dict[str, Any]) -> dict[str, Any] | None:
        for item in self.items:
            if item["id"] == config_id:
                item.update(data)
                return item.copy()
        return None

    async def delete(self, config_id: int) -> bool:
        before = len(self.items)
        self.items = [item for item in self.items if item["id"] != config_id]
        return len(self.items) < before

    async def clear_default(self) -> None:
        for item in self.items:
            item["is_default"] = False

    async def get_default(self) -> dict[str, Any] | None:
        item = next((item for item in self.items if item.get("is_default") and item.get("enabled", True)), None)
        return item.copy() if item else None


def make_auth(*, superuser: bool = True) -> AuthSchema:
    return AuthSchema(
        user=SimpleNamespace(id=9001, username="alice", dept_id=7, is_superuser=superuser),
        tenant_id=42,
    )


class RuntimeStructuredOut(BaseModel):
    summary: str
    risk_level: str


@pytest.mark.asyncio
async def test_platform_model_config_does_not_expose_api_key_and_preserves_existing_key() -> None:
    repo = MemoryAiConfigRepository()
    service = PlatformAiModelConfigService(make_auth(), repository=repo)

    created = await service.create(
        AiModelConfigSchema(
            name="DeepSeek",
            provider_type="deepseek",
            base_url="https://api.deepseek.com/v1",
            api_key="sk-secret-123456",
            model_id="deepseek-v4-flash",
            temperature=0.5,
            max_tokens=200000,
            timeout_seconds=30,
            enabled=True,
            is_default=True,
        )
    )

    assert "api_key" not in created
    assert "api_key_cipher" not in created
    assert created["has_api_key"] is True
    assert created["api_key_masked"] == "****3456"
    assert created["is_default"] is True

    listed = await service.list()
    assert listed["active_id"] == created["id"]
    assert listed["default_id"] == created["id"]
    assert "api_key" not in listed["items"][0]

    original_cipher = repo.items[0]["api_key_cipher"]
    updated = await service.update(
        created["id"],
        AiModelConfigUpdateSchema(
            name="Renamed",
            provider_type="deepseek",
            base_url="https://api.deepseek.com/v1",
            model_id="deepseek-reasoner",
            temperature=0.2,
            max_tokens=4096,
            timeout_seconds=45,
            enabled=True,
            is_default=True,
        ),
    )

    assert "api_key" not in updated
    assert repo.items[0]["api_key_cipher"] == original_cipher
    assert service.decrypt_api_key(original_cipher) == "sk-secret-123456"
    assert updated["model_id"] == "deepseek-reasoner"


@pytest.mark.asyncio
async def test_only_superuser_can_manage_platform_model_config() -> None:
    repo = MemoryAiConfigRepository()
    service = PlatformAiModelConfigService(make_auth(superuser=False), repository=repo)

    with pytest.raises(CustomException):
        await service.create(
            AiModelConfigSchema(
                name="Denied",
                base_url="https://api.example.com/v1",
                api_key="sk-denied",
                model_id="example-model",
            )
        )


@pytest.mark.asyncio
async def test_only_one_platform_default_model_config() -> None:
    repo = MemoryAiConfigRepository()
    service = PlatformAiModelConfigService(make_auth(), repository=repo)

    first = await service.create(
        AiModelConfigSchema(name="First", base_url="https://first.example/v1", api_key="sk-first", model_id="first", is_default=True)
    )
    second = await service.create(
        AiModelConfigSchema(name="Second", base_url="https://second.example/v1", api_key="sk-second", model_id="second", is_default=True)
    )

    listed = await service.list()
    defaults = [item for item in listed["items"] if item["is_default"]]
    assert [item["id"] for item in defaults] == [second["id"]]
    assert first["id"] != second["id"]


@pytest.mark.asyncio
async def test_runtime_uses_platform_default_model_config() -> None:
    repo = MemoryAiConfigRepository()
    service = PlatformAiModelConfigService(make_auth(), repository=repo)
    await service.create(
        AiModelConfigSchema(
            name="Active",
            base_url="https://active.example/v1",
            api_key="sk-active",
            model_id="active-model",
            temperature=0.1,
            is_default=True,
        )
    )

    captured: dict[str, Any] = {}

    async def fake_runner(**kwargs):
        captured.update(kwargs)
        return "ok"

    result = await AiRuntimeService(make_auth(), repository=repo, chat_runner=fake_runner, audit_enabled=False).chat(
        "hello",
        source_module="module_wms",
        source_feature="stock_warning",
    )

    assert result == "ok"
    assert captured["model_config"]["source"] == "platform_default"
    assert captured["model_config"]["model_id"] == "active-model"
    assert captured["model_config"]["api_key"] == "sk-active"
    assert captured["message"] == "hello"


@pytest.mark.asyncio
async def test_ai_runtime_structured_generate_uses_langchain_contract() -> None:
    repo = MemoryAiConfigRepository()
    service = PlatformAiModelConfigService(make_auth(), repository=repo)
    await service.create(
        AiModelConfigSchema(
            name="DeepSeek",
            provider_type="deepseek",
            base_url="https://api.deepseek.com",
            api_key="sk-active",
            model_id="deepseek-v4-flash",
            is_default=True,
        )
    )

    async def fake_structured_runner(**kwargs):
        assert kwargs["response_format"] is RuntimeStructuredOut
        assert kwargs["model_config"]["base_url"] == "https://api.deepseek.com"
        assert kwargs["system_prompt"] == "只返回结构化结果"
        return RuntimeStructuredOut(summary="库存预警集中在低安全库存物料。", risk_level="warning")

    runtime = AiRuntimeService(
        make_auth(),
        repository=repo,
        chat_runner=fake_structured_runner,
        audit_enabled=False,
    )

    result = await runtime.structured_generate(
        "基于规则摘要生成结构化结果",
        response_format=RuntimeStructuredOut,
        source_module="module_wms",
        source_feature="dashboard_summary",
        prompt_key="wms.dashboard_summary.v1",
        business_id="tenant:1",
        system_prompt="只返回结构化结果",
    )

    assert result.summary == "库存预警集中在低安全库存物料。"
    assert result.risk_level == "warning"


@pytest.mark.asyncio
async def test_missing_platform_default_model_config_is_controlled_error() -> None:
    repo = MemoryAiConfigRepository()

    with pytest.raises(CustomException):
        await resolve_default_model_config(make_auth(), repository=repo)


def test_prompt_and_action_registry_has_minimal_default_entries() -> None:
    prompt = default_ai_registry.get_prompt("chat.default")
    action = default_ai_registry.get_action("navigate.system")

    assert prompt is not None
    assert "中文" in prompt.instructions
    assert action is not None
    assert action.kind == "navigate"


def test_ai_call_audit_record_redacts_api_key() -> None:
    record = AiCallAuditRecord(
        event_id="event-1",
        user_id=9001,
        tenant_id=42,
        session_id="session-1",
        message="hello",
        model_config={"model_id": "active-model", "api_key": "sk-secret"},
        source_module="module_wms",
        source_feature="stock_warning",
        runtime="langchain",
        provider="openai-compatible",
        prompt_key="wms.warning_advice.v1",
        business_id="warning:12",
        duration_ms=123,
        status="success",
    )

    dumped = record.to_safe_dict()
    assert dumped["model_config"]["model_id"] == "active-model"
    assert dumped["source_module"] == "module_wms"
    assert dumped["runtime"] == "langchain"
    assert dumped["provider"] == "openai-compatible"
    assert dumped["prompt_key"] == "wms.warning_advice.v1"
    assert dumped["business_id"] == "warning:12"
    assert dumped["duration_ms"] == 123
    assert "api_key" not in dumped["model_config"]
