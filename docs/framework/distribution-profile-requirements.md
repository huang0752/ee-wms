# FastapiAdmin 通用发行裁剪机制需求文档

## 1. 背景

FastapiAdmin 当前已具备菜单、角色、租户、套餐、插件、动态路由、代码生成、任务、通知、AI、`fa-*` 组件等框架能力。基于该框架可以派生 WMS、MES、CRM、内部运营后台、SaaS 平台等不同产品。

不同产品交付时，需要对框架默认能力做“减法”：

1. 某些菜单不应展示给当前产品。
2. 某些插件不应进入当前发行包。
3. 某些初始化种子不应导入。
4. 某些前端静态路由或快捷入口不应暴露。
5. 某些通用模块仍应保留代码，但在当前产品中默认关闭。

当前框架已有局部能力，例如菜单 `status/hidden/scope`、套餐菜单、套餐插件、租户插件启停、动态插件访问校验。但这些能力更偏“运行时授权和显示控制”，还不是完整的“发行裁剪机制”。

本文提出一个通用框架能力：**Distribution Profile（发行配置）**。它面向所有基于 FastapiAdmin 的产品，而不是 WMS 特判。

## 2. 目标

### 2.1 核心目标

建立一套通用发行配置机制，使同一套框架可以按不同发行包加载不同模块、菜单、插件、种子和前端入口。

示例发行包：

- `default`：框架默认完整后台。
- `wms`：智慧仓储系统。
- `mes`：智慧制造执行系统。
- `crm`：客户关系管理系统。
- `internal`：内部管理后台。
- `saas`：SaaS 平台版。

框架只识别通用概念，例如模块、插件、菜单、seed pack、静态路由、功能开关，不理解 WMS/MES 的业务语义。

### 2.2 设计目标

1. **通用性**：发行配置不写死任何业务产品。
2. **可组合**：支持多个 seed pack、多个模块、多个插件组合。
3. **可追踪**：启动时能输出当前 profile、加载了哪些模块、跳过了哪些内容。
4. **可回滚**：默认 `default` 行为尽量兼容现有框架。
5. **前后端一致**：后端 seed、插件、菜单与前端静态入口使用同一发行配置或同源下发配置。
6. **不替代权限**：发行裁剪是产品级可用性控制，不替代角色、菜单、租户、套餐、按钮权限。

## 3. 非目标

1. 不实现 WMS、MES、CRM 的业务逻辑。
2. 不把业务模块都改造成插件市场插件。
3. 不用发行配置代替 RBAC、租户隔离、套餐授权。
4. 不要求物理删除未启用模块代码。
5. 不要求首版实现按 profile 做前端 tree-shaking 或 bundle 级剔除。

## 4. 当前能力与差距

| 领域 | 当前能力 | 差距 |
|---|---|---|
| 菜单 | `platform_menu.status`、`hidden`、`scope`，可级联停用 | 无 profile 级菜单声明和初始化过滤 |
| 套餐 | `platform_package_menu`、`platform_package_plugin` | 偏租户授权，不等于产品发行裁剪 |
| 插件 | `platform_plugin.status`、`platform_tenant_plugin.enabled`、动态插件访问校验 | controller 仍会被扫描注册，缺少扫描阶段过滤 |
| 初始化 | 固定 `prepare_init_models` + 固定 JSON，空表导入 | 无 seed pack 和 profile 选择 |
| 前端 | 动态菜单来自后端，静态路由内置 | fastlink、dashboard、静态入口缺少 profile 控制 |
| 配置 | `.env` 可配置基础环境 | 缺少发行配置文件、解析器和前端下发接口 |

## 5. 核心概念

### 5.1 Distribution Profile

发行配置是一组声明，用于描述当前产品发行包启用哪些框架模块、插件、菜单、种子和前端入口。

建议命名：

```text
DISTRIBUTION_PROFILE=default
DISTRIBUTION_PROFILE=wms
DISTRIBUTION_PROFILE=mes
```

### 5.2 Module

模块指后端 API 模块、插件模块或前端模块命名空间，例如：

- `module_system`
- `module_platform`
- `module_monitor`
- `module_task`
- `module_generator`
- `module_ai`
- `module_example`
- `module_wms`

### 5.3 Seed Pack

Seed pack 指一组可独立加载的初始化数据。它可以包含菜单、套餐、插件、字典、参数、角色、演示数据等。

示例：

- `core`
- `platform`
- `monitor`
- `task`
- `ai`
- `generator`
- `example`
- `wms`
- `mes`

### 5.4 Static Route Group

前端静态入口分组，例如：

- `home`
- `dashboard`
- `fastlink`
- `pricing`
- `tutorial`
- `article`
- `fachat`
- `exception`

## 6. 配置文件建议

### 6.1 后端配置文件

建议位置：

