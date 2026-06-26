# Auth Login Features Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the login page and related public auth endpoints configurable as framework-level capabilities.

**Architecture:** Extend the existing public `/system/config/info` response with `authFeatures`, then let the frontend login view consume it through `assemblyStore`. Backend endpoints must enforce the same feature flags so hidden UI entries are not still callable.

**Tech Stack:** FastAPI, Pydantic, Vue 3, Pinia, Element Plus, Vitest, pytest.

---

### Task 1: Backend Auth Feature Contract

**Files:**
- Modify: `backend/app/config/setting.py`
- Modify: `backend/app/api/v1/module_system/config/schema.py`
- Modify: `backend/app/api/v1/module_system/config/controller.py`
- Test: `backend/tests/test_auth_feature_config.py`

- [ ] **Step 1: Add settings**

Add framework defaults:

```python
AUTH_LOGIN_REGISTER_ENABLE: bool = False
AUTH_LOGIN_FORGOT_PASSWORD_ENABLE: bool = True
AUTH_PASSWORD_RESET_MODE: Literal["email_code", "legacy_mobile", "disabled"] = "email_code"
AUTH_LOGIN_MOBILE_ENABLE: bool = False
AUTH_LOGIN_QR_ENABLE: bool = False
AUTH_LOGIN_REMEMBER_ME_ENABLE: bool = True
AUTH_LOGIN_DEMO_ACCOUNTS_ENABLE: bool = False
```

OAuth keeps using `OAUTH_ENABLE`, but public config must only expose configured providers.

- [ ] **Step 2: Expose public auth features**

Add Pydantic output models:

```python
class AuthFeaturesOut(BaseModel):
    register: bool
    forgotPassword: bool
    passwordResetMode: Literal["email_code", "legacy_mobile", "disabled"]
    oauth: bool
    oauthProviders: list[Literal["wechat", "qq", "github", "gitee"]]
    mobileLogin: bool
    qrLogin: bool
    rememberMe: bool
    demoAccounts: bool
```

Return `{ assembly, authFeatures }` from `/system/config/info`.

- [ ] **Step 3: Test public defaults**

Run:

```bash
cd backend
uv run pytest tests/test_auth_feature_config.py -q
```

Expected: config response includes conservative defaults and no OAuth providers when credentials are empty.

### Task 2: Backend Endpoint Enforcement

**Files:**
- Modify: `backend/app/api/v1/module_system/auth/controller.py`
- Modify: `backend/app/api/v1/module_system/user/controller.py`
- Test: `backend/tests/test_auth_feature_config.py`

- [ ] **Step 1: Register endpoint**

Guard `/system/auth/tenant/register` with `AUTH_LOGIN_REGISTER_ENABLE`; return 404 when disabled.

- [ ] **Step 2: Password reset endpoints**

Guard email-code endpoints with `AUTH_LOGIN_FORGOT_PASSWORD_ENABLE` and `AUTH_PASSWORD_RESET_MODE == "email_code"`.

Guard legacy `/system/user/password/forget` with `AUTH_PASSWORD_RESET_MODE == "legacy_mobile"`.

- [ ] **Step 3: OAuth providers**

Keep existing `OAUTH_ENABLE` 404. Also reject a provider unless it is both supported and configured.

- [ ] **Step 4: Test disabled behavior**

Tests must cover disabled register, disabled reset mode, legacy reset disabled by default, and OAuth configured-provider filtering.

### Task 3: Frontend Login Feature Consumption

**Files:**
- Modify: `frontend/web/src/config/assembly/default.ts`
- Modify: `frontend/web/src/store/modules/assembly.store.ts`
- Modify: `frontend/web/src/api/module_system/config.ts`
- Modify: `frontend/web/src/components/views/fa-login/forms/FaLoginAccountForm.vue`
- Modify: `frontend/web/src/components/views/fa-login/widgets/FaLoginThirdPartySection.vue`
- Modify: `frontend/web/src/views/module_system/auth/login/index.vue`
- Test: `frontend/web/src/__tests__/login-password-reset.spec.ts`

- [ ] **Step 1: Add TS auth feature type**

Add `AuthFeatures` to the public config type and default it to the backend conservative defaults.

- [ ] **Step 2: Account form props**

Add props:

```ts
showRemember
showForget
showMobileLogin
showQrLogin
showRegister
showDemoAccounts
oauthEnabled
oauthProviders
```

Render the corresponding controls only when true.

- [ ] **Step 3: Login view guards**

Load public config before rendering decisions. Prevent programmatic panel switching to disabled panels; if current panel becomes disabled, return to account login.

- [ ] **Step 4: OAuth section**

Re-enable `FaLoginThirdPartySection` only when `oauthEnabled && oauthProviders.length > 0`; providers come from config, not hardcoded UI visibility.

### Task 4: Verification and Commit

**Files:**
- No new production files expected beyond tasks above.

- [ ] **Step 1: Run backend checks**

```bash
cd backend
uv run ruff check app tests
uv run pytest tests/test_auth_feature_config.py tests/test_password_reset_email.py -q
```

- [ ] **Step 2: Run frontend checks**

```bash
cd frontend/web
corepack pnpm test -- src/__tests__/login-password-reset.spec.ts
corepack pnpm type-check
corepack pnpm build
```

- [ ] **Step 3: Review diff and commit**

Commit as:

```bash
git commit -m "feat: 增加登录能力配置中心"
```
