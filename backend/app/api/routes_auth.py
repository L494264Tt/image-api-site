from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.config import get_settings
from app.repositories.users import get_user_by_username, update_last_login
from app.schemas import CurrentUserResponse, LoginRequest, LoginResponse
from app.services.auth import create_access_token, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(request: LoginRequest, session: Session = Depends(get_db)) -> LoginResponse:
    user = get_user_by_username(session, request.username)
    if user is None or not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号已禁用")

    update_last_login(session, user)
    settings = get_settings()
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
