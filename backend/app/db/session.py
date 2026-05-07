from collections.abc import Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings, get_settings
from app.db.base import Base

_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def _is_sqlite(settings: Settings) -> bool:
    return settings.database_url.startswith("sqlite")


def get_engine(settings: Settings | None = None) -> Engine:
    global _engine
    current_settings = settings or get_settings()
    if _engine is None:
        kwargs: dict[str, object] = {"future": True}
        if _is_sqlite(current_settings):
            kwargs["connect_args"] = {"check_same_thread": False}
        _engine = create_engine(current_settings.database_url, **kwargs)
    return _engine


def get_session_factory(settings: Settings | None = None) -> sessionmaker[Session]:
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(
            bind=get_engine(settings),
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
            class_=Session,
        )
    return _session_factory


def get_db_session() -> Generator[Session, None, None]:
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()


def init_db(settings: Settings | None = None) -> None:
    from app import models  # noqa: F401

    engine = get_engine(settings)
    Base.metadata.create_all(bind=engine)
    ensure_runtime_schema(engine)


def ensure_runtime_schema(engine: Engine) -> None:
    inspector = inspect(engine)
    table_names = inspector.get_table_names()
    statements: list[str] = []

    if "image_generations" in table_names:
        columns = {column["name"] for column in inspector.get_columns("image_generations")}
        if "is_favorite" not in columns:
            if engine.dialect.name == "postgresql":
                statements.append("ALTER TABLE image_generations ADD COLUMN is_favorite BOOLEAN NOT NULL DEFAULT FALSE")
            else:
                statements.append("ALTER TABLE image_generations ADD COLUMN is_favorite BOOLEAN NOT NULL DEFAULT 0")
        if "deleted_at" not in columns:
            statements.append("ALTER TABLE image_generations ADD COLUMN deleted_at TIMESTAMP NULL")

    if "generation_jobs" in table_names:
        columns = {column["name"] for column in inspector.get_columns("generation_jobs")}
        if "request_payload" not in columns:
            if engine.dialect.name == "postgresql":
                statements.append("ALTER TABLE generation_jobs ADD COLUMN request_payload JSONB NOT NULL DEFAULT '{}'::jsonb")
            else:
                statements.append("ALTER TABLE generation_jobs ADD COLUMN request_payload JSON NOT NULL DEFAULT '{}'")
        if "attempt_count" not in columns:
            statements.append("ALTER TABLE generation_jobs ADD COLUMN attempt_count INTEGER NOT NULL DEFAULT 0")
        if "max_attempts" not in columns:
            statements.append("ALTER TABLE generation_jobs ADD COLUMN max_attempts INTEGER NOT NULL DEFAULT 2")
        if "locked_at" not in columns:
            statements.append("ALTER TABLE generation_jobs ADD COLUMN locked_at TIMESTAMP NULL")
        if "locked_by" not in columns:
            statements.append("ALTER TABLE generation_jobs ADD COLUMN locked_by VARCHAR(128) NULL")
        if "error_code" not in columns:
            statements.append("ALTER TABLE generation_jobs ADD COLUMN error_code VARCHAR(64) NULL")
        if "error_category" not in columns:
            statements.append("ALTER TABLE generation_jobs ADD COLUMN error_category VARCHAR(64) NULL")
        if "raw_error_message" not in columns:
            statements.append("ALTER TABLE generation_jobs ADD COLUMN raw_error_message TEXT NULL")
        if "effective_model" not in columns:
            statements.append("ALTER TABLE generation_jobs ADD COLUMN effective_model VARCHAR(64) NULL")
        if "endpoint_type" not in columns:
            statements.append("ALTER TABLE generation_jobs ADD COLUMN endpoint_type VARCHAR(64) NULL")

    if "image_generations" in table_names:
        columns = {column["name"] for column in inspector.get_columns("image_generations")}
        if "requested_model" not in columns:
            statements.append("ALTER TABLE image_generations ADD COLUMN requested_model VARCHAR(64) NULL")
        if "endpoint_type" not in columns:
            statements.append("ALTER TABLE image_generations ADD COLUMN endpoint_type VARCHAR(64) NULL")

    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))


def reset_db_for_tests(settings: Settings | None = None) -> None:
    from app import models  # noqa: F401

    engine = get_engine(settings)
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def dispose_engine_for_tests() -> None:
    global _engine, _session_factory
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _session_factory = None
