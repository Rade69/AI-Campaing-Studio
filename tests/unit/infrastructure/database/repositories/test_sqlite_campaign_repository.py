"""Unit tests for ``SqliteCampaignRepository.delete_campaign`` (ACS-GUI-006).

The delete is the FIRST delete operation in the entire repository layer.
These tests pin the cascade order and idempotency contract, so a future
"delete approved campaign" feature can extend the cascade (or
explicitly decide NOT to) with full visibility of today's baseline.

Pattern reference for the SQLite fixture: ``tests/integration/application/
campaigns/test_generate_campaign_plan_integration.py``.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from ai_campaign_studio.domain.campaign.entities import Campaign, CampaignBrief
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
from ai_campaign_studio.infrastructure.database.connection import create_connection
from ai_campaign_studio.infrastructure.database.migrations import run_migrations
from ai_campaign_studio.infrastructure.database.repositories import (
    SqliteCampaignRepository,
)

_MIGRATIONS_DIR = (
    Path(__file__).resolve().parents[5] / "resources" / "migrations"
)
_CREATED_AT = datetime(2026, 1, 1, tzinfo=UTC)


def _setup_db(tmp_path: Path):
    """Stand up a clean SQLite DB on tmp_path with migrations applied.

    Returns a (repo, conn) pair; caller is responsible for closing the
    connection (the standard ``conn.close()`` works because the repo
    holds a reference to the same connection).
    """
    conn = create_connection(tmp_path / "test.db")
    run_migrations(conn, _MIGRATIONS_DIR)
    return SqliteCampaignRepository(conn), conn


def _campaign(campaign_id: str, brief_id: str = "brief-1") -> Campaign:
    return Campaign(
        id=CampaignId(campaign_id),
        brand_id=BrandId("brand-1"),
        brand_snapshot_id=BrandSnapshotId("snap-1"),
        brief_id=brief_id,
        status=CampaignStatus.DRAFT,
        created_at=_CREATED_AT,
    )


def _brief(brief_id: str = "brief-1") -> CampaignBrief:
    return CampaignBrief(
        id=brief_id,
        offer="Test offer",
        goal="Test goal",
        audience_text="Adults",
        targets=(),
        content_piece_count=3,
        content_language_context="BHS_LATIN",
        special_instructions=(),
        created_at=_CREATED_AT,
    )


# --- happy path --------------------------------------------------------------


def test_delete_campaign_removes_campaign_row(tmp_path) -> None:
    """The campaign row itself is gone after ``delete_campaign``."""
    repo, conn = _setup_db(tmp_path)
    repo.save_brief(_brief())
    repo.save_campaign(_campaign("cmp-1"))

    assert conn.execute("SELECT COUNT(*) FROM campaigns").fetchone()[0] == 1
    repo.delete_campaign(CampaignId("cmp-1"), brief_id="brief-1")
    assert conn.execute("SELECT COUNT(*) FROM campaigns").fetchone()[0] == 0
    conn.close()


def test_delete_campaign_removes_brief_when_brief_id_passed(tmp_path) -> None:
    """The fresh brief that ``CreateCampaign`` just made is also gone —
    the bridge passes ``brief_id`` so this row is part of the cascade."""
    repo, conn = _setup_db(tmp_path)
    repo.save_brief(_brief())
    repo.save_campaign(_campaign("cmp-1"))

    assert conn.execute("SELECT COUNT(*) FROM campaign_briefs").fetchone()[0] == 1
    repo.delete_campaign(CampaignId("cmp-1"), brief_id="brief-1")
    assert conn.execute("SELECT COUNT(*) FROM campaign_briefs").fetchone()[0] == 0
    conn.close()


def test_delete_campaign_preserves_brief_when_brief_id_omitted(tmp_path) -> None:
    """``brief_id=None`` opt-out: a caller that knows the brief is shared
    with another aggregate can keep it. Future safety; not used by the
    bridge today."""
    repo, conn = _setup_db(tmp_path)
    repo.save_brief(_brief())
    repo.save_campaign(_campaign("cmp-1"))

    repo.delete_campaign(CampaignId("cmp-1"))  # no brief_id
    assert conn.execute("SELECT COUNT(*) FROM campaigns").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM campaign_briefs").fetchone()[0] == 1
    conn.close()


def test_delete_campaign_removes_plan_and_items(tmp_path) -> None:
    """A campaign that DID get a plan still cascades cleanly: plan rows
    and their items are removed in the same call. This proves the
    cascade is correct for the rare case where a compensating delete
    runs after a partial plan commit (should not happen in the bridge
    today, but the cascade must be safe either way)."""
    from ai_campaign_studio.domain.campaign.entities import (
        CampaignItem,
        CampaignPlan,
    )

    repo, conn = _setup_db(tmp_path)
    repo.save_brief(_brief())
    repo.save_campaign(_campaign("cmp-1"))
    plan = CampaignPlan(
        id=CampaignPlanId("plan-1"),
        campaign_id=CampaignId("cmp-1"),
        version=1,
        status=CampaignPlanStatus.DRAFT,
        created_at=_CREATED_AT,
        items=(
            CampaignItem(
                id=CampaignItemId("item-1"),
                order=1,
                role=CampaignRole.PROBLEM,
                topic="t1",
                goal="g",
                status=CampaignItemStatus.PLANNED,
                target_audience_id=None,
                facts_needed=(),
            ),
        ),
    )
    repo.save_plan(plan)
    assert conn.execute("SELECT COUNT(*) FROM campaign_plans").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM campaign_items").fetchone()[0] == 1

    repo.delete_campaign(CampaignId("cmp-1"), brief_id="brief-1")
    assert conn.execute("SELECT COUNT(*) FROM campaigns").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM campaign_briefs").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM campaign_plans").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM campaign_items").fetchone()[0] == 0
    conn.close()


# --- contract / edge cases ---------------------------------------------------


def test_delete_nonexistent_campaign_is_noop(tmp_path) -> None:
    """Idempotent: deleting a campaign that never existed is silent."""
    repo, conn = _setup_db(tmp_path)
    # No rows inserted at all.
    repo.delete_campaign(CampaignId("ghost"), brief_id="ghost-brief")
    # No rows were ever created; delete was a no-op.
    assert conn.execute("SELECT COUNT(*) FROM campaigns").fetchone()[0] == 0
    conn.close()


def test_delete_campaign_respects_fk_to_brief(tmp_path) -> None:
    """The cascade ordering (campaign BEFORE brief) is correct under
    ``PRAGMA foreign_keys = ON`` — this test would raise an
    ``IntegrityError`` if the order were reversed."""
    repo, conn = _setup_db(tmp_path)
    repo.save_brief(_brief())
    repo.save_campaign(_campaign("cmp-1"))
    # Should NOT raise. If it does, the SQL order is wrong.
    repo.delete_campaign(CampaignId("cmp-1"), brief_id="brief-1")
    conn.close()


def test_delete_campaign_does_not_touch_other_campaigns(tmp_path) -> None:
    """The cascade is scoped to the one campaign — sibling rows are
    untouched. Important: a compensating delete in a multi-campaign
    future must never cross-contaminate."""
    repo, conn = _setup_db(tmp_path)
    repo.save_brief(_brief("brief-a"))
    repo.save_campaign(_campaign("cmp-a", brief_id="brief-a"))
    repo.save_brief(_brief("brief-b"))
    repo.save_campaign(_campaign("cmp-b", brief_id="brief-b"))

    repo.delete_campaign(CampaignId("cmp-a"), brief_id="brief-a")

    assert conn.execute("SELECT COUNT(*) FROM campaigns").fetchone()[0] == 1
    assert conn.execute("SELECT id FROM campaigns").fetchone()[0] == "cmp-b"
    assert conn.execute("SELECT COUNT(*) FROM campaign_briefs").fetchone()[0] == 1
    conn.close()


# --- protocol conformance ----------------------------------------------------


def test_repository_implements_delete_campaign() -> None:
    """The repo class declares the port method (runtime checkable on the
    Protocol means the structural match is what counts)."""

    # CampaignRepositoryPort is runtime_checkable; the SqliteCampaignRepository
    # instance exposes the right structural shape. We don't need an actual
    # instance — just the class to be present and have the method.
    assert hasattr(SqliteCampaignRepository, "delete_campaign")


@pytest.mark.parametrize("brief_id", [None, "explicit-brief-id"])
def test_delete_campaign_signature_accepts_optional_brief_id(
    tmp_path, brief_id
) -> None:
    """The keyword-only ``brief_id`` parameter must be optional (``None``
    default) AND accept a concrete value. Both shapes must not raise on
    a fresh DB."""
    repo, conn = _setup_db(tmp_path)
    repo.save_brief(_brief())
    repo.save_campaign(_campaign("cmp-1"))

    # Should not raise regardless of the brief_id shape.
    repo.delete_campaign(CampaignId("cmp-1"), brief_id=brief_id)
    assert conn.execute("SELECT COUNT(*) FROM campaigns").fetchone()[0] == 0
    conn.close()


# --- ACS-F1-046: list_campaigns / get_latest_plan_for_campaign -------------


def test_list_campaigns_empty_db_returns_empty_tuple(tmp_path) -> None:
    """No campaigns -> ``()``, not an error (the bridge maps this to an
    empty list, never raises)."""
    repo, conn = _setup_db(tmp_path)
    assert repo.list_campaigns() == ()
    conn.close()


def test_list_campaigns_returns_newest_first(tmp_path) -> None:
    """Ordering contract: ``created_at DESC`` (newest first)."""
    repo, conn = _setup_db(tmp_path)
    repo.save_brief(_brief())  # campaigns.brief_id has an FK to campaign_briefs
    older = Campaign(
        id=CampaignId("cmp-older"),
        brand_id=BrandId("brand-1"),
        brand_snapshot_id=BrandSnapshotId("snap-1"),
        brief_id="brief-1",
        status=CampaignStatus.DRAFT,
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    newer = Campaign(
        id=CampaignId("cmp-newer"),
        brand_id=BrandId("brand-1"),
        brand_snapshot_id=BrandSnapshotId("snap-1"),
        brief_id="brief-1",
        status=CampaignStatus.DRAFT,
        created_at=datetime(2026, 1, 2, tzinfo=UTC),
    )
    repo.save_campaign(older)
    repo.save_campaign(newer)

    result = repo.list_campaigns()
    assert [str(c.id) for c in result] == ["cmp-newer", "cmp-older"]
    conn.close()


def test_get_latest_plan_for_campaign_no_plan_returns_none(tmp_path) -> None:
    """A campaign with no plan at all -> ``None`` (bridge maps to
    ``plan_item_count=0``)."""
    repo, conn = _setup_db(tmp_path)
    repo.save_brief(_brief())
    repo.save_campaign(_campaign("cmp-1"))
    assert repo.get_latest_plan_for_campaign(CampaignId("cmp-1")) is None
    conn.close()


def test_get_latest_plan_for_campaign_returns_highest_version(tmp_path) -> None:
    """Two plans for the same campaign -> the HIGHEST ``version`` wins,
    with its items loaded (same item-loading shape as ``get_plan``)."""
    from ai_campaign_studio.domain.campaign.entities import (
        CampaignItem,
        CampaignPlan,
    )

    repo, conn = _setup_db(tmp_path)
    repo.save_brief(_brief())
    repo.save_campaign(_campaign("cmp-1"))

    def _plan(plan_id: str, version: int) -> CampaignPlan:
        return CampaignPlan(
            id=CampaignPlanId(plan_id),
            campaign_id=CampaignId("cmp-1"),
            version=version,
            status=CampaignPlanStatus.DRAFT,
            created_at=_CREATED_AT,
            items=(
                CampaignItem(
                    id=CampaignItemId(f"item-{plan_id}"),
                    order=1,
                    role=CampaignRole.PROBLEM,
                    topic=f"t-{plan_id}",
                    goal="g",
                    status=CampaignItemStatus.PLANNED,
                    target_audience_id=None,
                    facts_needed=(),
                ),
            ),
        )

    repo.save_plan(_plan("plan-1", 1))
    repo.save_plan(_plan("plan-2", 2))

    result = repo.get_latest_plan_for_campaign(CampaignId("cmp-1"))
    assert result is not None
    assert str(result.id) == "plan-2"
    assert result.version == 2
    assert len(result.items) == 1
    assert str(result.items[0].id) == "item-plan-2"
    conn.close()
