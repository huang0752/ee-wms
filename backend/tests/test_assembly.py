from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config.setting import settings
from app.core.assembly import load_assembly_from_file, reset_assembly_cache
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


def _flatten_menu_seed(items: list[dict]) -> list[dict]:
    result: list[dict] = []
    for item in items:
        result.append(item)
        result.extend(_flatten_menu_seed(item.get("children") or []))
    return result
