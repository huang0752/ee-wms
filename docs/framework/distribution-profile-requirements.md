# FastapiAdmin 产品精简与能力装配机制规划文档

## 1. 背景

FastapiAdmin 当前已经具备用户、角色、权限、菜单、租户、套餐、插件、动态路由、代码生成、任务、通知、AI、`fa-*` 组件等框架能力。它适合作为多个产品的后台底座，例如智慧仓储、MES、ERP、CRM、内部运营后台、SaaS 管理平台等。

但当前底座同时包含较多演示内容和可选能力。新产品启动时通常需要做两类事情：

1. **从模板变成干净开发底座**：移除文章、定价、教程、示例页面、Mock、演示 seed、示例上传等内容。
2. **按产品选择能力组合**：选择启用哪些后端插件、前端入口、初始化数据包和功能开关。

如果直接用 `DISTRIBUTION_PROFILE=wms` 这类业务 profile，会把框架做窄。框架不应该理解“什么是 WMS、ERP、MES”，而应该提供通用的精简和能力装配机制，由产品仓库自己声明需要哪些能力。

Art Design Pro 的“精简版”思路值得借鉴：它提供一次性清理脚本，把演示页面、Mock、多语言演示数据、示例样式等清理掉，让项目进入干净开发状态。FastapiAdmin 也应提供类似能力，但还需要再增加一层长期可维护的产品能力装配。

## 2. 总体判断

本机制不应叫 `Distribution Profile = wms`。推荐拆成两套概念：

1. **Product Starter Preset（产品起步预设）**
   - 一次性初始化/清理动作。
   - 目标是把模板项目变成干净底座。
   - 类似 Art Design Pro 的 `pnpm clean:dev`。

2. **Capability Assembly（能力装配清单）**
   - 运行时或初始化时读取的能力声明。
   - 目标是声明当前产品启用哪些核心模块、插件、前端路由、seed pack 和功能开关。
   - 不写死 WMS、ERP、MES 等业务类型。

WMS、ERP、MES 只能作为产品仓库里的具体装配文件名或业务模块名存在，不能进入框架核心判断逻辑。

## 3. 目标

### 3.1 核心目标

建立一套通用机制，使 FastapiAdmin 可以作为多个产品的底座，并支持：

1. 一键清理演示内容，得到可开发的干净项目。
2. 按能力清单启用或禁用后端插件扫描。
3. 按能力清单控制前端静态路由、快捷入口、全局搜索入口。
4. 按能力清单选择初始化 seed pack。
5. 保留核心权限、租户、套餐、菜单等运行时安全边界。
6. 让产品仓库通过配置组合能力，而不是修改框架核心。

### 3.2 非目标

1. 不在框架核心写死 WMS、ERP、MES、CRM。
2. 不要求物理删除未启用模块代码。
3. 不用能力装配替代 RBAC、租户隔离、套餐授权或按钮权限。
4. 不要求首版实现前端 bundle 级 tree-shaking。
5. 不要求首版实现可视化插件市场或在线能力编排器。
6. 不自动删除已有生产数据。

## 4. 设计原则

1. **业务无关**：框架只识别 `core_modules`、`plugin_modules`、`route_groups`、`seed_packs`、`feature_flags` 等通用概念。
2. **默认兼容**：未配置时保持当前完整框架行为。
3. **前后端同源**：前端路由和后端模块使用同一份能力摘要或同源配置生成。
4. **安全后置校验**：前端隐藏只是体验优化，API 权限和租户隔离仍以后端为准。
5. **一次性精简与运行时装配分离**：清理演示内容和控制运行能力不能混在一个 `profile` 里。
6. **可观测**：启动、初始化、路由注册时输出当前装配状态和跳过原因。
7. **可迁移**：seed pack 和能力清单需要支持未来版本演进。

## 5. 核心概念

### 5.1 Product Starter Preset

产品起步预设是一次性脚本动作，用于清理模板项目中的演示内容。

建议预设：

