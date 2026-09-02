"""SQLite adapter for ``CampaignRepositoryPort`` (A5, dio 2).

Owns saving ``Campaign``/``CampaignBrief``/``CampaignPlan``/``CampaignItem``
rows and reading them back. The nested value-object lists (``targets``,
``special_instructions``, ``facts_needed``) are stored as JSON text columns;
enums are stored as their ``.value`` string and reconstructed as real domain
enums. ``save_*`` are idempotent (upsert by primary key).
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict
from datetime import datetime

from ai_campaign_studio.domain.campaign.entities import (
    Campaign,
    CampaignBrief,
    CampaignItem,
    CampaignPlan,
)
from ai_campaign_studio.domain.campaign.enums import (
    CampaignItemStatus,
    CampaignPlanStatus,
    CampaignStatus,
)
from ai_campaign_studio.domain.campaign.roles import CampaignRole
from ai_campaign_studio.domain.common.ids import (
    BrandId,
    BrandSnapshotId,
    CampaignId,
    CampaignItemId,
    CampaignPlanId,
)
from ai_campaign_studio.domain.content.entities import CampaignTarget


class SqliteCampaignRepository:
    """SQLite implementation of ``CampaignRepositoryPort``."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def save_brief(self, brief: CampaignBrief) -> None:
        self._connection.execute(
            "INSERT INTO campaign_briefs (id, offer, goal, audience_text,"
            " targets_json, content_piece_count, content_language_context,"
            " special_instructions_json, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"
            " ON CONFLICT(id) DO UPDATE SET offer=excluded.offer,"
            " goal=excluded.goal, audience_text=excluded.audience_text,"
            " targets_json=excluded.targets_json,"
            " content_piece_count=excluded.content_piece_count,"
            " content_language_context=excluded.content_language_context,"
            " special_instructions_json=excluded.special_instructions_json,"
            " created_at=excluded.created_at",
            (
                brief.id,
                brief.offer,
                brief.goal,
                brief.audience_text,
                json.dumps([asdict(target) for target in brief.targets]),
                brief.content_piece_count,
                brief.content_language_context,
                json.dumps(list(brief.special_instructions)),
                brief.created_at.isoformat(),
            ),
        )

    def save_campaign(self, campaign: Campaign) -> None:
        self._connection.execute(
            "INSERT INTO campaigns (id, brand_id, brand_snapshot_id, brief_id,"
            " status, created_at) VALUES (?, ?, ?, ?, ?, ?)"
            " ON CONFLICT(id) DO UPDATE SET brand_id=excluded.brand_id,"
            " brand_snapshot_id=excluded.brand_snapshot_id,"
            " brief_id=excluded.brief_id, status=excluded.status,"
            " created_at=excluded.created_at",
            (
                campaign.id,
                campaign.brand_id,
                campaign.brand_snapshot_id,
                campaign.brief_id,
                campaign.status.value,
                campaign.created_at.isoformat(),
            ),
        )

    def save_plan(self, plan: CampaignPlan) -> None:
        self._connection.execute(
            "INSERT INTO campaign_plans (id, campaign_id, version, status,"
            " created_at) VALUES (?, ?, ?, ?, ?)"
            " ON CONFLICT(id) DO UPDATE SET campaign_id=excluded.campaign_id,"
            " version=excluded.version, status=excluded.status,"
            " created_at=excluded.created_at",
            (
                plan.id,
                plan.campaign_id,
                plan.version,
                plan.status.value,
                plan.created_at.isoformat(),
            ),
        )
        # Replace the item rows so a re-save of the same plan is idempotent.
        self._connection.execute(
            "DELETE FROM campaign_items WHERE plan_id = ?", (plan.id,)
        )
        for item in plan.items:
            self._connection.execute(
                "INSERT INTO campaign_items (id, plan_id, \"order\", role, topic,"
                " goal, target_audience_id, facts_needed_json, status)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    item.id,
                    plan.id,
                    item.order,
                    item.role.value,
                    item.topic,
                    item.goal,
                    item.target_audience_id,
                    json.dumps(list(item.facts_needed)),
                    item.status.value,
                ),
            )

    def get_brief(self, brief_id: str) -> CampaignBrief | None:
        row = self._connection.execute(
            "SELECT * FROM campaign_briefs WHERE id = ?", (brief_id,)
        ).fetchone()
        if row is None:
            return None
        return _brief_from_row(row)

    def get_campaign(self, campaign_id: CampaignId) -> Campaign | None:
        row = self._connection.execute(
            "SELECT * FROM campaigns WHERE id = ?", (campaign_id,)
        ).fetchone()
        if row is None:
            return None
        return _campaign_from_row(row)

    def get_plan(self, plan_id: CampaignPlanId) -> CampaignPlan | None:
        row = self._connection.execute(
            "SELECT * FROM campaign_plans WHERE id = ?", (plan_id,)
        ).fetchone()
        if row is None:
            return None
        item_rows = self._connection.execute(
            "SELECT * FROM campaign_items WHERE plan_id = ? ORDER BY \"order\"",
            (plan_id,),
        ).fetchall()
        return CampaignPlan(
            id=CampaignPlanId(row["id"]),
            campaign_id=CampaignId(row["campaign_id"]),
            version=row["version"],
            status=CampaignPlanStatus(row["status"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            items=tuple(_item_from_row(item_row) for item_row in item_rows),
        )


def _campaign_from_row(row: sqlite3.Row) -> Campaign:
    return Campaign(
        id=CampaignId(row["id"]),
        brand_id=BrandId(row["brand_id"]),
        brand_snapshot_id=BrandSnapshotId(row["brand_snapshot_id"]),
        brief_id=row["brief_id"],
        status=CampaignStatus(row["status"]),
        created_at=datetime.fromisoformat(row["created_at"]),
    )


def _brief_from_row(row: sqlite3.Row) -> CampaignBrief:
    return CampaignBrief(
        id=row["id"],
        offer=row["offer"],
        goal=row["goal"],
        audience_text=row["audience_text"],
        targets=tuple(
            CampaignTarget(**target) for target in json.loads(row["targets_json"])
        ),
        content_piece_count=row["content_piece_count"],
        content_language_context=row["content_language_context"],
        created_at=datetime.fromisoformat(row["created_at"]),
        special_instructions=tuple(json.loads(row["special_instructions_json"])),
    )


def _item_from_row(row: sqlite3.Row) -> CampaignItem:
    return CampaignItem(
        id=CampaignItemId(row["id"]),
        order=row["order"],
        role=CampaignRole(row["role"]),
        topic=row["topic"],
        goal=row["goal"],
        status=CampaignItemStatus(row["status"]),
        target_audience_id=row["target_audience_id"],
        facts_needed=tuple(json.loads(row["facts_needed_json"])),
    )
