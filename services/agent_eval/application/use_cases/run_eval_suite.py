import asyncio
from typing import Callable, List, Optional
from ...domain.entities.task import Task
from ...domain.entities.eval_run import EvalRun
from ...domain.events.domain_events import EventBus
from contracts.events.events import SuiteCompleted
from .run_eval_task import RunEvalTaskUseCase
from datetime import datetime
from uuid import uuid4

class RunEvalSuiteUseCase:
    def __init__(self, run_task_use_case: RunEvalTaskUseCase, event_bus: EventBus):
        self.run_task_use_case = run_task_use_case
        self.event_bus = event_bus

    async def execute(self, tasks: List[Task], progress_callback: Optional[Callable] = None) -> List[EvalRun]:
        start_time = datetime.utcnow()
        runs = []
        
        for task in tasks:
            run = await self.run_task_use_case.execute(task)
            runs.append(run)
            if progress_callback:
                if asyncio.iscoroutinefunction(progress_callback):
                    await progress_callback(task=task, run=run, completed=len(runs), total=len(tasks))
                else:
                    progress_callback(task=task, run=run, completed=len(runs), total=len(tasks))

        # Summarize suite pass rate
        passed = sum(1 for r in runs if r.status == "PASS")
        duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        pass_rate = passed / max(1, len(tasks))

        self.event_bus.publish(SuiteCompleted(
            event_id=uuid4(),
            occurred_at=datetime.utcnow(),
            aggregate_id=str(uuid4()),
            pass_rate=pass_rate,
            total_tasks=len(tasks),
            duration_ms=duration_ms
        ))

        return runs
