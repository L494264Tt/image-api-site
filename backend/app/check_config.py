from __future__ import annotations

import argparse
import secrets
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import httpx
from pydantic import ValidationError
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from app.config import Settings


EXPECTED_TABLES = {
    "generation_jobs",
    "image_generations",
    "prompt_templates",
    "uploads",
    "users",
}


@dataclass(frozen=True)
class CheckResult:
    name: str
    ok: bool
    message: str


def _settings_error_message(exc: ValidationError) -> str:
    errors = exc.errors(include_input=False)
    if not errors:
        return "invalid settings"
    parts = []
    for error in errors:
        location = ".".join(str(item) for item in error.get("loc", ())) or "settings"
        message = str(error.get("msg", "invalid value"))
        parts.append(f"{location}: {message}")
    return "; ".join(parts)


def load_settings() -> tuple[Settings | None, CheckResult]:
    try:
        settings = Settings()
    except ValidationError as exc:
        return None, CheckResult("settings", False, _settings_error_message(exc))
    return settings, CheckResult("settings", True, "loaded and validated")


def check_storage(settings: Settings) -> CheckResult:
    storage_dir = Path(settings.image_storage_dir)
    probe_path = storage_dir / f".check-config-{secrets.token_hex(8)}.tmp"
    try:
        storage_dir.mkdir(parents=True, exist_ok=True)
        probe_path.write_text("ok", encoding="utf-8")
        if probe_path.read_text(encoding="utf-8") != "ok":
            return CheckResult("storage", False, "probe file contents did not round-trip")
    except OSError as exc:
        return CheckResult("storage", False, f"IMAGE_STORAGE_DIR is not writable: {exc.__class__.__name__}")
    finally:
        try:
            probe_path.unlink(missing_ok=True)
        except OSError:
            pass
    return CheckResult("storage", True, "IMAGE_STORAGE_DIR is writable")


def _build_engine(settings: Settings) -> Engine:
    kwargs: dict[str, object] = {"future": True}
    if settings.database_url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    return create_engine(settings.database_url, **kwargs)


def check_database(settings: Settings) -> CheckResult:
    engine = _build_engine(settings)
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
            table_names = set(inspect(connection).get_table_names())
    except SQLAlchemyError as exc:
        return CheckResult("database", False, f"connection failed: {exc.__class__.__name__}")
    finally:
        engine.dispose()

    missing_tables = sorted(EXPECTED_TABLES - table_names)
    if missing_tables:
        return CheckResult("database", False, f"connected, but missing tables: {', '.join(missing_tables)}")
    return CheckResult("database", True, "connected and expected tables are present")


def check_upstream(settings: Settings, *, timeout_seconds: float = 10.0) -> CheckResult:
    timeout = min(settings.upstream_timeout_seconds, timeout_seconds)
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            response = client.get(settings.upstream_base_url)
    except httpx.HTTPError as exc:
        return CheckResult("upstream", False, f"network check failed: {exc.__class__.__name__}")

    return CheckResult("upstream", True, f"reachable with HTTP {response.status_code}")


def format_result(result: CheckResult) -> str:
    status = "OK" if result.ok else "FAIL"
    return f"[{status}] {result.name}: {result.message}"


def run_checks(
    *,
    check_upstream_network: bool = False,
    printer: Callable[[str], None] = print,
) -> int:
    settings, settings_result = load_settings()
    results = [settings_result]
    printer(format_result(settings_result))
    if settings is None:
        return 1

    for check in (check_storage, check_database):
        result = check(settings)
        results.append(result)
        printer(format_result(result))

    if check_upstream_network:
        result = check_upstream(settings)
        results.append(result)
        printer(format_result(result))
    else:
        printer("[SKIP] upstream: network check disabled; pass --check-upstream to enable")

    return 0 if all(result.ok for result in results) else 1


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate backend runtime configuration.")
    parser.add_argument(
        "--check-upstream",
        action="store_true",
        help="also perform a network request to UPSTREAM_BASE_URL",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    return run_checks(check_upstream_network=args.check_upstream)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
