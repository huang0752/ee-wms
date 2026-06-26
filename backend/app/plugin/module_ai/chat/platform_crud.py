from typing import Any

import sqlalchemy as sa

from app.core.base_crud import CRUDBase
from app.core.base_schema import AuthSchema

from .model import AiModelConfigModel
from .schema import AiModelConfigSchema, AiModelConfigUpdateSchema


class AiModelConfigCRUD(CRUDBase[AiModelConfigModel, AiModelConfigSchema, AiModelConfigUpdateSchema]):
    """平台级 AI 模型配置数据层。"""

    def __init__(self, auth: AuthSchema) -> None:
        super().__init__(model=AiModelConfigModel, auth=auth)

    async def clear_default(self) -> None:
        stmt = sa.update(AiModelConfigModel).where(AiModelConfigModel.is_default.is_(True)).values(is_default=False)
        await self.db.execute(stmt)
        await self.db.flush()

    async def get_default(self) -> AiModelConfigModel | None:
        stmt = (
            sa.select(AiModelConfigModel)
            .where(
                AiModelConfigModel.is_deleted.is_(False),
                AiModelConfigModel.enabled.is_(True),
                AiModelConfigModel.is_default.is_(True),
            )
            .order_by(AiModelConfigModel.id.desc())
            .limit(1)
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()


class DatabaseAiConfigRepository:
    """Service 使用的仓储接口，测试可用内存仓储替换。"""

    def __init__(self, auth: AuthSchema) -> None:
        self.crud = AiModelConfigCRUD(auth)

    @staticmethod
    def _to_dict(item: AiModelConfigModel | None) -> dict[str, Any] | None:
        if item is None:
            return None
        return {
            "id": item.id,
            "provider_type": item.provider_type,
            "name": item.name,
            "base_url": item.base_url,
            "api_key_cipher": item.api_key_cipher,
            "model_id": item.model_id,
            "temperature": item.temperature,
            "max_tokens": item.max_tokens,
            "timeout_seconds": item.timeout_seconds,
            "enabled": item.enabled,
            "is_default": item.is_default,
            "description": item.description,
            "created_time": item.created_time.strftime("%Y-%m-%d %H:%M:%S") if item.created_time else None,
        }

    async def list(self) -> list[dict[str, Any]]:
        stmt = (
            sa.select(AiModelConfigModel)
            .where(AiModelConfigModel.is_deleted.is_(False))
            .order_by(AiModelConfigModel.is_default.desc(), AiModelConfigModel.id.desc())
        )
        rows = (await self.crud.db.execute(stmt)).scalars().all()
        return [self._to_dict(item) for item in rows if self._to_dict(item) is not None]

    async def get(self, config_id: int) -> dict[str, Any] | None:
        item = await self.crud.detail(id=config_id)
        return self._to_dict(item)

    async def create(self, data: dict[str, Any]) -> dict[str, Any]:
        item = AiModelConfigModel(**data)
        self.crud.db.add(item)
        await self.crud.db.flush()
        await self.crud.db.refresh(item)
        result = self._to_dict(item)
        assert result is not None
        return result

    async def update(self, config_id: int, data: dict[str, Any]) -> dict[str, Any] | None:
        item = await self.crud.detail(id=config_id)
        if item is None:
            return None
        for key, value in data.items():
            setattr(item, key, value)
        await self.crud.db.flush()
        await self.crud.db.refresh(item)
        return self._to_dict(item)

    async def delete(self, config_id: int) -> bool:
        if await self.crud.detail(id=config_id) is None:
            return False
        await self.crud.delete(ids=[config_id])
        return True

    async def clear_default(self) -> None:
        await self.crud.clear_default()

    async def get_default(self) -> dict[str, Any] | None:
        return self._to_dict(await self.crud.get_default())
