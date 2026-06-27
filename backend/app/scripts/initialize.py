"""
数据库初始化与种子数据管理。

简化策略：多数表为空时一次性插入种子数据，已有数据则跳过。
少量有稳定业务键的配置表会幂等追加缺失数据。
改 JSON → 清空对应表 → 重启即可；追加型表可直接重启补齐缺失项。
"""

import asyncio
import json
import re
from datetime import datetime, time
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.module_platform.email.model import EmailConfigModel, EmailTemplateModel
from app.api.v1.module_platform.invoice.model import InvoiceModel
from app.api.v1.module_platform.menu.model import MenuModel
from app.api.v1.module_platform.order.model import OrderModel, PaymentRecordModel, RefundModel
from app.api.v1.module_platform.package.model import PackageMenuModel, PackageModel, PackagePluginModel
from app.api.v1.module_platform.plugin.model import PluginModel, TenantPluginModel
from app.api.v1.module_platform.tenant.model import TenantModel, TenantUserModel
from app.api.v1.module_system.dept.model import DeptModel
from app.api.v1.module_system.dict.model import DictDataModel, DictTypeModel
from app.api.v1.module_system.log.model import LoginLogModel, OperationLogModel
from app.api.v1.module_system.notice.model import BusinessNotificationModel, NoticeModel, NoticeReadModel
from app.api.v1.module_system.params.model import ParamsModel
from app.api.v1.module_system.position.model import PositionModel
from app.api.v1.module_system.role.model import RoleModel
from app.api.v1.module_system.ticket.model import TicketModel
from app.api.v1.module_system.user.model import UserModel, UserRolesModel
from app.api.v1.module_wms.arrival.model import WmsArrivalLineModel, WmsArrivalOrderModel
from app.api.v1.module_wms.check.model import WmsStockCheckLineModel, WmsStockCheckOrderModel
from app.api.v1.module_wms.demo.model import WmsDemoSampleItemModel, WmsDemoSamplePoolModel
from app.api.v1.module_wms.inbound.model import WmsInboundLineModel, WmsInboundOrderModel
from app.api.v1.module_wms.inspection.model import WmsInspectionLineModel, WmsInspectionTaskModel
from app.api.v1.module_wms.integration.model import WmsIntegrationRequestModel
from app.api.v1.module_wms.issue.model import WmsIssueLineModel, WmsIssueOrderModel
from app.api.v1.module_wms.master.model import (
    WmsBarcodeRuleModel,
    WmsCustomerModel,
    WmsLocationModel,
    WmsMaterialModel,
    WmsSupplierModel,
    WmsWarehouseModel,
    WmsZoneModel,
)
from app.api.v1.module_wms.outbound.model import WmsOutboundLineModel, WmsOutboundOrderModel
from app.api.v1.module_wms.stock.model import (
    WmsStockBalanceModel,
    WmsStockBatchModel,
    WmsStockFlowModel,
    WmsStockLockModel,
    WmsTraceLinkModel,
)
from app.api.v1.module_wms.transfer.model import WmsTransferLineModel, WmsTransferOrderModel
from app.api.v1.module_wms.warning.model import WmsStockWarningModel
from app.config.path_conf import SCRIPT_DIR
from app.config.setting import settings
from app.core.assembly import get_assembly, known_plugin_module_codes, plugin_code_candidates
from app.core.database import async_db_session, create_tables
from app.core.logger import logger
from app.plugin.module_ai.chat.model import AiModelConfigModel
from app.plugin.module_example.demo.model import DemoModel
from app.plugin.module_task.business.task.model import BusinessTaskModel
from app.plugin.module_task.cronjob.node.model import NodeModel
from app.plugin.module_task.workflow.nodes.model import WorkflowNodeTypeModel
from app.scripts.seed_loader import resolve_seed_files


