import json
from typing import Any

from app.core.base_schema import AuthSchema
from app.core.logger import logger
from app.plugin.module_ai.chat.service import AiRuntimeService

from .enrichment_schema import WmsDemoAiEnrichmentOut, WmsDemoAiMaterialName, WmsDemoAiScenarioSummary
from .schema import WmsDemoInitSchema


class WmsDemoEnrichmentService:
    def __init__(self, auth: AuthSchema, runtime: AiRuntimeService | None = None) -> None:
        self.auth = auth
        self.runtime = runtime or AiRuntimeService(auth)

    async def enrich(self, data: WmsDemoInitSchema, product_mix: list[dict[str, Any]]) -> WmsDemoAiEnrichmentOut:
        if not data.use_ai_enrichment:
            return self._fallback(data, product_mix)
        try:
            result = await self.runtime.structured_generate(
                self._prompt(data, product_mix),
                response_format=WmsDemoAiEnrichmentOut,
                source_module="module_wms",
                source_feature="demo_data_enrichment",
                prompt_key="wms.demo_data_enrichment.v1",
                business_id=f"tenant:{getattr(self.auth, 'tenant_id', None)}",
                system_prompt=(
                    "你是电工装备制造企业的仓储试用数据文案生成器。"
                    "只返回符合契约的 JSON。"
                    "不得生成编号、主键、外键、数量、状态流转或库存余额。"
                    "只能生成名称、摘要、原因和说明。"
                ),
            )
        except Exception as exc:
            logger.warning("WMS试用数据AI增强降级: {}", exc)
            return self._fallback(data, product_mix)
        return WmsDemoAiEnrichmentOut.model_validate(result)

    def _prompt(self, data: WmsDemoInitSchema, product_mix: list[dict[str, Any]]) -> str:
        payload = {
            "profile": data.profile.model_dump(mode="json"),
            "warehouse_scenarios": data.warehouse_scenarios,
            "product_directions": data.product_directions,
            "custom_products": [item.model_dump(mode="json") for item in data.custom_products],
            "quantity_targets": data.quantity_targets.model_dump(mode="json"),
            "quality_requirements": data.quality_requirements,
            "generation_instructions": data.generation_instructions,
            "naming_style": data.naming_style,
            "product_mix_sample": product_mix[:40],
        }
        return (
            "请基于以下租户画像和产品样本，生成 WMS 试用数据的业务名称和说明。"
            "名称要贴近电工装备仓储现场，避免营销腔，避免重复单一。"
            "不要输出任何编号、外键、数量、状态变化或库存账面事实。\n"
            f"{json.dumps(payload, ensure_ascii=False, default=str)}"
        )

    @staticmethod
    def _fallback(data: WmsDemoInitSchema, product_mix: list[dict[str, Any]]) -> WmsDemoAiEnrichmentOut:
        company = data.profile.company_name
        material_names = [
            WmsDemoAiMaterialName(
                key=f"material-{index + 1}",
                name=str((item.get("material_patterns") or [item.get("name") or "电工装备物料"])[0])[:128],
                spec_hint=str((item.get("spec_patterns") or ["通用规格"])[0])[:128],
                category=str(item.get("category") or "电工装备")[:64],
                storage_trait="、".join(item.get("storage_traits") or [])[:64] or None,
            )
            for index, item in enumerate(product_mix[:600])
        ]
        return WmsDemoAiEnrichmentOut(
            source="rule_fallback",
            scenario=WmsDemoAiScenarioSummary(
                title=f"{company} WMS试用场景",
                summary="覆盖来料检验、批次入库、销售出库、生产领料、调拨盘点和库存预警。",
                highlights=["批次追溯", "库存预警", "入出库闭环"],
            ),
            warehouses=[f"{company}主材仓", f"{company}成品仓", f"{company}不良品仓"],
            zones=["原材料检验区", "成品待发区", "不良品隔离区", "辅料周转区"],
            materials=material_names,
            suppliers=["华南电工装备供应商", "华中成套组件供应商", "长三角线缆供应商"],
            customers=["配网改造项目部", "新能源升压站项目部", "工业园区配电项目部"],
            warning_reasons=["安全库存低于近期领料需求", "批次库存周转慢于试用阈值"],
            check_reasons=["盘点复核发现库位实物少于系统账面", "线缆盘具复核存在尾料差异"],
        )
