from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional

from ...application.services.judge_service import JudgeService

router = APIRouter(prefix="/judge", tags=["judge"])

class JudgeRequest(BaseModel):
    task: Dict[str, Any]
    trajectory: Dict[str, Any]
    final_output: str
    strategy: str = "hybrid"

class PairwiseRequest(BaseModel):
    task: Dict[str, Any]
    trajectory_a: Dict[str, Any]
    output_a: str
    trajectory_b: Dict[str, Any]
    output_b: str

# Quick dependency mock until main.py ties it
def get_judge_service():
    from ..main import get_service
    return get_service()

@router.post("/evaluate")
async def evaluate(request: JudgeRequest, service: JudgeService = Depends(get_judge_service)):
    from services.agent_eval.domain.entities.task import Task
    from services.agent_eval.domain.entities.trajectory import Trajectory
    
    task = Task.from_dict(request.task)
    traj_data = request.trajectory
    traj = Trajectory(
        trajectory_id=traj_data.get("trajectory_id", ""),
        run_id=traj_data.get("run_id", "")
    )

    result = await service.evaluate(task, traj, request.final_output, request.strategy)
    
    return {
        "score": {"value": result.score.value},
        "correctness": result.correctness,
        "tool_accuracy": result.tool_accuracy,
        "efficiency": result.efficiency,
        "hallucination": result.hallucination,
        "robustness": result.robustness,
        "rationale": result.rationale,
        "cost_usd": result.cost_usd,
        "cached": result.cached,
        "strategy_used": result.strategy_used.value if hasattr(result.strategy_used, 'value') else result.strategy_used
    }

@router.post("/pairwise")
async def pairwise(request: PairwiseRequest, service: JudgeService = Depends(get_judge_service)):
    from services.agent_eval.domain.entities.task import Task
    from services.agent_eval.domain.entities.trajectory import Trajectory
    
    task = Task.from_dict(request.task)
    traj_a = Trajectory(trajectory_id=request.trajectory_a.get("trajectory_id", ""), run_id="")
    traj_b = Trajectory(trajectory_id=request.trajectory_b.get("trajectory_id", ""), run_id="")

    result = await service.pairwise(task, traj_a, request.output_a, traj_b, request.output_b)
    return result

@router.get("/cache/stats")
async def cache_stats(service: JudgeService = Depends(get_judge_service)):
    return service.cache.stats()

@router.delete("/cache")
async def clear_cache(service: JudgeService = Depends(get_judge_service)):
    service.cache.cache.clear()
    service.cache.hits = 0
    service.cache.misses = 0
    return {"cleared": True}
