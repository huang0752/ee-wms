from decimal import Decimal

from fastapi.testclient import TestClient


def _create_master(test_client: TestClient, auth_headers: dict[str, str], resource: str, code: str, payload: dict | None = None) -> dict:
    body = {"code": code, "name": code, "status": 0}
    body.update(payload or {})
    resp = test_client.post(f"/wms/master/{resource}/create", json=body, headers=auth_headers)
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


def _scope(test_client: TestClient, auth_headers: dict[str, str], suffix: str) -> dict:
    wh1 = _create_master(test_client, auth_headers, "warehouse", f"WH_A_{suffix}", {"type": "main"})
    wh2 = _create_master(test_client, auth_headers, "warehouse", f"WH_B_{suffix}", {"type": "main"})
    loc1 = _create_master(test_client, auth_headers, "location", f"LOC_A_{suffix}", {"warehouse_id": wh1["id"]})
    loc2 = _create_master(test_client, auth_headers, "location", f"LOC_B_{suffix}", {"warehouse_id": wh2["id"]})
    mat = _create_master(test_client, auth_headers, "material", f"MAT_CK_{suffix}", {"unit": "pcs", "safety_stock": "10"})
    return {"wh1": wh1, "wh2": wh2, "loc1": loc1, "loc2": loc2, "mat": mat}


def _put_available(test_client: TestClient, auth_headers: dict[str, str], scope: dict, qty: str, batch_no: str = "BATCH-CK-001") -> None:
    payload = {
        "material_id": scope["mat"]["id"], "warehouse_id": scope["wh1"]["id"], "location_id": scope["loc1"]["id"],
        "batch_no": batch_no, "quantity": qty, "document_type": "seed", "document_no": f"SEED-{batch_no}",
    }
    assert test_client.post("/wms/stock/receive-pending", json=payload, headers=auth_headers).status_code == 200
    assert test_client.post("/wms/stock/approve-to-available", json=payload, headers=auth_headers).status_code == 200


def _balance(test_client: TestClient, auth_headers: dict[str, str], material_id: int, batch_no: str) -> list[dict]:
    resp = test_client.get("/wms/stock/balance/list", params={"material_id": material_id, "batch_no": batch_no, "page_size": 20}, headers=auth_headers)
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]["items"]


def test_transfer_writes_out_and_in_flows(test_client: TestClient, auth_headers: dict[str, str]) -> None:
    scope = _scope(test_client, auth_headers, "001")
    _put_available(test_client, auth_headers, scope, "8", "BATCH-TRF-001")
    create_resp = test_client.post("/wms/transfer/create", json={
        "order_no": "TRF-TEST-001", "from_warehouse_id": scope["wh1"]["id"], "to_warehouse_id": scope["wh2"]["id"],
        "lines": [{"material_id": scope["mat"]["id"], "from_location_id": scope["loc1"]["id"], "to_location_id": scope["loc2"]["id"], "batch_no": "BATCH-TRF-001", "quantity": "3"}],
    }, headers=auth_headers)
    assert create_resp.status_code == 200, create_resp.text
    order = create_resp.json()["data"]
    confirm_resp = test_client.post(f"/wms/transfer/confirm/{order['id']}", headers=auth_headers)
    assert confirm_resp.status_code == 200, confirm_resp.text
    assert confirm_resp.json()["data"]["status"] == "confirmed"
    flow_resp = test_client.get("/wms/stock/flow/list", params={"batch_no": "BATCH-TRF-001", "page_size": 20}, headers=auth_headers)
    flow_types = [item["flow_type"] for item in flow_resp.json()["data"]["items"]]
    assert "transfer_out" in flow_types
    assert "transfer_in" in flow_types


def test_stock_check_draft_then_audit_adjusts_balance(test_client: TestClient, auth_headers: dict[str, str]) -> None:
    scope = _scope(test_client, auth_headers, "002")
    _put_available(test_client, auth_headers, scope, "5", "BATCH-CHK-001")
    create_resp = test_client.post("/wms/check/create", json={
        "order_no": "CHK-TEST-001", "warehouse_id": scope["wh1"]["id"],
        "lines": [{"material_id": scope["mat"]["id"], "location_id": scope["loc1"]["id"], "batch_no": "BATCH-CHK-001", "system_qty": "5", "counted_qty": "7"}],
    }, headers=auth_headers)
    assert create_resp.status_code == 200, create_resp.text
    assert Decimal(_balance(test_client, auth_headers, scope["mat"]["id"], "BATCH-CHK-001")[0]["available_qty"]) == Decimal("5.0000")
    audit_resp = test_client.post(f"/wms/check/audit/{create_resp.json()['data']['id']}", headers=auth_headers)
    assert audit_resp.status_code == 200, audit_resp.text
    assert Decimal(_balance(test_client, auth_headers, scope["mat"]["id"], "BATCH-CHK-001")[0]["available_qty"]) == Decimal("7.0000")
    flow_resp = test_client.get("/wms/stock/flow/list", params={"batch_no": "BATCH-CHK-001", "flow_type": "adjust_after_check"}, headers=auth_headers)
    assert flow_resp.json()["data"]["total"] >= 1


def test_warning_scan_and_close(test_client: TestClient, auth_headers: dict[str, str]) -> None:
    scope = _scope(test_client, auth_headers, "003")
    scan_resp = test_client.post("/wms/warning/scan", json={"warehouse_id": scope["wh1"]["id"]}, headers=auth_headers)
    assert scan_resp.status_code == 200, scan_resp.text
    warnings = scan_resp.json()["data"]
    assert any(item["warning_type"] in {"safety_stock", "shortage"} for item in warnings)
    close_resp = test_client.post(f"/wms/warning/close/{warnings[0]['id']}", headers=auth_headers)
    assert close_resp.status_code == 200, close_resp.text
    assert close_resp.json()["data"]["status"] == "closed"
