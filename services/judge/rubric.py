"""Pydantic schemas and prompt builder for the LLM-as-Judge pipeline."""
from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, Field, field_validator

if TYPE_CHECKING:
    from services.agent_eval.domain.entities.task import Task
    from services.agent_eval.domain.entities.trajectory import Trajectory as TrajectoryResult


# ── Judge response schema ─────────────────────────────────────────────────────

class JudgeScore(BaseModel):
    """Structured scoring response from the LLM judge."""
    correctness: float = Field(..., ge=0.0, le=1.0,
        description="How well the final answer matches expected_outcome (0–1)")
    tool_accuracy: float = Field(..., ge=0.0, le=1.0,
        description="Right tools called with correct arguments (0–1)")
    efficiency: float = Field(..., ge=0.0, le=1.0,
        description="Minimal steps used; no wasted calls (0–1)")
    hallucination: float = Field(..., ge=0.0, le=1.0,
        description="Absence of fabricated information; 1=no hallucination (0–1)")
    robustness: float = Field(..., ge=0.0, le=1.0,
        description="Handling of ambiguity and edge-cases (0–1)")
    rationale: str = Field(..., min_length=10,
        description="Brief explanation (1–3 sentences) justifying the scores")

    @field_validator("correctness", "tool_accuracy", "efficiency",
                     "hallucination", "robustness", mode="before")
    @classmethod
    def clamp_to_range(cls, v: float) -> float:
        return max(0.0, min(1.0, float(v)))

    @property
    def weighted_overall(self) -> float:
        """Weighted composite score matching PRD weightings."""
        return round(
            self.correctness * 0.40
            + self.tool_accuracy * 0.25
            + self.efficiency * 0.15
            + self.hallucination * 0.10
            + self.robustness * 0.10,
            4,
        )


# ── Rubric definition ─────────────────────────────────────────────────────────

RUBRIC_DIMENSIONS = """
You are an expert AI evaluator. Score the agent trajectory below on five dimensions,
each from 0.0 (worst) to 1.0 (best). Return ONLY valid JSON matching this schema:

{
  "correctness":   <float 0-1>,  // Final answer vs expected_outcome. 1.0 = exact match.
  "tool_accuracy": <float 0-1>,  // Correct tool chosen, correct arguments supplied.
  "efficiency":    <float 0-1>,  // Minimal steps; 0 = grossly over-stepped, 1 = optimal.
  "hallucination": <float 0-1>,  // 1.0 = no fabrication. 0.0 = fabricated critical info.
  "robustness":    <float 0-1>,  // Handled edge-cases / ambiguity gracefully.
  "rationale":     "<1-3 sentences explaining scores>"
}

Do not include any text outside the JSON object.
"""


def build_judge_prompt(
    task: "Task",
    trajectory: "TrajectoryResult",
    final_output: str,
) -> str:
    """Construct the full prompt sent to the LLM judge."""
    import json

    span_summary = []
    for s in trajectory.spans[:30]:  # cap at 30 spans to stay within context
        span_summary.append({
            "type": s.get("span_type"),
            "tool": s.get("attributes", {}).get("tool_name"),
            "tokens": s.get("attributes", {}).get("tokens_total"),
            "error": s.get("error"),
            "duration_ms": s.get("duration_ms"),
        })

    return f"""{RUBRIC_DIMENSIONS}

=== TASK ===
Name: {task.name}
Category: {task.category}
Prompt: {task.prompt}
Expected outcome: {task.expected_outcome}
Max steps allowed: {task.max_steps}

=== TRAJECTORY SUMMARY ===
Total steps: {trajectory.step_count}
Total tokens: {trajectory.token_total}
Duration ms: {trajectory.duration_ms}
Tools called: {trajectory.tool_names_called}
Errors: {trajectory.error_count}
Step efficiency ratio: {trajectory.step_efficiency_ratio:.2f}

=== SPAN SEQUENCE ===
{json.dumps(span_summary, indent=2)}

=== FINAL AGENT OUTPUT ===
{final_output[:2000]}

=== YOUR EVALUATION (JSON only) ==="""
