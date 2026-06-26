# WMS Demo Data UI Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild WMS trial-data generation so tenant users can enter their own products, generation requirements, and quantity targets, then receive high-quality dynamic demo data instead of fixed rows.

**Architecture:** Keep formal WMS master data separate from demo-generation configuration. Add tenant-editable demo sample pools and a deterministic generation planner; the UI collects structured product requirements plus optional free-text instructions, while the backend validates, previews, generates, and quality-checks demo data under `tenant_id/is_demo/demo_batch_id`.

**Tech Stack:** FastAPI, SQLAlchemy 2, Pydantic, PostgreSQL, existing `BusinessTask`, platform `AiRuntimeService`, Vue 3, TypeScript, Element Plus, existing `fa-*` components, pytest, Vitest/vue-tsc.

---

## 1. Current Problems

Current UI and backend are too narrow for real tenant trials:

- `frontend/web/src/views/module_wms/demo/index.vue` only asks for company name, industry, scenario, warehouse count, and material count.
- `frontend/web/src/api/module_wms/demo.ts` caps frontend contract to `warehouse_count`, `material_count`, and `scenario`.
- `backend/app/api/v1/module_wms/demo/schema.py` caps warehouses at 3 and materials at 20.
- `backend/app/api/v1/module_wms/demo/generator.py` hard-codes one main material, one supplier, one customer, one batch, one inbound chain, one outbound order, one issue order, and one warning.
- Existing `backend/app/plugin/module_task/industry/*` is a read-only industry sample-pack skeleton; WMS needs tenant-editable demo-generation configuration.

## 2. Product Decisions

1. Demo sample pools are configuration, not formal master data.
2. System default sample pool is built in, but tenants can copy it and edit their own pool.
3. Users can enter their own products and requirements per generation run without first maintaining formal material records.
4. Quantity controls must be user-adjustable and clamped by server-side limits.
5. The generator must be dynamic and deterministic: same input and same seed produce stable structure, but generated records are not fixed one-off rows.
6. AI can enrich names and descriptions, but rule planning owns counts, relationships, dates, statuses, quantities, and referential integrity.
7. AI failure must not block generation.

## 3. Target User Experience

### 3.1 Page Structure

Use one page with tabs under `frontend/web/src/views/module_wms/demo/index.vue`.

| Tab | Purpose | Main Components |
|---|---|---|
| 生成演示数据 | Collect profile, products, requirements, quantity targets, preview, and start generation | Form sections, editable product table, scale cards, preview panel |
| 样本池配置 | Copy and edit tenant sample pools | Pool list, item table, prompt editor drawer |
| 生成历史 | View tasks, counts, errors, and clean batches | Task table, count detail drawer, clean confirm dialog |

### 3.2 Generation Form

Use fixed controls where possible, plus explicit free-text fields for tenant-specific products and requirements.

| Section | Field | Control | Backend Field |
|---|---|---|---|
| 企业画像 | 企业名称 | `ElInput` | `profile.company_name` |
| 企业画像 | 行业 | `ElInput` default 电工装备 | `profile.industry` |
| 企业画像 | 企业规模 | `ElSegmented` 小型/中型/大型 | `profile.company_size` |
| 样本来源 | 样本池 | `ElSelect` | `sample_pool_id` |
| 产品方向 | 产品方向 | `ElCheckboxGroup` | `product_directions` |
| 产品明细 | 自定义产品 | `ElTable` editable rows | `custom_products[]` |
| 产品明细 | 批量输入 | `ElInput type=textarea` | parsed into `custom_products[]` |
| 生成要求 | 仓储场景 | `ElCheckboxGroup` | `warehouse_scenarios` |
| 生成要求 | 质量/检验要求 | `ElInput type=textarea` | `quality_requirements` |
| 生成要求 | 命名风格 | `ElSelect` 工业真实/简洁编码/客户化 | `naming_style` |
| 数据规模 | 规模模式 | `ElSegmented` 快速/标准/丰富/自定义 | `scale_mode` |
| 数据规模 | 数量目标 | `ElSlider` + `ElInputNumber` | `quantity_targets` |
| 数据范围 | 时间范围 | `ElSelect` 30/90/180 天 | `time_range_days` |
| 智能增强 | 使用 AI 增强 | `ElSwitch` | `use_ai_enrichment` |
| 智能增强 | 额外要求 | `ElInput type=textarea` | `generation_instructions` |