| 预设 | 用途 |
|---|---|
| `full-demo` | 保留全部演示内容，适合框架展示和学习 |
| `minimal` | 只保留登录、首页、系统管理、权限、租户、设置等必要底座 |
| `business-admin` | 保留常见业务后台底座，例如任务、通知、文件、字典、审计 |
| `saas-admin` | 保留租户、套餐、插件、平台管理等 SaaS 底座 |

建议命令：

```bash
pnpm clean:starter
uv run app/scripts/apply_starter.py --preset minimal
uv run app/scripts/apply_starter.py --preset business-admin
```

该脚本可以删除或重写：

- 演示页面
- 演示菜单
- 示例 seed
- Mock 数据
- 示例上传文件
- 示例文档入口
- 定价、教程、文章、快捷链接等模板展示内容

精简脚本是破坏性操作，必须要求用户确认，并建议先提交或备份。

### 5.2 Capability Assembly

能力装配清单是产品运行和初始化时使用的声明文件。它表达“当前产品需要哪些能力”，但不表达“当前产品是什么行业”。

建议命名：

```env
APP_ASSEMBLY=default
APP_ASSEMBLY_FILE=backend/app/assemblies/default.toml
```

不建议：

```env
DISTRIBUTION_PROFILE=wms
```

产品仓库可以提供自己的清单，例如：

```text
backend/app/assemblies/default.toml
backend/app/assemblies/minimal.toml
backend/app/assemblies/smart-warehouse.toml
backend/app/assemblies/equipment-mes.toml
backend/app/assemblies/light-erp.toml
```

其中 `smart-warehouse` 是产品仓库自己的装配文件名，不是框架核心枚举。

### 5.3 Core Module

核心模块是底座必须存在的能力，例如：

- `auth`
- `tenant`
- `user`
- `role`
- `permission`
- `menu`
- `settings`
- `audit`

核心模块原则上不允许通过普通装配清单关闭。如果确实要关闭，应进入更高风险的定制模式。

### 5.4 Plugin Module

插件模块是可以按产品启用或关闭的后端能力，例如：

- `module_task`
- `module_generator`
- `module_ai`
- `module_example`
- `module_inventory`
- `module_workflow`

插件模块应支持：

1. 是否扫描注册 controller。
2. 是否初始化插件表。
3. 是否生成默认菜单和权限。
4. 是否出现在前端入口。

### 5.5 Route Group

前端静态路由按组声明，例如：

- `dashboard`
- `system`
- `platform`
- `user-profile`
- `pricing`
- `article`
- `tutorial`
- `ai-chat`
- `exception`

能力装配可以控制某个 route group 是否可见、可访问。

### 5.6 Seed Pack

Seed pack 是一组初始化数据。它可以包含菜单、角色、权限、套餐、插件、字典、参数、演示数据等。

示例：

- `core`
- `tenant_base`
- `platform_base`
- `task`
- `notification`
- `ai`
- `inventory_base`
- `demo`

产品应组合 seed pack，而不是复制修改一整套大 JSON。

## 6. 配置模型

### 6.1 装配文件位置

建议后端为主，前端通过接口读取摘要：

```text
backend/app/assemblies/default.toml
backend/app/assemblies/minimal.toml
backend/app/assemblies/business-admin.toml
```

产品仓库可追加：

```text
backend/app/assemblies/smart-warehouse.toml
backend/app/assemblies/equipment-mes.toml
backend/app/assemblies/light-erp.toml
```

### 6.2 示例配置

```toml
[assembly]
name = "smart-warehouse"
title = "智慧仓储产品装配"
description = "由产品仓库维护，框架只按能力清单执行"

[core]
required = [
  "auth",
  "tenant",
  "user",
  "role",
  "permission",
  "menu",
  "settings",
  "audit"
]

[backend]
enabled_plugins = [
  "module_task",
  "module_notification",
  "module_inventory",
  "module_workflow"
]

disabled_plugins = [
  "module_example",
  "module_article",
  "module_pricing",
  "module_tutorial"
]

[frontend]
enabled_route_groups = [
  "dashboard",
  "system",
  "platform",
  "user-profile",
  "inventory",
  "workflow",
  "exception"
]

disabled_route_groups = [
  "pricing",
  "article",
  "tutorial"
]

[seed]
packs = [
  "core",
  "tenant_base",
  "platform_base",
  "task",
  "notification",
  "inventory_base"
]

[features]
flags = {
  ai_assistant = false,
  plugin_market = true,
  tenant_package = true,
  demo_content = false
}
```

