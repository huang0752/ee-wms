# 产品装配与可见运行面减法框架合并说明

## 1. 背景

`ee-wms` 是基于 FastapiAdmin 的产品仓库。近期在 WMS 产品初始化时做了“先减法”的验证：后端插件、前端路由、动态菜单、首页、登录页提示、公告、版本提示、新手引导等都需要从“框架演示态”切换成“产品运行态”。

这次验证暴露了一个框架层问题：仅有后端插件禁用或前端静态路由过滤还不够。产品看到的运行面来自多个来源：

- 后端动态路由扫描。
- 用户 `current_info` 返回的动态菜单。
- seed 初始化数据。
- 前端静态路由。
- 前端登录页、首页、公告条、新版本提示、新手引导。
- 租户品牌配置。

如果这些入口没有统一受产品装配控制，就会出现“接口已禁用，但菜单还显示”“路由已过滤，但首页仍是演示页”“产品已是 WMS，但登录页仍提示 FastapiAdmin Star”的割裂状态。

本说明用于给框架开发评估：哪些减法能力应沉淀到 FastapiAdmin 框架，哪些应保留在 WMS 产品仓库。

## 2. 目标

框架需要提供一套通用的 **Capability Assembly（能力装配）** 机制，让任意产品仓库通过配置声明运行面，而不是让框架核心理解 WMS、MES、ERP 等业务语义。

目标：

1. 支持按装配启停后端插件和动态路由。
2. 支持按装配过滤前端静态路由组。
3. 支持按装配过滤后端返回的动态菜单。
4. 支持按装配选择 seed pack，并过滤禁用插件的 seed。
5. 支持按功能开关关闭框架演示内容，例如公告、版本提示、新手引导、Star 通知。
6. 保持默认完整行为兼容；未配置装配时不影响现有 FastapiAdmin 使用者。

非目标：

1. 不在框架核心写死 `wms`、`mes`、`erp`。
2. 不物理删除未启用模块源码。
3. 不用前端隐藏替代后端权限、租户隔离、套餐授权。
4. 不在框架中实现 WMS 首页、WMS 菜单、WMS 权限、WMS 业务模型。

## 3. 归属边界

| 能力 | 建议归属 | 说明 |
|---|---|---|
| 能力装配 TOML 解析 | 框架 | 通用机制，所有产品可复用 |
| 后端插件启停 | 框架 | 控制动态路由扫描与插件可见性 |
| 前端静态路由组过滤 | 框架 | 定价、文章、教程、changelog 等不应每个产品手工删 |
| 动态菜单过滤 | 框架 | 菜单来自后端，必须与路由/插件同源控制 |
| seed pack 选择与过滤 | 框架 | 新产品初始化需要可组合 seed |
| `demoContent` 等功能开关 | 框架 | 控制公告、版本提示、引导、Star 通知等演示态内容 |
| WMS 首页 | 产品 | 产品自己的业务入口 |
| WMS 品牌文案、租户名、版权 | 产品 | 产品配置或产品 seed |
| `module_wms` API/页面/权限 | 产品 | 业务域不可进入框架核心 |

## 4. 当前 ee-wms 参考实现

当前 `ee-wms` 已有可迁移参考代码。框架开发可以按这些文件评估抽取方式：

- `backend/app/core/assembly.py`
  - `AssemblyConfig`
  - `is_plugin_enabled`
  - `is_route_group_enabled`
  - `filter_menu_tree`
  - `get_frontend_assembly_summary`
- `backend/app/api/v1/module_system/user/service.py`
  - `current_info()` 返回菜单前调用装配过滤。
- `backend/app/scripts/initialize.py`
  - 初始化 seed 时过滤禁用插件菜单、插件表、插件关系表。
- `backend/app/assemblies/wms.toml`
  - 产品侧装配文件示例。
- `frontend/web/src/store/modules/assembly.store.ts`
  - 前端读取 `/system/config/info` 中的 assembly 摘要。
- `frontend/web/src/router/filterByAssembly.ts`
  - 静态路由组过滤。
- `frontend/web/src/hooks/core/useAppBootstrap.ts`
  - 先加载 assembly，再决定是否启动版本提示/轮询。
