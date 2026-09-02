"""Unit tests for brand value objects (A3)."""

from dataclasses import FrozenInstanceError

import pytest

from ai_campaign_studio.domain.brand.value_objects import (
    Audience,
    BrandVoice,
    Restriction,
    ServiceDefinition,
    VisualIdentity,
)


def test_brand_voice_uses_tuple_collections() -> None:
    voice = BrandVoice(
        formality="friendly",
        tone=["warm", "clear"],
        preferred_terms=["implant"],
        forbidden_terms=["cheap"],
        regional_vocabulary=["stomatolog"],
        tone_examples=["We care."],
    )
    assert isinstance(voice.tone, tuple)
    assert isinstance(voice.preferred_terms, tuple)
    assert isinstance(voice.forbidden_terms, tuple)
    assert isinstance(voice.regional_vocabulary, tuple)
    assert isinstance(voice.tone_examples, tuple)
    assert voice.tone == ("warm", "clear")


def test_brand_voice_is_frozen() -> None:
    voice = BrandVoice(formality="friendly")
    with pytest.raises(FrozenInstanceError):
        voice.formality = "formal"


def test_audience_is_frozen() -> None:
    audience = Audience(id="a1", name="Young adults", description="18-30")
    assert audience.needs == ()
    assert audience.objections == ()
    with pytest.raises(FrozenInstanceError):
        audience.name = "changed"


def test_service_definition_is_frozen() -> None:
    service = ServiceDefinition(id="s1", name="Implantology", description="...")
    with pytest.raises(FrozenInstanceError):
        service.description = "changed"


def test_restriction_is_frozen() -> None:
    restriction = Restriction(description="Do not guarantee medical outcomes.")
    with pytest.raises(FrozenInstanceError):
        restriction.description = "changed"


def test_visual_identity_defaults_and_frozen() -> None:
    identity = VisualIdentity()
    assert identity.logo_path is None
    assert identity.primary_colors == ()
    assert identity.secondary_colors == ()
    assert identity.font_families == ()
    assert identity.image_style_notes == ()
    with pytest.raises(FrozenInstanceError):
        identity.primary_colors = ("#000000",)
