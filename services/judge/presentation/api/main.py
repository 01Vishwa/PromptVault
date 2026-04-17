from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from .routers import judge
from ...infrastructure.llm.anthropic_client import AnthropicClient, BudgetTracker
from ...infrastructure.llm.cache import JudgeCache
from ...domain.strategies.rule_strategy import RuleJudgeStrategy
from ...domain.strategies.llm_strategy import LLMJudgeStrategy
from ...domain.strategies.hybrid_strategy import HybridJudgeStrategy
from ...application.services.judge_service import JudgeService

from core.errors.exceptions import JudgeBudgetExceededError, SafetyViolationError
import os

_service_instance = None

def get_service() -> JudgeService:
    return _service_instance

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _service_instance
    api_key = os.getenv("ANTHROPIC_API_KEY", "dummy")
    model = os.getenv("EVAL_JUDGE_MODEL", "claude-haiku-4-5-20251001")
    
    client = AnthropicClient(api_key, model)
    tracker = BudgetTracker(max_cost_usd=10.0)
    cache = JudgeCache()

    rule = RuleJudgeStrategy()
    llm = LLMJudgeStrategy(client, model, tracker)
    hybrid = HybridJudgeStrategy(rule, llm)

    _service_instance = JudgeService(rule, llm, hybrid, cache)
    
    yield

app = FastAPI(lifespan=lifespan, title="Judge Service", version="1.0.0")

@app.exception_handler(JudgeBudgetExceededError)
async def budget_handler(request: Request, exc: JudgeBudgetExceededError):
    return JSONResponse(status_code=402, content={"detail": str(exc)})

@app.exception_handler(SafetyViolationError)
async def safety_handler(request: Request, exc: SafetyViolationError):
    return JSONResponse(status_code=400, content={"detail": str(exc)})

app.include_router(judge.router)

@app.get("/health")
async def health():
    return {"status": "ok"}
