"""Application error taxonomy.

Owns the single ``AppError`` hierarchy and machine-readable ``ErrorCode``
shared across domain/application/infrastructure (``RegistryError``,
``SecretStoreError``, ``DatabaseError``, ``MigrationError``, etc.). Does not
define feature-specific error types outside this file — new error classes
are added here, not duplicated per-module.
"""

from enum import StrEnum


class ErrorCode(StrEnum):
    """Machine-readable error codes (P0 foundation subset)."""

    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"
    REGISTRY_ERROR = "REGISTRY_ERROR"
    SECRET_STORE_ERROR = "SECRET_STORE_ERROR"
    DATABASE_ERROR = "DATABASE_ERROR"
    MIGRATION_ERROR = "MIGRATION_ERROR"
    NETWORK_ERROR = "NETWORK_ERROR"
    RATE_LIMIT = "RATE_LIMIT"
    PROVIDER_ERROR = "PROVIDER_ERROR"
    INVALID_API_KEY = "INVALID_API_KEY"
    UI_BRIDGE_ERROR = "UI_BRIDGE_ERROR"
    INVALID_STATE_TRANSITION = "INVALID_STATE_TRANSITION"
    INVARIANT_VIOLATION = "INVARIANT_VIOLATION"
    ENTITY_NOT_FOUND = "ENTITY_NOT_FOUND"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"


class AppError(Exception):
    """Base class for all application errors.

    Carries a machine-readable :class:`ErrorCode`, a human-facing message and
    an optional technical context. ``technical_context`` must never contain
    secrets; it is deliberately excluded from the exception args so that
    ``repr``/logging cannot leak it by accident.
    """

    default_code: ErrorCode = ErrorCode.UNKNOWN_ERROR

    def __init__(
        self,
        human_message: str,
        error_code: ErrorCode | None = None,
        technical_context: str | None = None,
    ) -> None:
        self.error_code = error_code if error_code is not None else self.default_code
        self.human_message = human_message
        self.technical_context = technical_context
        super().__init__(human_message)


class DomainError(AppError):
    """Error originating in the domain layer."""


class InvalidStateTransition(DomainError):
    """A state transition was attempted that the domain rules disallow."""

    default_code: ErrorCode = ErrorCode.INVALID_STATE_TRANSITION


class InvariantViolation(DomainError):
    """A domain invariant was violated."""

    default_code: ErrorCode = ErrorCode.INVARIANT_VIOLATION


class EntityNotFound(DomainError):
    """A requested entity does not exist."""

    default_code: ErrorCode = ErrorCode.ENTITY_NOT_FOUND


class ApplicationError(AppError):
    """Error originating in the application/use-case layer."""


class InfrastructureError(AppError):
    """Error originating in an infrastructure adapter."""


class ConfigurationError(AppError):
    """Invalid or missing configuration."""

    default_code: ErrorCode = ErrorCode.CONFIGURATION_ERROR


class RegistryError(AppError):
    """A registry lookup or validation failed."""

    default_code: ErrorCode = ErrorCode.REGISTRY_ERROR


class SecretStoreError(AppError):
    """A secret-store operation failed."""

    default_code: ErrorCode = ErrorCode.SECRET_STORE_ERROR


class DatabaseError(AppError):
    """A database operation failed."""

    default_code: ErrorCode = ErrorCode.DATABASE_ERROR


class MigrationError(AppError):
    """A schema migration failed."""

    default_code: ErrorCode = ErrorCode.MIGRATION_ERROR


class JobError(AppError):
    """A background job failed."""
