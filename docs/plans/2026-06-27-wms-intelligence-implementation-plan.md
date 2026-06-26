# WMS Intelligence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn EE WMS from a rule-based warehouse prototype with an AI platform foundation into a user-visible intelligent warehouse system with explainable recommendations, risk summaries, and AI-assisted suggestions.

**Architecture:** Deterministic warehouse rules remain the source of truth for stock quantities, batch states, warnings, and document status. WMS intelligence is layered as rule context collectors, explainable scoring services, and AI enhancement services that call the platform default LLM only for natural-language summaries, advice, and structured drafts. Every AI feature has a rule-template fallback so core WMS workflows continue when the model is unavailable.

**Tech Stack:** FastAPI, SQLAlchemy 2, Pydantic, PostgreSQL, Redis, LangChain via `AiRuntimeService`, DeepSeek `deepseek-v4-flash`, Vue 3, Vite, TypeScript, Element Plus, existing `fa-*` components, pytest, Vitest/vue-tsc.

---

## 1. Current State

The system already has an intelligence foundation, but WMS business intelligence is not yet landed.

| Area | Current Implementation | Gap |
|---|---|---|
| Platform LLM | `backend/app/plugin/module_ai/chat/service.py` provides `AiRuntimeService`, platform default model resolution, encrypted API key, and basic audit. | Missing token usage, latency, prompt key, and structured WMS usage conventions. |
| Model Config | DeepSeek is configured locally as platform default; frontend model config is super-admin only. | WMS business pages do not consume the model yet. |
| WMS Warnings | `WmsStockWarningService.scan()` creates safety stock and shortage warnings. | No reason summary, severity scoring, handling suggestion, or AI explanation. |
| WMS Recommendations | `WmsStockRecommendService.recommend_outbound()` returns available balances ordered by creation time. | No score, rule reason, stock policy explanation, or user-facing recommendation text. |
| WMS Dashboard | `WmsDashboardService.summary()` returns metrics, tasks, and static next steps. | No dynamic risk digest, priority narrative, or AI summary. |
| Demo Data | `WmsDemoGenerator` creates deterministic demo data and tracks task state. | AI-enhanced names/descriptions and demo scenario narrative are not implemented. |
| Frontend | WMS pages exist; framework AI admin/chat is hidden in WMS assembly. | No WMS-facing intelligent summary/advice panels. |

The target is not a free-form chatbot. The target is WMS-facing intelligence embedded in warehouse workflows.

## 2. Non-Negotiable Boundaries

1. Stock quantity, availability, lock/freeze state, warning trigger, and document status must be computed by WMS rules and database state.
2. AI output is only an explanation, suggestion, summary, draft, or narrative. It never directly mutates inventory or confirms business documents.
3. All AI calls must use platform default model configuration. WMS must not store API keys or per-tenant model settings.
4. AI failures must degrade to deterministic rule templates.
5. Frontend must label generated text as `智能摘要` or `智能建议`, not as official inventory truth.
6. Any AI-assisted action that creates a task, opens a document, or proposes a stock operation must require user confirmation and permission checks.

## 3. Target Capabilities

### 3.1 V1 Intelligence Scope

| Capability | Rule Output | AI Enhancement | Frontend Surface |
|---|---|---|---|
| Dashboard intelligent summary | Metrics, open warnings, pending documents, stock structure, latest flows | Short risk digest and prioritized actions | `module_wms/dashboard/index.vue` top summary band |
| Warning handling advice | Warning type, material, current qty, threshold, warehouse, latest flows | Cause explanation and recommended actions | `module_wms/warning/index.vue` side panel/dialog |
| Outbound recommendation explanation | Candidate balances, FIFO/order score, available quantity, location/batch | Human-readable reason and caveats | `module_wms/stock/index.vue` recommendation drawer |
| Stock check difference explanation | Count difference, material, batch, last flows | Difference reason draft and review checklist | `module_wms/check/index.vue` detail drawer |
| Demo scenario enhancement | Deterministic rows and counts | Company-specific demo narrative and sample remarks | `module_wms/demo/index.vue` result summary |

### 3.2 V1 API Shape

All WMS intelligence endpoints live under `/wms/intelligence`:

| Endpoint | Method | Permission | Purpose |
|---|---|---|---|
| `/dashboard-summary` | `GET` | `module_wms:dashboard:query` | Return rule metrics plus AI/fallback summary. |
| `/warning/{warning_id}/advice` | `GET` | `module_wms:warning:query` | Return handling advice for one warning. |
| `/stock/outbound-explain` | `POST` | `module_wms:stock:query` | Explain ranked outbound candidates for material/warehouse. |
| `/check/{order_id}/difference-advice` | `GET` | `module_wms:check:query` | Explain stock check differences. |
| `/demo/{demo_batch_id}/summary` | `GET` | `module_wms:demo:init` | Summarize generated demo scenario. |

## 4. File Structure

### 4.1 Backend Files

Create these WMS intelligence files:

| File | Responsibility |
|---|---|
| `backend/app/api/v1/module_wms/intelligence/__init__.py` | Package marker. |
| `backend/app/api/v1/module_wms/intelligence/schema.py` | Pydantic request/response contracts for summaries, advice, scores, and fallback metadata. |
| `backend/app/api/v1/module_wms/intelligence/rule_service.py` | Deterministic context collection, scoring, severity, and fallback text. |
| `backend/app/api/v1/module_wms/intelligence/ai_service.py` | Calls `AiRuntimeService`, validates AI output, catches failures, and returns fallback when needed. |
| `backend/app/api/v1/module_wms/intelligence/controller.py` | FastAPI endpoints and permissions under `/wms/intelligence`. |

Modify these backend files:

