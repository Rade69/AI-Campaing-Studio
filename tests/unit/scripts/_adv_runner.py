"""Adversarial test runner — produces literal FAIL -> PASS evidence.

Each step is independent; files modified are restored at the end. The
runner is intentionally a plain script (no pytest framework), so it can
be invoked manually to record evidence. The runner is in
``tests/unit/scripts/`` so pytest collection picks it up; it is
collected as a single test by the ``name_test_*`` wrappers below.
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
VENV = REPO / ".venv" / "Scripts" / "python.exe"
PY = str(VENV) if VENV.is_file() else sys.executable


def run(label, cmd, expected_exit, env=None):
    """Run subprocess, return (passed, stdout, stderr, exitcode)."""
    print(f"=== {label} ===")
    completed = subprocess.run(
        cmd, cwd=REPO, capture_output=True, text=True, env=env
    )
    print("STDOUT:", completed.stdout.rstrip())
    print("STDERR:", completed.stderr.rstrip())
    print(f"EXIT={completed.returncode}  expected={expected_exit}")
    ok = completed.returncode == expected_exit
    print("RESULT:", "OK" if ok else "FAIL")
    print()
    return ok, completed


def main():
    results = []

    # --- ADV 1: resource validator catches broken platform ----
    print("############ ADV 1: resource validator ############")
    backup = REPO / "resources" / "platforms" / "instagram.yaml.bak"
    shutil.copy(
        REPO / "resources" / "platforms" / "instagram.yaml", backup
    )
    try:
        # Step 1: baseline
        ok, _ = run(
            "ADV 1.a baseline (should pass)",
            [PY, "scripts/validate_resources.py"], 0,
        )
        results.append(ok)

        # Step 2: add a duplicate-code platform
        dup = (REPO / "resources" / "platforms" / "instagram.yaml").read_text(
            encoding="utf-8"
        )
        dup_path = REPO / "resources" / "platforms" / "_adv_dup.yaml"
        dup_path.write_text(dup, encoding="utf-8")
        ok, _ = run(
            "ADV 1.b with duplicate platform code (should fail)",
            [PY, "scripts/validate_resources.py"], 1,
        )
        results.append(ok)
        dup_path.unlink()

        # Step 3: re-validate -> pass
        ok, _ = run(
            "ADV 1.c duplicate removed (should pass again)",
            [PY, "scripts/validate_resources.py"], 0,
        )
        results.append(ok)
    finally:
        backup.unlink(missing_ok=True)

    # --- ADV 2: secret scanner catches real key, no self-match -
    print("############ ADV 2: secret scanner ############")
    ok, _ = run(
        "ADV 2.a baseline (should pass)",
        [PY, "scripts/check_no_secrets.py"], 0,
    )
    results.append(ok)

    # Inject a real key into a tracked file inside the scan scope.
    # The scanner only sees git-tracked files, so the probe must be
    # `git add`-ed before the run, and `git rm`-ed (or just unlink the
    # file) afterward.
    probe = REPO / "src" / "ai_campaign_studio" / "_adv_probe.py"
    # Built at runtime so this script's own source has no key-shaped
    # literal in the tracked test scope (Codex review BF-1).
    _filler = "abcdefghijklmnop"
    probe_key = "sk-" + _filler * 2
    probe.write_text(
        '"""Adversarial probe."""\n'
        f'OPENAI_API_KEY = "{probe_key}"\n',
        encoding="utf-8",
    )
    subprocess.run(
        ["git", "add", str(probe.relative_to(REPO))],
        cwd=REPO, check=True, capture_output=True,
    )
    try:
        ok, completed = run(
            "ADV 2.b with real key in tracked file (should fail)",
            [PY, "scripts/check_no_secrets.py"], 1,
        )
        results.append(ok)
        # Print the exact finding line(s) for the evidence report.
        print("ADV 2.b finding(s) on stderr:")
        for line in completed.stderr.splitlines():
            if ":" in line and "scripts/" not in line and "/" in line:
                print("  ", line)
    finally:
        subprocess.run(
            ["git", "rm", "--cached", str(probe.relative_to(REPO))],
            cwd=REPO, capture_output=True,
        )
        probe.unlink(missing_ok=True)

    ok, _ = run(
        "ADV 2.c probe removed (should pass again)",
        [PY, "scripts/check_no_secrets.py"], 0,
    )
    results.append(ok)

    # Self-match: scanner source contains pattern-defining strings
    # (e.g. r"sk-[A-Za-z0-9]{16,}"). The scanner must NOT report itself.
    sys.path.insert(0, str(REPO / "scripts"))
    import check_no_secrets as cns
    findings = list(cns._scan_file(REPO, "scripts/check_no_secrets.py"))
    print(f"ADV 2.d self-scan findings count: {len(findings)}")
    if findings:
        for f in findings:
            print("  UNEXPECTED:", f.render())
    results.append(len(findings) == 0)

    # --- ADV 3: gate report fails when a check fails --------
    print("############ ADV 3: gate report honesty ############")
    gp = REPO / "scripts" / "generate_phase0_gate_report.py"
    backup_gp = gp.read_text(encoding="utf-8")
    try:
        # Force-fail the "ruff" check so the report should be FAIL.
        corrupted = backup_gp.replace(
            '_check_subprocess("ruff", repo_root, ["-m", "ruff", "check", "."]),',
            '_check_subprocess("ruff", repo_root, ["-c", "import sys; sys.exit(7)"]),',
        )
        assert corrupted != backup_gp, "patch did not apply"
        gp.write_text(corrupted, encoding="utf-8")
        completed = subprocess.run(
            [PY, "scripts/generate_phase0_gate_report.py"],
            cwd=REPO, capture_output=True, text=True,
        )
        print("ADV 3.a forced FAIL run stdout:", completed.stdout[-500:].rstrip())
        print("ADV 3.a forced FAIL run exit:", completed.returncode)
        payload = json.loads(
            (REPO / "artifacts" / "phase0_foundation_gate.json").read_text(
                encoding="utf-8"
            )
        )
        print("ADV 3.a report status:", payload["status"])
        print("ADV 3.a report ruff check:", payload["checks"]["ruff"])
        ruff_notes = [n for n in payload["notes"] if n["key"] == "ruff"]
        print("ADV 3.a report notes for ruff:", ruff_notes)
        ok_adv3a = (
            payload["status"] == "FAIL"
            and payload["checks"]["ruff"] is False
            and completed.returncode != 0
        )
        print("ADV 3.a RESULT:", "OK" if ok_adv3a else "FAIL")
        print()
        results.append(ok_adv3a)
    finally:
        gp.write_text(backup_gp, encoding="utf-8")

    ok, _ = run(
        "ADV 3.b revert (should pass)",
        [PY, "scripts/generate_phase0_gate_report.py"], 0,
    )
    results.append(ok)

    print("############ Summary ############")
    print(f"Total checks: {len(results)}, OK: {sum(results)}")
    print("ALL OK" if all(results) else "SOME FAILED")
    return 0 if all(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
