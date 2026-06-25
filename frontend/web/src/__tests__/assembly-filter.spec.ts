import { describe, expect, it } from "vitest";
import { filterRoutesByAssembly, isRouteGroupEnabled } from "@/router/filterByAssembly";
import type { AssemblySummary } from "@/config/assembly/default";
import type { RouteRecordRaw } from "vue-router";

const summary: AssemblySummary = {
  name: "minimal",
  title: "Minimal",
  enabledRouteGroups: ["home", "system", "exception", "user-profile"],
  disabledRouteGroups: ["pricing"],
  featureFlags: {},
};

describe("assembly route filtering", () => {
  const DummyComponent = { template: "<div />" };

  it("checks enabled and disabled route groups", () => {
    expect(isRouteGroupEnabled("home", summary)).toBe(true);
    expect(isRouteGroupEnabled("pricing", summary)).toBe(false);
    expect(isRouteGroupEnabled("unknown", summary)).toBe(false);
    expect(isRouteGroupEnabled(undefined, summary)).toBe(true);
  });

  it("filters nested static routes by routeGroup", () => {
    const routes: RouteRecordRaw[] = [
      {
        path: "/",
        component: DummyComponent,
        children: [
          { path: "home", component: DummyComponent, meta: { routeGroup: "home" } },
          { path: "pricing", component: DummyComponent, meta: { routeGroup: "pricing" } },
          { path: "settings", component: DummyComponent, meta: { routeGroup: "system" } },
        ],
      },
    ];
    const filtered = filterRoutesByAssembly(routes, summary);

    expect(filtered).toHaveLength(1);
    expect(filtered[0]?.children?.map((route) => route.path)).toEqual(["home", "settings"]);
  });

  it("keeps neutral route containers when an enabled child remains", () => {
    const routes: RouteRecordRaw[] = [
      {
        path: "/",
        component: DummyComponent,
        children: [
          {
            path: "fastlink",
            component: DummyComponent,
            meta: { hidden: true },
            children: [
              { path: "profile", component: DummyComponent, meta: { routeGroup: "user-profile" } },
              { path: "pricing", component: DummyComponent, meta: { routeGroup: "pricing" } },
            ],
          },
        ],
      },
    ];
    const filtered = filterRoutesByAssembly(routes, summary);
    const fastlink = filtered[0]?.children?.[0];

    expect(fastlink?.path).toBe("fastlink");
    expect(fastlink?.children?.map((route) => route.path)).toEqual(["profile"]);
  });
});
