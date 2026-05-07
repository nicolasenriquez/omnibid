from __future__ import annotations

import importlib.util
import shutil
from pathlib import Path
from types import ModuleType

import pytest


def _load_test_db_guard_module() -> ModuleType:
    script_path = Path(__file__).resolve().parents[2] / "scripts" / "test_db_guard.py"
    spec = importlib.util.spec_from_file_location("test_db_guard_module", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load scripts/test_db_guard.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_has_integration_tests_scans_repo_root_not_cwd(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_test_db_guard_module()

    sandbox_root = Path("tests") / "_tmp_test_db_guard"
    repo_root = (sandbox_root / "repo").resolve()
    tests_root = repo_root / "tests"
    outside_cwd = sandbox_root / "outside"

    if sandbox_root.exists():
        shutil.rmtree(sandbox_root, ignore_errors=True)

    tests_root.mkdir(parents=True)
    outside_cwd.mkdir(parents=True)
    (tests_root / "test_marker.py").write_text(
        "@pytest.mark.integration\n"
        "def test_placeholder() -> None:\n"
        "    assert True\n",
        encoding="utf-8",
    )

    try:
        monkeypatch.setattr(module, "REPO_ROOT", repo_root)
        monkeypatch.chdir(outside_cwd)
        assert module._has_integration_tests() is True
    finally:
        shutil.rmtree(sandbox_root, ignore_errors=True)
