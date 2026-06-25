"""
安全底座回归测试。

这些测试覆盖认证、公开账号入口、token 轮换和 RBAC 的关键安全边界。
"""

from __future__ import annotations

import time

from fastapi.testclient import TestClient


def _unique(prefix: str) -> str:
    return f"{prefix[:12]}_{time.time_ns() % 1_000_000_000_000}"


def _login(test_client: TestClient, username: str, password: str) -> dict:
    resp = test_client.post(
        "/system/auth/login",
        data={"username": username, "password": password, "login_type": "PC端"},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


def _create_user(test_client: TestClient, auth_headers: dict[str, str], username: str, password: str, mobile: str | None = None) -> None:
    payload = {
        "username": username,
        "password": password,
        "name": username,
    }
    if mobile:
        payload["mobile"] = mobile
    resp = test_client.post("/system/user/create", headers=auth_headers, json=payload)
    assert resp.status_code == 200, resp.text


def test_public_user_register_requires_authentication(test_client: TestClient) -> None:
    resp = test_client.post(
        "/system/user/register",
        json={"username": _unique("public_reg"), "password": "pass123", "name": "public"},
    )

    assert resp.status_code == 401


def test_current_user_info_requires_authentication(test_client: TestClient) -> None:
    resp = test_client.get("/system/user/current/info")

    assert resp.status_code == 401
    body = resp.json()
    assert body["success"] is False
    assert body["code"] == 10401


def test_current_user_info_rejects_invalid_token(test_client: TestClient) -> None:
    resp = test_client.get(
        "/system/user/current/info",
        headers={"Authorization": "Bearer invalid.token.value"},
    )

    assert resp.status_code == 401
    body = resp.json()
    assert body["success"] is False
    assert body["code"] == 10401


def test_forget_password_requires_matching_mobile(test_client: TestClient, auth_headers: dict[str, str]) -> None:
    username = _unique("forgot")
    _create_user(test_client, auth_headers, username=username, password="oldpass123", mobile="13800000000")

    resp = test_client.post(
        "/system/user/password/forget",
        json={"username": username, "new_password": "newpass123"},
    )

    assert resp.status_code in (400, 422)


def test_non_superuser_cannot_create_auto_login_token(test_client: TestClient, auth_headers: dict[str, str]) -> None:
    username = _unique("normal")
    password = "normal123"
    _create_user(test_client, auth_headers, username=username, password=password)
    token = _login(test_client, username=username, password=password)["access_token"]

    resp = test_client.post(
        "/system/auth/auto-login/token?user_id=1",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 403


def test_non_superuser_can_read_own_current_info(test_client: TestClient, auth_headers: dict[str, str]) -> None:
    username = _unique("normal_info")
    password = "normal123"
    _create_user(test_client, auth_headers, username=username, password=password)
    token = _login(test_client, username=username, password=password)["access_token"]

    resp = test_client.get(
        "/system/user/current/info",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["username"] == username


def test_non_superuser_without_permission_cannot_query_users(test_client: TestClient, auth_headers: dict[str, str]) -> None:
    username = _unique("normal_no_perm")
    password = "normal123"
    _create_user(test_client, auth_headers, username=username, password=password)
    token = _login(test_client, username=username, password=password)["access_token"]

    resp = test_client.get(
        "/system/user/list",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 403
    body = resp.json()
    assert body["success"] is False
    assert body["code"] == 10403


def test_superuser_can_query_users(test_client: TestClient) -> None:
    token = _login(test_client, username="admin", password="admin123")["access_token"]

    resp = test_client.get(
        "/system/user/list",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["success"] is True
    assert "items" in body["data"]
    assert "total" in body["data"]


def test_wildcard_permission_does_not_allow_non_superuser(test_client: TestClient, auth_headers: dict[str, str]) -> None:
    username = _unique("normal_wildcard")
    password = "normal123"
    _create_user(test_client, auth_headers, username=username, password=password)
    token = _login(test_client, username=username, password=password)["access_token"]

    resp = test_client.get(
        "/platform/invoice/list",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 403


def test_old_access_token_is_rejected_after_refresh(test_client: TestClient) -> None:
    login_data = _login(test_client, username="admin", password="admin123")
    old_access = login_data["access_token"]
    refresh_token = login_data["refresh_token"]

    refresh_resp = test_client.post(
        "/system/auth/token/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_resp.status_code == 200, refresh_resp.text

    old_access_resp = test_client.get(
        "/system/user/current/info",
        headers={"Authorization": f"Bearer {old_access}"},
    )

    assert old_access_resp.status_code == 401


def test_old_refresh_token_is_rejected_after_rotation(test_client: TestClient) -> None:
    login_data = _login(test_client, username="admin", password="admin123")
    old_refresh = login_data["refresh_token"]

    first_refresh = test_client.post(
        "/system/auth/token/refresh",
        json={"refresh_token": old_refresh},
    )
    assert first_refresh.status_code == 200, first_refresh.text

    second_refresh = test_client.post(
        "/system/auth/token/refresh",
        json={"refresh_token": old_refresh},
    )

    assert second_refresh.status_code == 401
