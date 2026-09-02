"""Unit tests for domain-specific error subclasses (A3 extension)."""

from ai_campaign_studio.domain.common.errors import (
    DomainError,
    EntityNotFound,
    ErrorCode,
    InvalidStateTransition,
    InvariantViolation,
)


def test_new_errors_are_domain_errors() -> None:
    for cls in (InvalidStateTransition, InvariantViolation, EntityNotFound):
        assert issubclass(cls, DomainError)


def test_new_errors_use_default_codes() -> None:
    assert (
        InvalidStateTransition("x").error_code
        == ErrorCode.INVALID_STATE_TRANSITION
    )
    assert InvariantViolation("x").error_code == ErrorCode.INVARIANT_VIOLATION
    assert EntityNotFound("x").error_code == ErrorCode.ENTITY_NOT_FOUND


def test_technical_context_is_not_leaked_into_args() -> None:
    err = InvariantViolation("bad", technical_context="sensitive detail")
    assert err.args == ("bad",)
    assert err.technical_context == "sensitive detail"
