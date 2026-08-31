"""Unit tests for domain common primitives."""

import uuid
from datetime import UTC, datetime

import pytest

from ai_campaign_studio.domain.common.errors import (
    AppError,
    ConfigurationError,
    DomainError,
    ErrorCode,
)
from ai_campaign_studio.domain.common.ids import new_id
from ai_campaign_studio.domain.common.timestamps import utc_now


def test_new_id_is_valid_uuid4_string() -> None:
    value = new_id()
    parsed = uuid.UUID(value)
    assert parsed.version == 4
    assert value != new_id()


def test_utc_now_is_timezone_aware_utc() -> None:
    now = utc_now()
    assert isinstance(now, datetime)
    assert now.tzinfo is UTC


def test_app_error_carries_code_message_and_context() -> None:
    err = AppError(
        "boom", error_code=ErrorCode.UNKNOWN_ERROR, technical_context="ctx"
    )
    assert err.error_code == ErrorCode.UNKNOWN_ERROR
    assert err.human_message == "boom"
    assert err.technical_context == "ctx"


def test_specific_errors_use_default_codes() -> None:
    assert ConfigurationError("bad").error_code == ErrorCode.CONFIGURATION_ERROR


def test_domain_error_is_an_app_error() -> None:
    with pytest.raises(AppError):
        raise DomainError("domain problem")
