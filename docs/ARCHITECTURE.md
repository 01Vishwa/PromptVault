# PromptVault — Architecture

## 1. System Overview

PromptVault is a Git-like version control system for LLM prompts. It treats prompts as first-class versioned artefacts with immutable versions, multi-provider execution, deployment pointers, and diff comparison.

```
┌───────────────────────────────────┐
│        Next.js 14 Frontend        │  ← App Router, shadcn/ui, Supabase Auth
│  (React 18 + Tailwind + Radix)    │
└──────────────┬────────────────────┘
               │ REST (JWT in Authorization header)
┌──────────────▼────────────────────┐
│       FastAPI Backend (async)     │  ← Pydantic v2, LiteLLM
│  Routes → Services → Supabase    │
└──────────────┬────────────────────┘
               │ Supabase client (PostgREST)
┌──────────────▼────────────────────┐
│    Supabase (PostgreSQL + RLS)    │  ← 4 tables, Row-Level Security
│         + Supabase Auth           │
└───────────────────────────────────┘
```

## 2. Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 14.2 (App Router), React 18, Tailwind CSS, shadcn/ui (Radix) |
| Backend | FastAPI (async), Python 3.11+, Pydantic v2 |
| Database | Supabase PostgreSQL with Row-Level Security |
| Auth | Supabase Auth (JWT) — shared between frontend and backend |
| LLM | LiteLLM (OpenAI, Anthropic, Google, Azure — unified interface) |
| Diff | difflib (unified diff) + diff-match-patch (character-level patches) |
| CI | GitHub Actions (lint, type-check, test, build, Docker) |

## 3. Repository Structure

```
├── .github/workflows/ci.yml     # CI pipeline
├── docker-compose.yml            # API + frontend containers
├── README.md
├── docs/
│   ├── ARCHITECTURE.md           # This file
│   └── REVIEW.md                 # Code review notes
├── backend/
│   ├── Dockerfile
│   ├── pyproject.toml
│   ├── .env.example
│   ├── supabase/migrations/
│   │   └── 001_initial_schema.sql
│   ├── app/
│   │   ├── main.py               # FastAPI app, CORS, exception handlers
│   │   ├── config.py             # Pydantic Settings
│   │   ├── api/v1/               # Route handlers
│   │   │   ├── prompts.py        # CRUD for prompts
│   │   │   ├── versions.py       # Version creation, listing, diff
│   │   │   ├── execute.py        # Multi-provider execution
│   │   │   ├── deployments.py    # Deploy / undeploy
│   │   │   └── serve.py          # Public serve endpoint
│   │   ├── core/
│   │   │   ├── auth.py           # JWT validation (python-jose)
│   │   │   └── supabase.py       # Client factory (service-role + user-scoped)
│   │   ├── schemas/              # Pydantic request/response models
│   │   └── services/             # Business logic
│   │       ├── prompt.py         # Prompt CRUD via Supabase
│   │       ├── version.py        # Immutable versions, SHA-256 hashing
│   │       ├── deployment.py     # Environment-based deployment pointers
│   │       ├── llm.py            # LiteLLM multi-provider execution
│   │       ├── parser.py         # {{variable}} extraction & rendering
│   │       └── diff.py           # Diff computation
│   └── tests/                    # 35 pytest tests (mocked Supabase)
└── frontend/
    ├── Dockerfile
    ├── package.json
    ├── vitest.config.ts
    └── src/
        ├── app/                  # Next.js App Router pages
        ├── components/           # UI components (9 feature + 8 shadcn/ui)
        └── lib/                  # API client, hooks, types, Supabase client
```

## 4. Database Schema

Four tables in Supabase PostgreSQL, all protected by Row-Level Security:

