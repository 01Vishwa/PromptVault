from pydantic import BaseModel, Field
from typing import List, Optional, Literal

class CheckpointSchema(BaseModel):
    step: int
    tool_called: Optional[str] = None
    output_contains: Optional[str] = None
    must_not_contain: Optional[str] = None
    description: Optional[str] = None

class TaskSchema(BaseModel):
    task_id: str
    name: str
    description: str = ""
    prompt: str
    expected_outcome: str = ""
    category: Literal["BASIC_QA", "TOOL_USE", "ADVERSARIAL", "MULTI_STEP"]
    checkpoints: List[CheckpointSchema] = Field(default_factory=list)
    max_steps: int = 10
    min_steps: int = 1
    perturbations: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
