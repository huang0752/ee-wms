from decimal import Decimal

from fastapi.testclient import TestClient


def _create_master(test_client: TestClient, auth_headers: dict[str, str], resource: str, code: str, payload: dict | None = None) -> dict:
    body = {"code": code, "name": code, "status": 0}
    body.update(payload or {})
    resp = test_client.post(f"/wms/master/{resource}/create", json=body, headers=auth_headers)
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


def _scope(test_client: TestClient, auth_headers: dict[str, str], suffix: str) -> dict:
    warehouse = _create_master(test_client, auth_headers, "warehouse", f"WH_OUT_{suffix}", {"type": "main"})
    location = _create_master(test_client, auth_headers, "location", f"LOC_OUT_{suffix}", {"warehouse_id": warehouse["id"]})
    material = _create_master(test_client, auth_headers, "material", f"MAT_OUT_{suffix}", {"unit": "pcs", "batch_flag": True})
    customer = _create_master(test_client, auth_headers, "customer", f"CUS_OUT_{suffix}")
    return {"warehouse": warehouse, "location": location, "material": material, "customer": customer}


def _stock_payload(scope: dict, batch_no: str, quantity: str) -> dict:
    return {
        "material_id": scope["material"]["id"],
        "warehouse_id": scope["warehouse"]["id"],
        "location_id": scope["location"]["id"],
        "batch_no": batch_no,
        "quantity": quantity,
        "document_type": "seed",
        "document_no": f"SEED-{batch_no}",
    }


def _put_available_stock(test_client: TestClient, auth_headers: dict[str, str], scope: dict, batch_no: str, quantity: str) -> None:
    payload = _stock_payload(scope, batch_no, quantity)
    assert test_client.post("/wms/stock/receive-pending", json=payload, headers=auth_headers).status_code == 200
    assert test_client.post("/wms/stock/approve-to-available", json=payload, headers=auth_headers).status_code == 200


def test_outbound_fifo_reserve_pick_review_confirm_deducts_stock(test_client: TestClient, auth_headers: dict[str, str]) -> None:
    scope = _scope(test_client, auth_headers, "001")
    _put_available_stock(test_client, auth_headers, scope, "BATCH-OUT-A", "4")
    _put_available_stock(test_client, auth_headers, scope, "BATCH-OUT-B", "5")

    recommend_resp = test_client.post(
        "/wms/stock/recommend",
        json={
            "material_id": scope["material"]["id"],
            "warehouse_id": scope["warehouse"]["id"],
            "quantity": "6",
            "document_type": "outbound",
            "document_no": "OUT-FIFO-001",
        },
        headers=auth_headers,
    )
    assert recommend_resp.status_code == 200, recommend_resp.text
    assert [item["batch_no"] for item in recommend_resp.json()["data"]][:2] == ["BATCH-OUT-A", "BATCH-OUT-B"]

    create_resp = test_client.post(
        "/wms/outbound/create",
        json={
            "order_no": "OUT-TEST-001",
            "customer_id": scope["customer"]["id"],
            "warehouse_id": scope["warehouse"]["id"],
            "lines": [{"material_id": scope["material"]["id"], "requested_qty": "6"}],
        },
        headers=auth_headers,
    )
    assert create_resp.status_code == 200, create_resp.text
    order = create_resp.json()["data"]

    for action, expected_status in [
        ("reserve", "reserved"),
        ("pick", "picked"),
        ("review", "reviewed"),
        ("confirm", "confirmed"),
    ]:
        resp = test_client.post(f"/wms/outbound/{action}/{order['id']}", headers=auth_headers)
        assert resp.status_code == 200, resp.text
        assert resp.json()["data"]["status"] == expected_status

    line_resp = test_client.get(f"/wms/outbound/{order['id']}/lines", headers=auth_headers)
    assert line_resp.status_code == 200, line_resp.text
    lines = line_resp.json()["data"]
    assert {line["batch_no"] for line in lines} == {"BATCH-OUT-A", "BATCH-OUT-B"}
    assert sum(Decimal(line["shipped_qty"]) for line in lines) == Decimal("6.0000")

    balance_resp = test_client.get(
        "/wms/stock/balance/list",
        params={"material_id": scope["material"]["id"], "page_size": 20},
        headers=auth_headers,
    )
    assert balance_resp.status_code == 200, balance_resp.text
    balances = {item["batch_no"]: item for item in balance_resp.json()["data"]["items"]}
    assert Decimal(balances["BATCH-OUT-A"]["quantity"]) == Decimal("0.0000")
    assert Decimal(balances["BATCH-OUT-B"]["quantity"]) == Decimal("3.0000")


def test_outbound_cancel_releases_locks(test_client: TestClient, auth_headers: dict[str, str]) -> None:
    scope = _scope(test_client, auth_headers, "002")
    _put_available_stock(test_client, auth_headers, scope, "BATCH-CANCEL-001", "5")
    create_resp = test_client.post(
        "/wms/outbound/create",
        json={
            "order_no": "OUT-CANCEL-001",
            "warehouse_id": scope["warehouse"]["id"],
            "lines": [{"material_id": scope["material"]["id"], "requested_qty": "3"}],
        },
        headers=auth_headers,
    )
    order = create_resp.json()["data"]
    assert test_client.post(f"/wms/outbound/reserve/{order['id']}", headers=auth_headers).status_code == 200
    cancel_resp = test_client.post(f"/wms/outbound/cancel/{order['id']}", headers=auth_headers)
    assert cancel_resp.status_code == 200, cancel_resp.text
    assert cancel_resp.json()["data"]["status"] == "cancelled"

    balance_resp = test_client.get(
        "/wms/stock/balance/list",
        params={"material_id": scope["material"]["id"], "batch_no": "BATCH-CANCEL-001"},
        headers=auth_headers,
    )
    balance = balance_resp.json()["data"]["items"][0]
    assert Decimal(balance["available_qty"]) == Decimal("5.0000")
    assert Decimal(balance["locked_qty"]) == Decimal("0.0000")


def test_production_issue_reserve_and_confirm(test_client: TestClient, auth_headers: dict[str, str]) -> None:
    scope = _scope(test_client, auth_headers, "003")
    _put_available_stock(test_client, auth_headers, scope, "BATCH-ISSUE-001", "7")
    create_resp = test_client.post(
        "/wms/issue/create",
        json={
            "order_no": "ISS-TEST-001",
            "work_order_no": "MO-001",
            "warehouse_id": scope["warehouse"]["id"],
            "lines": [{"material_id": scope["material"]["id"], "requested_qty": "4"}],
        },
        headers=auth_headers,
    )
    assert create_resp.status_code == 200, create_resp.text
    order = create_resp.json()["data"]
    for action, expected_status in [
        ("reserve", "reserved"),
        ("pick", "picked"),
        ("review", "reviewed"),
        ("confirm", "confirmed"),
    ]:
        resp = test_client.post(f"/wms/issue/{action}/{order['id']}", headers=auth_headers)
        assert resp.status_code == 200, resp.text
        assert resp.json()["data"]["status"] == expected_status

    balance_resp = test_client.get(
        "/wms/stock/balance/list",
        params={"material_id": scope["material"]["id"], "batch_no": "BATCH-ISSUE-001"},
        headers=auth_headers,
    )
    balance = balance_resp.json()["data"]["items"][0]
    assert Decimal(balance["quantity"]) == Decimal("3.0000")
    assert Decimal(balance["available_qty"]) == Decimal("3.0000")