### 6.3 命名规则

1. `APP_ASSEMBLY` 表示当前使用哪个能力装配。
2. `APP_ASSEMBLY_FILE` 可选，用于指定文件路径。
3. `APP_STARTER_PRESET` 只用于一次性精简脚本，不参与运行时权限判断。
4. 不使用 `wms`、`erp`、`mes` 作为框架内置枚举。

## 7. 后端规划

### 7.1 配置解析服务

新增：

```text
backend/app/core/assembly.py
```

职责：

1. 读取 `APP_ASSEMBLY` 和 `APP_ASSEMBLY_FILE`。
2. 加载 TOML 配置。
3. 校验字段类型和冲突。
4. 提供查询方法：
   - `get_current_assembly()`
   - `is_core_required(code)`
   - `is_plugin_enabled(code)`
   - `is_route_group_enabled(code)`
   - `get_seed_packs()`
   - `get_feature_flags()`
   - `get_frontend_summary()`
5. 启动时输出当前装配摘要。

### 7.2 后端插件扫描过滤

当前动态插件扫描在：

```text
backend/app/core/discover.py
```

规划改造：

1. 扫描 `app/plugin/module_*` 时识别 `top_module`。
2. 如果 `top_module` 在 `disabled_plugins` 中，跳过。
3. 如果配置了 `enabled_plugins`，只扫描启用列表中的插件。
4. 对跳过模块输出日志。
5. 保留现有运行时插件、租户、权限校验。

示例日志：

```text
Assembly: smart-warehouse
Enabled plugin modules: module_task,module_inventory,module_workflow
Skipped plugin module: module_example, reason=assembly disabled
```

### 7.3 API 暴露边界

插件被装配禁用时，应满足：

1. controller 不注册。
2. Swagger 不出现该插件 API。
3. 前端菜单不出现对应入口。
4. 即使用户猜测 URL，也无法访问已禁用插件 API。

但以下后端安全校验仍必须保留：

1. 登录鉴权。
2. 角色权限。
3. 菜单权限。
4. 租户隔离。
5. 套餐/插件授权。

能力装配是产品可用性边界，不是唯一安全边界。

### 7.4 配置摘要接口

新增或扩展公开配置接口，例如：

```text
GET /api/v1/system/config/info
```

返回：

```json
{
  "assembly": {
    "name": "smart-warehouse",
    "enabledRouteGroups": ["dashboard", "system", "user-profile", "inventory"],
    "disabledRouteGroups": ["pricing", "article", "tutorial"],
    "featureFlags": {
      "aiAssistant": false,
      "pluginMarket": true,
      "tenantPackage": true
    }
  }
}
```

注意：

1. 不下发配置文件路径。
2. 不下发环境变量原值。
3. 不下发数据库连接、密钥、内部路径等敏感信息。

### 7.5 启动诊断

后端启动时输出：

1. 当前 assembly 名称。
2. 配置文件来源。
3. 启用插件列表。
4. 禁用插件列表。
5. seed pack 列表。
6. feature flags 摘要。
7. 配置冲突或未知模块告警。

未知模块默认策略建议：

| 场景 | 策略 |
|---|---|
| `disabled_plugins` 指向不存在模块 | warning，不阻断启动 |
| `enabled_plugins` 指向不存在模块 | warning，不阻断启动 |
| seed pack 不存在 | error，阻断初始化，不阻断普通启动 |
| core required 缺失 | error，阻断启动 |

## 8. Seed Pack 规划

### 8.1 目录结构

建议：

```text
backend/app/scripts/seeds/
  core/
    seed.toml
    platform_menu.json
    platform_role.json
  tenant_base/
    seed.toml
    platform_package.json
    platform_package_menu.json
  task/
    seed.toml
    platform_plugin.json
    platform_menu.json
  inventory_base/
    seed.toml
    platform_menu.json
    system_dict_type.json
```

