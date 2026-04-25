from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field(default="Image API Site Backend", alias="APP_NAME")
    app_host: str = Field(default="0.0.0.0", alias="APP_HOST")
    app_port: int = Field(default=8000, alias="APP_PORT")
    upstream_base_url: str = Field(alias="UPSTREAM_BASE_URL")
    upstream_api_key: str = Field(alias="UPSTREAM_API_KEY")
    upstream_image_path: str = Field(default="/v1/responses", alias="UPSTREAM_IMAGE_PATH")
    upstream_model: str = Field(default="gpt-image-2", alias="UPSTREAM_MODEL")
    upstream_responses_model: str = Field(default="gpt-5.4", alias="UPSTREAM_RESPONSES_MODEL")
    upstream_timeout_seconds: float = Field(default=240.0, alias="UPSTREAM_TIMEOUT_SECONDS")
    database_url: str = Field(alias="DATABASE_URL")
    jwt_secret_key: str = Field(alias="JWT_SECRET_KEY")
    jwt_expire_minutes: int = Field(default=60 * 24 * 7, alias="JWT_EXPIRE_MINUTES")
    image_storage_dir: str = Field(default="/app/storage/images", alias="IMAGE_STORAGE_DIR")
    admin_username: str = Field(default="admin", alias="ADMIN_USERNAME")
    admin_password: str = Field(default="replace-with-a-strong-admin-password", alias="ADMIN_PASSWORD")
    cors_origins: str = Field(default="http://localhost:5173", alias="CORS_ORIGINS")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
