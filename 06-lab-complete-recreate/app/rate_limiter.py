import time
import uuid

from fastapi import HTTPException
from redis import Redis


def check_rate_limit(redis_client: Redis, user_id: str, limit: int = 10, window_seconds: int = 60) -> dict:
    """Sliding-window rate limit in Redis; raises 429 if exceeded."""
    now = time.time()
    key = f"rl:{user_id}"

    pipe = redis_client.pipeline()
    pipe.zremrangebyscore(key, 0, now - window_seconds)
    pipe.zcard(key)
    _, current_count = pipe.execute()

    if current_count >= limit:
        oldest = redis_client.zrange(key, 0, 0, withscores=True)
        if oldest:
            retry_after = max(1, int(oldest[0][1] + window_seconds - now) + 1)
        else:
            retry_after = window_seconds

        raise HTTPException(
            status_code=429,
            detail={
                "error": "Rate limit exceeded",
                "limit": limit,
                "window_seconds": window_seconds,
                "retry_after_seconds": retry_after,
            },
            headers={
                "Retry-After": str(retry_after),
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Remaining": "0",
            },
        )

    member = f"{now}:{uuid.uuid4().hex}"
    pipe = redis_client.pipeline()
    pipe.zadd(key, {member: now})
    pipe.expire(key, window_seconds + 5)
    pipe.execute()

    return {
        "limit": limit,
        "remaining": max(0, limit - (current_count + 1)),
        "window_seconds": window_seconds,
    }
