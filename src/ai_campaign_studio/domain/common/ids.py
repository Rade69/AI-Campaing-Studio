"""Identifier primitives (P0 + A3 extension).

Owns ``new_id()`` (UUID4) and the typed ID aliases used across the domain
(``BrandId``, ``FactId``, ``CampaignId``, ...). The aliases are runtime-
identical to ``str``; the ``NewType`` wrappers exist for the type checker only
so different ID kinds cannot be silently mixed.
"""

import uuid
from typing import NewType

ProjectId = NewType("ProjectId", str)
BrandId = NewType("BrandId", str)
BrandSnapshotId = NewType("BrandSnapshotId", str)
FactId = NewType("FactId", str)
CampaignId = NewType("CampaignId", str)
CampaignPlanId = NewType("CampaignPlanId", str)
CampaignItemId = NewType("CampaignItemId", str)
PostId = NewType("PostId", str)
RevisionId = NewType("RevisionId", str)
VisualSystemId = NewType("VisualSystemId", str)


def new_id() -> str:
    """Return a new UUID4 string identifier."""
    return str(uuid.uuid4())
