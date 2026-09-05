"""SQLite repository adapters (A5).

Concrete ``sqlite3`` implementations of the ``ports.repositories`` and
``ports.provider_config`` protocol interfaces. Built on the P0 connection/
migration foundation; callers pass a ``sqlite3.Connection`` (typically from
``SqliteUnitOfWork``).
"""

from .sqlite_brand_repository import SqliteBrandRepository
from .sqlite_campaign_repository import SqliteCampaignRepository
from .sqlite_content_repository import SqliteContentRepository
from .sqlite_fact_repository import SqliteFactRepository
from .sqlite_performance_repository import SqlitePerformanceRepository
from .sqlite_provider_config_repository import (
    SqliteModelSelectionRepository,
    SqliteProviderConfigRepository,
)
from .sqlite_revision_repository import SqliteRevisionRepository
from .sqlite_visual_repository import SqliteVisualRepository

__all__ = [
    "SqliteBrandRepository",
    "SqliteCampaignRepository",
    "SqliteContentRepository",
    "SqliteFactRepository",
    "SqliteModelSelectionRepository",
    "SqlitePerformanceRepository",
    "SqliteProviderConfigRepository",
    "SqliteRevisionRepository",
    "SqliteVisualRepository",
]
