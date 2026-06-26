from fastapi.testclient import TestClient


def test_wms_master_warehouse_crud(test_client: TestClient, auth_headers: dict[str, str]) -> None:
    payload = {
        "code": "WH_MAIN",
        "name": "总装主仓",
        "type": "main",
        "manager": "仓库主管",
        "status": 0,
    }

    create_resp = test_client.post(
        "/wms/master/warehouse/create",
        json=payload,
        headers=auth_headers,
    )
    assert create_resp.status_code == 200, create_resp.text
    created = create_resp.json()["data"]
    assert created["code"] == payload["code"]
    assert created["tenant_id"] == 1

    duplicate_resp = test_client.post(
        "/wms/master/warehouse/create",
        json=payload,
        headers=auth_headers,
    )
    assert duplicate_resp.status_code == 400
    assert "编码已存在" in duplicate_resp.text

    list_resp = test_client.get(
        "/wms/master/warehouse/list",
        params={"code": "WH_MAIN"},
        headers=auth_headers,
    )
    assert list_resp.status_code == 200, list_resp.text
    page = list_resp.json()["data"]
    assert page["total"] >= 1
    assert any(item["code"] == "WH_MAIN" for item in page["items"])

    update_resp = test_client.put(
        f"/wms/master/warehouse/update/{created['id']}",
        json={**payload, "name": "总装主仓A区"},
        headers=auth_headers,
    )
    assert update_resp.status_code == 200, update_resp.text
    assert update_resp.json()["data"]["name"] == "总装主仓A区"


def test_wms_master_barcode_rule_requires_object_type(
    test_client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    resp = test_client.post(
        "/wms/master/barcode-rule/create",
        json={"code": "BC_MAT", "name": "物料条码"},
        headers=auth_headers,
    )
    assert resp.status_code == 400
    assert "对象类型" in resp.text
