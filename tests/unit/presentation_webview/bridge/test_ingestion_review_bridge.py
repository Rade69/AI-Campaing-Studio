"""Unit tests for the S2-G7b ingestion-review bridge methods + ACS-S2-018
snapshot activate / list.

Boundary validation, error mapping, and the resource-lifecycle error
dispatch (which must return the exact per-method DTO shape, same rule as
every other bridge method — no other method's keys may leak through).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

from ai_campaign_studio.config.paths import AppPaths
from ai_campaign_studio.config.settings import AppSettings
from ai_campaign_studio.domain.brand.entities import Brand, BrandSnapshot
from ai_campaign_studio.domain.brand.value_objects import BrandVoice, VisualIdentity
from ai_campaign_studio.domain.common.ids import BrandId, BrandSnapshotId
from ai_campaign_studio.presentation_webview.bridge import CampaignBridgeApi


def _isolated_bridge(tmp_path: Path) -> CampaignBridgeApi:
    db_path = tmp_path / "test.db"
    paths = AppPaths(
        app_name="AI Campaign Studio (test)",
        database_filename=db_path.name,
        data_dir_override=tmp_path,
    )
    settings = AppSettings(environment="development")
    return CampaignBridgeApi(paths=paths, settings=settings)


def test_non_dict_payload_returns_validation_error_for_all_six_methods(
    tmp_path: Path,
) -> None:
    bridge = _isolated_bridge(tmp_path)
    calls = [
        bridge.get_ingestion_review,
        bridge.approve_fact_candidate,
        bridge.reject_fact_candidate,
        bridge.assemble_brand_snapshot,
        bridge.activate_brand_snapshot,
        bridge.list_brand_snapshots,
    ]
    for call in calls:
        result = call("not a dict")  # type: ignore[arg-type]
        assert result["ok"] is False
        assert result["error_code"] == "VALIDATION_ERROR"


def test_missing_candidate_id_is_validation_error(tmp_path: Path) -> None:
    bridge = _isolated_bridge(tmp_path)
    assert bridge.approve_fact_candidate({})["error_code"] == "VALIDATION_ERROR"
    assert bridge.reject_fact_candidate({})["error_code"] == "VALIDATION_ERROR"


def test_approve_unknown_candidate_is_validation_error(tmp_path: Path) -> None:
    bridge = _isolated_bridge(tmp_path)
    result = bridge.approve_fact_candidate({"candidate_id": "cand-missing"})
    assert result["ok"] is False
    assert result["error_code"] == "VALIDATION_ERROR"
    assert "ne postoji" in result["error_message"].lower()


def test_reject_unknown_candidate_is_validation_error(tmp_path: Path) -> None:
    bridge = _isolated_bridge(tmp_path)
    result = bridge.reject_fact_candidate({"candidate_id": "cand-missing"})
    assert result["ok"] is False
    assert result["error_code"] == "VALIDATION_ERROR"


def test_lifecycle_failure_uses_per_method_error_shape(tmp_path: Path) -> None:
    """A resource-lifecycle exception (SQLite open fails) must map to the
    exact per-method DTO shape — the same BF-5 rule as every other bridge
    method. No other method's keys may leak through.
    """
    bridge = _isolated_bridge(tmp_path)
    with patch(
        "ai_campaign_studio.presentation_webview.bridge.create_connection",
        side_effect=RuntimeError("db open failed"),
    ):
        review = bridge.get_ingestion_review({})
        approve = bridge.approve_fact_candidate({"candidate_id": "c-any"})
        reject = bridge.reject_fact_candidate({"candidate_id": "c-any"})
        assemble = bridge.assemble_brand_snapshot({})
        activate = bridge.activate_brand_snapshot({"snapshot_id": "snap-any"})
        listing = bridge.list_brand_snapshots({})

    assert review["ok"] is False
    assert review["error_code"] == "INTERNAL_ERROR"
    assert set(review.keys()) == {
        "ok",
        "brand_id",
        "candidates",
        "approved_count",
        "rejected_count",
        "error_code",
        "error_message",
    }

    assert approve["ok"] is False
    assert approve["error_code"] == "INTERNAL_ERROR"
    assert set(approve.keys()) == {
        "ok",
        "approved_fact_id",
        "candidate_id",
        "snapshot_url",
        "version",
        "error_code",
        "error_message",
    }

    assert reject["ok"] is False
    assert reject["error_code"] == "INTERNAL_ERROR"
    assert set(reject.keys()) == {
        "ok",
        "candidate_id",
        "status",
        "error_code",
        "error_message",
    }

    assert assemble["ok"] is False
    assert assemble["error_code"] == "INTERNAL_ERROR"
    assert set(assemble.keys()) == {
        "ok",
        "snapshot_id",
        "brand_id",
        "version",
        "approved_fact_count",
        "created_at",
        "error_code",
        "error_message",
    }

    # ACS-S2-018: the two new snapshot methods must use the same rule —
    # no key from any other method's DTO may leak into the error shape.
    assert activate["ok"] is False
    assert activate["error_code"] == "INTERNAL_ERROR"
    assert set(activate.keys()) == {
        "ok",
        "snapshot_id",
        "brand_id",
        "version",
        "approved_fact_count",
        "created_at",
        "was_already_active",
        "error_code",
        "error_message",
    }

    assert listing["ok"] is False
    assert listing["error_code"] == "INTERNAL_ERROR"
    assert set(listing.keys()) == {
        "ok",
        "brand_id",
        "snapshots",
        "error_code",
        "error_message",
    }


# --- ACS-S2-018: activate / list bridge methods ---


def _seed_brand_and_two_snapshots(
    bridge: CampaignBridgeApi, tmp_path: Path
) -> tuple[str, str, str]:
    """Insert a brand and two snapshots (v1, v2) directly through the
    bridge's per-call resource scope. Returns ``(brand_id, v1_id, v2_id)``
    as strings so tests can call into the bridge like a GUI would.
    """
    from dataclasses import replace

    with bridge._resource_scope():
        brand_id = BrandId("brand-test")
        bridge._brand_repo.save_brand(
            Brand(
                id=brand_id,
                name="Test",
                created_at=datetime(2026, 1, 1, tzinfo=UTC),
            )
        )
        v1_id = BrandSnapshotId("snap-v1")
        v2_id = BrandSnapshotId("snap-v2")
        base = BrandSnapshot(
            id=v1_id,
            brand_id=brand_id,
            version=1,
            language="en",
            locale="en_US",
            script="Latin",
            voice=BrandVoice(formality=""),
            audiences=(),
            services=(),
            visual_identity=VisualIdentity(),
            restrictions=(),
            approved_fact_ids=(),
            created_at=datetime(2026, 1, 1, tzinfo=UTC),
        )
        bridge._brand_repo.save_snapshot(base)
        bridge._brand_repo.save_snapshot(replace(base, id=v2_id, version=2))
    return str(brand_id), str(v1_id), str(v2_id)


def test_activate_brand_snapshot_happy_path_updates_seed(
    tmp_path: Path,
) -> None:
    """The headline guarantee: activating a snapshot rewrites the cache
    so the next ``_ensure_brand()`` call (the function every other bridge
    method uses to resolve the active snapshot) reports the new version.
    """
    bridge = _isolated_bridge(tmp_path)
    _brand_id, v1_id, v2_id = _seed_brand_and_two_snapshots(bridge, tmp_path)
    # Seed the cache with v1 (simulating the brand being seeded initially).
    seed_path = tmp_path / "brand-seed.json"
    seed_path.write_text(
        json.dumps({"brand_id": _brand_id, "brand_snapshot_id": v1_id}),
        encoding="utf-8",
    )

    result = bridge.activate_brand_snapshot({"snapshot_id": v2_id})
    assert result["ok"] is True
    assert result["snapshot_id"] == v2_id
    assert result["version"] == 2
    assert result["was_already_active"] is False

    # The cache now points at v2.
    cached = json.loads(seed_path.read_text(encoding="utf-8"))
    assert cached["brand_snapshot_id"] == v2_id
    assert cached["brand_id"] == _brand_id

    # And the next ``_ensure_brand()`` (which ``get_brand_overview`` /
    # ``create_campaign_and_generate_plan`` read) returns the v2 snapshot
    # — this is the real "downstream callers see the activated version"
    # check, not the cache file contents. Must run inside a resource scope
    # because ``_ensure_brand`` reads through ``self._brand_repo``.
    with bridge._resource_scope():
        active_brand_id, active_snapshot_id = bridge._ensure_brand()
    assert str(active_brand_id) == _brand_id
    assert str(active_snapshot_id) == v2_id


def test_activate_brand_snapshot_already_active_returns_was_already_active_true(
    tmp_path: Path,
) -> None:
    bridge = _isolated_bridge(tmp_path)
    _brand_id, v1_id, _v2_id = _seed_brand_and_two_snapshots(bridge, tmp_path)
    seed_path = tmp_path / "brand-seed.json"
    seed_path.write_text(
        json.dumps({"brand_id": _brand_id, "brand_snapshot_id": v1_id}),
        encoding="utf-8",
    )

    result = bridge.activate_brand_snapshot({"snapshot_id": v1_id})
    assert result["ok"] is True
    assert result["was_already_active"] is True
    # Cache file untouched (still pointing at v1, same mtime not asserted).
    cached = json.loads(seed_path.read_text(encoding="utf-8"))
    assert cached["brand_snapshot_id"] == v1_id


def test_activate_brand_snapshot_unknown_id_is_validation_error(
    tmp_path: Path,
) -> None:
    bridge = _isolated_bridge(tmp_path)
    result = bridge.activate_brand_snapshot({"snapshot_id": "snap-does-not-exist"})
    assert result["ok"] is False
    assert result["error_code"] == "VALIDATION_ERROR"
    assert "ne postoji" in result["error_message"].lower()


def test_activate_brand_snapshot_missing_snapshot_id_is_validation_error(
    tmp_path: Path,
) -> None:
    bridge = _isolated_bridge(tmp_path)
    # Activate is explicitly user-driven — NO fallback to the cached
    # snapshot (that would silently no-op). An empty payload is an error.
    assert bridge.activate_brand_snapshot({})["error_code"] == "VALIDATION_ERROR"


def test_list_brand_snapshots_marks_active_row(tmp_path: Path) -> None:
    bridge = _isolated_bridge(tmp_path)
    _brand_id, v1_id, v2_id = _seed_brand_and_two_snapshots(bridge, tmp_path)
    seed_path = tmp_path / "brand-seed.json"
    # Seed points at v2 — that's the "active" row.
    seed_path.write_text(
        json.dumps({"brand_id": _brand_id, "brand_snapshot_id": v2_id}),
        encoding="utf-8",
    )

    result = bridge.list_brand_snapshots({})
    assert result["ok"] is True
    assert result["brand_id"] == _brand_id
    snapshots = result["snapshots"]
    assert len(snapshots) == 2
    # DESC ordering: v2 first.
    assert snapshots[0]["version"] == 2
    assert snapshots[1]["version"] == 1
    by_id = {row["snapshot_id"]: row for row in snapshots}
    assert by_id[v2_id]["is_active"] is True
    assert by_id[v1_id]["is_active"] is False


def test_list_brand_snapshots_no_active_cache_returns_no_active_rows(
    tmp_path: Path,
) -> None:
    """When ``brand-seed.json`` does not exist, every row is reported
    with ``is_active=False`` — the user must explicitly activate one
    before anything is "live". This is the natural state right after
    the first ``assemble_brand_snapshot`` call (Opcija 2 contract:
    assemble does NOT auto-activate).
    """
    bridge = _isolated_bridge(tmp_path)
    brand_id, _v1_id, _v2_id = _seed_brand_and_two_snapshots(bridge, tmp_path)
    # Pass ``brand_id`` explicitly — an empty payload would fall through
    # ``_resolve_review_brand_id`` to ``_ensure_brand`` and create the
    # default fixture brand, hiding the rows we actually want to test.
    result = bridge.list_brand_snapshots({"brand_id": brand_id})
    assert result["ok"] is True
    assert result["brand_id"] == brand_id
    snapshots = result["snapshots"]
    assert len(snapshots) == 2
    assert all(row["is_active"] is False for row in snapshots), (
        "Without a cache, NO row may claim to be active"
    )
