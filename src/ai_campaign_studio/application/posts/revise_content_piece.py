"""ReviseContentPiece use-case (A12 dio 2, plan section 38).

Owns revising an existing social post: validate the revision scope, call the
AI for a partial-field change, re-lint the existing claims, derive the status
(APPROVED always returns to NEEDS_REVIEW), and persist the Revision + updated
ContentPiece atomically. Depends only on ports.
"""

from __future__ import annotations

import json
from dataclasses import asdict, replace
from pathlib import Path
from typing import Protocol

from ai_campaign_studio.application.posts.claim_linter import (
    lint_claim,
    load_claim_rules,
)
from ai_campaign_studio.application.posts.derive_content_status import (
    derive_content_status,
)
from ai_campaign_studio.application.schemas.revision_output import RevisionOutput
from ai_campaign_studio.domain.common.errors import EntityNotFound, InvariantViolation
from ai_campaign_studio.domain.common.ids import PostId, RevisionId, new_id
from ai_campaign_studio.domain.common.timestamps import utc_now
from ai_campaign_studio.domain.content.entities import ContentPiece, SocialPostPayload
from ai_campaign_studio.domain.content.enums import ContentStatus
from ai_campaign_studio.domain.content.revisions import (
    Revision,
    RevisionOrigin,
    RevisionType,
)
from ai_campaign_studio.domain.facts.entities import ApprovedFact
from ai_campaign_studio.ports.ai import AIRequest, TextGenerationPort
from ai_campaign_studio.ports.prompts import PromptRepositoryPort
from ai_campaign_studio.ports.repositories import (
    ContentRepositoryPort,
    FactRepositoryPort,
    RevisionRepositoryPort,
)

_PROMPT_NAME = "revision"
_PROMPT_VERSION = "1"
_CLAIM_RULES_PATH = (
    Path(__file__).resolve().parents[4]
    / "resources"
    / "claim_rules"
    / "default_v1.yaml"
)

_ALLOWED_FIELDS: dict[RevisionType, frozenset[str]] = {
    RevisionType.NEW_HEADLINE: frozenset({"headline"}),
    RevisionType.NEW_CTA: frozenset({"cta"}),
    RevisionType.STRONGER_HOOK: frozenset({"hook"}),
    RevisionType.SHORTER: frozenset({"headline", "caption", "hook", "body"}),
    RevisionType.LONGER: frozenset({"headline", "caption", "hook", "body"}),
    RevisionType.MORE_PROFESSIONAL: frozenset({"headline", "caption", "hook", "body"}),
    RevisionType.MORE_FRIENDLY: frozenset({"headline", "caption", "hook", "body"}),
    RevisionType.LESS_PROMOTIONAL: frozenset(
        {"headline", "caption", "hook", "body", "cta"}
    ),
    RevisionType.CUSTOM: frozenset(
        {"headline", "caption", "hook", "body", "cta", "hashtags"}
    ),
    # NEW_VISUAL_DIRECTION is intentionally absent — rejected in execute().
}

_PAYLOAD_FIELDS = frozenset({"headline", "caption", "hook", "body", "cta", "hashtags"})


class _UnitOfWork(Protocol):
    """Minimal transaction boundary the use-case needs."""

    def __enter__(self) -> _UnitOfWork: ...

    def __exit__(
        self, exc_type: object, exc_value: object, traceback: object
    ) -> bool: ...

    def commit(self) -> None: ...


