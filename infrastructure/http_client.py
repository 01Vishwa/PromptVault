import httpx
from typing import AsyncGenerator

class ServiceClient:
    """Typed async HTTP client for inter-service communication."""
    def __init__(self, base_url: str, timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.client = None

    async def __aenter__(self):
        self.client = httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.aclose()

    async def get(self, path: str, **params) -> dict:
        if not self.client:
             raise RuntimeError("Client not initialized. Use async context manager.")
        response = await self.client.get(path, params=params)
        response.raise_for_status()
        return response.json()

    async def post(self, path: str, body: dict) -> dict:
        if not self.client:
             raise RuntimeError("Client not initialized. Use async context manager.")
        response = await self.client.post(path, json=body)
        response.raise_for_status()
        return response.json()

    async def stream_sse(self, path: str) -> AsyncGenerator[dict, None]:
        if not self.client:
             raise RuntimeError("Client not initialized. Use async context manager.")
        async with self.client.stream("GET", path) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    import json
                    yield json.loads(line[6:])

    async def health_check(self) -> bool:
        try:
             res = await self.get("/health")
             return res.get("status") == "ok"
        except Exception:
             return False
