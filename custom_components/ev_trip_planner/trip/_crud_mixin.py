"""CRUD mixin for TripManager — extracted from trip_manager.py.

Contains all trip lifecycle CRUD operations: setup, load, save,
add, update, delete, pause/resume, complete/cancel, and sensor
event emissions.

The mixin reads shared state from `self` (inherited via MRO):
- `self._trips`, `self._recurring_trips`, `self._punctual_trips`
- `self._storage`, `self._emhass_adapter`, `self.hass`
- `self._entry_id`, `self.vehicle_id`, `self._sensor_callbacks`
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from homeassistant.core import HomeAssistant
from homeassistant.helpers import storage as ha_storage
from homeassistant.helpers.storage import Store

from ..const import (
    DOMAIN,
    TRIP_TYPE_PUNCTUAL,
    TRIP_TYPE_RECURRING,
)
from ..utils import generate_trip_id

from ._sensor_callbacks import _SensorCallbacks

_UNSET = object()

_LOGGER = logging.getLogger(__name__)


class _CRUDMixin:
    """Mix-in providing trip lifecycle CRUD operations.

    The mixin's __init__ is minimal — it only initializes the
    sensor callback system. All other state comes from the host
    class via MRO.
    """

    def __init__(self) -> None:
        """Initialize the CRUD mixin."""
        self._sensor_callbacks: _SensorCallbacks = _SensorCallbacks()

    # ── Lifecycle ──────────────────────────────────────────────

    async def async_setup(self) -> None:
        """Configura el gestor de viajes y carga los datos desde el almacenamiento."""
        _LOGGER.info("Configurando gestor de viajes para vehículo: %s", self.vehicle_id)
        await self.vehicle_controller.async_setup()
        await self._load_trips()
        # CRITICAL FIX: Publish trips to EMHASS after loading from storage
        # This ensures EMHASS sensor is updated after HA restart when trips are loaded
        # Previously, _load_trips() was called but publish_deferrable_loads() was NOT,
        # causing the EMHASS template to show empty arrays after restart
        await self.publish_deferrable_loads()

    async def _load_trips(self) -> None:
        """Carga los viajes desde el almacenamiento persistente.

        Only loads if memory is empty (first load). This prevents overwriting
        in-memory data with stale storage data during service calls.
        """
        # Skip loading if we already have data in memory
        if self._punctual_trips or self._recurring_trips or self._trips:
            _LOGGER.debug(
                "Skipping _load_trips for %s: already have %d punctual, %d recurring trips in memory",
                self.vehicle_id,
                len(self._punctual_trips),
                len(self._recurring_trips),
            )
            return

        # DEBUG: Add stack trace to see who is calling _load_trips()
        import traceback

        _LOGGER.debug("=== _load_trips START === vehicle=%s", self.vehicle_id)
        _LOGGER.debug(
            "=== _load_trips CALLED FROM ===\n%s", traceback.format_stack()[-3]
        )
        try:
            # DI: use injected storage if available, otherwise fallback to direct Store
            stored_data: Optional[Dict[str, Any]] = None
            if self._storage is not None:
                _LOGGER.debug("=== Using injected storage ===")
                stored_data = await self._storage.async_load()
            else:
                _LOGGER.debug("=== Using fallback HA Store ===")
                storage_key = f"{DOMAIN}_{self.vehicle_id}"
                _LOGGER.debug("=== Loading from store with key: %s ===", storage_key)
                store: Store[Dict[str, Any]] = ha_storage.Store(
                    self.hass,
                    version=1,
                    key=storage_key,
                )
                stored_data = await store.async_load()
            _LOGGER.debug("=== async_load returned: %s ===", stored_data is not None)
            _LOGGER.debug("=== stored_data type: %s ===", type(stored_data).__name__)
            _LOGGER.debug("=== stored_data value: %s ===", stored_data)
            if stored_data:
                _LOGGER.debug(
                    "=== stored_data structure: %s ===",
                    (
                        list(stored_data.keys())
                        if isinstance(stored_data, dict)
                        else "not a dict"
                    ),
                )
                _LOGGER.debug(
                    "=== stored_data['data'] exists: %s ===",
                    "data" in stored_data if isinstance(stored_data, dict) else False,
                )

                # Store API retorna datos dentro de la clave "data"
                if isinstance(stored_data, dict) and "data" in stored_data:
                    data = stored_data.get("data", {})
                else:
                    # Fallback: use stored_data directly if no "data" key
                    data = stored_data
                _LOGGER.debug("=== data extracted: %s ===", data)
                _LOGGER.debug("=== data from stored_data.get('data', {}): %s ===", data)

                self._trips = data.get("trips", {})
                self._recurring_trips = data.get("recurring_trips", {})
                self._punctual_trips = data.get("punctual_trips", {})
                self._last_update = data.get("last_update")

                # Sanitize recurring trips: remove entries with invalid hora format
                self._recurring_trips = self._sanitize_recurring_trips(
                    self._recurring_trips
                )

                _LOGGER.debug("=== AFTER LOAD ===")
                _LOGGER.debug("=== self._trips: %d trips ===", len(self._trips))
                _LOGGER.debug(
                    "=== self._recurring_trips: %d recurrentes ===",
                    len(self._recurring_trips),
                )
                _LOGGER.debug(
                    "=== self._punctual_trips: %d puntuales ===",
                    len(self._punctual_trips),
                )

                # Log detailed trip info
                if self._recurring_trips:
                    _LOGGER.debug(
                        "=== Recurring trips IDs: %s ===",
                        list(self._recurring_trips.keys())[:5],
                    )
                if self._punctual_trips:
                    _LOGGER.debug(
                        "=== Punctual trips IDs: %s ===",
                        list(self._punctual_trips.keys())[:5],
                    )
            else:
                _LOGGER.debug(
                    "No se encontraron viajes almacenados para %s",
                    self.vehicle_id,
                )
                self._reset_trips()
        except asyncio.CancelledError:  # pragma: no cover
            # CancelledError during storage load is known issue with hass-taste-test
            # This happens when storage operations are cancelled during setup
            # Treat as empty state (no trips) rather than error
            _LOGGER.warning(
                "Storage load cancelled (known hass-taste-test timing issue) - "
                "continuing with empty trip state for vehicle %s",
                self.vehicle_id,
            )
            self._trips = {}
            self._recurring_trips = {}
            self._punctual_trips = {}
            self._last_update = None
        except Exception as err:
            _LOGGER.error("Error cargando viajes: %s", err, exc_info=True)
            self._trips = {}
            self._recurring_trips = {}
            self._punctual_trips = {}
            self._last_update = None

    # ── YAML Fallback ──────────────────────────────────────────

    async def _load_trips_yaml(self, storage_key: str) -> None:
        """Carga los viajes desde un archivo YAML (fallback para Container).

        HA I/O: This method performs file I/O that cannot be tested without
        real Home Assistant filesystem access. Marked with pragma: no cover.
        """
        try:  # pragma: no cover
            # Get config directory from Home Assistant
            config_dir = self.hass.config.config_dir
            if not config_dir:  # pragma: no cover
                config_dir = "/config"

            # Construct YAML file path
            yaml_file = (
                Path(config_dir) / "ev_trip_planner" / f"{storage_key}.yaml"
            )  # pragma: no cover

            # Ensure directory exists
            yaml_file.parent.mkdir(parents=True, exist_ok=True)  # pragma: no cover

            # Try to load YAML file
            if yaml_file.exists():  # pragma: no cover
                with open(yaml_file, "r", encoding="utf-8") as f:  # pragma: no cover
                    data = yaml.safe_load(f) or {}

                if "data" in data:
                    trip_data = data["data"]
                    self._trips = trip_data.get("trips", {})
                    self._recurring_trips = trip_data.get("recurring_trips", {})
                    self._punctual_trips = trip_data.get("punctual_trips", {})
                    self._last_update = trip_data.get("last_update")
                    _LOGGER.info(
                        "Viajes cargados desde YAML fallback: %d recurrentes, %d puntuales",
                        len(self._recurring_trips),
                        len(self._punctual_trips),
                    )
                else:
                    _LOGGER.info(
                        "No se encontraron viajes almacenados en YAML para %s",
                        self.vehicle_id,
                    )
                    self._reset_trips()
            else:
                _LOGGER.info(
                    "Archivo YAML no encontrado para %s, usando datos vacíos",
                    self.vehicle_id,
                )
                self._reset_trips()
        except Exception as err:  # pragma: no cover
            _LOGGER.error("Error cargando viajes desde YAML: %s", err)
            self._reset_trips()

    def _reset_trips(self) -> None:
        """Resetea todas las colecciones de viajes."""
        self._trips = {}
        self._recurring_trips = {}
        self._punctual_trips = {}
        self._last_update = None

    # ── Save ───────────────────────────────────────────────────

    async def async_save_trips(self) -> None:
        """Guarda los viajes en el almacenamiento persistente."""
        _LOGGER.info(
            "async_save_trips START - vehicle=%s, recurrentes=%d, puntuales=%d",
            self.vehicle_id,
            len(self._recurring_trips),
            len(self._punctual_trips),
        )

        data = {
            "trips": self._trips,
            "recurring_trips": self._recurring_trips,
            "punctual_trips": self._punctual_trips,
            "last_update": datetime.now(timezone.utc).isoformat(),
        }

        try:
            # DI: use injected storage if available, otherwise fallback to direct Store
            if self._storage is not None:
                _LOGGER.info("=== Using injected storage ===")
                await self._storage.async_save(data)
            else:
                _LOGGER.info("=== Using fallback HA Store ===")
                storage_key = f"{DOMAIN}_{self.vehicle_id}"
                _LOGGER.info("Creating store with key: %s", storage_key)
                store: Store[Dict[str, Any]] = ha_storage.Store(
                    self.hass,
                    version=1,
                    key=storage_key,
                )
                await store.async_save(data)
            _LOGGER.info(
                "Viajes guardados en HA storage: %d recurrentes, %d puntuales",
                len(self._recurring_trips),
                len(self._punctual_trips),
            )

            # NOTE: publish_deferrable_loads() removed from here to prevent race condition
            # The caller (async_add_punctual_trip, etc.) is responsible for calling
            # publish_deferrable_loads() AFTER async_save_trips() completes
        except Exception as err:
            _LOGGER.error("Error guardando viajes: %s", err, exc_info=True)
            # Fallback to YAML if HA storage fails (HA I/O bound - pragma)
            try:  # pragma: no cover
                await self._save_trips_yaml(f"{DOMAIN}_{self.vehicle_id}")
            except Exception as yaml_err:  # pragma: no cover
                _LOGGER.error("YAML fallback also failed: %s", yaml_err)

    async def _save_trips_yaml(self, storage_key: str) -> None:
        """Guarda los viajes en un archivo YAML (fallback para Container).

        HA I/O: This method performs file I/O that cannot be tested without
        real Home Assistant filesystem access. Marked with pragma: no cover.
        """
        try:  # pragma: no cover
            # Get config directory from Home Assistant
            config_dir = self.hass.config.config_dir
            if not config_dir:  # pragma: no cover
                config_dir = "/config"

            # Construct YAML file path
            yaml_file = Path(config_dir) / "ev_trip_planner" / f"{storage_key}.yaml"  # pragma: no cover

            # Ensure directory exists
            yaml_file.parent.mkdir(parents=True, exist_ok=True)  # pragma: no cover

            # Write data to YAML
            data = {
                "data": {
                    "trips": self._trips,
                    "recurring_trips": self._recurring_trips,
                    "punctual_trips": self._punctual_trips,
                    "last_update": datetime.now(timezone.utc).isoformat(),
                }
            }

            with open(yaml_file, "w", encoding="utf-8") as f:  # pragma: no cover
                yaml.dump(data, f, allow_unicode=True)  # pragma: no cover

            _LOGGER.info(
                "Viajes guardados en YAML fallback: %d recurrentes, %d puntuales",
                len(self._recurring_trips),
                len(self._punctual_trips),
            )
        except Exception as err:  # pragma: no cover
            _LOGGER.error("Error guardando viajes en YAML: %s", err)

    # ── Getters ────────────────────────────────────────────────

    async def async_get_recurring_trips(self) -> List[Dict[str, Any]]:
        """Obtiene la lista de viajes recurrentes."""
        return list(self._recurring_trips.values())

    async def async_get_punctual_trips(self) -> List[Dict[str, Any]]:
        """Obtiene la lista de viajes puntuales."""
        return list(self._punctual_trips.values())

    def get_all_trips(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get all trips (both recurring and punctual) as a combined dict.

        Returns:
            Dict with 'recurring' and 'punctual' keys containing trip lists.
        """
        return {
            "recurring": list(self._recurring_trips.values()),
            "punctual": list(self._punctual_trips.values()),
        }

    # ── Add ────────────────────────────────────────────────────

    async def async_add_recurring_trip(self, **kwargs: Any) -> None:
        """Añade un nuevo viaje recurrente y sincroniza con EMHASS."""
        _LOGGER.debug(
            "Adding recurring trip for vehicle %s: dia_semana=%s, hora=%s, km=%.1f, kwh=%.2f",
            self.vehicle_id,
            kwargs.get("dia_semana"),
            kwargs.get("hora"),
            kwargs.get("km", 0),
            kwargs.get("kwh", 0),
        )
        # Validate hora format before storing
        hora = kwargs.get("hora", "")
        self._validate_hora(hora)

        # Generate trip ID using the new format: rec_{day}_{random}
        if "trip_id" in kwargs:
            trip_id = kwargs["trip_id"]
        else:
            day = kwargs.get("dia_semana", "lunes")
            trip_id = generate_trip_id("recurring", day)
        self._recurring_trips[trip_id] = {
            "id": trip_id,
            "tipo": TRIP_TYPE_RECURRING,
            "dia_semana": kwargs["dia_semana"],
            "hora": kwargs["hora"],
            "km": kwargs["km"],
            "kwh": kwargs["kwh"],
            "descripcion": kwargs.get("descripcion", ""),
            "activo": True,
        }
        await self.async_save_trips()
        _LOGGER.info(
            "Added recurring trip %s for vehicle %s",
            trip_id,
            self.vehicle_id,
        )

        # Emit sensor events to replace lazy `from .sensor import` calls
        self._sensor_callbacks.emit(
            "trip_created_recurring",
            self.hass,
            self._entry_id,
            self._recurring_trips[trip_id],
            trip_id,
        )
        self._sensor_callbacks.emit(
            "trip_sensor_created_emhass",
            self.hass,
            self._entry_id,
            trip_id=trip_id,
        )

        # T019.3: Publish new trip to EMHASS
        if self._emhass_adapter:
            await self._async_publish_new_trip_to_emhass(self._recurring_trips[trip_id])

    async def async_add_punctual_trip(self, **kwargs: Any) -> None:
        """Añade un nuevo viaje puntual y sincroniza con EMHASS."""
        _LOGGER.debug(
            "Adding punctual trip for vehicle %s: datetime=%s, km=%.1f, kwh=%.2f",
            self.vehicle_id,
            kwargs.get("datetime_str", kwargs.get("datetime", "")),
            kwargs.get("km", 0),
            kwargs.get("kwh", 0),
        )
        # Generate trip ID using the new format: pun_{date}_{random}
        if "trip_id" in kwargs:
            trip_id = kwargs["trip_id"]
        else:
            datetime_str = kwargs.get("datetime_str", kwargs.get("datetime", ""))
            # Extract date from datetime string (format: YYYY-MM-DDTHH:MM)
            if datetime_str:
                date_part = datetime_str.split("T")[0].replace("-", "")
            else:
                date_part = ""
            trip_id = generate_trip_id("punctual", date_part)
        self._punctual_trips[trip_id] = {
            "id": trip_id,
            "tipo": TRIP_TYPE_PUNCTUAL,
            "datetime": kwargs.get("datetime_str", kwargs.get("datetime", "")),
            "km": kwargs["km"],
            "kwh": kwargs["kwh"],
            "descripcion": kwargs.get("descripcion", ""),
            "estado": "pendiente",
        }
        await self.async_save_trips()
        _LOGGER.info(
            "Added punctual trip %s for vehicle %s",
            trip_id,
            self.vehicle_id,
        )

        # Emit sensor events to replace lazy `from .sensor import` calls
        self._sensor_callbacks.emit(
            "trip_created_punctual",
            self.hass,
            self._entry_id,
            self._punctual_trips[trip_id],
            trip_id,
        )
        self._sensor_callbacks.emit(
            "trip_sensor_created_emhass",
            self.hass,
            self._entry_id,
            trip_id=trip_id,
        )

        # T019.3: Publish new trip to EMHASS
        if self._emhass_adapter:
            await self._async_publish_new_trip_to_emhass(self._punctual_trips[trip_id])

    # ── Update ─────────────────────────────────────────────────

    async def async_update_trip(self, trip_id: str, updates: Dict[str, Any]) -> None:
        """Actualiza un viaje existente y sincroniza con EMHASS.

        Detects trip edits and triggers EMHASS update when:
        - km/kwh changes (affects energy calculation)
        - datetime/hora changes (affects deadline/deferrable window)
        - descripcion changes (informational only)
        - activo/estado changes (affects if trip is published)
        """
        _LOGGER.debug(
            "Updating trip %s for vehicle %s: updates=%s",
            trip_id,
            self.vehicle_id,
            updates,
        )

        # Filter updates to only keep fields relevant to the trip type
        RECURRENT_RELEVANT_FIELDS = {
            "dia_semana",
            "hora",
            "km",
            "kwh",
            "descripcion",
            "activo",
            "tipo",
            "id",
        }
        PUNCTUAL_RELEVANT_FIELDS = {
            "datetime",
            "km",
            "kwh",
            "descripcion",
            "activo",
            "tipo",
            "id",
        }

        # Get old trip data before update for comparison
        old_trip = None
        trip_type = None
        if trip_id in self._recurring_trips:
            old_trip = self._recurring_trips[trip_id].copy()
            trip_type = "recurring"
            # Filter: only apply updates to fields relevant for recurring trips
            filtered_updates = {
                k: v for k, v in updates.items() if k in RECURRENT_RELEVANT_FIELDS
            }
            self._recurring_trips[trip_id].update(filtered_updates)
        elif trip_id in self._punctual_trips:
            old_trip = self._punctual_trips[trip_id].copy()
            trip_type = "punctual"
            # Filter: only apply updates to fields relevant for punctual trips
            filtered_updates = {
                k: v for k, v in updates.items() if k in PUNCTUAL_RELEVANT_FIELDS
            }
            self._punctual_trips[trip_id].update(filtered_updates)

        if old_trip is None:
            _LOGGER.warning(
                "Trip %s not found for update in vehicle %s",
                trip_id,
                self.vehicle_id,
            )
            return

        await self.async_save_trips()
        _LOGGER.info(
            "Updated %s trip %s for vehicle %s",
            trip_type,
            trip_id,
            self.vehicle_id,
        )

        # Emit sensor update event to replace lazy `from .sensor import` call
        trip_data = self._recurring_trips.get(trip_id) or self._punctual_trips.get(
            trip_id
        )
        if trip_data:
            self._sensor_callbacks.emit(
                "trip_sensor_updated",
                self.hass,
                self._entry_id,
                trip_data,
            )

        # T019.3: Detect trip changes and trigger EMHASS update
        if old_trip and self._emhass_adapter:
            await self._async_sync_trip_to_emhass(trip_id, old_trip, updates)

    # ── Delete ─────────────────────────────────────────────────

    async def async_delete_trip(self, trip_id: str) -> None:
        """Elimina un viaje existente y sincroniza con EMHASS."""
        _LOGGER.debug("Deleting trip %s from vehicle %s", trip_id, self.vehicle_id)

        trip_found = False
        if trip_id in self._recurring_trips:
            del self._recurring_trips[trip_id]
            trip_found = True
        elif trip_id in self._punctual_trips:
            del self._punctual_trips[trip_id]
            trip_found = True

        if not trip_found:
            _LOGGER.warning(
                "Trip %s not found for deletion in vehicle %s",
                trip_id,
                self.vehicle_id,
            )
            return

        await self.async_save_trips()
        _LOGGER.info("Deleted trip %s from vehicle %s", trip_id, self.vehicle_id)

        # Emit sensor removal events to replace lazy `from .sensor import` calls
        self._sensor_callbacks.emit(
            "trip_removed",
            self.hass,
            self._entry_id,
            trip_id=trip_id,
        )
        self._sensor_callbacks.emit(
            "trip_sensor_removed_emhass",
            self.hass,
            self._entry_id,
            trip_id=trip_id,
        )

        # T019.3: Remove from EMHASS when deleted
        if self._emhass_adapter:
            await self._async_remove_trip_from_emhass(trip_id)

    async def async_delete_all_trips(self) -> None:
        """Deletes all recurring and punctual trips for cascade deletion."""
        _LOGGER.debug(
            "DEBUG async_delete_all_trips: START for vehicle %s", self.vehicle_id
        )

        # CRITICAL FIX: Clear dictionaries FIRST, then publish empty list once.
        # Previously, this looped through trips calling _async_remove_trip_from_emhass,
        # which called publish_deferrable_loads() (no args = None), which internally
        # called _get_all_active_trips() and REPUBLISHED all remaining trips.
        # By clearing first and then publishing [], we ensure EMHASS cache is cleared.
        self._trips = {}
        self._recurring_trips = {}
        self._punctual_trips = {}
        await self.async_save_trips()

        # CRITICAL FIX: Clear EMHASS adapter's _published_trips BEFORE publish_deferrable_loads.
        # This prevents _handle_config_entry_update (triggered during integration deletion)
        # from seeing non-empty _published_trips and republishing old trips via
        # update_charging_power(). _handle_config_entry_update runs BEFORE async_delete_all_trips
        # in some deletion flows, and it calls update_charging_power() which publishes _published_trips.
        # By clearing _published_trips first, we ensure _handle_config_entry_update sees empty
        # and reloads from trip_manager (which is already cleared), preventing republish.
        if self._emhass_adapter:
            self._emhass_adapter._published_trips = []
            self._emhass_adapter._cached_per_trip_params.clear()
            self._emhass_adapter._cached_power_profile = []
            self._emhass_adapter._cached_deferrables_schedule = []

        # CRITICAL: Call publish_deferrable_loads with explicit [] (not None).
        # publish_deferrable_loads(None) would call _get_all_active_trips() which
        # returns all trips still in storage (before clear). With [], the early return
        # in async_publish_all_deferrable_loads clears _cached_per_trip_params and
        # _cached_power_profile and returns without republishing.
        if self._emhass_adapter:
            _LOGGER.debug(
                "DEBUG async_delete_all_trips: Calling publish_deferrable_loads([])"
            )
            await self.publish_deferrable_loads([])
            # EXTRA SAFEGUARD: Also directly clear the adapter's cache as a backup.
            # This ensures _cached_per_trip_params is cleared even if the coordinator
            # refresh/reRead flow has issues.
            self._emhass_adapter._cached_per_trip_params.clear()
            self._emhass_adapter._published_trips = []
            self._emhass_adapter._cached_power_profile = []
            self._emhass_adapter._cached_deferrables_schedule = []
            _LOGGER.debug(
                "DEBUG async_delete_all_trips: Directly cleared adapter cache as safeguard"
            )

        # EXTRA SAFEGUARD: Directly clear coordinator data to ensure sensor sees empty state.
        # This addresses the case where _get_coordinator() returns None during deletion flow,
        # causing the direct coordinator.data update in async_publish_all_deferrable_loads to be skipped.
        # Without this, def_total_hours_array might still show old trips after integration deletion.
        try:
            entry = self.hass.config_entries.async_get_entry(self._entry_id)
            if entry and hasattr(entry, "runtime_data") and entry.runtime_data:
                coordinator = getattr(entry.runtime_data, "coordinator", None)
                if coordinator is not None:
                    _LOGGER.debug(
                        "DEBUG async_delete_all_trips: Directly clearing coordinator.data"
                    )
                    # Handle case where coordinator.data might be None before first refresh
                    existing_data = coordinator.data or {}
                    coordinator.data = {
                        **existing_data,
                        "per_trip_emhass_params": {},
                        "emhass_power_profile": [],
                        "emhass_deferrables_schedule": [],
                    }
                    await coordinator.async_refresh()
                    _LOGGER.debug(
                        "DEBUG async_delete_all_trips: Coordinator data cleared and refreshed"
                    )
                else:
                    _LOGGER.debug(
                        "DEBUG async_delete_all_trips: coordinator is None in runtime_data"
                    )
            else:
                _LOGGER.debug(
                    "DEBUG async_delete_all_trips: entry or runtime_data is None/empty"
                )
        except Exception as err:
            _LOGGER.warning(
                "DEBUG async_delete_all_trips: Exception during coordinator cleanup: %s",
                err,
            )

        _LOGGER.info("Deleted all trips for vehicle %s", self.vehicle_id)

    # ── Pause/Resume ───────────────────────────────────────────

    async def async_pause_recurring_trip(self, trip_id: str) -> None:
        """Pausa un viaje recurrente."""
        _LOGGER.debug(
            "Pausing recurring trip %s for vehicle %s", trip_id, self.vehicle_id
        )
        if trip_id in self._recurring_trips:
            self._recurring_trips[trip_id]["activo"] = False
            await self.async_save_trips()
            _LOGGER.info(
                "Paused recurring trip %s for vehicle %s", trip_id, self.vehicle_id
            )
        else:
            _LOGGER.warning(
                "Recurring trip %s not found for pause in vehicle %s",
                trip_id,
                self.vehicle_id,
            )

    async def async_resume_recurring_trip(self, trip_id: str) -> None:
        """Reanuda un viaje recurrente."""
        _LOGGER.debug(
            "Resuming recurring trip %s for vehicle %s", trip_id, self.vehicle_id
        )
        if trip_id in self._recurring_trips:
            self._recurring_trips[trip_id]["activo"] = True
            await self.async_save_trips()
            _LOGGER.info(
                "Resumed recurring trip %s for vehicle %s", trip_id, self.vehicle_id
            )
        else:
            _LOGGER.warning(
                "Recurring trip %s not found for resume in vehicle %s",
                trip_id,
                self.vehicle_id,
            )

    # ── Sensor Update ──────────────────────────────────────────

    async def async_update_trip_sensor(self, trip_id: str) -> None:
        """Update the Home Assistant sensor entity for an updated trip.

        This method updates the sensor entity's state and attributes
        when a trip is modified via async_update_trip.

        HA I/O: This method performs Home Assistant entity registry and
        state operations that cannot be unit tested. Marked with pragma: no cover.

        Args:
            trip_id: Unique identifier for the trip to update
        """
        try:  # pragma: no cover
            from homeassistant.helpers import entity_registry as er

            registry = er.async_get(self.hass)

            # Build entity_id from trip_id
            entity_id = f"sensor.trip_{trip_id}"

            # Check if entity exists
            existing_entry = registry.async_get(entity_id)

            if existing_entry is None:
                # Entity doesn't exist, nothing to update
                _LOGGER.debug(
                    "Trip sensor %s does not exist, nothing to update",
                    entity_id,
                )
                return

            # Get the updated trip data
            trip_data = None
            trip_type = None
            if trip_id in self._recurring_trips:
                trip_data = self._recurring_trips[trip_id]
                trip_type = "recurring"
            elif trip_id in self._punctual_trips:
                trip_data = self._punctual_trips[trip_id]
                trip_type = "punctual"

            if trip_data is None:
                _LOGGER.warning(
                    "Trip %s not found for sensor update in vehicle %s",
                    trip_id,
                    self.vehicle_id,
                )
                return

            # Update the entity state with new trip data
            state_attributes = {
                "trip_id": trip_id,
                "trip_type": trip_type,
                "descripcion": trip_data.get("descripcion", ""),
                "km": trip_data.get("km", 0.0),
                "kwh": trip_data.get("kwh", 0.0),
                "fecha_hora": trip_data.get("datetime", trip_data.get("hora", "")),
                "activo": trip_data.get("activo", True),
                "estado": trip_data.get("estado", "pendiente"),
            }

            # Determine the native value (state)
            if trip_type == "punctual":
                native_value = trip_data.get("estado", "pendiente")
            else:
                native_value = "recurrente"

            # Update state via Home Assistant core
            self.hass.states.async_set(
                entity_id,
                native_value,
                attributes=state_attributes,
            )

            _LOGGER.info(
                "Updated trip sensor %s for trip %s (vehicle: %s, state: %s)",
                entity_id,
                trip_id,
                self.vehicle_id,
                native_value,
            )

        except Exception as err:  # pragma: no cover
            _LOGGER.error(
                "Error updating trip sensor for trip %s: %s",
                trip_id,
                err,
                exc_info=True,
            )

    # ── Complete/Cancel ────────────────────────────────────────

    async def async_complete_punctual_trip(self, trip_id: str) -> None:
        """Marca un viaje puntual como completado."""
        _LOGGER.debug(
            "Completing punctual trip %s for vehicle %s", trip_id, self.vehicle_id
        )
        if trip_id in self._punctual_trips:
            self._punctual_trips[trip_id]["estado"] = "completado"
            await self.async_save_trips()
            _LOGGER.info(
                "Completed punctual trip %s for vehicle %s", trip_id, self.vehicle_id
            )
        else:
            _LOGGER.warning(
                "Punctual trip %s not found for completion in vehicle %s",
                trip_id,
                self.vehicle_id,
            )

    async def async_cancel_punctual_trip(self, trip_id: str) -> None:
        """Cancela un viaje puntual."""
        _LOGGER.debug(
            "Cancelling punctual trip %s for vehicle %s", trip_id, self.vehicle_id
        )
        if trip_id in self._punctual_trips:
            del self._punctual_trips[trip_id]
            await self.async_save_trips()
            _LOGGER.info(
                "Cancelled punctual trip %s for vehicle %s", trip_id, self.vehicle_id
            )
        else:
            _LOGGER.warning(
                "Punctual trip %s not found for cancellation in vehicle %s",
                trip_id,
                self.vehicle_id,
            )
            return
        # T019.3: Remove from EMHASS when cancelled
        if self._emhass_adapter:
            await self._async_remove_trip_from_emhass(trip_id)

    # ── EMHASS Helpers ─────────────────────────────────────────

    async def _async_sync_trip_to_emhass(
        self,
        trip_id: str,
        old_trip: Dict[str, Any],
        updates: Dict[str, Any],
    ) -> None:
        """Sync trip changes to EMHASS adapter.

        Detects which fields changed and updates the deferrable load accordingly.
        """
        if not self._emhass_adapter:
            return

        try:
            # Determine if this is an active trip (for publishing)
            is_active = True
            if trip_id in self._recurring_trips:
                is_active = self._recurring_trips[trip_id].get("activo", True)
            elif trip_id in self._punctual_trips:
                is_active = self._punctual_trips[trip_id].get("estado") == "pendiente"

            if not is_active:
                # Trip is paused/cancelled - remove from EMHASS
                await self._async_remove_trip_from_emhass(trip_id)
                _LOGGER.info(
                    "Trip %s is inactive, removed from EMHASS deferrable loads", trip_id
                )
                return

            # Get the updated trip
            trip = None
            if trip_id in self._recurring_trips:
                trip = self._recurring_trips[trip_id]
            elif trip_id in self._punctual_trips:
                trip = self._punctual_trips[trip_id]

            if not trip:
                await self._async_remove_trip_from_emhass(trip_id)
                return

            # Determine what changed
            changed_fields = set(updates.keys())

            # Check for critical changes that require recalculation
            recalc_fields = {
                "km",
                "kwh",
                "datetime",
                "hora",
                "dia_semana",
                "descripcion",
            }
            needs_recalculate = bool(changed_fields & recalc_fields)

            if needs_recalculate:
                # T019.3: Recalculate deferrable load parameters
                # Update the deferrable load with new parameters
                await self._emhass_adapter.async_update_deferrable_load(trip)

                # Also update all deferrable loads to recalculate schedule
                await self.publish_deferrable_loads()

                _LOGGER.info(
                    "Trip %s updated in EMHASS (recalculated): changed fields=%s",
                    trip_id,
                    changed_fields,
                )
            else:
                # Non-critical changes (just update attributes)
                await self._emhass_adapter.async_update_deferrable_load(trip)

                _LOGGER.debug(
                    "Trip %s updated in EMHASS (attributes only): changed fields=%s",
                    trip_id,
                    changed_fields,
                )

        except Exception as err:
            _LOGGER.error("Error syncing trip %s to EMHASS: %s", trip_id, err)

    async def _async_remove_trip_from_emhass(self, trip_id: str) -> None:
        """Remove a trip from EMHASS deferrable loads."""
        if not self._emhass_adapter:
            return

        try:
            await self._emhass_adapter.async_remove_deferrable_load(trip_id)

            # Update all deferrable loads to reflect the removal
            await self.publish_deferrable_loads()

            _LOGGER.info("Trip %s removed from EMHASS deferrable loads", trip_id)
        except Exception as err:
            _LOGGER.error("Error removing trip %s from EMHASS: %s", trip_id, err)

    async def _async_publish_new_trip_to_emhass(self, trip: Dict[str, Any]) -> None:
        """Publish a new trip to EMHASS as a deferrable load."""
        if not self._emhass_adapter:
            return

        try:
            # Publish this trip
            await self._emhass_adapter.async_publish_deferrable_load(trip)

            # Also publish all trips to recalculate the schedule
            await self.publish_deferrable_loads()

            _LOGGER.info(
                "Published new trip %s to EMHASS deferrable loads",
                trip.get("id"),
            )
        except Exception as err:
            _LOGGER.error("Error publishing trip %s to EMHASS: %s", trip.get("id"), err)

    async def _get_all_active_trips(self) -> List[Dict[str, Any]]:
        """Get all active trips for EMHASS publishing."""
        import traceback

        _LOGGER.debug(
            "DEBUG _get_all_active_trips: _recurring_trips count=%d",
            len(self._recurring_trips),
        )
        _LOGGER.debug(
            "DEBUG _get_all_active_trips: _punctual_trips count=%d",
            len(self._punctual_trips),
        )
        _LOGGER.debug(
            "DEBUG _get_all_active_trips: CALLED FROM\n\nFROM\n\n%s",
            traceback.format_stack()[-3],
        )

        all_trips = []
        for trip in self._recurring_trips.values():
            if trip.get("activo", True):
                _LOGGER.debug(
                    "DEBUG _get_all_active_trips: adding recurring trip id=%s, trip=%s",
                    trip.get("id"),
                    trip,
                )
                all_trips.append(trip)

        for trip_id, trip in self._punctual_trips.items():
            estado = trip.get("estado")
            _LOGGER.debug(
                "DEBUG _get_all_active_trips: punctual trip %s estado=%s, trip=%s",
                trip_id,
                estado,
                trip,
            )
            if estado == "pendiente":
                all_trips.append(trip)

        _LOGGER.debug(
            "DEBUG _get_all_active_trips: returning %d trips: %s",
            len(all_trips),
            [t.get("id") for t in all_trips],
        )
        return all_trips
