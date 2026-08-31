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

The checker covers ``import``, absolute and relative ``from`` imports, and
literal dynamic imports (``importlib.import_module(...)``,
``import_module(...)``, ``__import__(...)``).
"""

import ast
from collections.abc import Iterable
from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parents[2] / "src" / "ai_campaign_studio"

_PACKAGE_PREFIX = "ai_campaign_studio"

_INFRA_MODULE = "ai_campaign_studio.infrastructure"
_PRESENTATION_MODULE = "ai_campaign_studio.presentation"
_JOBS_MODULE = "ai_campaign_studio.jobs"

_GUI_MODULES = {"PySide6", "PyQt6", "pywebview"}
_PROVIDER_SDK_MODULES = {"openai", "anthropic", "google", "deepseek"}
_BROWSER_MODULES = {"playwright"}
_WEB_MODULES = {"requests", "flask", "fastapi"}

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


def _package_for(relative_path: Path) -> str:
    """Return the full package path of a scanned file (filename excluded)."""
    return ".".join((_PACKAGE_PREFIX, *relative_path.parts[:-1]))


def _dynamic_import_target(call: ast.Call) -> str | None:
    """Return the literal module name of a dynamic import call, if any."""
    if (
        isinstance(call.func, ast.Attribute)
        and call.func.attr == "import_module"
        and isinstance(call.func.value, ast.Name)
        and call.func.value.id == "importlib"
    ):
        arg = call.args[0] if call.args else None
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            return arg.value
        return None

    if isinstance(call.func, ast.Name) and call.func.id == "import_module":
        arg = call.args[0] if call.args else None
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            return arg.value
        return None

    if isinstance(call.func, ast.Name) and call.func.id == "__import__":
        arg = call.args[0] if call.args else None
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            return arg.value
        return None

    return None


def _iter_imports(path: Path, package: str) -> Iterable[tuple[str, str]]:
    """Yield ``(full_module_name, top_level_name)`` for every import.

    Handles ``import``, absolute and relative ``from`` imports, and literal
    dynamic imports via ``importlib.import_module``/``import_module``/
    ``__import__``. Relative imports are resolved against *package* (the full
    ``ai_campaign_studio...`` package path of the scanned file).

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
            if node.level == 0:
                module = node.module or ""
                for alias in node.names:
                    if alias.name == "*":
                        full = module
                    else:
                        full = f"{module}.{alias.name}" if module else alias.name
                    yield full, full.split(".")[0]
            else:
                base_parts = package.split(".")
                up = node.level - 1
                if up >= len(base_parts):
                    continue
                target_parts = base_parts[: len(base_parts) - up]
                if node.module:
                    target_parts = [*target_parts, *node.module.split(".")]
                for alias in node.names:
                    if alias.name == "*":
                        full = ".".join(target_parts)
                    else:
                        full = ".".join([*target_parts, alias.name])
                    yield full, full.split(".")[0]
        elif isinstance(node, ast.Call):
            target = _dynamic_import_target(node)
            if target is not None:
                yield target, target.split(".")[0]


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
        package = _package_for(relative)
        for module, top in _iter_imports(py_file, package):
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


def test_checker_flags_relative_forbidden_import(tmp_path: Path) -> None:
    (tmp_path / "domain").mkdir()
    # `from .. import infrastructure` = ai_campaign_studio.infrastructure
    (tmp_path / "domain" / "evil.py").write_text(
        "from .. import infrastructure\n", encoding="utf-8"
    )
    violations = find_violations(tmp_path)
    assert any(
        "domain/evil.py" in v and "ai_campaign_studio.infrastructure" in v
        for v in violations
    )


def test_checker_flags_importlib_import_module(tmp_path: Path) -> None:
    (tmp_path / "domain").mkdir()
    (tmp_path / "domain" / "evil.py").write_text(
        "import importlib\n"
        "importlib.import_module('ai_campaign_studio.infrastructure')\n",
        encoding="utf-8",
    )
    violations = find_violations(tmp_path)
    assert any(
        "domain/evil.py" in v and "ai_campaign_studio.infrastructure" in v
        for v in violations
    )


def test_checker_flags_dunder_import(tmp_path: Path) -> None:
    (tmp_path / "domain").mkdir()
    (tmp_path / "domain" / "evil.py").write_text(
        "__import__('PySide6')\n", encoding="utf-8"
    )
    violations = find_violations(tmp_path)
    assert any("domain/evil.py" in v and "PySide6" in v for v in violations)


def test_checker_flags_lowercase_web_modules(tmp_path: Path) -> None:
    (tmp_path / "domain").mkdir()
    (tmp_path / "domain" / "evil.py").write_text(
        "import flask\nimport fastapi\n", encoding="utf-8"
    )
    violations = find_violations(tmp_path)
    assert any("flask" in v for v in violations)
    assert any("fastapi" in v for v in violations)
