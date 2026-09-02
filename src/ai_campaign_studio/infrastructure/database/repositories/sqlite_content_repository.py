"""SQLite adapter for ``ContentRepositoryPort`` (A5, dio 2).

Owns saving ``ContentPiece`` rows (plus the ``ContentClaim`` join rows) and
reading them back. The claim graph is stored in ``content_claims`` (join table
with a ``position`` column so the tuple order survives round-trip); the
``facts_allowed``/``revision_ids`` lists are JSON text columns. Enums are
stored as ``.value`` and reconstructed as real domain enums.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime

from ai_campaign_studio.domain.common.ids import (
    BrandSnapshotId,
    CampaignId,
    CampaignItemId,
    FactId,
    PostId,
    RevisionId,
)
from ai_campaign_studio.domain.content.claims import ContentClaim
from ai_campaign_studio.domain.content.entities import CampaignTarget, ContentPiece
from ai_campaign_studio.domain.content.enums import (
    ClaimStatus,
    ClaimType,
    ContentPayloadType,
    ContentStatus,
)


class SqliteContentRepository:
    """SQLite implementation of ``ContentRepositoryPort``."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def save_content_piece(self, content_piece: ContentPiece) -> None:
        self._connection.execute(
            "INSERT INTO content_pieces (id, campaign_item_id, target_channel,"
            " target_platform_code, target_format_code, payload_type, status,"
            " brand_snapshot_id, facts_allowed_json, revision_ids_json,"
            " created_at, updated_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
            " ON CONFLICT(id) DO UPDATE SET"
            " campaign_item_id=excluded.campaign_item_id,"
            " target_channel=excluded.target_channel,"
            " target_platform_code=excluded.target_platform_code,"
            " target_format_code=excluded.target_format_code,"
            " payload_type=excluded.payload_type, status=excluded.status,"
            " brand_snapshot_id=excluded.brand_snapshot_id,"
            " facts_allowed_json=excluded.facts_allowed_json,"
            " revision_ids_json=excluded.revision_ids_json,"
            " created_at=excluded.created_at, updated_at=excluded.updated_at",
            (
                content_piece.id,
                content_piece.campaign_item_id,
                content_piece.target.channel,
                content_piece.target.platform_code,
                content_piece.target.format_code,
                content_piece.payload_type.value,
                content_piece.status.value,
                content_piece.brand_snapshot_id,
                json.dumps(list(content_piece.facts_allowed)),
                json.dumps(list(content_piece.revision_ids)),
                content_piece.created_at.isoformat(),
                content_piece.updated_at.isoformat(),
            ),
        )
        # Replace the claim rows so a re-save is idempotent.
        self._connection.execute(
            "DELETE FROM content_claims WHERE piece_id = ?", (content_piece.id,)
        )
        for position, claim in enumerate(content_piece.claims):
            self._connection.execute(
                "INSERT INTO content_claims (id, piece_id, position, text, type,"
                " fact_ids_json, status, reason_codes_json)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    claim.id,
                    content_piece.id,
                    position,
                    claim.text,
                    claim.type.value,
                    json.dumps(list(claim.fact_ids)),
                    claim.status.value,
                    json.dumps(list(claim.reason_codes)),
                ),
            )

    def get_content_piece(self, content_piece_id: PostId) -> ContentPiece | None:
        row = self._connection.execute(
            "SELECT * FROM content_pieces WHERE id = ?", (content_piece_id,)
        ).fetchone()
        if row is None:
            return None
        return _content_piece_from_row(self._connection, row)

    def list_campaign_content(
        self, campaign_id: CampaignId
    ) -> tuple[ContentPiece, ...]:
        rows = self._connection.execute(
            "SELECT content_pieces.* FROM content_pieces"
            " JOIN campaign_items"
            "   ON campaign_items.id = content_pieces.campaign_item_id"
            " JOIN campaign_plans ON campaign_plans.id = campaign_items.plan_id"
            " WHERE campaign_plans.campaign_id = ?"
            " ORDER BY content_pieces.id",
            (campaign_id,),
        ).fetchall()
        return tuple(_content_piece_from_row(self._connection, row) for row in rows)


def _content_piece_from_row(
    connection: sqlite3.Connection, row: sqlite3.Row
) -> ContentPiece:
    claim_rows = connection.execute(
        "SELECT * FROM content_claims WHERE piece_id = ? ORDER BY position",
        (row["id"],),
    ).fetchall()
    return ContentPiece(
        id=PostId(row["id"]),
        campaign_item_id=CampaignItemId(row["campaign_item_id"]),
        target=CampaignTarget(
            channel=row["target_channel"],
            platform_code=row["target_platform_code"],
            format_code=row["target_format_code"],
        ),
        payload_type=ContentPayloadType(row["payload_type"]),
        status=ContentStatus(row["status"]),
        brand_snapshot_id=BrandSnapshotId(row["brand_snapshot_id"]),
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
        facts_allowed=tuple(FactId(x) for x in json.loads(row["facts_allowed_json"])),
        revision_ids=tuple(
            RevisionId(x) for x in json.loads(row["revision_ids_json"])
        ),
        claims=tuple(_claim_from_row(claim_row) for claim_row in claim_rows),
    )


def _claim_from_row(row: sqlite3.Row) -> ContentClaim:
    return ContentClaim(
        id=row["id"],
        text=row["text"],
        type=ClaimType(row["type"]),
        status=ClaimStatus(row["status"]),
        fact_ids=tuple(FactId(x) for x in json.loads(row["fact_ids_json"])),
        reason_codes=tuple(json.loads(row["reason_codes_json"])),
    )
