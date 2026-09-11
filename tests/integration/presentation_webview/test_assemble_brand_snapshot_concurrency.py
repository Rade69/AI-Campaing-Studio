"""Concurrency regression for assembling immutable brand snapshots."""

from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from ai_campaign_studio.domain.common.ids import BrandId
from ai_campaign_studio.infrastructure.database.connection import create_connection
from ai_campaign_studio.infrastructure.database.repositories import (
    SqliteBrandRepository,
)
from tests.integration.presentation_webview.test_ingestion_review_flow import (
    _BRAND_ID,
    _CAND_1,
    _isolated_bridge,
    _seed_review_data,
)


def test_concurrent_assemble_assigns_distinct_sequential_versions(
    tmp_path: Path,
) -> None:
    """Two pywebview workers must not persist the same brand version."""
    bridge = _isolated_bridge(tmp_path)
    _seed_review_data(bridge)
    approved = bridge.approve_fact_candidate({"candidate_id": str(_CAND_1)})
    assert approved["ok"] is True, approved

    rendezvous = threading.Barrier(2)
    original_get_latest = SqliteBrandRepository.get_latest_snapshot

    def synchronized_get_latest(
        repository: SqliteBrandRepository, brand_id: BrandId
    ) -> object:
        latest = original_get_latest(repository, brand_id)
        try:
            # Without serialization both workers rendezvous after reading the
            # same version. With the fix, the first worker times out while it
            # owns the per-brand lock; the second then observes its write.
            rendezvous.wait(timeout=1)
        except threading.BrokenBarrierError:
            pass
        return latest

    with patch.object(
        SqliteBrandRepository,
        "get_latest_snapshot",
        synchronized_get_latest,
    ):
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(
                executor.map(
                    lambda _: bridge.assemble_brand_snapshot(
                        {"brand_id": str(_BRAND_ID)}
                    ),
                    range(2),
                )
            )

    assert all(result["ok"] is True for result in results), results
    assert sorted(result["version"] for result in results) == [1, 2]

    connection = create_connection(bridge._bootstrap.paths.database_path)
    try:
        rows = connection.execute(
            "SELECT version FROM brand_snapshots WHERE brand_id = ?"
            " ORDER BY version",
            (_BRAND_ID,),
        ).fetchall()
        assert [row["version"] for row in rows] == [1, 2]
    finally:
        connection.close()
