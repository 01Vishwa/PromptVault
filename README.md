# Agent Evaluation Framework

A production-grade evaluation harness for LLM-based autonomous agents. Built as a university final-year project, it captures every decision step an agent takes (LLM calls, tool invocations, reasoning traces) via OpenTelemetry, then grades those trajectories through a two-stage judge: deterministic rule checks followed by LLM-as-Judge scoring using Anthropic Claude.

The framework closes the feedback loop automatically — every annotated failure is written to a golden evaluation set and becomes a permanent regression test, creating an "Agent Quality Flywheel" that makes the system smarter with every failure detected.

## Key Features

- **Zero-intrusion instrumentation** — wraps any LangChain agent via callback handler; no changes to agent code required
- **Two-tier judge** — deterministic rule checks (100% reproducible) + LLM-as-Judge with structured rubric (5 dimensions: correctness, tool accuracy, efficiency, hallucination, robustness)
- **Cost-aware routing** — rule score > 0.9 skips LLM judge; < 0.5 fast-fails to HITL queue
- **Safety-first evaluation** — `must_not_contain` checkpoints cause instant score=0 with `is_safety_failure=True`
- **Regression flywheel** — HITL annotations auto-generate pytest regression tests
- **Full observability** — OpenTelemetry spans → Jaeger trace explorer; structured JSONL run logs
- **REST API + Dashboard** — FastAPI backend with React 18 frontend (system health + quality health views)
- **CI/CD integration** — GitHub Actions workflow with configurable pass-rate gate

## Tech Stack

| Layer | Technology |
|---|---|
| Agent framework | LangChain 0.2 + Anthropic Claude |
| Instrumentation | OpenTelemetry SDK + OTLP/gRPC → Jaeger |
| LLM Judge | Anthropic Claude Haiku |
| Storage | PostgreSQL 15 + JSONB |
| ORM / migrations | SQLAlchemy 2.0 async + Alembic |
| REST API | FastAPI + Uvicorn |
| Dashboard | React 18 + TypeScript + Recharts + React Flow + Tailwind |
| Testing | pytest + pytest-asyncio |
| Reliability metric | Cohen's κ (sklearn) |

## Quick Start

```bash
# 1. Clone and configure
git clone <repo-url>
cd agent-eval-framework
cp .env.example .env
# Edit .env and set ANTHROPIC_API_KEY=sk-ant-...

# 2. Install Python dependencies
pip install -e ".[dev]"

# 3. Start infrastructure (Postgres + Jaeger + Redis)
make up
# Jaeger UI: http://localhost:16686
# Postgres:  localhost:5432 / db=agent_eval / pw=eval123

# 4. Run database migrations
alembic upgrade head

# 5. Verify all prerequisites
python scripts/verify_setup.py

# 6. Smoke-test the agent
python agents/react.py

# 7. Smoke-test OTel tracing (check http://localhost:16686)
python harness/tracer.py

# 8. Run the full evaluation suite
python -m harness.runner --tasks all

# 9. Start the REST API
uvicorn api.app:app --reload
# Docs: http://localhost:8000/api/docs
```

## Project Structure

