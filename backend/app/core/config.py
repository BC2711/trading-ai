from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Trading AI"
    environment: str = "development"
    api_prefix: str = "/api"
    docs_enabled: bool = True
    api_key: str | None = None
    jwt_secret: str = "change-me-in-production"
    jwt_refresh_secret: str = "change-me-refresh-token-secret"
    access_token_expire_minutes: int = 120
    refresh_token_expire_days: int = 7
    login_throttle_max_attempts: int = 5
    login_throttle_window_seconds: int = 300
    login_throttle_lockout_seconds: int = 300
    development_auto_create_schema: bool = True
    development_schema_repair_enabled: bool = True
    credential_encryption_secret: str = "change-me-in-production"
    allowed_hosts: list[str] = ["localhost", "127.0.0.1", "testserver", "backend"]
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
    ]
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
    sentiment_providers: list[str] = ["newsapi", "cryptopanic", "reddit", "x"]
    sentiment_request_timeout_seconds: float = 8.0
    sentiment_items_per_provider: int = 10
    news_api_key: str | None = None
    news_api_base_url: str = "https://newsapi.org/v2/everything"
    cryptopanic_api_key: str | None = None
    cryptopanic_base_url: str = "https://cryptopanic.com/api/v1/posts/"
    reddit_bearer_token: str | None = None
    reddit_api_base_url: str = "https://www.reddit.com"
    reddit_subreddit: str = "CryptoCurrency"
    reddit_user_agent: str = "trading-ai/0.1"
    x_bearer_token: str | None = None
    x_recent_search_url: str = "https://api.x.com/2/tweets/search/recent"
    notification_request_timeout_seconds: float = 8.0
    notification_email_smtp_host: str | None = None
    notification_email_smtp_port: int = 587
    notification_email_use_tls: bool = True
    notification_email_username: str | None = None
    notification_email_password: str | None = None
    notification_email_from: str | None = None
    notification_email_to: list[str] = []
    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None
    telegram_api_base_url: str = "https://api.telegram.org"
    whatsapp_access_token: str | None = None
    whatsapp_phone_number_id: str | None = None
    whatsapp_to_number: str | None = None
    whatsapp_api_base_url: str = "https://graph.facebook.com/v20.0"
    discord_webhook_url: str | None = None

    # Websocket Settings
    ws_ping_interval: int = 20
    ws_ping_timeout: int = 10

    # Baseline API abuse protection. Use an edge proxy/WAF for distributed production rate limiting.
    rate_limit_enabled: bool = True
    rate_limit_requests: int = 120
    rate_limit_window_seconds: int = 60

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"

    @property
    def api_key_auth_enabled(self) -> bool:
        return bool(self.api_key)

    @property
    def expose_docs(self) -> bool:
        return self.docs_enabled and not self.is_production

    @model_validator(mode="after")
    def validate_production_settings(self) -> "Settings":
        if self.is_production:
            if not self.api_key:
                raise ValueError("API_KEY is required when ENVIRONMENT=production")
            if self.jwt_secret == "change-me-in-production":
                raise ValueError("JWT_SECRET must be changed when ENVIRONMENT=production")
            if self.jwt_refresh_secret == "change-me-refresh-token-secret":
                raise ValueError("JWT_REFRESH_SECRET must be changed when ENVIRONMENT=production")
            if self.credential_encryption_secret == "change-me-in-production":
                raise ValueError("CREDENTIAL_ENCRYPTION_SECRET must be changed when ENVIRONMENT=production")
            if "*" in self.allowed_hosts:
                raise ValueError("ALLOWED_HOSTS cannot contain '*' when ENVIRONMENT=production")
            if "*" in self.cors_origins:
                raise ValueError("CORS_ORIGINS cannot contain '*' when ENVIRONMENT=production")
        return self

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
