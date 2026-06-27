import hashlib
import random
from dataclasses import dataclass

from app.core.base_schema import AuthSchema

from .codecs import safe_category_code
from .enrichment_schema import WmsDemoAiEnrichmentOut
from .fact_plan import WmsDemoFactPlan, WmsDemoFactPlanner
from .numbering import WmsDemoNumbering
from .pool_service import WmsDemoSamplePoolService
from .schema import WmsDemoInitSchema, WmsDemoPreviewOut, WmsDemoScenarioSummaryOut

MODE_TARGETS = {
    "quick": {"warehouse": 2, "location": 30, "material": 30, "stock_flow": 90, "business_doc": 40, "warning": 3},
    "standard": {"warehouse": 3, "location": 100, "material": 80, "stock_flow": 300, "business_doc": 120, "warning": 8},
    "rich": {"warehouse": 5, "location": 300, "material": 200, "stock_flow": 1000, "business_doc": 400, "warning": 20},
}


@dataclass
class DemoPlan:
    request: WmsDemoInitSchema
    sample_pool_name: str
    product_mix: list[dict]
    counts: dict[str, int]
    workflow_coverage: list[str]
    warnings: list[str]
    preview_names: dict[str, list[str]]
    fact_plan: WmsDemoFactPlan | None = None
    enrichment: WmsDemoAiEnrichmentOut | None = None
    legacy_mode: bool = False

    def preview(self) -> WmsDemoPreviewOut:
        scenario_summary = None
        if self.enrichment:
            scenario_summary = WmsDemoScenarioSummaryOut.model_validate(self.enrichment.scenario.model_dump())
        return WmsDemoPreviewOut(
            sample_pool_name=self.sample_pool_name,
            scale_mode=self.request.scale_mode,
            estimated_counts=self.counts,
            product_mix=self.product_mix,
            workflow_coverage=self.workflow_coverage,
            warnings=self.warnings,
            preview_names=self.preview_names,
            enrichment_source=self.enrichment.source if self.enrichment else "rule_fallback",
            scenario_summary=scenario_summary,
        )


