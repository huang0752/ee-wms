from .planner import DemoPlan


class WmsDemoQualityService:
    @staticmethod
    def preview_report(plan: DemoPlan) -> dict:
        checks = {
            "has_products": bool(plan.product_mix),
            "has_counts": bool(plan.counts),
            "numbering_preview": bool(plan.preview_names.get("document_numbers")),
            "workflow_coverage": bool(plan.workflow_coverage),
        }
        return {"passed": all(checks.values()), "checks": checks, "counts": plan.counts, "warnings": plan.warnings}

    @staticmethod
    def persisted_report(plan: DemoPlan, counts: dict[str, int]) -> dict:
        required = ["warehouse", "material", "stock_flow"]
        checks = {f"has_{key}": counts.get(key, 0) > 0 for key in required}
        if not plan.legacy_mode and plan.request.scale_mode in {"standard", "rich"}:
            checks["standard_material_count"] = counts.get("material", 0) >= min(80, plan.counts.get("material", 0))
            checks["standard_flow_count"] = counts.get("stock_flow", 0) >= min(300, plan.counts.get("stock_flow", 0))
            checks["has_transfer"] = counts.get("transfer_order", 0) > 0
            checks["has_stock_check"] = counts.get("stock_check_order", 0) > 0
        return {"passed": all(checks.values()), "checks": checks, "counts": counts, "warnings": plan.warnings}