```sql
prompts              prompt_versions        deployments           executions
─────────            ───────────────        ───────────           ──────────
id (UUID PK)         id (UUID PK)           id (UUID PK)          id (UUID PK)
user_id (UUID)  ←──  prompt_id (FK)    ──→  prompt_id (FK)        prompt_version_id (FK)
name                 version_number         prompt_version_id (FK) user_id
slug (UNIQUE)        version_hash           environment            model_provider
description          template_text          deployed_by            model_name
tags (TEXT[])        system_prompt          deployed_at            rendered_prompt
is_archived          variables (TEXT[])     is_active              response_text
created_at           model_config (JSONB)                          tokens_in / tokens_out
updated_at           commit_message                                latency_ms
                     author_id                                     cost_estimate
                     created_at                                    status / error_message
```

### Row-Level Security

- All tables enforce `auth.uid() = user_id` for SELECT/INSERT/UPDATE/DELETE
- The `serve` endpoint uses a service-role client to bypass RLS (public access)
- `prompt_versions` links to `prompts.user_id` via a subquery policy

### Key Constraints

- `(prompt_id, version_number)` — UNIQUE per prompt
- `(prompt_id, version_hash)` — UNIQUE (content-addressable dedup)
- `(prompt_id, environment)` — UNIQUE active deployment per environment
- `version_number` auto-increments via a trigger function

## 5. Authentication Flow

```
Frontend                    Supabase Auth               Backend
────────                    ─────────────               ───────
signInWithPassword() ──────→ Returns JWT ──────┐
                                               │
Stores in cookie (SSR) ◄──────────────────────┘
                                               
API call ──────────────────────────────────────→ Authorization: Bearer <JWT>
                                                 │
                                                 ├─ python-jose validates JWT
                                                 ├─ Extracts user_id (sub claim)
                                                 └─ Creates user-scoped Supabase client
                                                    (RLS enforces row ownership)
```

- Frontend uses `@supabase/ssr` for cookie-based session management
- Backend validates JWT signature using `SUPABASE_JWT_SECRET`
- User-scoped Supabase client automatically applies RLS policies

## 6. API Design

All routes under `/api/v1/`:

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/prompts` | ✓ | Create prompt |
| `GET` | `/prompts` | ✓ | List user's prompts (search, archive filter) |
| `GET` | `/prompts/{id}` | ✓ | Get single prompt |
| `PATCH` | `/prompts/{id}` | ✓ | Update prompt metadata |
| `DELETE` | `/prompts/{id}` | ✓ | Delete prompt |
| `POST` | `/prompts/{id}/versions` | ✓ | Create immutable version |
| `GET` | `/prompts/{id}/versions` | ✓ | List versions |
| `GET` | `/prompts/{id}/versions/{number}` | ✓ | Get version by number |
| `GET` | `/prompts/{id}/versions/{from}/diff/{to}` | ✓ | Diff two versions |
| `POST` | `/execute` | ✓ | Execute version across providers |
| `POST` | `/prompts/{id}/deployments` | ✓ | Deploy version to environment |
| `GET` | `/prompts/{id}/deployments` | ✓ | List deployments |
| `DELETE` | `/prompts/{id}/deployments/{env}` | ✓ | Undeploy from environment |
| `POST` | `/serve/{slug}` | ✗ | Public: resolve slug → execute |

## 7. Key Design Patterns

### Content-Addressable Versions

Each version gets a deterministic SHA-256 hash from `template_text + system_prompt + model_config`. Creating a version with identical content to an existing one returns the existing version (idempotent).

### Deployment Pointers

Deployments are environment-specific pointers (`production`, `staging`, `development`) to a specific prompt version. Only one active deployment per environment per prompt (UPSERT semantics).

### Multi-Provider Execution

The execute endpoint runs the same rendered prompt across multiple LLM providers in parallel using `asyncio.gather`. Each execution result is persisted to the `executions` table with token counts, latency, and cost estimates.

### Template Engine

Variables use `{{variable_name}}` syntax. The parser extracts variables via regex and renders templates by substitution. Variables are auto-detected and stored on version creation.

## 8. Frontend Architecture

### App Router Pages

| Route | Component | Purpose |
|-------|-----------|---------|
| `/` | PromptListView | Browse, search, create prompts |
| `/prompts/[promptId]` | PromptDetailView | Version list, template viewer, diff, deploy |
| `/playground` | PlaygroundView | Execute prompts across providers |
| `/login` | LoginPage | Supabase email/password auth |

### Component Hierarchy

```
RootLayout
└── AuthShell (auth gate)
    ├── Navbar (navigation, sign-out)
    └── Page Content
        ├── PromptListView
        │   └── CreatePromptDialog
        ├── PromptDetailView
        │   ├── CreateVersionDialog
        │   ├── DiffViewer
        │   └── DeployPanel (with production confirmation)
        └── PlaygroundView (prompt/version selectors)
