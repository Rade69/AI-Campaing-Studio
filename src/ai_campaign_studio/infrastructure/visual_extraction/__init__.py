"""Visual identity extraction infrastructure (S2-G5).

Owns the cheap-signal visual-identity extraction layer of Website/Brand
ingestion: ``AssetExtractor`` (favicon/OpenGraph/Twitter assets),
``VisualIdentityExtractor`` (HTML → existing ``VisualIdentity`` VO) and
``VisualIdentityAdapter`` (implements the existing S2-G1
``VisualIdentityExtractorPort``). No new port, no new VO, no migration, no
image analysis — stdlib ``html.parser``/``re``/``urllib.parse`` only.
"""

from ai_campaign_studio.infrastructure.visual_extraction.adapter import (
    VisualIdentityAdapter,
)
from ai_campaign_studio.infrastructure.visual_extraction.asset_extractor import (
    AssetExtractor,
)
from ai_campaign_studio.infrastructure.visual_extraction.visual_identity_extractor import (  # noqa: E501
    VisualIdentityExtractor,
)

__all__ = [
    "AssetExtractor",
    "VisualIdentityAdapter",
    "VisualIdentityExtractor",
]
