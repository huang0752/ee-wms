from sqlalchemy import select

from app.core.base_schema import AuthSchema
from app.core.exceptions import CustomException

from .fixtures.electrical_equipment import DEFAULT_POOL
from .model import WmsDemoSampleItemModel, WmsDemoSamplePoolModel
from .pool_schema import (
    WmsDemoSampleItemOut,
    WmsDemoSampleItemUpdate,
    WmsDemoSamplePoolOut,
    WmsDemoSamplePoolUpdate,
)


class WmsDemoSamplePoolService:
    SYSTEM_TENANT_ID = 1

    def __init__(self, auth: AuthSchema) -> None:
        self.auth = auth
        if auth.db is None:
            raise CustomException(msg="数据库会话不存在")
        self.db = auth.db

    async def list_pools(self) -> list[WmsDemoSamplePoolOut]:
        await self.ensure_default_pool()
        stmt = (
            select(WmsDemoSamplePoolModel)
            .where(
                WmsDemoSamplePoolModel.is_deleted.is_(False),
                WmsDemoSamplePoolModel.is_active.is_(True),
                (WmsDemoSamplePoolModel.is_system.is_(True)) | (WmsDemoSamplePoolModel.tenant_id == self._tenant_id()),
            )
            .order_by(WmsDemoSamplePoolModel.is_system.desc(), WmsDemoSamplePoolModel.id.asc())
        )
        pools = list((await self.db.execute(stmt)).scalars().all())
        return [await self._pool_out(pool) for pool in pools]

    async def get_pool(self, pool_id: int | None = None) -> WmsDemoSamplePoolOut:
        await self.ensure_default_pool()
        pool = await self._get_visible_pool(pool_id) if pool_id else await self._get_default_pool()
        return await self._pool_out(pool)

    async def copy_pool(self, pool_id: int) -> WmsDemoSamplePoolOut:
        source = await self._get_visible_pool(pool_id)
        code = f"{source.code}_tenant_{self._tenant_id()}"
        existing = (
            await self.db.execute(
                select(WmsDemoSamplePoolModel)
                .where(
                    WmsDemoSamplePoolModel.tenant_id == self._tenant_id(),
                    WmsDemoSamplePoolModel.code == code,
                    WmsDemoSamplePoolModel.is_deleted.is_(False),
                )
                .limit(1)
            )
        ).scalars().first()
        if existing:
            return await self._pool_out(existing)

        pool = WmsDemoSamplePoolModel(
            tenant_id=self._tenant_id(),
            code=code,
            name=f"{source.name}（租户副本）",
            industry=source.industry,
            is_system=False,
            is_active=True,
            base_pool_id=source.id,
            prompt_template=source.prompt_template,
            fallback_template=source.fallback_template,
            config=source.config,
            created_id=self._user_id(),
            updated_id=self._user_id(),
        )
        self.db.add(pool)
        await self.db.flush()
        for item in await self._items(source.id or 0):
            self.db.add(
                WmsDemoSampleItemModel(
                    tenant_id=self._tenant_id(),
                    pool_id=pool.id,
                    group_key=item.group_key,
                    group_name=item.group_name,
                    item_key=item.item_key,
                    item_name=item.item_name,
                    acceptance_scope=item.acceptance_scope,
                    spec_patterns=item.spec_patterns,
                    supplier_patterns=item.supplier_patterns,
                    material_patterns=item.material_patterns,
                    storage_traits=item.storage_traits,
                    quality_traits=item.quality_traits,
                    weight=item.weight,
                    enabled=item.enabled,
                    created_id=self._user_id(),
                    updated_id=self._user_id(),
                )
            )
        await self.db.commit()
        return await self._pool_out(pool)

    async def update_pool(self, pool_id: int, data: WmsDemoSamplePoolUpdate) -> WmsDemoSamplePoolOut:
        pool = await self._get_tenant_pool(pool_id)
        values = data.model_dump(exclude_unset=True)
        for key, value in values.items():
            setattr(pool, key, value)
        pool.updated_id = self._user_id()
        await self.db.commit()
        return await self._pool_out(pool)

    async def update_item(self, item_id: int, data: WmsDemoSampleItemUpdate) -> WmsDemoSampleItemOut:
        item = (
            await self.db.execute(
                select(WmsDemoSampleItemModel)
                .join(WmsDemoSamplePoolModel, WmsDemoSamplePoolModel.id == WmsDemoSampleItemModel.pool_id)
                .where(
                    WmsDemoSampleItemModel.id == item_id,
                    WmsDemoSampleItemModel.tenant_id == self._tenant_id(),
                    WmsDemoSampleItemModel.is_deleted.is_(False),
                    WmsDemoSamplePoolModel.is_system.is_(False),
                    WmsDemoSamplePoolModel.tenant_id == self._tenant_id(),
                )
                .limit(1)
            )
        ).scalars().first()
        if not item:
            raise CustomException(msg="样本项不存在或不可编辑", status_code=404)
        values = data.model_dump(exclude_unset=True)
        for key, value in values.items():
            setattr(item, key, value)
        item.updated_id = self._user_id()
        await self.db.commit()
        return self._item_out(item)

    async def ensure_default_pool(self) -> WmsDemoSamplePoolModel:
        existing = (
            await self.db.execute(
                select(WmsDemoSamplePoolModel)
                .where(
                    WmsDemoSamplePoolModel.code == DEFAULT_POOL["code"],
                    WmsDemoSamplePoolModel.is_system.is_(True),
                    WmsDemoSamplePoolModel.is_deleted.is_(False),
                )
                .limit(1)
            )
        ).scalars().first()
        if existing:
            return existing

        pool = WmsDemoSamplePoolModel(
            tenant_id=self.SYSTEM_TENANT_ID,
            code=DEFAULT_POOL["code"],
            name=DEFAULT_POOL["name"],
            industry=DEFAULT_POOL["industry"],
            is_system=True,
            is_active=True,
            prompt_template=DEFAULT_POOL["prompt_template"],
            fallback_template=DEFAULT_POOL["fallback_template"],
            config=DEFAULT_POOL["config"],
        )
        self.db.add(pool)
        await self.db.flush()
        for item in DEFAULT_POOL["items"]:
            self.db.add(WmsDemoSampleItemModel(tenant_id=self.SYSTEM_TENANT_ID, pool_id=pool.id, enabled=True, **item))
        await self.db.flush()
        return pool

    async def enabled_items(self, pool_id: int | None = None) -> list[WmsDemoSampleItemModel]:
        pool = await self._get_visible_pool(pool_id) if pool_id else await self._get_default_pool()
        return [
            item
            for item in await self._items(pool.id or 0)
            if item.enabled and not item.is_deleted
        ]

    async def _get_default_pool(self) -> WmsDemoSamplePoolModel:
        tenant_pool = (
            await self.db.execute(
                select(WmsDemoSamplePoolModel)
                .where(
                    WmsDemoSamplePoolModel.tenant_id == self._tenant_id(),
                    WmsDemoSamplePoolModel.is_active.is_(True),
                    WmsDemoSamplePoolModel.is_deleted.is_(False),
                )
                .order_by(WmsDemoSamplePoolModel.id.asc())
                .limit(1)
            )
        ).scalars().first()
        if tenant_pool:
            return tenant_pool
        return await self.ensure_default_pool()

    async def _get_visible_pool(self, pool_id: int) -> WmsDemoSamplePoolModel:
        pool = (
            await self.db.execute(
                select(WmsDemoSamplePoolModel)
                .where(
                    WmsDemoSamplePoolModel.id == pool_id,
                    WmsDemoSamplePoolModel.is_deleted.is_(False),
                    (WmsDemoSamplePoolModel.is_system.is_(True)) | (WmsDemoSamplePoolModel.tenant_id == self._tenant_id()),
                )
                .limit(1)
            )
        ).scalars().first()
        if not pool:
            raise CustomException(msg="样本池不存在", status_code=404)
        return pool

    async def _get_tenant_pool(self, pool_id: int) -> WmsDemoSamplePoolModel:
        pool = (
            await self.db.execute(
                select(WmsDemoSamplePoolModel)
                .where(
                    WmsDemoSamplePoolModel.id == pool_id,
                    WmsDemoSamplePoolModel.tenant_id == self._tenant_id(),
                    WmsDemoSamplePoolModel.is_system.is_(False),
                    WmsDemoSamplePoolModel.is_deleted.is_(False),
                )
                .limit(1)
            )
        ).scalars().first()
        if not pool:
            raise CustomException(msg="样本池不存在或不可编辑", status_code=404)
        return pool

    async def _pool_out(self, pool: WmsDemoSamplePoolModel) -> WmsDemoSamplePoolOut:
        out = WmsDemoSamplePoolOut.model_validate(pool)
        out.items = [self._item_out(item) for item in await self._items(pool.id or 0)]
        return out

    async def _items(self, pool_id: int) -> list[WmsDemoSampleItemModel]:
        return list(
            (
                await self.db.execute(
                    select(WmsDemoSampleItemModel)
                    .where(WmsDemoSampleItemModel.pool_id == pool_id, WmsDemoSampleItemModel.is_deleted.is_(False))
                    .order_by(WmsDemoSampleItemModel.group_key.asc(), WmsDemoSampleItemModel.id.asc())
                )
            ).scalars().all()
        )

    @staticmethod
    def _item_out(item: WmsDemoSampleItemModel) -> WmsDemoSampleItemOut:
        data = WmsDemoSampleItemOut.model_validate(item)
        data.spec_patterns = list(item.spec_patterns or [])
        data.supplier_patterns = list(item.supplier_patterns or [])
        data.material_patterns = list(item.material_patterns or [])
        data.storage_traits = list(item.storage_traits or [])
        data.quality_traits = list(item.quality_traits or [])
        return data

    def _tenant_id(self) -> int:
        return self.auth.tenant_id or 1

    def _user_id(self) -> int | None:
        user = self.auth.get_user()
        return getattr(user, "id", None)
