# WMS V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build EE WMS V1 as an extensible warehouse product on top of the latest FastapiAdmin framework, starting with a correct inventory ledger and then layering inbound, outbound, traceability, dashboards, and demo data.

**Architecture:** WMS is a product module inside the `ee-wms` repository, not a generic framework plugin. Reusable platform capabilities stay in FastapiAdmin framework; WMS owns warehouse domain models, stock rules, APIs, pages, seed data, and demo generators. Inventory correctness is centered on immutable stock flows plus summarized balances.

**Tech Stack:** FastAPI, SQLAlchemy 2, Pydantic, Alembic-style initialization scripts, PostgreSQL, Redis, Vue 3, Vite, TypeScript, Pinia, Element Plus, `fa-*` components, Vitest, pytest.

---

## 1. Product Boundaries

WMS must use these namespaces consistently:

| Area | Namespace |
|---|---|
| Backend APIs | `backend/app/api/v1/module_wms/` |
| Frontend views | `frontend/web/src/views/module_wms/` |
| Frontend API clients | `frontend/web/src/api/module_wms/` |
| Permissions | `module_wms:<resource>:<action>` |
| Product assembly | `backend/app/assemblies/wms.toml` |
| Seed pack | `backend/app/scripts/seeds/wms/seed.toml` |
| Demo data module | `module="wms"` |

Do not add WMS business logic to `module_system`, `module_platform`, or framework plugin modules unless the capability is reusable by MES/CRM/other products.

## 1.1 V1 Simplification Decisions

V1 must stay simple while preserving extension points:

| Decision | V1 Implementation | Extension Point |
|---|---|---|
| SN management | Batch-first inventory. `sn_code` is nullable and not part of required workflows. | Enable SN-specific pages and unique stock records later. |
| PDA | H5/responsive scan pages and keyboard scanner input. No native app. | Reuse the same API contracts from UniApp/App later. |
| IQC | Lightweight WMS inspection task and result judgment. | Sync to MES quality module through external reference fields later. |
| ERP/MES | Manual entry, Excel import, and stable API contracts. No live automatic integration in V1. | Add idempotent REST/message sync later. |
| Approval | Status machine + button permission + operation log. No workflow engine in V1. | Keep `workflow_instance_id` for later workflow integration. |

## 2. Domain Model Layers

### 2.1 Master Data

Master data is editable, tenant-scoped, and mostly CRUD:

- `WmsWarehouse`: warehouse code, name, type, manager, `dept_id`, status.
- `WmsZone`: warehouse area/zone, usage, status.
- `WmsLocation`: physical location, capacity, category constraints, mix rules, status.
- `WmsMaterial`: material code, name, spec, unit, category, batch flag, nullable SN flag, safety stock.
- `WmsSupplier`: supplier code, name, contact, status.
- `WmsCustomer`: customer code, name, contact, status.
- `WmsBarcodeRule`: rule object type, prefix, segment strategy, enabled status.

### 2.2 Inventory Ledger

Inventory data must be append-first:

- `WmsStockBatch`: batch-first inventory unit with nullable `sn_code`, status, and source.
- `WmsStockBalance`: summarized quantity by material, warehouse, location, batch, status.
- `WmsStockFlow`: immutable stock movement record.
- `WmsStockLock`: reserved quantity for outbound or production issue.
- `WmsTraceLink`: graph relation between batch, order, inspection, inbound, outbound, and production references.

Rule: every quantity mutation writes `WmsStockFlow` first inside the transaction, then updates `WmsStockBalance`. Direct balance edits are only allowed through an audited adjustment service.

### 2.3 Business Documents

Documents coordinate workflow and reference the ledger:

- Arrival: `WmsArrivalOrder`, `WmsArrivalLine`.
- Inspection: `WmsInspectionTask`, `WmsInspectionLine`.
- Inbound: `WmsInboundOrder`, `WmsInboundLine`.
- Outbound: `WmsOutboundOrder`, `WmsOutboundLine`.
- Production issue: `WmsIssueOrder`, `WmsIssueLine`.
- Transfer: `WmsTransferOrder`, `WmsTransferLine`.
- Stock check: `WmsStockCheckOrder`, `WmsStockCheckLine`.
- Warning: `WmsStockWarning`.

All business documents should include optional integration fields from V1:

- `external_source`: `manual`, `excel`, `erp`, `mes`, `pda`, or future source code.
- `external_id`: external system primary key.
- `external_no`: external business number.
- `sync_status`: `not_required`, `pending`, `synced`, `failed`.
- `workflow_instance_id`: nullable future workflow reference.

## 3. Status And Quantity Rules

### 3.1 Stock Status

