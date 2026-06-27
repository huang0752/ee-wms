from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, func, or_, select

from app.config.setting import settings
from app.core.assembly import AssemblyConfig, load_assembly_from_file, reset_assembly_cache
from app.scripts.initialize import InitializeData


def test_load_assembly_from_toml(tmp_path: Path) -> None:
    config = tmp_path / "demo.toml"
    config.write_text(
        """
[assembly]
name = "demo"
title = "Demo"

[backend]
disabled_plugins = ["module_example"]

[frontend]
enabled_route_groups = ["home", "system"]
disabled_route_groups = ["pricing"]

[menu]
disabled_paths = ["/system/notice"]

[seed]
packs = ["minimal"]

[features]
flags = { ai_assistant = false }
""",
        encoding="utf-8",
    )

    assembly = load_assembly_from_file(config)

    assert assembly.name == "demo"
    assert not assembly.is_plugin_enabled("module_example")
    assert assembly.is_plugin_enabled("module_task")
    assert assembly.is_route_group_enabled("home")
    assert not assembly.is_route_group_enabled("pricing")
    assert assembly.disabled_menu_paths == ["/system/notice"]
    assert assembly.seed_packs == ["minimal"]
    assert assembly.frontend_summary()["featureFlags"]["aiAssistant"] is False


def test_disabled_plugin_is_not_registered_in_dynamic_router(tmp_path: Path) -> None:
    config = tmp_path / "minimal.toml"
    config.write_text(
        """
[assembly]
name = "minimal-test"

[backend]
disabled_plugins = ["module_example"]

[seed]
packs = ["legacy"]
""",
        encoding="utf-8",
    )

    old_file = settings.APP_ASSEMBLY_FILE
    old_name = settings.APP_ASSEMBLY
    settings.APP_ASSEMBLY_FILE = str(config)
    settings.APP_ASSEMBLY = "minimal-test"
    reset_assembly_cache()

    import app.core.discover as discover

    old_router = discover._dynamic_router_cache
    discover._dynamic_router_cache = None
    try:
        router = discover.get_dynamic_router()
        paths = {getattr(route, "path", "") for route in router.routes}
        assert not any(path.startswith("/example") for path in paths)
        assert any(path.startswith("/task") for path in paths)
    finally:
        discover._dynamic_router_cache = old_router
        settings.APP_ASSEMBLY_FILE = old_file
        settings.APP_ASSEMBLY = old_name
        reset_assembly_cache()


def test_public_config_info_returns_assembly(test_client: TestClient) -> None:
    response = test_client.get("/system/config/info")
    assert response.status_code == 200
    payload = response.json()["data"]["assembly"]
    assert payload["name"]
    assert isinstance(payload["enabledRouteGroups"], list)
    assert isinstance(payload["disabledRouteGroups"], list)
    assert isinstance(payload["featureFlags"], dict)


@pytest.mark.asyncio
async def test_wms_menu_visible_for_superadmin_after_wms_seed_initialization() -> None:
    old_file = settings.APP_ASSEMBLY_FILE
    old_name = settings.APP_ASSEMBLY
    settings.APP_ASSEMBLY_FILE = "app/assemblies/wms.toml"
    settings.APP_ASSEMBLY = "wms"
    reset_assembly_cache()

    try:
        initializer = InitializeData()
        menus = _flatten_menu_seed(await initializer._InitializeData__load_json("platform_menu"))
    finally:
        settings.APP_ASSEMBLY_FILE = old_file
        settings.APP_ASSEMBLY = old_name
        reset_assembly_cache()

    route_paths = {item.get("route_path") for item in menus}
    route_names = {item.get("route_name") for item in menus}

    assert "/module-wms" in route_paths
    assert "dashboard" in route_paths
    assert "demo" in route_paths
    assert "WmsDashboard" in route_names
    assert "WmsDemo" in route_names


