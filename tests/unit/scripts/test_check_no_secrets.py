"""Unit tests for ``scripts/check_no_secrets.py``.

Test fixtures build key-shaped values at *runtime* via the
``_real_*`` helpers below so the source contains no key-shaped literal
in the tracked test scope (Codex review BF-1).

Round 1 extension (BF-3): the ``ai_campaign_studio_env`` pattern
matches the canonical ``AI_CAMPAIGN_STUDIO_<PROVIDER>_API_KEY``
convention and is exercised for every current provider plus a
hypothetical future one.

Round 1 extension (BF-2): ``Finding.render()`` no longer echoes the
raw value; per-test assertions check that the rendered output
contains the ``<redacted>`` marker instead.
"""

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


# --- runtime-constructed fixtures --------------------------------------
#
# These helpers concatenate short substrings at *runtime* so the source
# file has no single 16+ alphanumerics-after-prefix literal. The
# resulting strings are 32 alphanumerics after the prefix — the same
# shape the scanner is designed to catch — but the scanner never sees
# them as source text, only as values written into test fixtures in
# a temp directory or as values passed to ``_is_placeholder``.

_FILLER = "abcdefghijklmnop"  # 16 chars, no prefix on its own


def _real_openai_key() -> str:
    return "sk-" + _FILLER * 2  # 32 alphanumerics after "sk-"


def _real_bearer_token() -> str:
    return _FILLER * 2  # 32 alphanumerics


def _real_api_key_value() -> str:
    return _FILLER * 2  # 32 alphanumerics; scanner requires 8+


# --- is_placeholder -----------------------------------------------------


@pytest.mark.parametrize(
    "value",
    [
        "EXAMPLE",
        # Built at runtime so the source itself has no key-shaped literal.
        "sk-" + "EXAMPLEKEYEXAMPLEKEY",
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
        _real_openai_key(),
        _real_bearer_token(),
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
    key = _real_openai_key()
    p.write_text(f'OPENAI_API_KEY = "{key}"\n', encoding="utf-8")
    findings = list(cns._scan_file(tmp_path, "leak.py"))
    pattern_ids = {f.pattern_id for f in findings}
    assert "openai_sk_prefix" in pattern_ids
    assert "openai_key" in pattern_ids
    # BF-2: the rendered finding must NOT contain the raw key value.
    for f in findings:
        assert key not in f.render(), (
            f"finding leaked raw key in render output: {f.render()!r}"
        )


def test_scan_file_detects_bearer(tmp_path: Path) -> None:
    p = tmp_path / "h.py"
    bearer = _real_bearer_token()
    p.write_text(
        f'h = {{"Authorization": "Bearer {bearer}"}}\n',
        encoding="utf-8",
    )
    findings = list(cns._scan_file(tmp_path, "h.py"))
    assert any(f.pattern_id == "bearer_token" for f in findings)
    for f in findings:
        assert bearer not in f.render(), (
            f"finding leaked raw bearer in render output: {f.render()!r}"
        )


def test_scan_file_detects_api_key_assignment(tmp_path: Path) -> None:
    p = tmp_path / "cfg.py"
    value = _real_api_key_value()
    p.write_text(f'cfg = {{"api_key": "{value}"}}\n', encoding="utf-8")
    findings = list(cns._scan_file(tmp_path, "cfg.py"))
    assert any(f.pattern_id == "generic_api_key" for f in findings)
    for f in findings:
        assert value not in f.render(), (
            f"finding leaked raw api_key value in render output: "
            f"{f.render()!r}"
        )


def test_scan_file_ignores_placeholder(tmp_path: Path) -> None:
    p = tmp_path / "cfg.py"
    # "sk-EXAMPLEKEYEXAMPLEKEY" contains the placeholder substring
    # "example" so the scanner must skip it after the placeholder filter.
    p.write_text(
        'OPENAI_API_KEY = "sk-EXAMPLEKEYEXAMPLEKEY"\n', encoding="utf-8"
    )
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


def test_scan_file_detects_ai_campaign_studio_env_per_provider(tmp_path: Path) -> None:
    """The canonical env-var convention is
    ``AI_CAMPAIGN_STUDIO_<PROVIDER_CODE>_API_KEY=...`` for every
    provider. The scanner must catch this for every provider
    registered today *and* any future one (Codex review BF-3,
    round 1 extension)."""
    # Built at runtime so the source itself has no key-shaped literal
    # in the tracked test scope.
    def _studio_env_line(provider: str, with_quote: bool = False) -> str:
        value = "abcdefghijklmnop" * 2  # 32 alphanumerics
        if with_quote:
            return f'AI_CAMPAIGN_STUDIO_{provider}_API_KEY="{value}"'
        return f"AI_CAMPAIGN_STUDIO_{provider}_API_KEY={value}"

    # Every current provider in the registry, plus a hypothetical
    # future one. All must be caught by ``ai_campaign_studio_env``.
    providers = [
        "OPENAI",
        "ANTHROPIC",
        "GOOGLE",
        "DEEPSEEK",
        "OPENROUTER",
        "OPENAI_COMPATIBLE",
        # Future provider that does not exist yet — proves the
        # pattern is structural, not per-provider.
        "MISTRAL",
    ]
    for provider in providers:
        for with_quote in (False, True):
            p = tmp_path / "leak.py"
            p.write_text(
                _studio_env_line(provider, with_quote) + "\n",
                encoding="utf-8",
            )
            findings = list(cns._scan_file(tmp_path, "leak.py"))
            assert any(f.pattern_id == "ai_campaign_studio_env" for f in findings), (
                f"scanner missed {provider!r} via ai_campaign_studio_env "
                f"(quote={with_quote}); findings="
                f"{[f.pattern_id for f in findings]}"
            )
            # BF-2 still in force: rendered output must not echo the value.
            for f in findings:
                if f.pattern_id == "ai_campaign_studio_env":
                    assert "<redacted>" in f.render(), (
                        f"rendered finding did not redact value: {f.render()!r}"
                    )


# --- scan() / main() end-to-end ----------------------------------------


def test_scan_dedupes_repeat_matches(tmp_path: Path, monkeypatch) -> None:
    """Two patterns that match the same line are reported twice, but the
    same ``(path, line, pattern_id)`` triple appears at most once."""
    (tmp_path / "scripts").mkdir()
    # Stage a fake check_no_secrets.py outside the scan scope, then a
    # tracked file with a real key.
    leak = tmp_path / "src" / "leak.py"
    leak.parent.mkdir(parents=True, exist_ok=True)
    key = _real_openai_key()
    leak.write_text(f'k = "{key}"\n', encoding="utf-8")

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
    # BF-2: the scanner's stdout/stderr on the clean repo must not echo
    # any key-shaped value (there shouldn't be any in a clean repo,
    # but this guards against future regressions).
    leaked = _FILLER * 2
    combined = completed.stdout + completed.stderr
    assert leaked not in combined, (
        f"clean-repo scanner output leaked a key-shaped value: "
        f"{combined!r}"
    )
