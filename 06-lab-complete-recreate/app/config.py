import logging
import os
from dataclasses import dataclass, field


@dataclass
class Settings:
    host: str = field(default_factory=lambda: os.getenv("HOST", "0.0.0.0"))
    port: int = field(default_factory=lambda: int(os.getenv("PORT", "8000")))
    environment: str = field(default_factory=lambda: os.getenv("ENVIRONMENT", "development"))
    app_name: str = field(default_factory=lambda: os.getenv("APP_NAME", "Day12 Production Agent"))
    app_version: str = field(default_factory=lambda: os.getenv("APP_VERSION", "1.0.0"))
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO").upper())

    # Security
    agent_api_key: str = field(default_factory=lambda: os.getenv("AGENT_API_KEY", "dev-secret-key"))
    allowed_origins: list[str] = field(
        default_factory=lambda: os.getenv("ALLOWED_ORIGINS", "*").split(",")
    )

    # Rate limiting + budget
    rate_limit_per_minute: int = field(
        default_factory=lambda: int(os.getenv("RATE_LIMIT_PER_MINUTE", "10"))
    )
    monthly_budget_usd: float = field(
        default_factory=lambda: float(os.getenv("MONTHLY_BUDGET_USD", "10.0"))
    )

    # State storage
    redis_url: str = field(default_factory=lambda: os.getenv("REDIS_URL", "redis://redis:6379/0"))

    # Mock LLM pricing defaults (cheap simulation)
    price_per_1k_input_tokens: float = field(
        default_factory=lambda: float(os.getenv("PRICE_PER_1K_INPUT_TOKENS", "0.00015"))
    )
    price_per_1k_output_tokens: float = field(
        default_factory=lambda: float(os.getenv("PRICE_PER_1K_OUTPUT_TOKENS", "0.0006"))
    )

    def validate(self):
        logger = logging.getLogger(__name__)
        if self.environment == "production" and self.agent_api_key == "dev-secret-key":
            raise ValueError("AGENT_API_KEY must be set in production")

        if self.rate_limit_per_minute <= 0:
            raise ValueError("RATE_LIMIT_PER_MINUTE must be positive")
        if self.monthly_budget_usd <= 0:
            raise ValueError("MONTHLY_BUDGET_USD must be positive")

        logger.info("Settings validated")
        return self


settings = Settings().validate()
