"""Brand fixture mapper (A4).

Owns ``map_brand_fixture``: converts a validated ``BrandFixtureSchema`` into
the immutable domain objects (``Brand``, ``BrandSnapshot``, ``ApprovedFact``).
Pure in-memory transformation — no persistence, no mutation.
"""

from __future__ import annotations

from ai_campaign_studio.application.schemas.brand_fixture import BrandFixtureSchema
from ai_campaign_studio.domain.brand.entities import Brand, BrandSnapshot
from ai_campaign_studio.domain.brand.value_objects import (
    Audience,
    BrandVoice,
    Restriction,
    ServiceDefinition,
    VisualIdentity,
)
from ai_campaign_studio.domain.common.ids import (
    BrandId,
    BrandSnapshotId,
    FactId,
    new_id,
)
from ai_campaign_studio.domain.common.timestamps import utc_now
from ai_campaign_studio.domain.facts.entities import ApprovedFact, SourceReference
from ai_campaign_studio.domain.facts.enums import FactStatus


def map_brand_fixture(
    fixture: BrandFixtureSchema,
) -> tuple[Brand, BrandSnapshot, tuple[ApprovedFact, ...]]:
    """Map a validated fixture to immutable domain objects.

    Returns ``(brand, snapshot, facts)``. ``snapshot.approved_fact_ids`` is
    exactly the ids of the returned facts (same order, no loss or
    duplication). No SQLite/persistence call happens here — this is a pure
    in-memory transformation (persistence is A5).
    """
    now = utc_now()

    brand = Brand(
        id=BrandId(new_id()),
        name=fixture.brand.name,
        created_at=now,
    )

    facts = tuple(
        ApprovedFact(
            id=FactId(new_id()),
            logical_fact_id=fact.logical_fact_id,
            version=fact.version,
            content=fact.content,
            source_ref=SourceReference(
                source_type=fact.source_ref.source_type,
                uri=fact.source_ref.uri,
                snapshot_id=fact.source_ref.snapshot_id,
                chunk_id=fact.source_ref.chunk_id,
            ),
            status=FactStatus.APPROVED,
            created_at=now,
        )
        for fact in fixture.facts
    )

    voice = BrandVoice(
        formality=fixture.voice.formality,
        tone=fixture.voice.tone,
        preferred_terms=fixture.voice.preferred_terms,
        forbidden_terms=fixture.voice.forbidden_terms,
        regional_vocabulary=fixture.voice.regional_vocabulary,
        tone_examples=fixture.voice.tone_examples,
    )

    audiences = tuple(
        Audience(
            id=audience.id,
            name=audience.name,
            description=audience.description,
            needs=audience.needs,
            objections=audience.objections,
        )
        for audience in fixture.audiences
    )

    services = tuple(
        ServiceDefinition(
            id=service.id,
            name=service.name,
            description=service.description,
        )
        for service in fixture.services
    )

    restrictions = tuple(
        Restriction(description=restriction.description)
        for restriction in fixture.restrictions
    )

    visual_identity = VisualIdentity(
        logo_path=fixture.visual_identity.logo_path,
        primary_colors=fixture.visual_identity.primary_colors,
        secondary_colors=fixture.visual_identity.secondary_colors,
        font_families=fixture.visual_identity.font_families,
        image_style_notes=fixture.visual_identity.image_style_notes,
    )

    context = fixture.default_content_language_context

    snapshot = BrandSnapshot(
        id=BrandSnapshotId(new_id()),
        brand_id=brand.id,
        version=1,
        language=context.language_family.value,
        locale=context.locale.value,
        script=context.script.value,
        voice=voice,
        audiences=audiences,
        services=services,
        visual_identity=visual_identity,
        restrictions=restrictions,
        approved_fact_ids=tuple(fact.id for fact in facts),
        created_at=now,
    )

    return brand, snapshot, facts
