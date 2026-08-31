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
    paths = AppPaths(
        data_dir_override=tmp_path / "data",
        resource_dir_override=tmp_path / "resources",
    )
    bootstrap = create_bootstrap(paths=paths)
    assert isinstance(bootstrap, Bootstrap)
    assert bootstrap.settings is not None
    assert bootstrap.paths is paths
    assert bootstrap.logger is not None


def test_main_returns_zero(monkeypatch) -> None:
    monkeypatch.setattr(
        "ai_campaign_studio.main.create_bootstrap", lambda: object()
    )
    assert main(["--health-check"]) == 0
