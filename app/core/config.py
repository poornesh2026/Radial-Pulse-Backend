"""Application settings.

All configuration comes from environment variables (12-factor). Nothing
environment-specific is hard-coded. In AWS, the ECS task definition injects:

* plain values (APP_ENV, COGNITO_*, S3_ASSETS_BUCKET, ...) as environment variables
* DB_PASSWORD from Secrets Manager (the Aurora-managed master secret)

Locally, values come from ``services/api/.env`` (git-ignored; copy ``.env.example``).
"""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict
from sqlalchemy.engine import URL, make_url

AppEnv = Literal["local", "test", "dev", "prod"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # ---- runtime --------------------------------------------------------------
    app_env: AppEnv = "local"
    debug: bool = False
    log_level: str = "INFO"
    service_name: str = "radial-pulse-api"
    service_version: str = Field(default="0.1.0", description="Set to the git SHA by CI/CD.")
    #: Show /docs and /openapi.json. Defaults to on for local/dev, off for prod.
    docs_enabled: bool | None = None

    # ---- database -------------------------------------------------------------
    #: Full URL wins if set (local/test). Otherwise built from DB_* parts (AWS).
    database_url: SecretStr | None = None
    db_host: str | None = None
    db_port: int = 5432
    db_name: str = "radial_pulse"
    db_user: str | None = None
    db_password: SecretStr | None = None
    db_sslmode: Literal["disable", "prefer", "require", "verify-full"] = "prefer"
    db_pool_size: int = 5
    db_max_overflow: int = 5
    db_pool_recycle_seconds: int = 1800
    db_echo: bool = False

    # ---- HTTP -----------------------------------------------------------------
    cors_allowed_origins: Annotated[list[str], NoDecode] = Field(default_factory=list)

    # ---- auth (Cognito) -------------------------------------------------------
    cognito_region: str | None = None
    cognito_user_pool_id: str | None = None
    #: App client ids allowed to call the API (web + mobile). Comma-separated in env.
    cognito_app_client_ids: Annotated[list[str], NoDecode] = Field(default_factory=list)
    #: Hosted UI domain (https://...). Used to call /oauth2/userInfo on first sign-in.
    cognito_domain: str | None = None
    jwks_cache_seconds: int = 3600
    #: Clock skew allowance when checking exp/iat.
    jwt_leeway_seconds: int = 30

    # ---- storage (S3) ---------------------------------------------------------
    aws_region: str = "ap-south-1"
    s3_assets_bucket: str | None = None
    s3_kms_key_id: str | None = None
    s3_presign_ttl_seconds: int = 300
    max_upload_bytes: int = 200 * 1024 * 1024  # 200 MB

    # --------------------------------------------------------------- validators
    @field_validator("cors_allowed_origins", "cognito_app_client_ids", mode="before")
    @classmethod
    def _split_csv(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @model_validator(mode="after")
    def _environment_rules(self) -> Settings:
        if self.app_env == "prod":
            if self.debug:
                raise ValueError("DEBUG must be false in prod")
            if "*" in self.cors_allowed_origins:
                raise ValueError("Wildcard CORS is not allowed in prod")
            if any(o.startswith("http://") for o in self.cors_allowed_origins):
                raise ValueError("Prod CORS origins must be https")
            if self.db_sslmode not in ("require", "verify-full"):
                raise ValueError("Prod database connections must use TLS (DB_SSLMODE=require|verify-full)")
        if self.app_env in ("dev", "prod") and not self.auth_configured:
            raise ValueError("COGNITO_REGION, COGNITO_USER_POOL_ID and COGNITO_APP_CLIENT_IDS are required")
        return self

    # ------------------------------------------------------------ derived values
    @property
    def auth_configured(self) -> bool:
        return bool(self.cognito_region and self.cognito_user_pool_id and self.cognito_app_client_ids)

    @property
    def cognito_issuer(self) -> str | None:
        if not (self.cognito_region and self.cognito_user_pool_id):
            return None
        return f"https://cognito-idp.{self.cognito_region}.amazonaws.com/{self.cognito_user_pool_id}"

    @property
    def cognito_jwks_url(self) -> str | None:
        issuer = self.cognito_issuer
        return f"{issuer}/.well-known/jwks.json" if issuer else None

    @property
    def show_docs(self) -> bool:
        if self.docs_enabled is not None:
            return self.docs_enabled
        return self.app_env in ("local", "test", "dev")

    @property
    def sqlalchemy_url(self) -> URL:
        """Database URL. Never log this — it contains the password."""
        if self.database_url is not None:
            return make_url(self.database_url.get_secret_value())
        if not (self.db_host and self.db_user and self.db_password):
            raise RuntimeError("Database is not configured: set DATABASE_URL or DB_HOST/DB_USER/DB_PASSWORD")
        return URL.create(
            drivername="postgresql+psycopg",
            username=self.db_user,
            password=self.db_password.get_secret_value(),
            host=self.db_host,
            port=self.db_port,
            database=self.db_name,
            query={"sslmode": self.db_sslmode},
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
