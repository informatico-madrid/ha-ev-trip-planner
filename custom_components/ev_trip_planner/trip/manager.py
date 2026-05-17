"""TripManager — facade for composed sub-components.

Pure composition over inheritance. No MRO, no mixins, no wrapper methods.
"""

from __future__ import annotations

import datetime as _datetime_mod  # noqa: F401
import logging
from pathlib import Path  # noqa: F401
from typing import Any, Dict, Optional

from homeassistant.core import HomeAssistant

from ..emhass import EMHASSAdapter
from ..utils import sanitize_recurring_trips as pure_sanitize_recurring_trips
from ..utils import validate_hora as pure_validate_hora
from ..vehicle import VehicleController
from ._crud import TripCRUD
from ._emhass_sync import EMHASSSync
from ._persistence import TripPersistence
from ._power_profile import PowerProfile
from ._schedule import TripScheduler
from ._soc_helpers import SOCHelpers
from ._soc_query import SOCQuery
from ._soc_window import SOCWindow
from ._trip_lifecycle import TripLifecycle
from ._trip_navigator import TripNavigator
from ._types import TripManagerConfig
from .state import TripManagerState

_LOGGER = logging.getLogger(__name__)


class TripManager:
    """Gestión central de viajes — composed sub-component facade."""

    def __init__(
        self,
        hass: HomeAssistant,
        vehicle_id: str,
        config: Optional[TripManagerConfig] = None,
    ) -> None:
        """Inicializa el gestor de viajes para un vehículo específico."""
        cfg = config or TripManagerConfig()

        # Create shared state
        self._state = TripManagerState(
            hass=hass,
            vehicle_id=vehicle_id,
            entry_id=cfg.entry_id or "",
            storage=cfg.storage,
            emhass_adapter=cfg.emhass_adapter,
        )

        # Create vehicle controller
        self._state.vehicle_controller = VehicleController(
            hass, vehicle_id, cfg.presence_config, self
        )

        # Create sub-component instances
        self._persistence = TripPersistence(self._state)
        self._crud = TripCRUD(self._state)
        self._lifecycle = TripLifecycle(self._state)
        self._emhass_sync = EMHASSSync(self._state)
        self._soc_helpers = SOCHelpers(self._state)
        self._soc_query = SOCQuery(self._state)
        self._soc_window = SOCWindow(self._state)
        self._power = PowerProfile(self._state)
        self._schedule = TripScheduler(self._state)
        self._navigator = TripNavigator(self._state)

        # Wire sub-component references on state for cross-component access
        self._state._crud = self._crud
        self._state._persistence = self._persistence
        self._state._soc = self._soc_query
        self._state._power = self._power
        self._state._schedule = self._schedule
        self._state._navigator = self._navigator
        self._state._emhass_sync = self._emhass_sync
        self._state._soc_helpers = self._soc_helpers
        self._state._lifecycle = self._lifecycle
        self._state._soc_window = self._soc_window

        # Delegates needed by sub-components during operation
        self._state.async_save_trips = self._persistence.async_save_trips

    # ── EMHASS adapter property ──────────────────────────────────

    @property
    def emhass_adapter(self) -> Optional[EMHASSAdapter]:
        """Get the EMHASS adapter."""
        return self._state.emhass_adapter

    @emhass_adapter.setter
    def emhass_adapter(self, value: Optional[EMHASSAdapter]) -> None:
        """Set the EMHASS adapter."""
        self._state.emhass_adapter = value
        _LOGGER.debug("EMHASS adapter set for vehicle %s", self._state.vehicle_id)

    # ── Static helpers ───────────────────────────────────────────

    @staticmethod
    def _validate_hora(hora: str) -> None:
        """Valida que una cadena de hora tenga el formato HH:MM y valores válidos."""
        pure_validate_hora(hora)

    def _sanitize_recurring_trips(self, trips: Dict[str, Any]) -> Dict[str, Any]:
        """Elimina viajes recurrentes con formato de hora inválido."""
        original_count = len(trips)
        sanitized = pure_sanitize_recurring_trips(trips)
        removed_count = original_count - len(sanitized)
        if removed_count > 0:
            _LOGGER.warning(
                "%d recurring trip(s) ignored due to invalid hora format. "
                "Fix or remove invalid entries from storage.",
                removed_count,
            )
        return sanitized