- `frontend/web/src/hooks/core/useCeremony.ts`
  - `demoContent=false` 时不打开框架公告。
- `frontend/web/src/components/text-effect/fa-festival-text-scroll/index.vue`
  - 已打开的公告条也按 `demoContent` 隐藏。
- `frontend/web/src/views/module_system/auth/login/index.vue`
  - 登录后新手引导和 Star 通知按 `demoContent` 控制。

## 5. 建议配置模型

框架保留默认完整装配，产品仓库可增加自己的装配文件。

```toml
[assembly]
name = "business-admin"
title = "业务后台装配"
description = "框架通用业务后台能力组合"

[core]
required = ["auth", "tenant", "user", "role", "permission", "menu", "settings", "audit"]

[backend]
enabled_plugins = ["module_ai", "module_task", "module_generator"]
disabled_plugins = ["module_example"]

[frontend]
enabled_route_groups = [
  "auth",
  "home",
  "dashboard",
  "system",
  "platform",
  "module-task",
  "module-generator",
  "ai-chat",
  "user-profile",
  "exception"
]
disabled_route_groups = ["pricing", "article", "tutorial", "changelog"]

[seed]
packs = ["business-admin"]

[features]
flags = {
  ai_assistant = true,
  plugin_market = false,
  tenant_package = true,
  demo_content = false,
  fast_enter = true
}
```

产品仓库中的 WMS 可写成：

```toml
[assembly]
name = "wms"
title = "EE WMS 装配"
description = "产品仓库维护的 WMS 运行态装配；框架只按通用能力执行。"

[backend]
enabled_plugins = ["module_ai", "module_task", "module_generator"]
disabled_plugins = ["module_example"]

[frontend]
enabled_route_groups = [
  "auth",
  "home",
  "dashboard",
  "system",
  "platform",
  "module-wms",
  "user-profile",
  "exception"
]
disabled_route_groups = ["ai-chat", "module-task", "module-generator", "pricing", "article", "tutorial", "changelog"]

[seed]
packs = ["wms"]

[features]
flags = { demo_content = false, ai_assistant = false, fast_enter = true }
```

框架不要对 `name = "wms"` 做任何特殊判断。`wms` 只是产品仓库选择的装配文件名。
该示例同时说明：后端插件启用不等于前端管理入口必须展示。产品可以保留框架能力，同时通过 route group 和 feature flag 隐藏业务用户不该直接看到的管理界面。

## 6. 后端框架改造建议

### 6.1 装配配置对象

建议在框架中保留一个独立模块，例如：

```text
backend/app/core/assembly.py
```

核心接口：

```python
def get_assembly() -> AssemblyConfig:
    ...

def is_plugin_enabled(code: str) -> bool:
    return get_assembly().is_plugin_enabled(code)

def get_frontend_assembly_summary() -> dict[str, Any]:
    return get_assembly().frontend_summary()

def filter_menu_tree_by_assembly(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return get_assembly().filter_menu_tree(items)
```

参考菜单过滤实现：