class InitializeData:
    """初始化数据库和基础数据"""

    _DATETIME_RE = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")
    _DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
    _TIME_RE = re.compile(r"^\d{2}:\d{2}:\d{2}(\.\d+)?$")

    # 按依赖关系排序：先基础表，再关联表
    prepare_init_models: list[type] = [
        # ── 平台管理：基础表 ──
        PackageModel,
        TenantModel,
        PluginModel,
        MenuModel,
        # ── 系统管理：基础表 ──
        ParamsModel,
        DeptModel,
        RoleModel,
        DictTypeModel,
        DictDataModel,
        PositionModel,
        UserModel,
        # ── 平台管理：依赖用户的表 ──
        EmailConfigModel,
        EmailTemplateModel,
        OrderModel,
        InvoiceModel,
        PaymentRecordModel,
        RefundModel,
        # ── 关联表 ──
        UserRolesModel,
        TenantUserModel,
        PackageMenuModel,
        PackagePluginModel,
        TenantPluginModel,
        # ── 其他系统/业务表 ──
        NoticeModel,
        NoticeReadModel,
        BusinessNotificationModel,
        TicketModel,
        # ── 日志表（追加写入） ──
        LoginLogModel,
        OperationLogModel,
        # ── 插件表 ──
        NodeModel,
        BusinessTaskModel,
        WorkflowNodeTypeModel,
        AiModelConfigModel,
        DemoModel,
        # ── WMS 产品表 ──
        WmsWarehouseModel,
        WmsZoneModel,
        WmsLocationModel,
        WmsMaterialModel,
        WmsSupplierModel,
        WmsCustomerModel,
        WmsBarcodeRuleModel,
        WmsStockBatchModel,
        WmsStockBalanceModel,
        WmsStockFlowModel,
        WmsStockLockModel,
        WmsTraceLinkModel,
        WmsArrivalOrderModel,
        WmsArrivalLineModel,
        WmsInspectionTaskModel,
        WmsInspectionLineModel,
        WmsInboundOrderModel,
        WmsInboundLineModel,
        WmsIntegrationRequestModel,
        WmsOutboundOrderModel,
        WmsOutboundLineModel,
        WmsIssueOrderModel,
        WmsIssueLineModel,
        WmsTransferOrderModel,
        WmsTransferLineModel,
        WmsStockCheckOrderModel,
        WmsStockCheckLineModel,
        WmsStockWarningModel,
        WmsDemoSamplePoolModel,
        WmsDemoSampleItemModel,
    ]

    # 树形模型：JSON 含嵌套 children，需递归创建对象
    _RECURSIVE_TABLES: set[str] = {"platform_menu", "sys_dept"}

    def __init__(self) -> None:
        self._seed_files_by_table = resolve_seed_files()
        self._assembly = get_assembly()
        self._disabled_module_codes = {
            module_code
            for module_code in known_plugin_module_codes()
            if not self._assembly.is_plugin_enabled(module_code)
        }
        self._disabled_plugin_codes = {
            plugin_code
            for module_code in self._disabled_module_codes
            for plugin_code in plugin_code_candidates(module_code)
        }
        self._disabled_plugin_seed_ids: set[int] = set()
        self._plugin_seed_id_map: dict[int, int] = {}

    async def init_db(self) -> None:
        """建表并导入种子数据"""
        try:
            await create_tables()
        except asyncio.exceptions.TimeoutError:
            logger.error("❌️ 数据库表结构初始化超时")
            raise

        async with async_db_session() as session:
            async with session.begin():
                await self.__init_data(session)

    async def __init_data(self, db: AsyncSession) -> None:
        """按依赖顺序初始化各表种子数据"""
        dict_type_mapping: dict[str, Any] = {}  # dict_type → DictTypeModel 实例

        init_models = [
            model for model in self.prepare_init_models
            if model.__tablename__ in self._seed_files_by_table
        ]

        for model in init_models:
            table_name = model.__tablename__

            data = await self.__load_json(table_name)
            if not data:
                logger.info(f"⏭️  跳过 {table_name} 表，无初始化数据")
                continue

            try:
                await self.__reset_identity_if_empty(db, model)
                await self.__sync_identity_to_max(db, model)

                # 树形表（platform_menu / sys_dept）：递归创建含 children 的对象
                if table_name in self._RECURSIVE_TABLES:
                    count = await db.execute(select(func.count()).select_from(model))
                    if count.scalar():
                        if table_name == "platform_menu":
                            added = await self.__append_missing_menu_tree(db, data, model)
                            if added:
                                logger.info(f"✅️ 已向 {table_name} 追加 {added} 条缺失菜单")
                            else:
                                logger.info(f"⏭️  跳过 {table_name} 表数据初始化（表已有数据且无缺失菜单）")
                            continue
                        logger.info(f"⏭️  跳过 {table_name} 表数据初始化（表已有数据）")
                        continue
                    objs = self.__create_objects_with_children(data, model)
                    db.add_all(objs)
                    await db.flush()
                    logger.info(f"✅️ 已向 {table_name} 写入初始化数据")
                    continue

                # 字典类型表：存储类型映射供字典数据使用
                if table_name == "sys_dict_type":
                    count = await db.execute(select(func.count()).select_from(model))
                    if count.scalar():
                        logger.info(f"⏭️  跳过 {table_name} 表数据初始化（表已有数据）")
                        continue
                    objs = []
                    for item in data:
                        obj = model(**item)
                        objs.append(obj)
                        dict_type_mapping[item["dict_type"]] = obj
                    db.add_all(objs)
                    await db.flush()
                    logger.info(f"✅️ 已向 {table_name} 写入初始化数据")
                    continue

                # 字典数据表：关联 dict_type_id
                if table_name == "sys_dict_data":
                    count = await db.execute(select(func.count()).select_from(model))
                    if count.scalar():
                        logger.info(f"⏭️  跳过 {table_name} 表数据初始化（表已有数据）")
                        continue
                    objs = []
                    for item in data:
                        dict_type_str = item.get("dict_type")
                        if dict_type_str not in dict_type_mapping:
                            logger.warning(f"⚠️  未找到字典类型 {dict_type_str}，跳过")
                            continue
                        item["dict_type_id"] = dict_type_mapping[dict_type_str].id
                        objs.append(model(**item))
                    db.add_all(objs)
                    await db.flush()
                    logger.info(f"✅️ 已向 {table_name} 写入初始化数据")
                    continue

                # 日志表：追加写入，已有数据跳过
                if table_name in ("sys_login_log", "sys_operation_log"):
                    count = await db.execute(select(func.count()).select_from(model))
                    if count.scalar():
                        logger.info(f"⏭️  跳过 {table_name} 表数据初始化（表已有数据）")
                        continue
                    objs = [model(**item) for item in data]
                    db.add_all(objs)
                    await db.flush()
                    logger.info(f"✅️ 已向 {table_name} 写入 {len(objs)} 条")
                    continue

                # 邮件模板按 template_code 追加缺失项，避免新增业务模板被已有旧数据挡住。
                if table_name == "platform_email_template":
                    added = await self.__append_missing_by_unique_key(db, data, model, "template_code")
                    if added:
                        logger.info(f"✅️ 已向 {table_name} 追加 {added} 条缺失模板")
                    else:
                        logger.info(f"⏭️  跳过 {table_name} 表数据初始化（无缺失模板）")
                    continue

                if table_name == "platform_package_menu":
                    count = await db.execute(select(func.count()).select_from(model))
                    if count.scalar():
                        logger.info(f"⏭️  跳过 {table_name} 表数据初始化（表已有数据）")
                        continue
                    data = await self.__filter_existing_relation_seed(
                        db, data, PackageModel, "package_id", MenuModel, "menu_id"
                    )
                    if not data:
                        data = await self.__build_default_package_menu_seed(db)
                    if not data:
                        logger.info(f"⏭️  跳过 {table_name} 表数据初始化（无有效菜单授权）")
                        continue

                if table_name == "platform_package_plugin":
                    count = await db.execute(select(func.count()).select_from(model))
                    if count.scalar():
                        logger.info(f"⏭️  跳过 {table_name} 表数据初始化（表已有数据）")
                        continue
                    data = await self.__filter_existing_relation_seed(
                        db, data, PackageModel, "package_id", PluginModel, "plugin_id"
                    )
                    if not data:
                        logger.info(f"⏭️  跳过 {table_name} 表数据初始化（无有效插件授权）")
                        continue

                # 普通表：空表时插入，已有数据跳过
                count = await db.execute(select(func.count()).select_from(model))
                if count.scalar():
                    logger.info(f"⏭️  跳过 {table_name} 表数据初始化（表已有数据）")
                    continue
                objs = [model(**item) for item in data]
                db.add_all(objs)
                await db.flush()
                logger.info(f"✅️ 已向 {table_name} 写入初始化数据")

            except Exception:
                logger.error(f"❌️ 初始化 {table_name} 表数据失败")
                raise

        await self.__sync_seed_identity_sequences(db, init_models)
        await self.__backfill_tenant_memberships(db)
        await self.__sync_seed_identity_sequences(db, init_models)

    async def __reset_identity_if_empty(self, db: AsyncSession, model: type) -> None:
        """Reset PostgreSQL identity sequence for empty seed tables after failed retries."""
        if settings.DATABASE_TYPE not in {"postgres", "postgresql"}:
            return
        if "id" not in model.__table__.columns:
            return
        count = await db.execute(select(func.count()).select_from(model))
        if count.scalar():
            return
        sequence_name = (
            await db.execute(
                text("SELECT pg_get_serial_sequence(:table_name, 'id')"),
                {"table_name": model.__tablename__},
            )
        ).scalar_one_or_none()
        if sequence_name:
            await db.execute(
                text("SELECT setval(CAST(:sequence_name AS regclass), 1, false)"),
                {"sequence_name": sequence_name},
            )

    async def __sync_seed_identity_sequences(self, db: AsyncSession, models: list[type]) -> None:
        """Keep PostgreSQL sequences aligned after seed rows with fixed IDs are loaded."""
        if settings.DATABASE_TYPE not in {"postgres", "postgresql"}:
            return
        synced = 0
        for model in models:
            if await self.__sync_identity_to_max(db, model):
                synced += 1
        if synced:
            logger.info(f"✅️ 已同步 {synced} 个 seed 表自增序列")

    async def __sync_identity_to_max(self, db: AsyncSession, model: type) -> bool:
        """Set a PostgreSQL ID sequence to MAX(id), so the next insert uses MAX(id) + 1."""
        if settings.DATABASE_TYPE not in {"postgres", "postgresql"}:
            return False
        if "id" not in model.__table__.columns:
            return False
        sequence_name = (
            await db.execute(
                text("SELECT pg_get_serial_sequence(:table_name, 'id')"),
                {"table_name": model.__tablename__},
            )
        ).scalar_one_or_none()
        if not sequence_name:
            return False
        max_id = (await db.execute(select(func.max(model.id)))).scalar_one_or_none()
        if max_id is None:
            return False
        await db.execute(
            text("SELECT setval(CAST(:sequence_name AS regclass), :max_id, true)"),
            {"sequence_name": sequence_name, "max_id": max_id},
        )
        return True

    async def __filter_existing_relation_seed(
        self,
        db: AsyncSession,
        data: list[dict],
        left_model: type,
        left_key: str,
        right_model: type,
        right_key: str,
    ) -> list[dict]:
        left_ids = set((await db.execute(select(left_model.id))).scalars().all())
        right_ids = set((await db.execute(select(right_model.id))).scalars().all())
        filtered = [
            item
            for item in data
            if item.get(left_key) in left_ids and item.get(right_key) in right_ids
        ]
        skipped = len(data) - len(filtered)
        if skipped:
            logger.warning(f"⚠️  跳过 {skipped} 条无效关系 seed: {left_key}/{right_key}")
        return filtered

    async def __build_default_package_menu_seed(self, db: AsyncSession) -> list[dict]:
        """Use current tenant-visible menus when legacy package-menu ids are stale."""
        package_ids = set((await db.execute(select(PackageModel.id))).scalars().all())
        menu_ids = set(
            (
                await db.execute(
                    select(MenuModel.id).where(
                        MenuModel.scope == "tenant",
                        MenuModel.status == 0,
                    )
                )
            )
            .scalars()
            .all()
        )
        if not package_ids or not menu_ids:
            return []
        logger.warning("⚠️  套餐菜单 seed 固定 ID 已失效，按当前租户菜单生成默认套餐授权")
        return [
            {"package_id": package_id, "menu_id": menu_id}
            for package_id in sorted(package_ids)
            for menu_id in sorted(menu_ids)
        ]

    async def __backfill_tenant_memberships(self, db: AsyncSession) -> None:
        """回填历史用户的租户关系，保证会话租户校验不会误杀旧数据。"""
        stmt = (
            select(UserModel)
            .where(
                UserModel.tenant_id.is_not(None),
                UserModel.is_deleted.is_(False),
            )
        )
        users = (await db.execute(stmt)).scalars().all()
        added = 0
        for user in users:
            exists_stmt = (
                select(TenantUserModel)
                .where(
                    TenantUserModel.user_id == user.id,
                    TenantUserModel.tenant_id == user.tenant_id,
                )
                .limit(1)
            )
            if (await db.execute(exists_stmt)).scalar_one_or_none():
                continue
            has_any_stmt = select(TenantUserModel).where(TenantUserModel.user_id == user.id).limit(1)
            has_any = (await db.execute(has_any_stmt)).scalar_one_or_none()
            db.add(
                TenantUserModel(
                    user_id=user.id,
                    tenant_id=user.tenant_id,
                    role="owner" if user.is_superuser else "member",
                    is_default=0 if has_any else 1,
                )
            )
            added += 1
        if added:
            await db.flush()
            logger.info(f"✅️ 已回填 {added} 条用户租户关系")

    @staticmethod
    def __create_objects_with_children(data: list[dict], model_class: type) -> list:
        """递归创建树形模型实例，处理嵌套 children 并注入 parent_id"""

        def _create(obj_data: dict) -> Any:
            children_data = obj_data.pop("children", [])

            # JSON 中子节点 parent_id 通常为 null，先按原始值创建
            obj = model_class(**obj_data)

            if children_data:
                obj.children = [_create(child) for child in children_data]

            return obj

        return [_create(item) for item in data]

    async def __append_missing_menu_tree(
        self,
        db: AsyncSession,
        data: list[dict],
        model_class: type,
        parent_id: int | None = None,
    ) -> int:
        """向已有菜单表幂等追加 seed 中缺失的菜单节点。"""
        added = 0
        for raw_item in data:
            item = dict(raw_item)
            children = item.pop("children", [])
            menu = await self.__find_existing_menu(db, model_class, item, parent_id)
            if menu is None:
                menu = model_class(**item, parent_id=parent_id)
                db.add(menu)
                await db.flush()
                added += 1
            added += await self.__append_missing_menu_tree(db, children, model_class, menu.id)
        return added

    async def __find_existing_menu(
        self,
        db: AsyncSession,
        model_class: type,
        item: dict,
        parent_id: int | None,
    ) -> Any | None:
        """按稳定路由/权限信息查找已存在菜单，避免重复追加。"""
        conditions = [model_class.parent_id.is_(parent_id)] if parent_id is None else [model_class.parent_id == parent_id]
        route_name = item.get("route_name")
        route_path = item.get("route_path")
        component_path = item.get("component_path")
        permission = item.get("permission")

        if route_name:
            conditions.append(model_class.route_name == route_name)
        elif route_path:
            conditions.append(model_class.route_path == route_path)
        elif component_path:
            conditions.append(model_class.component_path == component_path)
        elif permission:
            conditions.extend(
                [
                    model_class.permission == permission,
                    model_class.name == item.get("name"),
                    model_class.type == item.get("type"),
                ]
            )
        else:
            conditions.extend(
                [
                    model_class.name == item.get("name"),
                    model_class.type == item.get("type"),
                ]
            )

        stmt = select(model_class).where(*conditions).limit(1)
        return (await db.execute(stmt)).scalar_one_or_none()

    async def __append_missing_by_unique_key(
        self,
        db: AsyncSession,
        data: list[dict],
        model_class: type,
        key: str,
    ) -> int:
        """按稳定业务键追加缺失 seed，保留已有记录的人工修改。"""
        added = 0
        column = getattr(model_class, key)
        for item in data:
            key_value = item.get(key)
            if key_value is None:
                continue
            exists_stmt = select(model_class).where(column == key_value).limit(1)
            if (await db.execute(exists_stmt)).scalar_one_or_none():
                continue
            db.add(model_class(**item))
            added += 1
        if added:
            await db.flush()
        return added

    async def __load_json(self, filename: str) -> list[dict]:
        """读取并解析种子数据 JSON 文件"""
        json_paths = self._seed_files_by_table.get(filename) or [SCRIPT_DIR / f"{filename}.json"]
        if not json_paths:
            return []

        try:
            raw: list[dict] = []
            for json_path in json_paths:
                if not json_path.exists():
                    continue
                with open(json_path, encoding="utf-8") as f:
                    loaded = json.loads(f.read())
                if not isinstance(loaded, list):
                    raise TypeError(f"{json_path} 须为 JSON 数组")
                raw.extend(loaded)
            data = self.__filter_seed_data(filename, raw)
            return [self._parse_date_strings(item) for item in data]
        except json.JSONDecodeError as e:
            logger.error(f"❌️ 解析 {filename} seed 失败: {e!s}")
            raise
        except Exception as e:
            logger.error(f"❌️ 读取 {filename} seed 失败: {e!s}")
            raise

    def __filter_seed_data(self, table_name: str, data: list[dict]) -> list[dict]:
        """按当前 assembly 裁剪 legacy seed 中的可选插件数据。"""
        if table_name == "platform_menu":
            return self.__filter_menu_tree(data)
        if not self._disabled_module_codes:
            return data
        if table_name == "platform_plugin":
            return self.__filter_platform_plugins(data)
        if table_name in {"platform_package_plugin", "platform_tenant_plugin"}:
            return self.__filter_plugin_relations(data)
        return data

    def __filter_menu_tree(self, data: list[dict]) -> list[dict]:
        return self._assembly.filter_menu_tree(data)

    def __filter_platform_plugins(self, data: list[dict]) -> list[dict]:
        filtered: list[dict] = []
        self._disabled_plugin_seed_ids = set()
        self._plugin_seed_id_map = {}

        for original_id, item in enumerate(data, start=1):
            if item.get("code") in self._disabled_plugin_codes:
                self._disabled_plugin_seed_ids.add(original_id)
                continue
            self._plugin_seed_id_map[original_id] = len(filtered) + 1
            filtered.append(item)
        return filtered

    def __filter_plugin_relations(self, data: list[dict]) -> list[dict]:
        filtered: list[dict] = []
        for item in data:
            original_plugin_id = item.get("plugin_id")
            if original_plugin_id in self._disabled_plugin_seed_ids:
                continue
            plugin_id = self._plugin_seed_id_map.get(original_plugin_id, original_plugin_id)
            filtered.append({**item, "plugin_id": plugin_id})
        return filtered

    @classmethod
    def _parse_date_strings(cls, data: dict) -> dict:
        """递归转换 JSON 中的日期时间字符串为 datetime 对象（兼容 PostgreSQL）"""
        result = {}
        for key, value in data.items():
            if isinstance(value, str):
                if cls._DATETIME_RE.match(value):
                    result[key] = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
                elif cls._DATE_RE.match(value):
                    result[key] = datetime.strptime(value, "%Y-%m-%d").date()
                elif cls._TIME_RE.match(value):
                    result[key] = time.fromisoformat(value)
                else:
                    result[key] = value
            elif isinstance(value, dict):
                result[key] = cls._parse_date_strings(value)
            else:
                result[key] = value
        return result
