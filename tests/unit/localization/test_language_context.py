"""Tests for ``ContentLanguageContext`` invariants."""

import pytest
from pydantic import ValidationError

from ai_campaign_studio.localization.enums import (
    AppLocale,
    BHSRegionalVariant,
    ContentLanguageFamily,
    Script,
)
from ai_campaign_studio.localization.language_context import ContentLanguageContext


def _context(
    family: ContentLanguageFamily,
    variant: BHSRegionalVariant = BHSRegionalVariant.NEUTRAL,
    *,
    locale: AppLocale | None = None,
    script: Script = Script.LATIN,
) -> ContentLanguageContext:
    if locale is None:
        locale = (
            AppLocale.EN
            if family is ContentLanguageFamily.EN
            else AppLocale.BHS_LATIN
        )
    return ContentLanguageContext(
        language_family=family,
        regional_variant=variant,
        script=script,
        locale=locale,
    )


def test_en_neutral_is_valid() -> None:
    context = _context(ContentLanguageFamily.EN, BHSRegionalVariant.NEUTRAL)
    assert context.language_family is ContentLanguageFamily.EN
    assert context.regional_variant is BHSRegionalVariant.NEUTRAL
    assert context.script is Script.LATIN


def test_en_with_regional_variant_is_invalid() -> None:
    with pytest.raises(ValidationError):
        _context(ContentLanguageFamily.EN, BHSRegionalVariant.BS)


@pytest.mark.parametrize(
    "variant",
    [
        BHSRegionalVariant.NEUTRAL,
        BHSRegionalVariant.BS,
        BHSRegionalVariant.SR,
        BHSRegionalVariant.HR,
    ],
)
def test_bhs_regional_variants_are_valid(variant: BHSRegionalVariant) -> None:
    context = _context(ContentLanguageFamily.BHS, variant)
    assert context.regional_variant is variant


def test_non_latin_script_is_invalid() -> None:
    with pytest.raises(ValidationError):
        ContentLanguageContext(
            language_family=ContentLanguageFamily.EN,
            regional_variant=BHSRegionalVariant.NEUTRAL,
            script="CYRILLIC",  # type: ignore[arg-type]
            locale=AppLocale.EN,
        )


def test_context_is_immutable() -> None:
    context = _context(ContentLanguageFamily.BHS, BHSRegionalVariant.BS)
    with pytest.raises(ValidationError):
        context.regional_variant = BHSRegionalVariant.SR  # type: ignore[misc]
