"""SQLite adapter for ``VisualRepositoryPort`` (A5, dio 2).

Owns saving ``CampaignVisualSystem`` rows and reading them back. The ``style``
list is a JSON text column; enum-typed attributes are stored as ``.value`` and
reconstructed as real domain enums.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime

from ai_campaign_studio.domain.common.ids import CampaignId, VisualSystemId
from ai_campaign_studio.domain.visual.entities import CampaignVisualSystem
from ai_campaign_studio.domain.visual.enums import (
    Alignment,
    HeadlineScale,
    LayoutPrimitive,
)


class SqliteVisualRepository:
    """SQLite implementation of ``VisualRepositoryPort``."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def save_visual_system(self, system: CampaignVisualSystem) -> None:
        self._connection.execute(
            "INSERT INTO campaign_visual_systems (id, campaign_id,"
            " primary_layout_family, secondary_layout_family, headline_scale,"
            " image_treatment, logo_rule, cta_rule, alignment, style_json,"
            " created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
            " ON CONFLICT(id) DO UPDATE SET campaign_id=excluded.campaign_id,"
            " primary_layout_family=excluded.primary_layout_family,"
            " secondary_layout_family=excluded.secondary_layout_family,"
            " headline_scale=excluded.headline_scale,"
            " image_treatment=excluded.image_treatment,"
            " logo_rule=excluded.logo_rule, cta_rule=excluded.cta_rule,"
            " alignment=excluded.alignment, style_json=excluded.style_json,"
            " created_at=excluded.created_at",
            (
                system.id,
                system.campaign_id,
                system.primary_layout_family.value,
                (
                    system.secondary_layout_family.value
                    if system.secondary_layout_family is not None
                    else None
                ),
                system.headline_scale.value,
                system.image_treatment,
                system.logo_rule,
                system.cta_rule,
                system.alignment.value,
                json.dumps(list(system.style)),
                system.created_at.isoformat(),
            ),
        )

    def get_visual_system(
        self, visual_system_id: VisualSystemId
    ) -> CampaignVisualSystem | None:
        row = self._connection.execute(
            "SELECT * FROM campaign_visual_systems WHERE id = ?",
            (visual_system_id,),
        ).fetchone()
        if row is None:
            return None
        return CampaignVisualSystem(
            id=VisualSystemId(row["id"]),
            campaign_id=CampaignId(row["campaign_id"]),
            primary_layout_family=LayoutPrimitive(row["primary_layout_family"]),
            secondary_layout_family=(
                LayoutPrimitive(row["secondary_layout_family"])
                if row["secondary_layout_family"] is not None
                else None
            ),
            headline_scale=HeadlineScale(row["headline_scale"]),
            image_treatment=row["image_treatment"],
            logo_rule=row["logo_rule"],
            cta_rule=row["cta_rule"],
            alignment=Alignment(row["alignment"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            style=tuple(json.loads(row["style_json"])),
        )
