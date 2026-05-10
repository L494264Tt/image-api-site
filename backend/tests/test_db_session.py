from sqlalchemy import inspect

from app.config import Settings
from app.db.session import dispose_engine_for_tests, get_engine, init_db


def _settings(database_url: str) -> Settings:
    return Settings.model_validate(
        {
            "UPSTREAM_BASE_URL": "https://example.com",
            "UPSTREAM_API_KEY": "sk-test",
            "DATABASE_URL": database_url,
            "JWT_SECRET_KEY": "test-secret-with-at-least-32-characters",
            "ADMIN_PASSWORD": "StrongTestAdminPass123!",
        }
    )


def test_init_db_creates_sqlite_schema_for_tests(tmp_path) -> None:
    dispose_engine_for_tests()
    settings = _settings(f"sqlite+pysqlite:///{tmp_path / 'init.db'}")

    init_db(settings)

    tables = set(inspect(get_engine(settings)).get_table_names())
    assert {"users", "image_generations", "generation_jobs", "uploads", "prompt_templates"} <= tables


def test_init_db_does_not_create_non_sqlite_schema(monkeypatch) -> None:
    settings = _settings("postgresql+psycopg://user:pass@localhost:5432/app")
    called = False

    def fail_get_engine(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("init_db should not create or mutate production schemas by default")

    monkeypatch.delenv("RUN_DATABASE_MIGRATIONS_ON_STARTUP", raising=False)
    monkeypatch.setattr("app.db.session.get_engine", fail_get_engine)

    init_db(settings)

    assert called is False


def test_init_db_runs_migrations_when_enabled(monkeypatch) -> None:
    settings = _settings("postgresql+psycopg://user:pass@localhost:5432/app")
    migrated = []

    monkeypatch.setenv("RUN_DATABASE_MIGRATIONS_ON_STARTUP", "true")
    monkeypatch.setattr("app.db.session.run_migrations", lambda received_settings: migrated.append(received_settings))

    init_db(settings)

    assert migrated == [settings]
