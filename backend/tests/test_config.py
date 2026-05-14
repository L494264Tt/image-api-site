import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import app


def test_settings_support_database_and_auth_values() -> None:
    settings = Settings.model_validate(
        {
            "APP_NAME": "Test",
            "APP_HOST": "127.0.0.1",
            "APP_PORT": 8000,
            "UPSTREAM_BASE_URL": "https://example.com",
            "UPSTREAM_API_KEY": "sk-test",
            "DATABASE_URL": "postgresql+psycopg://user:pass@localhost:5432/app",
            "JWT_SECRET_KEY": "test-secret-with-at-least-32-characters",
            "IMAGE_STORAGE_DIR": "/tmp/storage",
            "ADMIN_USERNAME": "admin",
            "ADMIN_PASSWORD": "StrongTestAdminPass123!",
        }
    )

    assert settings.database_url.startswith("postgresql+psycopg://")
    assert settings.jwt_secret_key == "test-secret-with-at-least-32-characters"
    assert settings.image_storage_dir == "/tmp/storage"
    assert settings.admin_username == "admin"
    assert settings.run_database_migrations_on_startup is False


def test_settings_support_startup_migration_flag() -> None:
    settings = Settings.model_validate(
        {
            "UPSTREAM_BASE_URL": "https://example.com",
            "UPSTREAM_API_KEY": "sk-test",
            "DATABASE_URL": "postgresql+psycopg://user:pass@localhost:5432/app",
            "JWT_SECRET_KEY": "test-secret-with-at-least-32-characters",
            "ADMIN_PASSWORD": "StrongTestAdminPass123!",
            "RUN_DATABASE_MIGRATIONS_ON_STARTUP": "true",
        }
    )

    assert settings.run_database_migrations_on_startup is True


def test_settings_reject_default_secret_values() -> None:
    with pytest.raises(ValueError):
        Settings.model_validate(
            {
                "UPSTREAM_BASE_URL": "https://example.com",
                "UPSTREAM_API_KEY": "sk-test",
                "DATABASE_URL": "postgresql+psycopg://user:pass@localhost:5432/app",
                "JWT_SECRET_KEY": "replace-with-at-least-32-random-characters",
                "ADMIN_PASSWORD": "StrongTestAdminPass123!",
            }
        )


def test_settings_reject_default_admin_password() -> None:
    with pytest.raises(ValueError):
        Settings.model_validate(
            {
                "UPSTREAM_BASE_URL": "https://example.com",
                "UPSTREAM_API_KEY": "sk-test",
                "DATABASE_URL": "postgresql+psycopg://user:pass@localhost:5432/app",
                "JWT_SECRET_KEY": "test-secret-with-at-least-32-characters",
                "ADMIN_PASSWORD": "admin",
            }
        )


def test_config_endpoint_exposes_model_capabilities() -> None:
    client = TestClient(app)

    response = client.get("/api/config")

    assert response.status_code == 200
    payload = response.json()
    assert payload["defaultModel"] == "gpt-image-2"
    assert payload["modelOptions"] == ["gpt-image-2"]
    assert payload["sizeOptions"] == ["auto", "1024x1024", "1024x1536", "1536x1024"]
    assert payload["qualityOptions"] == ["auto", "low", "medium", "high"]
    assert payload["backgroundOptions"] == ["auto", "transparent", "opaque"]
    assert payload["inputFidelityOptions"] == ["auto", "low", "high"]

    capability = payload["modelCapabilities"][0]
    assert capability["id"] == "gpt-image-2"
    assert capability["label"] == "gpt-image-2"
    assert capability["supports_text_to_image"] is True
    assert capability["supports_image_to_image"] is True
    assert capability["supports_image_input"] is True
    assert capability["default_endpoint"] == "responses"
    assert capability["sizes"] == payload["sizeOptions"]
    assert capability["qualities"] == payload["qualityOptions"]
    assert capability["backgrounds"] == payload["backgroundOptions"]
    assert capability["input_fidelities"] == payload["inputFidelityOptions"]
