from app.core.base_crud import CRUDBase
from app.core.base_schema import AuthSchema

from .model import BusinessNotificationModel, NoticeModel
from .schema import (
    BusinessNotificationCreateSchema,
    BusinessNotificationUpdateSchema,
    NoticeCreateSchema,
    NoticeUpdateSchema,
)


class NoticeCRUD(CRUDBase[NoticeModel, NoticeCreateSchema, NoticeUpdateSchema]):
    """公告数据层"""

    def __init__(self, auth: AuthSchema) -> None:
        super().__init__(model=NoticeModel, auth=auth)


class BusinessNotificationCRUD(
    CRUDBase[BusinessNotificationModel, BusinessNotificationCreateSchema, BusinessNotificationUpdateSchema]
):
    """业务通知数据层。"""

    def __init__(self, auth: AuthSchema) -> None:
        super().__init__(model=BusinessNotificationModel, auth=auth)
