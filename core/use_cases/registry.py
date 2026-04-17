import json
import os
from pathlib import Path
from typing import Dict, Optional
from .schema import TaskSchema

# Resolve path relative to the repo root (two levels above this file: core/use_cases/ -> core/ -> repo root)
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_DEFAULT_TASK_LIBRARY = str(_REPO_ROOT / "tests" / "fixtures" / "tasks")

class TaskRegistry:
    def __init__(self, library_path: str = _DEFAULT_TASK_LIBRARY):
        self.library_path = library_path
        self._tasks: Dict[str, TaskSchema] = {}
        self.load_all()

    def load_all(self):
        if not os.path.exists(self.library_path):
            return
        
        for filename in os.listdir(self.library_path):
            if filename.endswith(".json"):
                path = os.path.join(self.library_path, filename)
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    task = TaskSchema(**data)
                    self._tasks[task.task_id] = task

    def get_task(self, task_id: str) -> Optional[TaskSchema]:
        return self._tasks.get(task_id)

    def list_tasks(self) -> list[TaskSchema]:
        return list(self._tasks.values())
