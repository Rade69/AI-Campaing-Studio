"""``ExportCampaign`` use-case (A15, plan section 46).

Composes ``RenderPost`` (ACS-F1-033) for per-post PNG generation and
emits a self-contained ZIP archive with:

- ``campaign.json`` — campaign identity, brief, plan version, visual
  system, content_piece_ids in export order
- ``content-NN/content.json`` — per-piece structured payload (id, target,
  text fields, claims, render result, timestamps)
- ``content-NN/caption.txt`` — plain-text caption (for human review)
- ``content-NN/feed.png`` — rendered PNG bytes (from ``RenderPost``)
- ``telemetry/ai_summary.json`` — aggregated ``provider``/``model`` from
  the ``Revision`` records of each exported piece

The use-case is a pure orchestrator. It does NOT persist anything
itself — all writes go through ``ExportWriterPort.write_zip`` (which is
the only seam that touches the filesystem). Per-piece failures are
recorded in ``skipped_content_piece_ids``, never raised — a partial
export is a valid artifact.

Why ``RenderPost`` is composed inside instead of injected as a
dependency? The contract (plan §46) is explicit: "``ExportCampaign``
interno konstruiše ``RenderPost`` iz sirovih portova
(``content_repo``, ``campaign_repo``, ``visual_repo``, ``renderer``),
isti obrazac kao ``run_system_b.py``" — the use-case is a use-case
*orchestrator* of a small pipeline, not a peer of the renderer. Taking
``RenderPost`` as a constructor dep would conflate composition with
collaboration. The four raw ports are the actual collaborator surface.
"""

from __future__ import annotations

import json
import tempfile
from dataclasses import dataclass
from pathlib import Path

from ai_campaign_studio.application.rendering import RenderPost
from ai_campaign_studio.domain.analytics.match_key import compute_analytics_match_key
from ai_campaign_studio.domain.campaign.entities import (
    Campaign,
    CampaignBrief,
    CampaignPlan,
)
from ai_campaign_studio.domain.common.errors import (
    EntityNotFound,
    InvariantViolation,
)
from ai_campaign_studio.domain.common.ids import (
    CampaignId,
    CampaignPlanId,
    DistributionInstanceId,
    RevisionId,
    VisualSystemId,
    new_id,
)
from ai_campaign_studio.domain.common.timestamps import utc_now
from ai_campaign_studio.domain.content.entities import ContentPiece
from ai_campaign_studio.domain.performance.entities import DistributionInstance
from ai_campaign_studio.domain.performance.enums import DistributionSource
from ai_campaign_studio.ports.export import ExportResult, ExportWriterPort
from ai_campaign_studio.ports.rendering import RendererPort
from ai_campaign_studio.ports.repositories import (
    CampaignRepositoryPort,
    ContentRepositoryPort,
    PerformanceRepositoryPort,
    RevisionRepositoryPort,
    VisualRepositoryPort,
)


@dataclass(frozen=True)
class _PieceExport:
    """Internal: the per-piece artefacts assembled before writing.

    Kept as a small private dataclass so the per-piece loop stays
    readable. The public ``ExportResult`` exposes only the ids; the
    per-piece files are written once into the ZIP and not held in
    memory longer than necessary.
    """

    piece: ContentPiece
    folder_name: str   # e.g. "content-01"
    render_status: str
    render_warnings: tuple[str, ...]
    png_bytes: bytes


class ExportCampaign:
    """Bundle a campaign into a self-contained ZIP archive.

    Parameters mirror the union of read operations actually needed
    (``get_campaign``, ``get_brief``, ``get_plan``, ``get_visual_system``,
    ``list_campaign_content``, ``list_entity_revisions``) plus the two
    collaborators that do the heavy lifting:
    - ``renderer`` — a ``RendererPort`` (typically ``PillowRenderer``)
    - ``export_writer`` — an ``ExportWriterPort`` (typically
      ``ZipExportWriter``)

    Per the contract, ``plan_id`` and ``visual_system_id`` are passed
    as EXPLICIT parameters to ``execute()`` (same shape as
    ``PlanPostLayout.execute(plan_id=...)`` and
    ``RenderPost.execute(visual_system_id=...)``). The use-case never
    invents a "current plan" or "current visual system" lookup — the
    caller already has the ids from upstream steps.
    """

    def __init__(
        self,
        campaign_repo: CampaignRepositoryPort,
        content_repo: ContentRepositoryPort,
        visual_repo: VisualRepositoryPort,
        revision_repo: RevisionRepositoryPort,
        renderer: RendererPort,
        export_writer: ExportWriterPort,
        performance_repo: PerformanceRepositoryPort,
    ) -> None:
        self._campaign_repo = campaign_repo
        self._content_repo = content_repo
        self._visual_repo = visual_repo
        self._revision_repo = revision_repo
        self._renderer = renderer
        self._export_writer = export_writer
        self._performance_repo = performance_repo

    def execute(
        self,
        campaign_id: CampaignId,
        plan_id: CampaignPlanId,
        visual_system_id: VisualSystemId,
        output_zip_path: str,
    ) -> ExportResult:
        # 1-4. Load the four upstream artefacts; raise SPECIFIC
        #      EntityNotFound for each (one branch per upstream object,
        #      not a combined "any missing" branch — easier to debug,
        #      easier to test).
        campaign = self._load_campaign(campaign_id)
        brief = self._load_brief(campaign.brief_id)
        plan = self._load_plan(plan_id)
        if plan.campaign_id != campaign_id:
            raise InvariantViolation(
                f"plan {plan_id} belongs to campaign {plan.campaign_id},"
                f" not the requested campaign {campaign_id}"
            )
        self._load_visual_system(visual_system_id)

        # 5-6. Pull all pieces for this campaign and sort by their
        #      CampaignItem.order — NOT by the order the repository
        #      happens to return them. ``plan.items`` is the
        #      authoritative order for this plan; we map each piece to
        #      its item via ``campaign_item_id``.
        pieces = self._content_repo.list_campaign_content(campaign_id)
        ordered_pieces = self._order_pieces_by_plan(pieces, plan)

        # 7. Per-piece render. Each piece that succeeds becomes one
        #    folder (``content-01``, ``content-02``, ...). The counter
        #    counts ONLY exported pieces (per the contract: "računajući
        #    SAMO eksportovane — ne preskočene").
        exports: list[_PieceExport] = []
        skipped: list[str] = []
        for piece in ordered_pieces:
            folder_name = f"content-{len(exports) + 1:02d}"
            export, skip_id = self._render_one_piece(
                piece, visual_system_id, folder_name
            )
            if export is None:
                skipped.append(skip_id)
                continue
            exports.append(export)

        exported_ids = tuple(str(e.piece.id) for e in exports)

        # 8. manifest.json — analytics-ready per-item identity (Faza 1 v1.5
        #    §5). ``content_revision_id`` is the LATEST revision; a piece
        #    with no revision at all is a data-integrity bug (not a skip
        #    reason), so it raises ``InvariantViolation``.
        manifest_items = []
        distribution_instance_ids: list[str] = []
        for e in exports:
            content_revision_id = _latest_revision_id(e.piece)
            distribution_instance = DistributionInstance(
                id=DistributionInstanceId(new_id()),
                campaign_id=campaign.id,
                campaign_item_id=e.piece.campaign_item_id,
                content_piece_id=e.piece.id,
                content_revision_id=RevisionId(content_revision_id),
                channel_code=e.piece.target.channel,
                platform_code=e.piece.target.platform_code,
                format_code=e.piece.target.format_code,
                distribution_source=DistributionSource.EXPORT,
                created_at=utc_now(),
            )
            self._performance_repo.save_distribution_instance(
                distribution_instance
            )
            distribution_instance_ids.append(str(distribution_instance.id))
            manifest_items.append(
                {
                    "campaign_item_id": str(e.piece.campaign_item_id),
                    "content_piece_id": str(e.piece.id),
                    "content_revision_id": content_revision_id,
                    "channel_code": e.piece.target.channel,
                    "platform_code": e.piece.target.platform_code,
                    "format_code": e.piece.target.format_code,
                    "analytics_match_key": compute_analytics_match_key(
                        str(e.piece.id),
                        content_revision_id,
                        e.piece.target.platform_code,
                        e.piece.target.format_code,
                    ),
                    "artifacts": [
                        f"{e.folder_name}/feed.png",
                        f"{e.folder_name}/caption.txt",
                        f"{e.folder_name}/content.json",
                    ],
                }
            )
        manifest = {
            "schema_version": 1,
            "campaign_id": str(campaign.id),
            "campaign_plan_id": str(plan.id),
            "exported_at": utc_now().isoformat(),
            "items": manifest_items,
        }

        # 9. Telemetry aggregation: ``list_entity_revisions("ContentPiece", piece.id)``
        #    returns the audit trail. ONLY revisions that have BOTH
        #    ``provider`` and ``model`` set count (some are MANUAL or
        #    SYSTEM without AI attribution). The note is REQUIRED —
        #    token/cost/latency are NOT persisted anywhere in the
        #    system (Revision schema has no such columns), so the
        #    summary must declare the limitation instead of inventing
        #    numbers. This is the project-wide "fact-first/provenance"
        #    principle.
        ai_call_count = 0
        providers: set[str] = set()
        models: set[str] = set()
        for e in exports:
            for revision in self._revision_repo.list_entity_revisions(
                "ContentPiece", str(e.piece.id)
            ):
                if revision.provider is not None and revision.model is not None:
                    ai_call_count += 1
                    providers.add(revision.provider)
                    models.add(revision.model)
        ai_summary = {
            "content_piece_count": len(exports),
            "ai_call_count": ai_call_count,
            "providers_used": sorted(providers),
            "models_used": sorted(models),
            "note": (
                "Token/cost/latency metrike nisu dostupne — "
                "trenutno se ne perzistuju nigdje u sistemu (vidi "
                "Revision šemu). Ovo NIJE propust ovog exporta, "
                "nego postojeće ograničenje sistema."
            ),
        }

        # 10. campaign.json — campaign identity + brief + plan_version.
        #    ``content_piece_ids`` lists ONLY exported pieces, in the
        #    SAME order as the folders, so a downstream consumer can
        #    recover the export order without re-running the
        #    CampaignItem-order lookup.
        campaign_json = {
            "campaign_id": str(campaign.id),
            "brand_snapshot_id": str(campaign.brand_snapshot_id),
            "brief": {
                "offer": brief.offer,
                "goal": brief.goal,
                "audience_text": brief.audience_text,
                "content_piece_count": brief.content_piece_count,
                "content_language_context": brief.content_language_context,
            },
            "plan_version": plan.version,
            "visual_system_id": str(visual_system_id),
            "content_piece_ids": exported_ids,
            "created_at": campaign.created_at.isoformat(),
            "exported_at": utc_now().isoformat(),
        }

        # 11. Assemble the full files dict and write the ZIP.
        files: dict[str, bytes] = {
            "campaign.json": _json_bytes(campaign_json),
            "manifest.json": _json_bytes(manifest),
        }
        files["telemetry/ai_summary.json"] = _json_bytes(ai_summary)
        for e in exports:
            files[f"{e.folder_name}/content.json"] = _json_bytes(
                _content_json(e)
            )
            files[f"{e.folder_name}/caption.txt"] = (
                e.piece.payload.caption.encode("utf-8")  # type: ignore[union-attr]
            )
            files[f"{e.folder_name}/feed.png"] = e.png_bytes
        self._export_writer.write_zip(output_zip_path, files)

        return ExportResult(
            zip_path=output_zip_path,
            exported_content_piece_ids=exported_ids,
            skipped_content_piece_ids=tuple(skipped),
            distribution_instance_ids=tuple(distribution_instance_ids),
        )

    # -- helpers ------------------------------------------------------------

    def _load_campaign(self, campaign_id: CampaignId) -> Campaign:
        campaign = self._campaign_repo.get_campaign(campaign_id)
        if campaign is None:
            raise EntityNotFound(f"campaign {campaign_id} not found")
        return campaign

    def _load_brief(self, brief_id: str) -> CampaignBrief:
        brief = self._campaign_repo.get_brief(brief_id)
        if brief is None:
            raise EntityNotFound(f"brief {brief_id} not found")
        return brief

    def _load_plan(self, plan_id: CampaignPlanId) -> CampaignPlan:
        plan = self._campaign_repo.get_plan(plan_id)
        if plan is None:
            raise EntityNotFound(f"plan {plan_id} not found")
        return plan

    def _load_visual_system(self, visual_system_id: VisualSystemId) -> None:
        if self._visual_repo.get_visual_system(visual_system_id) is None:
            raise EntityNotFound(
                f"visual system {visual_system_id} not found"
            )

    def _order_pieces_by_plan(
        self,
        pieces: tuple[ContentPiece, ...],
        plan: CampaignPlan,
    ) -> tuple[ContentPiece, ...]:
        """Map each piece to its ``CampaignItem.order`` and sort.

        Pieces whose ``campaign_item_id`` is not in ``plan.items`` (e.g.
        a stale ContentPiece from a re-plan) are placed at the end in
        stable order. ``sorted`` is stable, so the within-bucket order
        matches the repository's return order — deterministic and
        reviewable.
        """
        order_by_item_id: dict[str, int] = {
            str(item.id): item.order for item in plan.items
        }
        # Default order for unmatched items: place AFTER all matched
        # items by using ``max(order) + 1`` (or 0 if plan is empty).
        fallback = (
            max(order_by_item_id.values(), default=0) + 1
            if order_by_item_id
            else 0
        )
        return tuple(
            sorted(
                pieces,
                key=lambda p: order_by_item_id.get(
                    str(p.campaign_item_id), fallback
                ),
            )
        )

    def _render_one_piece(
        self,
        piece: ContentPiece,
        visual_system_id: VisualSystemId,
        folder_name: str,
    ) -> tuple[_PieceExport | None, str]:
        """Render one piece to a temp PNG and return the export bundle.

        Returns ``(None, piece_id_str)`` if the piece was skipped
        (either no payload or no LayoutSpec); the caller records the id
        in ``skipped_content_piece_ids``. Returns
        ``(_PieceExport(...), piece_id_str)`` on success — the
        ``piece_id_str`` is duplicated in both branches so the loop
        doesn't have to extract it from the ``piece`` itself.

        Two SPECIFIC skip reasons (per contract):

        - ``piece.payload is None`` — the post was never generated or
          the payload was wiped during a destructive revision flow. No
          text to export, so the PNG would be empty.
        - ``RenderPost.execute`` raises ``EntityNotFound`` — the post
          was never put through ``PlanPostLayout`` (no LayoutSpec in
          the database). We catch THIS SPECIFIC EXCEPTION ONLY; any
          other failure (corrupt PNG, I/O error, schema bug) propagates
          so a future review can see the real cause instead of a
          silent skip.
        """
        if piece.payload is None:
            return None, str(piece.id)

        # Compose RenderPost from the four raw ports (contract: "interno
        # konstruiše RenderPost iz sirovih portova", NOT a constructor
        # dep).
        render_post = RenderPost(
            content_repo=self._content_repo,
            campaign_repo=self._campaign_repo,
            visual_repo=self._visual_repo,
            renderer=self._renderer,
        )

        # RenderPost takes a path on disk, not BytesIO. The contract is
        # explicit: "temp PNG putanja preko tempfile". Use
        # ``delete=False`` so the file survives the ``with`` block (we
        # need to read it after Pillow closes the handle), and clean up
        # explicitly in ``finally``.
        tmp_handle = tempfile.NamedTemporaryFile(
            prefix="acs-export-", suffix=".png", delete=False
        )
        tmp_path = tmp_handle.name
        tmp_handle.close()
        try:
            try:
                result = render_post.execute(
                    piece.id, visual_system_id, tmp_path
                )
            except EntityNotFound:
                # SPECIFIC skip: no LayoutSpec for this piece. Do NOT
                # catch broader Exception here — a real bug in
                # RenderPost or Pillow must propagate so a reviewer
                # sees the stack trace.
                return None, str(piece.id)

            png_bytes = Path(tmp_path).read_bytes()
            export = _PieceExport(
                piece=piece,
                folder_name=folder_name,
                render_status=result.status.value,
                render_warnings=result.warnings,
                png_bytes=png_bytes,
            )
            return export, str(piece.id)
        finally:
            # Best-effort cleanup; ignore failures (Windows holds the
            # file briefly after write close).
            try:
                Path(tmp_path).unlink()
            except OSError:
                pass