def test_wms_assembly_cuts_demo_and_marketing_entries() -> None:
    assembly = load_assembly_from_file(Path("app/assemblies/wms.toml"))

    assert assembly.name == "wms"
    assert not assembly.is_plugin_enabled("module_example")
    assert assembly.is_plugin_enabled("module_ai")
    assert assembly.is_plugin_enabled("module_task")
    assert assembly.is_plugin_enabled("module_generator")
    assert not assembly.is_route_group_enabled("ai-chat")
    assert not assembly.is_route_group_enabled("dashboard")
    assert not assembly.is_route_group_enabled("module-task")
    assert not assembly.is_route_group_enabled("module-generator")
    assert not assembly.is_route_group_enabled("payment")
    assert not assembly.is_route_group_enabled("pricing")
    assert not assembly.is_route_group_enabled("article")
    assert not assembly.is_route_group_enabled("tutorial")
    assert not assembly.is_route_group_enabled("changelog")
    assert assembly.is_route_group_enabled("module-wms")
    assert "/platform/package" in assembly.disabled_menu_paths
    assert "/platform/order" in assembly.disabled_menu_paths
    assert "/platform/invoice" in assembly.disabled_menu_paths
    assert "/platform/plugin-market" in assembly.disabled_menu_paths
    assert "/system/notice" in assembly.disabled_menu_paths
    assert "/system/ticket" in assembly.disabled_menu_paths
    assert assembly.seed_packs == ["wms"]
    assert assembly.frontend_summary()["featureFlags"]["aiAssistant"] is False
    assert assembly.frontend_summary()["featureFlags"]["demoContent"] is False
    assert assembly.frontend_summary()["featureFlags"]["tenantWorkspaceOverview"] is False


def test_assembly_filters_runtime_menu_tree_by_plugin_and_route_group() -> None:
    assembly = AssemblyConfig(
        disabled_plugins=["module_example"],
        enabled_route_groups=["system", "module-task"],
        disabled_route_groups=["monitor", "swagger"],
    )
    menu_tree = [
        {"title": "系统管理", "route_path": "/system", "children": []},
        {"title": "监控管理", "route_path": "/monitor", "children": []},
        {"title": "接口管理", "route_path": "/swagger", "children": []},
        {
            "title": "平台管理",
            "route_path": "/platform",
            "children": [
                {"title": "租户管理", "route_path": "tenant"},
                {"title": "套餐管理", "route_path": "package"},
                {"title": "订单管理", "route_path": "order"},
                {"title": "发票管理", "route_path": "invoice"},
                {"title": "插件市场", "route_path": "plugin-market"},
            ],
        },
        {
            "title": "任务管理",
            "route_path": "/task",
            "children": [{"title": "业务任务", "route_path": "business/task"}],
        },
        {
            "title": "AI管理",
            "route_path": "/ai",
            "children": [{"title": "AI对话", "route_path": "chat"}],
        },
        {
            "title": "案例管理",
            "route_path": "/example",
            "children": [
                {
                    "title": "demo示例",
                    "route_path": "demo",
                    "component_path": "module_example/demo/index",
                    "permission": "module_example:demo:query",
                }
            ],
        },
    ]

    filtered = assembly.filter_menu_tree(menu_tree)

    titles = {item["title"] for item in filtered}
    assert titles == {"系统管理", "任务管理"}
    task = next(item for item in filtered if item["title"] == "任务管理")
    assert task["children"] == [{"title": "业务任务", "route_path": "business/task"}]


def test_wms_assembly_filters_runtime_menu_tree() -> None:
    assembly = load_assembly_from_file(Path("app/assemblies/wms.toml"))
    menu_tree = [
        {"title": "系统管理", "route_path": "/system", "children": []},
        {"title": "监控管理", "route_path": "/monitor", "children": []},
        {"title": "接口管理", "route_path": "/swagger", "children": []},
        {
            "title": "平台管理",
            "route_path": "/platform",
            "children": [
                {"title": "租户管理", "route_path": "tenant"},
                {"title": "套餐管理", "route_path": "package"},
                {"title": "订单管理", "route_path": "order"},
                {"title": "发票管理", "route_path": "invoice"},
                {"title": "插件市场", "route_path": "plugin-market"},
            ],
        },
        {
            "title": "任务管理",
            "route_path": "/task",
            "children": [{"title": "业务任务", "route_path": "business/task"}],
        },
        {
            "title": "案例管理",
            "route_path": "/example",
            "children": [
                {
                    "title": "demo示例",
                    "route_path": "demo",
                    "component_path": "module_example/demo/index",
                    "permission": "module_example:demo:query",
                }
            ],
        },
        {
            "title": "代码管理",
            "route_path": "/generator",
            "children": [
                {
                    "title": "代码生成",
                    "route_path": "gencode",
                    "component_path": "module_generator/gencode/index",
                    "permission": "module_generator:gencode:query",
                }
            ],
        },
    ]

    filtered = assembly.filter_menu_tree(menu_tree)
    titles = {item["title"] for item in filtered}

    assert "系统管理" in titles
    assert "平台管理" in titles
    assert "代码管理" not in titles
    assert "任务管理" not in titles
    assert "AI管理" not in titles
    assert "监控管理" not in titles
    assert "接口管理" not in titles
    assert "案例管理" not in titles
    platform = next(item for item in filtered if item["title"] == "平台管理")
    platform_titles = {item["title"] for item in platform["children"]}
    assert platform_titles == {"租户管理"}