### 8.2 Seed Manifest

每个 seed pack 维护自己的 `seed.toml`：

```toml
name = "inventory_base"
depends = ["core", "tenant_base"]

[[tables]]
model = "app.api.v1.module_platform.menu.model.MenuModel"
table = "platform_menu"
file = "platform_menu.json"
mode = "insert_if_empty"
recursive = true

[[tables]]
model = "app.api.v1.module_system.dict.model.DictTypeModel"
table = "system_dict_type"
file = "system_dict_type.json"
mode = "upsert_by_code"
```

### 8.3 导入策略

首版支持：

| mode | 含义 |
|---|---|
| `insert_if_empty` | 目标表为空才导入 |
| `append_only` | 只追加不存在的数据 |
| `upsert_by_code` | 按唯一 code 更新或插入 |
| `skip` | 声明但不导入，用于占位 |

暂缓支持：

1. 复杂数据迁移 DSL。
2. 在线回滚。
3. 按租户差异化 seed。
4. seed pack 图形化管理。

### 8.4 与现有初始化兼容

当前 `backend/app/scripts/initialize.py` 使用固定模型列表和固定 JSON。迁移策略：

1. 保留当前导入逻辑作为 `default` 行为。
2. 将现有 JSON 逐步迁移到 `seeds/core`、`seeds/platform_base` 等 pack。
3. 未配置 assembly 时仍走当前兼容路径。
4. 配置 assembly 后走 seed pack 路径。
5. 已有数据库不自动删除任何数据。

## 9. 前端规划

### 9.1 静态路由分组

当前前端静态路由应增加 route group 元数据：

```ts
meta: {
  title: "xxx",
  routeGroup: "user-profile"
}
```

或在路由定义外维护映射：

```ts
const routeGroupMap = {
  "/fastlink/profile": "user-profile",
  "/fastlink/pricing": "pricing",
  "/fastlink/article": "article",
  "/dashboard": "dashboard"
}
```

`/fastlink` 父路由只作为静态容器，不应绑定可裁剪 route group。否则关闭营销页、教程页时会误伤用户资料页等必需入口。

推荐优先使用 `meta.routeGroup`，便于局部判断。

### 9.2 配置加载流程

前端启动流程：

1. 加载本地默认 assembly summary。
2. 请求后端 `/config/info`。
3. 后端成功返回后覆盖本地默认值。
4. 根据 route group 过滤静态路由。
5. 根据 feature flags 控制快捷入口、顶部入口、全局搜索入口。

后端不可用时：

1. 登录页、异常页、基础布局仍可加载。
2. 使用本地默认配置。
3. 控制台输出 warning。

### 9.3 需要受控的前端入口

1. `staticRoutes.ts` 中的静态路由。
2. fastlink 子页面。
3. dashboard 子页签。
4. 快捷入口。
5. 全局搜索结果。
6. 顶栏 AI、通知、设置等入口。
7. 任何仅靠前端静态定义出现的模板展示入口。

### 9.4 直接访问处理

被禁用 route group 应满足：

1. 不出现在菜单中。
2. 不出现在全局搜索中。
3. 直接访问时进入 404 或无权限页。
4. 如果后端 API 也禁用，页面不应发出无意义请求。

## 10. 权限与多租户关系

能力装配、套餐授权、角色权限、按钮权限、租户隔离是不同层级：

| 层级 | 作用 |
|---|---|
| 能力装配 | 当前产品整体有哪些能力 |
| 套餐授权 | 当前租户购买或拥有哪些能力 |
| 菜单权限 | 当前角色可见哪些页面 |
| 按钮/API 权限 | 当前用户可执行哪些动作 |
| 租户隔离 | 当前用户只能访问本租户数据 |

最终可用能力应满足：

```text
产品装配启用
AND 后端插件已注册
AND 菜单状态启用
AND 租户套餐允许
AND 角色菜单授权
AND 按钮/API 权限允许
AND 数据租户隔离通过
```