| File | Change |
|---|---|
| `backend/app/api/v1/module_wms/__init__.py` | Include `IntelligenceRouter`. |
| `backend/app/api/v1/module_wms/stock/recommend_service.py` | Add score and rule reason generation for outbound candidates. |
| `backend/app/api/v1/module_wms/stock/schema.py` | Add scored recommendation response schema. |
| `backend/app/api/v1/module_wms/warning/schema.py` | Add optional advice fields only if persisting advice is chosen. V1 can return advice without persisting. |
| `backend/app/plugin/module_ai/chat/audit.py` | Add optional `prompt_key`, `duration_ms`, `input_tokens`, `output_tokens`, and `business_id`. |
| `backend/app/plugin/module_ai/chat/service.py` | Populate duration and prompt metadata in `AiRuntimeService`; keep token usage best-effort. |
| `backend/tests/test_wms_intelligence.py` | New backend coverage for fallback, rule scoring, and AI call boundaries. |
| `backend/tests/test_ai_platform_foundation.py` | Extend audit assertions for added metadata. |

### 4.2 Frontend Files

Create:

| File | Responsibility |
|---|---|
| `frontend/web/src/api/module_wms/intelligence.ts` | Typed API client for WMS intelligence endpoints. |
| `frontend/web/src/views/module_wms/components/WmsIntelligenceSummary.vue` | Reusable summary/advice panel with `source=rule_fallback/ai` tag. |
| `frontend/web/src/views/module_wms/components/WmsAdviceDrawer.vue` | Shared drawer for warning/check/recommendation advice. |

Modify:

| File | Change |
|---|---|
| `frontend/web/src/views/module_wms/dashboard/index.vue` | Add intelligent summary band above metrics. |
| `frontend/web/src/views/module_wms/warning/index.vue` | Add `智能建议` action for each warning. |
| `frontend/web/src/views/module_wms/stock/index.vue` | Add recommendation explanation drawer for outbound candidates. |
| `frontend/web/src/views/module_wms/check/index.vue` | Add stock-check difference advice entry. |
| `frontend/web/src/views/module_wms/demo/index.vue` | Show generated scenario narrative after demo generation. |

## 5. Implementation Tasks

### Task 1: Add WMS Intelligence Contracts

**Files:**
- Create: `backend/app/api/v1/module_wms/intelligence/__init__.py`
- Create: `backend/app/api/v1/module_wms/intelligence/schema.py`
- Test: `backend/tests/test_wms_intelligence.py`

- [ ] **Step 1: Write schema tests**

Add this to `backend/tests/test_wms_intelligence.py`:

```python
from app.api.v1.module_wms.intelligence.schema import (
    WmsIntelligenceSource,
    WmsIntelligenceSummaryOut,
    WmsRiskLevel,
)


def test_intelligence_summary_schema_has_source_and_risk_level() -> None:
    summary = WmsIntelligenceSummaryOut(
        title="今日仓储风险摘要",
        summary="当前有 2 条未关闭预警，建议先处理安全库存不足物料。",
        risk_level=WmsRiskLevel.warning,
        source=WmsIntelligenceSource.rule_fallback,
        bullets=["处理安全库存不足", "复核待出库锁定库存"],
        actions=[{"label": "查看预警", "route": "/module-wms/analytics/warning"}],
    )

    assert summary.source == WmsIntelligenceSource.rule_fallback
    assert summary.risk_level == WmsRiskLevel.warning
    assert summary.actions[0]["route"] == "/module-wms/analytics/warning"
```

- [ ] **Step 2: Run the failing test**

Run:

```bash
cd backend
uv run pytest tests/test_wms_intelligence.py::test_intelligence_summary_schema_has_source_and_risk_level -q
```

Expected: import failure because `backend/app/api/v1/module_wms/intelligence/schema.py` does not exist.

- [ ] **Step 3: Create schema module**

Create `backend/app/api/v1/module_wms/intelligence/__init__.py` as an empty file.

Create `backend/app/api/v1/module_wms/intelligence/schema.py`:

```python
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class WmsRiskLevel(StrEnum):
    normal = "normal"
    warning = "warning"
    critical = "critical"


class WmsIntelligenceSource(StrEnum):
    ai = "ai"
    rule_fallback = "rule_fallback"


class WmsIntelligenceAction(BaseModel):
    label: str = Field(..., min_length=1, max_length=80)
    route: str | None = Field(None, max_length=200)
    permission: str | None = Field(None, max_length=120)
    payload: dict[str, Any] = Field(default_factory=dict)


class WmsIntelligenceSummaryOut(BaseModel):
    title: str
    summary: str
    risk_level: WmsRiskLevel = WmsRiskLevel.normal
    source: WmsIntelligenceSource = WmsIntelligenceSource.rule_fallback
    bullets: list[str] = Field(default_factory=list)
    actions: list[WmsIntelligenceAction | dict[str, Any]] = Field(default_factory=list)


class WmsWarningAdviceOut(BaseModel):
    warning_id: int
    warning_type: str
    risk_level: WmsRiskLevel
    reason: str
    advice: str
    source: WmsIntelligenceSource
    actions: list[WmsIntelligenceAction] = Field(default_factory=list)


class WmsOutboundExplainRequest(BaseModel):
    material_id: int
    warehouse_id: int | None = None
    location_id: int | None = None
    required_qty: str | None = None


class WmsOutboundCandidateScore(BaseModel):
    balance_id: int
    material_id: int
    warehouse_id: int
    location_id: int
    batch_no: str | None = None
    available_qty: str
    score: int
    rule_reasons: list[str]


class WmsOutboundExplainOut(BaseModel):
    material_id: int
    source: WmsIntelligenceSource
    summary: str
    candidates: list[WmsOutboundCandidateScore]
```

