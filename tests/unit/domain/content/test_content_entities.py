"""Content entity/claim/revision tests (A3)."""

from datetime import UTC, datetime

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
from ai_campaign_studio.domain.content.revisions import Revision, RevisionOrigin


def _dt() -> datetime:
    return datetime(2026, 9, 2, tzinfo=UTC)


def test_content_claim_coerces_collections_to_tuple() -> None:
    claim = ContentClaim(
        id="cl1",
        text="We are open seven days a week",
        type=ClaimType.FACT,
        status=ClaimStatus.VERIFIED_BY_FACT,
        fact_ids=["f1"],
        reason_codes=["ok"],
    )

    assert isinstance(claim.fact_ids, tuple)
    assert claim.fact_ids == ("f1",)


def test_revision_origin_is_enum() -> None:
    revision = Revision(
        id="r1",
        entity_type="content_piece",
        entity_id="p1",
        version=1,
        timestamp=_dt(),
        origin=RevisionOrigin.AI,
        previous_value="old",
        new_value="new",
    )

    assert revision.origin is RevisionOrigin.AI


def test_content_piece_constructs_and_coerces_collections() -> None:
    target = CampaignTarget(
        channel="SOCIAL", platform_code="INSTAGRAM", format_code="FEED_POST"
    )
    piece = ContentPiece(
        id="p1",
        campaign_item_id="ci1",
        target=target,
        payload_type=ContentPayloadType.SOCIAL_POST,
        status=ContentStatus.DRAFT,
        brand_snapshot_id="bs1",
        created_at=_dt(),
        updated_at=_dt(),
        facts_allowed=["f1"],
        revision_ids=["r1"],
    )

    assert piece.status is ContentStatus.DRAFT
    assert isinstance(piece.facts_allowed, tuple)
    assert piece.facts_allowed == ("f1",)


def test_social_post_payload_coerces_hashtags_to_tuple() -> None:
    payload = SocialPostPayload(
        headline="Headline",
        caption="Caption",
        hook="Hook",
        body="Body",
        cta="Call to action",
        hashtags=["a", "b"],
    )

    assert isinstance(payload.hashtags, tuple)
    assert payload.hashtags == ("a", "b")
