import { describe, expect, it } from "vitest";

import {
  PLATFORM_TENANT_PERMISSIONS,
  expandPermissionAliases,
  hasPermissionInList,
} from "@/constants/permissions";

describe("permission aliases", () => {
  it("keeps module_platform tenant permissions primary while accepting legacy module_system tenant permissions", () => {
    expect(PLATFORM_TENANT_PERMISSIONS.query).toBe("module_platform:tenant:query");
    expect(expandPermissionAliases("module_platform:tenant:update")).toEqual([
      "module_platform:tenant:update",
      "module_system:tenant:update",
    ]);
    expect(hasPermissionInList(["module_system:tenant:update"], "module_platform:tenant:update")).toBe(
      true
    );
    expect(hasPermissionInList(["module_system:tenant:delete"], "module_platform:tenant:update")).toBe(
      false
    );
  });
});
