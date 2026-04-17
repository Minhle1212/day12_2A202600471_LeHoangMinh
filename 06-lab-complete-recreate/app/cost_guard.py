from datetime import datetime, timezone

from fastapi import HTTPException
from redis import Redis


def estimate_cost_usd(
    input_tokens: int,
    output_tokens: int,
    price_per_1k_input_tokens: float,
    price_per_1k_output_tokens: float,
) -> float:
    input_cost = (input_tokens / 1000) * price_per_1k_input_tokens
    output_cost = (output_tokens / 1000) * price_per_1k_output_tokens
    return round(input_cost + output_cost, 6)


def _month_key(user_id: str) -> str:
    month = datetime.now(timezone.utc).strftime("%Y-%m")
    return f"budget:{user_id}:{month}"


def check_monthly_budget(redis_client: Redis, user_id: str, additional_cost: float, monthly_budget: float) -> None:
    key = _month_key(user_id)
    current = float(redis_client.get(key) or 0)
    projected = current + additional_cost
    if projected > monthly_budget:
        raise HTTPException(
            status_code=402,
            detail={
                "error": "Monthly budget exceeded",
                "budget_usd": monthly_budget,
                "used_usd": round(current, 6),
                "would_be_usd": round(projected, 6),
            },
        )


def record_monthly_spend(redis_client: Redis, user_id: str, cost: float) -> float:
    key = _month_key(user_id)
    updated = redis_client.incrbyfloat(key, cost)
    # expire safely after month rollover window
    redis_client.expire(key, 35 * 24 * 3600)
    return round(float(updated), 6)
