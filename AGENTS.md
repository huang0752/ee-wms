# Repository Guidelines

## Project Structure & Module Organization

This repository is a FastapiAdmin-based EE WMS product monorepo.

- `backend/`: FastAPI backend, SQLAlchemy models, Alembic migrations, scripts, templates, and tests.
- `backend/app/api/v1/`: core API modules. WMS business modules should use the `module_wms` namespace.
- `backend/app/plugin/`: optional framework plugins such as AI, generator, task, and workflow.
- `frontend/web/`: Vue 3 + Vite + TypeScript admin UI.
- `frontend/web/src/components/`: reusable `fa-*` UI components; prefer these before adding new primitives.
- `frontend/web/src/views/`: page views. WMS pages should live under `views/module_wms`.
- `frontend/app/`: UniApp mobile/H5 client.
- `docs/`: framework/product documentation.
- `docker/`: deployment assets.

## Framework vs Product Boundaries

This product is based on the maintainable FastapiAdmin framework fork at remote `framework`. Treat framework and WMS business code as separate layers.

Put reusable platform capabilities in the framework layer when they are useful beyond WMS, such as tenant configuration, permissions, menu/route machinery, upload categories, task/notification foundations, AI model configuration, code generation templates, shared `fa-*` components, dashboard shells, and security fixes.

Keep WMS-specific domain behavior in the product layer: warehouse entities, stock ledger rules, inbound/outbound workflows, barcode operations, inventory warnings, traceability, and MES integration. Use `module_wms` naming for backend APIs, frontend routes, permissions, and seed data.

When a framework issue blocks WMS, document it clearly before patching around it. Include the symptom, affected files, expected framework behavior, WMS impact, and whether the fix should land in `framework` first or remain product-local temporarily. Prefer fixing the framework when two or more products would benefit.

## Build, Test, and Development Commands

Backend:

```bash
cd backend
uv sync
uv run python main.py upgrade --env=dev
uv run python main.py run --env=dev
uv run pytest
uv run ruff check .
```

Frontend Web:

```bash
cd frontend/web
pnpm install
pnpm run dev
pnpm run type-check
pnpm run test
pnpm run build
pnpm run lint
```

Run backend on `localhost:8001`; web dev server defaults to `localhost:5180`.

## Coding Style & Naming Conventions

Python targets 3.12, uses 4-space indentation, type hints, Pydantic schemas, and SQLAlchemy 2 style models. Follow existing `controller.py`, `service.py`, `crud.py`, `model.py`, and `schema.py` module patterns.

Frontend code uses Vue SFCs, TypeScript, Element Plus, Tailwind utilities, and existing `fa-*` components. Use `PascalCase` for components, `camelCase` for variables/functions, and `module_wms:<resource>:<action>` for WMS permission codes.

## Testing Guidelines

Backend tests use `pytest` and `pytest-asyncio`; place tests under `backend/tests/` with names like `test_*.py`. Cover tenant isolation, permission denial, and CRUD/service behavior for WMS modules. Frontend tests use Vitest; keep specs near relevant UI logic or in `src/__tests__/`.

## Commit & Pull Request Guidelines

History uses concise Chinese messages and conventional prefixes, for example `feat: 增加业务任务与通知样例底座`, `fix: 修复租户配置品牌与加载契约`, and `初始化WMS产品基座配置`.

Pull requests should include scope, behavior changes, database/migration impact, test results, screenshots for visible UI changes, and a note on framework-vs-product placement. Do not commit local secrets, `.env.dev`, `node_modules`, virtualenvs, logs, generated caches, or upload artifacts.

## Security & Configuration Tips

Keep local backend config in `backend/env/.env.dev`; it is ignored by git. Current dev database is PostgreSQL `ee_wms_dev` with Redis on `127.0.0.1:6379`. Never hard-code API keys or tenant-specific credentials in source files.