class WmsDemoPlanner:
    def __init__(self, auth: AuthSchema) -> None:
        self.auth = auth

    async def build(self, data: WmsDemoInitSchema, demo_batch_id: str | None = None) -> DemoPlan:
        pool_service = WmsDemoSamplePoolService(self.auth)
        pool = await pool_service.get_pool(data.sample_pool_id)
        items = [item for item in pool.items if item.enabled]
        legacy_mode = self._legacy_mode(data)
        fact_plan = None if legacy_mode else WmsDemoFactPlanner().build(data)
        counts = self._counts(data, legacy_mode, fact_plan)
        rng = self._rng(data, demo_batch_id or "preview")
        product_mix = self._product_mix(data, items, counts["material"], rng)
        numbering = WmsDemoNumbering(self.auth, data.numbering, demo_batch_id)
        preview_names = self._preview_names(numbering, product_mix)
        workflows = ["warehouse", "location", "material", "arrival", "inspection", "inbound", "outbound", "issue", "warning", "trace"]
        if not legacy_mode and data.scale_mode != "quick":
            workflows.extend(["transfer", "stock_check", "stock_lock"])
        warnings = []
        if data.scale_mode == "quick":
            warnings.append("快速体验模式可能不会完整覆盖调拨和盘点流程。")
        if not data.custom_products:
            warnings.append("未填写自有产品，将主要使用样本池产品生成。")
        return DemoPlan(
            request=data,
            sample_pool_name=pool.name,
            product_mix=product_mix,
            counts=counts,
            workflow_coverage=workflows,
            warnings=warnings,
            preview_names=preview_names,
            fact_plan=fact_plan,
            legacy_mode=legacy_mode,
        )

    @staticmethod
    def _legacy_mode(data: WmsDemoInitSchema) -> bool:
        fields_set = set(getattr(data, "model_fields_set", set()))
        if fields_set and fields_set <= {"profile", "batch_policy", "use_ai_enrichment"}:
            return True
        targets = data.quantity_targets
        has_targets = any(
            value is not None
            for value in [
                targets.warehouse_count,
                targets.location_count,
                targets.material_count,
                targets.stock_flow_count,
                targets.business_doc_count,
                targets.warning_count,
            ]
        )
        return bool((data.profile.warehouse_count or data.profile.material_count) and not has_targets and not data.custom_products and not data.product_directions)

    @staticmethod
    def _counts(data: WmsDemoInitSchema, legacy_mode: bool, fact_plan: WmsDemoFactPlan | None = None) -> dict[str, int]:
        if legacy_mode:
            material = data.profile.material_count or 3
            warehouse = data.profile.warehouse_count or 1
            return {
                "warehouse": warehouse,
                "zone": warehouse,
                "location": warehouse,
                "material": material,
                "supplier": 1,
                "customer": 1,
                "barcode_rule": 1,
                "stock_flow": 3,
                "business_doc": 4,
                "warning": 1,
            }
        if fact_plan:
            return fact_plan.counts.copy()
        base = dict(MODE_TARGETS.get(data.scale_mode, MODE_TARGETS["standard"]))
        targets = data.quantity_targets
        if targets.warehouse_count is not None:
            base["warehouse"] = targets.warehouse_count
        if targets.location_count is not None:
            base["location"] = targets.location_count
        if targets.material_count is not None:
            base["material"] = targets.material_count
        if targets.stock_flow_count is not None:
            base["stock_flow"] = targets.stock_flow_count
        if targets.business_doc_count is not None:
            base["business_doc"] = targets.business_doc_count
        if targets.warning_count is not None:
            base["warning"] = targets.warning_count
        base["stock_flow"] = max(base["stock_flow"], base["material"] * 4)
        base["business_doc"] = max(base["business_doc"], base["material"] * 2)
        base["zone"] = max(base["warehouse"], min(base["location"], base["warehouse"] * 3))
        base["supplier"] = max(2, min(20, max(1, base["material"] // 12)))
        base["customer"] = max(1, min(12, max(1, base["material"] // 20)))
        base["barcode_rule"] = 4
        return base

    @staticmethod
    def _rng(data: WmsDemoInitSchema, demo_batch_id: str) -> random.Random:
        seed_text = f"{demo_batch_id}:{data.profile.company_name}:{data.scale_mode}:{len(data.custom_products)}"
        seed = int(hashlib.sha256(seed_text.encode()).hexdigest()[:12], 16)
        return random.Random(seed)

    @staticmethod
    def _product_mix(data: WmsDemoInitSchema, items: list, material_count: int, rng: random.Random) -> list[dict]:
        mix: list[dict] = []
        for product in data.custom_products:
            mix.append(
                {
                    "source": "custom",
                    "name": product.name,
                    "category": product.category or product.name,
                    "voltage_level": product.voltage_level,
                    "spec_patterns": product.spec_examples or [product.voltage_level or "通用规格"],
                    "material_patterns": [product.name],
                    "supplier_patterns": [product.supplier_requirement or f"{product.name}供应商"],
                    "storage_traits": product.storage_traits,
                    "quality_traits": [product.quality_requirements] if product.quality_requirements else [],
                    "weight": product.weight,
                }
            )
        enabled_items = [
            item for item in items
            if not data.product_directions
            or item.group_name in data.product_directions
            or item.item_name in data.product_directions
        ] or items
        for item in enabled_items:
            mix.append(
                {
                    "source": "sample_pool",
                    "name": item.item_name,
                    "category": item.group_name,
                    "voltage_level": None,
                    "spec_patterns": item.spec_patterns or [],
                    "material_patterns": item.material_patterns or [item.item_name],
                    "supplier_patterns": item.supplier_patterns or [f"{item.item_name}供应商"],
                    "storage_traits": item.storage_traits or [],
                    "quality_traits": item.quality_traits or [],
                    "weight": item.weight,
                }
            )
        if not mix:
            mix.append({"source": "fallback", "name": "通用电工装备", "category": "通用", "spec_patterns": ["GEN"], "material_patterns": ["通用物料"], "supplier_patterns": ["通用供应商"], "storage_traits": [], "quality_traits": [], "weight": 1})
        weighted = []
        for item in mix:
            weighted.extend([item] * int(item.get("weight") or 1))
        selected = []
        required_custom = [item for item in mix if item["source"] == "custom"]
        selected.extend(required_custom)
        while len(selected) < max(material_count, len(required_custom)):
            selected.append(rng.choice(weighted))
        return selected[:material_count]

    @staticmethod
    def _preview_names(numbering: WmsDemoNumbering, product_mix: list[dict]) -> dict[str, list[str]]:
        first = product_mix[0]
        material_code = numbering.code("material", category_short=safe_category_code(str(first.get("category") or "GEN")))
        return {
            "warehouse_codes": [numbering.code("warehouse")],
            "material_codes": [material_code],
            "batch_numbers": [numbering.batch_no(material_code)],
            "document_numbers": [numbering.document_no("arrival"), numbering.document_no("inbound")],
        }
