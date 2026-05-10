from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_admin_user, get_db
from app.models.user import User
from app.repositories.users import (
    create_user,
    get_user_by_id,
    get_user_by_username,
    list_users,
    update_user_active_status,
)
from app.schemas import UserCreateRequest, UserResponse, UserStatusRequest
from app.services.auth import hash_password

router = APIRouter(prefix="/api/admin", tags=["admin"])


def user_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        username=user.username,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
        updated_at=user.updated_at,
        last_login_at=user.last_login_at,
    )


@router.get("/users", response_model=list[UserResponse])
def admin_list_users(
    _: User = Depends(get_admin_user),
    session: Session = Depends(get_db),
) -> list[UserResponse]:
    return [user_response(user) for user in list_users(session)]


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def admin_create_user(
    request: UserCreateRequest,
    _: User = Depends(get_admin_user),
    session: Session = Depends(get_db),
) -> UserResponse:
    username = request.username.strip()
    role = request.role.strip()
    if not username:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Username is required")
    if not role:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Role is required")
    if get_user_by_username(session, username) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists")

    try:
        user = create_user(
            session,
            username=username,
            password_hash=hash_password(request.password),
            role=role,
            is_active=request.is_active,
        )
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists") from exc
    return user_response(user)


@router.patch("/users/{user_id}/status", response_model=UserResponse)
def admin_update_user_status(
    user_id: int,
    request: UserStatusRequest,
    admin: User = Depends(get_admin_user),
    session: Session = Depends(get_db),
) -> UserResponse:
    user = get_user_by_id(session, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.id == admin.id and not request.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot disable current admin user")

    return user_response(update_user_active_status(session, user, request.is_active))
