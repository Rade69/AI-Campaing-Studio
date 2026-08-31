"""Localization enums.

Two UI locales (``AppLocale``), a content-language family model and the BHS
regional variants. Regional variants refine generated-copy terminology; they
are not separate application locales (D-LANG-1/D-LANG-2).
"""

from enum import StrEnum


class AppLocale(StrEnum):
    """The two application UI locales."""

    EN = "EN"
    BHS_LATIN = "BHS_LATIN"


class ContentLanguageFamily(StrEnum):
    """Language family of generated content (separate from UI locale)."""

    EN = "EN"
    BHS = "BHS"


class BHSRegionalVariant(StrEnum):
    """Regional terminology variant for the BHS language family."""

    NEUTRAL = "NEUTRAL"
    BS = "BS"
    SR = "SR"
    HR = "HR"


class Script(StrEnum):
    """Writing system for generated content."""

    LATIN = "LATIN"
