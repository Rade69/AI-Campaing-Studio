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


# --- _run_python subprocess observability (ACS-MAINT-001) -------------


def test_run_python_pytest_includes_stdout_tail(monkeypatch) -> None:
    """ACS-MAINT-001: when a pytest subprocess fails, ``notes[].detail``
    must include the stdout tail so the pytest ``FAILED tests/...``
    summary line is preserved for offline diagnosis. The stderr-only
    detail string is useless for the long-standing gate-report flake.
    """
    fake_completed = subprocess.CompletedProcess(
        args=[],
        returncode=1,
        stdout=(
            "..........F............                                          [ 60%]\n"
            "===================== short test summary info =====================\n"
            "FAILED tests/unit/scripts/test_x.py::test_y - AssertionError\n"
            "1 failed in 0.50s\n"
        ),
        stderr="some pytest warning line\n",
    )
    monkeypatch.setattr(gpr.subprocess, "run", lambda *a, **kw: fake_completed)

    passed, detail = gpr._run_python(
        Path("/tmp"), ["-m", "pytest", "-q"]
    )
    assert passed is False
    # stderr tail still present (back-compat with prior format).
    assert "stderr_tail=some pytest warning line" in detail
    # stdout tail present with the FAILED summary line.
    assert "stdout_tail=" in detail
    assert (
        "FAILED tests/unit/scripts/test_x.py::test_y" in detail
    )
    assert "1 failed in 0.50s" in detail
    # exit code present.
    assert "exit=1" in detail


def test_run_python_secret_scan_does_not_leak_stdout(monkeypatch) -> None:
    """ACS-MAINT-001 (regression guard): the secret-scan special case
    must REMAIN untouched. The secret scanner can echo the secret-
    shaped value it just detected on stderr, so ``notes[].detail`` for
    that check must contain ONLY the exit code, never stdout/stderr
    content. The new pytest-branch ``stdout_tail`` capture is gated
    by ``is_pytest`` and does NOT reach the secret-scan path.
    """
    fake_completed = subprocess.CompletedProcess(
        args=[],
        returncode=0,
        stdout="NO CONFIRMED SECRET in tracked files\n",
        stderr="would-have-leaked-secret-if-persisted\n",
    )
    monkeypatch.setattr(gpr.subprocess, "run", lambda *a, **kw: fake_completed)

    # The args list ends with ``check_no_secrets.py`` which is the
    # trigger for the secret-scan special case in ``_run_python``.
    passed, detail = gpr._run_python(
        Path("/tmp"),
        [str(Path("/repo") / "scripts" / "check_no_secrets.py")],
    )
    assert passed is True
    # Detail is the bare exit code -- no stderr_tail, no stdout_tail,
    # no leaked content.
    assert detail == "exit=0"
    assert "stderr_tail" not in detail
    assert "stdout_tail" not in detail
    assert "NO CONFIRMED SECRET" not in detail
    assert "would-have-leaked-secret" not in detail


def test_run_python_non_pytest_does_not_include_stdout_tail(
    monkeypatch,
) -> None:
    """ACS-MAINT-001 (regression guard): for non-pytest subprocess
    invocations (e.g. ``ruff``, ``mypy``), the ``detail`` string
    keeps the prior ``exit=N stderr_tail=...`` format -- it does NOT
    grow a ``stdout_tail=`` field. Adding it broadly would risk
    pulling in stdout from arbitrary tools; the contract scopes the
    new field to pytest only.
    """
    fake_completed = subprocess.CompletedProcess(
        args=[],
        returncode=1,
        stdout="ruff found 1 error\n",
        stderr="E501 line too long\n",
    )
    monkeypatch.setattr(gpr.subprocess, "run", lambda *a, **kw: fake_completed)

    passed, detail = gpr._run_python(
        Path("/tmp"),
        ["-m", "ruff", "check", "."],
    )
    assert passed is False
    assert "exit=1" in detail
    assert "stderr_tail=E501 line too long" in detail
    # No stdout_tail for non-pytest invocations.
    assert "stdout_tail" not in detail
    assert "ruff found 1 error" not in detail


# --- end-to-end: actual gate report against the current repo -----------


def test_gate_report_against_current_repo_passes() -> None:
    """Run the real gate report generator. This exercises every check
    for real (subprocess, import + function call, registry load,
    health check, secret scan).

    The gate report itself runs ``pytest -q`` as part of its ``pytest``
    check. To avoid infinite recursion (gate → pytest → gate → …) the
    gate report sets ``ACS_GATE_REPORT_RUNNING=1`` for its ``pytest``
    subprocess; this test respects that and short-circuits.

    Flake note (ACS-F1-052 + ACS-MAINT-001): this test is known to be
    intermittently flaky under heavy resource contention (e.g. when
    invoked immediately after a full 1223+ test-suite run). ACS-F1-052
    isolated the nested pytest invocation (``ACS_GATE_REPORT_RUNNING``,
    ``--basetemp``, ``-p no:cacheprovider``) which reduced the rate but
    did not eliminate the flake. ACS-MAINT-001 added stdout-tail
    observability so the *cause* of the next occurrence is in
    ``artifacts/phase0_foundation_gate.json`` under
    ``notes[].detail`` (look for ``stdout_tail=``). If this test fails,
    inspect that JSON first -- it should now contain pytest's
    ``FAILED tests/...`` summary line, not just a useless stderr tail.
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
