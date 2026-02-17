# backend/app/schemas/evaluation.py
"""
Pydantic schemas for Evaluation Engine – offline runs, LLM-as-judge, scoring.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class EvaluatorConfig(BaseModel):
    """Configuration for the evaluator."""
    judge_model_provider: Optional[str] = None
    judge_model_name: Optional[str] = None
    judge_prompt_template: Optional[str] = Field(
        None,
        description="Template with placeholders: {input}, {expected_output}, {actual_output}"
    )
    judge_output_schema: Optional[Dict[str, Any]] = None
    scoring_rubric: Optional[Dict[str, Any]] = None
    custom_evaluator_path: Optional[str] = None
    thresholds: Optional[Dict[str, float]] = None


class EvaluationJobCreate(BaseModel):
    """Request to launch an offline evaluation run."""
    name: str = Field(..., min_length=1, max_length=255)
    prompt_version_ids: List[uuid.UUID] = Field(..., min_length=1)
    dataset_version_id: uuid.UUID
    model_providers: List[str] = Field(..., min_length=1)
    model_names: List[str] = Field(..., min_length=1)
    evaluator_type: str = Field(
        ..., pattern=r"^(llm_judge|exact_match|fuzzy_match|custom|composite)$"
    )
    evaluator_config: Optional[EvaluatorConfig] = None
    seed: Optional[int] = Field(None, description="RNG seed for reproducibility")
    max_concurrency: int = Field(default=5, ge=1, le=50)
    environment: str = Field(default="evaluation")


class EvaluationJobRead(BaseModel):
    id: uuid.UUID
    name: str
    status: str  # pending | running | completed | failed
    prompt_version_ids: List[uuid.UUID]
    dataset_version_id: uuid.UUID
    evaluator_type: str
    total_rows: int
    completed_rows: int
    failed_rows: int
    seed: Optional[int]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime

    model_config = {"from_attributes": True}


class EvaluationResult(BaseModel):
    """Result of evaluating a single row."""
    run_id: uuid.UUID
    dataset_row_id: uuid.UUID
    prompt_version_id: uuid.UUID
    model_provider: str
    model_name: str
    input_data: Dict[str, Any]
    expected_output: Optional[Dict[str, Any]]
    actual_output: str
    scores: Dict[str, float]
    judge_reasoning: Optional[str] = None
    latency_ms: int
    tokens_in: int
    tokens_out: int
    cost_estimate: float


class EvaluationSummary(BaseModel):
    """Aggregated evaluation results per prompt_version × model."""
    evaluation_job_id: uuid.UUID
    prompt_version_id: uuid.UUID
    model_provider: str
    model_name: str
    total_rows: int
    avg_scores: Dict[str, float]
    median_scores: Dict[str, float]
    p95_latency_ms: float
    total_cost: float
    pass_rate: Optional[float] = None


class LLMJudgeOutput(BaseModel):
    """Expected schema from the LLM-as-judge response."""
    overall_score: float = Field(..., ge=0.0, le=1.0)
    dimension_scores: Optional[Dict[str, float]] = None
    reasoning: str
    is_pass: bool
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
