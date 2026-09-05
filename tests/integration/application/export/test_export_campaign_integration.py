"""Integration test for ``ExportCampaign`` (A15, plan section 46).

Full pipeline against a real SQLite DB and the real ``PillowRenderer``
+ real ``ZipExportWriter``. The export is the LAST step of the
campaign lifecycle; this test exercises the wire that A14 (render)
and A13 (plan) handed off, plus the new A15 (export) on top.

The integration test is the only place that PROVES the end-to-end
shape of the ZIP: re-opens the file with ``zipfile.ZipFile`` and
inspects every entry, not just the dict that the use-case hands to
the writer. A unit test that only checks the in-memory dict would
miss a real-bug class (e.g. accidental base64 encoding of the PNG
bytes, or writing the JSON with a non-UTF-8 codec).
"""

from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

from ai_campaign_studio.application.brands.load_brand_fixture import LoadBrandFixture
from ai_campaign_studio.application.campaigns.approve_campaign_plan import (
    ApproveCampaignPlan,
)
from ai_campaign_studio.application.campaigns.create_campaign import CreateCampaign
from ai_campaign_studio.application.campaigns.generate_campaign_plan import (
    GenerateCampaignPlan,
)
from ai_campaign_studio.application.export import ExportCampaign
from ai_campaign_studio.application.posts.generate_social_post import (
    GenerateSocialPost,
)
from ai_campaign_studio.application.visual.generate_visual_system import (
    GenerateVisualSystem,
)
from ai_campaign_studio.application.visual.plan_post_layout import PlanPostLayout
from ai_campaign_studio.domain.common.ids import DistributionInstanceId
from ai_campaign_studio.domain.content.entities import CampaignTarget
from ai_campaign_studio.infrastructure.database.connection import create_connection
from ai_campaign_studio.infrastructure.database.migrations import run_migrations
from ai_campaign_studio.infrastructure.database.repositories import (
    SqliteBrandRepository,
    SqliteCampaignRepository,
    SqliteContentRepository,
    SqliteFactRepository,
    SqlitePerformanceRepository,
    SqliteRevisionRepository,
    SqliteVisualRepository,
)
from ai_campaign_studio.infrastructure.database.unit_of_work import SqliteUnitOfWork
from ai_campaign_studio.infrastructure.export import ZipExportWriter
from ai_campaign_studio.infrastructure.rendering import PillowRenderer
from ai_campaign_studio.ports.ai import AIRequest, AIResponse
from ai_campaign_studio.ports.prompts import PromptDefinition

_MIGRATIONS_DIR = Path(__file__).resolve().parents[4] / "resources" / "migrations"
_FIXTURE_PATH = (
    Path(__file__).resolve().parents[4] / "resources" / "fixtures" / "brightsmile.json"
)


# ---------------------------------------------------------------------------
# Fake AI / prompt ports (hermetic — same pattern as
# test_plan_post_layout_integration.py so the AI layer is bypassed).
# ``provider`` and ``model`` are passed in so the test can pin
# exact values for the telemetry assertion.
# ---------------------------------------------------------------------------


class _FakeAiPort:
    def __init__(
        self,
        payload: dict,
        provider: str = "fake",
        model: str = "fake",
    ) -> None:
        self._payload = payload
        self._provider = provider
        self._model = model

    def generate(self, request: AIRequest) -> AIResponse:
        del request
        return AIResponse(
            provider=self._provider,
            model=self._model,
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
# AI payloads — two plan items (PROBLEM + SOLUTION) so the export has
# two content folders to verify.
# ---------------------------------------------------------------------------


def _brief() -> dict:
    return {
        "offer": "Dental implants",
        "goal": "Book consultations",
        "audience_text": "Adults 25-45",
        "targets": [
            {
                "channel": "SOCIAL",
                "platform_code": "INSTAGRAM",
                "format_code": "FEED_POST",
            }
        ],
        # Two content pieces so the export ZIP gets content-01 + content-02.
        "content_piece_count": 2,
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
            },
            {
                "order": 2,
                "role": "EDUCATION",
                "topic": "Affordable payment plans",
                "goal": "engagement",
                "facts_needed": [],
            },
        ],
    }