- [ ] **Step 4: Run schema test**

Run:

```bash
cd backend
uv run pytest tests/test_wms_intelligence.py::test_intelligence_summary_schema_has_source_and_risk_level -q
```

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/v1/module_wms/intelligence backend/tests/test_wms_intelligence.py
git commit -m "feat: 增加WMS智能输出契约"
```

### Task 2: Build Deterministic Rule Intelligence Service

**Files:**
- Create: `backend/app/api/v1/module_wms/intelligence/rule_service.py`
- Modify: `backend/tests/test_wms_intelligence.py`

- [ ] **Step 1: Write fallback service tests**

Add:

```python
from types import SimpleNamespace

import pytest

from app.core.base_schema import AuthSchema
from app.api.v1.module_wms.intelligence.rule_service import WmsIntelligenceRuleService
from app.api.v1.module_wms.intelligence.schema import WmsIntelligenceSource


class FakeDashboardService:
    async def summary(self):
        return SimpleNamespace(
            metrics=[
                SimpleNamespace(label="未关闭预警", value=3, status="warning"),
                SimpleNamespace(label="待处理单据", value=5, status="warning"),
            ],
            tasks=[SimpleNamespace(title="处理库存预警", status="active", time="3 条")],
            next_steps=["按预警处理安全库存与短缺物料"],
        )


@pytest.mark.asyncio
async def test_rule_dashboard_summary_uses_current_metrics(monkeypatch: pytest.MonkeyPatch) -> None:
    auth = AuthSchema(user=SimpleNamespace(id=1), tenant_id=1)

    monkeypatch.setattr(
        "app.api.v1.module_wms.intelligence.rule_service.WmsDashboardService",
        lambda _auth: FakeDashboardService(),
    )

    result = await WmsIntelligenceRuleService(auth).dashboard_summary()

    assert result.source == WmsIntelligenceSource.rule_fallback
    assert result.risk_level == "warning"
    assert "3 条未关闭预警" in result.summary
```

- [ ] **Step 2: Run the failing test**

```bash
cd backend
uv run pytest tests/test_wms_intelligence.py::test_rule_dashboard_summary_uses_current_metrics -q
```

Expected: import failure because `rule_service.py` does not exist.

- [ ] **Step 3: Implement rule service**

Create `backend/app/api/v1/module_wms/intelligence/rule_service.py`:

```python
from app.core.base_schema import AuthSchema

from ..dashboard.service import WmsDashboardService
from .schema import WmsIntelligenceAction, WmsIntelligenceSource, WmsIntelligenceSummaryOut, WmsRiskLevel


class WmsIntelligenceRuleService:
    def __init__(self, auth: AuthSchema) -> None:
        self.auth = auth

    async def dashboard_summary(self) -> WmsIntelligenceSummaryOut:
        summary = await WmsDashboardService(self.auth).summary()
        metric_map = {item.label: item.value for item in summary.metrics}
        open_warnings = int(metric_map.get("未关闭预警", 0) or 0)
        pending_docs = int(metric_map.get("待处理单据", 0) or 0)
        risk_level = WmsRiskLevel.critical if open_warnings >= 10 else WmsRiskLevel.warning if open_warnings or pending_docs else WmsRiskLevel.normal

        bullets = []
        if open_warnings:
            bullets.append(f"当前有 {open_warnings} 条未关闭预警，需要优先处理安全库存、短缺或冻结库存。")
        if pending_docs:
            bullets.append(f"当前有 {pending_docs} 张待处理单据，建议按到货、出库、生产领料顺序推进。")
        if not bullets:
            bullets.append("当前仓储运行平稳，未发现需要立即处理的库存风险。")

        return WmsIntelligenceSummaryOut(
            title="今日仓储风险摘要",
            summary=f"当前有 {open_warnings} 条未关闭预警，{pending_docs} 张待处理单据。",
            risk_level=risk_level,
            source=WmsIntelligenceSource.rule_fallback,
            bullets=bullets,
            actions=[
                WmsIntelligenceAction(label="查看库存预警", route="/module-wms/analytics/warning", permission="module_wms:warning:query"),
                WmsIntelligenceAction(label="查看库存流水", route="/module-wms/inventory/stock", permission="module_wms:stock:query"),
            ],
        )
```

- [ ] **Step 4: Run the rule test**

```bash
cd backend
uv run pytest tests/test_wms_intelligence.py::test_rule_dashboard_summary_uses_current_metrics -q
```

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/v1/module_wms/intelligence/rule_service.py backend/tests/test_wms_intelligence.py
git commit -m "feat: 增加WMS规则智能摘要"
```

### Task 3: Add AI Enhancement Service With Fallback

**Files:**
- Create: `backend/app/api/v1/module_wms/intelligence/ai_service.py`
- Modify: `backend/tests/test_wms_intelligence.py`

- [ ] **Step 1: Write AI fallback test**

Add:

```python
from app.api.v1.module_wms.intelligence.ai_service import WmsIntelligenceAIService


class FailingRuntime:
    async def chat(self, *args, **kwargs):
        raise RuntimeError("model unavailable")


@pytest.mark.asyncio
async def test_ai_dashboard_summary_falls_back_to_rules(monkeypatch: pytest.MonkeyPatch) -> None:
    auth = AuthSchema(user=SimpleNamespace(id=1), tenant_id=1)

    monkeypatch.setattr(
        "app.api.v1.module_wms.intelligence.rule_service.WmsDashboardService",
        lambda _auth: FakeDashboardService(),
    )

    result = await WmsIntelligenceAIService(auth, runtime=FailingRuntime()).dashboard_summary()

    assert result.source == WmsIntelligenceSource.rule_fallback
    assert "未关闭预警" in result.summary
```