不能因为前端隐藏了入口，就跳过后端权限校验。

## 11. 产品仓库使用方式

推荐产品仓库只维护以下内容：

```text
backend/app/assemblies/smart-warehouse.toml
backend/app/scripts/seeds/inventory_base/
backend/app/plugin/module_inventory/
frontend/web/src/views/inventory/
frontend/web/src/router/business/inventory.ts
```

框架仓库维护：

```text
backend/app/core/assembly.py
backend/app/core/discover.py
backend/app/scripts/apply_starter.py
backend/app/scripts/seed_loader.py
frontend/web/src/config/assembly/
frontend/web/src/router/filterByAssembly.ts
```

产品仓库不应修改框架核心来表达“我是 WMS”。它只声明自己需要库存、库位、出入库、盘点、通知、工作流等能力。

## 12. 起步预设规划

### 12.1 `full-demo`

保留全部内容，用于框架展示、二次开发参考、文档截图。

### 12.2 `minimal`

保留：

- 登录/退出
- 首页/工作台
- 用户
- 角色
- 权限
- 菜单
- 租户基础
- 系统设置
- 审计日志
- 异常页

清理：

- 文章
- 定价
- 教程
- 示例业务
- 演示上传
- fastlink 示例入口中的营销页、文章页、教程页和 AI 聊天页
- demo seed

### 12.3 `business-admin`

在 `minimal` 基础上保留：

- 字典
- 文件
- 通知
- 任务
- 代码生成
- 操作日志
- 常见业务导航骨架

### 12.4 `saas-admin`

在 `business-admin` 基础上保留：

- 租户套餐
- 平台套餐菜单
- 平台插件
- 租户插件启停
- 计费/版本预留接口

## 13. 实施阶段

### Phase 0：概念收敛与文档改造

目标：

1. 将 `Distribution Profile=wms` 改为 `Product Starter + Capability Assembly`。
2. 明确 WMS/ERP/MES 不进入框架核心。
3. 明确一次性精简和运行时装配的边界。

交付：

- 本规划文档。
- 命名规范。
- MVP 范围确认。

### Phase 1：只读能力装配

目标：

1. 新增 `APP_ASSEMBLY` 配置。
2. 新增 TOML 解析服务。
3. 启动时输出 assembly 摘要。
4. 不改变现有运行行为。

交付：

- `backend/app/core/assembly.py`
- `backend/app/assemblies/default.toml`
- 单元测试：配置加载、默认值、冲突校验。

### Phase 2：后端插件扫描过滤

目标：

1. 在 `discover.py` 接入 assembly。
2. 禁用插件不注册 controller。
3. Swagger 不出现禁用插件接口。
4. 保留运行时权限校验。

交付：

- 动态扫描过滤。
- 启动日志。
- 测试覆盖启用/禁用列表。

### Phase 3：前端 route group 过滤

目标：

1. 给静态路由补充 route group。
2. 新增前端 assembly summary store。
3. 根据后端配置过滤静态路由、快捷入口、全局搜索。
4. 后端不可用时有本地默认兜底。

交付：

- `frontend/web/src/config/assembly/default.ts`
- `frontend/web/src/router/filterByAssembly.ts`
- 静态路由元数据改造。
- 前端构建验证。

### Phase 4：Starter Preset 精简脚本

目标：

1. 提供类似 Art Design Pro `clean:dev` 的精简脚本。
2. 支持 `minimal`、`business-admin`、`saas-admin`。
3. 执行前展示删除清单并要求确认。
4. 不自动提交，不静默删除。

交付：

- `backend/app/scripts/apply_starter.py`
- `frontend/web/scripts/clean-starter.ts` 或统一 Node/Python 脚本。
- `pnpm clean:starter`
- 使用文档。

### Phase 5：Seed Pack 改造

目标：

1. 兼容当前初始化 JSON。
2. 支持 seed pack manifest。
3. 支持 assembly 指定 seed packs。
4. 支持幂等导入策略。

交付：

