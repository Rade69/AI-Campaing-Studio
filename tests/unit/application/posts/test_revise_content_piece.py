"""Unit tests for ReviseContentPiece (A12 dio 2) with fake ports."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from ai_campaign_studio.application.posts.revise_content_piece import (
    ReviseContentPiece,
)
from ai_campaign_studio.domain.common.errors import EntityNotFound, InvariantViolation
from ai_campaign_studio.domain.common.ids import (
    BrandSnapshotId,
    CampaignItemId,
    FactId,
    PostId,
)
from ai_campaign_studio.domain.content.claims import ContentClaim
from ai_campaign_studio.domain.content.entities import (
    CampaignTarget,
    ContentPiece,
    SocialPostPayload,
)
from ai_campaign_studio.domain.content.enums import (
    ClaimStatus,
    ClaimType,
    ContentPayloadType,
    ContentStatus,
)
from ai_campaign_studio.domain.content.revisions import RevisionType
from ai_campaign_studio.domain.facts.entities import ApprovedFact, SourceReference
from ai_campaign_studio.domain.facts.enums import FactStatus
from ai_campaign_studio.ports.ai import AIRequest, AIResponse
from ai_campaign_studio.ports.prompts import PromptDefinition

_CREATED_AT = datetime(2026, 1, 1, tzinfo=UTC)


class _FakeUnitOfWork:
    def __init__(self) -> None:
        self.committed = False

    def __enter__(self) -> _FakeUnitOfWork:
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> bool:  # noqa: ANN001
        return False

    def commit(self) -> None:
        self.committed = True


class _FakeContentRepository:
    def __init__(self, piece: ContentPiece) -> None:
        self._piece = piece

    def get_content_piece(self, content_piece_id):  # noqa: ANN001
        return self._piece if self._piece.id == content_piece_id else None

    def save_content_piece(self, content_piece) -> None:  # noqa: ANN001
        self._piece = content_piece

    def list_campaign_content(self, campaign_id):  # noqa: ANN001
        del campaign_id
        return ()


class _FakeFactRepository:
    def __init__(self, facts: tuple[ApprovedFact, ...]) -> None:
        self._facts = {fact.id: fact for fact in facts}

    def get_fact(self, fact_id):  # noqa: ANN001
        return self._facts.get(fact_id)

    def save_fact(self, fact) -> None:  # noqa: ANN001
        del fact

    def list_snapshot_facts(self, snapshot_id):  # noqa: ANN001
        del snapshot_id
        return tuple(self._facts.values())


class _FakeRevisionRepository:
    def __init__(self) -> None:
        self.saved: list = []

    def save_revision(self, revision) -> None:  # noqa: ANN001
        self.saved.append(revision)

    def get_revision(self, revision_id):  # noqa: ANN001
        del revision_id
        return None

    def list_entity_revisions(self, entity_type, entity_id):  # noqa: ANN001
        del entity_type, entity_id
        return tuple(self.saved)


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
    def __init__(self, payload: dict | None) -> None:
        self._payload = payload
        self.calls: list[AIRequest] = []

    def generate(self, request: AIRequest) -> AIResponse:
        self.calls.append(request)
        return AIResponse(
            provider="fake",
            model="fake",
            latency_ms=1,
            structured_payload=self._payload,
        )


def _payload() -> SocialPostPayload:
    return SocialPostPayload(
        headline="Old headline",
        caption="Old caption",
        hook="Old hook",
        body="Old body",
        cta="Old cta",
        hashtags=(),
    )


def _claim() -> ContentClaim:
    return ContentClaim(
        id="claim-1",
        text="We offer dental implants",
        type=ClaimType.FACT,
        status=ClaimStatus.VERIFIED_BY_FACT,
        fact_ids=(FactId("fact-1"),),
    )


def _fact() -> ApprovedFact:
    return ApprovedFact(
        id=FactId("fact-1"),
        logical_fact_id="logical-1",
        version=1,
        content="We offer dental implants",
        source_ref=SourceReference(source_type="fixture", uri="fixture://x"),
        status=FactStatus.APPROVED,
        created_at=_CREATED_AT,
    )


def _piece(
    status: ContentStatus = ContentStatus.DRAFT,
    payload: SocialPostPayload | None = None,
    revision_ids: tuple = (),
) -> ContentPiece:
    return ContentPiece(
        id=PostId("post-1"),
        campaign_item_id=CampaignItemId("item-1"),
        target=CampaignTarget(
            channel="SOCIAL", platform_code="INSTAGRAM", format_code="FEED_POST"
        ),
        payload_type=ContentPayloadType.SOCIAL_POST,
        status=status,
        brand_snapshot_id=BrandSnapshotId("snap-1"),
        created_at=_CREATED_AT,
        updated_at=_CREATED_AT,
        facts_allowed=(FactId("fact-1"),),
        claims=(_claim(),),
        revision_ids=revision_ids,
        payload=payload,
    )


def _make_use_case(piece, ai_payload, revision_repo=None):
    return ReviseContentPiece(
        _FakeContentRepository(piece),
        _FakeFactRepository((_fact(),)),
        revision_repo if revision_repo is not None else _FakeRevisionRepository(),
        _FakePromptRepository(),
        _FakeAiPort(ai_payload),
        _FakeUnitOfWork(),
    )


def test_new_headline_changes_only_headline() -> None:
    use_case = _make_use_case(
        _piece(payload=_payload()), {"headline": "New headline"}
    )

    updated = use_case.execute(
        PostId("post-1"), RevisionType.NEW_HEADLINE, "warmer headline"
    )

    assert updated.payload is not None
    assert updated.payload.headline == "New headline"
    assert updated.payload.caption == "Old caption"
    assert updated.payload.hook == "Old hook"
    assert updated.payload.body == "Old body"
    assert updated.payload.cta == "Old cta"


def test_invalid_ai_output_raises_before_persist() -> None:
    revision_repo = _FakeRevisionRepository()
    use_case = ReviseContentPiece(
        _FakeContentRepository(_piece(payload=_payload())),
        _FakeFactRepository((_fact(),)),
        revision_repo,
        _FakePromptRepository(),
        _FakeAiPort({"headline": 123}),  # wrong type
        _FakeUnitOfWork(),
    )

    with pytest.raises(ValidationError):
        use_case.execute(PostId("post-1"), RevisionType.NEW_HEADLINE, "x")

    assert revision_repo.saved == []


def test_out_of_scope_field_rejected_before_persist() -> None:
    content_repo = _FakeContentRepository(_piece(payload=_payload()))
    revision_repo = _FakeRevisionRepository()
    use_case = ReviseContentPiece(
        content_repo,
        _FakeFactRepository((_fact(),)),
        revision_repo,
        _FakePromptRepository(),
        _FakeAiPort({"headline": "New", "caption": "Changed"}),
        _FakeUnitOfWork(),
    )

    with pytest.raises(InvariantViolation):
        use_case.execute(PostId("post-1"), RevisionType.NEW_HEADLINE, "x")

    assert revision_repo.saved == []  # nothing persisted


def test_new_visual_direction_rejected_without_ai_call() -> None:
    ai_port = _FakeAiPort(None)
    use_case = ReviseContentPiece(
        _FakeContentRepository(_piece(payload=_payload())),
        _FakeFactRepository((_fact(),)),
        _FakeRevisionRepository(),
        _FakePromptRepository(),
        ai_port,
        _FakeUnitOfWork(),
    )

    with pytest.raises(InvariantViolation):
        use_case.execute(PostId("post-1"), RevisionType.NEW_VISUAL_DIRECTION, "x")

    assert ai_port.calls == []


def test_no_payload_rejected() -> None:
    use_case = _make_use_case(_piece(payload=None), {"headline": "New"})

    with pytest.raises(InvariantViolation):
        use_case.execute(PostId("post-1"), RevisionType.NEW_HEADLINE, "x")


def test_unknown_piece_raises() -> None:
    use_case = _make_use_case(_piece(payload=_payload()), {"headline": "New"})

    with pytest.raises(EntityNotFound):
        use_case.execute(PostId("missing"), RevisionType.NEW_HEADLINE, "x")


def test_approved_piece_always_needs_review() -> None:
    use_case = _make_use_case(
        _piece(status=ContentStatus.APPROVED, payload=_payload()),
        {"headline": "Clean new headline"},
    )

    updated = use_case.execute(
        PostId("post-1"), RevisionType.NEW_HEADLINE, "cleaner"
    )

    assert updated.status is ContentStatus.NEEDS_REVIEW


def test_draft_piece_follows_derive_status() -> None:
    use_case = _make_use_case(
        _piece(status=ContentStatus.DRAFT, payload=_payload()),
        {"headline": "Clean new headline"},
    )

    updated = use_case.execute(
        PostId("post-1"), RevisionType.NEW_HEADLINE, "cleaner"
    )

    assert updated.status is ContentStatus.DRAFT


def test_claims_are_relinted_not_regenerated() -> None:
    use_case = _make_use_case(
        _piece(payload=_payload()), {"headline": "New headline"}
    )

    updated = use_case.execute(PostId("post-1"), RevisionType.NEW_HEADLINE, "x")

    assert len(updated.claims) == 1
    assert updated.claims[0].id == "claim-1"
    assert updated.claims[0].text == "We offer dental implants"
    assert updated.claims[0].fact_ids == (FactId("fact-1"),)


def test_revision_version_increments_and_ids_grow() -> None:
    content_repo = _FakeContentRepository(_piece(payload=_payload()))
    revision_repo = _FakeRevisionRepository()
    use_case = ReviseContentPiece(
        content_repo,
        _FakeFactRepository((_fact(),)),
        revision_repo,
        _FakePromptRepository(),
        _FakeAiPort({"headline": "First"}),
        _FakeUnitOfWork(),
    )

    first = use_case.execute(PostId("post-1"), RevisionType.NEW_HEADLINE, "a")
    assert len(first.revision_ids) == 1

    use_case2 = ReviseContentPiece(
        content_repo,
        _FakeFactRepository((_fact(),)),
        revision_repo,
        _FakePromptRepository(),
        _FakeAiPort({"headline": "Second"}),
        _FakeUnitOfWork(),
    )
    second = use_case2.execute(PostId("post-1"), RevisionType.NEW_HEADLINE, "b")

    assert len(second.revision_ids) == 2
    versions = [revision.version for revision in revision_repo.saved]
    assert versions == [1, 2]
