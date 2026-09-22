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

    # Payments — default TEST. Live requires pay_mode=live AND PAYMENTS_LIVE
    # AND allow_live_charges (see payments.live_charges_allowed).
    pay_mode: str = "test"
    pay_provider: str = "stripe"
    payments_live: bool = False  # STRLIX_PAYMENTS_LIVE; also read PAYMENTS_LIVE in payments.py
    allow_live_charges: bool = False  # STRLIX_ALLOW_LIVE_CHARGES — second gate
    stripe_publishable_key: str = "pk_test_REPLACE_ME"
    stripe_secret_key: str = "sk_test_REPLACE_ME"
    stripe_webhook_secret: str = "whsec_test_REPLACE_ME"
    razorpay_key_id: str = "rzp_test_REPLACE_ME"
    razorpay_key_secret: str = "REPLACE_ME"
    checkout_success_url: str = "http://127.0.0.1:8080/market/?paid=1"
    checkout_cancel_url: str = "http://127.0.0.1:8080/market/?canceled=1"

    stream_url: str = "http://127.0.0.1:8789"
    stream_fallback: str = "http://127.0.0.1:8787"
    cors_origins: str = "*"

    rate_limit_per_min: int = 60
    # Anonymous and signup paths stay tight during the free month. Redis is
    # the shared limiter when STRLIX_REDIS_URL is set; free launch does not
    # raise these caps.
    anon_rate_per_min: int = 5
    login_rate_per_min: int = 10
    waitlist_rate_per_min: int = 8
    applicationinsights_connection_string: str = ""

    # Launch billing. Default is a free first month with no card.
    # Live Stripe stays independently triple-gated in payments.py.
    # Turn the free month off only by setting BOTH:
    #   STRLIX_BILLING_MODE=test|live   (or unprefixed BILLING_MODE)
    #   STRLIX_FREE_LAUNCH_MODE=false   (or unprefixed FREE_LAUNCH_MODE)
    billing_mode: str = "free_month"
    free_launch_mode: bool = True
    free_month_days: int = 30
    invite_codes: str = ""  # comma-separated; empty = open signup
    support_email: str = "support@strlix.app"
    # True until the mailbox is monitored. Static legal pages say so;
    # they do not read this flag. Set false only after the inbox is live,
    # and edit static/legal plus web-market/legal in the same change.
    support_email_placeholder: bool = True

    # Auth. Default anon keeps /v1/auth/anon and phone-first demos working.
    # entra adds RS256 validation; it does not disable anon sessions.
    auth_mode: str = "anon"  # anon | entra
    entra_tenant_id: str = ""
    entra_client_id: str = ""
    entra_audience: str = "api://strlix-market"
    entra_issuer: str = ""
    entra_jwks_uri: str = ""
    entra_kind: str = "workforce"  # workforce | ciam

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
