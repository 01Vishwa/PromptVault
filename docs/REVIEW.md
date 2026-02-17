# PromptVault — Code Review & Build Notes

## Build Summary

| Section | Scope | Status |
|---------|-------|--------|
| 1 | Database + Backend (Supabase migration, FastAPI routes, services, schemas) | ✅ Complete |
| 2 | Frontend (Next.js 14 App Router, shadcn/ui, 9 feature components) | ✅ Complete |
| 3 | Integration & Cleanup (dead code removal, schema fixes, 35 backend tests) | ✅ Complete |
| 4 | Frontend Polish (a11y, debounce, error boundaries, deploy confirmation, playground UX) | ✅ Complete |
| 5 | Testing, CI/CD & Documentation (38 frontend tests, CI rewrite, docs rewrite) | ✅ Complete |

## Architecture Decisions

### Supabase over raw PostgreSQL + SQLAlchemy

The original blueprint specified 13 tables with SQLAlchemy ORM, Alembic migrations, Celery workers, Redis cache, and pgvector. This was replaced with a Supabase-based architecture for the MVP:

- **4 tables** (prompts, prompt_versions, deployments, executions) with Row-Level Security
- **Supabase Auth** shared between frontend and backend (single JWT)
- **No ORM** — direct Supabase PostgREST client for all queries
- **No workers** — LLM execution is synchronous via `asyncio.gather`

This eliminated ~2000 LoC of dead code (models, workers, SDK, infrastructure layers) that referenced non-existent Settings fields.

### LiteLLM over raw OpenAI/Anthropic SDKs

A single `litellm.acompletion()` call handles all providers with uniform response parsing, token counting, and cost estimation. Provider selection is done via `provider/model` string format (e.g., `openai/gpt-4o-mini`).

### Vitest over Jest

Vitest was chosen for frontend testing because:
- Native ESM support (no transform issues with Next.js 14)
- Faster startup than Jest with SWC
- Compatible with React Testing Library

## Issues Found & Fixed

### Section 3: Integration & Cleanup

| # | Issue | Fix |
|---|-------|-----|
| 1 | `model_config` field name conflicted with Pydantic v2 reserved name | Renamed to `llm_config` with `alias="model_config"` for JSON compatibility |
| 2 | `EvaluationJobCreate` referenced `EvaluatorConfig` before it was defined | Moved `EvaluatorConfig` class definition above its usage |
| 3 | `deployment.deployed_by` typed as `uuid.UUID` but Supabase returns string | Changed to `str` |
| 4 | 35 tests failed due to `get_user_client()` trying to parse test JWT | Patched at router module level instead of core module |
| 5 | ~2000 LoC of dead SQLAlchemy/Celery/Redis code | Removed entirely (models, workers, SDK, infrastructure) |

### Section 4: Frontend Polish

| # | Issue | Fix |
|---|-------|-----|
| 1 | `useAuth` created new Supabase client every render | Wrapped in `useMemo` |
| 2 | `useAsync` deps spread pattern fragile | Replaced with `useRef` for deps |
| 3 | No global error boundary | Added `app/error.tsx` |
| 4 | Search fired API call per keystroke | Added `useDebounce(300ms)` |
| 5 | Dialog form state persisted across open/close | Reset on `onOpenChange(false)` |
| 6 | PromptDetailView loading/error states discarded | Wired up loading spinner + error card |
| 7 | Deploy to production had no confirmation | Added confirmation dialog |
| 8 | Serve endpoint showed "your-slug" placeholder | Shows actual prompt slug |
| 9 | Playground required pasting raw UUID | Added prompt → version dropdown selectors |
| 10 | Sign-up had no success feedback | Shows "Check your email" message |
| 11 | Backend Dockerfile healthcheck used unavailable `httpx` | Changed to `curl` |

### Section 5: Testing, CI/CD & Docs

| # | Issue | Fix |
|---|-------|-----|
| 1 | CI referenced Alembic, PostgreSQL, Redis (non-existent) | Rewrote for Supabase mock tests |
| 2 | No frontend CI steps | Added lint, type-check, build, test jobs |
| 3 | No frontend tests existed | Created 38 Vitest tests |
| 4 | ARCHITECTURE.md described wrong system (13 tables, Celery, pgvector) | Complete rewrite for actual 4-table Supabase architecture |
| 5 | REVIEW.md referenced non-existent files | Complete rewrite |
| 6 | `pyproject.toml` had non-standard build-backend | Fixed to `setuptools.build_meta` |

## Test Coverage

### Backend: 35 tests (pytest)

- `test_prompts.py` — 5 tests (CRUD operations, not-found handling)
- `test_versions.py` — 3 tests (create, list, diff)
- `test_deployments.py` — 3 tests (deploy, list, undeploy)
- `test_parser.py` — 7 tests (variable extraction, template rendering)
- `test_diff.py` — 6 tests (unified diff, hash determinism)
- `test_schemas.py` — 10 tests (Pydantic validation edge cases)
- `test_health.py` — 1 test (smoke)

### Frontend: 38 tests (Vitest + React Testing Library)

- `hooks.test.ts` — 7 tests (useDebounce timing, useAsync lifecycle)
- `api.test.ts` — 9 tests (URL construction, auth headers, error handling)
- `types.test.ts` — 9 tests (TypeScript interface shape validation)
- `LoginPage.test.tsx` — 5 tests (form rendering, auth flow, error/success states)
- `PromptListView.test.tsx` — 5 tests (loading, empty, data, search, new button)
- `DiffViewer.test.tsx` — 3 tests (loading, render, error)

## Remaining Recommendations

1. **E2E tests** — Add Playwright tests for critical user flows (create prompt → create version → deploy)
2. **Rate limiting** — Add rate limiting to the serve endpoint
3. **Evaluation system** — Schemas exist but no API routes; implement when needed
4. **Monitoring** — Add structured logging and error tracking (Sentry)
5. **RBAC** — Currently single-user RLS; add team/org support if needed