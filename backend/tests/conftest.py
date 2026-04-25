import os
from pathlib import Path

import pytest


os.environ.setdefault("APP_NAME", "Image API Site Backend Test")
os.environ.setdefault("APP_HOST", "127.0.0.1")
os.environ.setdefault("APP_PORT", "8000")
os.environ.setdefault("UPSTREAM_BASE_URL", "https://example.com")
os.environ.setdefault("UPSTREAM_API_KEY", "sk-test")
os.environ.setdefault("UPSTREAM_IMAGE_PATH", "/v1/responses")
os.environ.setdefault("UPSTREAM_MODEL", "gpt-image-2")
os.environ.setdefault("UPSTREAM_RESPONSES_MODEL", "gpt-5.4")
os.environ.setdefault("UPSTREAM_TIMEOUT_SECONDS", "240")
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///./test_image_api_site.db")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret")
os.environ.setdefault("JWT_EXPIRE_MINUTES", "10080")
os.environ.setdefault("IMAGE_STORAGE_DIR", "./test_storage/images")
os.environ.setdefault("ADMIN_USERNAME", "admin")
os.environ.setdefault("ADMIN_PASSWORD", "replace-with-a-strong-admin-password")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:5173")


@pytest.fixture(autouse=True)
def reset_state() -> None:
    from app.config import get_settings
    from app.db.session import dispose_engine_for_tests, get_session_factory, reset_db_for_tests
    from app.repositories.users import create_user
    from app.services.auth import hash_password

    get_settings.cache_clear()
    dispose_engine_for_tests()
    settings = get_settings()
    storage_root = Path(settings.image_storage_dir).parent
    db_path = Path("./test_image_api_site.db")

    if db_path.exists():
        db_path.unlink()
    if storage_root.exists():
        for child in sorted(storage_root.rglob("*"), reverse=True):
            if child.is_file():
                child.unlink()
            elif child.is_dir():
                child.rmdir()
        if storage_root.exists():
            storage_root.rmdir()

    reset_db_for_tests(settings)
    session = get_session_factory(settings)()
    try:
        create_user(
            session,
            username=settings.admin_username,
            password_hash=hash_password(settings.admin_password),
            role="admin",
        )
    finally:
        session.close()