```

### Data Fetching

- `useAsync(fetcher, deps)` — generic hook for API calls with loading/error states
- `useDebounce(value, ms)` — debounce for search input
- `useAuth()` — Supabase auth state, signIn/signUp/signOut
- All API calls go through `lib/api.ts` which attaches the Supabase JWT

## 9. Testing Strategy

### Backend (35 tests)

| Category | Count | Approach |
|----------|-------|----------|
| API routes | 11 | ASGI TestClient, mocked Supabase client |
| Schemas | 10 | Pydantic validation edge cases |
| Parser | 7 | Variable extraction & template rendering |
| Diff | 6 | Unified diff & hash computation |
| Health | 1 | Smoke test |

Tests mock the Supabase client at the router module level to avoid real JWT parsing or network calls.

### Frontend (38 tests)

| Category | Count | Approach |
|----------|-------|----------|
| Hooks | 7 | renderHook (useDebounce, useAsync) |
| API client | 9 | Mocked fetch, verify URLs/methods/headers |
| Type shapes | 9 | Compile-time type safety assertions |
| Components | 13 | React Testing Library (LoginPage, PromptListView, DiffViewer) |

### CI Pipeline

Six parallel jobs: backend-lint, backend-typecheck, backend-test, frontend-check (lint + tsc), frontend-build, frontend-test. Docker image builds on main branch merges.

## 10. Configuration

### Backend Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `SUPABASE_URL` | ✓ | Supabase project URL |
| `SUPABASE_ANON_KEY` | ✓ | Supabase anon/public key |
| `SUPABASE_SERVICE_ROLE_KEY` | ✓ | Service role key (for serve endpoint) |
| `SUPABASE_JWT_SECRET` | ✓ | JWT secret for token validation |
| `OPENAI_API_KEY` | | OpenAI API key (for LiteLLM) |
| `ANTHROPIC_API_KEY` | | Anthropic API key |
| `GOOGLE_API_KEY` | | Google AI API key |
| `ALLOWED_ORIGINS` | | CORS origins (comma-separated) |
| `ENV` | | Environment name (default: development) |

### Frontend Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `NEXT_PUBLIC_API_URL` | ✓ | Backend API base URL |
| `NEXT_PUBLIC_SUPABASE_URL` | ✓ | Supabase project URL |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | ✓ | Supabase anon key |

## 11. Deployment

### Docker Compose

```yaml
services:
  api:        # FastAPI on :8000, reads backend/.env
  frontend:   # Next.js standalone on :3000, env vars from compose
```

Both images are multi-stage builds. The backend runs as non-root user `axiom` with 4 Uvicorn workers. The frontend uses Next.js standalone output mode.

### Production Checklist

- [ ] Run `001_initial_schema.sql` in Supabase SQL Editor
- [ ] Configure Supabase Auth (email provider, redirect URLs)
- [ ] Set all env vars in `.env` / `.env.local`
- [ ] Set `ALLOWED_ORIGINS` to your frontend domain
- [ ] Review RLS policies match your access requirements
