from enum import Enum
from dataclasses import dataclass

class RunStatus(str, Enum):
    RUNNING = "RUNNING"
    PASS = "PASS"
    FAIL = "FAIL"
    ERROR = "ERROR"

class TaskCategory(str, Enum):
    BASIC_QA = "BASIC_QA"
    TOOL_USE = "TOOL_USE"
    ADVERSARIAL = "ADVERSARIAL"
    MULTI_STEP = "MULTI_STEP"

class JudgeStrategy(str, Enum):
    RULE = "RULE"
    LLM = "LLM"
    HYBRID = "HYBRID"

class Severity(str, Enum):
    CRITICAL = "CRITICAL"
    MAJOR = "MAJOR"
    MINOR = "MINOR"

class RootCause(str, Enum):
    BAD_PLAN = "BAD_PLAN"
    WRONG_TOOL = "WRONG_TOOL"
    WRONG_TOOL_ARGS = "WRONG_TOOL_ARGS"
    HALLUCINATION = "HALLUCINATION"
    PROMPT_INJECTION = "PROMPT_INJECTION"
    TOOL_ERROR = "TOOL_ERROR"
    OTHER = "OTHER"

@dataclass(frozen=True)
class SpanType:
    LLM_CALL = "LLM_CALL"
    TOOL_CALL = "TOOL_CALL"
    CHAIN_STEP = "CHAIN_STEP"
