"""Guard: the shared presentation folder must stay framework-neutral.

Scans ``src/ai_campaign_studio/presentation/*.py`` and fails on any import of
a GUI/web framework, a provider SDK, or the infrastructure layer — the exact
boundary that ``PySide6`` vs ``pywebview`` will later implement against.
"""

import ast
from pathlib import Path

_PRESENTATION_DIR = (
    Path(__file__).resolve().parents[3]
    / "src"
    / "ai_campaign_studio"
    / "presentation"
)

_PRESENTATION_PACKAGE = "ai_campaign_studio.presentation"

_FORBIDDEN_TOP_LEVEL = {
    "PySide6",
    "PySide2",
    "PyQt6",
    "PyQt5",
    "pywebview",
    "flask",
    "fastapi",
    "requests",
    "openai",
    "anthropic",
    "google",
    "deepseek",
}
_FORBIDDEN_PREFIXES = ("ai_campaign_studio.infrastructure",)


def _imported_modules(path: Path) -> set[str]:
    """Return full module names imported by a file.

    ``from X import Y`` counts as importing ``X.Y`` (so
    ``from ai_campaign_studio import infrastructure`` is caught), and relative
    imports are resolved against the presentation package.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if node.level == 0:
                    module = node.module or ""
                    full = module if alias.name == "*" else f"{module}.{alias.name}"
                    modules.add(full)
                else:
                    base = _PRESENTATION_PACKAGE.split(".")
                    up = node.level - 1
                    if up >= len(base):
                        continue
                    target = base[: len(base) - up]
                    if node.module:
                        target = [*target, *node.module.split(".")]
                    if alias.name != "*":
                        target = [*target, alias.name]
                    modules.add(".".join(target))
    return modules


def _forbidden_names(path: Path) -> list[str]:
    """Return the forbidden module names imported by ``path``."""
    offenders: list[str] = []
    for name in _imported_modules(path):
        if name.split(".")[0] in _FORBIDDEN_TOP_LEVEL:
            offenders.append(name)
        for prefix in _FORBIDDEN_PREFIXES:
            if name == prefix or name.startswith(prefix + "."):
                offenders.append(name)
    return offenders


def test_presentation_has_no_gui_web_or_infra_imports() -> None:
    offenders: list[str] = []
    for py_file in sorted(_PRESENTATION_DIR.glob("*.py")):
        for name in _forbidden_names(py_file):
            offenders.append(f"{py_file.name}: {name}")
    assert offenders == []


def test_guard_detects_forbidden_imports(tmp_path: Path) -> None:
    """Prove the guard is not a no-op for both boundary kinds."""
    evil = tmp_path / "evil.py"
    evil.write_text(
        "import PySide6\n"
        "from ai_campaign_studio import infrastructure\n"
        "from ai_campaign_studio.infrastructure.database import create_connection\n",
        encoding="utf-8",
    )
    offenders = _forbidden_names(evil)
    assert "PySide6" in offenders
    assert "ai_campaign_studio.infrastructure" in offenders
    assert (
        "ai_campaign_studio.infrastructure.database.create_connection" in offenders
    )


def test_guard_allows_clean_presentation_imports(tmp_path: Path) -> None:
    clean = tmp_path / "clean.py"
    clean.write_text(
        "from ai_campaign_studio.localization.enums import AppLocale\n"
        "from dataclasses import dataclass\n",
        encoding="utf-8",
    )
    assert _forbidden_names(clean) == []
