from app.core.base_crud import CRUDBase
from app.core.base_schema import AuthSchema

from .model import BusinessTaskModel
from .schema import BusinessTaskCreateSchema, BusinessTaskUpdateSchema


class BusinessTaskCRUD(CRUDBase[BusinessTaskModel, BusinessTaskCreateSchema, BusinessTaskUpdateSchema]):
    """业务长任务数据层。"""

    def __init__(self, auth: AuthSchema) -> None:
        super().__init__(model=BusinessTaskModel, auth=auth)
