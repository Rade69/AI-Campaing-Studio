"""SQLite adapter for ``BrandRepositoryPort`` (A5).

Owns saving ``Brand`` and ``BrandSnapshot`` rows and reading them back. The
value-object graph (voice/audiences/services/visual_identity/restrictions) is
stored as JSON text columns — this is infrastructure serialization; the
domain dataclasses remain the source of truth. ``save_*`` are idempotent
(upsert by primary key).
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict
from datetime import datetime

from ai_campaign_studio.domain.brand.entities import Brand, BrandSnapshot
from ai_campaign_studio.domain.brand.value_objects import (
    Audience,
    BrandVoice,
    Restriction,
    ServiceDefinition,
    VisualIdentity,
)
from ai_campaign_studio.domain.common.ids import BrandId, BrandSnapshotId, FactId


class SqliteBrandRepository:
    """SQLite implementation of ``BrandRepositoryPort``."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def save_brand(self, brand: Brand) -> None:
        self._connection.execute(
            "INSERT INTO brands (id, name, created_at) VALUES (?, ?, ?)"
            " ON CONFLICT(id) DO UPDATE SET name=excluded.name,"
            " created_at=excluded.created_at",
            (brand.id, brand.name, brand.created_at.isoformat()),
        )

    def save_snapshot(self, snapshot: BrandSnapshot) -> None:
        self._connection.execute(
            "INSERT INTO brand_snapshots (id, brand_id, version, language,"
            " locale, script, voice_json, audiences_json, services_json,"
            " visual_identity_json, restrictions_json, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
            " ON CONFLICT(id) DO UPDATE SET brand_id=excluded.brand_id,"
            " version=excluded.version, language=excluded.language,"
            " locale=excluded.locale, script=excluded.script,"
            " voice_json=excluded.voice_json,"
            " audiences_json=excluded.audiences_json,"
            " services_json=excluded.services_json,"
            " visual_identity_json=excluded.visual_identity_json,"
            " restrictions_json=excluded.restrictions_json,"
            " created_at=excluded.created_at",
            (
                snapshot.id,
                snapshot.brand_id,
                snapshot.version,
                snapshot.language,
                snapshot.locale,
                snapshot.script,
                json.dumps(asdict(snapshot.voice)),
                json.dumps([asdict(audience) for audience in snapshot.audiences]),
                json.dumps([asdict(service) for service in snapshot.services]),
                json.dumps(asdict(snapshot.visual_identity)),
                json.dumps(
                    [asdict(restriction) for restriction in snapshot.restrictions]
                ),
                snapshot.created_at.isoformat(),
            ),
        )
        # Replace the join rows so a re-save of the same snapshot is idempotent.
        self._connection.execute(
            "DELETE FROM brand_snapshot_facts WHERE snapshot_id = ?",
            (snapshot.id,),
        )
        for position, fact_id in enumerate(snapshot.approved_fact_ids):
            self._connection.execute(
                "INSERT INTO brand_snapshot_facts (snapshot_id, fact_id, position)"
                " VALUES (?, ?, ?)",
                (snapshot.id, fact_id, position),
            )

    def get_snapshot(self, snapshot_id: BrandSnapshotId) -> BrandSnapshot | None:
        row = self._connection.execute(
            "SELECT * FROM brand_snapshots WHERE id = ?",
            (snapshot_id,),
        ).fetchone()
        if row is None:
            return None
        fact_rows = self._connection.execute(
            "SELECT fact_id FROM brand_snapshot_facts WHERE snapshot_id = ?"
            " ORDER BY position",
            (snapshot_id,),
        ).fetchall()
        return BrandSnapshot(
            id=BrandSnapshotId(row["id"]),
            brand_id=BrandId(row["brand_id"]),
            version=row["version"],
            language=row["language"],
            locale=row["locale"],
            script=row["script"],
            voice=BrandVoice(**json.loads(row["voice_json"])),
            audiences=tuple(
                Audience(**audience) for audience in json.loads(row["audiences_json"])
            ),
            services=tuple(
                ServiceDefinition(**service)
                for service in json.loads(row["services_json"])
            ),
            visual_identity=VisualIdentity(**json.loads(row["visual_identity_json"])),
            restrictions=tuple(
                Restriction(**restriction)
                for restriction in json.loads(row["restrictions_json"])
            ),
            approved_fact_ids=tuple(FactId(row["fact_id"]) for row in fact_rows),
            created_at=datetime.fromisoformat(row["created_at"]),
        )
