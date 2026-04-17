class EvalFrameworkError(Exception):
    """Base exception for evaluation framework."""
    pass

class TaskNotFoundError(EvalFrameworkError):
    pass

class RunNotFoundError(EvalFrameworkError):
    pass

class AgentTimeoutError(EvalFrameworkError):
    pass

class JudgeBudgetExceededError(EvalFrameworkError):
    pass

class SafetyViolationError(EvalFrameworkError):
    def __init__(self, message: str, must_not_contain: str):
        super().__init__(message)
        self.must_not_contain = must_not_contain

class InfrastructureError(EvalFrameworkError):
    pass