- [ ] **Step 2: Run failing test**

```bash
cd backend
uv run pytest tests/test_wms_intelligence.py::test_ai_dashboard_summary_falls_back_to_rules -q
```

Expected: import failure because `ai_service.py` does not exist.

- [ ] **Step 3: Implement AI service**

Create `backend/app/api/v1/module_wms/intelligence/ai_service.py`:

```python
from app.core.base_schema import AuthSchema
from app.core.logger import logger
from app.plugin.module_ai.chat.service import AiRuntimeService

from .rule_service import WmsIntelligenceRuleService
from .schema import WmsIntelligenceSource, WmsIntelligenceSummaryOut


class WmsIntelligenceAIService:
    def __init__(self, auth: AuthSchema, runtime: AiRuntimeService | None = None) -> None:
        self.auth = auth
        self.runtime = runtime or AiRuntimeService(auth)
        self.rule_service = WmsIntelligenceRuleService(auth)

    async def dashboard_summary(self) -> WmsIntelligenceSummaryOut:
        fallback = await self.rule_service.dashboard_summary()
        prompt = (
            "你是 WMS 智慧仓储系统的业务分析助手。"
            "请基于以下规则摘要生成一段更自然的中文仓储风险摘要，"
            "不要改变数量事实，不要编造不存在的库存数据。"
            f"标题：{fallback.title}\n"
            f"规则摘要：{fallback.summary}\n"
            f"要点：{'；'.join(fallback.bullets)}"
        )
        try:
            text = await self.runtime.chat(
                prompt,
                source_module="module_wms",
                source_feature="dashboard_summary",
                system_prompt="只输出 120 字以内的中文摘要。不得输出 JSON。",
            )
        except Exception as exc:
            logger.warning("WMS 智能摘要 AI 降级: {}", exc)
            return fallback
        clean_text = text.strip()
        if not clean_text:
            return fallback
        return fallback.model_copy(update={"summary": clean_text, "source": WmsIntelligenceSource.ai})
```

- [ ] **Step 4: Run AI fallback test**

```bash
cd backend
uv run pytest tests/test_wms_intelligence.py::test_ai_dashboard_summary_falls_back_to_rules -q
```

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/v1/module_wms/intelligence/ai_service.py backend/tests/test_wms_intelligence.py
git commit -m "feat: 增加WMS智能摘要AI降级服务"
```

### Task 4: Expose WMS Intelligence APIs

**Files:**
- Create: `backend/app/api/v1/module_wms/intelligence/controller.py`
- Modify: `backend/app/api/v1/module_wms/__init__.py`
- Modify: `backend/tests/test_wms_intelligence.py`

- [ ] **Step 1: Write route registration test**

Add:

```python
def test_wms_intelligence_router_is_registered() -> None:
    from app.api.v1.module_wms import wms_router

    routes = {getattr(route, "path", "") for route in wms_router.routes}

    assert "/intelligence/dashboard-summary" in routes
```

- [ ] **Step 2: Run failing test**

```bash
cd backend
uv run pytest tests/test_wms_intelligence.py::test_wms_intelligence_router_is_registered -q
```

Expected: fail because router is not registered.

- [ ] **Step 3: Create controller**

Create `backend/app/api/v1/module_wms/intelligence/controller.py`:

```python
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.common.response import ResponseSchema, SuccessResponse
from app.core.base_schema import AuthSchema
from app.core.dependencies import AuthPermission
from app.core.router_class import OperationLogRoute

from .ai_service import WmsIntelligenceAIService
from .schema import WmsIntelligenceSummaryOut

IntelligenceRouter = APIRouter(
    route_class=OperationLogRoute,
    prefix="/intelligence",
    tags=["WMS", "智能分析"],
)


@IntelligenceRouter.get(
    "/dashboard-summary",
    summary="WMS驾驶舱智能摘要",
    response_model=ResponseSchema[WmsIntelligenceSummaryOut],
)
async def dashboard_intelligence_summary_controller(
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_wms:dashboard:query"]))],
) -> JSONResponse:
    result = await WmsIntelligenceAIService(auth).dashboard_summary()
    return SuccessResponse(data=result, msg="生成成功")
```

- [ ] **Step 4: Register router**

Modify `backend/app/api/v1/module_wms/__init__.py`:

```python
from .intelligence.controller import IntelligenceRouter
```

Add after `wms_router.include_router(DemoRouter)`:

```python
wms_router.include_router(IntelligenceRouter)
```

- [ ] **Step 5: Run registration test**

```bash
cd backend
uv run pytest tests/test_wms_intelligence.py::test_wms_intelligence_router_is_registered -q
```

Expected: pass.

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/v1/module_wms/__init__.py backend/app/api/v1/module_wms/intelligence/controller.py backend/tests/test_wms_intelligence.py
git commit -m "feat: 暴露WMS智能分析接口"
```

### Task 5: Add Warning Advice

**Files:**
- Modify: `backend/app/api/v1/module_wms/intelligence/rule_service.py`
- Modify: `backend/app/api/v1/module_wms/intelligence/ai_service.py`
- Modify: `backend/app/api/v1/module_wms/intelligence/controller.py`
- Modify: `backend/tests/test_wms_intelligence.py`

- [ ] **Step 1: Write warning advice rule test**

Add:

```python
@pytest.mark.asyncio
async def test_warning_advice_has_handling_action() -> None:
    warning = SimpleNamespace(
        id=12,
        warning_type="safety_stock",
        material_id=101,
        warehouse_id=3,
        current_qty=5,
        threshold_qty=20,
    )
    service = WmsIntelligenceRuleService(AuthSchema(user=SimpleNamespace(id=1), tenant_id=1))

    result = service.warning_advice_from_warning(warning)

    assert result.warning_id == 12
    assert result.risk_level == "warning"
    assert "安全库存" in result.reason
    assert result.actions[0].permission == "module_wms:stock:query"
```

