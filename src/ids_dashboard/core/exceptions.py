"""Application-specific exception types."""

from __future__ import annotations


class AppError(Exception):
    """Base exception for expected application failures."""

    default_status_code = 400
    default_error_code = "application_error"

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        error_code: str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code or self.default_status_code
        self.error_code = error_code or self.default_error_code


class ConfigurationError(AppError):
    """Raised when application configuration is invalid."""

    default_status_code = 500
    default_error_code = "configuration_error"


class IngestionError(AppError):
    """Raised when alert ingestion encounters invalid data."""

    default_status_code = 400
    default_error_code = "ingestion_error"


class ResourceNotFoundError(AppError):
    """Raised when a required local resource cannot be found."""

    default_status_code = 404
    default_error_code = "resource_not_found"

