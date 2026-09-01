"""Central logging configuration (stdlib only).

Owns building the application's console + rotating-file logger from
``AppSettings``/``AppPaths``. Does not redact sensitive values itself —
callers must run payloads through ``logging.redaction.redact`` first.
"""

import logging
from logging.handlers import RotatingFileHandler

from ai_campaign_studio.config.paths import AppPaths
from ai_campaign_studio.config.settings import AppSettings

LOGGER_NAME = "ai_campaign_studio"

_LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"


def configure_logging(settings: AppSettings, paths: AppPaths) -> logging.Logger:
    """Configure and return the application logger.

    Attaches a console handler and a UTF-8 rotating file handler. Callers must
    run sensitive payloads through ``ai_campaign_studio.logging.redaction.redact``
    before logging; this function never logs secret values itself.
    """
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(settings.log_level)
    logger.handlers.clear()

    formatter = logging.Formatter(_LOG_FORMAT)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    paths.logs_dir.mkdir(parents=True, exist_ok=True)
    file_handler = RotatingFileHandler(
        paths.logs_dir / "ai_campaign_studio.log",
        encoding="utf-8",
        maxBytes=1_000_000,
        backupCount=3,
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger
