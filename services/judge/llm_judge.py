"""LLM-as-Judge: calls Claude API with the rubric prompt and parses structured scores."""
from __future__ import annotations

import json
import os
import time
from typing import TYPE_CHECKING

import anthropic
from dotenv import load_dotenv
from pydantic import ValidationError

from services.judge.rubric import JudgeScore, build_judge_prompt

if TYPE_CHECKING:
    from services.agent_eval.domain.entities.task import Task
    from services.agent_eval.domain.entities.trajectory import Trajectory as TrajectoryResult

load_dotenv()

_DEFAULT_MODEL = "claude-haiku-4-5-20251001"
_RATE_LIMIT_WAIT_S = 60
_TIMEOUT_S = 30
_MAX_RETRIES = 2


class LLMJudgeError(Exception):
    """Raised when the LLM judge cannot produce a valid score after all retries."""


class LLMJudge:
    """Scores an agent trajectory using a Claude LLM with a structured rubric.

    Parameters
    ----------
    model:      Anthropic model name. Falls back to EVAL_JUDGE_MODEL env var.
    api_key:    Anthropic API key. Falls back to ANTHROPIC_API_KEY env var.
    """

    def __init__(
        self,
        model: str | None = None,
        api_key: str | None = None,
    ) -> None:
        self.model = model or os.environ.get("EVAL_JUDGE_MODEL", _DEFAULT_MODEL)
        self._client = anthropic.Anthropic(
            api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"),
        )

    def score(
        self,
        task: "Task",
        trajectory: "TrajectoryResult",  # Trajectory domain entity
        final_output: str,
    ) -> JudgeScore:
        """Call Claude with the rubric prompt and return a validated JudgeScore.

        Retry policy
        ------------
        - On API rate limit (429): wait 60 s, retry once.
        - On parse/validation failure: re-prompt once with error context.
        - On second failure: raise LLMJudgeError.
        """
        prompt = build_judge_prompt(task, trajectory, final_output)
        last_error: Exception | None = None

        for attempt in range(_MAX_RETRIES):
            try:
                response = self._client.messages.create(
                    model=self.model,
                    max_tokens=512,
                    timeout=_TIMEOUT_S,
                    messages=[{"role": "user", "content": prompt}],
                )
                raw_text = response.content[0].text.strip()
                return self._parse_response(raw_text)

            except anthropic.RateLimitError as exc:
                last_error = exc
                if attempt < _MAX_RETRIES - 1:
                    time.sleep(_RATE_LIMIT_WAIT_S)
                    continue
                break

            except (LLMJudgeError, ValidationError) as exc:
                last_error = exc
                if attempt < _MAX_RETRIES - 1:
                    # Amend prompt with parse error context for retry
                    prompt = (
                        f"{prompt}\n\n[Previous attempt failed: {exc}. "
                        "Please return ONLY the JSON object.]"
                    )
                    continue
                break

            except Exception as exc:
                last_error = exc
                break

        raise LLMJudgeError(
            f"LLM judge failed after {_MAX_RETRIES} attempts. "
            f"Last error: {last_error}"
        ) from last_error

    def _parse_response(self, raw: str) -> JudgeScore:
        """Extract JSON from the model response and validate with Pydantic."""
        # Strip markdown code fences if present
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            inner = [l for l in lines if not l.startswith("```")]
            cleaned = "\n".join(inner).strip()

        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise LLMJudgeError(f"Response is not valid JSON: {exc}\nRaw: {raw[:300]}")

        try:
            return JudgeScore.model_validate(data)
        except ValidationError as exc:
            raise LLMJudgeError(f"Response failed schema validation: {exc}")
