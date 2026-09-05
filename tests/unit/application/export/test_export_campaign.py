"""Unit tests for ``ExportCampaign`` (A15, plan section 46).

Fake-port pattern: each Repository / Renderer / Writer gets a thin
fake that records calls and returns scripted results. The integration
tier (``test_export_campaign_integration.py``) replaces these fakes
with real SQLite + real Pillow + real ``ZipExportWriter``.
"""

from __future__ import annotations

import json
import zipfile
from datetime import UTC, datetime
from pathlib import Path

import pytest

from ai_campaign_studio.application.export import ExportCampaign
from ai_campaign_studio.domain.campaign.entities import (
    Campaign,
    CampaignBrief,
    CampaignItem,
    CampaignPlan,
)
from ai_campaign_studio.domain.campaign.enums import (
    CampaignItemStatus,
    CampaignPlanStatus,
    CampaignStatus,
)
from ai_campaign_studio.domain.campaign.roles import CampaignRole
from ai_campaign_studio.domain.common.errors import (
    EntityNotFound,
    InvariantViolation,
)
from ai_campaign_studio.domain.common.ids import (
    BrandId,
    BrandSnapshotId,
    CampaignId,
    CampaignItemId,
    CampaignPlanId,
    PostId,
    RevisionId,
    VisualSystemId,
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
from ai_campaign_studio.domain.content.revisions import (
    Revision,
    RevisionOrigin,
)
from ai_campaign_studio.domain.visual.entities import CampaignVisualSystem
from ai_campaign_studio.domain.visual.enums import (
    Alignment,
    CtaStyle,
    HeadlinePosition,
    HeadlineScale,
    ImagePosition,
    LayoutPrimitive,
    LogoPosition,
    Overlay,
)
from ai_campaign_studio.domain.visual.layout import LayoutSpec
from ai_campaign_studio.ports.rendering import (
    RenderRequest,
    RenderResult,
    RenderStatus,
)

# ---------------------------------------------------------------------------
# Test fixtures (in-memory entities, fakes)
# ---------------------------------------------------------------------------


def _dt() -> datetime:
    return datetime(2026, 1, 1, tzinfo=UTC)


def _campaign(campaign_id: str = "c-1") -> Campaign:
    return Campaign(
        id=CampaignId(campaign_id),
        brand_id=BrandId("b-1"),
        brand_snapshot_id=BrandSnapshotId("bs-1"),
        brief_id="brief-1",
        status=CampaignStatus.DRAFT,
        created_at=_dt(),
    )


def _brief() -> CampaignBrief:
    return CampaignBrief(
        id="brief-1",
        offer="Test offer",
        goal="Test goal",
        audience_text="Adults 25-45",
        targets=(),
        content_piece_count=2,
        content_language_context="BHS_LATIN",
        special_instructions=(),
        created_at=_dt(),
    )


def _plan(
    campaign_id: str = "c-1",
    items: tuple[CampaignItem, ...] = (),
    version: int = 1,
) -> CampaignPlan:
    return CampaignPlan(
        id=CampaignPlanId("plan-1"),
        campaign_id=CampaignId(campaign_id),
        version=version,
        status=CampaignPlanStatus.APPROVED,
        created_at=_dt(),
        items=items,
    )


def _item(item_id: str, order: int) -> CampaignItem:
    return CampaignItem(
        id=CampaignItemId(item_id),
        order=order,
        role=CampaignRole.PROBLEM,
        topic=f"Topic {item_id}",
        goal="awareness",
        status=CampaignItemStatus.PLANNED,
    )


def _visual_system() -> CampaignVisualSystem:
    return CampaignVisualSystem(
        id=VisualSystemId("vs-1"),
        campaign_id=CampaignId("c-1"),
        primary_layout_family=LayoutPrimitive.HERO,
        headline_scale=HeadlineScale.MEDIUM,
        image_treatment="",
        logo_rule="",
        cta_rule="",
        alignment=Alignment.LEFT,
        created_at=_dt(),
    )


def _layout_spec(piece_id: str) -> LayoutSpec:
    return LayoutSpec(
        primitive=LayoutPrimitive.HERO,
        image_position=ImagePosition.NONE,
        headline_position=HeadlinePosition.TOP,
        headline_scale=HeadlineScale.MEDIUM,
        overlay=Overlay.NONE,
        logo_position=LogoPosition.TOP_LEFT,
        cta_style=CtaStyle.SOLID,
        alignment=Alignment.LEFT,
        format="200x200",
        id=f"ls-{piece_id}",
        content_piece_id=PostId(piece_id),
        validation_status="VALID",
    )


def _payload() -> SocialPostPayload:
    return SocialPostPayload(
        headline="h", caption="c", hook="k", body="b", cta="ct"
    )


def _piece(
    piece_id: str,
    item_id: str,
    *,
    with_payload: bool = True,
    revision_ids: tuple[RevisionId, ...] = (RevisionId("rev-1"),),
) -> ContentPiece:
    return ContentPiece(
        id=PostId(piece_id),
        campaign_item_id=CampaignItemId(item_id),
        target=CampaignTarget(
            channel="SOCIAL",
            platform_code="INSTAGRAM",
            format_code="FEED_POST",
        ),
        payload_type=ContentPayloadType.SOCIAL_POST,
        status=ContentStatus.APPROVED,
        brand_snapshot_id=BrandSnapshotId("bs-1"),
        created_at=_dt(),
        updated_at=_dt(),
        revision_ids=revision_ids,
        payload=_payload() if with_payload else None,
    )


def _claim(claim_id: str) -> ContentClaim:
    return ContentClaim(
        id=claim_id,
        text=f"claim {claim_id}",
        type=ClaimType.FACT,
        status=ClaimStatus.APPROVED,
        fact_ids=(),
        reason_codes=(),
    )


# Sentinel: separates "use the default fixture" from "explicitly None
# to simulate a missing upstream object" in ``_use_case``. Plain
# ``None`` would be ambiguous with a default argument.
class _Missing:
    """Sentinel type — ``_use_case`` recognises instances and
    substitutes the matching default. Use the module-level
    ``MISSING`` instance, not this class, in tests."""

    pass


MISSING = _Missing()


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class _FakeCampaignRepo:
    """In-memory CampaignRepositoryPort.

    Each of the three upstream objects is stored as-given (no
    defaulting). The ``_use_case`` helper is responsible for
    constructing the default fixture for happy-path tests and
    passing ``None`` for missing-scenario tests.
    """

    def __init__(
        self,
        campaign: Campaign | None,
        brief: CampaignBrief | None,
        plan: CampaignPlan | None,
    ) -> None:
        self._campaign = campaign
        self._brief = brief
        self._plan = plan
        self.get_campaign_calls = 0
        self.get_brief_calls = 0
        self.get_plan_calls = 0

    def get_campaign(self, campaign_id: CampaignId) -> Campaign | None:
        self.get_campaign_calls += 1
        if self._campaign is not None and campaign_id == self._campaign.id:
            return self._campaign
        return None

    def get_brief(self, brief_id: str) -> CampaignBrief | None:
        self.get_brief_calls += 1
        if self._brief is not None and brief_id == self._brief.id:
            return self._brief
        return None

    def get_plan(self, plan_id: CampaignPlanId) -> CampaignPlan | None:
        self.get_plan_calls += 1
        if self._plan is not None and plan_id == self._plan.id:
            return self._plan
        return None


class _FakeContentRepo:
    """In-memory ContentRepositoryPort."""

    def __init__(self, pieces: tuple[ContentPiece, ...] = ()) -> None:
        self._pieces = {str(p.id): p for p in pieces}
        self.list_calls = 0
        self.get_calls = 0

    def get_content_piece(self, content_piece_id: PostId) -> ContentPiece | None:
        self.get_calls += 1
        return self._pieces.get(str(content_piece_id))

    def list_campaign_content(
        self, campaign_id: CampaignId
    ) -> tuple[ContentPiece, ...]:
        # All pieces belong to the test campaign by construction.
        self.list_calls += 1
        return tuple(self._pieces.values())


class _FakeVisualRepo:
    """In-memory VisualRepositoryPort.

    No defaulting: the caller (``_use_case``) decides what is
    present and what is missing. Passing ``None`` for
    ``visual_system`` simulates the "visual system not found" branch.
    """

    def __init__(
        self,
        visual_system: CampaignVisualSystem | None,
        layouts: dict[str, LayoutSpec] | None,
        campaign: Campaign | None,
    ) -> None:
        self._vs = visual_system
        self._layouts = layouts or {}
        self._campaign = campaign

    def get_visual_system(
        self, visual_system_id: VisualSystemId
    ) -> CampaignVisualSystem | None:
        if self._vs is not None and visual_system_id == self._vs.id:
            return self._vs
        return None

    def get_layout_spec_by_content_piece(
        self, content_piece_id: PostId
    ) -> LayoutSpec | None:
        return self._layouts.get(str(content_piece_id))

    def get_campaign(self, campaign_id: CampaignId) -> Campaign | None:
        return self._campaign


class _FakeRevisionRepo:
    """In-memory RevisionRepositoryPort.

    ``revisions_by_piece`` maps piece_id (str) -> tuple of Revision.
    """

    def __init__(
        self, revisions_by_piece: dict[str, tuple[Revision, ...]] | None = None
    ) -> None:
        self._revs = revisions_by_piece or {}

    def list_entity_revisions(
        self, entity_type: str, entity_id: str
    ) -> tuple[Revision, ...]:
        if entity_type == "ContentPiece":
            return self._revs.get(entity_id, ())
        return ()


class _RecordingRenderer:
    """Fake RendererPort that returns a configurable status and a
    deterministic PNG-shaped byte blob.

    ``render_status`` controls ``RenderResult.status`` for every call;
    ``raise_layout_missing`` flips the renderer to raise
    ``EntityNotFound`` (simulating the "piece without LayoutSpec"
    skip path — the use-case catches this SPECIFIC exception).
    """

    def __init__(
        self,
        render_status: RenderStatus = RenderStatus.SUCCESS,
        png_bytes: bytes = b"\x89PNG\r\n\x1a\nFAKE_PNG",
    ) -> None:
        self.requests: list[RenderRequest] = []
        self._status = render_status
        self._png = png_bytes

    def render(self, request: RenderRequest) -> RenderResult:
        self.requests.append(request)
        return RenderResult(
            status=self._status,
            output_path=request.output_path,
            warnings=(),
            render_ms=1.0,
        )

    @property
    def png_bytes(self) -> bytes:
        return self._png


class _RecordingExportWriter:
    """Fake ExportWriterPort that records the call and writes nothing."""

    def __init__(self) -> None:
        self.last_output_path: str | None = None
        self.last_files: dict[str, bytes] | None = None
        self.call_count = 0

    def write_zip(
        self, output_path: str, files: dict[str, bytes]
    ) -> None:
        self.call_count += 1
        self.last_output_path = output_path
        # Copy to a fresh dict so the caller can't mutate our record
        # after the call (defensive — the use-case does not mutate).
        self.last_files = dict(files)


# ---------------------------------------------------------------------------
# Convenience: build a use-case with two renderable pieces by default
# ---------------------------------------------------------------------------


def _build_two_pieces() -> tuple[
    ContentPiece, ContentPiece, CampaignItem, CampaignItem
]:
    """Two pieces whose ``CampaignItem`` orders are 1 and 2. The two
    items are passed in REVERSE order to ``_FakeContentRepo`` (item-2
    first, item-1 second) so the order-sort test below can prove the
    export followed ``plan.items.order`` instead of the repo's
    accidental order.
    """
    item1 = _item("item-1", order=1)
    item2 = _item("item-2", order=2)
    piece1 = _piece("p-1", "item-1")
    piece2 = _piece("p-2", "item-2")
    return piece1, piece2, item1, item2


def _use_case(
    pieces: tuple[ContentPiece, ...] = (),
    plan_items: tuple[CampaignItem, ...] = (),
    *,
    layouts: dict[str, LayoutSpec] | None = None,
    visual_system: CampaignVisualSystem | None = MISSING,
    campaign: Campaign | None = MISSING,
    brief: CampaignBrief | None = MISSING,
    plan: CampaignPlan | None = MISSING,
    revisions: dict[str, tuple[Revision, ...]] | None = None,
    renderer: _RecordingRenderer | None = None,
    writer: _RecordingExportWriter | None = None,
):
    """Build a wired-up ``ExportCampaign`` for one test.

    The ``MISSING`` sentinel separates "use the default fixture"
    (most happy-path tests) from "explicitly None to simulate a
    missing upstream object" (the four per-object not-found
    tests). Plain ``None`` would be ambiguous with the natural
    "no value" of a default-argument.
    """
    plan_eff = plan if plan is not MISSING else _plan(items=plan_items)
    campaign_eff = campaign if campaign is not MISSING else _campaign()
    brief_eff = brief if brief is not MISSING else _brief()
    vs_eff = visual_system if visual_system is not MISSING else _visual_system()

    campaign_repo = _FakeCampaignRepo(
        campaign=campaign_eff, brief=brief_eff, plan=plan_eff
    )
    content_repo = _FakeContentRepo(pieces=pieces)
    visual_repo = _FakeVisualRepo(
        visual_system=vs_eff,
        layouts=layouts,
        campaign=campaign_eff,
    )
    revision_repo = _FakeRevisionRepo(revisions_by_piece=revisions)
    renderer = renderer if renderer is not None else _RecordingRenderer()
    writer = writer if writer is not None else _RecordingExportWriter()
    uc = ExportCampaign(
        campaign_repo=campaign_repo,
        content_repo=content_repo,
        visual_repo=visual_repo,
        revision_repo=revision_repo,
        renderer=renderer,
        export_writer=writer,
    )
    return uc, campaign_repo, content_repo, visual_repo, revision_repo, renderer, writer


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_happy_path_two_pieces_writes_zip_with_correct_keys() -> None:
    """Two renderable pieces -> ``write_zip`` receives exactly
    ``campaign.json``, ``telemetry/ai_summary.json``, and
    ``content-01/{content.json, caption.txt, feed.png}`` +
    ``content-02/...``. Nothing else.
    """
    piece1, piece2, item1, item2 = _build_two_pieces()
    # Repo order: piece2 first (would be ``content-01`` if we naively
    # trusted the repo) — but the plan says item1 is order=1.
    pieces = (piece2, piece1)
    layouts = {"p-1": _layout_spec("p-1"), "p-2": _layout_spec("p-2")}

    uc, _, _, _, _, _, writer = _use_case(
        pieces=pieces, plan_items=(item1, item2), layouts=layouts
    )
    result = uc.execute(
        CampaignId("c-1"),
        CampaignPlanId("plan-1"),
        VisualSystemId("vs-1"),
        str(Path("ignored.zip")),
    )

    assert writer.call_count == 1
    files = writer.last_files or {}
    assert set(files.keys()) == {
        "campaign.json",
        "manifest.json",
        "telemetry/ai_summary.json",
        "content-01/content.json",
        "content-01/caption.txt",
        "content-01/feed.png",
        "content-02/content.json",
        "content-02/caption.txt",
        "content-02/feed.png",
    }
    # The use-case passes the caller's path through unchanged.
    assert writer.last_output_path == "ignored.zip"
    # The two exported piece ids, in plan-item order, not repo order.
    assert result.exported_content_piece_ids == ("p-1", "p-2")
    assert result.skipped_content_piece_ids == ()


def test_folder_numbering_follows_plan_item_order_not_repo_order() -> None:
    """The CRITICAL test: pieces arrive in REVERSE order from the
    fake repo (``piece2`` first, ``piece1`` second), but the
    ``plan.items`` are ordered ``item-1`` (order=1) then ``item-2``
    (order=2). The export must produce ``content-01`` for the piece
    that maps to item-1, regardless of repo return order. This is
    the test that proves the spec's "prati CampaignItem.order, NE
    arbitraran redoslijed iz repozitorijuma" rule.
    """
    piece1, piece2, item1, item2 = _build_two_pieces()
    layouts = {"p-1": _layout_spec("p-1"), "p-2": _layout_spec("p-2")}

    # Reverse the pieces in the repo.
    uc, _, _, _, _, _, writer = _use_case(
        pieces=(piece2, piece1),  # repo returns item-2's piece first
        plan_items=(item1, item2),  # but plan says item-1 is order=1
        layouts=layouts,
    )
    result = uc.execute(
        CampaignId("c-1"),
        CampaignPlanId("plan-1"),
        VisualSystemId("vs-1"),
        "out.zip",
    )

    files = writer.last_files or {}
    # content-01 must hold the piece for item-1 (i.e. p-1), not the
    # first piece the repo returned.
    content_01 = json.loads(files["content-01/content.json"])
    content_02 = json.loads(files["content-02/content.json"])
    assert content_01["id"] == "p-1"
    assert content_01["campaign_item_id"] == "item-1"
    assert content_02["id"] == "p-2"
    assert content_02["campaign_item_id"] == "item-2"
    # And the public result mirrors the folder order.
    assert result.exported_content_piece_ids == ("p-1", "p-2")


def test_piece_without_payload_is_skipped() -> None:
    """A piece whose ``payload is None`` is recorded in
    ``skipped_content_piece_ids`` and is NOT in the ZIP at all (no
    folder, no telemetry entry, no campaign.json entry)."""
    piece1 = _piece("p-1", "item-1", with_payload=True)
    piece2 = _piece("p-2", "item-2", with_payload=False)
    item1 = _item("item-1", order=1)
    item2 = _item("item-2", order=2)
    layouts = {"p-1": _layout_spec("p-1")}  # p-2 has no layout (irrelevant here)

    uc, _, _, _, _, renderer, writer = _use_case(
        pieces=(piece1, piece2),
        plan_items=(item1, item2),
        layouts=layouts,
    )
    result = uc.execute(
        CampaignId("c-1"),
        CampaignPlanId("plan-1"),
        VisualSystemId("vs-1"),
        "out.zip",
    )

    files = writer.last_files or {}
    assert "content-01/content.json" in files
    assert "content-02" not in str(files.keys())  # skipped
    assert result.exported_content_piece_ids == ("p-1",)
    assert result.skipped_content_piece_ids == ("p-2",)
    # Renderer only called for the piece that was actually rendered.
    assert len(renderer.requests) == 1
    assert renderer.requests[0].content_piece_id == PostId("p-1")


def test_piece_without_layout_spec_is_skipped() -> None:
    """A piece whose ``RenderPost.execute`` raises ``EntityNotFound``
    (because no LayoutSpec exists) is skipped. The use-case catches
    this SPECIFIC exception — any other exception would propagate."""
    piece1 = _piece("p-1", "item-1")
    piece2 = _piece("p-2", "item-2")
    item1 = _item("item-1", order=1)
    item2 = _item("item-2", order=2)
    # Only p-1 has a layout spec; p-2's lookup will miss.
    layouts = {"p-1": _layout_spec("p-1")}

    uc, _, _, visual_repo, _, _, writer = _use_case(
        pieces=(piece1, piece2),
        plan_items=(item1, item2),
        layouts=layouts,
    )
    # Sanity: the fake will return None for p-2's layout.
    assert visual_repo.get_layout_spec_by_content_piece(PostId("p-2")) is None

    result = uc.execute(
        CampaignId("c-1"),
        CampaignPlanId("plan-1"),
        VisualSystemId("vs-1"),
        "out.zip",
    )

    files = writer.last_files or {}
    assert "content-01/feed.png" in files
    assert "content-02" not in str(files.keys())
    assert result.exported_content_piece_ids == ("p-1",)
    assert result.skipped_content_piece_ids == ("p-2",)


def test_missing_campaign_raises_entity_not_found() -> None:
    """No campaign -> ``EntityNotFound`` (one branch per upstream
    object, NOT a combined branch)."""
    piece1, _, item1, _ = _build_two_pieces()
    layouts = {"p-1": _layout_spec("p-1")}

    uc, _, _, _, _, _, _ = _use_case(
        pieces=(piece1,),
        plan_items=(item1,),
        layouts=layouts,
        campaign=None,  # type: ignore[arg-type]
    )
    with pytest.raises(EntityNotFound):
        uc.execute(
            CampaignId("c-1"),
            CampaignPlanId("plan-1"),
            VisualSystemId("vs-1"),
            "out.zip",
        )


def test_missing_brief_raises_entity_not_found() -> None:
    piece1, _, item1, _ = _build_two_pieces()
    layouts = {"p-1": _layout_spec("p-1")}
    uc, _, _, _, _, _, _ = _use_case(
        pieces=(piece1,),
        plan_items=(item1,),
        layouts=layouts,
        brief=None,  # type: ignore[arg-type]
    )
    with pytest.raises(EntityNotFound):
        uc.execute(
            CampaignId("c-1"),
            CampaignPlanId("plan-1"),
            VisualSystemId("vs-1"),
            "out.zip",
        )


def test_missing_plan_raises_entity_not_found() -> None:
    piece1, _, item1, _ = _build_two_pieces()
    layouts = {"p-1": _layout_spec("p-1")}
    uc, _, _, _, _, _, _ = _use_case(
        pieces=(piece1,),
        plan_items=(item1,),
        layouts=layouts,
        plan=None,  # type: ignore[arg-type]
    )
    with pytest.raises(EntityNotFound):
        uc.execute(
            CampaignId("c-1"),
            CampaignPlanId("plan-1"),
            VisualSystemId("vs-1"),
            "out.zip",
        )


def test_plan_from_other_campaign_raises_invariant_violation() -> None:
    """Plan exists but belongs to a different campaign -> the
    use-case detects ``plan.campaign_id != campaign_id`` and raises
    ``InvariantViolation``. This guards against a caller that passes
    the wrong plan id."""
    piece1, _, item1, _ = _build_two_pieces()
    layouts = {"p-1": _layout_spec("p-1")}
    other_plan = _plan(
        campaign_id="c-OTHER",
        items=(item1,),
    )
    uc, _, _, _, _, _, _ = _use_case(
        pieces=(piece1,),
        plan_items=(item1,),
        layouts=layouts,
        plan=other_plan,
    )
    with pytest.raises(InvariantViolation):
        uc.execute(
            CampaignId("c-1"),
            CampaignPlanId("plan-1"),
            VisualSystemId("vs-1"),
            "out.zip",
        )


def test_missing_visual_system_raises_entity_not_found() -> None:
    piece1, _, item1, _ = _build_two_pieces()
    layouts = {"p-1": _layout_spec("p-1")}
    uc, _, _, _, _, _, _ = _use_case(
        pieces=(piece1,),
        plan_items=(item1,),
        layouts=layouts,
        visual_system=None,  # type: ignore[arg-type]
    )
    with pytest.raises(EntityNotFound):
        uc.execute(
            CampaignId("c-1"),
            CampaignPlanId("plan-1"),
            VisualSystemId("vs-1"),
            "out.zip",
        )


def test_telemetry_aggregates_provider_and_model() -> None:
    """``telemetry/ai_summary.json`` aggregates ``(provider, model)``
    across all revisions of all exported pieces. The aggregation is
    distinct (no duplicates in the lists) and the count is the
    TOTAL number of revisions with BOTH provider and model set.
    """
    piece1, _, item1, _ = _build_two_pieces()
    layouts = {"p-1": _layout_spec("p-1")}

    def _rev(rid: str, provider: str | None, model: str | None) -> Revision:
        return Revision(
            id=RevisionId(rid),
            entity_type="ContentPiece",
            entity_id="p-1",
            version=1,
            timestamp=_dt(),
            origin=RevisionOrigin.AI,
            previous_value="",
            new_value="",
            provider=provider,
            model=model,
            prompt_version=None,
            instruction=None,
        )

    # Two AI revisions on p-1 (one google, one openai), one with a
    # missing model (must be excluded from the count), one MANUAL
    # (must be excluded by the ``provider is not None AND model is
    # not None`` rule).
    revisions = {
        "p-1": (
            _rev("r-1", "google", "gemini-2.5-flash"),
            _rev("r-2", "openai", "gpt-4o-mini"),
            _rev("r-3", "google", None),  # model missing -> skip
            _rev("r-4", None, None),       # manual/system  -> skip
        ),
    }

    uc, _, _, _, _, _, writer = _use_case(
        pieces=(piece1,),
        plan_items=(item1,),
        layouts=layouts,
        revisions=revisions,
    )
    uc.execute(
        CampaignId("c-1"),
        CampaignPlanId("plan-1"),
        VisualSystemId("vs-1"),
        "out.zip",
    )

    summary = json.loads(writer.last_files["telemetry/ai_summary.json"])
    assert summary["content_piece_count"] == 1
    assert summary["ai_call_count"] == 2
    assert summary["providers_used"] == ["google", "openai"]
    assert summary["models_used"] == ["gemini-2.5-flash", "gpt-4o-mini"]
    # The "token/cost gap" note is mandatory — the spec requires it
    # to be present and explicit, not an invented zero. The
    # production string is mixed-case ("nisu dostupne"); we assert
    # case-insensitively so a future rephrase of the note (e.g.
    # "NISU" or "Nisu") does not break the test.
    note_lower = summary["note"].lower()
    assert "token/cost/latency" in note_lower
    assert "nisu" in note_lower
    assert "nije propust" in note_lower


def test_campaign_json_has_no_secrets() -> None:
    """``campaign.json`` is built from the campaign + brief + plan +
    exported piece ids. It must contain NO API-key / Secret-shaped
    value. This is a smoke test — the real protection is that
    ``ExportCampaign`` never imports ``SecretStore`` / keyring, but
    the JSON shape is also pinned here so a future "include provider
    key" optimisation is caught.
    """
    piece1, _, item1, _ = _build_two_pieces()
    layouts = {"p-1": _layout_spec("p-1")}

    uc, _, _, _, _, _, writer = _use_case(
        pieces=(piece1,),
        plan_items=(item1,),
        layouts=layouts,
    )
    uc.execute(
        CampaignId("c-1"),
        CampaignPlanId("plan-1"),
        VisualSystemId("vs-1"),
        "out.zip",
    )

    campaign_json_str = writer.last_files["campaign.json"].decode("utf-8")
    # A few heuristic patterns that would catch an accidental secret
    # leak; the use-case does not import SecretStore at all, but a
    # future PR could regress this.
    for forbidden in (
        "sk-",         # OpenAI-style
        "sk_live_",    # generic
        "api_key",
        "secret",
        "password",
        "token",
    ):
        assert forbidden not in campaign_json_str.lower(), (
            f"campaign.json must not contain {forbidden!r}"
        )


def test_export_writer_received_zip_bytes_are_valid_zip(
    tmp_path: Path,
) -> None:
    """Round-trip check at the unit tier: re-open the ``files`` dict
    in memory by writing it through the real ``zipfile`` module and
    confirm every entry survives. Catches a regression where the
    use-case accidentally double-encodes the bytes (e.g. base64)
    before handing them to the writer.
    """
    from ai_campaign_studio.infrastructure.export import ZipExportWriter

    piece1, piece2, item1, item2 = _build_two_pieces()
    layouts = {"p-1": _layout_spec("p-1"), "p-2": _layout_spec("p-2")}

    # Swap in the REAL stdlib writer so the ZIP ends up on disk and
    # can be re-opened via ``zipfile.ZipFile`` (the recording fake
    # only captures the dict, which is exactly what we DO NOT want
    # to test here).
    uc, _, _, _, _, _, _ = _use_case(
        pieces=(piece1, piece2),
        plan_items=(item1, item2),
        layouts=layouts,
        writer=ZipExportWriter(),
    )
    out = tmp_path / "round-trip.zip"
    uc.execute(
        CampaignId("c-1"),
        CampaignPlanId("plan-1"),
        VisualSystemId("vs-1"),
        str(out),
    )
    # ``out`` is a real ZIP on disk. Re-open and verify.
    with zipfile.ZipFile(out, mode="r") as zf:
        assert "campaign.json" in zf.namelist()
        assert "content-01/feed.png" in zf.namelist()
        assert "content-02/feed.png" in zf.namelist()
        assert json.loads(zf.read("campaign.json"))["content_piece_ids"] == [
            "p-1",
            "p-2",
        ]


def test_export_manifest_contains_stable_ids() -> None:
    piece1, piece2, item1, item2 = _build_two_pieces()
    layouts = {"p-1": _layout_spec("p-1"), "p-2": _layout_spec("p-2")}
    uc, _, _, _, _, _, writer = _use_case(
        pieces=(piece1, piece2), plan_items=(item1, item2), layouts=layouts
    )
    uc.execute(
        CampaignId("c-1"),
        CampaignPlanId("plan-1"),
        VisualSystemId("vs-1"),
        "out.zip",
    )
    manifest = json.loads(writer.last_files["manifest.json"])
    assert manifest["campaign_id"] == "c-1"
    assert manifest["campaign_plan_id"] == "plan-1"
    assert [i["campaign_item_id"] for i in manifest["items"]] == [
        "item-1",
        "item-2",
    ]
    assert [i["content_piece_id"] for i in manifest["items"]] == [
        "p-1",
        "p-2",
    ]


def test_export_manifest_contains_content_revision_id() -> None:
    piece1 = _piece("p-1", "item-1", revision_ids=(RevisionId("rev-42"),))
    item1 = _item("item-1", order=1)
    layouts = {"p-1": _layout_spec("p-1")}
    uc, _, _, _, _, _, writer = _use_case(
        pieces=(piece1,), plan_items=(item1,), layouts=layouts
    )
    uc.execute(
        CampaignId("c-1"),
        CampaignPlanId("plan-1"),
        VisualSystemId("vs-1"),
        "out.zip",
    )
    manifest = json.loads(writer.last_files["manifest.json"])
    assert manifest["items"][0]["content_revision_id"] == "rev-42"


def test_export_manifest_contains_target_identity() -> None:
    piece1, _, item1, _ = _build_two_pieces()
    layouts = {"p-1": _layout_spec("p-1")}
    uc, _, _, _, _, _, writer = _use_case(
        pieces=(piece1,), plan_items=(item1,), layouts=layouts
    )
    uc.execute(
        CampaignId("c-1"),
        CampaignPlanId("plan-1"),
        VisualSystemId("vs-1"),
        "out.zip",
    )
    manifest = json.loads(writer.last_files["manifest.json"])
    item = manifest["items"][0]
    assert item["channel_code"] == "SOCIAL"
    assert item["platform_code"] == "INSTAGRAM"
    assert item["format_code"] == "FEED_POST"


def test_manifest_has_schema_version() -> None:
    piece1, _, item1, _ = _build_two_pieces()
    layouts = {"p-1": _layout_spec("p-1")}
    uc, _, _, _, _, _, writer = _use_case(
        pieces=(piece1,), plan_items=(item1,), layouts=layouts
    )
    uc.execute(
        CampaignId("c-1"),
        CampaignPlanId("plan-1"),
        VisualSystemId("vs-1"),
        "out.zip",
    )
    manifest = json.loads(writer.last_files["manifest.json"])
    assert manifest["schema_version"] == 1


def test_piece_without_revision_raises_invariant() -> None:
    piece1 = _piece("p-1", "item-1", revision_ids=())
    item1 = _item("item-1", order=1)
    layouts = {"p-1": _layout_spec("p-1")}
    uc, _, _, _, _, _, _ = _use_case(
        pieces=(piece1,), plan_items=(item1,), layouts=layouts
    )
    with pytest.raises(InvariantViolation):
        uc.execute(
            CampaignId("c-1"),
            CampaignPlanId("plan-1"),
            VisualSystemId("vs-1"),
            "out.zip",
        )
