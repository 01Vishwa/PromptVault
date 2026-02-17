# PromptVault — Git-like Version Control for LLM Prompts

Production-grade platform for treating LLM prompts as first-class versioned artefacts with immutable versions, multi-provider execution, deployment pointers, and diff comparison.

## Architecture

| Layer | Stack |
|-------|-------|
| **Frontend** | Next.js 14 (App Router), shadcn/ui, Supabase Auth |
| **Backend** | FastAPI (async), Pydantic v2, LiteLLM |
| **Database** | Supabase (PostgreSQL with Row-Level Security) |
| **Auth** | Supabase Auth (JWT) — shared between frontend + backend |

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full system design.

## Quick Start

### 1. Supabase Setup

1. Create a [Supabase project](https://supabase.com/dashboard)
2. Open the SQL Editor and run `backend/supabase/migrations/001_initial_schema.sql`
3. Copy your project URL, anon key, service role key, and JWT secret from **Settings → API**

### 2. Backend

```bash
cd backend
cp .env.example .env
# Edit .env with your Supabase credentials + LLM API keys

pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
```

Verify: `curl http://localhost:8000/health` → `{"status":"ok"}`

API docs: http://localhost:8000/api/docs

### 3. Frontend

```bash
cd frontend
cp .env.local.example .env.local
# Edit .env.local with your Supabase URL + anon key

npm install
npm run dev
```

Open http://localhost:3000

### 4. Docker Compose (alternative)

```bash
# Set env vars in backend/.env and export Supabase vars for frontend
docker compose up -d
```

## API Endpoints

| Resource | Endpoints |
|----------|-----------|
| **Prompts** | `POST/GET/PATCH/DELETE /api/v1/prompts/` |
| **Versions** | `POST/GET /api/v1/prompts/{id}/versions`, `GET .../versions/{from}/diff/{to}` |
| **Deployments** | `POST/GET/DELETE /api/v1/prompts/{id}/deployments/` |
| **Execute** | `POST /api/v1/execute` — multi-provider parallel execution |
| **Serve** | `POST /api/v1/serve/{slug}` — public endpoint (no auth) |

## Testing

```bash
# Backend (35 tests)
cd backend
pytest -v

# Frontend (38 tests)
cd frontend
npm test
```

Backend tests mock Supabase and run against the ASGI app — no database required.
Frontend tests use Vitest + React Testing Library.

## Tech Stack

- **API**: FastAPI (async) + Uvicorn
- **Database**: Supabase (PostgreSQL + RLS)
- **Auth**: Supabase Auth (JWT), python-jose
- **LLM**: LiteLLM (OpenAI, Anthropic, Google, Azure)
- **Diff**: difflib + diff-match-patch
- **Validation**: Pydantic v2
- **Frontend**: Next.js 14, React 18, Tailwind CSS, Radix UI
