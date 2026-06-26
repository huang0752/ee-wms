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

Use these top-level menus:

| Menu | Route group | Permission |
|---|---|---|
| 仓储驾驶舱 | `wms-dashboard` | `module_wms:dashboard:query` |
| 仓储基础 | `wms-master` | directory only |
| 到货与检验 | `wms-arrival` | directory only |
| 入库管理 | `wms-inbound` | directory only |
| 出库管理 | `wms-outbound` | directory only |
| 库存管理 | `wms-stock` | directory only |
| 预警与分析 | `wms-warning` | directory only |
| 仓储追溯 | `wms-trace` | `module_wms:trace:query` |
| 试用数据 | `wms-demo` | `module_wms:demo:init` |

Button permissions follow `query/create/update/delete/import/export/confirm/cancel/audit/freeze/unfreeze/print`.

## 5. Product Assembly

Create `backend/app/assemblies/wms.toml`:

```toml
[assembly]
name = "wms"
title = "EE WMS"
description = "Electrical equipment warehouse management product assembly"

[backend]
enabled_core_modules = ["module_system", "module_platform", "module_common", "module_monitor"]
enabled_plugin_modules = ["module_ai", "module_task", "module_generator"]
disabled_plugin_modules = ["module_example"]

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
  "workspace",
  "outside",
  "exception"
]
disabled_route_groups = ["pricing", "article", "tutorial", "changelog"]

[seed]
packs = ["minimal", "wms"]

[feature_flags]
ai_assistant = true
fast_enter = true
wms_demo_data = true
```

Add `APP_ASSEMBLY = "wms"` to local development env only after the WMS seed pack exists.

## 6. Development Phases

### Phase 0: Planning And Product Setup

**Outcome:** WMS has a tracked plan, assembly, initial seed file, and module skeleton.

**Files:**
- Create: `backend/app/assemblies/wms.toml`
- Create: `backend/app/api/v1/module_wms/__init__.py`
- Create: `backend/app/api/v1/module_wms/README.md`
- Create: `frontend/web/src/api/module_wms/README.md`
- Create: `frontend/web/src/views/module_wms/README.md`
- Create: `backend/app/scripts/seeds/wms/seed.toml`

- [ ] Create the WMS assembly file from section 5.
- [ ] Create backend and frontend module directories.
- [ ] Create an empty seed pack with only package metadata.
- [ ] Run `cd backend && uv run pytest tests/test_assembly.py -q`.
- [ ] Run `cd frontend/web && corepack pnpm run type-check`.
- [ ] Commit: `chore: 初始化WMS产品装配骨架`.

### Phase 1: Master Data Foundation

**Outcome:** Warehouse, zone, location, material, supplier, customer, and barcode rules have backend CRUD, menu seed, and frontend list/forms.

**Files:**
- Create under `backend/app/api/v1/module_wms/master/`: `model.py`, `schema.py`, `crud.py`, `service.py`, `controller.py`.
- Create `backend/tests/test_wms_master.py`.
- Create `frontend/web/src/api/module_wms/master.ts`.
- Create pages under `frontend/web/src/views/module_wms/master/`.

- [ ] Write pytest cases for tenant isolation and CRUD permission denial.
- [ ] Implement SQLAlchemy models with `TenantMixin`, `UserMixin`, `dept_id`, `is_demo`, `demo_batch_id`.
- [ ] Implement services with code uniqueness per tenant.
- [ ] Add menu seed for master data pages and buttons.
- [ ] Build frontend pages with `FaTable`, `FaSearchBar`, `FaDialog`, `FaForm`, and status tags.
- [ ] Keep SN fields nullable and hidden behind simple form switches; do not build SN-only workflows in this phase.
- [ ] Run `cd backend && uv run pytest tests/test_wms_master.py -q`.
- [ ] Run `cd frontend/web && corepack pnpm run type-check`.
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

- [ ] Write tests for inbound flow creating balance.
- [ ] Write tests for lock preventing double allocation.
- [ ] Write tests for frozen/pending/defective stock excluded from outbound recommendation.
- [ ] Write tests for flow-before-balance transaction behavior.
- [ ] Implement ledger service methods: `receive_pending`, `approve_to_available`, `lock_stock`, `release_lock`, `ship_locked`, `freeze`, `unfreeze`, `adjust_after_check`.
- [ ] Implement realtime stock query page.
- [ ] Treat `sn_code` as optional metadata in ledger tests; batch number remains the required trace key.
- [ ] Commit: `feat: 增加WMS库存账核心`.

### Phase 3: Arrival, Inspection, And Inbound

**Outcome:** Purchase arrival can be received, inspected, converted to inbound, and posted to stock.

**Files:**
- Create `backend/app/api/v1/module_wms/arrival/`.
- Create `backend/app/api/v1/module_wms/inspection/`.
- Create `backend/app/api/v1/module_wms/inbound/`.
- Create `backend/tests/test_wms_inbound_flow.py`.
- Create matching frontend API and views.

- [ ] Test arrival status: `pending_receive -> received -> pending_inspection -> pending_inbound -> closed`.
- [ ] Test inspection result controls stock status.
- [ ] Test inbound confirmation writes `WmsStockFlow` and updates `WmsStockBalance`.
- [ ] Implement location recommendation using material category and available capacity.
- [ ] Add pages for arrival list/detail, inspection task, inbound confirmation.
- [ ] Keep IQC local to WMS: store result, inspector, inspected time, attachment references, and optional `external_quality_id`.
- [ ] Commit: `feat: 打通WMS采购到货入库闭环`.

### Phase 4: Production Issue And Outbound

**Outcome:** Production issue and sales outbound can reserve stock, pick, review, confirm, and deduct stock.

**Files:**
- Create `backend/app/api/v1/module_wms/outbound/`.
- Create `backend/app/api/v1/module_wms/issue/`.
- Create `backend/tests/test_wms_outbound_flow.py`.
- Create matching frontend API and views.

- [ ] Test FIFO batch recommendation.
- [ ] Test production issue lock and confirmation.
- [ ] Test sales outbound pick/review/confirm.
- [ ] Test cancel releases locks.
- [ ] Add outbound and issue pages.
- [ ] Support manual and imported production demand first; MES work order fields are optional external references in V1.
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
