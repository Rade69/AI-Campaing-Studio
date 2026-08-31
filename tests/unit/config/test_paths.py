"""Unit tests for application paths."""

from pathlib import Path

from ai_campaign_studio.config.paths import AppPaths


def test_all_paths_are_path_objects(tmp_path: Path) -> None:
    paths = AppPaths(
        data_dir_override=tmp_path / "data",
        resource_dir_override=tmp_path / "resources",
    )
    for attr in (
        "data_dir",
        "database_dir",
        "database_path",
        "cache_dir",
        "logs_dir",
        "projects_dir",
        "artifacts_dir",
        "resources_dir",
    ):
        assert isinstance(getattr(paths, attr), Path)


def test_overrides_are_respected(tmp_path: Path) -> None:
    data = tmp_path / "data"
    resources = tmp_path / "resources"
    paths = AppPaths(
        database_filename="custom.db",
        data_dir_override=data,
        resource_dir_override=resources,
    )
    assert paths.data_dir == data
    assert paths.database_dir == data / "database"
    assert paths.database_path == data / "database" / "custom.db"
    assert paths.resources_dir == resources


def test_instantiation_has_no_filesystem_side_effect(tmp_path: Path) -> None:
    data = tmp_path / "data"
    AppPaths(data_dir_override=data, resource_dir_override=tmp_path / "resources")
    assert not data.exists()


def test_ensure_directories_creates_application_dirs(tmp_path: Path) -> None:
    paths = AppPaths(
        data_dir_override=tmp_path / "data",
        resource_dir_override=tmp_path / "resources",
    )
    paths.ensure_directories()
    assert paths.database_dir.is_dir()
    assert paths.cache_dir.is_dir()
    assert paths.logs_dir.is_dir()
    assert paths.projects_dir.is_dir()
    assert paths.artifacts_dir.is_dir()