```text
backend/app/distributions/default.toml
backend/app/distributions/wms.toml
backend/app/distributions/mes.toml
```

示例：

```toml
[distribution]
name = "wms"
title = "智慧仓储发行包"
description = "用于 WMS 产品的 FastapiAdmin 发行配置"

[modules]
enabled = [
  "module_system",
  "module_platform",
  "module_monitor",
  "module_task",
  "module_generator",
  "module_ai",
  "module_wms"
]
disabled = [
  "module_example"
]

[plugins]
enabled = [
  "module_task",
  "module_generator",
  "module_ai"
]
disabled = [
  "module_example"
]

[seed]
packs = [
  "core",
  "platform",
  "monitor",
  "task",
  "generator",
  "ai",
  "wms"
]

[frontend]
enabled_static_routes = [
  "home",
  "dashboard",
  "system",
  "platform"
]
disabled_static_routes = [
  "fastlink.pricing",
  "fastlink.article",
  "fastlink.tutorial"
]
```

### 6.2 环境变量

`.env.dev` / `.env.prod` 增加：

```env
DISTRIBUTION_PROFILE = "wms"
```

未配置时默认：

```env
DISTRIBUTION_PROFILE = "default"
```

## 7. 后端需求

### 7.1 配置解析服务

新增框架级服务，例如：

```text
backend/app/core/distribution.py
```

职责：

1. 读取 `settings.DISTRIBUTION_PROFILE`。
2. 加载对应 TOML 文件。
3. 校验配置结构。
4. 提供查询方法：
   - `is_module_enabled(code)`
   - `is_plugin_enabled(code)`
   - `get_seed_packs()`
   - `get_frontend_config()`
   - `get_enabled_modules()`
5. 启动日志输出当前发行配置。

### 7.2 动态插件扫描过滤

当前 `app/core/discover.py` 会扫描 `app/plugin/module_*/**/controller.py`。建议在扫描阶段接入发行配置：

1. 若 `module_example` 在 `disabled` 中，跳过该模块 controller。
2. 若设置了 `modules.enabled`，只扫描启用模块。
3. 跳过时记录日志，例如：

```text
⏭️  跳过插件模块 module_example：distribution profile disabled
```

注意：访问校验仍需保留，扫描过滤只是减少当前发行包暴露面。

### 7.3 初始化 seed pack

当前初始化逻辑位于 `backend/app/scripts/initialize.py`，依赖固定模型列表和固定 JSON 文件。

建议改造为：

```text
backend/app/scripts/seeds/core/*.json
backend/app/scripts/seeds/platform/*.json
backend/app/scripts/seeds/task/*.json
backend/app/scripts/seeds/wms/*.json
```

加载流程：

1. 根据 distribution 的 `seed.packs` 获取 pack 列表。
2. 按依赖顺序加载 pack。
3. 每个 pack 内声明模型、JSON、依赖和导入策略。
4. 保留现有“空表导入、已有数据跳过”的默认策略。

建议支持 seed manifest：

```toml
name = "wms"
depends = ["core", "platform"]

[[tables]]
model = "app.api.v1.module_platform.menu.model.MenuModel"
table = "platform_menu"
file = "platform_menu.json"
mode = "insert_if_empty"
recursive = true
```

### 7.4 菜单与套餐初始化

菜单、套餐、插件初始化需要支持 profile 差异：

1. `platform_menu.json` 可拆分为多个 seed pack。
2. `platform_package_menu.json` 可按发行包指定默认套餐菜单。
3. `platform_package_plugin.json` 可按发行包指定默认插件。
4. `platform_plugin.json` 只初始化当前发行包允许的插件。

不建议通过删除菜单记录来表达裁剪，应通过 profile seed 控制初始数据，通过状态字段支持运行时调整。

### 7.5 配置下发接口

建议新增或扩展公开配置接口，向前端返回发行配置摘要：

```json
{
  "distribution": {
    "profile": "wms",
    "enabledModules": ["module_system", "module_platform", "module_wms"],
    "disabledStaticRoutes": ["fastlink.pricing", "fastlink.article"]
  }
}
```

该接口不应泄露敏感信息，例如文件路径、内部环境变量、密钥。

## 8. 前端需求

### 8.1 静态路由裁剪

当前 `frontend/web/src/router/staticRoutes.ts` 包含登录、异常页、dashboard、fastlink、文章、定价、教程、AI 对话等静态入口。

建议增加发行配置过滤：

1. 启动时读取后端配置或本地构建配置。
2. 对静态路由按 route group 过滤。
3. 对 fastlink 子路由支持细粒度禁用。
4. 被禁用路由应无法通过地址栏访问，返回 404 或无权限页。

### 8.2 快捷入口和导航

以下入口应受发行配置控制：

