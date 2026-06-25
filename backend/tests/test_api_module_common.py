"""
模块接口测试 —— module_common（公共模块）
每个接口一个测试用例，验证路由存在且返回码正确。
"""

from conftest import assert_route
from fastapi.testclient import TestClient

PNG_1X1 = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\xf8\xff"
    b"\xff?\x00\x05\xfe\x02\xfeA\xe2!\xbc\x00\x00\x00\x00IEND\xaeB`\x82"
)


class TestHealth:
    """健康检查接口。"""

    def test_health_check(self, test_client: TestClient) -> None:
        assert_route(test_client, "GET", "/common/health", expected_status=200)

    def test_health_ready(self, test_client: TestClient) -> None:
        assert_route(test_client, "GET", "/common/health/ready", expected_status=200)

    def test_health_live(self, test_client: TestClient) -> None:
        assert_route(test_client, "GET", "/common/health/live", expected_status=200)


class TestFile:
    """文件管理接口。"""

    def test_upload_file(self, test_client: TestClient) -> None:
        assert_route(test_client, "POST", "/common/file/upload")

    def test_upload_tenant_brand_file_uses_tenant_brand_directory(
        self, test_client: TestClient, auth_headers: dict
    ) -> None:
        response = test_client.post(
            "/common/file/upload?upload_type=tenant_logo",
            headers=auth_headers,
            files={"file": ("logo.png", PNG_1X1, "image/png")},
        )

        assert response.status_code == 200, response.text
        payload = response.json()["data"]
        assert "/tenant/brand/logo/" in payload["file_path"].replace("\\", "/")
        assert "/tenant/brand/logo/" in payload["file_url"].replace("\\", "/")

    def test_download_file(self, test_client: TestClient) -> None:
        assert_route(
            test_client,
            "POST",
            "/common/file/download",
            json={"file_path": "test.txt", "delete": False},
        )
