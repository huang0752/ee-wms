from fastapi.testclient import TestClient
from sqlalchemy import func, select


async def test_wms_demo_init_creates_task_and_demo_rows(test_client: TestClient, auth_headers: dict[str, str]) -> None:
    response = test_client.post(
        "/wms/demo/init",
        headers=auth_headers,
        json={
            "profile": {
                "company_name": "测试智能制造有限公司",
                "industry": "智能制造",
                "warehouse_count": 1,
                "material_count": 3,
                "scenario": "starter",
            },
            "batch_policy": "clean_rebuild",
        },
    )
    assert response.status_code == 200, response.text
    payload = response.json()["data"]
    demo_batch_id = payload["demo_batch_id"]
    assert payload["module"] == "wms"
    assert payload["task_id"] > 0
    assert payload["counts"]["warehouse"] == 1
    assert payload["counts"]["arrival_order"] == 1
    assert payload["counts"]["warning"] == 1

    from app.api.v1.module_wms.master.model import WmsMaterialModel, WmsWarehouseModel
    from app.api.v1.module_wms.stock.model import WmsStockBalanceModel, WmsStockFlowModel
    from app.core.database import async_db_session
    from app.plugin.module_task.business.task.model import BusinessTaskModel

    async with async_db_session() as db:
        tasks = (
            await db.execute(
                select(BusinessTaskModel).where(
                    BusinessTaskModel.module == "wms",
                    BusinessTaskModel.biz_type == "demo_batch_init",
                    BusinessTaskModel.demo_batch_id == demo_batch_id,
                )
            )
        ).scalars().all()
        assert len(tasks) == 1
        assert tasks[0].status == "success"
        assert tasks[0].is_demo is True

        for model in [WmsWarehouseModel, WmsMaterialModel, WmsStockBalanceModel, WmsStockFlowModel]:
            rows = (await db.execute(select(model).where(model.demo_batch_id == demo_batch_id))).scalars().all()
            assert rows
            assert all(row.is_demo is True for row in rows)
            assert all(row.tenant_id == tasks[0].tenant_id for row in rows)

        for model in [WmsWarehouseModel, WmsMaterialModel]:
            rows = (await db.execute(select(model).where(model.demo_batch_id == demo_batch_id))).scalars().all()
            assert all("-" not in row.code for row in rows)

    list_resp = test_client.get("/wms/master/warehouse/list?is_demo=true", headers=auth_headers)
    assert list_resp.status_code == 200, list_resp.text
    assert list_resp.json()["code"] == 0


async def test_wms_demo_clean_only_deletes_demo_rows_for_batch(test_client: TestClient, auth_headers: dict[str, str]) -> None:
    init_resp = test_client.post(
        "/wms/demo/init",
        headers=auth_headers,
        json={"profile": {"company_name": "清理测试有限公司"}, "batch_policy": "append"},
    )
    assert init_resp.status_code == 200, init_resp.text
    demo_batch_id = init_resp.json()["data"]["demo_batch_id"]

    from app.api.v1.module_wms.master.model import WmsWarehouseModel
    from app.core.database import async_db_session
    from app.plugin.module_task.business.task.model import BusinessTaskModel

    async with async_db_session() as db:
        task = (
            await db.execute(select(BusinessTaskModel).where(BusinessTaskModel.demo_batch_id == demo_batch_id))
        ).scalars().one()
        formal = WmsWarehouseModel(
            tenant_id=task.tenant_id,
            created_id=task.created_id,
            updated_id=task.updated_id,
            code=f"FORMAL_{demo_batch_id[-6:]}",
            name="正式仓库",
            status=0,
            is_demo=False,
            demo_batch_id=demo_batch_id,
        )
        db.add(formal)
        await db.commit()

    clean_resp = test_client.delete(f"/wms/demo/clean/{demo_batch_id}", headers=auth_headers)
    assert clean_resp.status_code == 200, clean_resp.text
    counts = clean_resp.json()["data"]["counts"]
    assert counts["warehouse"] == 1
    assert counts["business_task"] == 1

    async with async_db_session() as db:
        demo_warehouses = (
            await db.execute(
                select(func.count())
                .select_from(WmsWarehouseModel)
                .where(WmsWarehouseModel.demo_batch_id == demo_batch_id, WmsWarehouseModel.is_demo.is_(True))
            )
        ).scalar_one()
        formal_warehouses = (
            await db.execute(
                select(func.count())
                .select_from(WmsWarehouseModel)
                .where(WmsWarehouseModel.demo_batch_id == demo_batch_id, WmsWarehouseModel.is_demo.is_(False))
            )
        ).scalar_one()
        assert demo_warehouses == 0
        assert formal_warehouses == 1