- 快速入口 `fastEnter`
- 全局搜索中的静态路由结果
- dashboard 静态页签
- fastlink 页面
- 顶栏 AI/通知/设置等入口，如其依赖模块被关闭

### 8.3 前端本地兜底配置

当后端配置接口不可用时，前端应有默认配置：

```text
frontend/web/src/config/distribution/default.ts
```

但后端下发配置优先级更高，以保证前后端一致。

## 9. 权限关系

发行裁剪、套餐授权、角色权限、按钮权限的关系建议如下：

1. **发行裁剪**：决定当前产品发行包有哪些能力。
2. **套餐授权**：决定某租户可用哪些能力。
3. **角色菜单权限**：决定某角色可见哪些菜单。
4. **按钮/API 权限**：决定某用户可执行哪些操作。

最终可见菜单应满足：

```text
发行包启用
AND 菜单状态启用
AND 租户套餐包含
AND 用户角色授权
AND 前端静态入口未禁用
```

## 10. 日志与可观测性

启动时应输出：

1. 当前 `DISTRIBUTION_PROFILE`。
2. 已启用模块列表。
3. 已跳过模块列表。
4. 已加载 seed pack 列表。
5. 被跳过的 seed pack 和原因。
6. 前端配置摘要。

示例：

```text
✅ Distribution profile: wms
✅ Enabled modules: module_system,module_platform,module_wms
⏭️ Disabled modules: module_example
✅ Seed packs loaded: core,platform,wms
```

## 11. 兼容与迁移

首版应保证：

1. 未配置 `DISTRIBUTION_PROFILE` 时行为等同当前框架。
2. 现有 `backend/app/scripts/data/*.json` 可作为 `default` seed pack 兼容来源。
3. 现有菜单、套餐、插件表结构尽量不破坏。
4. 已有租户数据不因切换 profile 自动删除。
5. 如果 profile 移除了某菜单，只影响新初始化和可见性，不直接删除生产数据。

## 12. 验收标准

### 12.1 后端验收

1. 设置 `DISTRIBUTION_PROFILE=default`，框架行为与当前一致。
2. 设置 `DISTRIBUTION_PROFILE=wms`，后端启动日志显示 wms profile。
3. 被禁用的插件模块不参与动态扫描。
4. 初始化只加载 profile 声明的 seed pack。
5. 插件访问校验仍然生效。
6. Swagger 中不出现被扫描过滤的插件接口。

### 12.2 前端验收

1. 前端能读取发行配置。
2. 被禁用的静态路由不出现在菜单、快捷入口、全局搜索中。
3. 直接访问被禁用路由时不能进入页面。
4. 后端菜单、前端静态入口、角色权限的最终显示结果一致。

### 12.3 数据验收

1. 新库初始化后，菜单和套餐符合 profile 声明。
2. 已有数据库不因新增 profile 机制被误删数据。
3. seed pack 重复执行仍保持幂等或明确跳过。

## 13. 建议分阶段实现

### Phase 1：只读配置与日志

- 增加 `DISTRIBUTION_PROFILE`。
- 增加 TOML 解析。
- 启动时输出 profile 和配置摘要。
- 不改变现有行为。

### Phase 2：后端插件扫描过滤

- 在 `discover.py` 接入 module/plugin enable 判断。
- 验证禁用插件不出现在 Swagger。
- 保留访问校验。

### Phase 3：seed pack 改造

- 将现有 `scripts/data` 兼容为 `default` pack。
- 支持 profile 指定 seed packs。
- 支持菜单、套餐、插件数据按 pack 初始化。

### Phase 4：前端静态入口过滤

- 后端下发发行配置摘要。
- 前端过滤 static routes、fastlink、快捷入口、全局搜索。

### Phase 5：产品发行包落地

- 新增 `wms` profile 作为首个使用者。
- 后续 MES、CRM 按同一机制扩展。

## 14. 待评估问题

1. 配置文件用 TOML、YAML 还是 Python dict 更适合当前框架。
2. profile 文件放在框架仓库，还是允许产品仓库覆盖。
3. 是否需要支持 profile 继承，例如 `wms extends default`。
4. seed pack 是否需要支持版本号和迁移。
5. 前端静态路由过滤应以后端配置为准，还是构建期配置为准。
6. 插件禁用后是否仍允许超管在插件市场看到但不可安装。
7. 对已有租户切换 profile 时是否需要生成影响预览。

## 15. 对 WMS 的使用方式

WMS 只是该机制的一个使用者。WMS profile 不应写入框架核心逻辑，只提供声明文件和业务 seed pack：

```text
backend/app/distributions/wms.toml
backend/app/scripts/seeds/wms/
frontend/web/src/config/distribution/wms.ts
```

框架评估时应重点判断该机制是否也适用于 MES、CRM、SaaS 平台版和内部后台，而不是只满足 WMS 当前裁剪需求。
