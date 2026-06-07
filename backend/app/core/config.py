from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Trading AI"
    api_prefix: str = "/api"
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:5174", "http://127.0.0.1:5173", "http://127.0.0.1:5174"]
    database_url: str = "postgresql+psycopg://trading:trading@localhost:5432/trading"
    redis_url: str = "redis://redis:6379/0"
    celery_broker_url: str = "redis://redis:6379/1"
    celery_result_backend: str = "redis://redis:6379/2"
    binance_api_base_url: str = "https://api.binance.com"
    market_sync_symbols: list[str] = ["BTCUSDT", "ETHUSDT"]
    market_sync_timeframe: str = "15m"
    market_sync_limit: int = 500
    market_sync_interval_minutes: int = 5
    market_sync_regenerate_signals: bool = True
    enable_metrics: bool = True
    sentry_dsn: str | None = None
    sentry_environment: str = "development"
    ai_provider: str = "rules"
    openai_api_key: str | None = None
    openai_api_base_url: str = "https://api.openai.com"
    openai_model: str = "gpt-3.5-turbo"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3"
    local_model_path: str | None = None

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
