"""Composition-root skeleton for the AI Campaign Studio application."""


class Bootstrap:
    """Minimal application composition root.

    Intentionally empty in the Phase 0 foundation. Later phases add settings,
    paths, logging, registries, and adapters without turning this class into a
    service locator.
    """


def create_bootstrap() -> Bootstrap:
    """Build the application composition root."""
    return Bootstrap()
