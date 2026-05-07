from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.config import Settings, get_settings
from app.repositories.users import get_user_by_username, update_last_login
from app.security import login_rate_limit_key, login_rate_limiter
from app.schemas import CurrentUserResponse, LoginRequest, LoginResponse
from app.services.auth import create_access_token, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(
    request: Request,
    login_request: LoginRequest,
    session: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> LoginResponse:
    rate_limit_key = login_rate_limit_key(request, login_request.username)
    login_rate_limiter.check(key=rate_limit_key, settings=settings)

    user = get_user_by_username(session, login_request.username)
    if user is None or not verify_password(login_request.password, user.password_hash):
        login_rate_limiter.record_failure(key=rate_limit_key, settings=settings)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")
    if not user.is_active:
        login_rate_limiter.record_failure(key=rate_limit_key, settings=settings)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号已禁用")

    login_rate_limiter.record_success(key=rate_limit_key)
    update_last_login(session, user)
    return LoginResponse(
        access_token=create_access_token(user, settings),
        user=CurrentUserResponse(id=user.id, username=user.username, role=user.role),
    )


@router.get("/me", response_model=CurrentUserResponse)
def me(user=Depends(get_current_user)) -> CurrentUserResponse:
    return CurrentUserResponse(id=user.id, username=user.username, role=user.role)


@router.post("/logout")
def logout() -> dict[str, bool]:
    return {"success": True}