### 3.3 Custom Product Row

Users must be able to enter their own products without creating formal materials first.

```ts
interface WmsDemoCustomProduct {
  name: string;
  category?: string;
  voltage_level?: string;
  spec_examples?: string[];
  unit?: string;
  storage_traits?: string[];
  quality_requirements?: string;
  supplier_requirement?: string;
  weight?: number;
}
```

UI validation:

- `name` is required, max 80 chars.
- `weight` defaults to `1`, min `1`, max `10`.
- `spec_examples` can be typed as comma-separated text and normalized before submit.
- Empty table is allowed; then generator uses selected sample pool and product directions.

### 3.4 Quantity Controls

The user can tune counts, but backend clamps unsafe values.

| Mode | Warehouses | Locations | Materials | Stock Flows | Business Docs | Use Case |
|---|---:|---:|---:|---:|---:|---|
| 快速体验 | 1-2 | 20-60 | 20-50 | 50-150 | 20-60 | Smoke test and sales demo |
| 标准演示 | 3-5 | 100-300 | 80-200 | 300-800 | 120-300 | Default tenant trial |
| 丰富演示 | 5-8 | 300-800 | 200-500 | 1000-3000 | 400-1000 | Deep trial |
| 自定义 | 1-8 | 10-1000 | 10-600 | 20-5000 | 20-1500 | Advanced admin only |

The form must show an estimated count preview before generation.

## 4. Backend File Structure

### 4.1 Create

- `backend/app/api/v1/module_wms/demo/model.py`: sample-pool and sample-item models.
- `backend/app/api/v1/module_wms/demo/pool_schema.py`: pool CRUD and item schemas.
- `backend/app/api/v1/module_wms/demo/pool_service.py`: system-pool loading, tenant copy, tenant edit, validation.
- `backend/app/api/v1/module_wms/demo/fixtures/electrical_equipment.py`: default built-in sample pool.
- `backend/app/api/v1/module_wms/demo/planner.py`: converts request + sample pool into a deterministic generation plan.
- `backend/app/api/v1/module_wms/demo/ai_enricher.py`: calls platform AI only for naming and narrative enrichment.
- `backend/app/api/v1/module_wms/demo/writer.py`: writes planned WMS rows and counts.
- `backend/app/api/v1/module_wms/demo/quality.py`: validates generated plan and persisted counts.
- `backend/tests/test_wms_demo_sample_pool.py`: pool copy/edit/isolation tests.
- `backend/tests/test_wms_demo_generation_plan.py`: planner and quantity tests.
- `backend/tests/test_wms_demo_data_v2.py`: end-to-end generation and cleanup tests.

### 4.2 Modify

- `backend/app/api/v1/module_wms/demo/schema.py`: replace narrow `warehouse_count/material_count` with richer request schema.
- `backend/app/api/v1/module_wms/demo/controller.py`: add pool, preview, history endpoints.
- `backend/app/api/v1/module_wms/demo/generator.py`: turn into orchestration wrapper around planner/enricher/writer/quality.
- `backend/app/api/v1/module_wms/__init__.py`: ensure new controllers remain discovered through `DemoRouter`.
- `backend/app/scripts/initialize.py`: load system demo pool config if using database-backed system pool.
- `backend/app/alembic/versions/20260627_01_wms_demo_sample_pool.py`: add sample-pool tables.
- `frontend/web/src/api/module_wms/demo.ts`: add request/response types and pool APIs.
- `frontend/web/src/views/module_wms/demo/index.vue`: rebuild as tabbed page.
- `frontend/web/src/views/module_wms/demo/components/ProductInputTable.vue`: custom products table.
- `frontend/web/src/views/module_wms/demo/components/QuantityTargetPanel.vue`: scale and sliders.
- `frontend/web/src/views/module_wms/demo/components/SamplePoolEditor.vue`: tenant pool editor.
- `frontend/web/src/views/module_wms/demo/components/DemoPreviewPanel.vue`: count preview and warnings.

