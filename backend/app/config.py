from functools import lru_cache

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field(default="Image API Site Backend", alias="APP_NAME")
    app_host: str = Field(default="0.0.0.0", alias="APP_HOST")
    app_port: int = Field(default=8000, alias="APP_PORT")
    upstream_base_url: str = Field(alias="UPSTREAM_BASE_URL")
    upstream_api_key: str = Field(alias="UPSTREAM_API_KEY")
    upstream_image_path: str = Field(default="/v1/responses", alias="UPSTREAM_IMAGE_PATH")
    upstream_image_edit_path: str = Field(default="/v1/images/edits", alias="UPSTREAM_IMAGE_EDIT_PATH")
    upstream_model: str = Field(default="gpt-image-2", alias="UPSTREAM_MODEL")
    upstream_image_models: str = Field(default="gpt-image-2,gpt-image-1.5,gpt-image-1", alias="UPSTREAM_IMAGE_MODELS")
    upstream_responses_model: str = Field(default="gpt-5.4", alias="UPSTREAM_RESPONSES_MODEL")
    upstream_timeout_seconds: float = Field(default=240.0, alias="UPSTREAM_TIMEOUT_SECONDS")
    worker_poll_interval_seconds: float = Field(default=2.0, alias="WORKER_POLL_INTERVAL_SECONDS")
    worker_stale_after_seconds: int = Field(default=900, alias="WORKER_STALE_AFTER_SECONDS")
    worker_max_attempts: int = Field(default=2, alias="WORKER_MAX_ATTEMPTS")
    worker_id: str = Field(default="image-worker", alias="WORKER_ID")
    database_url: str = Field(alias="DATABASE_URL")
    jwt_secret_key: str = Field(alias="JWT_SECRET_KEY")
    jwt_expire_minutes: int = Field(default=60 * 24 * 7, alias="JWT_EXPIRE_MINUTES")
    image_storage_dir: str = Field(default="/app/storage/images", alias="IMAGE_STORAGE_DIR")
    admin_username: str = Field(default="admin", alias="ADMIN_USERNAME")
    admin_password: str = Field(alias="ADMIN_PASSWORD")
    cors_origins: str = Field(default="http://localhost:5173", alias="CORS_ORIGINS")
    app_env: str = Field(default="production", alias="APP_ENV")
    enable_api_docs: bool = Field(default=False, alias="ENABLE_API_DOCS")
    login_rate_limit_attempts: int = Field(default=5, alias="LOGIN_RATE_LIMIT_ATTEMPTS")
    login_rate_limit_window_seconds: int = Field(default=60, alias="LOGIN_RATE_LIMIT_WINDOW_SECONDS")
    max_active_generation_jobs_per_user: int = Field(default=3, alias="MAX_ACTIVE_GENERATION_JOBS_PER_USER")
    max_bulk_download_images: int = Field(default=50, alias="MAX_BULK_DOWNLOAD_IMAGES")
    max_bulk_download_bytes: int = Field(default=200 * 1024 * 1024, alias="MAX_BULK_DOWNLOAD_BYTES")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    def image_model_list(self) -> list[str]:
        models = [item.strip() for item in self.upstream_image_models.split(",") if item.strip()]
        if self.upstream_model not in models:
            return [self.upstream_model, *models]
        return models

    @field_validator("jwt_secret_key")
    @classmethod
    def validate_jwt_secret_key(cls, value: str) -> str:
        if value == "replace-with-at-least-32-random-characters":
            raise ValueError("JWT_SECRET_KEY must be changed before startup")
        if len(value) < 32:
            raise ValueError("JWT_SECRET_KEY must be at least 32 characters")
        return value

    @field_validator("admin_password")
    @classmethod
    def validate_admin_password(cls, value: str) -> str:
        if value in {"", "change-me", "password", "admin", "replace-with-a-strong-admin-password"}:
            raise ValueError("ADMIN_PASSWORD must be set to a non-default password")
        if len(value) < 12:
            raise ValueError("ADMIN_PASSWORD must be at least 12 characters")
        return value

    @model_validator(mode="after")
    def validate_cors(self) -> "Settings":
        if self.app_env.lower() == "production" and "*" in self.cors_origin_list():
            raise ValueError("CORS_ORIGINS cannot include * in production")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
