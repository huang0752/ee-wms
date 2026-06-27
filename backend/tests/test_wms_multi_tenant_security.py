import asyncio

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.api.v1.module_platform.tenant.model import TenantUserModel
from app.api.v1.module_system.user.model import UserModel
from app.api.v1.module_system.user.schema import UserForgetPasswordSchema
from app.api.v1.module_system.user.service import UserService
from app.api.v1.module_wms.master.model import WmsLocationModel, WmsMaterialModel, WmsWarehouseModel
from app.core.base_schema import AuthSchema
from app.core.database import async_db_session
from app.core.exceptions import CustomException
from app.utils.hash_bcrpy_util import PwdUtil


async def _ensure_user(username: str, tenant_id: int, password: str = "safe123") -> UserModel:
    async with async_db_session() as db:
        existing = (
            await db.execute(
                select(UserModel).where(
                    UserModel.username == username,
                    UserModel.tenant_id == tenant_id,
                    UserModel.is_deleted.is_(False),
                )
            )
        ).scalars().first()
        if existing:
            return existing

        user = UserModel(
            tenant_id=tenant_id,
            username=username,
            password=PwdUtil.hash_password(password),
            name=username,
            status=0,
            is_superuser=False,
        )
        db.add(user)
        await db.flush()
        db.add(TenantUserModel(user_id=user.id, tenant_id=tenant_id, role="member", is_default=1))
        await db.commit()
        return user


async def _create_tenant2_wms_master() -> tuple[WmsWarehouseModel, WmsLocationModel, WmsMaterialModel]:
    async with async_db_session() as db:
        warehouse = WmsWarehouseModel(
            tenant_id=2,
            code="WH_CROSS_T2",
            name="租户2仓库",
            status=0,
            created_id=4,
            updated_id=4,
        )
        material = WmsMaterialModel(
            tenant_id=2,
            code="MAT_CROSS_T2",
            name="租户2物料",
            status=0,
            unit="pcs",
            created_id=4,
            updated_id=4,
        )
        db.add_all([warehouse, material])
        await db.flush()
        location = WmsLocationModel(
            tenant_id=2,
            code="LOC_CROSS_T2",
            name="租户2库位",
            warehouse_id=warehouse.id,
            status=0,
            created_id=4,
            updated_id=4,
        )
        db.add(location)
        await db.commit()
        return warehouse, location, material


def test_login_rejects_ambiguous_username_across_tenants(test_client: TestClient) -> None:
    username = "same_login_mt"
    asyncio.run(_ensure_user(username, tenant_id=1))
    asyncio.run(_ensure_user(username, tenant_id=2))

    resp = test_client.post(
        "/system/auth/login",
        data={"username": username, "password": "safe123"},
    )

    assert resp.status_code == 400
    assert "租户" in resp.text


def test_forget_password_rejects_ambiguous_username_across_tenants() -> None:
    username = "same_reset_mt"
    asyncio.run(_ensure_user(username, tenant_id=1))
    asyncio.run(_ensure_user(username, tenant_id=2))

    async def run_case() -> None:
        async with async_db_session() as db:
            auth = AuthSchema(db=db, check_data_scope=False)
            try:
                await UserService(auth).forget_password(
                    UserForgetPasswordSchema(username=username, mobile="13800138000", new_password="safe456")
                )
            except CustomException as exc:
                assert "租户" in exc.msg
                return
            raise AssertionError("forget_password should reject ambiguous usernames")

    asyncio.run(run_case())


def test_wms_stock_rejects_cross_tenant_master_ids(
    test_client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    warehouse, location, material = asyncio.run(_create_tenant2_wms_master())

    resp = test_client.post(
        "/wms/stock/receive-pending",
        json={
            "material_id": material.id,
            "warehouse_id": warehouse.id,
            "location_id": location.id,
            "batch_no": "BATCH-CROSS-TENANT",
            "quantity": "1",
            "document_type": "arrival",
            "document_no": "ARR-CROSS-TENANT",
        },
        headers=auth_headers,
    )

    assert resp.status_code == 400
    assert "不存在" in resp.text or "租户" in resp.text
