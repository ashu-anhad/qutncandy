from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    environment: str = "development"  # "production" turns on the safety checks below
    database_url: str = "postgresql+psycopg://candy:candy@localhost:5432/cutencandy"
    cors_origins: str = "http://localhost:5173"

    jwt_secret: str = "change-me"
    access_token_minutes: int = 15
    refresh_token_days: int = 30
    cookie_secure: bool = False

    media_dir: str = "media"
    media_url: str = "/media"
    max_upload_mb: int = 5

    # Checkout (money in paise)
    shipping_fee: int = 9900
    free_shipping_min: int = 199900
    order_expiry_minutes: int = 15
    max_qty_per_item: int = 10

    # Razorpay (test keys start with rzp_test_). Empty = online payment disabled.
    razorpay_key_id: str = ""
    razorpay_key_secret: str = ""
    razorpay_webhook_secret: str = ""
    store_name: str = "QutnCandy"

    # Public URL of the storefront, used for links in emails.
    site_url: str = "http://localhost:5173"
    low_stock_threshold: int = 3

    # Email (SMTP). Empty host = emails are written to the log instead of sent.
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    mail_from: str = "QutnCandy <no-reply@qutncandy.com>"

    # Google sign-in (OAuth Web client ID). Empty = Google button hidden.
    google_client_id: str = ""
    # Phone OTP login. Until an SMS provider is wired into core/messaging.py, codes go to the log.
    otp_enabled: bool = False

    @model_validator(mode="after")
    def check_production(self):
        """Refuse to run in production with development defaults."""
        if self.environment == "production":
            problems = []
            if self.jwt_secret in ("", "change-me") or len(self.jwt_secret) < 32:
                problems.append("JWT_SECRET must be a long random value")
            if not self.cookie_secure:
                problems.append("COOKIE_SECURE must be true")
            if not self.site_url.startswith("https://"):
                problems.append("SITE_URL must use https://")
            if self.otp_enabled:
                problems.append("OTP_ENABLED must be false until an SMS provider is connected")
            if problems:
                raise ValueError("Unsafe production settings: " + "; ".join(problems))
        return self


settings = Settings()
