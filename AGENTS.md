# Repository Guidelines

## Project Structure & Module Organization

This repository is the EE WMS product repo based on the maintainable FastapiAdmin framework fork at remote `framework`.

- `backend/`: FastAPI backend, SQLAlchemy models, Alembic migrations, scripts, seed packs, and tests.
- `backend/app/api/v1/`: core API modules. WMS business APIs should use the `module_wms` namespace.
- `backend/app/plugin/`: optional framework plugins such as AI, generator, task, and workflow.
- `backend/app/assemblies/`: reusable framework capability assembly profiles.
- `frontend/web/`: Vue 3 + Vite + TypeScript admin UI.
- `frontend/web/src/components/`: reusable `fa-*` UI components; prefer these before adding new primitives.
- `frontend/web/src/views/`: page views. WMS pages should live under `views/module_wms`.
- `frontend/app/`: UniApp mobile/H5 client placeholder.
- `docs/`: framework and product documentation.

## Framework vs Product Boundaries

Treat framework and WMS business code as separate layers. Put reusable platform capabilities in the framework layer when they help more than WMS: tenant configuration, permissions, menu/route machinery, upload categories, task/notification foundations, AI model configuration, code generation templates, shared `fa-*` components, dashboard shells, security fixes, and capability assembly.

Keep WMS domain behavior in the product layer: warehouse entities, stock ledger rules, inbound/outbound workflows, barcode operations, inventory warnings, traceability, and MES integration. Use `module_wms` for backend APIs, frontend routes, permissions, and seed data.

When a framework issue blocks WMS, document the symptom, affected files, expected framework behavior, WMS impact, and whether the fix should land in `framework` first or stay product-local temporarily.

## Build, Test, and Development Commands

Backend commands run from `backend/`:

```bash
uv sync
uv run python main.py upgrade --env=dev
uv run python main.py run --env=dev
uv run pytest tests -q
uv run ruff check app tests
```

Frontend commands run from `frontend/web/`:

```bash
pnpm install
pnpm dev
pnpm type-check
pnpm test
pnpm build
pnpm lint
```

Backend defaults to `localhost:8001`; the web dev server defaults to `localhost:5180`.

## Coding Style & Naming Conventions

Python targets 3.12, uses 4-space indentation, type hints, Ruff formatting rules, and SQLAlchemy 2 style models. Follow existing `controller.py`, `service.py`, `crud.py`, `model.py`, and `schema.py` patterns.

Frontend code uses Vue SFCs, TypeScript, Element Plus, Tailwind utilities, ESLint, Prettier, Stylelint, and existing `fa-*` components. Use `PascalCase` for components, `camelCase` for variables/functions, and permission codes such as `module_wms:<resource>:<action>`.

## Testing Guidelines

Backend tests use `pytest` and `pytest-asyncio`; place tests under `backend/tests/` with names like `test_*.py`. Cover tenant isolation, permission denial, menu/route consistency, and CRUD/service behavior for WMS modules. Frontend tests use Vitest; keep specs under `frontend/web/src/__tests__/` or near the changed UI logic.

## Commit & Pull Request Guidelines

History uses concise Chinese messages and Conventional Commit prefixes, for example `feat: 增加业务任务与通知样例底座`, `fix: 修复租户配置品牌与加载契约`, and `merge: 同步最新框架能力到WMS`.

Pull requests should include scope, behavior changes, database/migration impact, seed or permission changes, verification commands, screenshots for visible UI changes, and a note on framework-vs-product placement. Do not commit local secrets, `.env.dev`, `node_modules`, virtualenvs, logs, generated caches, uploads, or product draft files unless explicitly required.

## Security & Configuration Tips

Keep local backend config in `backend/env/.env.dev`; it is ignored by git. Current dev database is PostgreSQL `ee_wms_dev` with Redis on `127.0.0.1:6379`. Never hard-code API keys, tenant credentials, SMTP secrets, or plaintext model keys in source files or API responses.
