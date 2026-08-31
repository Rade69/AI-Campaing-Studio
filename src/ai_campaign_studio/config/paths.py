"""Filesystem path resolution.

Uses ``platformdirs`` for the platform-appropriate data root and derives the
remaining application directories beneath it. No user-specific path is ever
hardcoded, and importing/instantiating this module has no filesystem side
effects — directory creation is explicit via :meth:`AppPaths.ensure_directories`.
"""

from pathlib import Path

import platformdirs


class AppPaths:
    """Resolved application paths."""

    def __init__(
        self,
        app_name: str = "AI Campaign Studio",
        database_filename: str = "ai_campaign_studio.db",
        data_dir_override: Path | str | None = None,
        resource_dir_override: Path | str | None = None,
    ) -> None:
        data_root = (
            Path(data_dir_override)
            if data_dir_override is not None
            else Path(platformdirs.user_data_dir(app_name))
        )
        self.data_dir = data_root
        self.database_dir = data_root / "database"
        self.database_path = self.database_dir / database_filename
        self.cache_dir = data_root / "cache"
        self.logs_dir = data_root / "logs"
        self.projects_dir = data_root / "projects"
        self.artifacts_dir = data_root / "artifacts"
        self.resources_dir = (
            Path(resource_dir_override)
            if resource_dir_override is not None
            else self._default_resources_dir()
        )

    def ensure_directories(self) -> None:
        """Create all application directories (explicit, no import side effect)."""
        for directory in (
            self.database_dir,
            self.cache_dir,
            self.logs_dir,
            self.projects_dir,
            self.artifacts_dir,
        ):
            directory.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _default_resources_dir() -> Path:
        """Return the bundled resources directory (repo ``resources/``).

        ``paths.py`` lives at ``src/ai_campaign_studio/config/paths.py``; the
        repository root is three parents up, hence ``parents[3]``.
        """
        return Path(__file__).resolve().parents[3] / "resources"
