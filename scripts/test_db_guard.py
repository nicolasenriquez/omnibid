from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


ENV_FILE_PATH = Path(".env")


def _clean_env_value(raw_value: str) -> str:
    value = raw_value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def _read_from_dotenv(key: str, env_file_path: Path) -> str | None:
    if not env_file_path.exists():
        return None

    for line in env_file_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        name, raw_value = stripped.split("=", 1)
        if name.strip() == key:
            return _clean_env_value(raw_value)
    return None


def _get_required_test_database_url() -> str:
    test_url = os.getenv("TEST_DATABASE_URL") or _read_from_dotenv("TEST_DATABASE_URL", ENV_FILE_PATH)
    if not test_url:
        raise ValueError("TEST_DATABASE_URL is not set.")
    return test_url


def _get_runtime_database_url() -> str | None:
    return os.getenv("DATABASE_URL") or _read_from_dotenv("DATABASE_URL", ENV_FILE_PATH)


def ensure_test_database_safety() -> str:
    test_url = _get_required_test_database_url()
    runtime_url = _get_runtime_database_url()

    if runtime_url and runtime_url == test_url:
        raise ValueError("TEST_DATABASE_URL must differ from DATABASE_URL")

    return test_url


def run_integration_tests() -> int:
    test_url = ensure_test_database_safety()
    env = os.environ.copy()
    env["DATABASE_URL"] = test_url

    completed = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-m", "integration"],
        env=env,
        check=False,
    )
    return completed.returncode


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[1] not in {"check", "run-integration"}:
        print("Usage: python scripts/test_db_guard.py [check|run-integration]")
        return 2

    mode = argv[1]
    try:
        if mode == "check":
            ensure_test_database_safety()
            print("Test DB check passed")
            return 0

        return run_integration_tests()
    except ValueError as error:
        print(str(error))
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