@pytest.mark.asyncio
async def test_seed_data_filters_disabled_plugin_menus_and_relations() -> None:
    old_file = settings.APP_ASSEMBLY_FILE
    old_name = settings.APP_ASSEMBLY
    settings.APP_ASSEMBLY_FILE = "app/assemblies/business-admin.toml"
    settings.APP_ASSEMBLY = "business-admin"
    reset_assembly_cache()

    try:
        initializer = InitializeData()

        menus = await initializer._InitializeData__load_json("platform_menu")
        flat_menus = _flatten_menu_seed(menus)
        assert not any(str(item.get("permission") or "").startswith("module_ai:") for item in flat_menus)
        assert not any(str(item.get("permission") or "").startswith("module_example:") for item in flat_menus)
        assert not any(str(item.get("component_path") or "").startswith("module_ai/") for item in flat_menus)
        assert not any(str(item.get("component_path") or "").startswith("module_example/") for item in flat_menus)
        assert any(str(item.get("component_path") or "").startswith("module_generator/") for item in flat_menus)

        plugins = await initializer._InitializeData__load_json("platform_plugin")
        plugin_codes = {item["code"] for item in plugins}
        assert "ai_assistant" not in plugin_codes
        assert "code_generator" in plugin_codes
        assert "workflow_engine" in plugin_codes

        package_plugins = await initializer._InitializeData__load_json("platform_package_plugin")
        tenant_plugins = await initializer._InitializeData__load_json("platform_tenant_plugin")
        assert all(item["plugin_id"] <= len(plugins) for item in package_plugins)
        assert all(item["plugin_id"] <= len(plugins) for item in tenant_plugins)
    finally:
        settings.APP_ASSEMBLY_FILE = old_file
        settings.APP_ASSEMBLY = old_name
        reset_assembly_cache()


@pytest.mark.asyncio
async def test_seed_menu_filters_disabled_route_groups_without_disabled_plugins(tmp_path: Path) -> None:
    config = tmp_path / "route-group-only.toml"
    config.write_text(
        """
[assembly]
name = "route-group-only"

[backend]
disabled_plugins = []

[frontend]
enabled_route_groups = ["system", "platform"]
disabled_route_groups = ["monitor", "swagger"]

[seed]
packs = ["legacy"]
""",
        encoding="utf-8",
    )
    old_file = settings.APP_ASSEMBLY_FILE
    old_name = settings.APP_ASSEMBLY
    settings.APP_ASSEMBLY_FILE = str(config)
    settings.APP_ASSEMBLY = "route-group-only"
    reset_assembly_cache()

    try:
        initializer = InitializeData()
        menus = await initializer._InitializeData__load_json("platform_menu")
        top_paths = {item.get("route_path") for item in menus}
        assert "/monitor" not in top_paths
        assert "/swagger" not in top_paths
    finally:
        settings.APP_ASSEMBLY_FILE = old_file
        settings.APP_ASSEMBLY = old_name
        reset_assembly_cache()


