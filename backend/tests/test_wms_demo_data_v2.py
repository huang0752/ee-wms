from fastapi.testclient import TestClient
from sqlalchemy import func, select


def _standard_payload() -> dict:
    return {
        "profile": {
            "company_name": "电工装备测试租户",
            "industry": "电工装备",
            "company_size": "medium",
            "scenario": "starter",
        },
        "numbering": {
            "tenant_short_code": "EET",
            "numbering_style": "tenant",
            "date_format": "yyyyMMdd",
            "sequence_digits": 4,
            "include_demo_suffix": True,
            "prefixes": {},
        },
        "custom_products": [
            {
                "name": "油浸式变压器",
                "category": "变压器",
                "voltage_level": "10kV",
                "spec_examples": ["S13-M", "S20-M"],
                "storage_traits": ["重型库位", "防潮"],
                "weight": 5,
            }
        ],
        "warehouse_scenarios": ["质检入库", "销售出库", "调拨盘点"],
        "scale_mode": "standard",
        "quantity_targets": {
            "warehouse_count": 3,
            "location_count": 100,
            "material_count": 80,
            "stock_flow_count": 300,
            "business_doc_count": 160,
            "warning_count": 8,
        },
        "time_range_days": 90,
        "naming_style": "industrial",
        "quality_requirements": "覆盖电工装备关键物资，编号体现租户短码。",
        "generation_instructions": "规格、批次、供应商保持丰富。",
        "use_ai_enrichment": True,
        "product_directions": [],
    }


async def test_wms_demo_preview_uses_sample_pool_without_persisting(test_client: TestClient, auth_headers: dict[str, str]) -> None:
    from app.api.v1.module_wms.master.model import WmsMaterialModel
    from app.core.database import async_db_session

    async with async_db_session() as db:
        before = (await db.execute(select(func.count()).select_from(WmsMaterialModel))).scalar_one()

    response = test_client.post("/wms/demo/preview", headers=auth_headers, json=_standard_payload())
    assert response.status_code == 200, response.text
    payload = response.json()["data"]
    assert payload["sample_pool_name"]
    assert payload["estimated_counts"]["material"] >= 80
    assert payload["estimated_counts"]["stock_flow"] >= 300
    assert payload["preview_names"]["material_codes"][0].startswith("EET-")

    async with async_db_session() as db:
        after = (await db.execute(select(func.count()).select_from(WmsMaterialModel))).scalar_one()
    assert after == before


async def test_wms_demo_sample_pool_and_standard_generation(test_client: TestClient, auth_headers: dict[str, str]) -> None:
    pool_resp = test_client.get("/wms/demo/sample-pools", headers=auth_headers)
    assert pool_resp.status_code == 200, pool_resp.text
    pools = pool_resp.json()["data"]
    assert pools
    assert pools[0]["items"]

    payload = _standard_payload()
    payload["sample_pool_id"] = pools[0]["id"]
    init_resp = test_client.post("/wms/demo/init", headers=auth_headers, json=payload)
    assert init_resp.status_code == 200, init_resp.text
    batch = init_resp.json()["data"]
    assert batch["counts"]["material"] >= 80
    assert batch["counts"]["stock_flow"] >= 300
    assert batch["counts"]["transfer_order"] >= 1
    assert batch["counts"]["stock_check_order"] >= 1
    assert batch["quality_report"]["passed"] is True

    clean_resp = test_client.delete(f"/wms/demo/clean/{batch['demo_batch_id']}", headers=auth_headers)
    assert clean_resp.status_code == 200, clean_resp.text
