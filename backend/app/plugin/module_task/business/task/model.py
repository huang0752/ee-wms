from sqlalchemy import JSON, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import ModelMixin, TenantMixin, UserMixin


class BusinessTaskModel(ModelMixin, TenantMixin, UserMixin):
    """通用业务长任务表。"""

    __tablename__: str = "task_business_task"
    __table_args__ = {"comment": "通用业务长任务表", "extend_existing": True}
    __loader_options__: list[str] = ["created_by", "updated_by", "deleted_by", "tenant_by"]

    module: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment="业务模块")
    biz_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment="业务类型")
    biz_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True, comment="业务对象ID")
    title: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="任务标题")
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False, index=True, comment="任务状态")
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="进度百分比")
    payload: Mapped[dict | None] = mapped_column(JSON, nullable=True, comment="任务输入")
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True, comment="任务结果")
    error: Mapped[str | None] = mapped_column(Text, nullable=True, comment="错误信息")
    is_demo: Mapped[bool] = mapped_column(default=False, nullable=False, index=True, comment="是否试用数据")
    demo_batch_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True, comment="试用数据批次ID")
    description: Mapped[str | None] = mapped_column(Text, default=None, nullable=True, comment="备注")
