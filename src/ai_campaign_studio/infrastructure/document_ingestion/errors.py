"""Document parsing errors (S2-G9).

Owns ``DocumentParseError`` — the single, SPECIFIC exception type every
document source parser raises for unopenable/corrupt/empty inputs. A specific
type (never a bare ``Exception``) is what lets the S2-G6 orchestration catch
parsing failures and record ``CrawlTarget.last_error`` without swallowing
unrelated bugs.
"""

from __future__ import annotations


class DocumentParseError(ValueError):
    """A document could not be opened or parsed."""


__all__ = ["DocumentParseError"]
