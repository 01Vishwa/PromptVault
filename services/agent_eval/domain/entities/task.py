from dataclasses import dataclass
from typing import Optional, List, FrozenSet, Tuple
from core.domain.types import TaskCategory

@dataclass(frozen=True)
class CheckpointVO:
    step: int
    tool_called: Optional[str] = None
    output_contains: Optional[str] = None
    must_not_contain: Optional[str] = None
    description: Optional[str] = None

    def is_safety_check(self) -> bool:
        return self.must_not_contain is not None

@dataclass
class Task:
    task_id: str
    name: str
    description: str
    prompt: str
    expected_outcome: str
    category: TaskCategory
    checkpoints: Tuple[CheckpointVO, ...]
    max_steps: int
    min_steps: int
    perturbations: Tuple[str, ...]
    tags: FrozenSet[str]

    @classmethod
    def from_dict(cls, data: dict) -> 'Task':
        checkpoints_data = data.get("checkpoints", [])
        checkpoints = tuple(
            CheckpointVO(
                step=cp.get("step"),
                tool_called=cp.get("tool_called"),
                output_contains=cp.get("output_contains"),
                must_not_contain=cp.get("must_not_contain"),
                description=cp.get("description")
            )
            for cp in checkpoints_data
        )

        return cls(
            task_id=data["task_id"],
            name=data["name"],
            description=data.get("description", ""),
            prompt=data["prompt"],
            expected_outcome=data.get("expected_outcome", ""),
            category=TaskCategory(data["category"]) if "category" in data else TaskCategory.BASIC_QA,
            checkpoints=checkpoints,
            max_steps=data.get("max_steps", 10),
            min_steps=data.get("min_steps", 1),
            perturbations=tuple(data.get("perturbations", [])),
            tags=frozenset(data.get("tags", []))
        )

    def validate(self) -> list[str]:
        errors = []
        if not self.task_id:
            errors.append("task_id is required")
        if not self.prompt:
            errors.append("prompt is required")
        if self.min_steps > self.max_steps:
            errors.append("min_steps cannot be greater than max_steps")
        return errors

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "name": self.name,
            "description": self.description,
            "prompt": self.prompt,
            "expected_outcome": self.expected_outcome,
            "category": self.category.value if isinstance(self.category, TaskCategory) else self.category,
            "checkpoints": [
                {
                    "step": cp.step,
                    "tool_called": cp.tool_called,
                    "output_contains": cp.output_contains,
                    "must_not_contain": cp.must_not_contain,
                    "description": cp.description
                } for cp in self.checkpoints
            ],
            "max_steps": self.max_steps,
            "min_steps": self.min_steps,
            "perturbations": list(self.perturbations),
            "tags": list(self.tags)
        }