| Status | Meaning | Can outbound | Can lock | Can count |
|---|---|---:|---:|---:|
| `pending_inspection` | received but not judged | no | no | yes |
| `available` | usable inventory | yes | yes | yes |
| `locked` | reserved by document | no for other docs | already locked | yes |
| `frozen` | quality/manual hold | no | no | yes |
| `defective` | nonconforming inventory | no | no | yes |
| `shipped` | historical shipped batch | no | no | no |

### 3.2 Quantity Fields

`WmsStockBalance` stores:

- `quantity`: physical quantity.
- `available_qty`: quantity that can be used.
- `locked_qty`: reserved quantity.
- `frozen_qty`: frozen quantity.
- `pending_qty`: pending inspection quantity.

Invariant:

```text
quantity = available_qty + locked_qty + frozen_qty + pending_qty + defective_qty
```

### 3.3 Service Rules

All inventory services must enforce:

1. No outbound from `pending_inspection`, `frozen`, or `defective`.
2. No double reservation of the same quantity.
3. FIFO recommendation ignores frozen, pending, defective, and locked quantities.
4. Stock check does not update official balance until audit.
5. Demo data cleanup only deletes rows with matching `tenant_id`, `is_demo = true`, and `demo_batch_id`.

## 4. Menu And Permission Plan

Use `/module-wms` as the dynamic menu root. The framework assembly derives menu route groups from the first route segment, so all WMS menu routes must stay under `/module-wms/...` and use the enabled `module-wms` route group. Do not create unrelated top-level route groups such as `wms-dashboard` unless the assembly and frontend route filtering are updated together.

Use these WMS menus:

| Menu | Route | Permission |
|---|---|---|
| 仓储管理 | `/module-wms` | directory only |
| 仓储驾驶舱 | `/module-wms/dashboard` | `module_wms:dashboard:query` |
| 仓储基础 | `/module-wms/master` | directory only |
| 到货与检验 | `/module-wms/arrival` | directory only |
| 入库管理 | `/module-wms/inbound` | directory only |
| 出库管理 | `/module-wms/outbound` | directory only |
| 库存管理 | `/module-wms/stock` | directory only |
| 预警与分析 | `/module-wms/warning` | directory only |
| 仓储追溯 | `/module-wms/trace` | `module_wms:trace:query` |
| 试用数据 | `/module-wms/demo` | `module_wms:demo:init` |

V1 master data currently uses the shared `module_wms:master:query/create/update/delete` permissions for the unified master-data entry. Workflow pages should follow resource-specific actions such as `query/create/update/delete/import/export/confirm/cancel/audit/freeze/unfreeze/print` when they are implemented.

## 5. Product Assembly

Current `backend/app/assemblies/wms.toml` is already created and uses the current framework assembly schema:

```toml
[assembly]
name = "wms"
title = "EE WMS 装配"
description = "EE WMS 产品运行态装配：保留后台基础、任务、AI、代码生成与行业样例能力，裁剪演示和营销入口。"

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
  "module-wms",
  "user-profile",
  "payment",
  "workspace",
  "outside",
  "exception"
]
disabled_route_groups = ["pricing", "article", "tutorial", "changelog"]

[seed]
packs = ["wms"]

[features]
flags = { ai_assistant = true, plugin_market = false, tenant_package = true, demo_content = false, fast_enter = true, wms_demo_data = true }
```

Local development already uses the WMS assembly. The WMS seed pack depends on `business-admin` and appends product-specific seed files after framework seed packs; do not copy WMS menus into framework seed JSON.

## 6. Development Phases

### Phase 0: Planning, Product Setup, And Visible Subtraction

**Outcome:** WMS has a tracked plan, current assembly schema, visible framework-demo subtraction, initial seed pack, WMS menu, and module skeleton.

**Files:**
- Existing: `backend/app/assemblies/wms.toml`
- Existing: `backend/app/scripts/seeds/wms/seed.toml`
- Create/maintain: `backend/app/scripts/seeds/wms/platform_menu.json`
- Create/maintain: `backend/app/api/v1/module_wms/`
- Create/maintain: `frontend/web/src/api/module_wms/`
- Create/maintain: `frontend/web/src/views/module_wms/`

- [x] Create the WMS assembly file from section 5.
- [x] Keep visible subtraction in assembly and feature flags; do not physically delete framework source.
- [x] Hide FastapiAdmin demo/marketing links behind `demoContent` or WMS config.
- [x] Create WMS backend and frontend module directories.
- [x] Create seed pack and product menu append file.
- [ ] Verify WMS menu appears for superadmin after database initialization.
- [ ] Run `cd backend && uv run pytest tests/test_assembly.py -q`.
- [ ] Run `cd frontend/web && corepack pnpm run type-check`.
- [ ] Commit: `chore: 收口WMS产品减法与模块空壳`.

### Phase 1: Master Data Foundation

