import os
from collections.abc import Generator
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import Settings, get_settings
from app.db.base import Base

_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def _is_sqlite(settings: Settings) -> bool:
    return settings.database_url.startswith("sqlite")


def _run_migrations_on_startup() -> bool:
    return os.getenv("RUN_DATABASE_MIGRATIONS_ON_STARTUP", "").lower() in {"1", "true", "yes", "on"}


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

    current_settings = settings or get_settings()
    if _run_migrations_on_startup():
        run_migrations(current_settings)
        return

    if not _is_sqlite(current_settings):
        return

    engine = get_engine(current_settings)
    Base.metadata.create_all(bind=engine)


def run_migrations(settings: Settings | None = None) -> None:
    current_settings = settings or get_settings()
    alembic_ini = Path(__file__).resolve().parents[2] / "alembic.ini"
    config = Config(str(alembic_ini))
    config.set_main_option("sqlalchemy.url", current_settings.database_url)
    config.set_main_option("script_location", str(alembic_ini.parent / "alembic"))
    command.upgrade(config, "head")


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
