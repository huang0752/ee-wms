from sqlalchemy import Boolean, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base_model import ModelMixin


class AiModelConfigModel(ModelMixin):
    """平台级 AI/LLM 模型配置。"""

    __tablename__ = "ai_model_config"
    __table_args__ = {"comment": "平台级 AI 模型配置"}

    provider_type: Mapped[str] = mapped_column(String(64), nullable=False, default="openai_compatible", index=True, comment="供应商类型")
    name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, comment="配置名称")
    base_url: Mapped[str] = mapped_column(String(500), nullable=False, comment="API Base URL")
    api_key_cipher: Mapped[str] = mapped_column(Text, nullable=False, comment="API Key 密文")
    model_id: Mapped[str] = mapped_column(String(128), nullable=False, comment="模型 ID")
    temperature: Mapped[float] = mapped_column(Float, nullable=False, default=0.7, comment="温度")
    max_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True, default=None, comment="最大 token")
    timeout_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=60, comment="超时时间（秒）")
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True, comment="是否启用")
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True, comment="是否默认模型")
    description: Mapped[str | None] = mapped_column(Text, nullable=True, default=None, comment="备注")
