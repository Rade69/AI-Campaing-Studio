"""Boilerplate filter (S2-G4).

Owns a conservative, line-based post-processing pass that removes residual
boilerplate from already-extracted TEXT (share / nav / footer / cookie labels).
Trafilatura already strips most boilerplate (``favor_precision=True``); this
pass is a defensive SECOND layer and is deliberately NON-DESTRUCTIVE — it only
drops a line that exactly matches a curated boilerplate phrase (or a
copyright/cookie-consent signature), so it never removes legitimate main
content (sanity invariant: it must not lower the Q12 benchmark F1).

Does NOT do the heavy structural stripping (that is Trafilatura's job, done in
``MainContentExtractor``) and does NOT parse HTML — it takes plain text.
"""

from __future__ import annotations

import re

# Whole-line (case-folded, stripped) phrases that are boilerplate, never main
# content. Kept deliberately small and unambiguous so the pass stays
# non-destructive.
_BOILERPLATE_LINES: frozenset[str] = frozenset(
    {
        # social / share labels
        "facebook",
        "instagram",
        "twitter",
        "x (twitter)",
        "viber",
        "telegram",
        "whatsapp",
        "linkedin",
        "youtube",
        "tiktok",
        "google news",
        "pinterest",
        "snapchat",
        "threads",
        "e-mail",
        "email",
        "rss",
        # share / engagement actions
        "podijeli",
        "podeli",
        "share",
        "pratite nas",
        "pratite nas na",
        "follow us",
        "prijavi grešku",
        "prijavi gresku",
        "prijavi grešku u tekstu",
        "pročitajte i ovo",
        "procitajte i ovo",
        "najčitanije",
        "najcitanije",
        "nove vijesti",
        "najnovije",
        "vrh stranice",
        "komentari",
        "komentara",
        # footer / legal / nav
        "impresum",
        "pravila korištenja",
        "pravila korišćenja",
        "uslovi korišćenja",
        "uslovi korištenja",
        "autorska prava",
        "prigovori i ispravke",
        "marketing",
        "kontakt",
        "elektronsko izdanje",
    }
)

_COPYRIGHT_RE = re.compile(r"©|\(c\)|\bsva prava zadržana\b", re.IGNORECASE)

# A line is cookie-consent only if it mentions cookies AND a consent/notice
# signal word. The bare word "kolačić" alone is NOT enough (it also means
# "biscuit" and can be legitimate recipe content).
_COOKIE_RE = re.compile(r"kolači|kolaci|cookie", re.IGNORECASE)
_CONSENT_RE = re.compile(
    r"koristi|prihvat|privola|saglasnost|politika|postavke|upravljanje"
    r"|consent|policy|settings",
    re.IGNORECASE,
)


class BoilerplateFilter:
    """Remove residual boilerplate lines from extracted text."""

    def filter(self, text: str) -> str:
        """Return ``text`` with boilerplate lines removed.

        Deterministic and non-destructive: only whole lines that match a
        curated boilerplate phrase (or a copyright signature) are dropped;
        every other non-empty line is preserved verbatim.
        """
        kept: list[str] = []
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            if self._is_boilerplate(line):
                continue
            kept.append(line)
        return "\n\n".join(kept)

    @staticmethod
    def _is_boilerplate(line: str) -> bool:
        if line.casefold() in _BOILERPLATE_LINES:
            return True
        if _COPYRIGHT_RE.search(line):
            return True
        return bool(_COOKIE_RE.search(line) and _CONSENT_RE.search(line))


__all__ = ["BoilerplateFilter"]
