"""Guard: the shared presentation folder must stay framework-neutral.

Scans ``src/ai_campaign_studio/presentation/*.py`` and fails on any import of
a GUI/web framework, a provider SDK, or the infrastructure layer — the exact
boundary that ``PySide6`` vs ``pywebview`` will later implement against.
Covers static imports and literal dynamic imports (``importlib.import_module``,
``__import__``).
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

_DYNAMIC_IMPORT_CALLABLES = {
    "importlib.import_module",
    "importlib.__import__",
    "builtins.__import__",
    "__import__",
}


class _ImportScanner(ast.NodeVisitor):
    """Collect static and literal-dynamic module names with alias resolution."""

    def __init__(self) -> None:
        self.bindings: dict[str, str] = {}
        self.modules: set[str] = set()

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            local = alias.asname or alias.name.split(".")[0]
            self.bindings[local] = alias.name
            self.modules.add(alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        for alias in node.names:
            if node.level == 0:
                module = node.module or ""
                full = module if alias.name == "*" else f"{module}.{alias.name}"
                self.modules.add(full)
                self.bindings[alias.asname or alias.name] = full
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
                full = ".".join(target)
                self.modules.add(full)
                self.bindings[alias.asname or alias.name] = full
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        # getattr(importlib, "import_module")("<literal>")
        if isinstance(node.func, ast.Call):
            inner = node.func
            if (
                isinstance(inner.func, ast.Name)
                and inner.func.id == "getattr"
                and len(inner.args) == 2
            ):
                obj = self._resolve(inner.args[0])
                attr_arg = inner.args[1]
                if (
                    obj == "importlib"
                    and isinstance(attr_arg, ast.Constant)
                    and isinstance(attr_arg.value, str)
                    and attr_arg.value == "import_module"
                ):
                    literal = self._literal_arg(node)
                    if literal is not None:
                        self.modules.add(literal)
        target = self._resolve(node.func)
        if target in _DYNAMIC_IMPORT_CALLABLES:
            literal = self._literal_arg(node)
            if literal is not None:
                self.modules.add(literal)
        self.generic_visit(node)

    @staticmethod
    def _literal_arg(call: ast.Call) -> str | None:
        first = call.args[0] if call.args else None
        if isinstance(first, ast.Constant) and isinstance(first.value, str):
            return first.value
        return None

    def _resolve(self, expr: ast.expr) -> str | None:
        if isinstance(expr, ast.Name):
            return self.bindings.get(expr.id, expr.id)
        if isinstance(expr, ast.Attribute):
            base = self._resolve(expr.value)
            if base is None:
                return None
            return f"{base}.{expr.attr}"
        return None


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    scanner = _ImportScanner()
    scanner.visit(tree)
    return scanner.modules


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
    """Prove the guard is not a no-op for both boundary kinds (static)."""
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


def test_guard_detects_literal_dynamic_imports(tmp_path: Path) -> None:
    """Prove the guard catches importlib.import_module / __import__ bypasses."""
    evil = tmp_path / "evil.py"
    evil.write_text(
        "import importlib\n"
        "importlib.import_module('PySide6')\n"
        "__import__('PySide6')\n"
        "importlib.import_module('ai_campaign_studio.infrastructure.database')\n",
        encoding="utf-8",
    )
    offenders = _forbidden_names(evil)
    assert "PySide6" in offenders
    assert "ai_campaign_studio.infrastructure.database" in offenders


def test_guard_allows_clean_presentation_imports(tmp_path: Path) -> None:
    clean = tmp_path / "clean.py"
    clean.write_text(
        "from ai_campaign_studio.localization.enums import AppLocale\n"
        "from dataclasses import dataclass\n",
        encoding="utf-8",
    )
    assert _forbidden_names(clean) == []
