"""Integration tests for ReviseContentPiece (A12 dio 2) on a real SQLite DB."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from ai_campaign_studio.application.brands.load_brand_fixture import LoadBrandFixture
from ai_campaign_studio.application.campaigns.create_campaign import CreateCampaign
from ai_campaign_studio.application.posts.revise_content_piece import (
    ReviseContentPiece,
)
from ai_campaign_studio.domain.campaign.entities import CampaignItem, CampaignPlan
from ai_campaign_studio.domain.campaign.enums import (
    CampaignItemStatus,
    CampaignPlanStatus,
)
from ai_campaign_studio.domain.campaign.roles import CampaignRole
from ai_campaign_studio.domain.common.ids import CampaignItemId, CampaignPlanId, PostId
from ai_campaign_studio.domain.content.entities import (
    CampaignTarget,
    ContentPiece,
    SocialPostPayload,
)
from ai_campaign_studio.domain.content.enums import (
    ContentPayloadType,
    ContentStatus,
)
from ai_campaign_studio.domain.content.revisions import RevisionType
from ai_campaign_studio.infrastructure.database.connection import create_connection
from ai_campaign_studio.infrastructure.database.migrations import run_migrations
from ai_campaign_studio.infrastructure.database.repositories import (
    SqliteBrandRepository,
    SqliteCampaignRepository,
    SqliteContentRepository,
    SqliteFactRepository,
    SqliteRevisionRepository,
)
from ai_campaign_studio.infrastructure.database.unit_of_work import SqliteUnitOfWork
from ai_campaign_studio.ports.ai import AIRequest, AIResponse
from ai_campaign_studio.ports.prompts import PromptDefinition

_MIGRATIONS_DIR = Path(__file__).resolve().parents[4] / "resources" / "migrations"
_FIXTURE_PATH = (
    Path(__file__).resolve().parents[4] / "resources" / "fixtures" / "brightsmile.json"
)


class _FakePromptRepository:
    def get(self, name: str, version: str) -> PromptDefinition:
        return PromptDefinition(
            name=name,
            version=version,
            purpose="revision",
            input_contract="...",
            output_contract="...",
            language_support="EN/BHS",
            instructions="Revise the post.",
        )


class _FakeAiPort:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def generate(self, request: AIRequest) -> AIResponse:
        del request
        return AIResponse(
            provider="fake",
            model="fake",
            latency_ms=1,
            structured_payload=self._payload,
        )


class _FakeFactRepository:
    def get_fact(self, fact_id):  # noqa: ANN001
        del fact_id
        return None

    def save_fact(self, fact) -> None:  # noqa: ANN001
        del fact

    def list_snapshot_facts(self, snapshot_id):  # noqa: ANN001
        del snapshot_id
        return ()


class _FailingContentRepository:
    def __init__(self, inner: SqliteContentRepository) -> None:
        self._inner = inner

    def save_content_piece(self, content_piece) -> None:  # noqa: ANN001
        raise RuntimeError("simulated mid-persist failure")

    def get_content_piece(self, content_piece_id):  # noqa: ANN001
        return self._inner.get_content_piece(content_piece_id)

    def list_campaign_content(self, campaign_id):  # noqa: ANN001
        return self._inner.list_campaign_content(campaign_id)


def _valid_brief() -> dict:
    return {
        "offer": "Dental implants",
        "goal": "Book consultations",
        "audience_text": "Adults",
        "targets": [
            {
                "channel": "SOCIAL",
                "platform_code": "INSTAGRAM",
                "format_code": "FEED_POST",
            }
        ],
        "content_piece_count": 1,
        "content_language_context": "BHS_LATIN",
    }


def _setup(tmp_path: Path):
    connection = create_connection(tmp_path / "test.db")
    run_migrations(connection, _MIGRATIONS_DIR)
    brand_repo = SqliteBrandRepository(connection)
    fact_repo = SqliteFactRepository(connection)
    campaign_repo = SqliteCampaignRepository(connection)
    content_repo = SqliteContentRepository(connection)
    revision_repo = SqliteRevisionRepository(connection)
    uow = SqliteUnitOfWork(connection)

    snapshot = LoadBrandFixture(brand_repo, fact_repo, uow).execute(_FIXTURE_PATH)
    campaign = CreateCampaign(campaign_repo, uow).execute(
        snapshot.brand_id, snapshot.id, _valid_brief()
    )
    item = CampaignItem(
        id=CampaignItemId("item-1"),
        order=1,
        role=CampaignRole.PROBLEM,
        topic="Implantati",
        goal="Edukacija",
        status=CampaignItemStatus.PLANNED,
    )
    plan = CampaignPlan(
        id=CampaignPlanId("plan-1"),
        campaign_id=campaign.id,
        version=1,
        status=CampaignPlanStatus.APPROVED,
        created_at=datetime.now(UTC),
        items=[item],
    )
    campaign_repo.save_plan(plan)

    piece = ContentPiece(
        id=PostId("post-1"),
        campaign_item_id=item.id,
        target=CampaignTarget(
            channel="SOCIAL", platform_code="INSTAGRAM", format_code="FEED_POST"
        ),
        payload_type=ContentPayloadType.SOCIAL_POST,
        status=ContentStatus.DRAFT,
        brand_snapshot_id=snapshot.id,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        payload=SocialPostPayload(
            headline="Old", caption="C", hook="H", body="B", cta="CTA"
        ),
    )
    content_repo.save_content_piece(piece)

    return connection, content_repo, revision_repo, uow


def test_revise_persists_revision_and_piece(tmp_path: Path) -> None:
    connection, content_repo, revision_repo, uow = _setup(tmp_path)
    use_case = ReviseContentPiece(
        content_repo,
        _FakeFactRepository(),
        revision_repo,
        _FakePromptRepository(),
        _FakeAiPort({"headline": "New headline"}),
        uow,
    )

    updated = use_case.execute(
        PostId("post-1"), RevisionType.NEW_HEADLINE, "warmer"
    )

    assert updated.payload is not None
    assert updated.payload.headline == "New headline"
    assert content_repo.get_content_piece(PostId("post-1")) == updated
    revisions = revision_repo.list_entity_revisions("ContentPiece", "post-1")
    assert len(revisions) == 1
    assert revisions[0].version == 1
    connection.close()


def test_revise_is_atomic_on_mid_failure(tmp_path: Path) -> None:
    connection, content_repo, revision_repo, uow = _setup(tmp_path)
    use_case = ReviseContentPiece(
        _FailingContentRepository(content_repo),
        _FakeFactRepository(),
        revision_repo,
        _FakePromptRepository(),
        _FakeAiPort({"headline": "New headline"}),
        uow,
    )

    with pytest.raises(RuntimeError):
        use_case.execute(PostId("post-1"), RevisionType.NEW_HEADLINE, "x")

    assert revision_repo.list_entity_revisions("ContentPiece", "post-1") == ()
    persisted = content_repo.get_content_piece(PostId("post-1"))
    assert persisted is not None
    assert persisted.payload is not None
    assert persisted.payload.headline == "Old"
    connection.close()
