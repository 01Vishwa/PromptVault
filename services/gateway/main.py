from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
import os
import uuid
import httpx

from .auth import JWTHandler
from .router import ServiceRouter

app = FastAPI(title="API Gateway", version="1.0.0")

JWT_SECRET = os.getenv("JWT_SECRET_KEY", "super-secret")
EVAL_URL = os.getenv("EVAL_CORE_URL", "http://localhost:8000")
JUDGE_URL = os.getenv("JUDGE_SERVICE_URL", "http://localhost:8001")
METRICS_URL = os.getenv("METRICS_SERVICE_URL", "http://localhost:8002")

jwt_handler = JWTHandler(secret_key=JWT_SECRET)
service_router = ServiceRouter(EVAL_URL, JUDGE_URL, METRICS_URL)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")

class AuthRequest(BaseModel):
    api_key: str

@app.post("/auth/token")
async def login(req: AuthRequest):
    if not req.api_key:
        raise HTTPException(status_code=401, detail="API Key required")
    token = jwt_handler.create_token({"sub": "user_123", "scopes": ["eval", "read"]})
    return {"access_token": token, "token_type": "bearer", "expires_in": 3600}

@app.middleware("http")
async def correlation_id_middleware(request: Request, call_next):
    request.state.correlation_id = str(uuid.uuid4())
    response = await call_next(request)
    response.headers["X-Correlation-ID"] = request.state.correlation_id
    return response

@app.get("/health")
async def health():
    async with httpx.AsyncClient() as client:
        results = {"gateway": "ok", "services": {}}
        urls = {"eval_core": EVAL_URL, "judge": JUDGE_URL, "metrics": METRICS_URL}

        for name, url in urls.items():
            try:
                r = await client.get(f"{url}/health", timeout=3.0)
                results["services"][name] = "ok" if r.status_code == 200 else "down"
            except Exception:
                results["services"][name] = "down"

        return results

@app.api_route("/api/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy(request: Request, token: str = Depends(oauth2_scheme)):
    jwt_handler.verify_token(token)
    return await service_router.route_request(request)
