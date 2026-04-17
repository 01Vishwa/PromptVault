from fastapi import APIRouter
from core.use_cases.registry import TaskRegistry
from ...schemas.run_schemas import RunSummaryResponse

router = APIRouter(prefix="/tasks", tags=["tasks"])
registry = TaskRegistry()

@router.get("/")
async def list_tasks():
    tasks = registry.list_tasks()
    return [task.model_dump() for task in tasks]

@router.get("/{task_id}/history")
async def task_history(task_id: str):
    return []
