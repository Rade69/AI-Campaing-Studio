"""Analytics match key (Faza 0.7 §16, Faza 1 v1.5 §6).

Owns the deterministic identity that ties a future performance data point
back to exactly one exported content revision + target combination. Pure
stdlib (``hashlib``) — no I/O, no secrets, no PII.
"""

from __future__ import annotations

import hashlib

# 32 hex chars (128 bits). Long enough to avoid collisions for any real
# number of posts per campaign, deliberately NOT a full 64-char SHA-256 hex
# — this is a matching identity, not a security token.
_KEY_LENGTH = 32


def compute_analytics_match_key(
    content_piece_id: str,
    content_revision_id: str,
    platform_code: str,
    format_code: str,
) -> str:
    """Return a stable, deterministic key for one exported revision+target.

    - Deterministic for the same input (same 4-tuple -> same output).
    - Changes when ``content_revision_id`` changes (a new revision of the
      same post is a new identity for matching).
    - Changes when ``platform_code`` or ``format_code`` changes (same
      content on a different target is a new identity).
    - Contains no secrets/PII — only internal UUIDs and registry codes,
      hashed with SHA-256.

    The fields are joined with ``|`` before hashing so field boundaries are
    unambiguous (``"ab"+"c"`` != ``"a"+"bc"``).
    """
    joined = "|".join(
        (content_piece_id, content_revision_id, platform_code, format_code)
    )
    digest = hashlib.sha256(joined.encode("utf-8")).hexdigest()
    return digest[:_KEY_LENGTH]
