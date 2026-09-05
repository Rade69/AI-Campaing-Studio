"""SQLite adapter for ``VisualRepositoryPort`` (A5, dio 2).

Owns saving ``CampaignVisualSystem`` rows and reading them back. The ``style``
list is a JSON text column; enum-typed attributes are stored as ``.value`` and
reconstructed as real domain enums.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime

from ai_campaign_studio.domain.common.ids import (
    CampaignId,
    LayoutSpecId,
    PostId,
    VisualSystemId,
)
from ai_campaign_studio.domain.common.timestamps import utc_now
from ai_campaign_studio.domain.visual.entities import CampaignVisualSystem
from ai_campaign_studio.domain.visual.enums import (
    Alignment,
    CtaStyle,
    HeadlinePosition,
    HeadlineScale,
    ImagePosition,
    LayoutPrimitive,
    LogoPosition,
    Overlay,
)
from ai_campaign_studio.domain.visual.layout import LayoutSpec


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

    def save_layout_spec(self, layout_spec: LayoutSpec) -> None:
        if layout_spec.id is None:
            raise ValueError("layout_spec.id must be set before saving")
        if layout_spec.content_piece_id is None:
            raise ValueError(
                "layout_spec.content_piece_id must be set before saving"
            )
        if layout_spec.validation_status is None:
            raise ValueError(
                "layout_spec.validation_status must be set before saving"
            )

        payload = {
            "primitive": layout_spec.primitive.value,
            "image_position": layout_spec.image_position.value,
            "headline_position": layout_spec.headline_position.value,
            "headline_scale": layout_spec.headline_scale.value,
            "overlay": layout_spec.overlay.value,
            "logo_position": layout_spec.logo_position.value,
            "cta_style": layout_spec.cta_style.value,
            "alignment": layout_spec.alignment.value,
        }
        self._connection.execute(
            "INSERT INTO layout_specs (id, content_piece_id, format,"
            " payload_json, validation_status, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?)"
            " ON CONFLICT(id) DO UPDATE SET"
            " content_piece_id=excluded.content_piece_id,"
            " format=excluded.format,"
            " payload_json=excluded.payload_json,"
            " validation_status=excluded.validation_status",
            # ``created_at`` is deliberately NOT in the UPDATE set: it records
            # when the row was FIRST created, so a re-save of the same id must
            # not overwrite it (append-only/audit-trail principle).
            (
                layout_spec.id,
                layout_spec.content_piece_id,
                layout_spec.format,
                json.dumps(payload),
                layout_spec.validation_status,
                utc_now().isoformat(),
            ),
        )

    def get_layout_spec(self, layout_spec_id: LayoutSpecId) -> LayoutSpec | None:
        row = self._connection.execute(
            "SELECT * FROM layout_specs WHERE id = ?",
            (layout_spec_id,),
        ).fetchone()
        if row is None:
            return None
        payload = json.loads(row["payload_json"])
        return LayoutSpec(
            primitive=LayoutPrimitive(payload["primitive"]),
            image_position=ImagePosition(payload["image_position"]),
            headline_position=HeadlinePosition(payload["headline_position"]),
            headline_scale=HeadlineScale(payload["headline_scale"]),
            overlay=Overlay(payload["overlay"]),
            logo_position=LogoPosition(payload["logo_position"]),
            cta_style=CtaStyle(payload["cta_style"]),
            alignment=Alignment(payload["alignment"]),
            format=row["format"],
            id=LayoutSpecId(row["id"]),
            content_piece_id=PostId(row["content_piece_id"]),
            validation_status=row["validation_status"],
        )
