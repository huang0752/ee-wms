from collections.abc import Iterator
from decimal import Decimal

from fastapi.testclient import TestClient


def _suffix() -> Iterator[str]:
    counter = 0
    while True:
        counter += 1
        yield f"{counter:04d}"


_next_suffix = _suffix()


def _create_master(test_client: TestClient, auth_headers: dict[str, str], resource: str, code_prefix: str, payload: dict | None = None) -> dict:
    code = f"{code_prefix}_{next(_next_suffix)}"
    body = {"code": code, "name": code, "status": 0}
    body.update(payload or {})
    resp = test_client.post(f"/wms/master/{resource}/create", json=body, headers=auth_headers)
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


def _stock_scope(test_client: TestClient, auth_headers: dict[str, str]) -> dict:
    warehouse = _create_master(test_client, auth_headers, "warehouse", "WH_LEDGER", {"type": "main"})
    location = _create_master(
        test_client,
        auth_headers,
        "location",
        "LOC_LEDGER",
        {"warehouse_id": warehouse["id"], "mix_rule": "single_batch"},
    )
    material = _create_master(
        test_client,
        auth_headers,
        "material",
        "MAT_LEDGER",
        {"unit": "pcs", "batch_flag": True, "sn_flag": False},
    )
    return {"warehouse": warehouse, "location": location, "material": material}


def _receive_payload(scope: dict, batch_no: str, quantity: int | str) -> dict:
    return {
        "material_id": scope["material"]["id"],
        "warehouse_id": scope["warehouse"]["id"],
        "location_id": scope["location"]["id"],
        "batch_no": batch_no,
        "quantity": str(quantity),
        "document_type": "arrival",
        "document_no": f"ARR-{batch_no}",
    }


def test_stock_receive_and_approve_creates_balance_and_flow(test_client: TestClient, auth_headers: dict[str, str]) -> None:
    scope = _stock_scope(test_client, auth_headers)
    payload = _receive_payload(scope, "BATCH-RCV-001", 10)

    receive_resp = test_client.post("/wms/stock/receive-pending", json=payload, headers=auth_headers)
    assert receive_resp.status_code == 200, receive_resp.text
    received = receive_resp.json()["data"]
    assert Decimal(received["quantity"]) == Decimal("10.0000")
    assert Decimal(received["pending_qty"]) == Decimal("10.0000")
    assert Decimal(received["available_qty"]) == Decimal("0.0000")

    approve_resp = test_client.post("/wms/stock/approve-to-available", json=payload, headers=auth_headers)
    assert approve_resp.status_code == 200, approve_resp.text
    approved = approve_resp.json()["data"]
    assert Decimal(approved["quantity"]) == Decimal("10.0000")
    assert Decimal(approved["pending_qty"]) == Decimal("0.0000")
    assert Decimal(approved["available_qty"]) == Decimal("10.0000")

    flow_resp = test_client.get(
        "/wms/stock/flow/list",
        params={"batch_no": "BATCH-RCV-001", "page_size": 20},
        headers=auth_headers,
    )
    assert flow_resp.status_code == 200, flow_resp.text
    flows = flow_resp.json()["data"]["items"]
    assert [item["flow_type"] for item in flows] == ["receive_pending", "approve_to_available"]
    assert all(item["balance_id"] == approved["id"] for item in flows)


