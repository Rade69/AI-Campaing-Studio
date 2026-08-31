"""Immutable, validated content-language context.

``ContentLanguageContext`` describes the language of *generated content*, which
is independent from the UI locale (``AppLocale``). It carries no
fact/provenance logic: regional variants are presentation/copy rules only
(D-LANG-2/D-LANG-4).
"""

from pydantic import BaseModel, ConfigDict, model_validator

from ai_campaign_studio.localization.enums import (
    AppLocale,
    BHSRegionalVariant,
    ContentLanguageFamily,
    Script,
)


class ContentLanguageContext(BaseModel):
    """Validated, frozen language context for generated content.

    Invariants (Phase 0/1):
    - ``EN`` requires ``regional_variant == NEUTRAL``;
    - ``BHS`` allows ``NEUTRAL | BS | SR | HR``;
    - only ``LATIN`` script is supported.
    """

    model_config = ConfigDict(frozen=True)

    language_family: ContentLanguageFamily
    regional_variant: BHSRegionalVariant = BHSRegionalVariant.NEUTRAL
    script: Script = Script.LATIN
    locale: AppLocale
    preferred_terms: tuple[str, ...] = ()
    forbidden_terms: tuple[str, ...] = ()
    regional_vocabulary: tuple[str, ...] = ()
    tone_examples: tuple[str, ...] = ()

    @model_validator(mode="after")
    def _validate_invariants(self) -> "ContentLanguageContext":
        if self.script is not Script.LATIN:
            raise ValueError("Only Latin script is supported in Phase 0/1")
        if (
            self.language_family is ContentLanguageFamily.EN
            and self.regional_variant is not BHSRegionalVariant.NEUTRAL
        ):
            raise ValueError("EN requires regional_variant NEUTRAL")
        return self
