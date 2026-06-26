from fastapi.testclient import TestClient
from sqlalchemy import select


def _create_master(test_client: TestClient, auth_headers: dict[str, str], resource: str, code: str, payload: dict | None = None) -> dict:
    body = {"code": code, "name": code, "status": 0}
    body.update(payload or {})
    response = test_client.post(f"/wms/master/{resource}/create", json=body, headers=auth_headers)
    assert response.status_code == 200, response.text
    return response.json()["data"]


def _seed_stock(test_client: TestClient, auth_headers: dict[str, str], suffix: str) -> dict:
    warehouse = _create_master(test_client, auth_headers, "warehouse", f"WH_INT_{suffix}")
    location = _create_master(test_client, auth_headers, "location", f"LOC_INT_{suffix}", {"warehouse_id": warehouse["id"]})
    material = _create_master(
        test_client,
        auth_headers,
        "material",
        f"MAT_INT_{suffix}",
        {"unit": "pcs", "safety_stock": "50"},
    )
    payload = {
        "material_id": material["id"],
        "warehouse_id": warehouse["id"],
        "location_id": location["id"],
        "batch_no": f"BATCH-INT-{suffix}",
        "quantity": "80",
        "document_type": "inbound",
        "document_no": f"INB-INT-{suffix}",
    }
    assert test_client.post("/wms/stock/receive-pending", json=payload, headers=auth_headers).status_code == 200
    assert test_client.post("/wms/stock/approve-to-available", json=payload, headers=auth_headers).status_code == 200
    return {"warehouse": warehouse, "location": location, "material": material, "batch_no": payload["batch_no"], "document_no": payload["document_no"]}


async def test_inbound_purchase_arrival_contract_is_idempotent(test_client: TestClient, auth_headers: dict[str, str]) -> None:
    warehouse = _create_master(test_client, auth_headers, "warehouse", "WH_INT_ARR")
    material = _create_master(test_client, auth_headers, "material", "MAT_INT_ARR", {"unit": "pcs"})
    body = {
        "source": "erp",
        "contract": "purchase_arrival",
        "idempotency_key": "ERP-ARRIVAL-001",
        "payload": {
            "external_no": "ERP-PO-001",
            "warehouse_code": warehouse["code"],
            "supplier_code": "SUP-ERP",
            "lines": [{"material_code": material["code"], "quantity": "12", "batch_no": "ERP-BATCH-001"}],
        },
    }
    first = test_client.post("/wms/integration/inbound", json=body, headers=auth_headers)
    assert first.status_code == 200, first.text
    first_data = first.json()["data"]
    assert first_data["reused"] is False
    assert first_data["request"]["result"]["order_no"] == "ERP-PO-001"

    second = test_client.post("/wms/integration/inbound", json=body, headers=auth_headers)
    assert second.status_code == 200, second.text
    second_data = second.json()["data"]
    assert second_data["reused"] is True
    assert second_data["request"]["id"] == first_data["request"]["id"]

    from app.api.v1.module_wms.arrival.model import WmsArrivalOrderModel
    from app.api.v1.module_wms.integration.model import WmsIntegrationRequestModel
    from app.core.database import async_db_session

    async with async_db_session() as db:
        arrivals = (await db.execute(select(WmsArrivalOrderModel).where(WmsArrivalOrderModel.external_id == "ERP-ARRIVAL-001"))).scalars().all()
        requests = (await db.execute(select(WmsIntegrationRequestModel).where(WmsIntegrationRequestModel.idempotency_key == "ERP-ARRIVAL-001"))).scalars().all()
    assert len(arrivals) == 1
    assert arrivals[0].external_source == "erp"
    assert arrivals[0].external_no == "ERP-PO-001"
    assert len(requests) == 1


def test_outbound_available_stock_and_trace_contracts(test_client: TestClient, auth_headers: dict[str, str]) -> None:
    scope = _seed_stock(test_client, auth_headers, "OUT")
    stock_resp = test_client.post(
        "/wms/integration/outbound",
        json={"contract": "available_stock", "material_code": scope["material"]["code"]},
        headers=auth_headers,
    )
    assert stock_resp.status_code == 200, stock_resp.text
    stock = stock_resp.json()["data"]
    assert stock["contract"] == "available_stock"
    assert any(item["batch_no"] == scope["batch_no"] and item["available_qty"] == "80.0000" for item in stock["items"])

    trace_resp = test_client.post(
        "/wms/integration/outbound",
        json={"contract": "trace_result", "batch_no": scope["batch_no"]},
        headers=auth_headers,
    )
    assert trace_resp.status_code == 200, trace_resp.text
    trace = trace_resp.json()["data"]
    assert trace["contract"] == "trace_result"
    assert trace["items"][0]["batch_no"] == scope["batch_no"]


def test_integration_request_list_filters_by_contract(test_client: TestClient, auth_headers: dict[str, str]) -> None:
    body = {
        "source": "mes",
        "contract": "mes_work_order",
        "idempotency_key": "MES-WO-001",
        "payload": {"external_no": "MO-001", "work_order_no": "MO-001", "lines": []},
    }
    response = test_client.post("/wms/integration/inbound", json=body, headers=auth_headers)
    assert response.status_code == 200, response.text

    list_resp = test_client.get("/wms/integration/request/list?contract=mes_work_order", headers=auth_headers)
    assert list_resp.status_code == 200, list_resp.text
    items = list_resp.json()["data"]["items"]
    assert any(item["idempotency_key"] == "MES-WO-001" for item in items)
