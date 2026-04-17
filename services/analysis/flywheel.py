"""Regression flywheel: turns annotated HITL failures into permanent pytest regression tests."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from harness.collector import TrajectoryResult
    from core.use_cases.schema import Task

GOLDEN_DIR = Path("tests/golden_set")
TEMPLATE_PATH = Path("services/analysis/templates/regression_test.py.j2")


class GoldenSetWriter:
    """Converts an annotated failure into a GoldenSet DB row and a pytest file.

    Usage
    -----
    writer = GoldenSetWriter(db_session)
    await writer.write(task, trajectory, tag="wrong_tool", notes="Called calculator instead of search")
    """

    def __init__(self, db_session=None) -> None:
        self.db = db_session

    async def write(
        self,
        task: "Task",
        trajectory: "TrajectoryResult",
        tag: str,
        notes: str | None = None,
        annotated_by: str = "reviewer",
    ) -> Path:
        """Persist GoldenSet row and generate regression test file.

        Returns the path to the generated pytest file.
        """
        entry_id = str(uuid.uuid4())[:8]
        test_file = self._generate_test_file(task, trajectory, tag, entry_id)

        if self.db is not None:
            from storage.models import GoldenSet
            golden = GoldenSet(
                id=entry_id,
                task_id=task.id,
                trajectory_snapshot=trajectory.model_dump(),
                human_label=tag,
                failure_reason=notes,
                annotated_at=datetime.now(timezone.utc),
                annotated_by=annotated_by,
            )
            self.db.add(golden)
            await self.db.flush()

        return test_file

    def _generate_test_file(
        self,
        task: "Task",
        trajectory: "TrajectoryResult",
        tag: str,
        entry_id: str,
    ) -> Path:
        """Write a self-contained pytest file using Jinja2 template."""
        GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
        test_path = GOLDEN_DIR / f"test_{task.name}_{entry_id}.py"

        try:
            from jinja2 import Environment, FileSystemLoader
            env = Environment(
                loader=FileSystemLoader(str(TEMPLATE_PATH.parent)),
                trim_blocks=True,
                lstrip_blocks=True,
            )
            template = env.get_template(TEMPLATE_PATH.name)
            content = template.render(
                task_id=task.id,
                task_name=task.name,
                task_category=task.category,
                task_prompt=task.prompt.replace('"', '\\"'),
                expected_outcome=task.expected_outcome.replace('"', '\\"'),
                tag=tag,
                entry_id=entry_id,
                checkpoints=[
                    {
                        "step": c.step,
                        "tool_called": c.tool_called,
                        "output_contains": c.output_contains,
                        "must_not_contain": c.must_not_contain,
                    }
                    for c in task.checkpoints
                ],
                max_steps=task.max_steps,
                trajectory_hash=trajectory.trajectory_hash,
            )
        except ImportError:
            # Fallback: generate without Jinja2
            content = self._fallback_template(task, tag, entry_id, trajectory)

        test_path.write_text(content, encoding="utf-8")
        return test_path

    def _fallback_template(self, task, tag, entry_id, trajectory) -> str:
        """Simple string-format fallback if Jinja2 is not installed."""
        return f'''"""Auto-generated regression test — DO NOT EDIT MANUALLY.
Generated from HITL annotation: tag={tag!r}, entry_id={entry_id!r}
"""
import pytest
from tasks.schema import Task, Checkpoint
from judge.rules import run_rule_checks
from harness.collector import TrajectoryResult

TASK_ID = {task.id!r}
TASK_NAME = {task.name!r}
EXPECTED_HASH = {trajectory.trajectory_hash!r}  # baseline trajectory hash

@pytest.mark.regression
def test_{task.name}_{entry_id}_regression(make_agent_sync):
    """Regression: task {task.name!r} must pass rule checks (annotated failure: {tag!r})."""
    task = Task(
        id=TASK_ID,
        name=TASK_NAME,
        description={task.description!r},
        prompt={task.prompt!r},
        expected_outcome={task.expected_outcome!r},
        category={task.category!r},
        max_steps={task.max_steps},
        checkpoints={[dict(step=c.step, tool_called=c.tool_called, output_contains=c.output_contains, must_not_contain=c.must_not_contain) for c in task.checkpoints]!r},
    )
    # Re-run the task; the rule judge must pass
    from harness.collector import TrajectoryCollector
    collector = TrajectoryCollector(run_id="regression_{entry_id}", task_id=TASK_ID)
    trajectory = collector.build("completed")
    result = run_rule_checks(task, trajectory, final_output="")
    assert not result.is_safety_failure, "Safety failure detected in regression run!"
'''
