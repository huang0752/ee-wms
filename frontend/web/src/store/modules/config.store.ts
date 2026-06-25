/**
 * 系统配置状态管理模块
 *
 * 提供系统配置参数的状态管理
 *
 * ## 主要功能
 *
 * - 网站基础信息管理（标题、版本、描述）
 * - 网站图标配置（登录背景、favicon、Logo）
 * - 安全隐私配置（服务条款、版权、隐私政策）
 * - 接口安全配置（白名单、黑名单）
 * - 演示环境配置
 *
 * ## 使用场景
 *
 * - 系统初始化配置加载
 * - 登录页背景和Logo显示
 * - 底部版权信息展示
 * - 接口安全控制
 *
 * ## 持久化
 *
 * - 使用 localStorage 存储
 * - 自动缓存已加载的配置
 * - 支持强制刷新配置
 *
 * @module store/modules/config.store
 * @author FastapiAdmin Team
 */
import { store } from "@stores";
import ParamsAPI, { ConfigTable } from "@/api/module_system/params";
import TenantAPI from "@/api/module_platform/tenant";
import { defineStore } from "pinia";
import { ref } from "vue";
import { StorageConfig } from "@/utils/storage";

const PUBLIC_TENANT_ID = 1;
const TENANT_CONFIG_ALIASES: Record<string, string> = {
  name: "tenant_name",
  logo_url: "tenant_logo",
  version: "tenant_version",
};

export const useConfigStore = defineStore(
  "configStore",
  () => {
    // 系统配置、租户配置、最终生效配置分层保存，避免来源混淆。
    const systemConfigData = ref<Record<string, ConfigTable>>({});
    const tenantConfigData = ref<Record<string, ConfigTable>>({});
    const effectiveConfigData = ref<Record<string, ConfigTable>>({});
    // 兼容历史调用方：configData 表示最终生效配置。
    const configData = effectiveConfigData;
    // 是否已加载配置
    const isConfigLoaded = ref(false);
    // 是否正在加载配置
    const configLoading = ref(false);
    // 当前配置对应的租户 ID。用于租户切换时跳过旧缓存。
    const currentTenantConfigId = ref<number | null>(null);
    // 最近一次 fetch 时间戳，用于 force=true 时防止短期重复请求
    let _lastFetchedAt = 0;
    const MIN_FETCH_INTERVAL_MS = 5000;

    function resolveTenantId(tenantId?: number | null) {
      const explicitId = Number(tenantId);
      if (Number.isInteger(explicitId) && explicitId > 0) {
        return explicitId;
      }

      const savedTenantId = Number(localStorage.getItem(StorageConfig.LAST_TENANT_ID_KEY));
      if (Number.isInteger(savedTenantId) && savedTenantId > 0) {
        return savedTenantId;
      }

      return currentTenantConfigId.value || PUBLIC_TENANT_ID;
    }

    function upsertConfigItem(target: Record<string, ConfigTable>, item: Partial<ConfigTable>) {
      if (item.config_value !== undefined && item.config_key) {
        target[item.config_key] = item as ConfigTable;
      }
    }

    function upsertTenantConfigItem(item: Partial<ConfigTable>) {
      upsertConfigItem(tenantConfigData.value, item);
      const aliasKey = item.config_key ? TENANT_CONFIG_ALIASES[item.config_key] : undefined;
      if (aliasKey) {
        upsertConfigItem(tenantConfigData.value, {
          ...item,
          config_key: aliasKey,
        });
      }
    }

    function syncEffectiveConfig() {
      effectiveConfigData.value = {
        ...systemConfigData.value,
        ...tenantConfigData.value,
      };
    }

    /**
     * 获取系统配置 + 租户配置
     * @param force 是否强制刷新配置
     * @param tenantId 租户ID；未登录公开场景才回退到平台默认租户
     */
    async function getConfig(force = false, tenantId?: number | null) {
      const resolvedTenantId = resolveTenantId(tenantId);
      if (configLoading.value) {
        return;
      }
      // force=true 时也需防短期内重复请求
      if (!force && isConfigLoaded.value && currentTenantConfigId.value === resolvedTenantId) {
        return;
      }
      if (
        force &&
        currentTenantConfigId.value === resolvedTenantId &&
        Date.now() - _lastFetchedAt < MIN_FETCH_INTERVAL_MS
      ) {
        return;
      }
      configLoading.value = true;
      try {
        // 1. 获取系统级配置（演示模式、IP黑白名单等）
        const response = await ParamsAPI.getInitConfig();
        const list = response?.data?.data;
        if (!Array.isArray(list)) {
          console.warn("[configStore] getInitConfig: 响应 data 非数组", response?.data);
          return;
        }
        systemConfigData.value = {};
        list.forEach((item: ConfigTable) => {
          upsertConfigItem(systemConfigData.value, item);
        });

        // 2. 获取租户个性化配置（品牌标识、版权信息等）
        try {
          const tenantResp = await TenantAPI.getTenantConfigInfo(resolvedTenantId);
          const tenantList = tenantResp?.data?.data;
          if (Array.isArray(tenantList)) {
            tenantConfigData.value = {};
            tenantList.forEach((item: any) => {
              upsertTenantConfigItem(item);
            });
          }
          currentTenantConfigId.value = resolvedTenantId;
        } catch (e) {
          console.warn("[configStore] 获取租户配置失败（非关键错误）", e);
        }

        syncEffectiveConfig();
        isConfigLoaded.value = true;
        _lastFetchedAt = Date.now();
      } finally {
        configLoading.value = false;
      }
    }

    return {
      configData,
      systemConfigData,
      tenantConfigData,
      effectiveConfigData,
      isConfigLoaded,
      configLoading,
      currentTenantConfigId,
      getConfig,
    };
  },
  {
    persist: true,
  }
);

export function useConfigStoreHook() {
  return useConfigStore(store);
}
