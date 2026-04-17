import json
import logging
import signal
import socket
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import redis
import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.auth import verify_api_key
from app.config import settings
from app.cost_guard import check_monthly_budget, estimate_cost_usd, record_monthly_spend
from app.rate_limiter import check_rate_limit
from utils.mock_llm import ask as mock_ask


logging.basicConfig(
    level=getattr(logging, settings.log_level, logging.INFO),
    format='{"ts":"%(asctime)s","level":"%(levelname)s","msg":"%(message)s"}',
)
logger = logging.getLogger(__name__)

INSTANCE_ID = socket.gethostname()
START_MONO = time.monotonic()
_redis: redis.Redis | None = None
_is_ready = False
_is_shutting_down = False
_in_flight = 0


class AskRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=128)
    question: str = Field(..., min_length=1, max_length=2000)


class AskResponse(BaseModel):
    user_id: str
    question: str
    answer: str
    served_by: str
    usage: dict
    timestamp: str


def redis_client() -> redis.Redis:
    if _redis is None:
        raise HTTPException(503, "Redis not initialized")
    return _redis


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _redis, _is_ready, _is_shutting_down

    _is_shutting_down = False
    logger.info(json.dumps({"event": "startup", "instance": INSTANCE_ID}))

    try:
        _redis = redis.from_url(settings.redis_url, decode_responses=True)
        _redis.ping()
    except Exception as exc:
        logger.exception("Redis connection failed")
        raise RuntimeError(f"Redis unavailable: {exc}")

    _is_ready = True
    yield

    _is_shutting_down = True
    _is_ready = False
    timeout = 30
    waited = 0
    while _in_flight > 0 and waited < timeout:
        logger.info(json.dumps({"event": "waiting_in_flight", "count": _in_flight}))
        time.sleep(1)
        waited += 1

    logger.info(json.dumps({"event": "shutdown", "instance": INSTANCE_ID}))


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs" if settings.environment != "production" else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-API-Key"],
)


@app.middleware("http")
async def tracking_and_security(request: Request, call_next):
    global _in_flight
    _in_flight += 1
    start = time.time()
    try:
        response: Response = await call_next(request)
    finally:
        _in_flight -= 1

    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    if "server" in response.headers:
        del response.headers["server"]

    logger.info(
        json.dumps(
            {
                "event": "request",
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "ms": round((time.time() - start) * 1000, 2),
            }
        )
    )
    return response


@app.get("/")
def root():
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "instance": INSTANCE_ID,
    }


@app.get("/health")
def health():
    redis_ok = False
    try:
        redis_client().ping()
        redis_ok = True
    except Exception:
        redis_ok = False

    return {
        "status": "ok" if redis_ok else "degraded",
        "instance_id": INSTANCE_ID,
        "uptime_seconds": round(time.monotonic() - START_MONO, 1),
        "redis_connected": redis_ok,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/ready")
def ready():
    if _is_shutting_down:
        raise HTTPException(503, "Shutting down")
    if not _is_ready:
        raise HTTPException(503, "Not ready")
    try:
        redis_client().ping()
    except Exception:
        raise HTTPException(503, "Redis unavailable")
    return {"ready": True, "instance": INSTANCE_ID}


@app.post("/ask", response_model=AskResponse)
def ask_agent(body: AskRequest, _api_key: str = Depends(verify_api_key)):
    r = redis_client()

    rate_info = check_rate_limit(
        redis_client=r,
        user_id=body.user_id,
        limit=settings.rate_limit_per_minute,
        window_seconds=60,
    )

    # Token and cost estimation for budget check
    in_tokens = len(body.question.split()) * 2
    estimated_out_tokens = 80
    estimated_cost = estimate_cost_usd(
        in_tokens,
        estimated_out_tokens,
        settings.price_per_1k_input_tokens,
        settings.price_per_1k_output_tokens,
    )
    check_monthly_budget(r, body.user_id, estimated_cost, settings.monthly_budget_usd)

    history_key = f"history:{body.user_id}"
    user_turn = {
        "role": "user",
        "content": body.question,
        "ts": datetime.now(timezone.utc).isoformat(),
    }
    r.rpush(history_key, json.dumps(user_turn))

    answer = mock_ask(body.question)
    out_tokens = len(answer.split()) * 2
    actual_cost = estimate_cost_usd(
        in_tokens,
        out_tokens,
        settings.price_per_1k_input_tokens,
        settings.price_per_1k_output_tokens,
    )
    total_monthly_spend = record_monthly_spend(r, body.user_id, actual_cost)

    assistant_turn = {
        "role": "assistant",
        "content": answer,
        "ts": datetime.now(timezone.utc).isoformat(),
    }
    r.rpush(history_key, json.dumps(assistant_turn))
    r.ltrim(history_key, -20, -1)

    return AskResponse(
        user_id=body.user_id,
        question=body.question,
        answer=answer,
        served_by=INSTANCE_ID,
        usage={
            "rate_limit_remaining": rate_info["remaining"],
            "monthly_spend_usd": total_monthly_spend,
            "monthly_budget_usd": settings.monthly_budget_usd,
        },
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


def _on_signal(signum, _frame):
    global _is_ready, _is_shutting_down
    _is_shutting_down = True
    _is_ready = False
    logger.info(json.dumps({"event": "signal", "signum": signum}))


signal.signal(signal.SIGTERM, _on_signal)
signal.signal(signal.SIGINT, _on_signal)


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=False,
        timeout_graceful_shutdown=30,
    )