- [ ] **Step 2: Implement rule method**

Add to `WmsIntelligenceRuleService`:

```python
from .schema import WmsWarningAdviceOut


    def warning_advice_from_warning(self, warning) -> WmsWarningAdviceOut:
        warning_type = getattr(warning, "warning_type", "")
        current_qty = getattr(warning, "current_qty", None)
        threshold_qty = getattr(warning, "threshold_qty", None)
        if warning_type == "shortage":
            reason = f"当前可用库存为 {current_qty}，已形成短缺风险。"
            advice = "建议优先检查待入库、可调拨库存和未释放锁定库存；如无可用库存，应创建补货或采购任务。"
            risk_level = WmsRiskLevel.critical
        elif warning_type == "safety_stock":
            reason = f"当前可用库存 {current_qty} 低于安全库存 {threshold_qty}。"
            advice = "建议核对近期生产领料计划，并优先安排补货、调拨或释放可用批次。"
            risk_level = WmsRiskLevel.warning
        else:
            reason = "系统检测到库存风险，需要仓储人员复核。"
            advice = "建议查看库存流水、批次状态和关联单据后再处理。"
            risk_level = WmsRiskLevel.warning
        return WmsWarningAdviceOut(
            warning_id=warning.id,
            warning_type=warning_type,
            risk_level=risk_level,
            reason=reason,
            advice=advice,
            source=WmsIntelligenceSource.rule_fallback,
            actions=[
                WmsIntelligenceAction(label="查看库存", route="/module-wms/inventory/stock", permission="module_wms:stock:query"),
                WmsIntelligenceAction(label="查看预警", route="/module-wms/analytics/warning", permission="module_wms:warning:query"),
            ],
        )
```

- [ ] **Step 3: Add AI wrapper method**

Add to `WmsIntelligenceAIService`:

```python
    async def warning_advice(self, warning) -> WmsWarningAdviceOut:
        fallback = self.rule_service.warning_advice_from_warning(warning)
        prompt = (
            "你是 WMS 库存预警处理助手。请在不改变事实的前提下，"
            "把以下规则建议改写成更清晰的处理建议。"
            f"预警类型：{fallback.warning_type}\n"
            f"原因：{fallback.reason}\n"
            f"规则建议：{fallback.advice}"
        )
        try:
            text = await self.runtime.chat(
                prompt,
                source_module="module_wms",
                source_feature="warning_advice",
                system_prompt="只输出 160 字以内中文建议，不要输出库存数量以外的新事实。",
            )
        except Exception as exc:
            logger.warning("WMS 预警建议 AI 降级: {}", exc)
            return fallback
        return fallback.model_copy(update={"advice": text.strip() or fallback.advice, "source": WmsIntelligenceSource.ai})
```

- [ ] **Step 4: Add endpoint**

Add to `controller.py`:

```python
from fastapi import Path
from sqlalchemy import select

from ..warning.model import WmsStockWarningModel
from .schema import WmsWarningAdviceOut


@IntelligenceRouter.get(
    "/warning/{warning_id}/advice",
    summary="WMS库存预警智能建议",
    response_model=ResponseSchema[WmsWarningAdviceOut],
)
async def warning_advice_controller(
    warning_id: Annotated[int, Path(ge=1)],
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_wms:warning:query"]))],
) -> JSONResponse:
    stmt = select(WmsStockWarningModel).where(
        WmsStockWarningModel.id == warning_id,
        WmsStockWarningModel.tenant_id == (auth.tenant_id or 1),
        WmsStockWarningModel.is_deleted.is_(False),
    )
    warning = (await auth.db.execute(stmt)).scalar_one_or_none()
    if warning is None:
        from app.core.exceptions import CustomException

        raise CustomException(msg="预警不存在", status_code=404)
    result = await WmsIntelligenceAIService(auth).warning_advice(warning)
    return SuccessResponse(data=result, msg="生成成功")
```

- [ ] **Step 5: Run tests**

```bash
cd backend
uv run pytest tests/test_wms_intelligence.py -q
```

Expected: pass.

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/v1/module_wms/intelligence backend/tests/test_wms_intelligence.py
git commit -m "feat: 增加WMS库存预警智能建议"
```

### Task 6: Enhance Outbound Recommendation With Scoring

**Files:**
- Modify: `backend/app/api/v1/module_wms/stock/schema.py`
- Modify: `backend/app/api/v1/module_wms/stock/recommend_service.py`
- Modify: `backend/app/api/v1/module_wms/intelligence/rule_service.py`
- Modify: `backend/app/api/v1/module_wms/intelligence/controller.py`
- Modify: `backend/tests/test_wms_intelligence.py`

- [ ] **Step 1: Define scoring rule**

Use this deterministic scoring in V1:

| Rule | Points |
|---|---:|
| Available quantity greater than zero | +40 |
| Older stock balance first by `created_time` | +30 for first candidate, then -2 per rank down to +10 |
| Same requested warehouse | +15 |
| Same requested location | +10 |
| No frozen/pending/defective quantity | +5 |

The first implementation does not require expiry date because current stock batch model does not expose expiry fields in the recommendation query.

- [ ] **Step 2: Add scoring function test**

Add:

```python
from decimal import Decimal


