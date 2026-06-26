from decimal import Decimal
from typing import Any

from app.core.base_schema import AuthSchema

from ..dashboard.service import WmsDashboardService
from .schema import (
    WmsIntelligenceAction,
    WmsIntelligenceSource,
    WmsIntelligenceSummaryOut,
    WmsOutboundCandidateScore,
    WmsRiskLevel,
    WmsWarningAdviceOut,
)


class WmsIntelligenceRuleService:
    def __init__(self, auth: AuthSchema) -> None:
        self.auth = auth

    async def dashboard_summary(self) -> WmsIntelligenceSummaryOut:
        summary = await WmsDashboardService(self.auth).summary()
        metric_map = {item.label: item.value for item in summary.metrics}
        open_warnings = int(metric_map.get("未关闭预警", 0) or 0)
        pending_docs = int(metric_map.get("待处理单据", 0) or 0)
        risk_level = self._risk_level(open_warnings, pending_docs)

        bullets: list[str] = []
        if open_warnings:
            bullets.append(f"当前有 {open_warnings} 条未关闭预警，需要优先处理安全库存、短缺或冻结库存。")
        if pending_docs:
            bullets.append(f"当前有 {pending_docs} 张待处理单据，建议按到货、出库、生产领料顺序推进。")
        if not bullets:
            bullets.append("当前仓储运行平稳，未发现需要立即处理的库存风险。")

        return WmsIntelligenceSummaryOut(
            title="今日仓储风险摘要",
            summary=f"当前有 {open_warnings} 条未关闭预警，{pending_docs} 张待处理单据。",
            risk_level=risk_level,
            source=WmsIntelligenceSource.rule_fallback,
            bullets=bullets,
            actions=[
                WmsIntelligenceAction(label="查看库存预警", route="/module-wms/analytics/warning", permission="module_wms:warning:query"),
                WmsIntelligenceAction(label="查看库存流水", route="/module-wms/inventory/stock", permission="module_wms:stock:query"),
            ],
        )

    def warning_advice_from_warning(self, warning: Any) -> WmsWarningAdviceOut:
        warning_type = getattr(warning, "warning_type", "")
        current_qty = getattr(warning, "current_qty", None)
        threshold_qty = getattr(warning, "threshold_qty", None)
        if warning_type == "shortage":
            reason = f"当前可用库存为 {current_qty}，已形成短缺风险。"
            advice = "建议优先检查待入库、可调拨库存和未释放锁定库存；如无可用库存，应创建补货或采购任务。"
            risk_level = WmsRiskLevel.critical
        elif warning_type == "safety_stock":
            reason = f"当前可用库存 {current_qty} 低于安全库存 {threshold_qty}。"
            advice = "建议核对近期生产领料计划，并优先安排补货、调拨或释放可用批次。"
            risk_level = WmsRiskLevel.warning
        else:
            reason = "系统检测到库存风险，需要仓储人员复核。"
            advice = "建议查看库存流水、批次状态和关联单据后再处理。"
            risk_level = WmsRiskLevel.warning
        return WmsWarningAdviceOut(
            warning_id=warning.id,
            warning_type=warning_type,
            risk_level=risk_level,
            reason=reason,
            advice=advice,
            source=WmsIntelligenceSource.rule_fallback,
            actions=[
                WmsIntelligenceAction(label="查看库存", route="/module-wms/inventory/stock", permission="module_wms:stock:query"),
                WmsIntelligenceAction(label="查看预警", route="/module-wms/analytics/warning", permission="module_wms:warning:query"),
            ],
        )

    def score_outbound_candidates(self, candidates: list[Any], *, warehouse_id: int | None = None, location_id: int | None = None) -> list[WmsOutboundCandidateScore]:
        scored: list[WmsOutboundCandidateScore] = []
        for index, item in enumerate(candidates):
            available_qty = Decimal(str(getattr(item, "available_qty", "0") or "0"))
            frozen_qty = Decimal(str(getattr(item, "frozen_qty", "0") or "0"))
            pending_qty = Decimal(str(getattr(item, "pending_qty", "0") or "0"))
            defective_qty = Decimal(str(getattr(item, "defective_qty", "0") or "0"))
            score = 0
            reasons: list[str] = []
            if available_qty > 0:
                score += 40
                reasons.append("存在可用库存")
            fifo_score = max(30 - index * 2, 10)
            score += fifo_score
            reasons.append(f"按先进先出排序加 {fifo_score} 分")
            if warehouse_id and getattr(item, "warehouse_id", None) == warehouse_id:
                score += 15
                reasons.append("匹配指定仓库")
            if location_id and getattr(item, "location_id", None) == location_id:
                score += 10
                reasons.append("匹配指定库位")
            if frozen_qty == 0 and pending_qty >= 0 and defective_qty == 0:
                score += 5
                reasons.append("无冻结或不良库存风险")
            scored.append(
                WmsOutboundCandidateScore(
                    balance_id=getattr(item, "id"),
                    material_id=getattr(item, "material_id"),
                    warehouse_id=getattr(item, "warehouse_id"),
                    location_id=getattr(item, "location_id", None),
                    batch_no=getattr(item, "batch_no", None),
                    available_qty=str(available_qty),
                    score=score,
                    rule_reasons=reasons,
                )
            )
        return sorted(scored, key=lambda item: item.score, reverse=True)

    @staticmethod
    def outbound_summary(candidates: list[WmsOutboundCandidateScore]) -> str:
        if not candidates:
            return "当前未找到可用于出库的库存批次，请检查物料、仓库、库位或可用库存。"
        best = candidates[0]
        return f"共找到 {len(candidates)} 个可用批次，推荐优先使用批次 {best.batch_no or best.balance_id}，评分 {best.score}。"

    @staticmethod
    def _risk_level(open_warnings: int, pending_docs: int) -> WmsRiskLevel:
        if open_warnings >= 10:
            return WmsRiskLevel.critical
        if open_warnings or pending_docs:
            return WmsRiskLevel.warning
        return WmsRiskLevel.normal
