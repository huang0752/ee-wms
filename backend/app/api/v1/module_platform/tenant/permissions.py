TENANT_PERMISSION_PREFIX = "module_platform:tenant"
LEGACY_TENANT_PERMISSION_PREFIX = "module_system:tenant"

TENANT_PERMISSION_ACTIONS = ("query", "create", "update", "delete", "patch")

PLATFORM_TENANT_PERMISSIONS = {
    action: f"{TENANT_PERMISSION_PREFIX}:{action}" for action in TENANT_PERMISSION_ACTIONS
}
LEGACY_SYSTEM_TENANT_PERMISSIONS = {
    action: f"{LEGACY_TENANT_PERMISSION_PREFIX}:{action}" for action in TENANT_PERMISSION_ACTIONS
}


def tenant_permissions(action: str) -> list[str]:
    """Return primary platform permission plus legacy system alias."""
    if action not in PLATFORM_TENANT_PERMISSIONS:
        raise ValueError(f"Unsupported tenant permission action: {action}")
    return [
        PLATFORM_TENANT_PERMISSIONS[action],
        LEGACY_SYSTEM_TENANT_PERMISSIONS[action],
    ]


TENANT_QUERY_PERMISSIONS = tenant_permissions("query")
TENANT_CREATE_PERMISSIONS = tenant_permissions("create")
TENANT_UPDATE_PERMISSIONS = tenant_permissions("update")
TENANT_DELETE_PERMISSIONS = tenant_permissions("delete")
TENANT_PATCH_PERMISSIONS = tenant_permissions("patch")