@pytest.mark.asyncio
async def test_wms_seed_appends_product_menu_to_base_seed() -> None:
    old_file = settings.APP_ASSEMBLY_FILE
    old_name = settings.APP_ASSEMBLY
    settings.APP_ASSEMBLY_FILE = "app/assemblies/wms.toml"
    settings.APP_ASSEMBLY = "wms"
    reset_assembly_cache()

    try:
        initializer = InitializeData()
        menus = await initializer._InitializeData__load_json("platform_menu")
        flat_menus = _flatten_menu_seed(menus)
        top_paths = {item.get("route_path") for item in menus}
        permissions = {item.get("permission") for item in flat_menus}
        route_names = {item.get("route_name") for item in flat_menus}
        redirects = {item.get("route_name"): item.get("redirect") for item in flat_menus}

        assert "/platform" in top_paths
        assert "/system" in top_paths
        assert "/module-wms" in top_paths
        assert "WmsOps" in route_names
        assert "WmsReceiving" in route_names
        assert "WmsShipping" in route_names
        assert "WmsInventory" in route_names
        assert "WmsAnalytics" in route_names
        assert redirects["WmsOps"] == "/module-wms/ops/dashboard"
        assert redirects["WmsBase"] == "/module-wms/base/master"
        assert redirects["WmsReceiving"] == "/module-wms/receiving/arrival"
        assert redirects["WmsShipping"] == "/module-wms/shipping/outbound"
        assert redirects["WmsInventory"] == "/module-wms/inventory/stock"
        assert redirects["WmsAnalytics"] == "/module-wms/analytics/warning"
        assert redirects["WmsTrialTools"] == "/module-wms/trial-tools/demo"
        assert "module_wms:dashboard:query" in permissions
        assert "module_wms:master:query" in permissions
        assert "module_wms:master:create" in permissions
        assert "module_wms:arrival:query" in permissions
        assert "module_wms:arrival:receive" in permissions
        assert "module_wms:inspection:judge" in permissions
        assert "module_wms:inbound:query" in permissions
        assert "module_wms:inbound:confirm" in permissions
        assert "module_wms:outbound:query" in permissions
        assert "module_wms:outbound:reserve" in permissions
        assert "module_wms:outbound:confirm" in permissions
        assert "module_wms:issue:query" in permissions
        assert "module_wms:issue:reserve" in permissions
        assert "module_wms:issue:confirm" in permissions
        assert "module_wms:transfer:query" in permissions
        assert "module_wms:transfer:confirm" in permissions
        assert "module_wms:check:query" in permissions
        assert "module_wms:check:audit" in permissions
        assert "module_wms:warning:query" in permissions
        assert "module_wms:warning:scan" in permissions
        assert "module_wms:trace:query" in permissions
        assert "module_wms:demo:init" in permissions
        assert "module_wms:demo:clean" in permissions
        assert "module_wms:integration:inbound" in permissions
        assert "module_wms:integration:outbound" in permissions
        assert "module_wms:integration:query" in permissions
        assert "module_wms:stock:query" in permissions
        assert "module_wms:stock:lock" in permissions
        assert "module_wms:stock:unlock" in permissions
        assert "module_wms:stock:freeze" in permissions
        assert "module_wms:stock:adjust" in permissions
        assert not any(str(item.get("permission") or "").startswith("module_example:") for item in flat_menus)
    finally:
        settings.APP_ASSEMBLY_FILE = old_file
        settings.APP_ASSEMBLY = old_name
        reset_assembly_cache()


@pytest.mark.asyncio
async def test_wms_seed_backfills_missing_menu_when_table_already_exists(test_client: TestClient) -> None:
    old_file = settings.APP_ASSEMBLY_FILE
    old_name = settings.APP_ASSEMBLY
    settings.APP_ASSEMBLY_FILE = "app/assemblies/wms.toml"
    settings.APP_ASSEMBLY = "wms"
    reset_assembly_cache()

    try:
        from app.api.v1.module_platform.menu.model import MenuModel
        from app.core.database import async_db_session

        async with async_db_session() as db:
            await db.execute(
                delete(MenuModel).where(
                    or_(
                        MenuModel.route_name == "ModuleWms",
                        MenuModel.permission.like("module_wms:%"),
                        MenuModel.component_path.like("module_wms/%"),
                    )
                )
            )
            await db.commit()

        await InitializeData().init_db()

        async with async_db_session() as db:
            total = (
                await db.execute(
                    select(func.count())
                    .select_from(MenuModel)
                    .where(
                        or_(
                            MenuModel.route_name == "ModuleWms",
                            MenuModel.permission.like("module_wms:%"),
                            MenuModel.component_path.like("module_wms/%"),
                        )
                    )
                )
            ).scalar_one()
        assert total > 0
    finally:
        settings.APP_ASSEMBLY_FILE = old_file
        settings.APP_ASSEMBLY = old_name
        reset_assembly_cache()


