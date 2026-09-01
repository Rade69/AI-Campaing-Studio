"""Foundation smoke tests: package import and skeleton behavior."""

from pathlib import Path

import ai_campaign_studio
from ai_campaign_studio.bootstrap import Bootstrap, create_bootstrap
from ai_campaign_studio.config.paths import AppPaths
from ai_campaign_studio.main import main


def test_package_importable() -> None:
    assert ai_campaign_studio.__name__ == "ai_campaign_studio"


def test_package_has_version() -> None:
    assert ai_campaign_studio.__version__ == "0.1.0"


def test_bootstrap_wires_foundation(tmp_path: Path) -> None:
    paths = AppPaths(data_dir_override=tmp_path / "data")
    bootstrap = create_bootstrap(paths=paths)
    try:
        assert isinstance(bootstrap, Bootstrap)
        assert bootstrap.settings is not None
        assert bootstrap.paths is paths
        assert bootstrap.logger is not None
        assert bootstrap.translator is not None
        assert bootstrap.platform_registry is not None
        assert bootstrap.provider_registry is not None
        assert bootstrap.secret_store is not None
        assert bootstrap.database_connection is not None
        assert bootstrap.job_manager is not None
    finally:
        bootstrap.job_manager.shutdown(wait=False)
        bootstrap.database_connection.close()


def test_main_returns_zero(monkeypatch) -> None:
    monkeypatch.setattr(
        "ai_campaign_studio.main.run_health_check_cli", lambda: 0
    )
    assert main(["--health-check"]) == 0
