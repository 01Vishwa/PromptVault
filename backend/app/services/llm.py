# backend/app/services/llm.py
"""
LLM execution service — wraps LiteLLM for unified multi-provider calls.
Provider API keys are injected from server-side config, never from the client.
"""
from __future__ import annotations

import asyncio
import logging
import time
import uuid
from typing import Any, Dict, List, Optional

import litellm
from supabase import Client

from app.config import get_settings
from app.schemas.execution import ExecutionResult

logger = logging.getLogger("promptvault.llm")

# Prevent LiteLLM from reading env vars we don't want
litellm.drop_params = True


class LLMService:
    """Executes prompts via LiteLLM and logs results to the executions table."""

    def __init__(self, client: Client) -> None:
        self._db = client
        self._settings = get_settings()

    def _get_api_key(self, provider: str) -> Optional[str]:
        """Resolve API key for a provider from server-side settings. Never exposed."""
        provider_lower = provider.lower()
        if "openai" in provider_lower:
            return self._settings.OPENAI_API_KEY
        if "anthropic" in provider_lower or "claude" in provider_lower:
            return self._settings.ANTHROPIC_API_KEY
        if "gemini" in provider_lower or "google" in provider_lower:
            return self._settings.GOOGLE_API_KEY
        return None

    async def execute_single(
        self,
        *,
        model: str,
        rendered_prompt: str,
        system_prompt: Optional[str] = None,
        config_override: Optional[Dict[str, Any]] = None,
        prompt_version_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> ExecutionResult:
        """Execute a prompt against a single LiteLLM model string."""
        # Parse provider from model string (e.g. "openai/gpt-4o" → "openai")
        provider = model.split("/")[0] if "/" in model else model
        model_name = model.split("/", 1)[1] if "/" in model else model
        api_key = self._get_api_key(provider)

        messages: List[Dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": rendered_prompt})

        config = config_override or {}
        start = time.monotonic()
        status = "success"
        error_message = None
        response_text = None
        tokens_in = 0
        tokens_out = 0
        cost = 0.0

        try:
            response = await litellm.acompletion(
                model=model,
                messages=messages,
                api_key=api_key,
                temperature=config.get("temperature"),
                max_tokens=config.get("max_tokens"),
                top_p=config.get("top_p"),
            )
            response_text = response.choices[0].message.content or ""
            usage = response.usage
            if usage:
                tokens_in = usage.prompt_tokens or 0
                tokens_out = usage.completion_tokens or 0

            # LiteLLM cost estimation
            try:
                cost = litellm.completion_cost(completion_response=response)
            except Exception:
                cost = 0.0

        except Exception as exc:
            status = "error"
            error_message = str(exc)
            logger.warning("LLM execution failed for %s: %s", model, exc)

        latency_ms = int((time.monotonic() - start) * 1000)

        # Persist execution record
        exec_data = {
            "prompt_version_id": str(prompt_version_id),
            "user_id": str(user_id),
            "model_provider": provider,
            "model_name": model_name,
            "rendered_prompt": rendered_prompt,
            "system_prompt": system_prompt,
            "response_text": response_text,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "latency_ms": latency_ms,
            "cost_estimate": cost,
            "status": status,
            "error_message": error_message,
        }
        result = self._db.table("executions").insert(exec_data).execute()
        row = result.data[0]

        return ExecutionResult(
            id=row["id"],
            model_provider=provider,
            model_name=model_name,
            response_text=response_text,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            latency_ms=latency_ms,
            cost_estimate=cost,
            status=status,
            error_message=error_message,
            created_at=row["created_at"],
        )

    async def execute_multi(
        self,
        *,
        models: List[str],
        rendered_prompt: str,
        system_prompt: Optional[str] = None,
        config_override: Optional[Dict[str, Any]] = None,
        prompt_version_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> List[ExecutionResult]:
        """Execute a prompt against multiple providers in parallel."""
        tasks = [
            self.execute_single(
                model=model,
                rendered_prompt=rendered_prompt,
                system_prompt=system_prompt,
                config_override=config_override,
                prompt_version_id=prompt_version_id,
                user_id=user_id,
            )
            for model in models
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        execution_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error("Execution failed for %s: %s", models[i], result)
                # Create a failed result
                execution_results.append(
                    ExecutionResult(
                        id=uuid.uuid4(),
                        model_provider=models[i].split("/")[0],
                        model_name=models[i].split("/", 1)[-1],
                        response_text=None,
                        tokens_in=None,
                        tokens_out=None,
                        latency_ms=None,
                        cost_estimate=None,
                        status="error",
                        error_message=str(result),
                        created_at="",  # type: ignore[arg-type]
                    )
                )
            else:
                execution_results.append(result)

        return execution_results