```python
PLUGIN_CODE_ALIASES: dict[str, tuple[str, ...]] = {
    "module_ai": ("ai", "ai_assistant"),
    "module_generator": ("generator", "code_generator"),
    "module_task": ("task", "workflow_engine"),
    "module_example": ("example",),
}

MENU_ROUTE_GROUP_ALIASES: dict[str, str] = {
    "ai": "ai-chat",
    "generator": "module-generator",
    "task": "module-task",
}

def plugin_code_candidates(module_code: str) -> list[str]:
    normalized = _normalize_module_code(module_code)
    return [normalized, *PLUGIN_CODE_ALIASES.get(normalized, ())]

@dataclass(frozen=True)
class AssemblyConfig:
    enabled_plugins: list[str] = field(default_factory=list)
    disabled_plugins: list[str] = field(default_factory=list)
    enabled_route_groups: list[str] = field(default_factory=list)
    disabled_route_groups: list[str] = field(default_factory=list)
    feature_flags: dict[str, bool] = field(default_factory=dict)

    def is_plugin_enabled(self, code: str) -> bool:
        module_code = _normalize_module_code(code)
        disabled = {_normalize_module_code(item) for item in self.disabled_plugins}
        if module_code in disabled:
            return False
        enabled = {_normalize_module_code(item) for item in self.enabled_plugins}
        return not enabled or module_code in enabled

    def is_route_group_enabled(self, route_group: str | None) -> bool:
        if not route_group:
            return True
        group = route_group.strip()
        if group in set(self.disabled_route_groups):
            return False
        enabled = set(self.enabled_route_groups)
        return not enabled or group in enabled

    def is_menu_item_enabled(self, item: dict[str, Any]) -> bool:
        permission = str(item.get("permission") or "")
        component_path = str(item.get("component_path") or "")
        route_group = self._menu_route_group(item)

        for plugin_code in self.disabled_plugins:
            for candidate in plugin_code_candidates(plugin_code):
                if permission.startswith(f"{candidate}:"):
                    return False
                if component_path.startswith(f"{candidate}/"):
                    return False

        if route_group and not self.is_route_group_enabled(route_group):
            return False
        return True

    def _menu_route_group(self, item: dict[str, Any]) -> str | None:
        raw_path = str(item.get("route_path") or "").strip()
        if not raw_path or not raw_path.startswith("/"):
            return None
        first_segment = raw_path.strip("/").split("/", 1)[0]
        if not first_segment:
            return None
        normalized = first_segment.replace("_", "-")
        return MENU_ROUTE_GROUP_ALIASES.get(normalized, normalized)

    def filter_menu_tree(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        filtered: list[dict[str, Any]] = []
        for item in items:
            if not self.is_menu_item_enabled(item):
                continue
            next_item = dict(item)
            children = next_item.get("children") or []
            if children:
                next_item["children"] = self.filter_menu_tree(children)
            had_children = bool(children)
            is_empty_catalog = had_children and not next_item.get("children") and not next_item.get("component_path")
            if is_empty_catalog:
                continue
            filtered.append(next_item)
        return filtered
```

注意：`_menu_route_group()` 只应处理以 `/` 开头的顶层路由。子菜单通常是相对路径，例如 `business/task`，不能直接当作 route group 裁剪，否则会误删已启用插件的子菜单。

### 6.2 动态路由扫描

动态路由发现时，如果插件被禁用，应跳过该插件包：

```python
if not is_plugin_enabled(module_name):
    logger.info("⏭️  跳过插件模块 {}：assembly {} disabled", module_name, assembly.name)
    continue
```

验收标准：

- `disabled_plugins = ["module_example"]` 时，不注册 `/example` 动态 API。
- `/api/v1/example/demo/list` 返回 `404`。
- 日志能看到跳过原因。

### 6.3 当前用户菜单过滤

`current_info()` 是前端侧边栏菜单的数据来源，应在组树后统一过滤：

```python
menu_tree = traversal_to_tree([menu.model_dump() for menu in menus])
user_dict.menus = filter_menu_tree_by_assembly(menu_tree)
```

验收标准：

- `module_example` 被禁用时，`案例管理` 不出现在 `current_info.data.menus`。
- `monitor`、`swagger` 等不在 `enabled_route_groups` 中时，不出现在 `current_info.data.menus`。
- `module_task` 已启用时，`任务管理` 及其相对子菜单仍保留。
- 如果产品把 `module-task` 加入 `disabled_route_groups`，即使后端 `module_task` 插件启用，`任务管理` 也不出现在 `current_info.data.menus`。

### 6.4 seed 初始化过滤

初始化逻辑建议同时覆盖：

- `platform_menu`
- `platform_plugin`
- `platform_package_plugin`
- `platform_tenant_plugin`

参考规则：

```python
def __menu_item_disabled(self, item: dict) -> bool:
    permission = str(item.get("permission") or "")
    component_path = str(item.get("component_path") or "")
    for module_code in self._disabled_module_codes:
        if permission.startswith(f"{module_code}:"):
            return True
        if component_path.startswith(f"{module_code}/"):
            return True
    return False
```

