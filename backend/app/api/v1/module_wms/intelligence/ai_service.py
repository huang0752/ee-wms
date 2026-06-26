from typing import Any

from app.core.base_schema import AuthSchema
from app.core.logger import logger
from app.plugin.module_ai.chat.service import AiRuntimeService

from .rule_service import WmsIntelligenceRuleService
from .schema import WmsIntelligenceDraft, WmsIntelligenceSource, WmsIntelligenceSummaryOut, WmsWarningAdviceOut


class WmsIntelligenceAIService:
    def __init__(self, auth: AuthSchema, runtime: AiRuntimeService | None = None) -> None:
        self.auth = auth
        self.runtime = runtime or AiRuntimeService(auth)
        self.rule_service = WmsIntelligenceRuleService(auth)

    async def dashboard_summary(self) -> WmsIntelligenceSummaryOut:
        fallback = await self.rule_service.dashboard_summary()
        prompt = (
            "你是 WMS 智慧仓储系统的业务分析助手。请基于以下规则摘要生成结构化中文摘要，"
            "不要改变数量事实，不要编造不存在的库存数据。"
            f"标题：{fallback.title}\n"
            f"规则摘要：{fallback.summary}\n"
            f"要点：{'；'.join(fallback.bullets)}"
        )
        try:
            draft = await self.runtime.structured_generate(
                prompt,
                response_format=WmsIntelligenceDraft,
                source_module="module_wms",
                source_feature="dashboard_summary",
                prompt_key="wms.dashboard_summary.v1",
                business_id=f"tenant:{self.auth.tenant_id}",
                system_prompt="只返回符合结构化输出契约的中文仓储摘要，不得新增库存事实。",
            )
        except Exception as exc:
            logger.warning("WMS 智能摘要 AI 降级: {}", exc)
            return fallback
        return self._apply_draft(fallback, draft)

    async def warning_advice(self, warning: Any) -> WmsWarningAdviceOut:
        fallback = self.rule_service.warning_advice_from_warning(warning)
        prompt = (
            "你是 WMS 库存预警处理助手。请在不改变事实的前提下，把以下规则建议生成结构化中文建议。"
            f"预警类型：{fallback.warning_type}\n"
            f"原因：{fallback.reason}\n"
            f"规则建议：{fallback.advice}"
        )
        try:
            draft = await self.runtime.structured_generate(
                prompt,
                response_format=WmsIntelligenceDraft,
                source_module="module_wms",
                source_feature="warning_advice",
                prompt_key="wms.warning_advice.v1",
                business_id=f"warning:{fallback.warning_id}",
                system_prompt="只返回符合结构化输出契约的中文预警建议，不得新增库存事实。",
            )
        except Exception as exc:
            logger.warning("WMS 预警建议 AI 降级: {}", exc)
            return fallback
        summary = getattr(draft, "summary", "").strip()
        if not summary:
            return fallback
        return fallback.model_copy(update={"advice": summary, "source": WmsIntelligenceSource.ai})

    @staticmethod
    def _apply_draft(fallback: WmsIntelligenceSummaryOut, draft: Any) -> WmsIntelligenceSummaryOut:
        summary = getattr(draft, "summary", "").strip()
        bullets = getattr(draft, "bullets", None)
        if not summary:
            return fallback
        return fallback.model_copy(
            update={
                "summary": summary,
                "bullets": bullets or fallback.bullets,
                "source": WmsIntelligenceSource.ai,
            }
        )