## 5. Backend Contract

### 5.1 Init Request

```python
class WmsDemoQuantityTargets(BaseModel):
    warehouse_count: int | None = Field(default=None, ge=1, le=8)
    location_count: int | None = Field(default=None, ge=10, le=1000)
    material_count: int | None = Field(default=None, ge=10, le=600)
    stock_flow_count: int | None = Field(default=None, ge=20, le=5000)
    business_doc_count: int | None = Field(default=None, ge=20, le=1500)
    warning_count: int | None = Field(default=None, ge=0, le=200)


class WmsDemoCustomProduct(BaseModel):
    name: str = Field(..., min_length=1, max_length=80)
    category: str | None = Field(default=None, max_length=64)
    voltage_level: str | None = Field(default=None, max_length=32)
    spec_examples: list[str] = Field(default_factory=list, max_length=20)
    unit: str | None = Field(default=None, max_length=16)
    storage_traits: list[str] = Field(default_factory=list, max_length=10)
    quality_requirements: str | None = Field(default=None, max_length=500)
    supplier_requirement: str | None = Field(default=None, max_length=300)
    weight: int = Field(default=1, ge=1, le=10)


class WmsDemoInitSchema(BaseModel):
    profile: WmsDemoEnterpriseProfile = Field(default_factory=WmsDemoEnterpriseProfile)
    sample_pool_id: int | None = Field(default=None)
    product_directions: list[str] = Field(default_factory=list, max_length=20)
    custom_products: list[WmsDemoCustomProduct] = Field(default_factory=list, max_length=80)
    warehouse_scenarios: list[str] = Field(default_factory=list, max_length=10)
    scale_mode: Literal["quick", "standard", "rich", "custom"] = "standard"
    quantity_targets: WmsDemoQuantityTargets = Field(default_factory=WmsDemoQuantityTargets)
    time_range_days: int = Field(default=90, ge=7, le=180)
    naming_style: Literal["industrial", "compact", "tenant"] = "industrial"
    quality_requirements: str | None = Field(default=None, max_length=1000)
    generation_instructions: str | None = Field(default=None, max_length=1500)
    use_ai_enrichment: bool = True
```

### 5.2 Preview Response

`POST /wms/demo/preview` must not write WMS business rows.

```python
class WmsDemoPreviewOut(BaseModel):
    sample_pool_name: str
    scale_mode: str
    estimated_counts: dict[str, int]
    product_mix: list[dict]
    workflow_coverage: list[str]
    warnings: list[str]
    preview_names: dict[str, list[str]]
```

### 5.3 Batch Response

Extend existing `WmsDemoBatchOut`.

```python
class WmsDemoBatchOut(BaseModel):
    module: str = "wms"
    scenario: str
    demo_batch_id: str
    task_id: int
    counts: dict[str, int]
    summary: list[str]
    preview_snapshot: dict | None = None
    quality_report: dict | None = None
```

## 6. Generation Rules

### 6.1 Deterministic Dynamic Seed

Use a seeded random generator:

```python
seed_text = f"{tenant_id}:{demo_batch_id}:{profile.company_name}:{scale_mode}:{len(custom_products)}"
seed = int(hashlib.sha256(seed_text.encode()).hexdigest()[:12], 16)
rng = random.Random(seed)
```

This avoids hard-coded rows while keeping generation debuggable.

### 6.2 Product Mix