@pytest.mark.asyncio
async def test_seed_identity_sync_sets_postgres_sequence_to_max_id(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.api.v1.module_platform.tenant.model import TenantModel

    class _FakeResult:
        def __init__(self, value):
            self.value = value

        def scalar_one_or_none(self):
            return self.value

    class _FakeSession:
        def __init__(self):
            self.calls = []
            self.results = [
                _FakeResult("public.platform_tenant_id_seq"),
                _FakeResult(12),
                _FakeResult(None),
            ]

        async def execute(self, statement, params=None):
            self.calls.append((statement, params))
            return self.results.pop(0)

    old_database_type = settings.DATABASE_TYPE
    monkeypatch.setattr(settings, "DATABASE_TYPE", "postgres")
    db = _FakeSession()

    try:
        synced = await InitializeData()._InitializeData__sync_identity_to_max(db, TenantModel)
    finally:
        monkeypatch.setattr(settings, "DATABASE_TYPE", old_database_type)

    assert synced is True
    assert len(db.calls) == 3
    assert db.calls[0][1] == {"table_name": "platform_tenant"}
    assert db.calls[2][1] == {
        "sequence_name": "public.platform_tenant_id_seq",
        "max_id": 12,
    }


@pytest.mark.asyncio
async def test_wms_seed_backfills_product_menu_tree_and_owner_role_authorizations(test_client: TestClient) -> None:
    old_file = settings.APP_ASSEMBLY_FILE
    old_name = settings.APP_ASSEMBLY
    settings.APP_ASSEMBLY_FILE = "app/assemblies/wms.toml"
    settings.APP_ASSEMBLY = "wms"
    reset_assembly_cache()

    try:
        from app.api.v1.module_platform.menu.model import MenuModel
        from app.api.v1.module_platform.package.model import PackageMenuModel
        from app.api.v1.module_system.role.model import RoleMenusModel, RoleModel
        from app.core.database import async_db_session

        async with async_db_session() as db:
            product_menu_rows = (
                await db.execute(
                    select(MenuModel.id, MenuModel.route_name).where(
                        MenuModel.route_name.in_(
                            [
                                "Platform",
                                "PlatformWorkspace",
                                "System",
                                "User",
                                "Role",
                                "Dept",
                                "ModuleWms",
                                "WmsOps",
                                "WmsDashboard",
                            ]
                        ),
                        MenuModel.status == 0,
                    )
                )
            ).all()
            by_route_name = {route_name: menu_id for menu_id, route_name in product_menu_rows}
            assert {
                "Platform",
                "PlatformWorkspace",
                "System",
                "User",
                "Role",
                "Dept",
                "ModuleWms",
                "WmsOps",
                "WmsDashboard",
            }.issubset(by_route_name)

            owner_role_id = (
                await db.execute(
                    select(RoleModel.id)
                    .where(RoleModel.tenant_id == 2, RoleModel.code == "TEST_ADMIN")
                    .limit(1)
                )
            ).scalar_one()
            product_menu_ids = list(by_route_name.values())

            await db.execute(delete(PackageMenuModel).where(PackageMenuModel.menu_id.in_(product_menu_ids)))
            await db.execute(
                delete(RoleMenusModel).where(
                    RoleMenusModel.role_id == owner_role_id,
                    RoleMenusModel.menu_id.in_(product_menu_ids),
                )
            )
            await db.commit()

        await InitializeData().init_db()

        async with async_db_session() as db:
            package_count = (
                await db.execute(
                    select(func.count())
                    .select_from(PackageMenuModel)
                    .where(PackageMenuModel.menu_id.in_(product_menu_ids))
                )
            ).scalar_one()
            role_count = (
                await db.execute(
                    select(func.count())
                    .select_from(RoleMenusModel)
                    .where(
                        RoleMenusModel.role_id == owner_role_id,
                        RoleMenusModel.menu_id.in_(product_menu_ids),
                    )
                )
            ).scalar_one()

        assert package_count >= len(product_menu_ids)
        assert role_count == len(product_menu_ids)
    finally:
        settings.APP_ASSEMBLY_FILE = old_file
        settings.APP_ASSEMBLY = old_name
        reset_assembly_cache()


def _flatten_menu_seed(items: list[dict]) -> list[dict]:
    result: list[dict] = []
    for item in items:
        result.append(item)
        result.extend(_flatten_menu_seed(item.get("children") or []))
    return result
