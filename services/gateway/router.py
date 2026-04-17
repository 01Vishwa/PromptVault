import httpx
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse

class ServiceRouter:
    """Reverse proxy: routes requests to correct microservice via httpx."""
    def __init__(self, eval_core_url: str, judge_url: str, metrics_url: str):
        self.routes = {
            "/api/runs": eval_core_url.rstrip("/") + "/runs",
            "/api/tasks": eval_core_url.rstrip("/") + "/tasks",
            "/api/judge": judge_url.rstrip("/") + "/judge",
            "/api/metrics": metrics_url.rstrip("/") + "/metrics"
        }
        self.client = httpx.AsyncClient()

    async def route_request(self, request: Request):
        path = request.url.path
        target_url = None
        
        for prefix, backend in self.routes.items():
            if path.startswith(prefix):
                target_url = path.replace("/api", backend, 1)
                break

        if not target_url:
            raise HTTPException(status_code=404, detail="Route not found on Gateway")

        query_params = request.url.query
        if query_params:
            target_url += f"?{query_params}"

        headers = dict(request.headers)
        headers.pop("host", None)
        headers["X-Request-ID"] = request.state.correlation_id

        try:
            if "stream" in target_url:
                req = self.client.build_request("GET", target_url, headers=headers)
                r = await self.client.send(req, stream=True)
                return StreamingResponse(r.aiter_raw(), media_type=r.headers.get("content-type"))

            method = request.method
            body = await request.body()
            
            response = await self.client.request(
                method=method,
                url=target_url,
                headers=headers,
                content=body,
                timeout=60.0
            )

            return JSONResponse(
                content=response.json() if response.content else None,
                status_code=response.status_code,
                headers=dict(response.headers)
            )

        except httpx.RequestError as exc:
            return JSONResponse(
                status_code=503,
                content={"message": f"Service unavailable: {str(exc)}"}
            )