class ReviseContentPiece:
    """Revise an existing content piece according to an explicit command."""

    def __init__(
        self,
        content_repo: ContentRepositoryPort,
        fact_repo: FactRepositoryPort,
        revision_repo: RevisionRepositoryPort,
        prompt_repo: PromptRepositoryPort,
        ai_port: TextGenerationPort,
        unit_of_work: _UnitOfWork,
    ) -> None:
        self._content_repo = content_repo
        self._fact_repo = fact_repo
        self._revision_repo = revision_repo
        self._prompt_repo = prompt_repo
        self._ai_port = ai_port
        self._unit_of_work = unit_of_work

    def execute(
        self,
        content_piece_id: PostId,
        revision_type: RevisionType,
        instruction: str,
    ) -> ContentPiece:
        piece = self._content_repo.get_content_piece(content_piece_id)
        if piece is None:
            raise EntityNotFound(f"content piece {content_piece_id} not found")

        if piece.payload is None:
            raise InvariantViolation(
                f"content piece {content_piece_id} has no payload to revise"
            )

        if revision_type is RevisionType.NEW_VISUAL_DIRECTION:
            raise InvariantViolation(
                "NEW_VISUAL_DIRECTION revision is not supported yet "
                "(Visual System pipeline is a later task)"
            )

        allowed_fields = _ALLOWED_FIELDS[revision_type]

        facts = _load_facts(piece, self._fact_repo)

        prompt = self._prompt_repo.get(_PROMPT_NAME, _PROMPT_VERSION)
        immutable_fields = sorted(_PAYLOAD_FIELDS - allowed_fields)
        request = AIRequest(
            purpose=_PROMPT_NAME,
            prompt_name=_PROMPT_NAME,
            prompt_version=_PROMPT_VERSION,
            system_text=prompt.instructions,
            user_text=_build_user_text(
                piece.payload, revision_type, instruction, immutable_fields, facts
            ),
            json_schema=RevisionOutput.model_json_schema(),
        )

        response = self._ai_port.generate(request)
        if response.structured_payload is None:
            raise InvariantViolation("AI response has no structured_payload")

        output = RevisionOutput.model_validate(response.structured_payload)

        out_of_scope = output.changed_fields - allowed_fields
        if out_of_scope:
            raise InvariantViolation(
                f"revision changed fields outside the allowed set for "
                f"{revision_type.value}: {sorted(out_of_scope)}"
            )

        new_payload = _apply_changes(piece.payload, output)

        rules = load_claim_rules(_CLAIM_RULES_PATH)
        relinted_claims = tuple(
            lint_claim(claim, rules) for claim in piece.claims
        )

        natural_status = derive_content_status(relinted_claims)
        final_status = (
            ContentStatus.NEEDS_REVIEW
            if piece.status is ContentStatus.APPROVED
            else natural_status
        )

        existing = self._revision_repo.list_entity_revisions(
            "ContentPiece", str(content_piece_id)
        )
        next_version = len(existing) + 1

        revision = Revision(
            id=RevisionId(new_id()),
            entity_type="ContentPiece",
            entity_id=str(content_piece_id),
            version=next_version,
            timestamp=utc_now(),
            origin=RevisionOrigin.AI,
            previous_value=json.dumps(asdict(piece.payload)),
            new_value=json.dumps(asdict(new_payload)),
            provider=response.provider,
            model=response.model,
            prompt_version=_PROMPT_VERSION,
            instruction=f"[{revision_type.value}] {instruction}",
        )

        updated_piece = replace(
            piece,
            payload=new_payload,
            claims=relinted_claims,
            status=final_status,
            revision_ids=(*piece.revision_ids, revision.id),
            updated_at=utc_now(),
        )

        with self._unit_of_work:
            self._revision_repo.save_revision(revision)
            self._content_repo.save_content_piece(updated_piece)
            self._unit_of_work.commit()

        return updated_piece


def _load_facts(
    piece: ContentPiece, fact_repo: FactRepositoryPort
) -> tuple[ApprovedFact, ...]:
    facts: list[ApprovedFact] = []
    for fact_id in piece.facts_allowed:
        fact = fact_repo.get_fact(fact_id)
        if fact is not None:
            facts.append(fact)
    return tuple(facts)


def _apply_changes(
    payload: SocialPostPayload, output: RevisionOutput
) -> SocialPostPayload:
    """Apply only the explicitly-changed fields; skip explicit nulls.

    ``hashtags`` is coerced ``list -> tuple`` (the domain payload stores a
    tuple; explicit ``null`` for a field is treated as "no change").
    """
    changes: dict[str, object] = {}
    for field in output.changed_fields:
        value = getattr(output, field)
        if value is None:
            continue
        if field == "hashtags":
            value = tuple(value)  # type: ignore[arg-type]
        changes[field] = value
    return replace(payload, **changes)  # type: ignore[arg-type]


def _build_user_text(
    payload: SocialPostPayload,
    revision_type: RevisionType,
    instruction: str,
    immutable_fields: list[str],
    facts: tuple[ApprovedFact, ...],
) -> str:
    lines = [
        "## Current post",
        f"headline: {payload.headline}",
        f"caption: {payload.caption}",
        f"hook: {payload.hook}",
        f"body: {payload.body}",
        f"cta: {payload.cta}",
        "hashtags: " + ", ".join(payload.hashtags),
        "## Revision command",
        f"revision_type: {revision_type.value}",
        f"instruction: {instruction}",
        "## Immutable fields (must not change)",
        ", ".join(immutable_fields),
        "## Allowed facts",
    ]
    if facts:
        for fact in facts:
            lines.append(f"- [{fact.id}] {fact.content}")
    else:
        lines.append("(none)")
    return "\n".join(lines)
