"""Architecture boundary checks: forbid dependency-direction violations.

These tests scan the real source tree with AST (no dependency-analysis
library) and assert the Clean/Hexagonal layer rules from the P0 plan:

    domain/       must not import infrastructure, presentation, jobs, GUI,
                  provider SDKs, HTTP/web frameworks or browsers.
    application/  must not import presentation, infrastructure, GUI,
                  provider SDKs or browsers.
    ports/        must not import infrastructure adapters.
    presentation/ must not import provider SDKs or the sqlite repository
                  implementation (infrastructure).
"""

import ast
from collections.abc import Iterable
from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parents[2] / "src" / "ai_campaign_studio"

_INFRA_MODULE = "ai_campaign_studio.infrastructure"
_PRESENTATION_MODULE = "ai_campaign_studio.presentation"
_JOBS_MODULE = "ai_campaign_studio.jobs"

_GUI_MODULES = {"PySide6", "PyQt6", "pywebview"}
_PROVIDER_SDK_MODULES = {"openai", "anthropic", "google", "deepseek"}
_BROWSER_MODULES = {"playwright"}
_WEB_MODULES = {"requests", "Flask"}

_FORBIDDEN_PREFIXES: dict[str, tuple[str, ...]] = {
    "domain": (_INFRA_MODULE, _PRESENTATION_MODULE, _JOBS_MODULE),
    "application": (_PRESENTATION_MODULE, _INFRA_MODULE),
    "ports": (_INFRA_MODULE,),
    "presentation": (_INFRA_MODULE,),
}

_FORBIDDEN_TOP_LEVEL: dict[str, set[str]] = {
    "domain": _GUI_MODULES | _PROVIDER_SDK_MODULES | _BROWSER_MODULES | _WEB_MODULES,
    "application": _GUI_MODULES | _PROVIDER_SDK_MODULES | _BROWSER_MODULES,
    "ports": set(),
    "presentation": _PROVIDER_SDK_MODULES,
}


def _layer_for(relative_path: Path) -> str | None:
    parts = relative_path.parts
    if not parts:
        return None
    top = parts[0]
    if top in _FORBIDDEN_PREFIXES:
        return top
    return None


def _iter_imports(path: Path) -> Iterable[tuple[str, str]]:
    """Yield ``(full_module_name, top_level_name)`` for every import.

    For ``from x.y import z`` the imported module is ``x.y.z`` (not just
    ``x.y``), so ``from ai_campaign_studio import infrastructure`` is still
    caught as an infrastructure import.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name, alias.name.split(".")[0]
        elif isinstance(node, ast.ImportFrom):
            if node.level > 0:
                continue
            module = node.module or ""
            for alias in node.names:
                if alias.name == "*":
                    full = module
                else:
                    full = f"{module}.{alias.name}" if module else alias.name
                yield full, full.split(".")[0]


def _is_forbidden(layer: str, module: str, top: str) -> bool:
    for prefix in _FORBIDDEN_PREFIXES[layer]:
        if module == prefix or module.startswith(prefix + "."):
            return True
    return top in _FORBIDDEN_TOP_LEVEL[layer]


def find_violations(root: Path) -> list[str]:
    """Return human-readable descriptions of every boundary violation."""
    violations: list[str] = []
    for py_file in sorted(root.rglob("*.py")):
        relative = py_file.relative_to(root)
        layer = _layer_for(relative)
        if layer is None:
            continue
        for module, top in _iter_imports(py_file):
            if _is_forbidden(layer, module, top):
                violations.append(
                    f"{relative.as_posix()}: forbidden {layer}/ import {module!r}"
                )
    return violations


def test_real_tree_has_no_boundary_violations() -> None:
    assert find_violations(SRC_ROOT) == []


def test_checker_flags_forbidden_imports_in_every_layer(tmp_path: Path) -> None:
    for layer in ("domain", "application", "ports", "presentation"):
        (tmp_path / layer).mkdir()
    (tmp_path / "domain" / "evil.py").write_text("import PySide6\n", encoding="utf-8")
    (tmp_path / "application" / "evil.py").write_text(
        "from ai_campaign_studio import infrastructure\n", encoding="utf-8"
    )
    (tmp_path / "ports" / "evil.py").write_text(
        "import ai_campaign_studio.infrastructure.database\n", encoding="utf-8"
    )
    (tmp_path / "presentation" / "evil.py").write_text(
        "import openai\n", encoding="utf-8"
    )

    violations = find_violations(tmp_path)

    assert len(violations) == 4
    assert any("domain/evil.py" in v and "PySide6" in v for v in violations)
    assert any(
        "application/evil.py" in v and "infrastructure" in v for v in violations
    )
    assert any("ports/evil.py" in v and "infrastructure" in v for v in violations)
    assert any("presentation/evil.py" in v and "openai" in v for v in violations)
