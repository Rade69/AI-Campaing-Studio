"""Application settings.

Owns the validated ``AppSettings`` model consumed by ``bootstrap.py`` and
``config/paths.py``. Does not hold secrets, provider credentials, campaign
defaults or hardcoded model lists — those belong to their own features.
"""

from pathlib import Path
from typing import Literal

from pydantic import BaseModel

AppEnvironment = Literal["development", "test", "production"]
AppLocale = Literal["EN", "BHS_LATIN"]
LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


class AppSettings(BaseModel):
    """Validated, framework-neutral application settings.

    Deliberately contains no secrets, provider credentials, campaign defaults
    or hardcoded model lists — those arrive with their own features.
    """

    app_name: str = "AI Campaign Studio"
    environment: AppEnvironment = "development"
    log_level: LogLevel = "INFO"
    app_locale: AppLocale = "BHS_LATIN"
    database_filename: str = "ai_campaign_studio.db"
    resource_dir_override: Path | None = None
    data_dir_override: Path | None = None