def test_outbound_candidate_score_prefers_available_fifo_candidate() -> None:
    service = WmsIntelligenceRuleService(AuthSchema(user=SimpleNamespace(id=1), tenant_id=1))
    candidate = SimpleNamespace(
        id=7,
        material_id=1,
        warehouse_id=2,
        location_id=3,
        batch_no="B001",
        available_qty=Decimal("10"),
        frozen_qty=Decimal("0"),
        pending_qty=Decimal("0"),
        defective_qty=Decimal("0"),
    )

    scored = service.score_outbound_candidate(candidate, rank=0, requested_warehouse_id=2, requested_location_id=3)

    assert scored.score == 100
    assert "FIFO优先" in "；".join(scored.rule_reasons)
```

- [ ] **Step 3: Implement scoring method**

Add to `WmsIntelligenceRuleService`:

```python
from .schema import WmsOutboundCandidateScore


    def score_outbound_candidate(self, candidate, *, rank: int, requested_warehouse_id: int | None, requested_location_id: int | None) -> WmsOutboundCandidateScore:
        score = 0
        reasons: list[str] = []
        if candidate.available_qty > 0:
            score += 40
            reasons.append("存在可用库存")
        fifo_score = max(10, 30 - rank * 2)
        score += fifo_score
        reasons.append("FIFO优先")
        if requested_warehouse_id and candidate.warehouse_id == requested_warehouse_id:
            score += 15
            reasons.append("匹配请求仓库")
        if requested_location_id and candidate.location_id == requested_location_id:
            score += 10
            reasons.append("匹配请求库位")
        if candidate.frozen_qty == 0 and candidate.pending_qty == 0 and candidate.defective_qty == 0:
            score += 5
            reasons.append("无冻结、待检或不良数量")
        return WmsOutboundCandidateScore(
            balance_id=candidate.id,
            material_id=candidate.material_id,
            warehouse_id=candidate.warehouse_id,
            location_id=candidate.location_id,
            batch_no=getattr(candidate, "batch_no", None),
            available_qty=str(candidate.available_qty),
            score=score,
            rule_reasons=reasons,
        )
```

- [ ] **Step 4: Add explain endpoint**

In `controller.py`, add endpoint using `WmsStockRecommendService.recommend_outbound()` and the scoring method. Return `WmsOutboundExplainOut` with fallback text:

```python
@IntelligenceRouter.post(
    "/stock/outbound-explain",
    summary="WMS出库推荐解释",
    response_model=ResponseSchema[WmsOutboundExplainOut],
)
async def outbound_explain_controller(
    data: WmsOutboundExplainRequest,
    auth: Annotated[AuthSchema, Depends(AuthPermission(["module_wms:stock:query"]))],
) -> JSONResponse:
    from ..stock.recommend_service import WmsStockRecommendService
    from ..stock.schema import WmsStockLockSchema

    candidates = await WmsStockRecommendService(auth).recommend_outbound(
        WmsStockLockSchema(
            material_id=data.material_id,
            warehouse_id=data.warehouse_id,
            location_id=data.location_id,
            quantity=data.required_qty or "0",
        )
    )
    rule_service = WmsIntelligenceRuleService(auth)
    scored = [
        rule_service.score_outbound_candidate(item, rank=index, requested_warehouse_id=data.warehouse_id, requested_location_id=data.location_id)
        for index, item in enumerate(candidates)
    ]
    result = WmsOutboundExplainOut(
        material_id=data.material_id,
        source=WmsIntelligenceSource.rule_fallback,
        summary="系统按可用库存、FIFO、仓库库位匹配和库存状态给出推荐顺序。",
        candidates=scored,
    )
    return SuccessResponse(data=result, msg="生成成功")
```

- [ ] **Step 5: Run tests**

```bash
cd backend
uv run pytest tests/test_wms_intelligence.py tests/test_wms_stock_ledger.py -q
```

Expected: pass.

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/v1/module_wms backend/tests/test_wms_intelligence.py
git commit -m "feat: 增强WMS出库推荐解释"
```

### Task 7: Frontend API And Reusable Intelligence Components

**Files:**
- Create: `frontend/web/src/api/module_wms/intelligence.ts`
- Create: `frontend/web/src/views/module_wms/components/WmsIntelligenceSummary.vue`
- Create: `frontend/web/src/views/module_wms/components/WmsAdviceDrawer.vue`

- [ ] **Step 1: Add typed API client**

Create `frontend/web/src/api/module_wms/intelligence.ts`:

```ts
import { request } from "@utils";

const API_PATH = "/wms/intelligence";

export type WmsRiskLevel = "normal" | "warning" | "critical";
export type WmsIntelligenceSource = "ai" | "rule_fallback";

export interface WmsIntelligenceAction {
  label: string;
  route?: string | null;
  permission?: string | null;
  payload?: Record<string, unknown>;
}

export interface WmsIntelligenceSummary {
  title: string;
  summary: string;
  risk_level: WmsRiskLevel;
  source: WmsIntelligenceSource;
  bullets: string[];
  actions: WmsIntelligenceAction[];
}

export interface WmsWarningAdvice {
  warning_id: number;
  warning_type: string;
  risk_level: WmsRiskLevel;
  reason: string;
  advice: string;
  source: WmsIntelligenceSource;
  actions: WmsIntelligenceAction[];
}

export const WmsIntelligenceAPI = {
  dashboardSummary() {
    return request<ApiResponse<WmsIntelligenceSummary>>({
      url: `${API_PATH}/dashboard-summary`,
      method: "get",
    });
  },
  warningAdvice(warningId: number) {
    return request<ApiResponse<WmsWarningAdvice>>({
      url: `${API_PATH}/warning/${warningId}/advice`,
      method: "get",
    });
  },
};
```

- [ ] **Step 2: Add summary component**

Create `frontend/web/src/views/module_wms/components/WmsIntelligenceSummary.vue`:

