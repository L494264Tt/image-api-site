from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes_auth import router as auth_router
from app.api.routes_images import router as images_router
from app.api.routes import router as api_router
from app.config import get_settings
from app.db.session import get_session_factory, init_db
from app.repositories.users import get_user_by_username, create_user
from app.services.auth import hash_password


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

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
    app.include_router(images_router)
    return app


app = create_app()
