import httpx
from typing import List, Optional, Union, Dict, Any
from ...domain.entities.eval_run import EvalRun
from ...domain.repositories.base import AbstractRunRepository
from ..use_cases.run_eval_suite import RunEvalSuiteUseCase
from ..use_cases.run_eval_task import RunEvalTaskUseCase
from core.use_cases.registry import TaskRegistry

class EvalService:
    """High-level service called by the API layer."""
    def __init__(self, 
                 run_suite_use_case: RunEvalSuiteUseCase, 
                 run_task_use_case: RunEvalTaskUseCase,
                 run_repo: AbstractRunRepository,
                 judge_client: httpx.AsyncClient,
                 judge_service_url: str):
        self.run_suite_use_case = run_suite_use_case
        self.run_task_use_case = run_task_use_case
        self.run_repo = run_repo
        self.judge_client = judge_client
        self.judge_service_url = judge_service_url.rstrip("/")
        self.registry = TaskRegistry()

    async def run_suite(self, task_ids: Union[List[str], str], category: Optional[str] = None, agent_version: str = "v1.0") -> Dict[str, Any]:
        tasks = []
        if isinstance(task_ids, str):
            task_ids = [task_ids]

        if task_ids and task_ids[0].lower() == "all":
            tasks = self.registry.list_tasks()
            if category:
                tasks = [t for t in tasks if t.category == category]
        else:
            for tid in task_ids:
                t = self.registry.get_task(tid)
                if t:
                    tasks.append(t)

        from ...domain.entities.task import Task
        domain_tasks = [Task.from_dict(t.model_dump()) for t in tasks]
        
        runs = await self.run_suite_use_case.execute(domain_tasks)

        scored_runs = []
        for run in runs:
            if run.trajectory and run.status == "PASS":
                try:
                    payload = {
                        "task": [t for t in domain_tasks if t.task_id == run.task_id][0].to_dict(),
                        "trajectory": run.trajectory.to_dict(),
                        "final_output": run.trajectory.final_output
                    }
                    response = await self.judge_client.post(
                        f"{self.judge_service_url}/evaluate",
                        json=payload
                    )
                    response.raise_for_status()
                    score_data = response.json()
                    run.score = score_data.get("score", {}).get("value", 0.0)
                    await self.run_repo.save(run)
                except httpx.HTTPError:
                    run.score = 0.0
            scored_runs.append(run.to_dict())

        return {
            "total_runs": len(scored_runs),
            "runs": scored_runs
        }

    async def get_run(self, run_id: str) -> Optional[EvalRun]:
        return await self.run_repo.get_by_id(run_id)

    async def list_runs(self, limit: int, offset: int, status: Optional[str] = None) -> List[EvalRun]:
        return await self.run_repo.list(limit, offset, status)