**Outcome:** Warehouse, zone, location, material, supplier, customer, and barcode rules have backend CRUD, menu seed, and frontend list/forms.

**Files:**
- Created under `backend/app/api/v1/module_wms/master/`: `model.py`, `schema.py`, `crud.py`, `service.py`, `controller.py`.
- Created `backend/tests/test_wms_master.py`.
- Created `frontend/web/src/api/module_wms/master.ts`.
- Created unified page `frontend/web/src/views/module_wms/master/index.vue`.

- [x] Write pytest cases for CRUD creation, duplicate code validation, and required barcode fields.
- [x] Implement SQLAlchemy models with `TenantMixin`, `UserMixin`, `dept_id`, `is_demo`, `demo_batch_id`.
- [x] Implement services with code uniqueness per tenant.
- [x] Add menu seed for master data page and buttons.
- [x] Build first frontend page for unified master-data CRUD.
- [x] Keep SN fields nullable and behind simple switches; no SN-only workflows in this phase.
- [x] Run `cd backend && uv run pytest tests/test_wms_master.py tests/test_assembly.py -q`.
- [x] Run `cd frontend/web && corepack pnpm run type-check`.
- [ ] Commit: `feat: 增加WMS仓储基础资料`.

### Phase 2: Inventory Ledger Core

**Outcome:** Stock batch, balance, flow, lock, and trace link services can create, lock, release, freeze, unfreeze, and query inventory.

**Files:**
- Create `backend/app/api/v1/module_wms/stock/model.py`.
- Create `backend/app/api/v1/module_wms/stock/ledger_service.py`.
- Create `backend/app/api/v1/module_wms/stock/recommend_service.py`.
- Create `backend/tests/test_wms_stock_ledger.py`.
- Create `frontend/web/src/api/module_wms/stock.ts`.
- Create `frontend/web/src/views/module_wms/stock/`.

- [x] Write tests for inbound flow creating balance.
- [x] Write tests for lock preventing double allocation.
- [x] Write tests for frozen/pending/defective stock excluded from outbound recommendation.
- [x] Write tests for flow-before-balance transaction behavior.
- [x] Implement ledger service methods: `receive_pending`, `approve_to_available`, `lock_stock`, `release_lock`, `ship_locked`, `freeze`, `unfreeze`, `adjust_after_check`.
- [x] Implement realtime stock query page.
- [x] Treat `sn_code` as optional metadata in ledger tests; batch number remains the required trace key.
- [ ] Commit: `feat: 增加WMS库存账核心`.

### Phase 3: Arrival, Inspection, And Inbound

**Outcome:** Purchase arrival can be received, inspected, converted to inbound, and posted to stock.

**Files:**
- Create `backend/app/api/v1/module_wms/arrival/`.
- Create `backend/app/api/v1/module_wms/inspection/`.
- Create `backend/app/api/v1/module_wms/inbound/`.
- Create `backend/tests/test_wms_inbound_flow.py`.
- Create matching frontend API and views.

- [x] Test arrival status: `pending_receive -> received -> pending_inspection -> pending_inbound -> closed`.
- [x] Test inspection result controls stock status.
- [x] Test inbound confirmation writes `WmsStockFlow` and updates `WmsStockBalance`.
- [x] Implement location recommendation using material category and available capacity.
- [x] Add pages for arrival list/detail, inspection task, inbound confirmation.
- [x] Keep IQC local to WMS: store result, inspector, inspected time, attachment references, and optional `external_quality_id`.
- [ ] Commit: `feat: 打通WMS采购到货入库闭环`.

### Phase 4: Production Issue And Outbound

**Outcome:** Production issue and sales outbound can reserve stock, pick, review, confirm, and deduct stock.

**Files:**
- Create `backend/app/api/v1/module_wms/outbound/`.
- Create `backend/app/api/v1/module_wms/issue/`.
- Create `backend/tests/test_wms_outbound_flow.py`.
- Create matching frontend API and views.

- [x] Test FIFO batch recommendation.
- [x] Test production issue lock and confirmation.
- [x] Test sales outbound pick/review/confirm.
- [x] Test cancel releases locks.
- [x] Add outbound and issue pages.
- [x] Support manual and imported production demand first; MES work order fields are optional external references in V1.
- [ ] Commit: `feat: 增加WMS出库与生产领料闭环`.

### Phase 5: Transfer, Stock Check, And Warning

**Outcome:** Inventory can be transferred, counted, adjusted after audit, and warned by rule.

**Files:**
- Create `backend/app/api/v1/module_wms/transfer/`.
- Create `backend/app/api/v1/module_wms/check/`.
- Create `backend/app/api/v1/module_wms/warning/`.
- Create `backend/tests/test_wms_check_warning.py`.
- Create matching frontend API and views.

