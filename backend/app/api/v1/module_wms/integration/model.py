from sqlalchemy import JSON, Boolean, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import ModelMixin, TenantMixin, UserMixin


class WmsIntegrationRequestModel(ModelMixin, TenantMixin, UserMixin):
    __tablename__ = "wms_integration_request"
    __table_args__ = (
        UniqueConstraint("tenant_id", "source", "idempotency_key", name="uq_wms_integration_tenant_source_key"),
        {"comment": "WMS外部系统集成请求"},
    )
    __loader_options__: list[str] = ["created_by", "updated_by", "deleted_by", "tenant_by"]

    source: Mapped[str] = mapped_column(String(32), nullable=False, index=True, comment="来源系统")
    contract: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment="契约类型")
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False, index=True, comment="幂等键")
    external_no: Mapped[str | None] = mapped_column(String(128), default=None, nullable=True, index=True, comment="外部单号")
    status: Mapped[str] = mapped_column(String(32), default="accepted", nullable=False, index=True, comment="处理状态")
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, comment="请求载荷")
    result: Mapped[dict | None] = mapped_column(JSON, default=None, nullable=True, comment="处理结果")
    error: Mapped[str | None] = mapped_column(Text, default=None, nullable=True, comment="错误信息")
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, comment="是否试用数据")
    demo_batch_id: Mapped[str | None] = mapped_column(String(64), default=None, nullable=True, index=True, comment="试用数据批次")