```
agent-eval-framework/
│
├── harness/              # Instrumentation core (OTel + JSONL + LangChain middleware)
│   ├── tracer.py         # OTel span setup, singleton tracer, helper context manager
│   ├── logger.py         # Structured JSONL logger (one file per run)
│   ├── middleware.py     # LangChain BaseCallbackHandler — 10 hooks, _SAFE=True
│   ├── collector.py      # SpanRecord + TrajectoryCollector → TrajectoryResult
│   └── runner.py         # TaskRunner + SuiteResult + CLI entry point
│
├── judge/                # Evaluation pipeline
│   ├── rules.py          # Deterministic rule judge (safety-first checkpoint eval)
│   ├── rubric.py         # JudgeScore schema + prompt builder for LLM judge
│   ├── llm_judge.py      # Claude API caller with retry + response validator
│   └── pipeline.py       # Two-stage orchestrator with cost-aware routing
│
├── tasks/                # Task definitions
│   ├── schema.py         # Task + Checkpoint + TaskResult Pydantic v2 models
│   ├── registry.py       # load_tasks(), filter helpers, Rich summary table
│   └── library/          # JSON task files (basic_qa, tool_use, adversarial)
│
├── storage/              # Persistence layer
│   ├── models.py         # SQLAlchemy 2.0 ORM: EvalRun, Trajectory, JudgeScore, GoldenSet, HitlQueue
│   ├── db.py             # Async engine + session factory + create_all_tables()
│   └── migrations/       # Alembic async env.py + versioned migration files
│
├── agents/
│   └── react.py          # ReAct agent under test: 4 tools + make_agent() factory
│
├── api/                  # FastAPI REST backend
│   ├── app.py            # App factory, CORS, lifespan, route mounting
│   ├── schemas.py        # Pydantic v2 request/response schemas (no ORM leak)
│   ├── deps.py           # Dependency providers (DB session, task library)
│   └── routes/           # runs.py, metrics.py, tasks.py, hitl.py
│
├── analysis/             # Metrics + reporting + regression flywheel
│   ├── metrics.py        # compute_run_metrics(), compute_suite_metrics()
│   ├── reporter.py       # write_run_json() → results/run_*.json + metrics_*.json
│   └── flywheel.py       # GoldenSetWriter: annotation → GoldenSet row + pytest file
│
├── scripts/
│   ├── verify_setup.py   # 7-check preflight (env, docker, postgres, jaeger, tasks, alembic)
│   ├── check_pass_rate.py# CI gate: asserts pass_rate ≥ 80%, safety = 100%, no regression
│   └── compute_kappa.py  # Cohen's κ inter-rater reliability (dissertation validation)
│
├── tests/
│   ├── test_harness.py   # unit tests: EvalLogger, Collector, Harness, RuleJudge
│   └── golden_set/       # Auto-generated regression tests (committed, not edited)
│
├── results/              # Run JSON artefacts (gitignored)
├── analysis/results/     # CSV/markdown exports (gitignored)
├── docker-compose.yml    # Postgres 15, Jaeger all-in-one, Redis 7
├── Makefile              # make up|down|test|run-eval|migrate
├── alembic.ini           # Points to storage/migrations
└── pyproject.toml        # PEP 517, Python ≥ 3.11, all deps declared
```

## Verification Commands

```bash
# Verify import graph is sound (no Docker needed)
python -c "from storage.models import Base; print('Models:', list(Base.metadata.tables.keys()))"
python -c "from harness import EvalLogger, EvalHarness, TrajectoryCollector; print('Harness OK')"
python -c "from tasks.schema import Task; t=Task(name='test_task',description='x',prompt='y',expected_outcome='z',category='basic_qa'); print('Task OK:', t.id)"
python tasks/registry.py
python -c "from judge.rules import run_rule_checks; print('Judge OK')"

# Run unit tests (no external services)
pytest tests/ -m "not integration and not regression and not flywheel" -v

# API docs (requires uvicorn running)
open http://localhost:8000/api/docs

# Cohen's κ reliability (requires data/human_scores.json + data/llm_scores.json)
python scripts/compute_kappa.py
```

## Evaluation Dimensions

| Dimension | Weight | Description |
|---|---|---|
| Correctness | 40% | Final output vs expected_outcome |
| Tool Accuracy | 25% | Right tools, right arguments |
| Efficiency | 15% | Minimal steps; no wasted calls |
| Hallucination | 10% | Absence of fabricated information |
| Robustness | 10% | Edge-case and ambiguity handling |

## CI Gate Thresholds

| Metric | Threshold | Action on breach |
|---|---|---|
| `task_success_rate` | ≥ 80% | CI fails |
| `safety_pass_rate` | = 100% | CI fails |
| `regression_delta` | > -5% | CI fails |
| Cohen's κ (per dimension) | > 0.6 | Dissertation gate |
