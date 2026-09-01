"""Unit tests for ``scripts/check_no_secrets.py``."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

_SCRIPTS = Path(__file__).resolve().parents[3] / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import check_no_secrets as cns  # type: ignore[import-not-found]  # noqa: E402  isort: skip


# --- is_placeholder -----------------------------------------------------


@pytest.mark.parametrize(
    "value",
    [
        "EXAMPLE",
        "sk-EXAMPLEKEYEXAMPLEKEY",
        "your-key-here-1234",
        "REDACTED-secret-by-vault",
        "placeholder",
        "changeme",
        "<your_key>",
        "",
        "   ",
    ],
)
def test_is_placeholder_true(value: str) -> None:
    assert cns._is_placeholder(value) is True


@pytest.mark.parametrize(
    "value",
    [
        "sk-abcdefghijklmnopqrstuvwxyz123456",
        "abcdefghijklmnopqrst",
    ],
)
def test_is_placeholder_false(value: str) -> None:
    assert cns._is_placeholder(value) is False


@pytest.mark.parametrize(
    "value",
    [
        # AWS documentation *example* key. Contains "EXAMPLE", so it IS a
        # placeholder by our heuristic — keeping it in its own parametrize
        # so the test documents the intentional behaviour.
        "AKIAIOSFODNN7EXAMPLE",
    ],
)
def test_is_placeholder_treats_documented_example_keys_as_placeholder(
    value: str,
) -> None:
    assert cns._is_placeholder(value) is True


# --- is_scannable -------------------------------------------------------


def test_is_scannable_excludes_md() -> None:
    assert cns._is_scannable("README.md") is False
    assert cns._is_scannable("docs/something.md") is False
    assert cns._is_scannable("plan.pdf") is False


def test_is_scannable_excludes_top_dirs() -> None:
    assert cns._is_scannable("agent_reports/some.md") is False
    assert cns._is_scannable(".claude/foo.py") is False
    assert cns._is_scannable("docs/spec.md") is False


def test_is_scannable_includes_root_configs() -> None:
    assert cns._is_scannable("pyproject.toml") is True
    assert cns._is_scannable("config.example.toml") is True


def test_is_scannable_excludes_self() -> None:
    rel = cns.SELF_PATH.relative_to(cns.SELF_PATH.parents[2]).as_posix()
    # In normal repo layout the scanner is at "scripts/check_no_secrets.py".
    assert cns._is_scannable(rel) is False


def test_is_scannable_includes_source_and_tests() -> None:
    assert cns._is_scannable("src/ai_campaign_studio/foo.py") is True
    assert cns._is_scannable("tests/unit/test_x.py") is True
    assert cns._is_scannable("scripts/other.py") is True
    assert cns._is_scannable("resources/platforms/instagram.yaml") is True
    assert cns._is_scannable("resources/i18n/en.json") is True


# --- _scan_file ---------------------------------------------------------


def test_scan_file_detects_openai_sk_prefix(tmp_path: Path) -> None:
    p = tmp_path / "leak.py"
    key = "sk-abcdefghijklmnopqrstuvwxyz123456"
    p.write_text(f'OPENAI_API_KEY = "{key}"\n', encoding="utf-8")
    findings = list(cns._scan_file(tmp_path, "leak.py"))
    pattern_ids = {f.pattern_id for f in findings}
    assert "openai_sk_prefix" in pattern_ids
    assert "openai_key" in pattern_ids


def test_scan_file_detects_bearer(tmp_path: Path) -> None:
    p = tmp_path / "h.py"
    p.write_text(
        'h = {"Authorization": "Bearer abcdefghijklmnopqrstuvwxyz123456"}\n',
        encoding="utf-8",
    )
    findings = list(cns._scan_file(tmp_path, "h.py"))
    assert any(f.pattern_id == "bearer_token" for f in findings)


def test_scan_file_detects_api_key_assignment(tmp_path: Path) -> None:
    p = tmp_path / "cfg.py"
    p.write_text('cfg = {"api_key": "abcdefghijklmnop"}\n', encoding="utf-8")
    findings = list(cns._scan_file(tmp_path, "cfg.py"))
    assert any(f.pattern_id == "generic_api_key" for f in findings)


def test_scan_file_ignores_placeholder(tmp_path: Path) -> None:
    p = tmp_path / "cfg.py"
    p.write_text('OPENAI_API_KEY = "sk-EXAMPLEKEYEXAMPLEKEY"\n', encoding="utf-8")
    findings = list(cns._scan_file(tmp_path, "cfg.py"))
    assert findings == []


def test_scan_file_ignores_short_tokens(tmp_path: Path) -> None:
    p = tmp_path / "cfg.py"
    p.write_text('OPENAI_API_KEY = "sk-abc"\n', encoding="utf-8")
    findings = list(cns._scan_file(tmp_path, "cfg.py"))
    assert findings == []


def test_scan_file_does_not_self_match() -> None:
    """Scan the scanner's own source file via the function; expect 0
    findings because the pattern definitions in the file are not
    themselves key-shaped values (they contain regex metachars, not
    16+ alphanumerics after the prefix)."""
    repo_root = Path(__file__).resolve().parents[3]
    findings = list(cns._scan_file(repo_root, "scripts/check_no_secrets.py"))
    assert findings == [], f"unexpected self-match: {[f.render() for f in findings]}"


# --- scan() / main() end-to-end ----------------------------------------


def test_scan_dedupes_repeat_matches(tmp_path: Path, monkeypatch) -> None:
    """Two patterns that match the same line are reported twice, but the
    same ``(path, line, pattern_id)`` triple appears at most once."""
    (tmp_path / "scripts").mkdir()
    # Stage a fake check_no_secrets.py outside the scan scope, then a
    # tracked file with a real key.
    leak = tmp_path / "src" / "leak.py"
    leak.parent.mkdir(parents=True, exist_ok=True)
    leak.write_text('k = "sk-abcdefghijklmnopqrstuvwxyz123456"\n', encoding="utf-8")

    # Stage a git repo so _list_tracked_files returns our file.
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=tmp_path,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"], cwd=tmp_path, check=True
    )
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "init"], cwd=tmp_path, check=True
    )

    findings = cns.scan(tmp_path)
    # Each (path, line, pattern_id) appears at most once.
    keys = [(f.path, f.line, f.pattern_id) for f in findings]
    assert len(keys) == len(set(keys))


def test_main_against_clean_repo_passes() -> None:
    """Run the scanner against the actual repo (clean state)."""
    if os.environ.get("ACS_GATE_REPORT_RUNNING") == "1":
        pytest.skip(
            "scanner e2e skipped while inside the gate report's own "
            "pytest invocation (ACS_GATE_REPORT_RUNNING=1)"
        )
    repo_root = Path(__file__).resolve().parents[3]
    # Use subprocess to ensure the same code path as production.
    completed = subprocess.run(
        [sys.executable, str(repo_root / "scripts" / "check_no_secrets.py")],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "NO CONFIRMED SECRET" in completed.stdout