框架后续可以统一复用 `AssemblyConfig.filter_menu_tree()`，避免 seed 过滤和运行时菜单过滤规则分叉。

## 7. 前端框架改造建议

### 7.1 Assembly Store

框架前端需要一个全局 store 读取后端公开摘要：

```ts
export interface AssemblySummary {
  name: string;
  title: string;
  enabledRouteGroups: string[];
  disabledRouteGroups: string[];
  featureFlags: Record<string, boolean>;
}

function isFeatureEnabled(feature: string, fallback = true): boolean {
  const value = summary.value.featureFlags[feature];
  return typeof value === "boolean" ? value : fallback;
}
```

后端公开摘要建议挂在：

```http
GET /api/v1/system/config/info
```

返回字段示例：

```json
{
  "assembly": {
    "name": "wms",
    "title": "EE WMS 装配",
    "enabledRouteGroups": ["home", "system", "platform", "module-task"],
    "disabledRouteGroups": ["pricing", "article", "tutorial", "changelog"],
    "featureFlags": {
      "demoContent": false,
      "aiAssistant": true,
      "fastEnter": true
    }
  }
}
```

### 7.2 启动顺序

应用启动时必须先加载 assembly，再启动演示态功能：

```ts
const bootstrap = async () => {
  checkStorageCompatibility();
  toggleTransition(false);
  await assemblyStore.loadPublicConfig();
  if (assemblyStore.isFeatureEnabled("demoContent", true)) {
    systemUpgrade();
    startVersionPolling();
  }
  initSiteConfig();
};
```

如果顺序反过来，`demoContent=false` 已经返回时，版本提示可能已经弹出。

### 7.3 静态路由过滤

静态路由 meta 增加 `routeGroup`：

```ts
{
  path: "pricing",
  meta: {
    title: "定价",
    routeGroup: "pricing"
  },
  component: () => import("@views/fastlink/pricing/index.vue")
}
```

过滤规则：

```ts
export function isRouteGroupEnabled(routeGroup: string | undefined, summary: AssemblySummary): boolean {
  if (!routeGroup) return true;
  if (summary.disabledRouteGroups.includes(routeGroup)) return false;
  return summary.enabledRouteGroups.length === 0 || summary.enabledRouteGroups.includes(routeGroup);
}
```

### 7.4 演示态内容开关

`demoContent=false` 时建议关闭：

- 登录页 Star/Github/Gitee 推广通知。
- 登录后新手引导。
- 顶栏常驻公告。
- 框架新版本提示和版本轮询。
- 演示快速链接。
- 示例首页卡片。

示例：

```ts
if (settingStore.showGuide && assemblyStore.isFeatureEnabled("demoContent", true)) {
  appStore.showGuide(true);
}
```

示例：

```ts
const showFestivalStrip = computed(
  () =>
    showFestivalText.value &&
    assemblyStore.isFeatureEnabled("demoContent", true) &&
    !!currentFestivalData.value?.scrollText
);
```

## 8. 产品仓库保留内容

框架完成上述能力后，WMS 产品仓库应尽量只保留：

```text
backend/app/assemblies/wms.toml
backend/app/scripts/seeds/wms/
frontend/web/src/views/dashboard/home/index.vue
frontend/web/src/views/module_wms/
frontend/web/src/api/module_wms/
backend/app/api/v1/module_wms/
docs/product/
```

WMS 首页、登录文案、租户品牌配置、业务菜单、业务权限、业务 API 不应回框架。

## 9. 测试建议

### 9.1 后端单元测试

建议添加：

```python
def test_wms_assembly_filters_runtime_menu_tree() -> None:
    assembly = load_assembly_from_file(Path("app/assemblies/wms.toml"))
    menu_tree = [
        {"title": "系统管理", "route_path": "/system", "children": []},
        {"title": "监控管理", "route_path": "/monitor", "children": []},
        {"title": "接口管理", "route_path": "/swagger", "children": []},
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
    ]

    filtered = assembly.filter_menu_tree(menu_tree)
    titles = {item["title"] for item in filtered}

    assert "系统管理" in titles
    assert "任务管理" in titles
    assert "监控管理" not in titles
    assert "接口管理" not in titles
    assert "案例管理" not in titles
```

