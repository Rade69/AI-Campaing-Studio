"""Unit tests for ``scripts/generate_phase0_gate_report.py``.

The hard-to-fake parts (subprocess, bootstrap) are tested end-to-end
on the current repo. The schema/render logic is tested with a tiny
in-memory set of ``CheckResult`` objects.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

_SCRIPTS = Path(__file__).resolve().parents[3] / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import generate_phase0_gate_report as gpr  # type: ignore[import-not-found]  # noqa: E402  isort: skip


# --- render_report ------------------------------------------------------


def test_render_report_passes_when_all_checks_true() -> None:
    checks = [gpr.CheckResult(key, True, "ok") for key in gpr.CHECK_KEYS]
    report = gpr.render_report(checks)
    assert report["status"] == "PASS"
    assert all(report["checks"].values())
    assert report["phase"] == "implementation-phase-0"
    assert report["ui_framework"] == "NOT_SELECTED"
    assert report["campaign_engine_implemented"] is False
    assert report["website_ingestion_implemented"] is False
    assert report["notes"] == []


def test_render_report_fails_when_any_check_false() -> None:
    checks = [gpr.CheckResult(key, True, "ok") for key in gpr.CHECK_KEYS]
    checks[3] = gpr.CheckResult("pytest", False, "boom")
    report = gpr.render_report(checks)
    assert report["status"] == "FAIL"
    assert report["checks"]["pytest"] is False
    # ``status`` must never be "PASS" with a hidden False — every False
    # is mirrored in ``checks`` and the top-level status.
    assert not all(report["checks"].values())
    # The note carries the failing check's detail.
    assert any(note["key"] == "pytest" for note in report["notes"])


def test_render_report_fills_missing_keys_with_false() -> None:
    """If a check key is missing from the input, it must default to False
    and force a FAIL — never silently pass."""
    checks = [gpr.CheckResult("package_import", True)]
    report = gpr.render_report(checks)
    assert report["status"] == "FAIL"
    for key in gpr.CHECK_KEYS:
        assert key in report["checks"]
    assert report["checks"]["ruff"] is False  # missing → False


def test_check_keys_match_plan_schema() -> None:
    """The 17 check keys in the plan §35 must all be present, and no
    more / no less."""
    expected = {
        "package_import",
        "ruff",
        "mypy",
        "pytest",
        "architecture_boundaries",
        "translations",
        "regional_language_resources",
        "platform_registry",
        "provider_registry",
        "secret_store",
        "database_connection",
        "migrations",
        "unit_of_work",
        "job_manager",
        "bootstrap",
        "health_check",
        "no_secrets_detected",
    }
    assert set(gpr.CHECK_KEYS) == expected


# --- write_report -------------------------------------------------------


def test_write_report_creates_artifacts_dir(tmp_path: Path) -> None:
    artifacts = tmp_path / "fresh" / "artifacts"
    out = gpr.write_report({"status": "PASS"}, artifacts)
    assert out == artifacts / "phase0_foundation_gate.json"
    assert out.is_file()
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["status"] == "PASS"


def test_write_report_overwrites_existing(tmp_path: Path) -> None:
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    gpr.write_report({"status": "PASS"}, artifacts)
    gpr.write_report({"status": "FAIL"}, artifacts)
    payload = json.loads(
        (artifacts / "phase0_foundation_gate.json").read_text(encoding="utf-8")
    )
    assert payload["status"] == "FAIL"


# --- end-to-end: actual gate report against the current repo -----------


def test_gate_report_against_current_repo_passes() -> None:
    """Run the real gate report generator. This exercises every check
    for real (subprocess, import + function call, registry load,
    health check, secret scan).

    The gate report itself runs ``pytest -q`` as part of its ``pytest``
    check. To avoid infinite recursion (gate → pytest → gate → …) the
    gate report sets ``ACS_GATE_REPORT_RUNNING=1`` for its ``pytest``
    subprocess; this test respects that and short-circuits.
    """
    if os.environ.get("ACS_GATE_REPORT_RUNNING") == "1":
        pytest.skip(
            "gate report e2e skipped while inside the gate report's own "
            "pytest invocation (ACS_GATE_REPORT_RUNNING=1)"
        )

    repo_root = Path(__file__).resolve().parents[3]
    completed = subprocess.run(
        [
            sys.executable,
            str(repo_root / "scripts" / "generate_phase0_gate_report.py"),
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        # Surface a readable failure rather than a bare assert.
        pytest.fail(
            "gate report failed:\n"
            f"  stdout={completed.stdout!r}\n"
            f"  stderr={completed.stderr!r}"
        )

    payload_path = repo_root / "artifacts" / "phase0_foundation_gate.json"
    assert payload_path.is_file()
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    assert payload["status"] == "PASS"
    for key in gpr.CHECK_KEYS:
        assert payload["checks"][key] is True, f"check {key} unexpectedly false"
    assert payload["ui_framework"] == "NOT_SELECTED"
    assert payload["campaign_engine_implemented"] is False
    assert payload["website_ingestion_implemented"] is False
    assert payload["notes"] == []
