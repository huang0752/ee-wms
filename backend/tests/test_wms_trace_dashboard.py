from fastapi.testclient import TestClient


def _create_master(test_client: TestClient, auth_headers: dict[str, str], resource: str, code: str, payload: dict | None = None) -> dict:
    body = {"code": code, "name": code, "status": 0}
    body.update(payload or {})
    resp = test_client.post(f"/wms/master/{resource}/create", json=body, headers=auth_headers)
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


def _seed_flow(test_client: TestClient, auth_headers: dict[str, str], suffix: str) -> dict:
    warehouse = _create_master(test_client, auth_headers, "warehouse", f"WH_TRACE_{suffix}")
    location = _create_master(test_client, auth_headers, "location", f"LOC_TRACE_{suffix}", {"warehouse_id": warehouse["id"]})
    material = _create_master(test_client, auth_headers, "material", f"MAT_TRACE_{suffix}", {"unit": "pcs"})
    batch_no = f"BATCH-TRACE-{suffix}"
    document_no = f"INB-TRACE-{suffix}"
    payload = {
        "material_id": material["id"],
        "warehouse_id": warehouse["id"],
        "location_id": location["id"],
        "batch_no": batch_no,
        "quantity": "6",
        "document_type": "inbound",
        "document_no": document_no,
    }
    assert test_client.post("/wms/stock/receive-pending", json=payload, headers=auth_headers).status_code == 200
    assert test_client.post("/wms/stock/approve-to-available", json=payload, headers=auth_headers).status_code == 200
    return {"warehouse": warehouse, "location": location, "material": material, "batch_no": batch_no, "document_no": document_no}


def test_dashboard_uses_real_wms_data(test_client: TestClient, auth_headers: dict[str, str]) -> None:
    scope = _seed_flow(test_client, auth_headers, "DASH")
    summary_resp = test_client.get("/wms/dashboard/summary", headers=auth_headers)
    assert summary_resp.status_code == 200, summary_resp.text
    labels = {item["label"]: item["value"] for item in summary_resp.json()["data"]["metrics"]}
    assert labels["仓库"] >= 1
    assert labels["物料"] >= 1
    assert labels["库存批次"] >= 1

    structure_resp = test_client.get("/wms/dashboard/stock-structure", headers=auth_headers)
    assert structure_resp.status_code == 200, structure_resp.text
    assert float(structure_resp.json()["data"]["available_qty"]) >= 6

    flows_resp = test_client.get("/wms/dashboard/latest-flows", headers=auth_headers)
    assert flows_resp.status_code == 200, flows_resp.text
    assert any(item["batch_no"] == scope["batch_no"] for item in flows_resp.json()["data"])

    assert scope["material"]["id"] > 0


def test_trace_forward_and_backward_from_batch(test_client: TestClient, auth_headers: dict[str, str]) -> None:
    scope = _seed_flow(test_client, auth_headers, "FLOW")
    forward_resp = test_client.get(
        "/wms/trace/batch",
        params={"batch_no": scope["batch_no"], "direction": "forward"},
        headers=auth_headers,
    )
    assert forward_resp.status_code == 200, forward_resp.text
    forward = forward_resp.json()["data"]
    assert forward["batch_no"] == scope["batch_no"]
    assert [flow["flow_type"] for flow in forward["flows"]][:2] == ["receive_pending", "approve_to_available"]
    assert any(node["node_no"] == scope["document_no"] for node in forward["nodes"])

    backward_resp = test_client.get(
        "/wms/trace/batch",
        params={"batch_no": scope["batch_no"], "direction": "backward"},
        headers=auth_headers,
    )
    assert backward_resp.status_code == 200, backward_resp.text
    backward = backward_resp.json()["data"]
    assert [flow["flow_type"] for flow in backward["flows"]][:2] == ["approve_to_available", "receive_pending"]