Planner builds product candidates from:

1. tenant custom products,
2. selected sample-pool items,
3. selected product directions,
4. fallback electrical-equipment defaults.

Rules:

- Every custom product with `weight > 0` must appear in generated material rows.
- At least 40% of materials should come from tenant custom products when provided.
- Generated material names must not use generic names like `试用物料1` unless all product sources are empty.
- Specs must combine voltage level, sample patterns, and sequence, for example `10kV KYN28A-12`, `110kV GIS-HG-252`, `ZC-YJV22-8.7/15kV`.

### 6.3 Count Allocation

Planner derives target counts from mode and user overrides:

```text
target.material_count = user value or mode default midpoint
target.stock_flow_count = max(user value, material_count * 4)
target.business_doc_count = max(user value, material_count * 2)
```

Distribution:

- 60-70% inbound and inspection flows.
- 20-30% outbound/issue flows.
- 5-10% check/adjustment flows.
- 3-8% warnings depending on selected risk style.

### 6.4 Workflow Coverage

Standard and rich modes must cover:

- warehouse, zone, location,
- material, supplier, customer, barcode rule,
- arrival, inspection, inbound,
- outbound, issue,
- transfer,
- stock check,
- stock lock/freeze or warning,
- trace links,
- dashboard-supporting historical flows.

Quick mode may skip transfer and stock check only if the UI warns the user before generation.

### 6.5 Quality Gate

Before commit, run a quality check:

```python
class WmsDemoQualityReport(BaseModel):
    passed: bool
    checks: dict[str, bool]
    counts: dict[str, int]
    warnings: list[str]
```

Minimum checks:

- `tenant_id` is present on every generated row.
- `is_demo=True` and `demo_batch_id` present on every generated row.
- material count >= requested minimum after clamping.
- no duplicate codes within tenant.
- every custom product appears in at least one material or warning text.
- standard/rich mode covers all required workflows.
- cleanup list includes every model written by writer.

## 7. Frontend Interaction Details

### 7.1 Fixed Controls Plus Free Text

The UI should guide users with structured controls but still allow real requirements:

- Product table for exact product names and specs.
- Requirement textareas for “我司主要做 10kV 环网柜，供应商分华东和华南，要求有来料不合格和安全库存预警” style input.
- Prompt editor only in sample-pool configuration, not in the main generation form.

### 7.2 Preview Before Generate

User flow:

1. Fill form.
2. Click `预览生成计划`.
3. Backend returns counts, product mix, sample names, workflow coverage, warnings.
4. User confirms `生成演示数据`.

Do not generate immediately from an incomplete form.

### 7.3 History And Cleanup

History table columns:

- batch id,
- sample pool,
- scale mode,
- counts,
- status,
- duration,
- created by,
- created time,
- clean action.

Clean dialog must show estimated affected rows grouped by object before deletion.

## 8. Implementation Tasks

### Task 1: Backend Schemas And Tests

**Files:**
- Modify: `backend/app/api/v1/module_wms/demo/schema.py`
- Test: `backend/tests/test_wms_demo_generation_plan.py`

- [ ] Add Pydantic schemas from section 5.
- [ ] Add validation tests for custom products, scale mode, quantity clamps, and long instruction rejection.
- [ ] Run `uv run pytest tests/test_wms_demo_generation_plan.py -q`.
- [ ] Commit:

```bash
git add backend/app/api/v1/module_wms/demo/schema.py backend/tests/test_wms_demo_generation_plan.py
git commit -m "test: 补充WMS演示数据请求契约"
```

### Task 2: Sample Pool Models And Service

**Files:**
- Create: `backend/app/api/v1/module_wms/demo/model.py`
- Create: `backend/app/api/v1/module_wms/demo/pool_schema.py`
- Create: `backend/app/api/v1/module_wms/demo/pool_service.py`
- Create: `backend/app/api/v1/module_wms/demo/fixtures/electrical_equipment.py`
- Create: `backend/app/alembic/versions/20260627_01_wms_demo_sample_pool.py`
- Test: `backend/tests/test_wms_demo_sample_pool.py`