### 9.2 API 验收

启动产品装配：

```bash
APP_ASSEMBLY=wms uv run python main.py run --env=dev
```

检查：

```bash
curl -sS http://127.0.0.1:41232/api/v1/system/config/info | python3 -m json.tool
curl -sS -o /tmp/example.txt -w '%{http_code}\n' http://127.0.0.1:41232/api/v1/example/demo/list
```

预期：

- `assembly.name = "wms"`。
- `featureFlags.demoContent = false`。
- example API 返回 `404`。

登录后检查菜单：

```bash
curl -sS http://127.0.0.1:41232/api/v1/system/user/current/info \
  -H "Authorization: Bearer <token>" | python3 -m json.tool
```

预期：

- 不包含 `案例管理`。
- 不包含未启用 route group 对应的 `监控管理`、`接口管理`。
- WMS V1 不包含 `代码管理`、`AI管理`、`任务管理`；这些后端插件能力保留，但前台管理入口由装配隐藏。

### 9.3 前端验收

```bash
cd frontend/web
corepack pnpm run type-check
```

浏览器验收：

- 登录页不出现 FastapiAdmin Star/Github/Gitee 推广通知。
- 顶部不出现框架发布公告。
- 登录后不弹新手引导。
- 首页不是框架演示数据看板。
- 菜单不显示案例、定价、文章、教程、更新日志等被裁剪内容。

## 10. 向框架合并的建议步骤

1. **先合并后端装配核心**
   - `AssemblyConfig`
   - TOML 加载
   - `get_frontend_assembly_summary`
   - 插件启停

2. **再合并菜单与 seed 过滤**
   - `current_info` 动态菜单过滤。
   - seed 初始化过滤。
   - 添加测试覆盖相对路径子菜单不误删。

3. **再合并前端 assembly store 与路由过滤**
   - 前端读取 config/info。
   - 静态路由按 `routeGroup` 过滤。
   - 默认 `defaultAssemblySummary` 保持完整行为。

4. **最后合并 demoContent 开关**
   - 版本提示。
   - 公告条。
   - 新手引导。
   - Star 通知。
   - 演示快速入口。

5. **框架提供示例装配**
   - `default.toml`：完整框架行为。
   - `minimal.toml`：极简后台。
   - `business-admin.toml`：常规业务后台。
   - `saas-admin.toml`：SaaS 平台后台。

产品仓库只维护自己的 `wms.toml` 和业务代码。

## 11. 风险与兼容性

1. **默认值必须完整兼容**
   - 没有 assembly 文件时，框架应保持当前完整演示行为。
   - `featureFlags.demoContent` 默认应为 `true`。

2. **菜单过滤不能破坏权限**
   - 菜单过滤只减少可见入口。
   - API 权限仍由 `AuthPermission`、角色、租户套餐控制。

3. **相对子路由不能误裁剪**
   - 顶层 `/task` 可映射到 `module-task`。
   - 子路径 `business/task` 不应被当作 route group。

4. **已有数据库不会自动删除菜单**
   - 运行时过滤可以即时生效。
   - 是否提供数据清理脚本，应作为单独 starter preset 或迁移工具评估。

5. **产品品牌不应进框架**
   - 框架可提供品牌配置字段。
   - EE WMS 文案、版权、租户名应留在产品 seed 或产品配置中。

## 12. 结论

这次 WMS 减法验证说明，产品装配不是单点功能，而是贯穿后端路由、菜单、seed、前端路由和演示态 UI 的框架能力。

建议框架优先沉淀以下通用能力：

1. `AssemblyConfig` 通用配置模型。
2. 后端插件与动态路由启停。
3. 动态菜单按装配过滤。
4. seed pack 与禁用插件 seed 过滤。
5. 前端静态路由组过滤。
6. `demoContent` 功能开关。

WMS 产品仓库只保留 `wms.toml`、WMS 首页、品牌 seed 和业务模块。这样框架不会被 WMS 做窄，同时后续 MES、ERP、CRM 等产品也可以复用同一套装配机制。
