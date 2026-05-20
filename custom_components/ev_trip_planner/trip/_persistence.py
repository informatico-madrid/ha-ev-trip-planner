"""Trip persistence — load/save lifecycle.

Migrated from _persistence_mixin.py. This is a plain class (no inheritance)
that owns trip persistence and YAML fallback methods.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from homeassistant.helpers import storage as ha_storage
from homeassistant.helpers.storage import Store

from ..const import DOMAIN
from .state import TripManagerState

_LOGGER = logging.getLogger(__name__)

# ── Log format string constants (US-5 testability) ──────────────────
_LOG_SETUP_INFO = "Configurando gestor de viajes para vehículo: %s"
_LOG_SAVE_START_INFO = "async_save_trips START - vehicle=%s, recurrentes=%d, puntuales=%d"
_LOG_SAVE_INJECTED = "=== Using injected storage ==="
_LOG_SAVE_FALLBACK = "=== Using fallback HA Store ==="
_LOG_SAVE_KEY_INFO = "Creating store with key: %s"
_LOG_SAVE_SUCCESS_INFO = "Viajes guardados en HA storage: %d recurrentes, %d puntuales"
_LOG_SAVE_ERROR = "Error guardando viajes: %s"
_LOG_SAVE_YAML_ERROR = "YAML fallback also failed: %s"
_LOG_LOAD_SKIP_DEBUG = (
    "Skipping _load_trips for %s: already have %d punctual, %d recurring trips"
)
_LOG_LOAD_START_DEBUG = "=== _load_trips START === vehicle=%s"
_LOG_LOAD_CANCEL_WARNING = (
    "Storage load cancelled (known timing issue) - continuing with empty state"
)
_LOG_LOAD_ERROR = "Error cargando viajes: %s"
_LOG_LOAD_YAML_ERROR = "Error cargando viajes desde YAML: %s"
_LOG_SAVE_YAML_FAIL_ERROR = "Error guardando viajes en YAML: %s"
_LOG_SANITIZE_WARNING = "%d recurring trip(s) ignored due to invalid hora format."


class TripPersistence:
    """Trip persistence and YAML fallback methods."""

    def __init__(self, state: TripManagerState) -> None:
        """Initialize with shared state."""
        self._state = state

    # ── Public API ─────────────────────────────────────────────────

    async def async_setup(self) -> None:  # pragma: no mutate
        """Configura el gestor de viajes y carga los datos desde el almacenamiento."""
        _LOGGER.info(_LOG_SETUP_INFO, self._state.vehicle_id)
        await self._state.vehicle_controller.async_setup()
        await self._load_trips()
        await self._state._schedule.publish_deferrable_loads()

    async def async_save_trips(self) -> None:  # pragma: no mutate
        """Guarda los viajes en el almacenamiento persistente."""
        state = self._state
        _LOGGER.info(
            _LOG_SAVE_START_INFO,
            state.vehicle_id,
            len(state.recurring_trips),
            len(state.punctual_trips),
        )

        data = {
            "trips": state._trips,
            "recurring_trips": state.recurring_trips,
            "punctual_trips": state.punctual_trips,
            "last_update": datetime.now(timezone.utc).isoformat(),
        }

        try:
            if state.storage is not None:
                _LOGGER.info(_LOG_SAVE_INJECTED)
                await state.storage.async_save(data)
            else:
                _LOGGER.info(_LOG_SAVE_FALLBACK)
                storage_key = f"{DOMAIN}_{state.vehicle_id}"
                _LOGGER.info(_LOG_SAVE_KEY_INFO, storage_key)
                store: Store[Dict[str, Any]] = ha_storage.Store(
                    state.hass,
                    version=1,
                    key=storage_key,
                )
                await store.async_save(data)
            _LOGGER.info(
                _LOG_SAVE_SUCCESS_INFO,
                len(state.recurring_trips),
                len(state.punctual_trips),
            )
        except Exception as err:
            _LOGGER.error(_LOG_SAVE_ERROR, err, exc_info=True)
            try:  # pragma: no cover reason=ha-filesystem-only
                await self._save_trips_yaml(f"{DOMAIN}_{state.vehicle_id}")
            except Exception as yaml_err:  # pragma: no cover reason=ha-filesystem-only
                _LOGGER.error("YAML fallback also failed: %s", yaml_err)

    # ── Private helpers ───────────────────────────────────────────

    async def _load_trips(self) -> None:  # pragma: no mutate
        """Carga los viajes desde el almacenamiento persistente."""
        state = self._state
        if state.punctual_trips or state.recurring_trips or state._trips:
            _LOGGER.debug(
                _LOG_LOAD_SKIP_DEBUG,
                state.vehicle_id,
                len(state.punctual_trips),
                len(state.recurring_trips),
            )
            return

        _LOGGER.debug(_LOG_LOAD_START_DEBUG, state.vehicle_id)
        try:
            stored_data: Optional[Dict[str, Any]] = None
            if state.storage is not None:
                stored_data = await state.storage.async_load()
            else:
                storage_key = f"{DOMAIN}_{state.vehicle_id}"
                store: Store[Dict[str, Any]] = ha_storage.Store(
                    state.hass,
                    version=1,
                    key=storage_key,
                )
                stored_data = await store.async_load()

            if stored_data:
                if isinstance(stored_data, dict) and "data" in stored_data:
                    data = stored_data.get("data", {})
                else:
                    data = stored_data

                state._trips = data.get("trips", {})
                state.recurring_trips = data.get("recurring_trips", {})
                state.punctual_trips = data.get("punctual_trips", {})
                state.last_update = data.get("last_update")

                state.recurring_trips = self._sanitize_recurring_trips(
                    state.recurring_trips
                )
            else:
                self._reset_trips()
        except asyncio.CancelledError:  # pragma: no cover reason=hass-taste-test-timing
            _LOGGER.warning(_LOG_LOAD_CANCEL_WARNING)
            state._trips = {}
            state.recurring_trips = {}
            state.punctual_trips = {}
            state.last_update = None
        except Exception as err:
            _LOGGER.error(_LOG_LOAD_ERROR, err, exc_info=True)
            state._trips = {}
            state.recurring_trips = {}
            state.punctual_trips = {}
            state.last_update = None

    async def _load_trips_yaml(
        self, storage_key: str
    ) -> None:  # pragma: no cover reason=ha-filesystem-only
        """Carga los viajes desde un archivo YAML (fallback)."""
        state = self._state
        try:
            ha_config = state.hass.config
            config_dir = ha_config.config_dir or "/config"
            yaml_file = Path(config_dir) / "ev_trip_planner" / f"{storage_key}.yaml"
            yaml_file.parent.mkdir(parents=True, exist_ok=True)
            if yaml_file.exists():
                with open(yaml_file, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                if "data" in data:
                    trip_data = data["data"]
                    state._trips = trip_data.get("trips", {})
                    state.recurring_trips = trip_data.get("recurring_trips", {})
                    state.punctual_trips = trip_data.get("punctual_trips", {})
                    state.last_update = trip_data.get("last_update")
                else:
                    self._reset_trips()
            else:
                self._reset_trips()
        except Exception as err:  # pragma: no cover reason=ha-filesystem-only
            _LOGGER.error(_LOG_LOAD_YAML_ERROR, err)
            self._reset_trips()

    async def _save_trips_yaml(self, storage_key: str) -> None:  # pragma: no mutate
        """Guarda los viajes en un archivo YAML (fallback)."""
        state = self._state
        try:  # pragma: no cover reason=ha-filesystem-only
            ha_config = state.hass.config
            config_dir = ha_config.config_dir or "/config"
            yaml_file = Path(config_dir) / "ev_trip_planner" / f"{storage_key}.yaml"
            yaml_file.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "data": {
                    "trips": state._trips,
                    "recurring_trips": state.recurring_trips,
                    "punctual_trips": state.punctual_trips,
                    "last_update": datetime.now(timezone.utc).isoformat(),
                }
            }
            with open(yaml_file, "w", encoding="utf-8") as f:
                yaml.dump(data, f, allow_unicode=True)
        except Exception as err:  # pragma: no cover reason=ha-filesystem-only
            _LOGGER.error(_LOG_SAVE_YAML_FAIL_ERROR, err)

    def _reset_trips(self) -> None:  # pragma: no mutate
        """Resetea todas las colecciones de viajes."""
        self._state._trips = {}
        self._state.recurring_trips = {}
        self._state.punctual_trips = {}
        self._state.last_update = None

    def _sanitize_recurring_trips(self, trips: Dict[str, Any]) -> Dict[str, Any]:  # pragma: no mutate
        """Elimina viajes recurrentes con formato de hora inválido."""
        from ..utils import sanitize_recurring_trips as pure_sanitize

        original_count = len(trips)
        sanitized = pure_sanitize(trips)
        removed_count = original_count - len(sanitized)
        if removed_count > 0:
            _LOGGER.warning(_LOG_SANITIZE_WARNING, removed_count)
        return sanitized
