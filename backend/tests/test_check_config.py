import pytest

from app import check_config


def test_run_checks_passes_without_upstream_network(monkeypatch: pytest.MonkeyPatch) -> None:
    lines: list[str] = []

    def fail_upstream(*args: object, **kwargs: object) -> check_config.CheckResult:
        raise AssertionError("upstream check should be opt-in")

    monkeypatch.setattr(check_config, "check_upstream", fail_upstream)

    exit_code = check_config.run_checks(printer=lines.append)

    assert exit_code == 0
    assert lines == [
        "[OK] settings: loaded and validated",
        "[OK] storage: IMAGE_STORAGE_DIR is writable",
        "[OK] database: connected and expected tables are present",
        "[SKIP] upstream: network check disabled; pass --check-upstream to enable",
    ]


def test_run_checks_can_include_upstream_network(monkeypatch: pytest.MonkeyPatch) -> None:
    lines: list[str] = []

    def pass_upstream(*args: object, **kwargs: object) -> check_config.CheckResult:
        return check_config.CheckResult("upstream", True, "reachable with HTTP 200")

    monkeypatch.setattr(check_config, "check_upstream", pass_upstream)

    exit_code = check_config.run_checks(check_upstream_network=True, printer=lines.append)

    assert exit_code == 0
    assert lines[-1] == "[OK] upstream: reachable with HTTP 200"


def test_run_checks_reports_storage_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    lines: list[str] = []

    def fail_storage(settings: object) -> check_config.CheckResult:
        return check_config.CheckResult("storage", False, "IMAGE_STORAGE_DIR is not writable: OSError")

    monkeypatch.setattr(check_config, "check_storage", fail_storage)

    exit_code = check_config.run_checks(printer=lines.append)

    assert exit_code == 1
    assert "[FAIL] storage: IMAGE_STORAGE_DIR is not writable: OSError" in lines


def test_load_settings_does_not_print_secret_inputs(monkeypatch: pytest.MonkeyPatch) -> None:
    leaked_secret = "short-secret"
    monkeypatch.setenv("JWT_SECRET_KEY", leaked_secret)

    settings, result = check_config.load_settings()

    assert settings is None
    assert result.ok is False
    assert leaked_secret not in result.message
    assert "JWT_SECRET_KEY" in result.message


def test_parse_args_defaults_to_skipping_upstream() -> None:
    args = check_config.parse_args([])

    assert args.check_upstream is False


def test_parse_args_accepts_check_upstream() -> None:
    args = check_config.parse_args(["--check-upstream"])

    assert args.check_upstream is True
