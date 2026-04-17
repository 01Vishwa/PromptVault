from dataclasses import dataclass, field
from typing import Tuple

@dataclass
class Score:
    value: float
    is_safety_failure: bool = False
    failures: Tuple[str, ...] = field(default_factory=tuple)
    warnings: Tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self):
        if not (0.0 <= self.value <= 1.0):
            raise ValueError(f"Score value {self.value} must be between 0.0 and 1.0")

    @classmethod
    def zero(cls, failures: Tuple[str, ...]) -> 'Score':
        return cls(value=0.0, failures=failures)

    @classmethod
    def perfect(cls) -> 'Score':
        return cls(value=1.0)

    def __add__(self, other: 'Score') -> 'Score':
        new_value = (self.value + other.value) / 2.0
        return Score(
            value=new_value,
            is_safety_failure=self.is_safety_failure or other.is_safety_failure,
            failures=self.failures + other.failures,
            warnings=self.warnings + other.warnings
        )

    def __float__(self) -> float:
        return float(self.value)
