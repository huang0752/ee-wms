from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints, field_validator

TitleText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]
ShortText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=128)]
MediumText = Annotated[str, StringConstraints(strip_whitespace=True, max_length=300)]
KeyText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64)]
TraitText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64)]


class WmsDemoAiScenarioSummary(BaseModel):
    title: TitleText = Field(default="WMS试用数据场景")
    summary: MediumText = Field(default="")
    highlights: list[Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]] = Field(
        default_factory=list,
        max_length=6,
    )

    @field_validator("highlights")
    @classmethod
    def remove_empty_highlights(cls, value: list[str]) -> list[str]:
        return [item for item in value if item]


class WmsDemoAiMaterialName(BaseModel):
    key: KeyText
    name: ShortText
    spec_hint: ShortText | None = None
    category: TraitText | None = None
    storage_trait: TraitText | None = None


class WmsDemoAiEnrichmentOut(BaseModel):
    source: Literal["ai", "rule_fallback"] = "ai"
    scenario: WmsDemoAiScenarioSummary = Field(default_factory=WmsDemoAiScenarioSummary)
    warehouses: list[ShortText] = Field(default_factory=list, max_length=20)
    zones: list[ShortText] = Field(default_factory=list, max_length=80)
    materials: list[WmsDemoAiMaterialName] = Field(default_factory=list, max_length=600)
    suppliers: list[ShortText] = Field(default_factory=list, max_length=80)
    customers: list[ShortText] = Field(default_factory=list, max_length=60)
    warning_reasons: list[ShortText] = Field(default_factory=list, max_length=200)
    check_reasons: list[ShortText] = Field(default_factory=list, max_length=80)