# -- module-level helpers ---------------------------------------------------


def _latest_revision_id(piece: ContentPiece) -> str:
    """Return the latest revision id for a piece, or raise.

    A piece with NO revision at all is a data-integrity bug (the current
    ``GenerateSocialPost`` always creates a Revision on first generation),
    not a normal "not ready yet" skip reason — so it raises
    ``InvariantViolation`` rather than silently exporting an un-identifiable
    item.
    """
    if not piece.revision_ids:
        raise InvariantViolation(
            f"content piece {piece.id} has no revisions — cannot derive"
            " content_revision_id for export"
        )
    return str(piece.revision_ids[-1])


def _json_bytes(obj: object) -> bytes:
    """Serialize ``obj`` to compact JSON bytes (UTF-8, no ASCII escape).

    ``ensure_ascii=False`` is essential: the caption and headline may
    contain BHS Latin diacritics (``č ć š đ ž``) which we want in the
    ZIP as-is, not as ``\\u0107`` escapes. ``sort_keys=True`` makes
    the JSON byte-stable across Python versions, which keeps the
    diff between two exports of the same campaign reviewable.
    """
    return json.dumps(
        obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _content_json(export: _PieceExport) -> dict:
    """Build the per-piece ``content.json`` dict.

    Mirrors the contract schema: id, campaign_item_id, target (channel/
    platform_code/format_code), payload (headline/caption/hook/body/cta/
    hashtags), status, claims (id/text/type/status/reason_codes/
    fact_ids), render_status, render_warnings, created_at, updated_at.
    ``piece.payload`` is guaranteed non-None here — the skip branch
    returns before we ever build a ``_PieceExport``.
    """
    payload = export.piece.payload
    assert payload is not None  # guarded by _render_one_piece
    return {
        "id": str(export.piece.id),
        "campaign_item_id": str(export.piece.campaign_item_id),
        "target": {
            "channel": export.piece.target.channel,
            "platform_code": export.piece.target.platform_code,
            "format_code": export.piece.target.format_code,
        },
        "payload": {
            "headline": payload.headline,
            "caption": payload.caption,
            "hook": payload.hook,
            "body": payload.body,
            "cta": payload.cta,
            "hashtags": list(payload.hashtags),
        },
        "status": export.piece.status.value,
        "claims": [
            {
                "id": c.id,
                "text": c.text,
                "type": c.type.value,
                "status": c.status.value,
                "reason_codes": list(c.reason_codes),
                "fact_ids": [str(fid) for fid in c.fact_ids],
            }
            for c in export.piece.claims
        ],
        "render_status": export.render_status,
        "render_warnings": list(export.render_warnings),
        "content_revision_id": _latest_revision_id(export.piece),
        "created_at": export.piece.created_at.isoformat(),
        "updated_at": export.piece.updated_at.isoformat(),
    }


__all__ = ["ExportCampaign"]
