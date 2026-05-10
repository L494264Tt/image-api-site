from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import Settings
from app.models.user import User

password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class InvalidTokenError(ValueError):
    pass


def hash_password(password: str) -> str:
    return password_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return password_context.verify(password, password_hash)


def create_access_token(user: User, settings: Settings) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {
        "sub": str(user.id),
        "username": user.username,
        "role": user.role,
        "exp": expires_at,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm="HS256")


def decode_access_token(token: str, settings: Settings) -> dict[str, str]:
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=["HS256"])
    except JWTError as exc:
        raise InvalidTokenError("Invalid access token") from exc

    if "sub" not in payload:
        raise InvalidTokenError("Token subject missing")

    return payload


def create_job_events_token(user: User, *, job_id: int, settings: Settings) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)
    payload = {
        "sub": str(user.id),
        "job_id": job_id,
        "scope": "generation_job_events",
        "exp": expires_at,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm="HS256")


def decode_job_events_token(token: str, *, job_id: int, settings: Settings) -> dict[str, str]:
    payload = decode_access_token(token, settings)
    if payload.get("scope") != "generation_job_events":
        raise InvalidTokenError("Invalid token scope")
    if int(payload.get("job_id", 0)) != job_id:
        raise InvalidTokenError("Token job mismatch")
    return payload
