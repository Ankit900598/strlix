from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="STRLIX_", env_file=".env", extra="ignore")

    database_url: str = ""
    market_db: str = "sqlite:///./demo/cloud-phone-market/market-dev.db"

    jwt_secret: str = "dev-only-change-me"
    jwt_iss: str = "strlix-market"
    jwt_aud: str = "market-api"
    jwt_access_ttl_sec: int = 900
    jwt_refresh_ttl_sec: int = 604800

    redis_url: str = ""
    redis_password: str = ""

    pay_mode: str = "test"
    pay_provider: str = "stripe"
    stripe_publishable_key: str = "pk_test_REPLACE_ME"
    stripe_secret_key: str = "sk_test_REPLACE_ME"
    razorpay_key_id: str = "rzp_test_REPLACE_ME"
    razorpay_key_secret: str = "REPLACE_ME"

    stream_url: str = "http://127.0.0.1:8789"
    stream_fallback: str = "http://127.0.0.1:8787"
    cors_origins: str = "*"

    rate_limit_per_min: int = 60
    applicationinsights_connection_string: str = ""

    @property
    def use_postgres(self) -> bool:
        url = (self.database_url or self.market_db or "").strip()
        return url.startswith("postgres://") or url.startswith("postgresql://")

    @property
    def pg_dsn(self) -> str:
        url = (self.database_url or self.market_db or "").strip()
        if url.startswith("postgres://"):
            return "postgresql://" + url[len("postgres://"):]
        return url

settings = Settings()