def test_stock_lock_prevents_double_allocation(test_client: TestClient, auth_headers: dict[str, str]) -> None:
    scope = _stock_scope(test_client, auth_headers)
    payload = _receive_payload(scope, "BATCH-LOCK-001", 5)
    assert test_client.post("/wms/stock/receive-pending", json=payload, headers=auth_headers).status_code == 200
    assert test_client.post("/wms/stock/approve-to-available", json=payload, headers=auth_headers).status_code == 200

    lock_resp = test_client.post(
        "/wms/stock/lock",
        json={
            "material_id": scope["material"]["id"],
            "warehouse_id": scope["warehouse"]["id"],
            "quantity": "3",
            "document_type": "outbound",
            "document_no": "OUT-LOCK-001",
        },
        headers=auth_headers,
    )
    assert lock_resp.status_code == 200, lock_resp.text
    locks = lock_resp.json()["data"]
    assert len(locks) == 1
    assert Decimal(locks[0]["quantity"]) == Decimal("3.0000")

    double_lock_resp = test_client.post(
        "/wms/stock/lock",
        json={
            "material_id": scope["material"]["id"],
            "warehouse_id": scope["warehouse"]["id"],
            "quantity": "3",
            "document_type": "outbound",
            "document_no": "OUT-LOCK-002",
        },
        headers=auth_headers,
    )
    assert double_lock_resp.status_code == 400
    assert "可用库存不足" in double_lock_resp.text


def test_recommend_excludes_pending_and_frozen_stock(test_client: TestClient, auth_headers: dict[str, str]) -> None:
    scope = _stock_scope(test_client, auth_headers)
    pending_payload = _receive_payload(scope, "BATCH-PENDING-001", 4)
    assert test_client.post("/wms/stock/receive-pending", json=pending_payload, headers=auth_headers).status_code == 200

    frozen_payload = _receive_payload(scope, "BATCH-FROZEN-001", 6)
    assert test_client.post("/wms/stock/receive-pending", json=frozen_payload, headers=auth_headers).status_code == 200
    assert test_client.post("/wms/stock/approve-to-available", json=frozen_payload, headers=auth_headers).status_code == 200
    assert test_client.post("/wms/stock/freeze", json={**frozen_payload, "quantity": "6"}, headers=auth_headers).status_code == 200

    available_payload = _receive_payload(scope, "BATCH-AVAILABLE-001", 8)
    assert test_client.post("/wms/stock/receive-pending", json=available_payload, headers=auth_headers).status_code == 200
    assert test_client.post("/wms/stock/approve-to-available", json=available_payload, headers=auth_headers).status_code == 200

    recommend_resp = test_client.post(
        "/wms/stock/recommend",
        json={
            "material_id": scope["material"]["id"],
            "warehouse_id": scope["warehouse"]["id"],
            "quantity": "5",
            "document_type": "outbound",
            "document_no": "OUT-REC-001",
        },
        headers=auth_headers,
    )
    assert recommend_resp.status_code == 200, recommend_resp.text
    batches = [item["batch_no"] for item in recommend_resp.json()["data"]]
    assert "BATCH-AVAILABLE-001" in batches
    assert "BATCH-PENDING-001" not in batches
    assert "BATCH-FROZEN-001" not in batches


def test_ship_locked_reduces_physical_balance(test_client: TestClient, auth_headers: dict[str, str]) -> None:
    scope = _stock_scope(test_client, auth_headers)
    payload = _receive_payload(scope, "BATCH-SHIP-001", 7)
    assert test_client.post("/wms/stock/receive-pending", json=payload, headers=auth_headers).status_code == 200
    assert test_client.post("/wms/stock/approve-to-available", json=payload, headers=auth_headers).status_code == 200
    lock_resp = test_client.post(
        "/wms/stock/lock",
        json={
            "material_id": scope["material"]["id"],
            "warehouse_id": scope["warehouse"]["id"],
            "quantity": "2",
            "document_type": "outbound",
            "document_no": "OUT-SHIP-001",
        },
        headers=auth_headers,
    )
    lock_id = lock_resp.json()["data"][0]["id"]
    ship_resp = test_client.post(f"/wms/stock/ship-lock/{lock_id}", headers=auth_headers)
    assert ship_resp.status_code == 200, ship_resp.text
    balance = ship_resp.json()["data"]
    assert Decimal(balance["quantity"]) == Decimal("5.0000")
    assert Decimal(balance["locked_qty"]) == Decimal("0.0000")
    assert Decimal(balance["available_qty"]) == Decimal("5.0000")
