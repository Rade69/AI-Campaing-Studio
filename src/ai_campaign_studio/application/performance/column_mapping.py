"""CSV column mapping (P1.5-G3 dio 1, Faza 0.7 §12/§14).

Owns the data-driven, deterministic mapping of raw CSV header names to
canonical performance fields, producing one ``ColumnMatch`` per canonical
field with status ``matched`` / ``ambiguous`` / ``unmatched``. The alias
lists live in ``resources/performance_import/column_aliases_v1.yaml``, not
hardcoded in Python. Does not match rows to ``DistributionInstance`` (that
is G4 / dio 2) and does no I/O beyond loading the YAML rules file.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import yaml  # type: ignore[import-untyped]

_DEFAULT_RULES_PATH = (
    Path(__file__).resolve().parents[4]
    / "resources"
    / "performance_import"
    / "column_aliases_v1.yaml"
)


@dataclass(frozen=True)
class ColumnAliasRules:
    """Loaded column-alias rules: mapping version + canonical field aliases.

    ``column_aliases`` preserves the YAML insertion order, so iterating it is
    deterministic (same file -> same field order -> same ``map_columns``
    result). Alias values are kept verbatim; matching casefolds them.
    """

    version: str
    column_aliases: dict[str, tuple[str, ...]]


@dataclass(frozen=True)
class ColumnMatch:
    """Mapping outcome for ONE canonical field.

    ``header`` is the single CSV header that matched, or ``None`` when there
    is no unique match (``unmatched`` or ``ambiguous``). ``candidates`` lists
    every CSV header that aliases this field (empty for ``unmatched``, one
    element for ``matched``, two or more for ``ambiguous``).
    """

    canonical_field: str
    header: str | None
    status: Literal["matched", "ambiguous", "unmatched"]
    candidates: tuple[str, ...]


def load_column_aliases(path: Path | None = None) -> ColumnAliasRules:
    """Load column alias rules from YAML (bundled default when no path).

    The returned ``version`` string feeds ``PerformanceImportBatch.mapping_version``
    later (dio 2), so an import is always traceable to the rule set used.
    """
    resolved = path if path is not None else _DEFAULT_RULES_PATH
    raw = yaml.safe_load(resolved.read_text(encoding="utf-8"))
    return ColumnAliasRules(
        version=str(raw["version"]),
        column_aliases={
            str(field): tuple(str(alias) for alias in aliases)
            for field, aliases in raw["column_aliases"].items()
        },
    )


def map_columns(
    headers: tuple[str, ...], rules: ColumnAliasRules
) -> tuple[ColumnMatch, ...]:
    """Map CSV headers to canonical fields (one ``ColumnMatch`` per field).

    Deterministic and case-insensitive: both header and alias are compared
    via ``str.casefold``. ``ambiguous`` means MORE than one CSV header aliases
    the SAME canonical field (e.g. both "spend" and "trošak" in one file); the
    field is then left with ``header=None`` so no value is silently picked.
    A header that matches NO field is simply an extra column — it is never an
    error here and stays available in ``ParsedRow.raw_values`` downstream.
    """
    matches: list[ColumnMatch] = []
    for field, aliases in rules.column_aliases.items():
        folded_aliases = {alias.casefold() for alias in aliases}
        candidates = tuple(
            header for header in headers if header.casefold() in folded_aliases
        )
        if not candidates:
            matches.append(ColumnMatch(field, None, "unmatched", ()))
        elif len(candidates) == 1:
            matches.append(
                ColumnMatch(field, candidates[0], "matched", candidates)
            )
        else:
            matches.append(ColumnMatch(field, None, "ambiguous", candidates))
    return tuple(matches)
