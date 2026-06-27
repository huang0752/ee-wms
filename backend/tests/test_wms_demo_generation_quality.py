from app.api.v1.module_wms.demo.codecs import compact_parent_code, safe_category_code
from app.api.v1.module_wms.demo.fact_plan import WmsDemoFactPlanner
from app.api.v1.module_wms.demo.generator import WmsDemoGenerator
from app.api.v1.module_wms.demo.schema import WmsDemoInitSchema


def test_safe_category_code_uses_ascii_mapping() -> None:
    assert safe_category_code("变压器") == "TR"
    assert safe_category_code("开关柜") == "SWG"
    assert safe_category_code("线缆") == "CBL"
    assert safe_category_code("未知中文") == "GEN"


def test_compact_parent_code_keeps_location_code_short() -> None:
    code = compact_parent_code("EE-WH-0001-67F8F5-ZN0001-67F8F5")
    assert code == "EEWH0001ZN0001"
    assert len(code) <= 18


def test_fact_planner_splits_business_documents() -> None:
    plan = WmsDemoFactPlanner().build(
        WmsDemoInitSchema(
            scale_mode="standard",
            quantity_targets={
                "warehouse_count": 3,
                "location_count": 100,
                "material_count": 80,
                "stock_flow_count": 300,
                "business_doc_count": 160,
                "warning_count": 8,
            },
        )
    )

    assert plan.counts["arrival_order"] == 40
    assert plan.counts["outbound_order"] == 32
    assert plan.counts["issue_order"] == 32
    assert plan.counts["transfer_order"] >= 8
    assert plan.counts["stock_check_order"] >= 8
    assert plan.counts["stock_flow"] >= 300


def test_demo_clean_deletes_references_before_stock_and_master_rows() -> None:
    labels = [label for label, _ in WmsDemoGenerator._delete_order()]

    assert labels.index("outbound_line") < labels.index("stock_lock")
    assert labels.index("issue_line") < labels.index("stock_lock")
    assert labels.index("stock_flow") < labels.index("stock_lock")
    assert labels.index("stock_flow") < labels.index("stock_balance")
    assert labels.index("stock_lock") < labels.index("material")
    assert labels.index("stock_balance") < labels.index("warehouse")
