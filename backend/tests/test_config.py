from app.config import Settings


def test_settings_support_database_and_auth_values() -> None:
    settings = Settings.model_validate(
        {
            "APP_NAME": "Test",
            "APP_HOST": "127.0.0.1",
            "APP_PORT": 8000,
            "UPSTREAM_BASE_URL": "https://example.com",
            "UPSTREAM_API_KEY": "sk-test",
            "DATABASE_URL": "postgresql+psycopg://user:pass@localhost:5432/app",
            "JWT_SECRET_KEY": "secret",
            "IMAGE_STORAGE_DIR": "/tmp/storage",
            "ADMIN_USERNAME": "admin",
            "ADMIN_PASSWORD": "replace-with-a-strong-admin-password",
        }
    )

    assert settings.database_url.startswith("postgresql+psycopg://")
    assert settings.jwt_secret_key == "secret"
    assert settings.image_storage_dir == "/tmp/storage"
    assert settings.admin_username == "admin"
