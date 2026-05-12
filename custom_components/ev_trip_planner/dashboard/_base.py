"""Dashboard base types — ABCs and Protocols for SOLID O compliance.

This module provides abstract base classes and protocols that define the
interfaces for dashboard operations, satisfying the Open/Closed principle
by allowing extension without modification of existing code.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional

from homeassistant.core import HomeAssistant


class DashboardComponentProtocol(ABC):
    """Protocol for modular dashboard components that can be added/removed."""

    @abstractmethod
    def component_name(self) -> str:
        """Return the unique component name."""

    @abstractmethod
    def component_config(self, vehicle_id: str) -> dict[str, Any]:
        """Return configuration dict for this component."""


class DashboardImporterProtocol(ABC):
    """Protocol defining the contract for dashboard import operations.

    Importers may be extended with new template formats (YAML, JSON, etc.)
    without modifying existing code.
    """

    @abstractmethod
    def validate_config(self, config: dict[str, Any]) -> bool:
        """Validate a dashboard configuration dictionary."""

    @abstractmethod
    def import_config(
        self,
        hass: HomeAssistant,
        vehicle_id: str,
        config: dict[str, Any],
    ) -> dict[str, Any]:
        """Import a validated dashboard configuration."""


class DashboardStorageStrategy(ABC):
    """Strategy interface for dashboard persistence backends.

    Storage backends (Lovelace, YAML file, etc.) implement this protocol
    to allow adding new storage methods without modifying existing code.
    """

    @abstractmethod
    def save_config(
        self,
        hass: HomeAssistant,
        vehicle_id: str,
        content: str,
    ) -> bool:
        """Save dashboard configuration to storage."""

    @abstractmethod
    def load_config(self, vehicle_id: str) -> Optional[str]:
        """Load dashboard configuration from storage."""

    @abstractmethod
    def exists(self, vehicle_id: str) -> bool:
        """Check if a dashboard configuration exists."""

    @abstractmethod
    def delete(self, vehicle_id: str) -> bool:
        """Delete a dashboard configuration."""


class DashboardTemplateStrategy(ABC):
    """Strategy interface for dashboard template loading.

    Template backends (HassOS asset, filesystem, etc.) implement this protocol
    to allow adding new template sources without modifying existing code.
    """

    @abstractmethod
    def get_template_path(self, template_name: str, vehicle_id: str) -> str:
        """Resolve the filesystem path for a template file."""

    @abstractmethod
    def load_template(self, path: str) -> Optional[str]:
        """Load template content from a file path."""

    @abstractmethod
    def save_template(
        self,
        path: str,
        content: str,
    ) -> bool:
        """Save template content to a file path."""
