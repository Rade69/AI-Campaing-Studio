"""Integration tests for CreateCampaign (A9) on a real SQLite DB."""

from __future__ import annotations

from pathlib import Path

import pytest

from ai_campaign_studio.application.campaigns.create_campaign import CreateCampaign
from ai_campaign_studio.domain.common.ids import BrandId, BrandSnapshotId
from ai_campaign_studio.infrastructure.database.connection import create_connection
from ai_campaign_studio.infrastructure.database.migrations import run_migrations
from ai_campaign_studio.infrastructure.database.repositories import (  # noqa: E501
    SqliteCampaignRepository,
)
from ai_campaign_studio.infrastructure.database.unit_of_work import SqliteUnitOfWork

_MIGRATIONS_DIR = Path(__file__).resolve().parents[4] / "resources" / "migrations"


def _valid_brief() -> dict:
    return {
        "offer": "Dental implants",
        "goal": "Book consultations",
        "audience_text": "Adults 25-55",
        "targets": [
            {
                "channel": "SOCIAL",
                "platform_code": "INSTAGRAM",
                "format_code": "FEED_POST",
            }
        ],
        "content_piece_count": 3,
        "content_language_context": "BHS_LATIN",
    }


def _setup_db(tmp_path: Path):
    connection = create_connection(tmp_path / "test.db")
    run_migrations(connection, _MIGRATIONS_DIR)
    return connection


class _FailingCampaignRepository:
    """save_brief succeeds, save_campaign raises (mid-persist failure)."""

    def __init__(self, inner: SqliteCampaignRepository) -> None:
        self._inner = inner

    def save_brief(self, brief) -> None:  # noqa: ANN001
        self._inner.save_brief(brief)

    def save_campaign(self, campaign) -> None:  # noqa: ANN001
        raise RuntimeError("simulated mid-load failure")

    def get_campaign(self, campaign_id):  # noqa: ANN001
        return self._inner.get_campaign(campaign_id)

    def get_brief(self, brief_id):  # noqa: ANN001
        return self._inner.get_brief(brief_id)

    def save_plan(self, plan) -> None:  # noqa: ANN001
        self._inner.save_plan(plan)

    def get_plan(self, plan_id):  # noqa: ANN001
        return self._inner.get_plan(plan_id)


def test_create_campaign_persists_brief_and_campaign(tmp_path: Path) -> None:
    connection = _setup_db(tmp_path)
    repo = SqliteCampaignRepository(connection)
    uow = SqliteUnitOfWork(connection)
    use_case = CreateCampaign(repo, uow)

    campaign = use_case.execute(
        BrandId("brand-1"), BrandSnapshotId("snap-1"), _valid_brief()
    )

    assert repo.get_campaign(campaign.id) == campaign
    assert repo.get_brief(campaign.brief_id) is not None
    connection.close()


def test_create_campaign_is_atomic_on_mid_failure(tmp_path: Path) -> None:
    connection = _setup_db(tmp_path)
    inner = SqliteCampaignRepository(connection)
    failing_repo = _FailingCampaignRepository(inner)
    uow = SqliteUnitOfWork(connection)
    use_case = CreateCampaign(failing_repo, uow)

    with pytest.raises(RuntimeError):
        use_case.execute(BrandId("brand-1"), BrandSnapshotId("snap-1"), _valid_brief())

    # Both tables must be empty — the whole create rolled back.
    assert connection.execute("SELECT COUNT(*) FROM campaigns").fetchone()[0] == 0
    assert connection.execute("SELECT COUNT(*) FROM campaign_briefs").fetchone()[0] == 0
    connection.close()
