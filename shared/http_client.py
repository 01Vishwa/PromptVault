"""Shared typed async HTTP client for inter-service communication."""
from __future__ import annotations

import json
from typing import Any, AsyncGenerator

import httpx


class ServiceClient:
    """Typed async HTTP client.

    Wraps ``httpx.AsyncClient`` with clean typed methods and SSE streaming.
    Use as an async context manager to manage the underlying connection pool.
    """

    def __init__(self, base_url: str, timeout: float = 30.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "ServiceClient":
        self._client = httpx.AsyncClient(base_url=self._base_url, timeout=self._timeout)
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    def _http(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError("ServiceClient must be used as an async context manager")
        return self._client

    async def get(self, path: str, **params: Any) -> dict:
        """GET *path* with optional query parameters."""
        resp = await self._http().get(path, params=params or None)
        resp.raise_for_status()
        return resp.json()

    async def post(self, path: str, body: dict) -> dict:
        """POST JSON *body* to *path*."""
        resp = await self._http().post(path, json=body)
        resp.raise_for_status()
        return resp.json()

    async def stream_sse(self, path: str) -> AsyncGenerator[dict, None]:
        """Yield parsed SSE event dicts as they arrive from *path*."""
        async with self._http().stream("GET", path, headers={"Accept": "text/event-stream"}) as resp:
            resp.raise_for_status()
            event_type = "message"
            data_lines: list[str] = []

            async for raw_line in resp.aiter_lines():
                line = raw_line.strip()
                if not line:
                    if data_lines:
                        raw_data = "\n".join(data_lines)
                        try:
                            parsed = json.loads(raw_data)
                        except json.JSONDecodeError:
                            parsed = {"data": raw_data}
                        parsed["type"] = event_type
                        yield parsed
                    event_type = "message"
                    data_lines = []
                elif line.startswith("event:"):
                    event_type = line[len("event:"):].strip()
                elif line.startswith("data:"):
                    data_lines.append(line[len("data:"):].strip())

    async def health_check(self) -> bool:
        """Return True if the service's /health endpoint returns 200."""
        try:
            resp = await self._http().get("/health", timeout=5.0)
            return resp.status_code == 200
        except Exception:
            return False