- `backend/app/scripts/seed_loader.py`
- `backend/app/scripts/seeds/core`
- `backend/app/scripts/seeds/tenant_base`
- `backend/app/scripts/seeds/platform_base`
- 初始化脚本适配。

### Phase 6：产品样例落地

目标：

1. 选一个真实产品仓库作为样例，例如智慧仓储。
2. 不在框架核心写死 `wms`。
3. 产品只提供自己的 assembly、业务插件、业务 seed、业务前端页面。

交付：

- `smart-warehouse.toml`
- `module_inventory`
- `inventory_base` seed pack
- 前端 inventory route group
- 初始化和启动验证记录。

### Phase 7：治理与长期演进

目标：

1. 支持 assembly 版本号。
2. 支持影响预览。
3. 支持配置校验命令。
4. 支持文档化产品装配模板。

暂缓：

- 在线可视化能力编排。
- 自动回滚生产菜单和权限。
- 前端构建期 tree-shaking。
- 复杂 profile 继承。

## 14. 验收标准

### 14.1 默认兼容

1. 未设置 `APP_ASSEMBLY` 时，系统行为与当前一致。
2. 默认菜单、插件、seed、静态路由不被意外裁剪。
3. 现有测试不因默认装配机制失败。

### 14.2 后端

1. 设置 assembly 后启动日志显示当前装配。
2. 禁用插件不参与 controller 扫描。
3. Swagger 不出现禁用插件 API。
4. 权限、租户、套餐校验仍然生效。
5. 未知插件给出 warning。
6. core required 缺失时启动失败或明确报错。

### 14.3 前端

1. 能读取后端 assembly summary。
2. 被禁用 route group 不出现在菜单、快捷入口、全局搜索。
3. 直接访问被禁用静态路由不能进入页面。
4. 后端不可用时有默认兜底，不白屏。

### 14.4 Seed

1. assembly 指定 seed packs 后，只导入指定 pack。
2. 重复执行初始化不产生重复数据。
3. 已有数据库不会被自动删除数据。
4. 缺失 seed pack 时初始化失败并给出明确错误。

### 14.5 Starter

1. 精简脚本执行前展示将删除/重写的文件和数据范围。
2. 用户输入确认后才执行。
3. `minimal` 能得到干净底座。
4. `business-admin` 和 `saas-admin` 能保留对应能力。
5. 精简后前后端仍可启动和构建。

## 15. 风险与控制

| 风险 | 控制方式 |
|---|---|
| 把框架做成 WMS 特化 | 框架只理解能力，不理解行业 |
| 前端隐藏被误当安全 | 后端权限、租户、套餐校验必须保留 |
| seed pack 改造过大 | 先兼容旧初始化，再逐步拆包 |
| 清理脚本误删 | 必须确认、输出清单、建议先提交 |
| 配置过度复杂 | 首版不做继承、不做在线编排 |
| 产品仓库改核心 | 明确框架核心与产品装配边界 |

## 16. 推荐 MVP 范围

第一轮不要只做“第一步”，但也不要一次性做满所有长期能力。推荐 MVP 覆盖完整闭环：

1. `APP_ASSEMBLY` 只读配置。
2. 后端插件扫描过滤。
3. 前端静态 route group 过滤。
4. 简单 seed pack 选择。
5. `minimal` starter 精简脚本。
6. 文档和验收清单。

暂不做：

1. assembly 继承。
2. seed 版本迁移。
3. 在线影响预览。
4. 可视化能力市场。
5. 前端 bundle 级裁剪。

## 17. 结论

当前场景有必要借鉴 Art Design Pro 的精简版，但不能只做一个 `clean:dev`，也不能把 `DISTRIBUTION_PROFILE=wms` 作为框架方向。

正确方向是：

1. 用 **Product Starter Preset** 解决“从模板到干净底座”的一次性问题。
2. 用 **Capability Assembly** 解决“不同产品选择不同能力”的长期问题。
3. 框架保持业务无关，产品仓库声明业务能力组合。
4. WMS、ERP、MES 都只是装配清单和业务模块的消费者，不是框架核心概念。
