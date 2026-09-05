"""Performance domain enums (Faza 0.7 §3, §13).

``DistributionSource`` (where a content distribution came from) and
``PerformanceSource`` (where performance data came from) are DELIBERATELY two
separate types: they share part of the vocabulary but are not the same
concept. ``DistributionSource`` has ``EXPORT`` (content can leave the system),
which makes no sense for ``PerformanceSource`` (metrics always ENTER the
system).
"""

from enum import StrEnum


class DistributionSource(StrEnum):
    """Where a content DISTRIBUTION came from."""

    EXPORT = "EXPORT"
    MANUAL = "MANUAL"
    CSV_IMPORT = "CSV_IMPORT"
    API = "API"


class PerformanceSource(StrEnum):
    """Where PERFORMANCE DATA came from."""

    CSV_IMPORT = "CSV_IMPORT"
    MANUAL = "MANUAL"
    API = "API"
