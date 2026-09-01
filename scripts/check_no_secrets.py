"""Scan tracked files for accidental secret/key leakage.

Usage:

    python scripts/check_no_secrets.py [--repo-root .]

Exit code 0 = no confirmed secret in tracked files, exit code 1 with the
exact ``file:line`` location otherwise.

Scan scope (tracked files only — ``git ls-files``):

* ``src/ai_campaign_studio/``
* ``tests/``
* ``scripts/``  (excluding this scanner's own source file)
* resource files: ``*.json``, ``*.yaml``, ``*.yml``, ``*.sql``
* root config: ``pyproject.toml``, ``config.example.toml``

Excluded (treated as plan/process documents, not runtime config):

* any ``*.md`` / ``*.pdf`` documentation
* the entire ``agent_reports/`` directory
* skill bundles, ``.claude/``, ``.agents/``, ``.agent/``

This script's own source file is excluded by name so that the pattern
*definitions* below never self-match. Patterns are intentionally
restrictive: they require the literal value to look like a real key (long
alphanumeric), not a regex fragment. The placeholder filter additionally
skips obvious non-credentials (``EXAMPLE``, ``REDACTED``, ``xxx``, …).
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

# A key-shaped value: at least 16 alphanumerics (and the allowed token
# characters ``._-`` for the Bearer form). 16 is the OpenAI project key
# length and comfortably excludes 4-6 char test tokens.
_KEY_VALUE = r"[A-Za-z0-9._\-]{16,}"
_VALUE_OR_QUOTED = r'(?:\"[^\"\s]{8,}\"|\"[A-Za-z0-9._\-]{8,}\"|[A-Za-z0-9._\-]{8,})'

# Placeholder substrings (lowercased). A value is a placeholder if the
# lowercased form contains any of these — this catches
# ``sk-EXAMPLEKEYEXAMPLEKEY``, ``your-key-here-stuff``, ``<YOUR_KEY>``, …
# without us having to enumerate every possible framing.
_PLACEHOLDER_SUBSTRINGS = (
    "example",
    "exampledummy",
    "redacted",
    "xxx",
    "your-key",
    "your_key",
    "placeholder",
    "changeme",
    "<key>",
    "<your",
    "todo",
    "fixme",
    "dummy",
    "fakekey",
    "fake-key",
    "not-a-real",
    "notareal",
)

# Each pattern: (id, regex). The regex must match the whole literal value
# (i.e. the value after ``=`` or after ``Bearer ``), not just a substring
# of the pattern-definition text. We enforce "the value is key-shaped" via
# a dedicated inner group plus a placeholder filter at match time.
#
# Two complementary styles are covered per secret name:
#   * Python assignment: ``OPENAI_API_KEY = "..."``
#   * JSON / dict:       ``"openai_api_key": "..."``
#
# All separators are wrapped in a small "punctuation+whitespace" class so
# both ``= "..."`` and ``": "..."`` are caught. Each pattern captures the
# value as group 1 for placeholder filtering.
PATTERNS: tuple[tuple[str, str], ...] = (
    (
        "openai_sk_prefix",
        r"\bsk-[A-Za-z0-9]{16,}\b",
    ),
    (
        "openai_key",
        r"\bOPENAI_API_KEY\b[^A-Za-z0-9_]{0,8}[\"']?(" + _KEY_VALUE + r")[\"']?",
    ),
    (
        "anthropic_key",
        r"\bANTHROPIC_API_KEY\b[^A-Za-z0-9_]{0,8}[\"']?(" + _KEY_VALUE + r")[\"']?",
    ),
    (
        "bearer_token",
        r"\bAuthorization\b[^\n]{0,40}?Bearer\s+(" + _KEY_VALUE + r")\b",
    ),
    (
        "generic_api_key",
        r"\bapi[_-]?key\b[^A-Za-z0-9_]{0,8}[\"\']([^\"\'\s]{8,})[\"\']",
    ),
)


@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    pattern_id: str
    snippet: str

    def render(self) -> str:
        return f"{self.path}:{self.line}: [{self.pattern_id}] {self.snippet}"


# Directories that are never scanned, even if they live under a tracked
# path (defensive: ``git ls-files`` should not include them, but explicit
# exclusion makes the contract auditable).
_EXCLUDED_TOP_DIRS = frozenset(
    {
        ".agent",
        ".agents",
        ".claude",
        ".github",
        ".gitnexus",
        "agent_reports",
        "docs",
    }
)

# Extensions that are scanned wherever they live.
_SCANNED_EXTENSIONS = frozenset(
    {".py", ".json", ".yaml", ".yml", ".sql", ".toml"}
)

# Root-level config files scanned explicitly (no extension glob above
# matches them — ``pyproject.toml`` does, ``config.example.toml`` does).
_ROOT_CONFIG_FILES = (
    "pyproject.toml",
    "config.example.toml",
)

# The scanner file is excluded by exact path so its pattern definitions
# (which intentionally mention strings like ``"sk-"`` and ``"api_key="``)
# can never self-match.
SELF_PATH = Path(__file__).resolve()


def _is_placeholder(value: str) -> bool:
    lowered = value.strip().strip("\"'<>").lower()
    if not lowered:
        return True
    return any(token in lowered for token in _PLACEHOLDER_SUBSTRINGS)


def _is_scannable(rel_path: str) -> bool:
    """Return True if a tracked relative path is in scan scope."""
    if not rel_path:
        return False
    parts = rel_path.replace("\\", "/").split("/")
    if not parts:
        return False
    if parts[0] in _EXCLUDED_TOP_DIRS:
        return False
    if rel_path.endswith(".md") or rel_path.endswith(".pdf"):
        return False
    if rel_path == SELF_PATH.name or rel_path.endswith("/" + SELF_PATH.name):
        return False
    # Explicit root config files
    if rel_path in _ROOT_CONFIG_FILES:
        return True
    # Tracked nested copies of the scanner (defensive)
    if parts[-1] == SELF_PATH.name:
        return False
    # Extension-based allow list for the rest
    suffix = Path(parts[-1]).suffix
    return suffix in _SCANNED_EXTENSIONS


def _list_tracked_files(repo_root: Path) -> list[str]:
    """Return git-tracked relative paths (forward-slash form)."""
    result = subprocess.run(
        ["git", "ls-files", "-z", "--"],
        cwd=repo_root,
        check=True,
        capture_output=True,
    )
    raw = result.stdout.decode("utf-8", errors="replace")
    return [entry for entry in raw.split("\x00") if entry]


def _scan_file(repo_root: Path, rel_path: str) -> Iterable[Finding]:
    absolute = repo_root / rel_path
    try:
        text = absolute.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        yield Finding(
            path=rel_path,
            line=0,
            pattern_id="read_error",
            snippet=str(exc),
        )
        return

    for line_number, line in enumerate(text.splitlines(), start=1):
        for pattern_id, pattern in PATTERNS:
            match = re.search(pattern, line)
            if match is None:
                continue
            # The captured group (if any) is the candidate value.
            candidate = match.group(1) if match.lastindex else match.group(0)
            if _is_placeholder(candidate):
                continue
            snippet = line.strip()
            if len(snippet) > 160:
                snippet = snippet[:157] + "..."
            yield Finding(
                path=rel_path,
                line=line_number,
                pattern_id=pattern_id,
                snippet=snippet,
            )


def scan(repo_root: Path) -> list[Finding]:
    """Scan all in-scope tracked files; return a deduplicated list of findings.

    Deduplication keeps one finding per ``(path, line, pattern_id)`` so a
    single real secret that happens to match multiple patterns (e.g. a long
    ``sk-...`` value also matching ``OPENAI_API_KEY=...``) is reported once
    per pattern, not many times. Findings are sorted for stable output.
    """
    raw: list[Finding] = []
    for rel_path in _list_tracked_files(repo_root):
        if not _is_scannable(rel_path):
            continue
        raw.extend(_scan_file(repo_root, rel_path))
    seen: set[tuple[str, int, str]] = set()
    deduped: list[Finding] = []
    for finding in raw:
        key = (finding.path, finding.line, finding.pattern_id)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(finding)
    deduped.sort(key=lambda finding: (finding.path, finding.line))
    return deduped


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    args = parser.parse_args(argv)

    repo_root = args.repo_root.resolve()
    findings = scan(repo_root)
    if findings:
        print(
            f"FAIL: {len(findings)} potential secret(s) in tracked files:",
            file=sys.stderr,
        )
        for finding in findings:
            print(finding.render(), file=sys.stderr)
        return 1

    print("NO CONFIRMED SECRET IN TRACKED FILES")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
