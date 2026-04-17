import asyncio
from typing import Tuple
from anthropic import AsyncAnthropic, RateLimitError

class AnthropicClient:
    def __init__(self, api_key: str, model: str):
        self.client = AsyncAnthropic(api_key=api_key)
        self.model = model

    async def complete(self, system: str, user: str, max_tokens: int) -> Tuple[str, int, int]:
        try:
            return await self._call_api(system, user, max_tokens)
        except RateLimitError:
            await asyncio.sleep(60)
            return await self._call_api(system, user, max_tokens)

    async def _call_api(self, system: str, user: str, max_tokens: int) -> Tuple[str, int, int]:
        response = await self.client.messages.create(
            model=self.model,
            system=system,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": user}]
        )
        return (
            response.content[0].text,
            response.usage.input_tokens,
            response.usage.output_tokens
        )

class BudgetTracker:
    def __init__(self, max_cost_usd: float):
        self.max_cost_usd = max_cost_usd
        self.total_spent = 0.0
        # Haiku 3 Haiku / Haiku 3.5 pricing approx
        self.input_cost_per_m = 0.25 
        self.output_cost_per_m = 1.25

    def record(self, input_tokens: int, output_tokens: int) -> None:
        cost = (input_tokens / 1_000_000) * self.input_cost_per_m + \
               (output_tokens / 1_000_000) * self.output_cost_per_m
        self.total_spent += cost

    def can_afford(self, estimated_tokens: int) -> bool:
        estimated_cost = (estimated_tokens / 1_000_000) * self.output_cost_per_m
        return (self.total_spent + estimated_cost) <= self.max_cost_usd
