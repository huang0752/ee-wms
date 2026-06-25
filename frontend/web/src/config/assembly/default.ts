export interface AssemblySummary {
  name: string;
  title: string;
  enabledRouteGroups: string[];
  disabledRouteGroups: string[];
  featureFlags: Record<string, boolean>;
}

export const defaultAssemblySummary: AssemblySummary = {
  name: "default",
  title: "默认完整装配",
  enabledRouteGroups: [],
  disabledRouteGroups: [],
  featureFlags: {
    aiAssistant: true,
    pluginMarket: true,
    tenantPackage: true,
    demoContent: true,
    fastEnter: true,
  },
};