- [ ] Test transfer writes out/in flow pair.
- [ ] Test stock check draft does not affect balance.
- [ ] Test stock check audit writes adjustment flow.
- [ ] Test safety stock, shortage, idle, overstock warnings.
- [ ] Add warning list with handle/close actions.
- [ ] Implement audit as permission-protected status transition; do not call workflow engine in V1.
- [ ] Commit: `feat: 增加WMS盘点调拨与库存预警`.

### Phase 6: Traceability And Dashboard

**Outcome:** Users can trace material/product batches and view WMS dashboard data.

**Files:**
- Create `backend/app/api/v1/module_wms/trace/`.
- Create `backend/app/api/v1/module_wms/dashboard/`.
- Create `backend/tests/test_wms_trace_dashboard.py`.
- Create `frontend/web/src/api/module_wms/dashboard.ts`.
- Create `frontend/web/src/views/module_wms/dashboard/`.
- Create `frontend/web/src/views/module_wms/trace/`.

- [ ] Test trace forward from material batch to production/outbound references.
- [ ] Test trace backward from product batch to material sources when links exist.
- [ ] Implement dashboard endpoints: `summary`, `tasks`, `stock-structure`, `trends`, `warnings`, `latest-flows`.
- [ ] Build dashboard with existing `FaStatsCard`, chart cards, and `FaTimelineListCard`.
- [ ] Commit: `feat: 增加WMS追溯与仓储驾驶舱`.

### Phase 7: Demo Data And AI-Enhanced Text

**Outcome:** Tenant admins can generate and clean WMS demo data without affecting formal data.

**Files:**
- Create `backend/app/api/v1/module_wms/demo/`.
- Create `backend/app/api/v1/module_wms/demo/generator.py`.
- Create `backend/app/scripts/data/wms_industry_terms.json`.
- Create `backend/app/scripts/data/wms_sample_pack.json`.
- Modify `backend/app/plugin/module_task/industry/service.py` only if reusable lookup support is missing.
- Create `backend/tests/test_wms_demo_data.py`.
- Create `frontend/web/src/views/module_wms/demo/`.

- [ ] Test demo generation creates one `BusinessTask`.
- [ ] Test all generated rows carry `tenant_id`, `is_demo`, and `demo_batch_id`.
- [ ] Test cleanup only deletes rows for current tenant and batch.
- [ ] Implement deterministic generator first; call AI only for names, descriptions, summaries, and suggestions.
- [ ] Add demo initialization page with enterprise profile fields.
- [ ] Commit: `feat: 增加WMS试用数据初始化`.

### Phase 8: Integration Boundaries

**Outcome:** ERP/MES/PDA integrations have stable internal contracts without depending on live external systems.

**Files:**
- Create `backend/app/api/v1/module_wms/integration/`.
- Create `backend/tests/test_wms_integration_contracts.py`.
- Create docs under `docs/product/integration/`.

- [ ] Define inbound contracts for material, purchase arrival, sales order, MES work order, BOM demand, completion inbound request.
- [ ] Define outbound contracts for available stock, shortage result, issue result, inbound result, trace result.
- [ ] Add idempotency keys for external requests.
- [ ] Store external reference fields on business documents.
- [ ] Keep V1 endpoints usable by manual tests and future sync clients; do not implement scheduled ERP/MES polling.
- [ ] Commit: `feat: 增加WMS外部系统对接契约`.

## 8. Verification Policy

Run these checks before each phase commit:

```bash
cd backend
uv run pytest tests/test_wms_<scope>.py -q
uv run ruff check app tests

cd frontend/web
corepack pnpm run type-check
corepack pnpm run test
```

Run broader checks before merging a phase:

```bash
cd backend && uv run pytest tests -q
cd frontend/web && corepack pnpm run build
```

## 9. Commit Strategy

Use one commit per phase or one commit per independently usable slice:

- `chore: 初始化WMS产品装配骨架`
- `feat: 增加WMS仓储基础资料`
- `feat: 增加WMS库存账核心`
- `feat: 打通WMS采购到货入库闭环`
- `feat: 增加WMS出库与生产领料闭环`
- `feat: 增加WMS盘点调拨与库存预警`
- `feat: 增加WMS追溯与仓储驾驶舱`
- `feat: 增加WMS试用数据初始化`

## 10. Scope Guardrails

Do not implement in V1:

- AGV scheduling algorithms.
- PLC/automatic warehouse control.
- Financial inventory costing.
- Offline PDA sync.
- Native PDA/App delivery.
- Full ERP connector.
- Full MES connector.
- Complex workflow engine approval.
- Required SN single-piece workflows.

V1 must leave extension points for those features through external reference fields, integration contracts, task handlers, and stock flow types.