- [ ] Create sample-pool and sample-item tables.
- [ ] Implement system default pool loading from fixture.
- [ ] Implement tenant copy and tenant-only edit.
- [ ] Test that system pool cannot be modified by tenant.
- [ ] Test that tenant A cannot see or edit tenant B pool.
- [ ] Run `uv run pytest tests/test_wms_demo_sample_pool.py -q`.
- [ ] Commit:

```bash
git add backend/app/api/v1/module_wms/demo/model.py backend/app/api/v1/module_wms/demo/pool_schema.py backend/app/api/v1/module_wms/demo/pool_service.py backend/app/api/v1/module_wms/demo/fixtures/electrical_equipment.py backend/app/alembic/versions backend/tests/test_wms_demo_sample_pool.py
git commit -m "feat: 增加WMS演示数据样本池"
```

### Task 3: Planner And Preview API

**Files:**
- Create: `backend/app/api/v1/module_wms/demo/planner.py`
- Create: `backend/app/api/v1/module_wms/demo/quality.py`
- Modify: `backend/app/api/v1/module_wms/demo/controller.py`
- Test: `backend/tests/test_wms_demo_generation_plan.py`

- [ ] Implement deterministic plan generation.
- [ ] Implement product mix from custom products plus sample pool.
- [ ] Implement estimated counts and workflow coverage.
- [ ] Add `POST /wms/demo/preview`.
- [ ] Test preview does not write WMS rows.
- [ ] Test custom product names appear in preview.
- [ ] Run `uv run pytest tests/test_wms_demo_generation_plan.py -q`.
- [ ] Commit:

```bash
git add backend/app/api/v1/module_wms/demo/planner.py backend/app/api/v1/module_wms/demo/quality.py backend/app/api/v1/module_wms/demo/controller.py backend/tests/test_wms_demo_generation_plan.py
git commit -m "feat: 增加WMS演示数据生成预览"
```

### Task 4: Writer Refactor

**Files:**
- Create: `backend/app/api/v1/module_wms/demo/writer.py`
- Modify: `backend/app/api/v1/module_wms/demo/generator.py`
- Modify: `backend/app/api/v1/module_wms/demo/quality.py`
- Test: `backend/tests/test_wms_demo_data_v2.py`

- [ ] Move row persistence from `generator.py` into writer.
- [ ] Generate multiple warehouses, locations, materials, suppliers, batches, and flows from plan.
- [ ] Add transfer, stock check, and stock lock/freeze/warning generation.
- [ ] Ensure `_delete_order()` includes every model written.
- [ ] Test standard mode count thresholds.
- [ ] Test cleanup only deletes current tenant demo rows.
- [ ] Run `uv run pytest tests/test_wms_demo_data.py tests/test_wms_demo_data_v2.py -q`.
- [ ] Commit:

```bash
git add backend/app/api/v1/module_wms/demo/writer.py backend/app/api/v1/module_wms/demo/generator.py backend/app/api/v1/module_wms/demo/quality.py backend/tests/test_wms_demo_data.py backend/tests/test_wms_demo_data_v2.py
git commit -m "feat: 重构WMS动态演示数据生成器"
```

### Task 5: AI Enrichment

**Files:**
- Create: `backend/app/api/v1/module_wms/demo/ai_enricher.py`
- Modify: `backend/app/api/v1/module_wms/demo/generator.py`
- Test: `backend/tests/test_wms_demo_data_v2.py`

- [ ] Use platform `AiRuntimeService`; do not import LangChain directly in WMS.
- [ ] Pass product mix, tenant instructions, naming style, and sample pool prompt to AI.
- [ ] Validate AI output lengths and fall back to rule names on failure.
- [ ] Test AI unavailable still succeeds.
- [ ] Run `uv run pytest tests/test_wms_demo_data_v2.py tests/test_wms_intelligence.py -q`.
- [ ] Commit:

```bash
git add backend/app/api/v1/module_wms/demo/ai_enricher.py backend/app/api/v1/module_wms/demo/generator.py backend/tests/test_wms_demo_data_v2.py
git commit -m "feat: 增强WMS演示数据AI命名"
```

### Task 6: Frontend API Contract

**Files:**
- Modify: `frontend/web/src/api/module_wms/demo.ts`

- [ ] Add TypeScript interfaces matching section 5.
- [ ] Add APIs: `preview`, `listSamplePools`, `copySamplePool`, `updateSamplePool`, `updateSampleItem`, `listHistory`.
- [ ] Run `pnpm type-check`.
- [ ] Commit:

```bash
git add frontend/web/src/api/module_wms/demo.ts
git commit -m "feat: 扩展WMS演示数据前端契约"
```

### Task 7: Frontend UI Refactor

**Files:**
- Modify: `frontend/web/src/views/module_wms/demo/index.vue`
- Create: `frontend/web/src/views/module_wms/demo/components/ProductInputTable.vue`
- Create: `frontend/web/src/views/module_wms/demo/components/QuantityTargetPanel.vue`
- Create: `frontend/web/src/views/module_wms/demo/components/SamplePoolEditor.vue`
- Create: `frontend/web/src/views/module_wms/demo/components/DemoPreviewPanel.vue`

- [ ] Replace single card form with tabbed page.
- [ ] Add custom product table and batch text parser.
- [ ] Add scale mode cards and quantity sliders.
- [ ] Add preview panel before generation.
- [ ] Add sample-pool editor with system pool read-only state.
- [ ] Add history tab and clean confirmation.
- [ ] Run `pnpm type-check && pnpm build`.
- [ ] Commit:

```bash
git add frontend/web/src/views/module_wms/demo frontend/web/src/api/module_wms/demo.ts
git commit -m "feat: 重构WMS试用数据配置界面"
```

### Task 8: End-To-End Verification

**Files:**
- Modify only if bugs are found.

- [ ] Backend: `uv run pytest tests/test_wms_demo_data.py tests/test_wms_demo_data_v2.py tests/test_wms_demo_sample_pool.py tests/test_wms_demo_generation_plan.py -q`.
- [ ] Frontend: `pnpm type-check && pnpm build`.
- [ ] Runtime: start backend on `41232` and frontend on `41291`.
- [ ] Browser test quick mode with no custom products.
- [ ] Browser test standard mode with custom products: `10kV环网柜`, `高压电缆`, `配电变压器`.
- [ ] Confirm generated data count meets preview within tolerance.
- [ ] Confirm cleanup removes only current batch.
- [ ] Commit fixes:

```bash
git add backend frontend
git commit -m "fix: 完善WMS演示数据重构验证"
```

## 9. Acceptance Criteria

- User can enter custom products, specs, quality requirements, supplier requirements, and generation instructions in the UI.
- User can adjust data scale with fixed modes or custom counts.
- Preview shows estimated generated counts and sample names before writing data.
- Standard mode generates at least 3 warehouses, 80 materials, 100 locations, 300 stock flows, and covers inbound, inspection, outbound, issue, transfer, stock check, warning, and trace.
- Custom product names appear in generated materials or related remarks.
- No generated material names are generic `试用物料N` when sample pool or custom products exist.
- All generated business rows carry `tenant_id`, `is_demo=True`, and `demo_batch_id`.
- Cleanup only affects current tenant demo rows.
- AI unavailable path succeeds with rule-generated names.
- Frontend build and backend tests pass.

## 10. Execution Notes

Do not start by polishing the UI only. The correct order is schema and planner first, then writer, then frontend. Otherwise the page will look configurable while the backend still produces fixed data.

Keep commits small and verified. If a task changes both backend and frontend, split the contract commit from the UI commit.
