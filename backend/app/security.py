import time
from dataclasses import dataclass, field

from fastapi import HTTPException, Request, status

from app.config import Settings


@dataclass
class LoginAttemptWindow:
    first_attempt_at: float
    attempts: int = 0


@dataclass
class InMemoryLoginRateLimiter:
    attempts_by_key: dict[str, LoginAttemptWindow] = field(default_factory=dict)

    def check(self, *, key: str, settings: Settings) -> None:
        now = time.monotonic()
        window = self.attempts_by_key.get(key)
        if window is None or now - window.first_attempt_at > settings.login_rate_limit_window_seconds:
            self.attempts_by_key[key] = LoginAttemptWindow(first_attempt_at=now, attempts=0)
            return
        if window.attempts >= settings.login_rate_limit_attempts:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="登录尝试过于频繁，请稍后再试。",
            )

    def record_failure(self, *, key: str, settings: Settings) -> None:
        now = time.monotonic()
        window = self.attempts_by_key.get(key)
        if window is None or now - window.first_attempt_at > settings.login_rate_limit_window_seconds:
            self.attempts_by_key[key] = LoginAttemptWindow(first_attempt_at=now, attempts=1)
            return
        window.attempts += 1

    def record_success(self, *, key: str) -> None:
        self.attempts_by_key.pop(key, None)

    def reset(self) -> None:
        self.attempts_by_key.clear()


login_rate_limiter = InMemoryLoginRateLimiter()


def login_rate_limit_key(request: Request, username: str) -> str:
    client_host = request.client.host if request.client else "unknown"
    return f"{client_host}:{username.strip().lower()}"