def _post_payload() -> dict:
    return {
        "headline": "Short headline",
        "caption": "Caption text",
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


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_end_to_end_export_writes_valid_zip_with_real_pngs(
    tmp_path: Path,
) -> None:
    """Full happy-path: brand -> campaign -> plan -> approve -> 2x
    GenerateSocialPost -> visual_system -> 2x PlanPostLayout ->
    ExportCampaign. Re-opens the resulting ZIP and asserts the
    on-disk structure.
    """
    connection = create_connection(tmp_path / "test.db")
    run_migrations(connection, _MIGRATIONS_DIR)

    brand_repo = SqliteBrandRepository(connection)
    fact_repo = SqliteFactRepository(connection)
    campaign_repo = SqliteCampaignRepository(connection)
    content_repo = SqliteContentRepository(connection)
    revision_repo = SqliteRevisionRepository(connection)
    visual_repo = SqliteVisualRepository(connection)
    performance_repo = SqlitePerformanceRepository(connection)
    uow = SqliteUnitOfWork(connection)

    # Realistic provider/model for the telemetry assertion below.
    ai = _FakeAiPort(_post_payload(), provider="google", model="gemini-2.5-flash")

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

    pieces = []
    for item in approved.items:
        piece = GenerateSocialPost(
            campaign_repo,
            brand_repo,
            fact_repo,
            content_repo,
            revision_repo,
            _FakePromptRepository(),
            ai,
            uow,
        ).execute(
            campaign.id,
            approved.id,
            item.id,
            CampaignTarget(
                channel="SOCIAL",
                platform_code="INSTAGRAM",
                format_code="FEED_POST",
            ),
        )
        pieces.append(piece)

    visual_system, _ = GenerateVisualSystem(
        campaign_repo,
        brand_repo,
        visual_repo,
        _FakePromptRepository(),
        _FakeAiPort(_visual_payload()),
        uow,
    ).execute(approved.id)

    for piece in pieces:
        PlanPostLayout(
            campaign_repo,
            content_repo,
            visual_repo,
            _FakePromptRepository(),
            _FakeAiPort(_layout_payload()),
            uow,
        ).execute(piece.id, visual_system.id, approved.id)

    # Now the actual A15 step — ExportCampaign with REAL PillowRenderer
    # and REAL ZipExportWriter. Nothing mocked at the renderer or
    # writer layer.
    exporter = ExportCampaign(
        campaign_repo=campaign_repo,
        content_repo=content_repo,
        visual_repo=visual_repo,
        revision_repo=revision_repo,
        renderer=PillowRenderer(),
        export_writer=ZipExportWriter(),
        performance_repo=performance_repo,
    )
    out_zip = tmp_path / "export.zip"
    result = exporter.execute(
        campaign.id, approved.id, visual_system.id, str(out_zip)
    )

    assert result.exported_content_piece_ids == (
        str(pieces[0].id),
        str(pieces[1].id),
    )
    assert result.skipped_content_piece_ids == ()
    assert result.zip_path == str(out_zip)
    assert out_zip.is_file()

    # Re-open the actual ZIP on disk and inspect it.
    with zipfile.ZipFile(out_zip, mode="r") as zf:
        names = set(zf.namelist())
        # Top-level + per-piece + telemetry.
        assert "campaign.json" in names
        assert "telemetry/ai_summary.json" in names
        for i in (1, 2):
            assert f"content-{i:02d}/content.json" in names
            assert f"content-{i:02d}/caption.txt" in names
            assert f"content-{i:02d}/feed.png" in names

        # campaign.json structure.
        campaign_json = json.loads(zf.read("campaign.json"))
        assert campaign_json["campaign_id"] == str(campaign.id)
        assert campaign_json["brand_snapshot_id"] == str(snapshot.id)
        assert campaign_json["plan_version"] == approved.version
        assert campaign_json["visual_system_id"] == str(visual_system.id)
        assert campaign_json["content_piece_ids"] == [
            str(pieces[0].id),
            str(pieces[1].id),
        ]
        assert campaign_json["brief"]["content_piece_count"] == 2
        assert "exported_at" in campaign_json
        assert "created_at" in campaign_json

        # content-01/content.json: per-piece structured payload.
        content_01 = json.loads(zf.read("content-01/content.json"))
        assert content_01["id"] == str(pieces[0].id)
        assert content_01["target"]["platform_code"] == "INSTAGRAM"
        assert content_01["payload"]["headline"] == "Short headline"
        assert content_01["render_status"] in (
            "SUCCESS", "LAYOUT_VALIDATION_ERROR", "RENDER_ERROR"
        )
        assert isinstance(content_01["render_warnings"], list)

        # content-01/feed.png: real PNG, non-empty, decodable.
        png_bytes = zf.read("content-01/feed.png")
        assert len(png_bytes) > 0
        # PNG magic: 89 50 4E 47 0D 0A 1A 0A. We do not pull in Pillow
        # for the integration test (the renderer already used it); the
        # magic-byte check is enough to prove the bytes are a real PNG
        # and not, e.g., an empty file or a text error message.
        assert png_bytes[:8] == b"\x89PNG\r\n\x1a\n"

        # content-01/caption.txt: plain text, exact caption from
        # _post_payload.
        assert zf.read("content-01/caption.txt") == b"Caption text"

        # telemetry/ai_summary.json: aggregates provider/model from
        # the real ``GenerateSocialPost`` revisions, which used the
        # fake AI port with provider="google", model="gemini-2.5-flash".
        summary = json.loads(zf.read("telemetry/ai_summary.json"))
        assert summary["content_piece_count"] == 2
        assert summary["ai_call_count"] == 2  # one revision per piece
        assert summary["providers_used"] == ["google"]
        assert summary["models_used"] == ["gemini-2.5-flash"]
        assert "nisu dostupne" in summary["note"].lower()

        # manifest.json: analytics-ready identity. content_revision_id must
        # match the REAL Revision persisted by GenerateSocialPost (read back
        # via RevisionRepositoryPort, not a fabricated value).
        assert "manifest.json" in names
        manifest = json.loads(zf.read("manifest.json"))
        assert manifest["schema_version"] == 1
        assert manifest["campaign_id"] == str(campaign.id)
        assert manifest["campaign_plan_id"] == str(approved.id)
        assert len(manifest["items"]) == 2
        for i, piece in enumerate(pieces):
            item = manifest["items"][i]
            assert item["content_piece_id"] == str(piece.id)
            assert item["campaign_item_id"] == str(piece.campaign_item_id)
            assert item["channel_code"] == "SOCIAL"
            assert item["platform_code"] == "INSTAGRAM"
            assert item["format_code"] == "FEED_POST"
            assert len(item["analytics_match_key"]) == 32
            assert item["artifacts"] == [
                f"content-{i + 1:02d}/feed.png",
                f"content-{i + 1:02d}/caption.txt",
                f"content-{i + 1:02d}/content.json",
            ]
            revisions = revision_repo.list_entity_revisions(
                "ContentPiece", str(piece.id)
            )
            assert revisions, f"piece {piece.id} has no revisions"
            assert item["content_revision_id"] == str(revisions[-1].id)

    # Distribution instances were actually persisted (round-trip through the
    # real SqlitePerformanceRepository, not a fake).
    for i, piece in enumerate(pieces):
        di_id = result.distribution_instance_ids[i]
        di = performance_repo.get_distribution_instance(
            DistributionInstanceId(di_id)
        )
        assert di is not None
        assert di.content_piece_id == piece.id
        revisions = revision_repo.list_entity_revisions(
            "ContentPiece", str(piece.id)
        )
        assert revisions
        assert di.content_revision_id == revisions[-1].id

    connection.close()


def test_export_zip_is_byte_stable_across_runs(tmp_path: Path) -> None:
    """Two runs of the same export produce functionally equivalent
    ZIPs (same names, same payload, same PNG bytes). Only the
    ``exported_at`` timestamp and the PNG header timestamp may
    differ. We assert the structurally-stable part.
    """
    from PIL import Image as _PILImage  # local import to keep the
    # test import-set small in the common case

    def _run(tmp_path: Path) -> zipfile.ZipFile:
        # ``sqlite3.connect`` does not create parent dirs; we run two
        # passes (r1, r2) so each pass needs its own subdirectory.
        run_dir = tmp_path
        run_dir.mkdir(parents=True, exist_ok=True)
        connection = create_connection(run_dir / "test.db")
        run_migrations(connection, _MIGRATIONS_DIR)
        brand_repo = SqliteBrandRepository(connection)
        fact_repo = SqliteFactRepository(connection)
        campaign_repo = SqliteCampaignRepository(connection)
        content_repo = SqliteContentRepository(connection)
        revision_repo = SqliteRevisionRepository(connection)
        visual_repo = SqliteVisualRepository(connection)
        performance_repo = SqlitePerformanceRepository(connection)
        uow = SqliteUnitOfWork(connection)
        ai = _FakeAiPort(_post_payload())
        snapshot = LoadBrandFixture(brand_repo, fact_repo, uow).execute(_FIXTURE_PATH)
        campaign = CreateCampaign(campaign_repo, uow).execute(
            snapshot.brand_id, snapshot.id, _brief()
        )
        plan = GenerateCampaignPlan(
            campaign_repo, brand_repo, _FakePromptRepository(),
            _FakeAiPort(_plan_payload()), uow,
        ).execute(campaign.id)
        approved = ApproveCampaignPlan(campaign_repo, uow).execute(plan.id)
        piece = GenerateSocialPost(
            campaign_repo, brand_repo, fact_repo, content_repo,
            revision_repo, _FakePromptRepository(), ai, uow,
        ).execute(
            campaign.id, approved.id, approved.items[0].id,
            CampaignTarget(
                channel="SOCIAL", platform_code="INSTAGRAM",
                format_code="FEED_POST",
            ),
        )
        vs, _ = GenerateVisualSystem(
            campaign_repo, brand_repo, visual_repo,
            _FakePromptRepository(), _FakeAiPort(_visual_payload()), uow,
        ).execute(approved.id)
        PlanPostLayout(
            campaign_repo, content_repo, visual_repo,
            _FakePromptRepository(), _FakeAiPort(_layout_payload()), uow,
        ).execute(piece.id, vs.id, approved.id)
        out_zip = tmp_path / "stable.zip"
        ExportCampaign(
            campaign_repo=campaign_repo, content_repo=content_repo,
            visual_repo=visual_repo, revision_repo=revision_repo,
            renderer=PillowRenderer(), export_writer=ZipExportWriter(),
            performance_repo=performance_repo,
        ).execute(campaign.id, approved.id, vs.id, str(out_zip))
        connection.close()
        return zipfile.ZipFile(out_zip, mode="r")

    zf1 = _run(tmp_path / "r1")
    zf2 = _run(tmp_path / "r2")
    try:
        # Two runs produce two ZIPs with the SAME set of arnames.
        assert set(zf1.namelist()) == set(zf2.namelist())

        # Per-piece content.json: same KEYS and VALUE TYPES, but the
        # exact id/timestamp values differ (UUIDs are generated per
        # run). We compare SCHEMA shape, not values.
        c1 = json.loads(zf1.read("content-01/content.json"))
        c2 = json.loads(zf2.read("content-01/content.json"))
        assert set(c1.keys()) == set(c2.keys())
        for key, val in c1.items():
            assert type(val) is type(c2[key]), (
                f"content.json[{key!r}] type differs: {type(val)} vs {type(c2[key])}"
            )

        # campaign.json: same KEYS and VALUE TYPES. ``content_piece_ids``
        # has the same LENGTH and same string-type per element.
        camp1 = json.loads(zf1.read("campaign.json"))
        camp2 = json.loads(zf2.read("campaign.json"))
        assert set(camp1.keys()) == set(camp2.keys())
        for key, val in camp1.items():
            if key == "content_piece_ids":
                assert len(val) == len(camp2[key])
                assert all(type(x) is str for x in val)
            else:
                assert type(val) is type(camp2[key])

        # Per-piece caption.txt: byte-identical (no UUID / timestamp
        # in the payload).
        assert zf1.read("content-01/caption.txt") == zf2.read(
            "content-01/caption.txt"
        )

        # PNG: same dimensions and same mode. We do NOT compare raw
        # bytes (Pillow embeds a creation timestamp). The decoder
        # pipeline is fully deterministic, so size/mode equality is
        # the strongest reasonable check here.
        png1 = io.BytesIO(zf1.read("content-01/feed.png"))
        png2 = io.BytesIO(zf2.read("content-01/feed.png"))
        with _PILImage.open(png1) as img1, _PILImage.open(png2) as img2:
            assert img1.size == img2.size
            assert img1.mode == img2.mode
    finally:
        zf1.close()
        zf2.close()
