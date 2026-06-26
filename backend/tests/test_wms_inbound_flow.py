from decimal import Decimal

from fastapi.testclient import TestClient


def _create_master(test_client: TestClient, auth_headers: dict[str, str], resource: str, code: str, payload: dict | None = None) -> dict:
    body = {"code": code, "name": code, "status": 0}
    body.update(payload or {})
    resp = test_client.post(f"/wms/master/{resource}/create", json=body, headers=auth_headers)
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


def _scope(test_client: TestClient, auth_headers: dict[str, str], suffix: str) -> dict:
    warehouse = _create_master(test_client, auth_headers, "warehouse", f"WH_IN_{suffix}", {"type": "main"})
    location = _create_master(
        test_client,
        auth_headers,
        "location",
        f"LOC_IN_{suffix}",
        {"warehouse_id": warehouse["id"], "capacity": "100", "category_constraints": ["electric"]},
    )
    material = _create_master(
        test_client,
        auth_headers,
        "material",
        f"MAT_IN_{suffix}",
        {"unit": "pcs", "category": "electric", "batch_flag": True},
    )
    supplier = _create_master(test_client, auth_headers, "supplier", f"SUP_IN_{suffix}")
    return {"warehouse": warehouse, "location": location, "material": material, "supplier": supplier}


def test_arrival_inspection_inbound_posts_available_and_defective_stock(
    test_client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    scope = _scope(test_client, auth_headers, "001")
    arrival_resp = test_client.post(
        "/wms/arrival/create",
        json={
            "order_no": "ARR-TEST-001",
            "supplier_id": scope["supplier"]["id"],
            "warehouse_id": scope["warehouse"]["id"],
            "external_source": "manual",
            "lines": [
                {
                    "material_id": scope["material"]["id"],
                    "planned_qty": "10",
                    "batch_no": "BATCH-IN-001",
                }
            ],
        },
        headers=auth_headers,
    )
    assert arrival_resp.status_code == 200, arrival_resp.text
    arrival = arrival_resp.json()["data"]
    assert arrival["status"] == "pending_receive"

    receive_resp = test_client.post(f"/wms/arrival/receive/{arrival['id']}", headers=auth_headers)
    assert receive_resp.status_code == 200, receive_resp.text
    task = receive_resp.json()["data"]
    assert task["status"] == "pending_inspection"

    inspection_lines_resp = test_client.get(f"/wms/inspection/{task['id']}/lines", headers=auth_headers)
    assert inspection_lines_resp.status_code == 200, inspection_lines_resp.text
    inspection_line = inspection_lines_resp.json()["data"][0]

    judge_resp = test_client.post(
        f"/wms/inspection/judge/{task['id']}",
        json={
            "lines": [
                {
                    "line_id": inspection_line["id"],
                    "accepted_qty": "8",
                    "rejected_qty": "2",
                }
            ]
        },
        headers=auth_headers,
    )
    assert judge_resp.status_code == 200, judge_resp.text
    judged = judge_resp.json()["data"]
    assert judged["status"] == "pending_inbound"
    assert judged["result"] == "partial"

    inbound_resp = test_client.post(
        f"/wms/inbound/create-from-inspection/{task['id']}",
        json={"location_id": scope["location"]["id"]},
        headers=auth_headers,
    )
    assert inbound_resp.status_code == 200, inbound_resp.text
    inbound = inbound_resp.json()["data"]
    assert inbound["status"] == "pending_confirm"

    inbound_lines_resp = test_client.get(f"/wms/inbound/{inbound['id']}/lines", headers=auth_headers)
    assert inbound_lines_resp.status_code == 200, inbound_lines_resp.text
    inbound_lines = inbound_lines_resp.json()["data"]
    assert {line["stock_status"] for line in inbound_lines} == {"available", "defective"}

    confirm_resp = test_client.post(f"/wms/inbound/confirm/{inbound['id']}", headers=auth_headers)
    assert confirm_resp.status_code == 200, confirm_resp.text
    confirmed = confirm_resp.json()["data"]
    assert confirmed["status"] == "confirmed"

    balance_resp = test_client.get(
        "/wms/stock/balance/list",
        params={"material_id": scope["material"]["id"], "batch_no": "BATCH-IN-001"},
        headers=auth_headers,
    )
    assert balance_resp.status_code == 200, balance_resp.text
    balance = balance_resp.json()["data"]["items"][0]
    assert Decimal(balance["quantity"]) == Decimal("10.0000")
    assert Decimal(balance["available_qty"]) == Decimal("8.0000")
    assert Decimal(balance["defective_qty"]) == Decimal("2.0000")
    assert Decimal(balance["pending_qty"]) == Decimal("0.0000")

    flow_resp = test_client.get(
        "/wms/stock/flow/list",
        params={"batch_no": "BATCH-IN-001", "page_size": 20},
        headers=auth_headers,
    )
    assert flow_resp.status_code == 200, flow_resp.text
    flow_types = [item["flow_type"] for item in flow_resp.json()["data"]["items"]]
    assert flow_types == ["receive_pending", "approve_to_available", "receive_pending", "reject_to_defective"]

    arrival_list_resp = test_client.get("/wms/arrival/list", params={"order_no": "ARR-TEST-001"}, headers=auth_headers)
    assert arrival_list_resp.status_code == 200, arrival_list_resp.text
    assert arrival_list_resp.json()["data"]["items"][0]["status"] == "closed"


def test_inbound_location_recommendation_respects_material_category(
    test_client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    scope = _scope(test_client, auth_headers, "002")
    resp = test_client.get(
        "/wms/inbound/recommend-location",
        params={"material_id": scope["material"]["id"], "warehouse_id": scope["warehouse"]["id"]},
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    rows = resp.json()["data"]
    assert any(row["id"] == scope["location"]["id"] for row in rows)
