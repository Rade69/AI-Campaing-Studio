"""pywebview presentation shell for AI Campaign Studio.

Owns the standalone entry point (no dependency on ``main.py`` /
``bootstrap.py`` from Phase 0). Adds a navigable pywebview window with
sidebar, topbar, breadcrumb slot, and a fixture-driven Početna screen.

The pywebview-specific security policy from ``docs/PYWEBVIEW_SECURITY.md``
is enforced at the entry point: ``gui='edgechromium'`` and
``debug=False`` are always passed explicitly, and a missing WebView2
Runtime raises a loud, human-readable error instead of silently
falling back to ``mshtml``.
"""

__all__ = ["__version__"]

__version__ = "0.1.0"
