"""Foundation smoke tests: package import and skeleton behavior."""

import ai_campaign_studio
from ai_campaign_studio.bootstrap import Bootstrap, create_bootstrap
from ai_campaign_studio.main import main


def test_package_importable() -> None:
    assert ai_campaign_studio.__name__ == "ai_campaign_studio"


def test_bootstrap_is_minimal() -> None:
    bootstrap = create_bootstrap()
    assert isinstance(bootstrap, Bootstrap)


def test_main_returns_zero() -> None:
    assert main() == 0
