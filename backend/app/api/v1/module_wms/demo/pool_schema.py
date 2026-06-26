from pydantic import BaseModel, Field


class WmsDemoSampleItemOut(BaseModel):
    id: int
    pool_id: int
    group_key: str
    group_name: str
    item_key: str
    item_name: str
    acceptance_scope: str | None = None
    spec_patterns: list[str] = Field(default_factory=list)
    supplier_patterns: list[str] = Field(default_factory=list)
    material_patterns: list[str] = Field(default_factory=list)
    storage_traits: list[str] = Field(default_factory=list)
    quality_traits: list[str] = Field(default_factory=list)
    weight: int = 1
    enabled: bool = True

    model_config = {"from_attributes": True}


class WmsDemoSamplePoolOut(BaseModel):
    id: int
    code: str
    name: str
    industry: str
    is_system: bool
    is_active: bool
    base_pool_id: int | None = None
    prompt_template: str | None = None
    fallback_template: str | None = None
    config: dict | None = None
    items: list[WmsDemoSampleItemOut] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class WmsDemoSamplePoolUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    is_active: bool | None = None
    prompt_template: str | None = Field(default=None, max_length=5000)
    fallback_template: str | None = Field(default=None, max_length=5000)
    config: dict | None = None


class WmsDemoSampleItemUpdate(BaseModel):
    item_name: str | None = Field(default=None, min_length=1, max_length=128)
    acceptance_scope: str | None = Field(default=None, max_length=1000)
    spec_patterns: list[str] | None = Field(default=None, max_length=20)
    supplier_patterns: list[str] | None = Field(default=None, max_length=20)
    material_patterns: list[str] | None = Field(default=None, max_length=20)
    storage_traits: list[str] | None = Field(default=None, max_length=10)
    quality_traits: list[str] | None = Field(default=None, max_length=10)
    weight: int | None = Field(default=None, ge=1, le=10)
    enabled: bool | None = None
