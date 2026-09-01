"""Generate ``artifacts/phase0_foundation_gate.json`` (machine-readable gate).

Usage:

    python scripts/generate_phase0_gate_report.py [--repo-root .]

This script never hardcodes any check result. Every key in the report is
filled by actually executing the corresponding command (subprocess) or
importing + calling the relevant module function, so a passing report
*means* the foundation is genuinely green at this revision.

Output schema (per plan §35 / contract §P0.28):

    {
      "phase": "implementation-phase-0",
      "status": "PASS" | "FAIL",
      "checks": { <17 booleans> },
      "ui_framework": "NOT_SELECTED",
      "campaign_engine_implemented": false,
      "website_ingestion_implemented": false,
      "notes": []
    }

``status`` is ``"PASS"`` **only** when every check is ``True``. Any
``False`` value flips ``status`` to ``"FAIL"`` — there is no middle
ground, and the report cannot lie.
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
import subprocess
import sys
import tempfile
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any

CHECK_KEYS: tuple[str, ...] = (
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
)


@dataclass(frozen=True)
class CheckResult:
    key: str
    passed: bool
    detail: str = ""


def _run_python(repo_root: Path, args: list[str]) -> tuple[bool, str]:
    """Run ``python -m <args>`` from ``repo_root`` and return ``(passed, detail)``.

    The ``pytest`` invocation is special: it sets
    ``ACS_GATE_REPORT_RUNNING=1`` so the gate-report end-to-end test (which
    invokes the real gate report) can detect that it is being run from
    inside the gate report and short-circuit. Without this guard the
    gate report would recurse forever: gate → pytest → gate → pytest → ….
    """
    is_pytest = (
        len(args) >= 2
        and args[0] == "-m"
        and args[1] == "pytest"
    )
    env = os.environ.copy() if is_pytest else None
    if is_pytest:
        env["ACS_GATE_REPORT_RUNNING"] = "1"
    try:
        completed = subprocess.run(
            [sys.executable, *args],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
            env=env,
        )
    except OSError as exc:
        return False, f"could not launch {args}: {exc}"
    passed = completed.returncode == 0
    stderr = completed.stderr.strip()
    last_line = stderr.splitlines()[-1] if stderr else "<empty>"
    detail = f"exit={completed.returncode} stderr_tail={last_line}"
    return passed, detail


def _check_package_import() -> CheckResult:
    try:
        module = importlib.import_module("ai_campaign_studio")
    except Exception as exc:  # noqa: BLE001
        return CheckResult("package_import", False, f"{type(exc).__name__}: {exc}")
    version = getattr(module, "__version__", "<missing>")
    return CheckResult("package_import", True, f"version={version}")


def _check_subprocess(key: str, repo_root: Path, args: list[str]) -> CheckResult:
    passed, detail = _run_python(repo_root, args)
    return CheckResult(key, passed, detail)


def _check_via_validate_resources(
    key: str, repo_root: Path
) -> CheckResult:
    """Use the in-process validator functions exposed by
    ``scripts/validate_resources`` for the i18n/regional sections. The
    process also runs the rest of the resource validation, but the gate
    report is split so the per-section check is precise.
    """
    sys.path.insert(0, str(repo_root / "scripts"))
    try:
        import validate_resources  # type: ignore[import-not-found]
    except Exception as exc:  # noqa: BLE001
        return CheckResult(key, False, f"import validate_resources: {exc}")
    resources = repo_root / "resources"
    if key == "translations":
        errors = validate_resources.validate_i18n(
            resources / "i18n" / "en.json", resources / "i18n" / "bhs.json"
        )
    elif key == "regional_language_resources":
        errors = []
        for path in sorted((resources / "regional_language").glob("bhs_*_v1.yaml")):
            errors.extend(validate_resources.validate_regional_yaml(path))
    else:  # pragma: no cover - guarded by caller
        return CheckResult(key, False, f"unsupported key {key!r}")
    if errors:
        return CheckResult(key, False, "; ".join(errors))
    return CheckResult(key, True, "ok")


def _check_registries_with_bootstrap(repo_root: Path) -> list[CheckResult]:
    """Run registry/secret-store/database/migrations/health checks via the
    real ``create_bootstrap`` against a temp data dir. This is the same
    path the CI health-check step uses, so the gate report cannot drift
    from CI behaviour.
    """
    results: list[CheckResult] = []
    data_dir = Path(tempfile.mkdtemp(prefix="acs-gate-"))
    try:
        from ai_campaign_studio.bootstrap import (  # type: ignore[import-not-found]
            create_bootstrap,
            run_health_check,
        )
        from ai_campaign_studio.config.paths import (  # type: ignore[import-not-found]
            AppPaths,
        )

        try:
            bootstrap = create_bootstrap(paths=AppPaths(data_dir_override=data_dir))
        except Exception as exc:  # noqa: BLE001
            # If bootstrap cannot be built, every downstream check is FAIL
            # with the same root cause; capture once and propagate.
            for key in (
                "platform_registry",
                "provider_registry",
                "secret_store",
                "database_connection",
                "migrations",
                "health_check",
            ):
                results.append(
                    CheckResult(key, False, f"bootstrap failed: {exc}")
                )
            return results
        try:
            health = run_health_check(bootstrap)
            health_ok = health.get("status") == "ok"
            results.append(
                CheckResult(
                    "health_check",
                    health_ok,
                    f"status={health.get('status')!r}",
                )
            )
            # Map gate-report keys → health-check payload keys.
            # ``bootstrap.run_health_check`` returns ``{"database": ...}``
            # (short name), but the gate schema mandates
            # ``"database_connection"`` (long name). They are distinct
            # variables; renaming one or the other would touch a runtime
            # contract owned by another P0 task, so the mapping lives here.
            health_key_map = (
                ("platform_registry", "platform_registry"),
                ("provider_registry", "provider_registry"),
                ("database_connection", "database"),
                ("migrations", "migrations"),
            )
            for gate_key, health_key in health_key_map:
                results.append(
                    CheckResult(
                        gate_key,
                        health.get(health_key) == "ok",
                        f"{health_key}={health.get(health_key)!r}",
                    )
                )
            results.append(
                CheckResult(
                    "secret_store",
                    health.get("secret_store") == "available",
                    f"secret_store={health.get('secret_store')!r}",
                )
            )
        except Exception as exc:  # noqa: BLE001
            for key in (
                "health_check",
                "platform_registry",
                "provider_registry",
                "secret_store",
                "database_connection",
                "migrations",
            ):
                if not any(result.key == key for result in results):
                    results.append(
                        CheckResult(key, False, f"{type(exc).__name__}: {exc}")
                    )
        finally:
            try:
                bootstrap.job_manager.shutdown(wait=False)
            except Exception:  # noqa: BLE001
                pass
            try:
                bootstrap.database_connection.close()
            except Exception:  # noqa: BLE001
                pass
    except Exception as exc:  # noqa: BLE001
        for key in (
            "platform_registry",
            "provider_registry",
            "secret_store",
            "database_connection",
            "migrations",
            "health_check",
        ):
            if not any(result.key == key for result in results):
                results.append(
                    CheckResult(key, False, f"unexpected: {type(exc).__name__}: {exc}")
                )
    return results


def collect_checks(repo_root: Path) -> list[CheckResult]:
    results: list[CheckResult] = [
        _check_package_import(),
        _check_subprocess("ruff", repo_root, ["-m", "ruff", "check", "."]),
        _check_subprocess("mypy", repo_root, ["-m", "mypy", "src"]),
        _check_subprocess("pytest", repo_root, ["-m", "pytest", "-q"]),
        _check_subprocess(
            "architecture_boundaries",
            repo_root,
            ["-m", "pytest", "tests/architecture", "-q"],
        ),
        _check_via_validate_resources("translations", repo_root),
        _check_via_validate_resources("regional_language_resources", repo_root),
        _check_subprocess(
            "unit_of_work",
            repo_root,
            ["-m", "pytest", "tests/unit/database", "-q"],
        ),
        _check_subprocess(
            "job_manager",
            repo_root,
            ["-m", "pytest", "tests/unit/jobs", "-q"],
        ),
        _check_subprocess(
            "bootstrap",
            repo_root,
            ["-m", "pytest", "tests/test_foundation.py", "-q"],
        ),
        _check_subprocess(
            "no_secrets_detected",
            repo_root,
            [str(repo_root / "scripts" / "check_no_secrets.py")],
        ),
    ]
    results.extend(_check_registries_with_bootstrap(repo_root))
    return results


def render_report(checks: list[CheckResult]) -> dict[str, Any]:
    by_key = {result.key: result.passed for result in checks}
    missing = [key for key in CHECK_KEYS if key not in by_key]
    for key in missing:
        by_key[key] = False
    all_passed = all(by_key.values())
    return {
        "phase": "implementation-phase-0",
        "status": "PASS" if all_passed else "FAIL",
        "checks": {key: by_key[key] for key in CHECK_KEYS},
        "ui_framework": "NOT_SELECTED",
        "campaign_engine_implemented": False,
        "website_ingestion_implemented": False,
        "notes": [
            {
                "key": result.key,
                "passed": result.passed,
                "detail": result.detail,
            }
            for result in checks
            if not result.passed
        ],
    }


def write_report(report: dict[str, Any], artifacts_dir: Path) -> Path:
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    out = artifacts_dir / "phase0_foundation_gate.json"
    out.write_text(
        json.dumps(report, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    args = parser.parse_args(argv)

    repo_root = args.repo_root.resolve()
    try:
        checks = collect_checks(repo_root)
    except Exception:  # noqa: BLE001
        # If collection itself explodes, surface the traceback and emit a
        # FAIL report so the artifact is never silent. The CI / human
        # owner can still see the exact failure.
        traceback.print_exc()
        checks = [
            CheckResult(key, False, "collect_checks raised")
            for key in CHECK_KEYS
        ]

    report = render_report(checks)
    out_path = write_report(report, repo_root / "artifacts")

    print(f"wrote {out_path}")
    summary = {"status": report["status"]}
    summary.update(report["checks"])
    print(json.dumps(summary, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
