from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base_model import MappedBase, ModelMixin, TenantMixin, UserMixin


class NoticeModel(ModelMixin, TenantMixin, UserMixin):
    """
    通知公告表
    """

    __tablename__: str = "sys_notice"
    __table_args__: dict[str, str] = {"comment": "通知公告表"}
    __loader_options__: list[str] = ["created_by", "updated_by", "deleted_by", "tenant_by"]

    notice_title: Mapped[str] = mapped_column(String(64), nullable=False, comment="公告标题")
    notice_type: Mapped[str] = mapped_column(String(1), nullable=False, comment="公告类型(1通知 2公告)")
    notice_content: Mapped[str | None] = mapped_column(Text, nullable=True, comment="公告内容")
    status: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="状态(0:启动 1:停用)", index=True)
    description: Mapped[str | None] = mapped_column(Text, default=None, nullable=True, comment="备注")


class NoticeReadModel(MappedBase):
    """
    通知已读记录表 — 记录用户对公告的已读状态。

    设计说明:
    - 不继承 TenantMixin：该表按 user_id 隔离，租户上下文由所属 notice 间接确定
    - (user_id, notice_id) 唯一约束 — 未建立记录即代表未读
    - 仅用于标记已读时间，不做其他业务用途
    - 不继承 ModelMixin：使用 (user_id, notice_id) 复合主键，无需自增 id 列
      （避免 SQLite 不支持复合主键列 autoincrement 的问题）
    """

    __tablename__: str = "sys_notice_read"
    __table_args__: tuple = (
        UniqueConstraint("user_id", "notice_id", name="uq_user_notice_read"),
        {"comment": "通知已读记录表"},
    )
    __loader_options__: list[str] = ["notice"]

    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("sys_user.id", ondelete="CASCADE"), primary_key=True, comment="用户ID")
    notice_id: Mapped[int] = mapped_column(Integer, ForeignKey("sys_notice.id", ondelete="CASCADE"), primary_key=True, comment="通知ID")
    read_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now, comment="已读时间")

    # 关联
    notice: Mapped[NoticeModel] = relationship("NoticeModel", lazy="selectin")


class BusinessNotificationModel(ModelMixin, TenantMixin, UserMixin):
    """业务通知/待办/预警表。"""

    __tablename__: str = "sys_business_notification"
    __table_args__: dict[str, str] = {"comment": "业务通知待办预警表"}
    __loader_options__: list[str] = ["created_by", "updated_by", "deleted_by", "tenant_by"]

    module: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment="业务模块")
    biz_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True, comment="业务类型")
    biz_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True, comment="业务对象ID")
    title: Mapped[str] = mapped_column(String(128), nullable=False, comment="标题")
    content: Mapped[str | None] = mapped_column(Text, nullable=True, comment="内容")
    level: Mapped[str] = mapped_column(String(32), default="info", nullable=False, index=True, comment="级别")
    action_url: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="处理链接")
    handled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True, comment="是否已处理")
    handled_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="处理时间")
    description: Mapped[str | None] = mapped_column(Text, default=None, nullable=True, comment="备注")