```vue
<template>
  <section class="wms-intelligence-summary" :class="`risk-${summary.risk_level}`">
    <div class="summary-head">
      <div>
        <h3>{{ summary.title }}</h3>
        <p>{{ summary.summary }}</p>
      </div>
      <ElTag :type="sourceTagType" effect="plain">{{ sourceLabel }}</ElTag>
    </div>
    <ul v-if="summary.bullets.length" class="summary-bullets">
      <li v-for="item in summary.bullets" :key="item">{{ item }}</li>
    </ul>
    <div v-if="summary.actions.length" class="summary-actions">
      <ElButton v-for="action in summary.actions" :key="action.label" size="small" plain @click="$emit('action', action)">
        {{ action.label }}
      </ElButton>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from "vue";
import type { WmsIntelligenceAction, WmsIntelligenceSummary } from "@/api/module_wms/intelligence";

const props = defineProps<{ summary: WmsIntelligenceSummary }>();
defineEmits<{ action: [action: WmsIntelligenceAction] }>();

const sourceLabel = computed(() => (props.summary.source === "ai" ? "AI 摘要" : "规则摘要"));
const sourceTagType = computed(() => (props.summary.source === "ai" ? "primary" : "info"));
</script>

<style scoped lang="scss">
.wms-intelligence-summary {
  padding: 16px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  background: var(--el-fill-color-blank);
}

.summary-head {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  justify-content: space-between;
}

h3 {
  margin: 0 0 6px;
  font-size: 16px;
}

p {
  margin: 0;
  color: var(--el-text-color-regular);
}

.summary-bullets {
  padding-left: 18px;
  margin: 12px 0 0;
  color: var(--el-text-color-secondary);
}

.summary-actions {
  display: flex;
  gap: 8px;
  margin-top: 12px;
}
</style>
```

- [ ] **Step 3: Run frontend type check**

```bash
cd frontend/web
node_modules/.bin/vue-tsc --noEmit
```

Expected: pass.

- [ ] **Step 4: Commit**

```bash
git add frontend/web/src/api/module_wms/intelligence.ts frontend/web/src/views/module_wms/components
git commit -m "feat: 增加WMS智能前端组件"
```

### Task 8: Land Dashboard Intelligent Summary

**Files:**
- Modify: `frontend/web/src/views/module_wms/dashboard/index.vue`

- [ ] **Step 1: Load intelligent summary in dashboard**

In `dashboard/index.vue`, import:

```ts
import WmsIntelligenceSummary from "../components/WmsIntelligenceSummary.vue";
import { WmsIntelligenceAPI, type WmsIntelligenceSummary as WmsIntelligenceSummaryData } from "@/api/module_wms/intelligence";
```

Add state:

```ts
const intelligenceSummary = ref<WmsIntelligenceSummaryData | null>(null);

const loadIntelligenceSummary = async () => {
  const res = await WmsIntelligenceAPI.dashboardSummary();
  if (res.data?.code === 0 && res.data.data) {
    intelligenceSummary.value = res.data.data;
  }
};
```

Call `loadIntelligenceSummary()` with existing dashboard data loading.

- [ ] **Step 2: Render summary band**

Add near the top of the dashboard template:

```vue
<WmsIntelligenceSummary
  v-if="intelligenceSummary"
  :summary="intelligenceSummary"
  @action="handleIntelligenceAction"
/>
```

Add action handler:

```ts
const handleIntelligenceAction = (action: { route?: string | null }) => {
  if (action.route) router.push(action.route);
};
```

- [ ] **Step 3: Run type check**

```bash
cd frontend/web
node_modules/.bin/vue-tsc --noEmit
```

Expected: pass.

- [ ] **Step 4: Commit**

```bash
git add frontend/web/src/views/module_wms/dashboard/index.vue
git commit -m "feat: 展示WMS驾驶舱智能摘要"
```

### Task 9: Land Warning Advice UI

**Files:**
- Modify: `frontend/web/src/views/module_wms/warning/index.vue`
- Modify: `frontend/web/src/views/module_wms/components/WmsAdviceDrawer.vue`

- [ ] **Step 1: Implement advice drawer**

Create or update `WmsAdviceDrawer.vue`:

```vue
<template>
  <FaDrawer v-model="visible" title="智能建议" size="420px">
    <template v-if="advice">
      <ElAlert :title="advice.source === 'ai' ? 'AI 智能建议' : '规则建议'" :type="advice.risk_level === 'critical' ? 'error' : 'warning'" show-icon :closable="false" />
      <ElDescriptions :column="1" border class="mt-4">
        <ElDescriptionsItem label="原因">{{ advice.reason }}</ElDescriptionsItem>
        <ElDescriptionsItem label="建议">{{ advice.advice }}</ElDescriptionsItem>
      </ElDescriptions>
    </template>
  </FaDrawer>
</template>

<script setup lang="ts">
import { computed } from "vue";
import type { WmsWarningAdvice } from "@/api/module_wms/intelligence";

const props = defineProps<{ modelValue: boolean; advice: WmsWarningAdvice | null }>();
const emit = defineEmits<{ "update:modelValue": [value: boolean] }>();

const visible = computed({
  get: () => props.modelValue,
  set: (value) => emit("update:modelValue", value),
});
</script>
```

- [ ] **Step 2: Add warning page action**

In `warning/index.vue`, import `WmsIntelligenceAPI` and `WmsAdviceDrawer`, add state:

```ts
const adviceVisible = ref(false);
const currentAdvice = ref<WmsWarningAdvice | null>(null);

const openAdvice = async (row: { id: number }) => {
  const res = await WmsIntelligenceAPI.warningAdvice(row.id);
  if (res.data?.code === 0 && res.data.data) {
    currentAdvice.value = res.data.data;
    adviceVisible.value = true;
  }
};
```

