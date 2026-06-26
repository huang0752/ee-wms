from types import SimpleNamespace

import pytest

from app.api.v1.module_wms.intelligence.ai_service import WmsIntelligenceAIService
from app.api.v1.module_wms.intelligence.rule_service import WmsIntelligenceRuleService
from app.api.v1.module_wms.intelligence.schema import WmsIntelligenceDraft, WmsIntelligenceSource, WmsIntelligenceSummaryOut, WmsRiskLevel
from app.core.base_schema import AuthSchema


class FakeDashboardService:
    async def summary(self):
        return SimpleNamespace(
            metrics=[
                SimpleNamespace(label="未关闭预警", value=3, status="warning"),
                SimpleNamespace(label="待处理单据", value=5, status="warning"),
            ],
            tasks=[SimpleNamespace(title="处理库存预警", status="active", time="3 条")],
            next_steps=["按预警处理安全库存与短缺物料"],
        )


class FailingRuntime:
    async def structured_generate(self, *args, **kwargs):
        raise RuntimeError("model unavailable")


class StructuredRuntime:
    async def structured_generate(self, *args, **kwargs):
        assert kwargs["response_format"] is WmsIntelligenceDraft
        assert kwargs["source_module"] == "module_wms"
        assert kwargs["source_feature"] == "dashboard_summary"
        assert kwargs["prompt_key"] == "wms.dashboard_summary.v1"
        return WmsIntelligenceDraft(
            summary="当前库存预警集中在安全库存不足物料，建议先处理 3 条预警。",
            bullets=["优先处理安全库存不足", "复核待处理单据"],
        )


def make_auth() -> AuthSchema:
    return AuthSchema(user=SimpleNamespace(id=1, username="tester"), tenant_id=1)


def test_intelligence_summary_schema_has_source_and_risk_level() -> None:
    summary = WmsIntelligenceSummaryOut(
        title="今日仓储风险摘要",
        summary="当前有 2 条未关闭预警，建议先处理安全库存不足物料。",
        risk_level=WmsRiskLevel.warning,
        source=WmsIntelligenceSource.rule_fallback,
        bullets=["处理安全库存不足", "复核待出库锁定库存"],
        actions=[{"label": "查看预警", "route": "/module-wms/analytics/warning"}],
    )

    assert summary.source == WmsIntelligenceSource.rule_fallback
    assert summary.risk_level == WmsRiskLevel.warning
    assert summary.actions[0].route == "/module-wms/analytics/warning"


@pytest.mark.asyncio
async def test_rule_dashboard_summary_uses_current_metrics(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.api.v1.module_wms.intelligence.rule_service.WmsDashboardService",
        lambda _auth: FakeDashboardService(),
    )

    result = await WmsIntelligenceRuleService(make_auth()).dashboard_summary()

    assert result.source == WmsIntelligenceSource.rule_fallback
    assert result.risk_level == WmsRiskLevel.warning
    assert "3 条未关闭预警" in result.summary


@pytest.mark.asyncio
async def test_ai_dashboard_summary_falls_back_to_rules(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.api.v1.module_wms.intelligence.rule_service.WmsDashboardService",
        lambda _auth: FakeDashboardService(),
    )

    result = await WmsIntelligenceAIService(make_auth(), runtime=FailingRuntime()).dashboard_summary()

    assert result.source == WmsIntelligenceSource.rule_fallback
    assert "未关闭预警" in result.summary


@pytest.mark.asyncio
async def test_ai_dashboard_summary_uses_structured_output(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.api.v1.module_wms.intelligence.rule_service.WmsDashboardService",
        lambda _auth: FakeDashboardService(),
    )

    result = await WmsIntelligenceAIService(make_auth(), runtime=StructuredRuntime()).dashboard_summary()

    assert result.source == WmsIntelligenceSource.ai
    assert result.summary.startswith("当前库存预警")
    assert result.bullets == ["优先处理安全库存不足", "复核待处理单据"]


def test_warning_advice_has_handling_action() -> None:
    warning = SimpleNamespace(
        id=12,
        warning_type="safety_stock",
        material_id=101,
        warehouse_id=3,
        current_qty=5,
        threshold_qty=20,
    )

    result = WmsIntelligenceRuleService(make_auth()).warning_advice_from_warning(warning)

    assert result.warning_id == 12
    assert result.risk_level == WmsRiskLevel.warning
    assert "安全库存" in result.reason
    assert result.actions[0].permission == "module_wms:stock:query"


def test_outbound_candidate_scoring_prefers_fifo_and_matches() -> None:
    candidates = [
        SimpleNamespace(id=1, material_id=10, warehouse_id=2, location_id=3, batch_no="B1", available_qty="5", frozen_qty="0", pending_qty="0", defective_qty="0"),
        SimpleNamespace(id=2, material_id=10, warehouse_id=2, location_id=4, batch_no="B2", available_qty="8", frozen_qty="0", pending_qty="0", defective_qty="0"),
    ]

    scored = WmsIntelligenceRuleService(make_auth()).score_outbound_candidates(candidates, warehouse_id=2, location_id=3)

    assert scored[0].balance_id == 1
    assert scored[0].score > scored[1].score
    assert "匹配指定库位" in scored[0].rule_reasons


def test_wms_intelligence_router_is_registered() -> None:
    from app.api.v1.module_wms import wms_router

    routes = {getattr(route, "path", "") for route in wms_router.routes}

    assert "/wms/intelligence/dashboard-summary" in routes
