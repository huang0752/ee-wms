from dataclasses import dataclass, field
from math import ceil

from .schema import WmsDemoInitSchema

BASE_TARGETS = {
    "quick": {
        "warehouse": 2,
        "location": 30,
        "material": 30,
        "stock_flow": 90,
        "business_doc": 40,
        "warning": 3,
    },
    "standard": {
        "warehouse": 3,
        "location": 100,
        "material": 80,
        "stock_flow": 300,
        "business_doc": 160,
        "warning": 8,
    },
    "rich": {
        "warehouse": 5,
        "location": 300,
        "material": 200,
        "stock_flow": 1000,
        "business_doc": 400,
        "warning": 20,
    },
}


@dataclass(frozen=True)
class WmsDemoFactPlan:
    counts: dict[str, int]
    status_mix: dict[str, dict[str, int]] = field(default_factory=dict)
    workflow_coverage: list[str] = field(default_factory=list)


class WmsDemoFactPlanner:
    def build(self, data: WmsDemoInitSchema) -> WmsDemoFactPlan:
        counts = self._base_counts(data)
        business_doc = counts.pop("business_doc")
        counts.update(self._split_business_docs(business_doc, data.scale_mode))
        counts["zone"] = max(counts["warehouse"] * 2, min(counts["location"], counts["warehouse"] * 4))
        counts["supplier"] = max(4, min(30, ceil(counts["material"] / 10)))
        counts["customer"] = max(3, min(20, ceil(counts["material"] / 16)))
        counts["barcode_rule"] = 4
        counts["stock_batch"] = max(counts["material"], counts["arrival_order"])
        counts["stock_balance"] = counts["stock_batch"]
        counts["stock_flow"] = max(
            counts["stock_flow"],
            counts["arrival_order"] * 3 + counts["outbound_order"] * 2 + counts["issue_order"] * 2,
        )
        return WmsDemoFactPlan(
            counts=counts,
            status_mix=self._status_mix(counts),
            workflow_coverage=[
                "warehouse",
                "location",
                "material",
                "arrival",
                "inspection",
                "inbound",
                "outbound",
                "issue",
                "transfer",
                "stock_check",
                "warning",
                "trace",
            ],
        )

    @staticmethod
    def _base_counts(data: WmsDemoInitSchema) -> dict[str, int]:
        base = dict(BASE_TARGETS.get(data.scale_mode, BASE_TARGETS["standard"]))
        targets = data.quantity_targets
        for source, target in {
            "warehouse_count": "warehouse",
            "location_count": "location",
            "material_count": "material",
            "stock_flow_count": "stock_flow",
            "business_doc_count": "business_doc",
            "warning_count": "warning",
        }.items():
            value = getattr(targets, source)
            if value is not None:
                base[target] = value
        return base

    @staticmethod
    def _split_business_docs(total: int, scale_mode: str) -> dict[str, int]:
        if scale_mode == "quick":
            return {
                "arrival_order": max(8, total * 30 // 100),
                "inspection_task": max(8, total * 30 // 100),
                "inbound_order": max(8, total * 30 // 100),
                "outbound_order": max(6, total * 15 // 100),
                "issue_order": max(6, total * 15 // 100),
                "transfer_order": max(2, total * 5 // 100),
                "stock_check_order": max(2, total * 5 // 100),
            }
        return {
            "arrival_order": max(20, total * 25 // 100),
            "inspection_task": max(20, total * 25 // 100),
            "inbound_order": max(20, total * 25 // 100),
            "outbound_order": max(12, total * 20 // 100),
            "issue_order": max(12, total * 20 // 100),
            "transfer_order": max(4, total * 5 // 100),
            "stock_check_order": max(4, total * 5 // 100),
        }

    @staticmethod
    def _status_mix(counts: dict[str, int]) -> dict[str, dict[str, int]]:
        return {
            "arrival_order": {
                "closed": counts["arrival_order"] * 70 // 100,
                "pending_inspection": counts["arrival_order"] * 30 // 100,
            },
            "outbound_order": {
                "confirmed": counts["outbound_order"] * 45 // 100,
                "reserved": counts["outbound_order"] * 25 // 100,
                "pending_reserve": counts["outbound_order"] * 30 // 100,
            },
            "issue_order": {
                "confirmed": counts["issue_order"] * 45 // 100,
                "picked": counts["issue_order"] * 20 // 100,
                "pending_reserve": counts["issue_order"] * 35 // 100,
            },
            "warning": {
                "open": counts["warning"] * 70 // 100,
                "closed": counts["warning"] * 30 // 100,
            },
        }
