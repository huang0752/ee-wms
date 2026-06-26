# WMS 前台能力保留评估

## 结论

WMS V1 前台只保留业务运行需要的入口：系统、平台、多租户基础、仓储业务、用户资料和租户品牌工作台。AI、任务、代码生成、租户分发财务、插件市场和通用演示仪表盘作为框架能力保留在后端和代码层，但不直接展示给 WMS 业务用户。

## 入口评估

| 入口 | V1 前台是否展示 | 处理方式 | 原因 |
|---|---|---|---|
| 仪表盘 | 否 | 禁用通用 `dashboard` route group | 框架示例仪表盘偏通用后台/营销数据；WMS 使用 `仓储管理 / 运营看板 / 仓储驾驶舱`。 |
| 代码管理 / 代码生成 | 否 | 禁用 `module-generator` route group | 开发工具，不属于仓储业务运行面。 |
| AI管理 | 否 | 禁用 `ai-chat` route group，关闭 `ai_assistant` feature flag | 模型、供应商 Key、调用参数属于平台/框架管理能力。 |
| 任务管理 | 否 | 禁用 `module-task` route group | 框架任务中心偏配置和调度管理，不等同于 WMS 作业任务。 |
| 套餐管理 | 否 | 通过 `[menu].disabled_paths` 隐藏 `/platform/package` | 多租户底座保留，但套餐设计和售卖不在 WMS V1 前台完成。 |
| 订单管理 | 否 | 隐藏 `/platform/order`，关闭 `tenant_billing` | 租户分发财务不在本系统完成。 |
| 发票管理 | 否 | 隐藏 `/platform/invoice`，关闭 `tenant_billing` | 发票和财务流程不属于 WMS 运行面。 |
| 支付页面 | 否 | 禁用 `payment` route group | 与隐藏的套餐/订单链路保持一致。 |
| 插件市场 | 否 | 隐藏 `/platform/plugin-market`，关闭 `plugin_market` | 第一版不开放插件安装/启停入口。 |
| 公告管理 | 否 | 隐藏 `/system/notice` | 第一版不做平台公告运营。 |
| 工单管理 | 否 | 隐藏 `/system/ticket` | 客服工单不属于 WMS 核心闭环。 |
| 租户管理、菜单管理、邮件管理、租户工作台 | 是 | 保留平台基础入口 | WMS 是多租户系统，需要租户、菜单、邮件和品牌配置能力。 |
| 仓储管理 | 是 | 保留并重组二级目录 | 业务主入口，按作业域拆成运营看板、基础资料、入库作业、出库作业、库存作业、分析追溯、试用工具。 |

## 保留边界

后端仍启用 `module_ai`、`module_task`、`module_generator`，用于框架维护、后续复用和能力验证。WMS 不直接暴露这些管理页。`platform` route group 继续启用，但通过精确菜单路径隐藏租户分发财务和插件市场，避免把平台管理整体做窄。

后续如果需要 AI 或任务能力，应在 `module_wms` 下建立业务入口，例如：

- `module_wms/assistant`: 库存预警说明、出入库异常解释、补货建议。
- `module_wms/work`: 入库作业、出库作业、盘点任务、待办处理。
- `module_wms/import`: 批量导入、试用数据生成、长任务进度。

这些页面可以复用框架服务，但权限、菜单和交互应使用 `module_wms:<resource>:<action>`，避免把框架管理入口直接给业务用户。

## 当前装配要求

- `enabled_route_groups` 不包含 `ai-chat`、`module-task`、`module-generator`。
- `enabled_route_groups` 不包含通用 `dashboard` 和 `payment`。
- `disabled_route_groups` 包含 `ai-chat`、`dashboard`、`module-task`、`module-generator`、`payment`。
- `[menu].disabled_paths` 包含 `/platform/package`、`/platform/order`、`/platform/invoice`、`/platform/plugin-market`、`/system/notice`、`/system/ticket`。
- `featureFlags.aiAssistant = false`。
- `featureFlags.tenantBilling = false`，租户工作台隐藏套餐价格、近期订单、选购套餐、我的订单和支付跳转。
- 测试必须覆盖 `AI管理`、`任务管理`、`代码管理`、租户分发财务菜单在 WMS 菜单中过滤。
