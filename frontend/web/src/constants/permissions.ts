const TENANT_PERMISSION_ACTIONS = ["query", "create", "update", "delete", "patch"] as const;

type TenantPermissionAction = (typeof TENANT_PERMISSION_ACTIONS)[number];

function buildTenantPermissions(prefix: "module_platform" | "module_system") {
  return TENANT_PERMISSION_ACTIONS.reduce(
    (acc, action) => {
      acc[action] = `${prefix}:tenant:${action}`;
      return acc;
    },
    {} as Record<TenantPermissionAction, string>
  );
}

export const PLATFORM_TENANT_PERMISSIONS = buildTenantPermissions("module_platform");
export const LEGACY_SYSTEM_TENANT_PERMISSIONS = buildTenantPermissions("module_system");

const PERMISSION_ALIASES = TENANT_PERMISSION_ACTIONS.reduce(
  (acc, action) => {
    const platformPermission = PLATFORM_TENANT_PERMISSIONS[action];
    const legacyPermission = LEGACY_SYSTEM_TENANT_PERMISSIONS[action];
    acc[platformPermission] = [legacyPermission];
    acc[legacyPermission] = [platformPermission];
    return acc;
  },
  {} as Record<string, string[]>
);

export function expandPermissionAliases(permission: string): string[] {
  return Array.from(new Set([permission, ...(PERMISSION_ALIASES[permission] ?? [])]));
}

export function hasPermissionInList(permissions: string[], requiredPermission: string): boolean {
  return expandPermissionAliases(requiredPermission).some((permission) =>
    permissions.includes(permission)
  );
}
