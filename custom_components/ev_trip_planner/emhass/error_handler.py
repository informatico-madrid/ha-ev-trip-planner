"""Error handling for EMHASS adapter operations."""

from __future__ import annotations

import logging
from typing import Any, Callable, Optional

from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

# Log string constants for testability (US-5 mutation-testing pattern)
_LOG_CONTEXT_ENTRY = "  %s: %s"
_LOG_ERROR_HANDLER_CALLBACK_FAILED = "Error handler callback failed"
_LOG_MISSING_ID = "Trip missing ID during %s"
_LOG_DEADLINE_ERROR = "Trip %s has no valid deadline during %s"
_LOG_INDEX_ERROR = "Attempted to %s index for unknown trip %s"
_LOG_STORAGE_ERROR = "Failed to %s index mapping from storage: %s"


class ErrorHandler:
    """Handles errors from EMHASS operations.

    Provides a centralized error handling interface for logging,
    state management, and error callbacks during EMHASS adapter
    operations (publish, update, remove, etc.).
    """

    def __init__(
        self,
        hass: HomeAssistant,
        on_error: Optional[Callable[[str, Exception], None]] = None,
    ) -> None:
        """Initialize error handler.

        Args:
            hass: HomeAssistant instance.
            on_error: Optional callback for error handling.
        """
        self.hass = hass
        self._on_error = on_error

    def handle_error(
        self,
        operation: str,
        error: Exception,
        context: Optional[dict[str, Any]] = None,
    ) -> None:
        """Handle an error during an EMHASS operation.

        Args:
            operation: Name of the operation that failed.
            error: The exception that occurred.
            context: Optional context dict with additional details.
        """
        message = f"Error during {operation}: {error}"
        _LOGGER.error(message)

        if context:
            for key, value in context.items():
                _LOGGER.debug(_LOG_CONTEXT_ENTRY, key, value)

        if self._on_error is not None:
            try:
                self._on_error(operation, error)
            except Exception:
                _LOGGER.exception(_LOG_ERROR_HANDLER_CALLBACK_FAILED)

    def handle_missing_id(self, trip_id: str, operation: str = "publish") -> bool:
        """Handle missing trip ID error.

        Args:
            trip_id: The trip identifier (may be None/empty).
            operation: Name of the operation.

        Returns:
            False to signal failure to the caller.
        """
        _LOGGER.error(_LOG_MISSING_ID, operation)
        return False

    def handle_deadline_error(self, trip_id: str, operation: str = "publish") -> bool:
        """Handle deadline calculation error.

        Args:
            trip_id: The trip identifier.
            operation: Name of the operation.

        Returns:
            False to signal failure to the caller.
        """
        _LOGGER.error(_LOG_DEADLINE_ERROR, trip_id, operation)
        return False

    def handle_index_error(
        self, trip_id: str, operation: str = "release"
    ) -> Optional[str]:
        """Handle index-related errors.

        Args:
            trip_id: The trip identifier.
            operation: Name of the operation.

        Returns:
            None to signal failure to the caller.
        """
        _LOGGER.warning(_LOG_INDEX_ERROR, operation, trip_id)
        return None

    def handle_storage_error(self, operation: str, error: Exception) -> None:
        """Handle storage-related errors (load/save index).

        Args:
            operation: The storage operation that failed.
            error: The exception that occurred.
        """
        _LOGGER.error(_LOG_STORAGE_ERROR, operation, error)
