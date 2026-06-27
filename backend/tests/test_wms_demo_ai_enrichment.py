from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.api.v1.module_wms.demo.enrichment_schema import (
    WmsDemoAiEnrichmentOut,
    WmsDemoAiMaterialName,
    WmsDemoAiScenarioSummary,
)
from app.api.v1.module_wms.demo.enrichment_service import WmsDemoEnrichmentService
from app.api.v1.module_wms.demo.schema import WmsDemoInitSchema


def test_ai_enrichment_output_accepts_structured_names() -> None:
    data = WmsDemoAiEnrichmentOut(
        scenario=WmsDemoAiScenarioSummary(
            title="华南电工装备仓储试用场景",
            summary="覆盖来料检验、批次入库、销售出库、生产领料和库存预警。",
            highlights=["来料检验闭环", "安全库存预警"],
        ),
        warehouses=["主材立体仓", "成套设备暂存仓"],
        zones=["重型原材区", "成品待发区"],
        materials=[
            WmsDemoAiMaterialName(
                key="material-1",
                name="油浸式变压器高压绕组组件",
                spec_hint="S13-M-10kV",
                category="变压器",
                storage_trait="重货防潮",
            )
        ],
        suppliers=["华中变压器组件供应商"],
        customers=["南网配网改造项目部"],
        warning_reasons=["安全库存低于项目领料需求"],
        check_reasons=["账实差异来自线缆盘具复核"],
    )

    assert data.scenario.title.startswith("华南")
    assert data.materials[0].name == "油浸式变压器高压绕组组件"
    assert data.source == "ai"


def test_ai_enrichment_output_limits_names() -> None:
    long_name = "高" * 129
    try:
        WmsDemoAiEnrichmentOut(
            warehouses=[long_name],
            zones=[],
            materials=[],
            suppliers=[],
            customers=[],
            warning_reasons=[],
            check_reasons=[],
        )
    except ValidationError as exc:
        assert "String should have at most 128 characters" in str(exc)
    else:
        raise AssertionError("expected max length validation error")


class FakeRuntime:
    def __init__(self, result):
        self.result = result
        self.calls = []

    async def structured_generate(self, prompt, **kwargs):
        self.calls.append({"prompt": prompt, **kwargs})
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


@pytest.mark.asyncio
async def test_enrichment_service_uses_structured_ai() -> None:
    runtime = FakeRuntime(
        WmsDemoAiEnrichmentOut(
            warehouses=["智能主材仓"],
            zones=["高压成套区"],
            materials=[],
            suppliers=[],
            customers=[],
            warning_reasons=[],
            check_reasons=[],
        )
    )
    service = WmsDemoEnrichmentService(auth=SimpleNamespace(tenant_id=1, user=None), runtime=runtime)

    result = await service.enrich(WmsDemoInitSchema(profile={"company_name": "测试公司"}), product_mix=[])

    assert result.source == "ai"
    assert result.warehouses == ["智能主材仓"]
    assert runtime.calls[0]["source_module"] == "module_wms"
    assert runtime.calls[0]["source_feature"] == "demo_data_enrichment"
    assert runtime.calls[0]["prompt_key"] == "wms.demo_data_enrichment.v1"
    assert "不得生成编号" in runtime.calls[0]["system_prompt"]
    assert "外键" in runtime.calls[0]["system_prompt"]
    assert "数量" in runtime.calls[0]["system_prompt"]
    assert "状态流转" in runtime.calls[0]["system_prompt"]
    assert "库存余额" in runtime.calls[0]["system_prompt"]


@pytest.mark.asyncio
async def test_enrichment_service_falls_back_when_ai_disabled() -> None:
    runtime = FakeRuntime(RuntimeError("should not be called"))
    service = WmsDemoEnrichmentService(auth=SimpleNamespace(tenant_id=1, user=None), runtime=runtime)

    result = await service.enrich(
        WmsDemoInitSchema(profile={"company_name": "测试公司"}, use_ai_enrichment=False),
        product_mix=[{"name": "低压开关柜", "category": "开关柜", "spec_patterns": ["GCS"], "storage_traits": ["防潮"]}],
    )

    assert result.source == "rule_fallback"
    assert result.scenario.title == "测试公司 WMS试用场景"
    assert result.materials[0].name == "低压开关柜"
    assert runtime.calls == []


@pytest.mark.asyncio
async def test_enrichment_service_falls_back_when_ai_fails() -> None:
    runtime = FakeRuntime(RuntimeError("model unavailable"))
    service = WmsDemoEnrichmentService(auth=SimpleNamespace(tenant_id=1, user=None), runtime=runtime)

    result = await service.enrich(WmsDemoInitSchema(profile={"company_name": "测试公司"}), product_mix=[])

    assert result.source == "rule_fallback"
    assert result.scenario.title == "测试公司 WMS试用场景"
