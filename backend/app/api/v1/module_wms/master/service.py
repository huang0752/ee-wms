from app.core.base_schema import AuthSchema, BatchSetAvailable
from app.core.exceptions import CustomException

from .crud import WmsMasterCRUD, model_for_resource
from .schema import (
    WmsMasterCreateSchema,
    WmsMasterOutSchema,
    WmsMasterQueryParam,
    WmsMasterResource,
    WmsMasterUpdateSchema,
)

RESOURCE_LABELS: dict[WmsMasterResource, str] = {
    "warehouse": "仓库",
    "zone": "库区",
    "location": "库位",
    "material": "物料",
    "supplier": "供应商",
    "customer": "客户",
    "barcode-rule": "条码规则",
}


class WmsMasterService:
    def __init__(self, auth: AuthSchema, resource: WmsMasterResource) -> None:
        self.auth = auth
        self.resource = resource
        self.crud = WmsMasterCRUD(auth, resource)

    async def detail(self, id: int) -> WmsMasterOutSchema:
        return await self.crud.get_or_404(id=id, out_schema=WmsMasterOutSchema)

    async def page(
        self,
        page_no: int,
        page_size: int,
        search: WmsMasterQueryParam | None = None,
        order_by: list[dict[str, str]] | None = None,
    ) -> dict:
        offset = (page_no - 1) * page_size
        return await self.crud.page(
            offset=offset,
            limit=page_size,
            order_by=order_by or [{"id": "desc"}],
            search=self._model_search(vars(search)) if search else {},
            out_schema=WmsMasterOutSchema,
        )

    async def create(self, data: WmsMasterCreateSchema) -> WmsMasterOutSchema:
        await self._validate_payload(data)
        await self._ensure_code_unique(data.code)
        obj = await self.crud.create(data=self._model_payload(data))
        return WmsMasterOutSchema.model_validate(obj)

    async def update(self, id: int, data: WmsMasterUpdateSchema) -> WmsMasterOutSchema:
        await self.crud.get_or_404(id=id, msg="更新失败，该数据不存在")
        await self._validate_payload(data)
        await self._ensure_code_unique(data.code, exclude_id=id)
        obj = await self.crud.update(id=id, data=self._model_payload(data))
        return WmsMasterOutSchema.model_validate(obj)

    async def delete(self, ids: list[int]) -> None:
        if not ids:
            raise CustomException(msg="删除失败，删除对象不能为空")
        existing = await self.crud.get_list(search={"id": ("in", ids)})
        if len(existing) != len(set(ids)):
            raise CustomException(msg="删除失败，部分数据不存在")
        await self.crud.delete(ids=ids)

    async def set_available(self, data: BatchSetAvailable) -> None:
        existing = await self.crud.get_list(search={"id": ("in", data.ids)})
        if len(existing) != len(set(data.ids)):
            raise CustomException(msg="状态修改失败，部分数据不存在")
        await self.crud.set(ids=data.ids, status=data.status)

    async def _ensure_code_unique(self, code: str, exclude_id: int | None = None) -> None:
        search: dict = {"code": code}
        if self.auth.tenant_id is not None:
            search["tenant_id"] = self.auth.tenant_id
        existing = await self.crud.get(**search)
        if existing and existing.id != exclude_id:
            label = RESOURCE_LABELS[self.resource]
            raise CustomException(msg=f"{label}编码已存在", status_code=400)

    async def _validate_payload(self, data: WmsMasterCreateSchema) -> None:
        if self.resource == "barcode-rule" and not data.object_type:
            raise CustomException(msg="条码规则必须填写对象类型", status_code=400)

    def _model_payload(self, data: WmsMasterCreateSchema) -> dict:
        model = model_for_resource(self.resource)
        valid_fields = set(model.__mapper__.columns.keys())
        payload = data.model_dump(exclude_unset=True)
        return {key: value for key, value in payload.items() if key in valid_fields}

    def _model_search(self, search: dict) -> dict:
        model = model_for_resource(self.resource)
        valid_fields = set(model.__mapper__.columns.keys())
        return {key: value for key, value in search.items() if key in valid_fields}
