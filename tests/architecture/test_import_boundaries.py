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


_DYNAMIC_IMPORT_CALLABLES = {
    "importlib.import_module",
    "importlib.__import__",
    "builtins.__import__",
    "__import__",
}


def _collect_import_aliases(tree: ast.Module) -> dict[str, str]:
    """Map local names to their canonical import targets.

    ``import importlib as loader`` → ``{"loader": "importlib"}``;
    ``from importlib import import_module as load`` →
    ``{"load": "importlib.import_module"}``.
    """
    aliases: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                local = alias.asname or alias.name.split(".")[0]
                aliases[local] = alias.name
        elif isinstance(node, ast.ImportFrom):
            if node.level != 0 or node.module is None:
                continue
            for alias in node.names:
                local = alias.asname or alias.name
                aliases[local] = f"{node.module}.{alias.name}"
    return aliases


def _resolve_expr(expr: ast.expr, aliases: dict[str, str]) -> str | None:
    """Resolve a name/attribute expression through the alias map."""
    if isinstance(expr, ast.Name):
        return aliases.get(expr.id, expr.id)
    if isinstance(expr, ast.Attribute):
        base = _resolve_expr(expr.value, aliases)
        if base is None:
            return None
        return f"{base}.{expr.attr}"
    return None


def _literal_arg(call: ast.Call) -> str | None:
    first = call.args[0] if call.args else None
    if isinstance(first, ast.Constant) and isinstance(first.value, str):
        return first.value
    return None


def _dynamic_import_target(call: ast.Call, aliases: dict[str, str]) -> str | None:
    """Return the literal module name of a dynamic import call, if any."""
    # getattr(importlib, "import_module")("<target>")
    if isinstance(call.func, ast.Call):
        inner = call.func
        if (
            isinstance(inner.func, ast.Name)
            and inner.func.id == "getattr"
            and len(inner.args) == 2
        ):
            obj = _resolve_expr(inner.args[0], aliases)
            attr_arg = inner.args[1]
            if (
                obj == "importlib"
                and isinstance(attr_arg, ast.Constant)
                and isinstance(attr_arg.value, str)
                and attr_arg.value == "import_module"
            ):
                return _literal_arg(call)
        return None

    callable_name = _resolve_expr(call.func, aliases)
    if callable_name not in _DYNAMIC_IMPORT_CALLABLES:
        return None
    return _literal_arg(call)


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
    aliases = _collect_import_aliases(tree)
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
            target = _dynamic_import_target(node, aliases)
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


def test_checker_flags_importlib_dunder_import(tmp_path: Path) -> None:
    (tmp_path / "domain").mkdir()
    (tmp_path / "domain" / "evil.py").write_text(
        "import importlib\n"
        "importlib.__import__('ai_campaign_studio.infrastructure')\n",
        encoding="utf-8",
    )
    violations = find_violations(tmp_path)
    assert any(
        "domain/evil.py" in v and "ai_campaign_studio.infrastructure" in v
        for v in violations
    )


def test_checker_flags_getattr_import_module(tmp_path: Path) -> None:
    (tmp_path / "domain").mkdir()
    (tmp_path / "domain" / "evil.py").write_text(
        "import importlib\n"
        "getattr(importlib, 'import_module')('ai_campaign_studio.infrastructure')\n",
        encoding="utf-8",
    )
    violations = find_violations(tmp_path)
    assert any(
        "domain/evil.py" in v and "ai_campaign_studio.infrastructure" in v
        for v in violations
    )


def test_checker_flags_import_alias_module(tmp_path: Path) -> None:
    (tmp_path / "domain").mkdir()
    (tmp_path / "domain" / "evil.py").write_text(
        "import importlib as loader\n"
        "loader.import_module('ai_campaign_studio.infrastructure')\n",
        encoding="utf-8",
    )
    violations = find_violations(tmp_path)
    assert any(
        "domain/evil.py" in v and "ai_campaign_studio.infrastructure" in v
        for v in violations
    )


def test_checker_flags_from_import_alias(tmp_path: Path) -> None:
    (tmp_path / "domain").mkdir()
    (tmp_path / "domain" / "evil.py").write_text(
        "from importlib import import_module as load\n"
        "load('ai_campaign_studio.infrastructure')\n",
        encoding="utf-8",
    )
    violations = find_violations(tmp_path)
    assert any(
        "domain/evil.py" in v and "ai_campaign_studio.infrastructure" in v
        for v in violations
    )


def test_checker_flags_builtins_dunder_import(tmp_path: Path) -> None:
    (tmp_path / "domain").mkdir()
    (tmp_path / "domain" / "evil.py").write_text(
        "import builtins\nbuiltins.__import__('PySide6')\n", encoding="utf-8"
    )
    violations = find_violations(tmp_path)
    assert any("domain/evil.py" in v and "PySide6" in v for v in violations)


def test_checker_allows_safe_relative_imports(tmp_path: Path) -> None:
    (tmp_path / "domain").mkdir()
    (tmp_path / "domain" / "ok.py").write_text(
        "from . import helper\nfrom .. import helper2\n", encoding="utf-8"
    )
    assert find_violations(tmp_path) == []


def test_checker_does_not_crash_on_nonliteral_dynamic_import(
    tmp_path: Path,
) -> None:
    (tmp_path / "domain").mkdir()
    (tmp_path / "domain" / "ok.py").write_text(
        "import importlib\n"
        "importlib.import_module('ai_campaign_studio' + '.infrastructure')\n",
        encoding="utf-8",
    )
    assert find_violations(tmp_path) == []
