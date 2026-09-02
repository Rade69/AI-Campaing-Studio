"""Brand fixture boundary schema (A4).

Owns the Pydantic models that validate a brand fixture JSON document. This is
a boundary: Pydantic is correct here, while the domain layer stays plain
dataclasses. Mapping to domain objects lives in
``application/mappers/brand_fixture_mapper.py``.
"""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

from ai_campaign_studio.localization.language_context import ContentLanguageContext


class BrandInfoSchema(BaseModel):
    """Top-level brand identity from the fixture."""

    name: str


class BrandVoiceSchema(BaseModel):
    """Fixture shape mirroring the domain ``BrandVoice`` fields."""

    formality: str
    tone: tuple[str, ...] = ()
    preferred_terms: tuple[str, ...] = ()
    forbidden_terms: tuple[str, ...] = ()
    regional_vocabulary: tuple[str, ...] = ()
    tone_examples: tuple[str, ...] = ()


class AudienceSchema(BaseModel):
    """Fixture shape mirroring the domain ``Audience`` fields."""

    id: str
    name: str
    description: str
    needs: tuple[str, ...] = ()
    objections: tuple[str, ...] = ()


class ServiceDefinitionSchema(BaseModel):
    """Fixture shape mirroring the domain ``ServiceDefinition`` fields."""

    id: str
    name: str
    description: str


class RestrictionSchema(BaseModel):
    """Fixture shape mirroring the domain ``Restriction`` fields."""

    description: str


class VisualIdentitySchema(BaseModel):
    """Fixture shape mirroring the domain ``VisualIdentity`` fields."""

    logo_path: str | None = None
    primary_colors: tuple[str, ...] = ()
    secondary_colors: tuple[str, ...] = ()
    font_families: tuple[str, ...] = ()
    image_style_notes: tuple[str, ...] = ()


class SourceReferenceSchema(BaseModel):
    """Fixture provenance reference for a single fact."""

    source_type: str = Field(min_length=1)
    uri: str = Field(min_length=1)
    snapshot_id: str | None = None
    chunk_id: str | None = None


class FactSchema(BaseModel):
    """A single fixture fact (source_ref is mandatory)."""

    logical_fact_id: str
    version: int
    content: str
    source_ref: SourceReferenceSchema


class BrandFixtureSchema(BaseModel):
    """Validated brand fixture document."""

    brand: BrandInfoSchema
    default_content_language_context: ContentLanguageContext
    voice: BrandVoiceSchema
    audiences: list[AudienceSchema]
    services: list[ServiceDefinitionSchema]
    facts: list[FactSchema]
    restrictions: list[RestrictionSchema] = Field(default_factory=list)
    visual_identity: VisualIdentitySchema

    @model_validator(mode="after")
    def _validate_facts(self) -> BrandFixtureSchema:
        if not self.facts:
            raise ValueError("fixture must contain at least one fact")
        logical_ids = [fact.logical_fact_id for fact in self.facts]
        if len(logical_ids) != len(set(logical_ids)):
            raise ValueError("logical_fact_id must be unique within a fixture")
        return self
