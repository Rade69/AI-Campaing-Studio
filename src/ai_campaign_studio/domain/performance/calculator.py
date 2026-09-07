"""P1.5-G5 derived metric calculator (Faza 1 v1.5 §20).

Owns deterministic derivation of CTR/CPC/CPM/CPA/ROAS/Conversion Rate from a
``CanonicalMetricSet``. Pure function: no I/O, no persistence, no ports, no
side effects. Does not aggregate across snapshots and does not compare or mix
currencies — both are P1.5-G6 read-model concerns, not this calculator.
"""

from __future__ import annotations

import math

from ai_campaign_studio.domain.performance.metrics import (
    CanonicalMetricSet,
    DerivedMetricSet,
)


def _safe_div(
    numerator: int | float | None,
    denominator: int | float | None,
) -> float | None:
    """Divide two raw inputs, returning ``None`` instead of ever failing.

    Uniform rule applied by every derived metric:

    - either operand ``None`` (missing) -> ``None`` — missing data is not zero;
    - either operand negative -> ``None`` — invalid input, fail soft per row;
    - either operand non-finite (``NaN``/``inf``) -> ``None``;
    - denominator zero -> ``None`` — no ``ZeroDivisionError``, no ``inf``.

    A numerator of zero with a positive denominator is a valid result (``0.0``).
    """
    if numerator is None or denominator is None:
        return None
    num = float(numerator)
    den = float(denominator)
    if num < 0 or den < 0:
        return None
    if not math.isfinite(num) or not math.isfinite(den):
        return None
    if den == 0:
        return None
    return num / den


def calculate_derived_metrics(metrics: CanonicalMetricSet) -> DerivedMetricSet:
    """Derive six metrics from one ``CanonicalMetricSet`` (Faza 1 v1.5 §20).

    Deterministic and pure. Percent-style metrics (CTR, Conversion Rate) are
    returned as RATIOS (0.034 == 3.4%), not percentages. Each metric applies
    the same ``_safe_div`` rule independently, so one bad input nulls only the
    metrics that use it — never the whole result, and never an exception.
    """
    ctr = _safe_div(metrics.clicks, metrics.impressions)
    cpc = _safe_div(metrics.spend, metrics.clicks)
    # CPM = spend / impressions * 1000 — the *1000 is part of CPM's own
    # definition (cost per thousand impressions), applied after the shared
    # division rule.
    cpm = _safe_div(metrics.spend, metrics.impressions)
    if cpm is not None:
        cpm *= 1000.0
    cpa = _safe_div(metrics.spend, metrics.conversions)
    roas = _safe_div(metrics.revenue, metrics.spend)
    conversion_rate = _safe_div(metrics.conversions, metrics.clicks)

    return DerivedMetricSet(
        ctr=ctr,
        cpc=cpc,
        cpm=cpm,
        cpa=cpa,
        roas=roas,
        conversion_rate=conversion_rate,
    )