Add a row action button labeled `智能建议` that calls `openAdvice(row)`, and render:

```vue
<WmsAdviceDrawer v-model="adviceVisible" :advice="currentAdvice" />
```

- [ ] **Step 3: Run type check**

```bash
cd frontend/web
node_modules/.bin/vue-tsc --noEmit
```

Expected: pass.

- [ ] **Step 4: Commit**

```bash
git add frontend/web/src/views/module_wms/warning/index.vue frontend/web/src/views/module_wms/components/WmsAdviceDrawer.vue
git commit -m "feat: 展示WMS库存预警智能建议"
```

### Task 10: Strengthen AI Audit Metadata

**Files:**
- Modify: `backend/app/plugin/module_ai/chat/audit.py`
- Modify: `backend/app/plugin/module_ai/chat/service.py`
- Modify: `backend/tests/test_ai_platform_foundation.py`

- [ ] **Step 1: Write audit metadata test**

Extend `test_ai_call_audit_record_redacts_api_key()`:

```python
record = AiCallAuditRecord(
    event_id="event-1",
    user_id=9001,
    tenant_id=42,
    session_id="session-1",
    message="hello",
    model_config={"model_id": "active-model", "api_key": "sk-secret"},
    source_module="module_wms",
    source_feature="stock_warning",
    prompt_key="wms.warning_advice.v1",
    duration_ms=123,
    status="success",
)

dumped = record.to_safe_dict()
assert dumped["prompt_key"] == "wms.warning_advice.v1"
assert dumped["duration_ms"] == 123
assert "api_key" not in dumped["model_config"]
```

- [ ] **Step 2: Add audit fields**

Modify `AiCallAuditRecord`:

```python
prompt_key: str | None = None
business_id: str | None = None
duration_ms: int | None = None
input_tokens: int | None = None
output_tokens: int | None = None
```

Add the same fields to `to_safe_dict()`.

- [ ] **Step 3: Capture duration in runtime**

In `AiRuntimeService.chat()`, wrap the call:

```python
from time import perf_counter

started_at = perf_counter()
...
duration_ms = int((perf_counter() - started_at) * 1000)
```

Pass `duration_ms=duration_ms` to `AiCallAuditRecord` on success and error.

- [ ] **Step 4: Run tests**

```bash
cd backend
uv run pytest tests/test_ai_platform_foundation.py tests/test_wms_intelligence.py -q
```

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add backend/app/plugin/module_ai/chat/audit.py backend/app/plugin/module_ai/chat/service.py backend/tests/test_ai_platform_foundation.py
git commit -m "feat: 完善AI调用审计元数据"
```

## 6. Verification Matrix

Run these before declaring the intelligence landing work complete:

```bash
cd backend
uv run pytest tests/test_wms_intelligence.py tests/test_ai_platform_foundation.py tests/test_wms_stock_ledger.py tests/test_wms_demo_data.py -q
uv run ruff check app/api/v1/module_wms app/plugin/module_ai tests/test_wms_intelligence.py tests/test_ai_platform_foundation.py
```

```bash
cd frontend/web
node_modules/.bin/vue-tsc --noEmit
node_modules/.bin/vite build --mode dev
```

Manual smoke checks:

1. Open `http://127.0.0.1:41291/#/module-wms/dashboard`.
2. Confirm the top section shows `智能摘要` or `规则摘要`.
3. Stop or break the model config temporarily in a dev database copy and confirm dashboard still shows a rule fallback summary.
4. Open WMS warning page and click `智能建议`; confirm advice appears and source tag is visible.
5. Confirm normal WMS stock operations still work without AI.

## 7. Acceptance Criteria

The implementation is acceptable when:

1. WMS dashboard displays a dynamic warehouse summary from rule data and upgrades to AI wording when model calls succeed.
2. WMS warning page can show handling advice for safety stock and shortage warnings.
3. Outbound recommendation exposes deterministic scores and rule reasons.
4. AI failure does not break dashboard, warning, recommendation, or stock operations.
5. All AI calls are made through platform default model configuration.
6. No WMS code stores API keys, model keys, or tenant-level LLM settings.
7. Frontend labels AI output clearly as `AI 摘要` or `AI 智能建议`.
8. Backend tests cover rule fallback and AI failure paths.
9. Frontend type check and backend test matrix pass.

## 8. Rollout Order

Use this order to keep risk low:

1. Contracts and rule fallback.
2. AI enhancement with fallback.
3. API exposure.
4. Dashboard summary.
5. Warning advice.
6. Outbound recommendation explanation.
7. Stock check and demo-data enhancement.
8. Audit metadata and operational hardening.

Each step must be independently shippable. If a later AI feature is delayed, the earlier dashboard and warning intelligence still remain useful.

## 9. Self-Review

Spec coverage:

- Platform default LLM usage is covered in Tasks 3, 4, 5, and 10.
- Rule-first WMS intelligence is covered in Tasks 2, 5, and 6.
- Dashboard, warning, outbound recommendation, stock check, and demo scenario are listed in target scope; dashboard and warning are first implementation path.
- Frontend WMS-specific intelligent surfaces are covered in Tasks 7, 8, and 9.
- Failure fallback and audit metadata are covered in Tasks 3 and 10.

Placeholder scan:

- This plan avoids `TBD`, vague “add error handling” instructions, and unbounded “write tests” steps.
- Every implementation task names exact files and commands.

Type consistency:

- Backend response source values are `ai` and `rule_fallback`.
- Frontend uses the same source union type.
- WMS endpoints consistently live under `/wms/intelligence`.
