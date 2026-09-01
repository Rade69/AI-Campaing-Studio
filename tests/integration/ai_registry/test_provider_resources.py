"""Integration checks for bundled AI provider resources."""

import re
from pathlib import Path

from ai_campaign_studio.ai_registry.registry import AIProviderRegistry

REPO_ROOT = Path(__file__).resolve().parents[3]
PROVIDERS_DIR = REPO_ROOT / "resources" / "ai_providers"

_SECRET_LIKE_PATTERNS = (
    r"sk-[A-Za-z0-9_-]{8,}",  # OpenAI / Anthropic key
    r"AIza[0-9A-Za-z_-]{10,}",  # Google API key
    r"Bearer\s+[A-Za-z0-9._-]{8,}",  # bearer token
    r"-----BEGIN [A-Z ]+PRIVATE KEY-----",  # PEM private key
)


def test_bundled_providers_load() -> None:
    registry = AIProviderRegistry.from_bundled_resources()
    providers = registry.list_providers()
    codes = [p.provider_code for p in providers]

    assert len(providers) == 6
    assert len(codes) == len(set(codes)) == 6
    for provider in providers:
        assert provider.base_url_mode in ("FIXED", "USER_CONFIGURABLE", "NONE")


def test_no_secret_like_content_in_provider_yaml() -> None:
    for path in PROVIDERS_DIR.glob("*.yaml"):
        text = path.read_text(encoding="utf-8")
        for pattern in _SECRET_LIKE_PATTERNS:
            assert not re.search(pattern, text), f"{path.name} matched {pattern!r}"
