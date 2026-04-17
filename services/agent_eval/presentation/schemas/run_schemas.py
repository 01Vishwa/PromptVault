from pydantic import BaseModel, ConfigDict
from typing import List, Optional, Union, Dict, Any
from datetime import datetime
from uuid import UUID

class CreateRunRequest(BaseModel):
    task_ids: Union[List[str], str] = "all"
    category: Optional[str] = None
    agent_version: str = "default"

class SpanResponse(BaseModel):
    span_type: str
    span_id: str
    duration_ms: int
    attributes: Dict[str, Any]
    error: bool

class TrajectoryResponse(BaseModel):
    spans: List[SpanResponse]
    step_count: int
    token_total: int
    duration_ms: int
    tool_names_called: List[str]
    error_count: int

class RunSummaryResponse(BaseModel):
    run_id: str
    task_id: str
    agent_version: str
    status: str
    created_at: datetime
    score: Optional[float]
    duration_ms: int

class RunDetailResponse(BaseModel):
    run_id: str
    task_id: str
    status: str
    trajectory: Optional[TrajectoryResponse]
    judge_scores: Optional[Dict[str, Any]]

class NodeData(BaseModel):
    id: str
    type: str # 'llm_call', 'tool_call', 'chain_step', 'error'
    data: Dict[str, Any]

class EdgeData(BaseModel):
    source: str
    target: str

class ReactFlowResponse(BaseModel):
    nodes: List[NodeData]
    edges: List[EdgeData]

class SuiteProgressEvent(BaseModel):
    run_id: str
    task_name: str
    completed: int
    total: int
    status: str
