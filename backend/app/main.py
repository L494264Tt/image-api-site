from pathlib import Path
import secrets

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.routes_admin import router as admin_router
from app.api.routes_auth import router as auth_router
from app.api.routes_images import router as images_router
from app.api.routes_prompts import router as prompts_router
from app.api.routes_uploads import router as uploads_router
from app.api.routes import router as api_router
from app.config import get_settings
from app.db.session import get_engine, get_session_factory, init_db
from app.observability import REQUEST_ID_HEADER, RequestIdLoggingMiddleware, configure_logging
from app.repositories.users import get_user_by_username, create_user
from app.services.auth import hash_password


def create_app() -> FastAPI:
    configure_logging()
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        docs_url="/docs" if settings.enable_api_docs else None,
        redoc_url="/redoc" if settings.enable_api_docs else None,
        openapi_url="/openapi.json" if settings.enable_api_docs else None,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list(),
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", REQUEST_ID_HEADER],
        expose_headers=[REQUEST_ID_HEADER],
    )
    app.add_middleware(RequestIdLoggingMiddleware)

    @app.get("/api/health")
    async def health() -> dict[str, object]:
        checks = {
            "database": check_database_health(settings),
            "storage": check_storage_health(settings.image_storage_dir),
            "worker": {
                "status": "configured",
                "pollIntervalSeconds": settings.worker_poll_interval_seconds,
                "staleAfterSeconds": settings.worker_stale_after_seconds,
                "maxAttempts": settings.worker_max_attempts,
            },
        }
        status = "ok" if checks["database"]["status"] == "ok" and checks["storage"]["status"] == "ok" else "degraded"
        return {"status": status, "checks": checks}

    @app.on_event("startup")
    def bootstrap_admin() -> None:
        init_db(settings)
        session = get_session_factory(settings)()
        try:
            admin = get_user_by_username(session, settings.admin_username)
            if admin is None:
                create_user(
                    session,
                    username=settings.admin_username,
                    password_hash=hash_password(settings.admin_password),
                    role="admin",
                )
        finally:
            session.close()

    app.include_router(api_router)
    app.include_router(auth_router)
    app.include_router(admin_router)
    app.include_router(images_router)
    app.include_router(prompts_router)
    app.include_router(uploads_router)
    return app


app = create_app()


def check_database_health(settings) -> dict[str, str]:
    try:
        with get_engine(settings).connect() as connection:
            connection.execute(text("select 1"))
    except Exception as exc:
        return {"status": "error", "message": exc.__class__.__name__}
    return {"status": "ok"}


def check_storage_health(image_storage_dir: str) -> dict[str, str]:
    storage_dir = Path(image_storage_dir)
    probe = storage_dir / f".health-{secrets.token_hex(8)}.tmp"
    try:
        storage_dir.mkdir(parents=True, exist_ok=True)
        probe.write_text("ok", encoding="utf-8")
        if probe.read_text(encoding="utf-8") != "ok":
            return {"status": "error", "message": "probe_mismatch"}
    except Exception as exc:
        return {"status": "error", "message": exc.__class__.__name__}
    finally:
        probe.unlink(missing_ok=True)
    return {"status": "ok"}
