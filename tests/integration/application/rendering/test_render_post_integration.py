"""Integration test for ``RenderPost`` (A14 dio 2) on a real SQLite DB.

This is the production-path end-to-end test: brand fixture ->
``CreateCampaign`` -> ``GenerateCampaignPlan`` -> ``ApproveCampaignPlan``
-> ``GenerateSocialPost`` -> ``GenerateVisualSystem`` -> ``PlanPostLayout``
-> ``RenderPost``. The renderer is the real ``PillowRenderer``, not a
fake. The output PNG is read back, validated, and its on-disk
``output_path`` is asserted to match what the caller asked for.

Unit-tier tests with fakes for all four ports live next to
``render_post.py``. The integration tier proves the wiring with real
SQLite + real Pillow.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from ai_campaign_studio.application.brands.load_brand_fixture import LoadBrandFixture
from ai_campaign_studio.application.campaigns.approve_campaign_plan import (
    ApproveCampaignPlan,
)
from ai_campaign_studio.application.campaigns.create_campaign import CreateCampaign
from ai_campaign_studio.application.campaigns.generate_campaign_plan import (
    GenerateCampaignPlan,
)
from ai_campaign_studio.application.posts.generate_social_post import (
    GenerateSocialPost,
)
from ai_campaign_studio.application.rendering import RenderPost
from ai_campaign_studio.application.visual.generate_visual_system import (
    GenerateVisualSystem,
)
from ai_campaign_studio.application.visual.plan_post_layout import PlanPostLayout
from ai_campaign_studio.domain.common.errors import EntityNotFound
from ai_campaign_studio.domain.common.ids import PostId, VisualSystemId
from ai_campaign_studio.domain.content.entities import CampaignTarget
from ai_campaign_studio.domain.visual.layout import LayoutSpec
from ai_campaign_studio.infrastructure.database.connection import create_connection
from ai_campaign_studio.infrastructure.database.migrations import run_migrations
from ai_campaign_studio.infrastructure.database.repositories import (
    SqliteBrandRepository,
    SqliteCampaignRepository,
    SqliteContentRepository,
    SqliteFactRepository,
    SqliteRevisionRepository,
    SqliteVisualRepository,
)
from ai_campaign_studio.infrastructure.database.unit_of_work import SqliteUnitOfWork
from ai_campaign_studio.infrastructure.rendering import PillowRenderer
from ai_campaign_studio.ports.ai import AIRequest, AIResponse
from ai_campaign_studio.ports.prompts import PromptDefinition
from ai_campaign_studio.ports.rendering import RenderStatus

_MIGRATIONS_DIR = Path(__file__).resolve().parents[4] / "resources" / "migrations"
_FIXTURE_PATH = (
    Path(__file__).resolve().parents[4] / "resources" / "fixtures" / "brightsmile.json"
)


# ---------------------------------------------------------------------------
# Fake AI / prompt ports -- identical pattern to
# test_plan_post_layout_integration.py so the AI layer is hermetic.
# ---------------------------------------------------------------------------


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


class _FakePromptRepository:
    def get(self, name: str, version: str) -> PromptDefinition:
        return PromptDefinition(
            name=name,
            version=version,
            purpose=name,
            input_contract="...",
            output_contract="...",
            language_support="EN/BHS",
            instructions="Produce the output.",
        )


# ---------------------------------------------------------------------------
# Pipelines
# ---------------------------------------------------------------------------


def _brief() -> dict:
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


def _plan_payload() -> dict:
    return {
        "campaign_theme": "Healthy smile",
        "items": [
            {
                "order": 1,
                "role": "PROBLEM",
                "topic": "Cost of implants",
                "goal": "awareness",
                "facts_needed": [],
            }
        ],
    }


def _post_payload() -> dict:
    return {
        "headline": "Short headline",
        "caption": "Caption",
        "hook": "Hook",
        "body": "Body",
        "cta": "CTA",
        "hashtags": [],
        "claims": [],
    }


def _visual_payload() -> dict:
    return {
        "campaign_visual_system": {
            "primary_layout_family": "HERO",
            "secondary_layout_family": None,
            "headline_scale": "LARGE",
            "image_treatment": "ROUNDED",
            "logo_rule": "SHOW",
            "cta_rule": "SHOW",
            "alignment": "CENTER",
            "style": ["clean"],
        },
        "layout_spec": {
            "primitive": "HERO",
            "image_position": "BACKGROUND",
            "headline_position": "CENTER",
            "headline_scale": "LARGE",
            "overlay": "DARK",
            "logo_position": "TOP_LEFT",
            "cta_style": "SOLID",
            "alignment": "CENTER",
            "format": "FEED_POST",
        },
    }


def _layout_payload() -> dict:
    return {
        "primitive": "HERO",
        "image_position": "BACKGROUND",
        "headline_position": "CENTER",
        "headline_scale": "LARGE",
        "overlay": "DARK",
        "logo_position": "TOP_LEFT",
        "cta_style": "SOLID",
        "alignment": "CENTER",
        "format": "999x999",
    }


def _run_full_pipeline(tmp_path: Path):
    """Build the production path: brand -> campaign -> plan -> post ->
    visual system -> layout. Return (piece, visual_system, layout) so
    each test can drive ``RenderPost`` with the artifacts it needs.
    """
    connection = create_connection(tmp_path / "test.db")
    run_migrations(connection, _MIGRATIONS_DIR)

    brand_repo = SqliteBrandRepository(connection)
    fact_repo = SqliteFactRepository(connection)
    campaign_repo = SqliteCampaignRepository(connection)
    content_repo = SqliteContentRepository(connection)
    revision_repo = SqliteRevisionRepository(connection)
    visual_repo = SqliteVisualRepository(connection)
    uow = SqliteUnitOfWork(connection)

    snapshot = LoadBrandFixture(brand_repo, fact_repo, uow).execute(_FIXTURE_PATH)
    campaign = CreateCampaign(campaign_repo, uow).execute(
        snapshot.brand_id, snapshot.id, _brief()
    )
    plan = GenerateCampaignPlan(
        campaign_repo,
        brand_repo,
        _FakePromptRepository(),
        _FakeAiPort(_plan_payload()),
        uow,
    ).execute(campaign.id)
    approved = ApproveCampaignPlan(campaign_repo, uow).execute(plan.id)

    item = approved.items[0]
    piece = GenerateSocialPost(
        campaign_repo,
        brand_repo,
        fact_repo,
        content_repo,
        revision_repo,
        _FakePromptRepository(),
        _FakeAiPort(_post_payload()),
        uow,
    ).execute(
        campaign.id,
        approved.id,
        item.id,
        CampaignTarget(
            channel="SOCIAL", platform_code="INSTAGRAM", format_code="FEED_POST"
        ),
    )

    visual_system, _ = GenerateVisualSystem(
        campaign_repo,
        brand_repo,
        visual_repo,
        _FakePromptRepository(),
        _FakeAiPort(_visual_payload()),
        uow,
    ).execute(approved.id)

    layout = PlanPostLayout(
        campaign_repo,
        content_repo,
        visual_repo,
        _FakePromptRepository(),
        _FakeAiPort(_layout_payload()),
        uow,
    ).execute(piece.id, visual_system.id, approved.id)

    return (
        connection,
        content_repo,
        campaign_repo,
        visual_repo,
        piece.id,
        visual_system.id,
        layout,
    )


def _build_use_case(connection) -> RenderPost:
    return RenderPost(
        content_repo=SqliteContentRepository(connection),
        campaign_repo=SqliteCampaignRepository(connection),
        visual_repo=SqliteVisualRepository(connection),
        renderer=PillowRenderer(),
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_end_to_end_render_post_writes_png(tmp_path: Path) -> None:
    """Happy path: ``RenderPost`` writes a real PNG to the caller's
    ``output_path``, the renderer reports ``SUCCESS``, and the on-disk
    file can be re-opened with Pillow without errors.
    """
    (
        connection,
        content_repo,
        campaign_repo,
        visual_repo,
        piece_id,
        vs_id,
        layout,
    ) = _run_full_pipeline(tmp_path)

    use_case = RenderPost(
        content_repo=content_repo,
        campaign_repo=campaign_repo,
        visual_repo=visual_repo,
        renderer=PillowRenderer(),
    )

    out_path = str(tmp_path / "rendered.png")
    result = use_case.execute(piece_id, vs_id, out_path)

    assert result.status is RenderStatus.SUCCESS
    assert result.output_path == out_path
    assert result.warnings == ()

    # File on disk: exists, non-empty, valid PNG, openable by Pillow.
    assert Path(out_path).is_file()
    assert Path(out_path).stat().st_size > 0
    reopened = Image.open(out_path)
    reopened.load()  # forces Pillow to decode the full pixel buffer
    assert reopened.format == "PNG"
    connection.close()


def test_render_post_uses_layout_format_dimensions(tmp_path: Path) -> None:
    """``PlanPostLayout`` overrides the AI's ``format`` field with the
    format-library value for the target (here: ``1080x1350`` for
    FEED_POST, as asserted in the planning integration test). The
    renderer MUST honour that exact canvas size in the on-disk PNG."""
    (
        connection,
        content_repo,
        campaign_repo,
        visual_repo,
        piece_id,
        vs_id,
        layout,
    ) = _run_full_pipeline(tmp_path)
    assert isinstance(layout, LayoutSpec)
    assert layout.format == "1080x1350"

    use_case = _build_use_case(connection)
    out_path = str(tmp_path / "rendered.png")
    result = use_case.execute(piece_id, vs_id, out_path)

    assert result.status is RenderStatus.SUCCESS
    with Image.open(out_path) as img:
        assert img.size == (1080, 1350)
    connection.close()


def test_render_post_missing_content_piece_raises(tmp_path: Path) -> None:
    """Looking up a post id that was never persisted -> ``EntityNotFound``."""
    connection = create_connection(tmp_path / "test.db")
    run_migrations(connection, _MIGRATIONS_DIR)
    use_case = _build_use_case(connection)

    with pytest.raises(EntityNotFound):
        use_case.execute(
            PostId("no-such-post"),
            VisualSystemId("vs-irrelevant"),
            str(tmp_path / "should_not_exist.png"),
        )
    # And nothing was written to the requested path.
    assert not (tmp_path / "should_not_exist.png").exists()
    connection.close()


def test_render_post_missing_layout_spec_raises(tmp_path: Path) -> None:
    """Visual system + content piece exist, but no layout spec was
    planned for the post -> ``EntityNotFound`` from the use-case."""
    (
        connection,
        content_repo,
        campaign_repo,
        visual_repo,
        piece_id,
        vs_id,
        _layout,
    ) = _run_full_pipeline(tmp_path)

    # Manually delete the layout spec for this post so the lookup misses
    # -- simulates the "piece was created but never put through
    # PlanPostLayout" path.
    connection.execute(
        "DELETE FROM layout_specs WHERE content_piece_id = ?", (str(piece_id),)
    )

    use_case = RenderPost(
        content_repo=content_repo,
        campaign_repo=campaign_repo,
        visual_repo=visual_repo,
        renderer=PillowRenderer(),
    )
    with pytest.raises(EntityNotFound):
        use_case.execute(piece_id, vs_id, str(tmp_path / "should_not_exist.png"))
    assert not (tmp_path / "should_not_exist.png").exists()
    connection.close()


def test_render_post_missing_visual_system_raises(tmp_path: Path) -> None:
    """Post + layout spec exist, but the caller passes a visual_system_id
    that was never persisted -> ``EntityNotFound`` from the use-case."""
    (
        connection,
        content_repo,
        campaign_repo,
        visual_repo,
        piece_id,
        _vs_id,
        _layout,
    ) = _run_full_pipeline(tmp_path)

    use_case = RenderPost(
        content_repo=content_repo,
        campaign_repo=campaign_repo,
        visual_repo=visual_repo,
        renderer=PillowRenderer(),
    )
    with pytest.raises(EntityNotFound):
        use_case.execute(
            piece_id,
            VisualSystemId("vs-does-not-exist"),
            str(tmp_path / "should_not_exist.png"),
        )
    assert not (tmp_path / "should_not_exist.png").exists()
    connection.close()
