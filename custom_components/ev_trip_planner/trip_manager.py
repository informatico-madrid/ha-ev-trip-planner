"""Gestión central de viajes y optimización de carga para vehículos eléctricos.

Implementa la lógica de planificación de viajes, cálculo de energía necesaria
y sincronización con EMHASS. Cumple con las reglas de Home Assistant 2026 para
runtime_data y tipado estricto.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, TypedDict

import yaml
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from .const import (
    CONF_CHARGING_POWER,
    DEFAULT_CHARGING_POWER,
    DEFAULT_SOC_BUFFER_PERCENT,
    DOMAIN,
    TRIP_TYPE_PUNCTUAL,
    TRIP_TYPE_RECURRING,
)
from .emhass_adapter import EMHASSAdapter
from .utils import calcular_energia_kwh, generate_trip_id
from .vehicle_controller import VehicleController

_LOGGER = logging.getLogger(__name__)

# Days of week in Spanish (lowercase)
DAYS_OF_WEEK = (
    "lunes",
    "martes",
    "miercoles",
    "jueves",
    "viernes",
    "sabado",
    "domingo",
)


class CargaVentana(TypedDict):
    """Structure for charging window information."""

    ventana_horas: float
    kwh_necesarios: float
    horas_carga_necesarias: float
    inicio_ventana: Optional[datetime]
    fin_ventana: Optional[datetime]
    es_suficiente: bool


class SOCMilestoneResult(TypedDict):
    """Return structure for calcular_hitos_soc function.

    Contains SOC milestone calculation results for a single trip,
    including the target SOC, energy requirements, accumulated deficit
    from backward propagation, and charging window details.
    """

    trip_id: str
    soc_objetivo: float
    kwh_necesarios: float
    deficit_acumulado: float
    ventana_carga: CargaVentana


class TripManager:
    """Gestión central de viajes y optimización de carga para vehículos eléctricos.

    Esta clase implementa la lógica de planificación de viajes, cálculo de energía
    necesaria y sincronización con EMHASS. Cumple con las reglas de Home Assistant
    2026 para runtime_data y tipado estricto.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        vehicle_id: str,
        presence_config: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Inicializa el gestor de viajes para un vehículo específico."""
        self.hass = hass
        self.vehicle_id = vehicle_id
        self.vehicle_controller = VehicleController(
            hass, vehicle_id, presence_config, self
        )
        self._trips: Dict[str, Any] = {}
        self._recurring_trips: Dict[str, Any] = {}
        self._punctual_trips: Dict[str, Any] = {}
        self._last_update: Optional[datetime] = None
        self._emhass_adapter: Optional[EMHASSAdapter] = None

    def set_emhass_adapter(self, adapter: EMHASSAdapter) -> None:
        """Set the EMHASS adapter for this trip manager."""
        self._emhass_adapter = adapter
        _LOGGER.debug("EMHASS adapter set for vehicle %s", self.vehicle_id)

    def get_emhass_adapter(self) -> Optional[EMHASSAdapter]:
        """Get the EMHASS adapter for this trip manager."""
        return self._emhass_adapter

    async def _publish_deferrable_loads(self) -> None:
        """Publish current trips to EMHASS as deferrable loads."""
        if not self._emhass_adapter:
            return
        all_trips = await self._get_all_active_trips()
        charging_power_kw = self._get_charging_power()
        await self._emhass_adapter.publish_deferrable_loads(
            all_trips,
            charging_power_kw,
        )

    async def async_setup(self) -> None:
        """Configura el gestor de viajes y carga los datos desde el almacenamiento."""
        _LOGGER.info("Configurando gestor de viajes para vehículo: %s", self.vehicle_id)
        await self.vehicle_controller.async_setup()
        await self._load_trips()

    async def _load_trips(self) -> None:
        """Carga los viajes desde el almacenamiento persistente."""
        _LOGGER.warning("=== _load_trips START === vehicle=%s", self.vehicle_id)
        try:
            from homeassistant.helpers import storage as ha_storage

            storage_key = f"{DOMAIN}_{self.vehicle_id}"
            _LOGGER.warning("=== Loading from store with key: %s ===", storage_key)

            # Use HA's official Store API for persistence
            store = ha_storage.Store(
                self.hass,
                version=1,
                key=storage_key,
            )
            _LOGGER.warning("=== Store created with key: %s ===", storage_key)

            stored_data = await store.async_load()
            _LOGGER.warning("=== async_load returned: %s ===", stored_data is not None)
            _LOGGER.warning("=== stored_data type: %s ===", type(stored_data).__name__)
            _LOGGER.warning("=== stored_data value: %s ===", stored_data)
            if stored_data:
                _LOGGER.warning(
                    "=== stored_data structure: %s ===",
                    (
                        list(stored_data.keys())
                        if isinstance(stored_data, dict)
                        else "not a dict"
                    ),
                )
                _LOGGER.warning(
                    "=== stored_data['data'] exists: %s ===",
                    "data" in stored_data if isinstance(stored_data, dict) else False,
                )

                # Store API retorna datos dentro de la clave "data"
                if isinstance(stored_data, dict) and "data" in stored_data:
                    data = stored_data.get("data", {})
                else:
                    # Fallback: use stored_data directly if no "data" key
                    data = stored_data
                _LOGGER.warning("=== data extracted: %s ===", data)
                _LOGGER.warning(
                    "=== data from stored_data.get('data', {}): %s ===", data
                )

                self._trips = data.get("trips", {})
                self._recurring_trips = data.get("recurring_trips", {})
                self._punctual_trips = data.get("punctual_trips", {})
                self._last_update = data.get("last_update")

                _LOGGER.warning("=== AFTER LOAD ===")
                _LOGGER.warning("=== self._trips: %d trips ===", len(self._trips))
                _LOGGER.warning(
                    "=== self._recurring_trips: %d recurrentes ===",
                    len(self._recurring_trips),
                )
                _LOGGER.warning(
                    "=== self._punctual_trips: %d puntuales ===",
                    len(self._punctual_trips),
                )

                # Log detailed trip info
                if self._recurring_trips:
                    _LOGGER.warning(
                        "=== Recurring trips IDs: %s ===",
                        list(self._recurring_trips.keys())[:5],
                    )
                if self._punctual_trips:
                    _LOGGER.warning(
                        "=== Punctual trips IDs: %s ===",
                        list(self._punctual_trips.keys())[:5],
                    )
            else:
                _LOGGER.warning(
                    "No se encontraron viajes almacenados para %s",
                    self.vehicle_id,
                )
                self._trips = {}
                self._recurring_trips = {}
                self._punctual_trips = {}
                self._last_update = None
        except asyncio.CancelledError:
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

    async def _load_trips_yaml(self, storage_key: str) -> None:
        """Carga los viajes desde un archivo YAML (fallback para Container)."""
        try:
            # Get config directory from Home Assistant
            config_dir = self.hass.config.config_dir
            if not config_dir:
                config_dir = "/config"

            # Construct YAML file path
            yaml_file = Path(config_dir) / "ev_trip_planner" / f"{storage_key}.yaml"

            # Ensure directory exists
            yaml_file.parent.mkdir(parents=True, exist_ok=True)

            # Try to load YAML file
            if yaml_file.exists():
                with open(yaml_file, "r", encoding="utf-8") as f:
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
        except Exception as err:
            _LOGGER.error("Error cargando viajes desde YAML: %s", err)
            self._reset_trips()

    def _reset_trips(self) -> None:
        """Resetea todas las colecciones de viajes."""
        self._trips = {}
        self._recurring_trips = {}
        self._punctual_trips = {}
        self._last_update = None

    async def async_save_trips(self) -> None:
        """Guarda los viajes en el almacenamiento persistente."""
        _LOGGER.info(
            "async_save_trips START - vehicle=%s, recurrentes=%d, puntuales=%d",
            self.vehicle_id,
            len(self._recurring_trips),
            len(self._punctual_trips),
        )
        try:
            from homeassistant.helpers import storage as ha_storage

            storage_key = f"{DOMAIN}_{self.vehicle_id}"
            _LOGGER.info("Creating store with key: %s", storage_key)

            # Use HA's official Store API for persistence
            store = ha_storage.Store(
                self.hass,
                version=1,
                key=storage_key,
            )

            data = {
                "trips": self._trips,
                "recurring_trips": self._recurring_trips,
                "punctual_trips": self._punctual_trips,
                "last_update": datetime.now().isoformat(),
            }

            _LOGGER.info(
                "About to call async_save with data keys: %s", list(data.keys())
            )
            await store.async_save(data)
            _LOGGER.info(
                "Viajes guardados en HA storage: %d recurrentes, %d puntuales",
                len(self._recurring_trips),
                len(self._punctual_trips),
            )

            # T019.3: Trigger EMHASS adapter update when trip state changes
            if self._emhass_adapter:
                await self._publish_deferrable_loads()
        except Exception as err:
            _LOGGER.error("Error guardando viajes: %s", err, exc_info=True)
            # Fallback to YAML if HA storage fails
            try:
                await self._save_trips_yaml(f"{DOMAIN}_{self.vehicle_id}")
            except Exception as yaml_err:
                _LOGGER.error("YAML fallback also failed: %s", yaml_err)

    async def _save_trips_yaml(self, storage_key: str) -> None:
        """Guarda los viajes en un archivo YAML (fallback para Container)."""
        try:
            # Get config directory from Home Assistant
            config_dir = self.hass.config.config_dir
            if not config_dir:
                config_dir = "/config"

            # Construct YAML file path
            yaml_file = Path(config_dir) / "ev_trip_planner" / f"{storage_key}.yaml"

            # Ensure directory exists
            yaml_file.parent.mkdir(parents=True, exist_ok=True)

            # Prepare data
            data = {
                "version": 1,
                "data": {
                    "trips": self._trips,
                    "recurring_trips": self._recurring_trips,
                    "punctual_trips": self._punctual_trips,
                    "last_update": datetime.now().isoformat(),
                },
            }

            # Write to YAML file
            with open(yaml_file, "w", encoding="utf-8") as f:
                yaml.dump(data, f, default_flow_style=False, allow_unicode=True)

            _LOGGER.info(
                "Viajes guardados en YAML fallback: %d recurrentes, %d puntuales",
                len(self._recurring_trips),
                len(self._punctual_trips),
            )
        except Exception as err:
            _LOGGER.error("Error guardando viajes en YAML: %s", err)

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
        # Generate trip ID using the new format: rec_{day}_{random}
        if "trip_id" in kwargs:
            trip_id = kwargs["trip_id"]
        else:
            day = kwargs.get("dia_semana", "lunes")
            trip_id = generate_trip_id(TRIP_TYPE_RECURRING, day)
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

        # T034: Create sensor entity for the trip
        await self.async_create_trip_sensor(trip_id, self._recurring_trips[trip_id])

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
            trip_id = generate_trip_id(TRIP_TYPE_PUNCTUAL, date_part)
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

        # T034: Create sensor entity for the trip
        await self.async_create_trip_sensor(trip_id, self._punctual_trips[trip_id])

        # T019.3: Publish new trip to EMHASS
        if self._emhass_adapter:
            await self._async_publish_new_trip_to_emhass(self._punctual_trips[trip_id])

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
        # Get old trip data before update for comparison
        old_trip = None
        trip_type = None
        if trip_id in self._recurring_trips:
            old_trip = self._recurring_trips[trip_id].copy()
            self._recurring_trips[trip_id].update(updates)
            trip_type = "recurring"
        elif trip_id in self._punctual_trips:
            old_trip = self._punctual_trips[trip_id].copy()
            self._punctual_trips[trip_id].update(updates)
            trip_type = "punctual"

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

        # T035: Update the sensor entity for the trip
        await self.async_update_trip_sensor(trip_id)

        # T019.3: Detect trip changes and trigger EMHASS update
        if old_trip and self._emhass_adapter:
            await self._async_sync_trip_to_emhass(trip_id, old_trip, updates)

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

        # T034: Remove sensor entity for the trip
        await self.async_remove_trip_sensor(trip_id)

        # T019.3: Remove from EMHASS when deleted
        if self._emhass_adapter:
            await self._async_remove_trip_from_emhass(trip_id)

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

    async def async_update_trip_sensor(self, trip_id: str) -> None:
        """Update the Home Assistant sensor entity for an updated trip.

        This method updates the sensor entity's state and attributes
        when a trip is modified via async_update_trip.

        Args:
            trip_id: Unique identifier for the trip to update
        """
        try:
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

            # Update the sensor state via Home Assistant API
            from homeassistant.helpers import device_registry

            # Get the device ID for this vehicle
            device_reg = device_registry.async_get(self.hass)
            device_id = None
            for dev in device_reg.devices.values():
                if dev.identifiers and (DOMAIN, self.vehicle_id) in dev.identifiers:
                    device_id = dev.id
                    break

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
                state_attributes=state_attributes,
                device_id=device_id,
            )

            _LOGGER.info(
                "Updated trip sensor %s for trip %s (vehicle: %s, state: %s)",
                entity_id,
                trip_id,
                self.vehicle_id,
                native_value,
            )

        except Exception as err:
            _LOGGER.error(
                "Error updating trip sensor for trip %s: %s",
                trip_id,
                err,
                exc_info=True,
            )

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
                await self._publish_deferrable_loads()

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

        except Exception as err:  # pragma: no cover
            _LOGGER.error("Error syncing trip %s to EMHASS: %s", trip_id, err)

    async def _async_remove_trip_from_emhass(self, trip_id: str) -> None:
        """Remove a trip from EMHASS deferrable loads."""
        if not self._emhass_adapter:
            return

        try:
            await self._emhass_adapter.async_remove_deferrable_load(trip_id)

            # Update all deferrable loads to reflect the removal
            await self._publish_deferrable_loads()

            _LOGGER.info("Trip %s removed from EMHASS deferrable loads", trip_id)
        except Exception as err:  # pragma: no cover
            _LOGGER.error("Error removing trip %s from EMHASS: %s", trip_id, err)

    async def _async_publish_new_trip_to_emhass(self, trip: Dict[str, Any]) -> None:
        """Publish a new trip to EMHASS as a deferrable load."""
        if not self._emhass_adapter:
            return

        try:
            # Publish this trip
            await self._emhass_adapter.async_publish_deferrable_load(trip)

            # Also publish all trips to recalculate the schedule
            await self._publish_deferrable_loads()

            _LOGGER.info(
                "Published new trip %s to EMHASS deferrable loads",
                trip.get("id"),
            )
        except Exception as err:  # pragma: no cover
            _LOGGER.error("Error publishing trip %s to EMHASS: %s", trip.get("id"), err)

    async def _get_all_active_trips(self) -> List[Dict[str, Any]]:
        """Get all active trips for EMHASS publishing."""
        all_trips = []
        for trip in self._recurring_trips.values():
            if trip.get("activo", True):
                all_trips.append(trip)
        for trip in self._punctual_trips.values():
            if trip.get("estado") == "pendiente":
                all_trips.append(trip)
        return all_trips

    async def async_get_kwh_needed_today(self) -> float:
        """Calcula la energía necesaria para hoy basado en los viajes."""
        today = datetime.now().date()
        total_kwh = 0.0
        for trip in self._recurring_trips.values():
            if trip["activo"] and self._is_trip_today(trip, today):
                total_kwh += trip["kwh"]
        for trip in self._punctual_trips.values():
            if trip["estado"] == "pendiente" and self._is_trip_today(trip, today):
                total_kwh += trip["kwh"]
        return total_kwh

    async def async_get_hours_needed_today(self) -> int:
        """Calcula las horas necesarias para cargar hoy."""
        import math

        kwh_needed = await self.async_get_kwh_needed_today()
        charging_power = self._get_charging_power()
        return math.ceil(kwh_needed / charging_power) if charging_power > 0 else 0

    def _get_charging_power(self) -> float:
        """Obtiene la potencia de carga desde la configuración."""
        try:
            # Buscar config entry por vehicle_name (vehicle_id es vehicle_name, no entry_id)
            entry = None
            for config_entry in self.hass.config_entries.async_entries(DOMAIN):
                if config_entry.data.get("vehicle_name") == self.vehicle_id:
                    entry = config_entry
                    break

            if entry and entry.data:
                power = entry.data.get(CONF_CHARGING_POWER, DEFAULT_CHARGING_POWER)
                # Ensure we return a valid number
                if isinstance(power, (int, float)) and power > 0:
                    return float(power)
        except Exception:
            pass
        return DEFAULT_CHARGING_POWER

    def get_charging_power(self) -> float:
        """Obtiene la potencia de carga configurada para el vehículo.

        Returns:
            float: Potencia de carga en kW (kilowatts). Retorna el valor configurado
                en la configuración del vehículo, o el valor predeterminado si no
                hay configuración disponible.

        Example:
            >>> power = trip_manager.get_charging_power()
            >>> print(f"{power} kW")
            "7.4 kW"
        """
        return self._get_charging_power()

    def _calcular_tasa_carga_soc(
        self, charging_power_kw: float, battery_capacity_kwh: float = 50.0
    ) -> float:
        """Calcula la tasa de carga en % SOC/hora.

        Formula: charging_power_kw / battery_capacity_kwh * 100 = % SOC/hour

        Args:
            charging_power_kw: Potencia de carga en kW
            battery_capacity_kwh: Capacidad de la bateria en kWh (default 50.0)

        Returns:
            Tasa de carga en % SOC por hora
        """
        if battery_capacity_kwh <= 0:
            return 0.0
        return (charging_power_kw / battery_capacity_kwh) * 100

    def _calcular_soc_objetivo_base(
        self,
        trip: Dict[str, Any],
        battery_capacity_kwh: float,
        consumption_kwh_per_km: float = 0.15,
    ) -> float:
        """Calculates the base SOC target percentage for a trip.

        Args:
            trip: Dictionary with trip data (kwh or km, consumo)
            battery_capacity_kwh: Battery capacity in kWh
            consumption_kwh_per_km: Energy consumption in kWh/km (default 0.15)

        Returns:
            Base SOC target percentage for the trip (energy + buffer)
        """
        # Calculate energy needed for trip
        if "kwh" in trip and trip["kwh"]:
            energia_kwh = trip["kwh"]
        else:
            distance_km = trip.get("km", 0.0)
            energia_kwh = calcular_energia_kwh(distance_km, consumption_kwh_per_km)

        # Convert to SOC percentage
        if battery_capacity_kwh > 0:
            energia_soc = (energia_kwh / battery_capacity_kwh) * 100
        else:
            energia_soc = 0.0

        # Add buffer
        soc_objetivo_base = energia_soc + DEFAULT_SOC_BUFFER_PERCENT
        return soc_objetivo_base

    async def async_get_next_trip(self) -> Optional[Dict[str, Any]]:
        """Obtiene el próximo viaje programado."""
        now = datetime.now()
        next_trip = None
        for trip in self._recurring_trips.values():
            if trip["activo"]:
                trip_time = self._get_trip_time(trip)
                if trip_time and trip_time > now:
                    if next_trip is None or trip_time < next_trip["time"]:
                        next_trip = {"time": trip_time, "trip": trip}
        for trip in self._punctual_trips.values():
            if trip["estado"] == "pendiente":
                trip_time = self._get_trip_time(trip)
                if trip_time and trip_time > now:
                    if next_trip is None or trip_time < next_trip["time"]:
                        next_trip = {"time": trip_time, "trip": trip}
        return next_trip["trip"] if next_trip else None

    async def async_get_next_trip_after(
        self, hora_regreso: datetime
    ) -> Optional[Dict[str, Any]]:
        """Obtiene el próximo viaje pendiente después de una hora de regreso.

        Filtra viajes puntuales con datetime > hora_regreso y estado=pendiente,
        y viajes recurrentes con hora > hora_regreso.time() para el día de
        hoy de la semana y activo=True.

        Args:
            hora_regreso: Fecha y hora de regreso del vehículo

        Returns:
            El próximo viaje más temprano después de hora_regreso, o None si
            no hay viajes pendientes.
        """
        next_trip = None
        hoy = hora_regreso.date()
        dia_semana_hoy = DAYS_OF_WEEK[hoy.weekday()]

        # Filter punctual trips: datetime > hora_regreso and estado=pendiente
        for trip in self._punctual_trips.values():
            if trip.get("estado") != "pendiente":
                continue
            trip_time = self._get_trip_time(trip)
            if trip_time and trip_time > hora_regreso:
                if next_trip is None or trip_time < next_trip["time"]:
                    next_trip = {"time": trip_time, "trip": trip}

        # Filter recurring trips: today's day_of_week, hora > hora_regreso.time(), activo=True
        for trip in self._recurring_trips.values():
            if not trip.get("activo", True):
                continue
            if trip.get("dia_semana", "").lower() != dia_semana_hoy:
                continue
            # Parse hora (format: "HH:MM")
            try:
                trip_hour = int(trip["hora"].split(":")[0])
                trip_minute = int(trip["hora"].split(":")[1])
                regreso_hour = hora_regreso.hour
                regreso_minute = hora_regreso.minute
                # Compare time only (not date) for recurring trips
                if trip_hour < regreso_hour or (
                    trip_hour == regreso_hour and trip_minute <= regreso_minute
                ):
                    continue
            except (ValueError, KeyError) as err:
                _LOGGER.warning(
                    "Error parsing recurring trip hora '%s': %s",
                    trip.get("hora"),
                    err,
                )
                continue
            # Build full datetime for today at the trip's hour
            trip_time = datetime.combine(hoy, datetime.strptime(trip["hora"], "%H:%M").time())
            if next_trip is None or trip_time < next_trip["time"]:
                next_trip = {"time": trip_time, "trip": trip}

        return next_trip["trip"] if next_trip else None

    def _is_trip_today(self, trip: Dict[str, Any], today: datetime.date) -> bool:
        """Verifica si un viaje ocurre hoy."""
        if trip["tipo"] == TRIP_TYPE_RECURRING:
            # Use weekday index to compare (0=lunes, 6=domingo)
            return DAYS_OF_WEEK[today.weekday()] == trip["dia_semana"].lower()
        elif trip["tipo"] == TRIP_TYPE_PUNCTUAL:
            return datetime.strptime(trip["datetime"], "%Y-%m-%dT%H:%M").date() == today
        return False

    def _get_trip_time(self, trip: Dict[str, Any]) -> Optional[datetime]:
        """Obtiene la fecha y hora del viaje."""
        if trip["tipo"] == TRIP_TYPE_RECURRING:
            now = datetime.now()
            today = now.date()
            day_of_week = now.weekday()
            target_day = self._get_day_index(trip["dia_semana"])
            days_ahead = (target_day - day_of_week) % 7
            if days_ahead == 0 and now.hour > int(trip["hora"].split(":")[0]):
                days_ahead = 7
            return datetime.combine(
                today + timedelta(days=days_ahead),
                datetime.strptime(trip["hora"], "%H:%M").time(),
            )
        elif trip["tipo"] == TRIP_TYPE_PUNCTUAL:
            return datetime.strptime(trip["datetime"], "%Y-%m-%dT%H:%M")
        return None

    def _get_day_index(self, day_name: str) -> int:
        """Obtiene el índice del día de la semana."""
        day_lower = day_name.lower().strip()
        # Try direct match first
        try:
            return DAYS_OF_WEEK.index(day_lower)
        except ValueError:
            pass

        # Try with proper capitalization
        for i, day in enumerate(DAYS_OF_WEEK):
            if day.lower() == day_lower:
                return i

        # If still not found, default to Monday (index 1)
        _LOGGER.warning(
            "Day '%s' not found in DAYS_OF_WEEK, defaulting to Monday", day_name
        )
        return 1

    async def async_get_vehicle_soc(self, vehicle_id: str) -> float:
        """Obtiene el SOC actual del vehículo desde el sensor configurado."""
        try:
            # Buscar config entry por vehicle_name (vehicle_id es vehicle_name, no entry_id)
            entry = None
            for config_entry in self.hass.config_entries.async_entries(DOMAIN):
                if config_entry.data.get("vehicle_name") == vehicle_id:
                    entry = config_entry
                    break

            if entry and entry.data:
                soc_sensor = entry.data.get("soc_sensor")
                if soc_sensor:
                    state = self.hass.states.get(soc_sensor)
                    if state and state.state not in ("unknown", "unavailable", "none"):
                        return float(state.state)
                _LOGGER.warning("Sensor SOC no disponible para %s", vehicle_id)
            else:
                _LOGGER.warning("Config entry no encontrada para %s", vehicle_id)
        except Exception as err:
            _LOGGER.error("Error obteniendo SOC: %s", err)
        return 0.0

    async def async_calcular_energia_necesaria(
        self, trip: Dict[str, Any], vehicle_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calcula la energía necesaria considerando el SOC actual.

        Args:
            trip: Diccionario con datos del viaje (kwh, km, datetime, etc.)
            vehicle_config: Diccionario con configuración del vehículo
                - battery_capacity_kwh: Capacidad de batería en kWh
                - charging_power_kw: Potencia de carga en kW
                - soc_current: SOC actual del vehículo en %
                - consumption_kwh_per_km: Consumo en kWh/km (opcional)

        Returns:
            Diccionario con:
                - energia_necesaria_kwh: Energía a cargar en kWh
                - horas_carga_necesarias: Horas necesarias para cargar
                - alerta_tiempo_insuficiente: True si no hay tiempo suficiente
                - horas_disponibles: Horas disponibles hasta el deadline

        Raises:
            ValueError: Si la distancia o el consumo son negativos.
        """
        battery_capacity = vehicle_config.get("battery_capacity_kwh", 50.0)
        charging_power_kw = vehicle_config.get("charging_power_kw", 3.6)
        soc_current = vehicle_config.get("soc_current", 100.0)
        consumption_kwh_per_km = vehicle_config.get("consumption_kwh_per_km", 0.15)

        # Calcular energía del viaje
        # Prioridad: usar kwh directo si existe, sino calcular desde km * consumo
        if "kwh" in trip:
            # Backward compatibility: usar valor directo si se proporciona
            energia_viaje = trip.get("kwh", 0.0)
        else:
            # Usar la fórmula: energia = distancia * consumo
            distance_km = trip.get("km", 0.0)
            energia_viaje = calcular_energia_kwh(distance_km, consumption_kwh_per_km)

        # Energía objetivo: energía del viaje + 40% de la batería (margen)
        energia_objetivo = energia_viaje + (battery_capacity * 0.4)

        # Energía actual en batería
        energia_actual = (soc_current / 100.0) * battery_capacity

        # Energía necesaria
        energia_necesaria = max(0.0, energia_objetivo - energia_actual)
        if charging_power_kw > 0:
            horas_carga = energia_necesaria / charging_power_kw
        else:
            horas_carga = 0

        # Calcular horas disponibles hasta el deadline
        horas_disponibles = 0.0
        alerta_tiempo_insuficiente = False

        # Get trip type from the trip dict
        trip_tipo = trip.get("tipo")
        trip_datetime = trip.get("datetime")

        if trip_tipo and trip_datetime:
            # Trip has tipo and datetime - use _get_trip_time
            trip_time = self._get_trip_time(trip)
            if trip_time:
                now = datetime.now()
                delta = trip_time - now
                horas_disponibles = delta.total_seconds() / 3600
                if horas_carga > horas_disponibles:
                    alerta_tiempo_insuficiente = True
        elif trip_datetime:
            # Handle case where trip has datetime but tipo not set
            try:
                if isinstance(trip_datetime, datetime):
                    trip_time = trip_datetime
                else:
                    trip_time = datetime.strptime(trip_datetime, "%Y-%m-%dT%H:%M")
                now = dt_util.now()
                delta = trip_time - now
                horas_disponibles = delta.total_seconds() / 3600
                if horas_carga > horas_disponibles:
                    alerta_tiempo_insuficiente = True
            except (KeyError, ValueError, TypeError):
                pass

        return {
            "energia_necesaria_kwh": round(energia_necesaria, 3),
            "horas_carga_necesarias": round(horas_carga, 2),
            "alerta_tiempo_insuficiente": alerta_tiempo_insuficiente,
            "horas_disponibles": round(horas_disponibles, 2),
        }

    async def calcular_ventana_carga(
        self,
        trip: Dict[str, Any],
        soc_actual: float,
        hora_regreso: Optional[datetime],
        charging_power_kw: float,
    ) -> Dict[str, Any]:
        """Calcula la ventana de carga disponible para un viaje.

        La ventana de carga es el tiempo desde que el coche regresa a casa
        hasta que inicia el siguiente viaje.

        Args:
            trip: Diccionario con datos del viaje (datetime, hora, km, kwh, etc.)
            soc_actual: SOC actual del vehículo en porcentaje (0-100)
            hora_regreso: Fecha y hora real de regreso del vehículo (None si no ha llegado)
            charging_power_kw: Potencia de carga en kW

        Returns:
            Diccionario con:
                - ventana_horas: Horas disponibles para cargar
                - kwh_necesarios: Energía necesaria en kWh
                - horas_carga_necesarias: Horas necesarias para cargar
                - inicio_ventana: Fecha y hora de inicio de la ventana
                - fin_ventana: Fecha y hora de fin de la ventana
                - es_suficiente: True si la ventana es suficiente para cargar
        """
        # Hardcoded trip duration: 6 hours (default)
        DURACION_VIAJE_HORAS = 6

        # Parse hora_regreso if it's a string
        parsed_hora_regreso = None
        if hora_regreso is not None:
            if isinstance(hora_regreso, str):
                try:
                    parsed_hora_regreso = datetime.fromisoformat(hora_regreso)
                except (ValueError, TypeError) as err:
                    _LOGGER.warning(
                        "Error parsing hora_regreso '%s': %s", hora_regreso, err
                    )
                    parsed_hora_regreso = None
            else:
                parsed_hora_regreso = hora_regreso

        # Check if next trip exists after hora_regreso (AC-5 edge case)
        if parsed_hora_regreso is not None:
            next_trip = await self.async_get_next_trip_after(parsed_hora_regreso)
            if next_trip is None:
                # No trips pending after hora_regreso - return zero values
                return {
                    "ventana_horas": 0,
                    "kwh_necesarios": 0,
                    "horas_carga_necesarias": 0,
                    "inicio_ventana": None,
                    "fin_ventana": None,
                    "es_suficiente": True,
                }

        # Get trip departure time (fin_ventana)
        trip_departure_time = self._get_trip_time(trip)
        if trip_departure_time is None:
            # Try parsing from trip dict directly
            trip_datetime = trip.get("datetime")
            if trip_datetime:
                try:
                    if isinstance(trip_datetime, datetime):
                        trip_departure_time = trip_datetime
                    else:
                        trip_departure_time = datetime.fromisoformat(trip_datetime)
                except (ValueError, TypeError) as err:
                    _LOGGER.warning(
                        "Error parsing trip datetime '%s': %s", trip_datetime, err
                    )
                    trip_departure_time = None

        # Calculate inicio_ventana
        if parsed_hora_regreso is not None:
            # Car has returned - use real return time
            inicio_ventana = parsed_hora_regreso
        elif trip_departure_time is not None:
            # Car not yet returned - estimate return time as 6h before departure
            inicio_ventana = trip_departure_time - timedelta(hours=DURACION_VIAJE_HORAS)
        else:
            # No departure time known - cannot calculate window
            return {
                "ventana_horas": 0.0,
                "kwh_necesarios": 0.0,
                "horas_carga_necesarias": 0.0,
                "inicio_ventana": None,
                "fin_ventana": None,
                "es_suficiente": True,
            }

        # Calculate fin_ventana (use trip departure time, or default to now + duration)
        if trip_departure_time is not None:
            fin_ventana = trip_departure_time
        else:
            fin_ventana = dt_util.now() + timedelta(hours=DURACION_VIAJE_HORAS)

        # Calculate ventana_horas
        delta = fin_ventana - inicio_ventana
        ventana_horas = max(0.0, delta.total_seconds() / 3600)

        # Calculate kwh_necesarios using existing logic
        vehicle_config = {
            "battery_capacity_kwh": 50.0,  # Default, will be overridden if available
            "charging_power_kw": charging_power_kw,
            "soc_current": soc_actual,
        }
        energia_info = await self.async_calcular_energia_necesaria(trip, vehicle_config)
        kwh_necesarios = energia_info["energia_necesaria_kwh"]

        # Calculate horas_carga_necesarias
        if charging_power_kw > 0:
            horas_carga_necesarias = kwh_necesarios / charging_power_kw
        else:
            horas_carga_necesarias = 0.0

        # Calculate es_suficiente
        es_suficiente = ventana_horas >= horas_carga_necesarias

        return {
            "ventana_horas": round(ventana_horas, 2),
            "kwh_necesarios": round(kwh_necesarios, 3),
            "horas_carga_necesarias": round(horas_carga_necesarias, 2),
            "inicio_ventana": inicio_ventana,
            "fin_ventana": fin_ventana,
            "es_suficiente": es_suficiente,
        }

    async def calcular_ventana_carga_multitrip(
        self,
        trips: List[Dict[str, Any]],
        soc_actual: float,
        hora_regreso: Optional[datetime],
        charging_power_kw: float,
    ) -> List[Dict[str, Any]]:
        """Calcula ventanas de carga para múltiples viajes en cadena.

        Cada viaje obtiene su propia ventana de carga. La ventana del primer
        viaje comienza en hora_regreso. Los viajes subsequentes comienzan
        cuando termina el viaje anterior (departure + 6h).

        Args:
            trips: Lista de diccionarios con datos de viajes
            soc_actual: SOC actual del vehículo en porcentaje (0-100)
            hora_regreso: Fecha y hora real de regreso (None si no ha llegado)
            charging_power_kw: Potencia de carga en kW

        Returns:
            Lista de diccionarios, uno por viaje, cada uno conteniendo:
                - ventana_horas: Horas disponibles para cargar
                - kwh_necesarios: Energía necesaria en kWh
                - horas_carga_necesarias: Horas necesarias para cargar
                - inicio_ventana: Fecha y hora de inicio de la ventana
                - fin_ventana: Fecha y hora de fin de la ventana
                - es_suficiente: True si la ventana es suficiente
                - trip: El trip original
        """
        # Hardcoded trip duration: 6 hours (default)
        DURACION_VIAJE_HORAS = 6

        if not trips:
            return []

        # Parse hora_regreso if it's a string
        parsed_hora_regreso = None
        if hora_regreso is not None:
            if isinstance(hora_regreso, str):
                try:
                    parsed_hora_regreso = datetime.fromisoformat(hora_regreso)
                except (ValueError, TypeError) as err:
                    _LOGGER.warning(
                        "Error parsing hora_regreso '%s': %s", hora_regreso, err
                    )
                    parsed_hora_regreso = None
            else:
                parsed_hora_regreso = hora_regreso

        # Sort trips by departure time (earliest first)
        sorted_trips = []
        for trip in trips:
            trip_time = self._get_trip_time(trip)
            if trip_time:
                sorted_trips.append((trip_time, trip))
        sorted_trips.sort(key=lambda x: x[0])
        trips_with_times = [(trip, trip_time) for trip_time, trip in sorted_trips]

        # Calculate window for each trip in chain
        results = []
        previous_arrival = None

        for idx, (trip, trip_departure_time) in enumerate(trips_with_times):
            # Determine window start for this trip
            if idx == 0:
                # First trip: window starts at hora_regreso (or estimated)
                if parsed_hora_regreso is not None:
                    # Car has returned - use real return time
                    window_start = parsed_hora_regreso
                else:
                    # Car not yet returned - estimate return as departure - 6h
                    window_start = trip_departure_time - timedelta(hours=DURACION_VIAJE_HORAS)
            else:
                # Subsequent trips: window starts at previous trip's arrival
                window_start = previous_arrival

            # Calculate arrival time for this trip (departure + 6h)
            trip_arrival = trip_departure_time + timedelta(hours=DURACION_VIAJE_HORAS)

            # Calculate ventana_horas
            delta = trip_arrival - window_start
            ventana_horas = max(0.0, delta.total_seconds() / 3600)

            # Calculate kwh_necesarios using existing logic
            vehicle_config = {
                "battery_capacity_kwh": 50.0,
                "charging_power_kw": charging_power_kw,
                "soc_current": soc_actual,
            }
            energia_info = await self.async_calcular_energia_necesaria(trip, vehicle_config)
            kwh_necesarios = energia_info["energia_necesaria_kwh"]

            # Calculate horas_carga_necesarias
            if charging_power_kw > 0:
                horas_carga_necesarias = kwh_necesarios / charging_power_kw
            else:
                horas_carga_necesarias = 0.0

            # Calculate es_suficiente
            es_suficiente = ventana_horas >= horas_carga_necesarias

            results.append({
                "ventana_horas": round(ventana_horas, 2),
                "kwh_necesarios": round(kwh_necesarios, 3),
                "horas_carga_necesarias": round(horas_carga_necesarias, 2),
                "inicio_ventana": window_start,
                "fin_ventana": trip_departure_time,
                "es_suficiente": es_suficiente,
                "trip": trip,
            })

            # Update previous_arrival for next iteration
            previous_arrival = trip_arrival

        return results

    async def calcular_soc_inicio_trips(
        self,
        trips: List[Dict[str, Any]],
        soc_inicial: float,
        hora_regreso: Optional[datetime],
        charging_power_kw: float,
        battery_capacity_kwh: float = 50.0,
    ) -> List[Dict[str, Any]]:
        """Calcula el SOC al inicio de cada viaje en cadena.

        Utiliza calcular_ventana_carga_multitrip para obtener las ventanas de carga
        y calcula el SOC de inicio para cada viaje.

        Args:
            trips: Lista de diccionarios con datos de viajes
            soc_inicial: SOC inicial del vehículo al comenzar la cadena (%)
            hora_regreso: Fecha y hora real de regreso (None si no ha llegado)
            charging_power_kw: Potencia de carga en kW
            battery_capacity_kwh: Capacidad de batería en kWh

        Returns:
            Lista de diccionarios, uno por viaje, conteniendo:
                - soc_inicio: SOC al inicio del viaje (%)
                - trip: El trip original
                - arrival_soc: SOC al llegar (después de cargar)
        """
        if not trips:
            return []

        # Obtener ventanas de carga para todos los viajes
        ventanas = await self.calcular_ventana_carga_multitrip(
            trips=trips,
            soc_actual=soc_inicial,
            hora_regreso=hora_regreso,
            charging_power_kw=charging_power_kw,
        )

        results = []
        soc_actual = soc_inicial

        for idx, ventana in enumerate(ventanas):
            trip = ventana["trip"]
            ventana_horas = ventana["ventana_horas"]
            kwh_necesarios = ventana["kwh_necesarios"]

            # SOC al inicio de este viaje
            soc_inicio = soc_actual

            # Calcular energía que se puede cargar en la ventana
            if charging_power_kw > 0 and ventana_horas > 0:
                kwh_disponibles = charging_power_kw * ventana_horas
                kwh_a_cargar = min(kwh_necesarios, kwh_disponibles)
            else:
                kwh_a_cargar = 0.0

            # Calcular SOC después de cargar (llegada al destino del viaje)
            if battery_capacity_kwh > 0:
                soc_llegada = soc_actual + (kwh_a_cargar / battery_capacity_kwh * 100)
                soc_llegada = min(100.0, soc_llegada)  # Cap at 100%
            else:
                soc_llegada = soc_actual

            results.append({
                "soc_inicio": round(soc_inicio, 2),
                "trip": trip,
                "arrival_soc": round(soc_llegada, 2),
            })

            # Actualizar SOC para el siguiente viaje
            soc_actual = soc_llegada

        return results

    async def calcular_hitos_soc(
        self,
        trips: List[Dict[str, Any]],
        soc_inicial: float,
        charging_power_kw: float,
        vehicle_config: Optional[Dict[str, Any]] = None,
        hora_regreso: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """Calcula los hitos SOC para múltiples viajes con propagación hacia atrás.

        Implementa el algoritmo de detección y propagación de déficit:
        1. Ordena viajes por hora de salida (primero el más temprano)
        2. Itera en ORDEN INVERSO (del último viaje al primero)
        3. Calcula capacidad de carga: tasa_carga_soc * ventana_horas
        4. Si soc_inicio + capacidad_carga < soc_objetivo:
           - deficit = soc_objetivo - (soc_inicio + capacidad_carga)
           - Añade el déficit al soc_objetivo del viaje ANTERIOR
        5. Almacena deficit_acumulado para cada viaje

        Args:
            trips: Lista de diccionarios con datos de viajes
            soc_inicial: SOC inicial del vehículo al comenzar la cadena (%)
            charging_power_kw: Potencia de carga en kW
            vehicle_config: Diccionario con configuración del vehículo
                - battery_capacity_kwh: Capacidad de batería en kWh (fallback 50.0)
            hora_regreso: Fecha y hora real de regreso (None si no ha llegado)

        Returns:
            Lista de SOCMilestoneResult con soc_objetivo ajustado y deficit_acumulado
        """
        # Extract battery_capacity_kwh from vehicle_config with fallback to 50.0 kWh
        battery_capacity_kwh = 50.0
        if vehicle_config and isinstance(vehicle_config, dict):
            battery_capacity_kwh = vehicle_config.get("battery_capacity_kwh", 50.0)

        if not trips:
            return []

        # Obtener información SOC inicio para todos los viajes
        soc_inicio_info = await self.calcular_soc_inicio_trips(
            trips=trips,
            soc_inicial=soc_inicial,
            hora_regreso=hora_regreso,
            charging_power_kw=charging_power_kw,
            battery_capacity_kwh=battery_capacity_kwh,
        )

        # Calcular tasa de carga SOC (%/hora)
        tasa_carga_soc = self._calcular_tasa_carga_soc(
            charging_power_kw, battery_capacity_kwh
        )

        # Obtener ventanas de carga
        ventanas = await self.calcular_ventana_carga_multitrip(
            trips=trips,
            soc_actual=soc_inicial,
            hora_regreso=hora_regreso,
            charging_power_kw=charging_power_kw,
        )

        # Crear lista de resultados ordenada por tiempo de salida
        # Primero, ordenamos los trips por departure time
        sorted_trips_with_times = []
        for idx, trip in enumerate(trips):
            trip_time = self._get_trip_time(trip)
            if trip_time:
                sorted_trips_with_times.append((trip_time, idx, trip))
        sorted_trips_with_times.sort(key=lambda x: x[0])  # Sort by time ascending

        # Mapear índices originales a posiciones ordenadas y viceversa
        idx_to_ordered = {}
        ordered_to_idx = {}
        for ordered_idx, (_, original_idx, _) in enumerate(sorted_trips_with_times):
            idx_to_ordered[original_idx] = ordered_idx
            ordered_to_idx[ordered_idx] = original_idx

        # Inicializar deficit_acumulado para cada viaje
        # El déficit se propaga al viaje anterior (en orden temporal, no en orden invertido)
        deficits = [0.0] * len(trips)

        _LOGGER.debug("Deficit propagation START: %d trips, soc_inicial=%.2f%%, tasa_carga_soc=%.2f%%/h", len(trips), soc_inicial, tasa_carga_soc)

        # ITERAR EN ORDEN INVERSO (del último viaje al primero)
        for ordered_idx in range(len(trips) - 1, -1, -1):
            # Obtener el índice original usando ordered_to_idx
            original_idx = ordered_to_idx.get(ordered_idx)
            if original_idx is None:
                continue

            # soc_inicio_info y ventanas están indexados por posición ordenada (sorted by time)
            soc_data = soc_inicio_info[ordered_idx]
            ventana = ventanas[ordered_idx]
            trip = trips[ordered_idx]

            soc_inicio = soc_data["soc_inicio"]
            ventana_horas = ventana["ventana_horas"]

            # Calcular soc_objetivo base para este viaje
            soc_objetivo = self._calcular_soc_objetivo_base(
                trip, battery_capacity_kwh
            )

            # Añadir déficit propagado desde viajes posteriores
            soc_objetivo_ajustado = soc_objetivo + deficits[original_idx]

            # Calcular capacidad de carga disponible
            capacidad_carga = tasa_carga_soc * ventana_horas

            _LOGGER.debug("Deficit calculation for trip %s (ordered_idx=%d): soc_inicio=%.2f%%, ventana_horas=%.2f, capacidad_carga=%.2f%%, soc_objetivo_base=%.2f%%, deficit_acumulado_previo=%.2f%%", trip.get("id", f"trip_{original_idx}"), ordered_idx, soc_inicio, ventana_horas, capacidad_carga, soc_objetivo, deficits[original_idx])

            # Verificar si hay déficit
            if soc_inicio + capacidad_carga < soc_objetivo_ajustado:
                deficit = soc_objetivo_ajustado - (soc_inicio + capacidad_carga)

                _LOGGER.debug("Deficit DETECTED for trip %s: deficit=%.2f%%, propagating to previous trip (ordered_idx=%d)", trip.get("id", f"trip_{original_idx}"), deficit, ordered_idx - 1)

                # Propagar el déficit al viaje ANTERIOR (en orden temporal)
                # Esto es, el viaje con departure time menor
                if ordered_idx > 0:
                    # Usar ordered_to_idx para encontrar el viaje anterior
                    prev_original_idx = ordered_to_idx.get(ordered_idx - 1)
                    if prev_original_idx is not None:
                        deficits[prev_original_idx] += deficit

                # Guardar deficit_acumulado para este viaje
                deficits[original_idx] += deficit

        # Construir resultados finales
        # soc_inicio_info, ventanas y deficits están indexados por posición ordenada (sorted by time)
        results: List[SOCMilestoneResult] = []

        _LOGGER.debug("Final SOC targets for %d trips: deficit propagation complete", len(trips))
        for ordered_idx in range(len(trips)):
            # Get original index to retrieve the trip from unsorted list
            original_idx = ordered_to_idx.get(ordered_idx)
            if original_idx is None:
                continue
            trip = trips[original_idx]
            soc_data = soc_inicio_info[ordered_idx]
            ventana = ventanas[ordered_idx]

            soc_objetivo = self._calcular_soc_objetivo_base(
                trip, battery_capacity_kwh
            )
            soc_objetivo_ajustado = soc_objetivo + deficits[original_idx]

            # Calculate kWh needed: (soc_objetivo - soc_inicio) * battery_capacity_kwh / 100
            soc_inicio = soc_data["soc_inicio"]
            kwh_necesarios = (soc_objetivo_ajustado - soc_inicio) * battery_capacity_kwh / 100

            results.append({
                "trip_id": trip.get("id", f"trip_{original_idx}"),
                "soc_objetivo": round(soc_objetivo_ajustado, 2),
                "kwh_necesarios": round(max(0.0, kwh_necesarios), 3),
                "deficit_acumulado": round(deficits[original_idx], 2),
                "ventana_carga": {
                    "ventana_horas": ventana["ventana_horas"],
                    "kwh_necesarios": ventana["kwh_necesarios"],
                    "horas_carga_necesarias": ventana["horas_carga_necesarias"],
                    "inicio_ventana": ventana["inicio_ventana"],
                    "fin_ventana": ventana["fin_ventana"],
                    "es_suficiente": ventana["es_suficiente"],
                },
            })

            _LOGGER.debug("Final SOC target for trip %s: soc_objetivo=%.2f%%, kwh_necesarios=%.3f, deficit_acumulado=%.2f%%", trip.get("id", f"trip_{original_idx}"), round(soc_objetivo_ajustado, 2), round(max(0.0, kwh_necesarios), 3), round(deficits[original_idx], 2))

        _LOGGER.debug("Deficit propagation COMPLETE for %d trips", len(trips))

        return results

    async def async_generate_power_profile(
        self,
        charging_power_kw: float = 3.6,
        planning_horizon_days: int = 7,
        vehicle_config: Optional[Dict[str, Any]] = None,
        hora_regreso: Optional[datetime] = None,
    ) -> List[float]:
        """Genera el perfil de potencia para EMHASS.

        Args:
            charging_power_kw: Potencia de carga en kW
            planning_horizon_days: Días de horizonte de planificación
            vehicle_config: Optional configuration dict with battery_capacity_kwh,
                          charging_power_kw, soc_current
            hora_regreso: Optional actual return time. If None, reads from
                         presence_monitor.async_get_hora_regreso()

        Returns:
            Lista de valores de potencia en watts (0 = no cargar, positivo = cargar)
        """
        # Cargar viajes
        await self._load_trips()

        # Obtener configuración del vehículo
        # Use provided vehicle_config if available, otherwise get from config entry
        if vehicle_config:
            battery_capacity = vehicle_config.get("battery_capacity_kwh", 50.0)
            soc_current = vehicle_config.get("soc_current")
        else:
            try:
                entry = self.hass.config_entries.async_get_entry(self.vehicle_id)
                if entry and entry.data:
                    battery_capacity = entry.data.get("battery_capacity_kwh", 50.0)
                else:
                    battery_capacity = 50.0
            except Exception:
                battery_capacity = 50.0
            soc_current = None

        # Obtener SOC actual - only fetch if not provided in vehicle_config
        if soc_current is None:
            soc_current = await self.async_get_vehicle_soc(self.vehicle_id)

        # Obtener hora_regreso si no fue proporcionada
        # Si no hay hora_regreso detectada aun, usar departure_time + 6h como estimado
        if hora_regreso is None and self.vehicle_controller._presence_monitor:
            hora_regreso = await self.vehicle_controller._presence_monitor.async_get_hora_regreso()

        # Inicializar perfil de potencia (0 = no cargar)
        profile_length = planning_horizon_days * 24
        power_profile = [0.0] * profile_length

        # Obtener todos los viajes pendientes
        all_trips = []
        for trip in self._recurring_trips.values():
            if trip.get("activo", True):
                all_trips.append(trip)
        for trip in self._punctual_trips.values():
            if trip.get("estado") == "pendiente":
                all_trips.append(trip)

        # Asignar índices a los viajes y aplicar prioridad
        # Urgentes = menor deadline = índice menor (prioridad alta)
        # Ordenar por tiempo de viaje (deadline más temprano = más urgente)
        now = datetime.now()
        for trip in all_trips:
            trip_time = self._get_trip_time(trip)
            if trip_time:
                trip["_deadline"] = trip_time
            else:
                # Sin deadline conocido = menor prioridad
                trip["_deadline"] = datetime.max

        # Ordenar trips: primero los más urgentes (deadline más cercano)
        all_trips.sort(key=lambda t: t.get("_deadline", datetime.max))

        # Asignar índice a cada viaje (0, 1, 2, ...)
        for idx, trip in enumerate(all_trips):
            trip["_trip_index"] = idx

        # Procesar cada viaje
        now = datetime.now()
        for trip in all_trips:
            # Calcular energía necesaria
            vehicle_config = {
                "battery_capacity_kwh": battery_capacity,
                "charging_power_kw": charging_power_kw,
                "soc_current": soc_current,
            }
            energia_info = await self.async_calcular_energia_necesaria(
                trip, vehicle_config
            )
            energia_kwh = energia_info["energia_necesaria_kwh"]

            if energia_kwh <= 0:
                continue

            # Usar calcular_ventana_carga para determinar la ventana de carga
            ventana_info = await self.calcular_ventana_carga(
                trip, soc_current, hora_regreso, charging_power_kw
            )

            # Si no hay ventana suficiente, skip
            if not ventana_info.get("es_suficiente", False):
                continue

            # Obtener inicio y fin de ventana
            inicio_ventana = ventana_info.get("inicio_ventana")
            fin_ventana = ventana_info.get("fin_ventana")

            if not inicio_ventana or not fin_ventana:
                continue

            # Convertir a watts
            charging_power_watts = charging_power_kw * 1000

            # Determinar posición en el perfil basada en la ventana
            delta_inicio = inicio_ventana - now
            horas_desde_ahora = int(delta_inicio.total_seconds() / 3600)

            if horas_desde_ahora < 0:
                # La ventana ya empezó, cargar inmediatamente
                hora_inicio_carga = 0
            else:
                hora_inicio_carga = horas_desde_ahora

            # Las horas necesarias para cargar
            horas_necesarias = ventana_info.get("horas_carga_necesarias", 0)
            if horas_necesarias == 0:
                horas_necesarias = 1

            # Fin de la ventana relativo a ahora
            delta_fin = fin_ventana - now
            horas_hasta_fin = int(delta_fin.total_seconds() / 3600)

            if horas_hasta_fin < 0:
                continue  # La ventana ya terminó

            # Distribuir la carga en las horas disponibles
            for h in range(hora_inicio_carga, min(hora_inicio_carga + horas_necesarias, horas_hasta_fin, profile_length)):
                if h >= 0 and h < profile_length:
                    power_profile[h] = charging_power_watts

        return power_profile

    async def async_generate_deferrables_schedule(
        self,
        charging_power_kw: float = 3.6,
        planning_horizon_days: int = 7,
    ) -> List[Dict[str, Any]]:
        """Genera el calendario de cargas diferibles para EMHASS.

        Maneja múltiples viajes con:
        - Index assignment: 0, 1, 2, ... por viaje (ordenados por prioridad)
        - Conflict detection: Múltiples viajes en la misma hora
        - Priority logic: Viajes más urgentes primero (deadline más cercano)

        Args:
            charging_power_kw: Potencia de carga en kW
            planning_horizon_days: Días de horizonte de planificación

        Returns:
            Lista de diccionarios con fecha y potencia por hora
            Formato: [{"date": "2026-03-17T14:00:00+01:00", "p_deferrable0": "0.0", "p_deferrable1": "0.0"}, ...]
        """
        # Cargar viajes
        await self._load_trips()

        # Obtener configuración
        try:
            entry = self.hass.config_entries.async_get_entry(self.vehicle_id)
            if entry and entry.data:
                entry.data.get("battery_capacity_kwh", 50.0)
        except Exception:
            pass

        # Obtener SOC actual
        await self.async_get_vehicle_soc(self.vehicle_id)

        # Obtener todos los viajes pendientes
        all_trips = []
        for trip in self._recurring_trips.values():
            if trip.get("activo", True):
                all_trips.append(trip)
        for trip in self._punctual_trips.values():
            if trip.get("estado") == "pendiente":
                all_trips.append(trip)

        # Ordenar trips por deadline (urgentes primero)
        # Conflict detection: múltiples viajes a la misma hora
        # Priority logic: deadline más cercano = más urgente = índice menor
        now = datetime.now()
        for trip in all_trips:
            trip_time = self._get_trip_time(trip)
            if trip_time:
                trip["_deadline"] = trip_time
                # Calcular horas hasta deadline para排序
                delta = trip_time - now
                trip["_hours_until_deadline"] = max(0, delta.total_seconds() / 3600)
            else:
                trip["_deadline"] = datetime.max
                trip["_hours_until_deadline"] = float("inf")

        # Ordenar: primero los más urgentes (menor hours_until_deadline)
        all_trips.sort(key=lambda t: t.get("_hours_until_deadline", float("inf")))

        # Asignar índice a cada viaje (0, 1, 2, ...)
        # Índice 0 = mayor prioridad = deadline más cercano
        trip_indices = {}
        for idx, trip in enumerate(all_trips):
            trip_id = trip.get("id", f"trip_{idx}")
            trip_indices[trip_id] = idx

        # Generar power profiles para cada índice de viaje
        # Cada índice de viaje tiene su propio perfil de potencia
        num_trips = len(all_trips)
        profile_length = planning_horizon_days * 24

        # Inicializar perfiles para cada viaje
        power_profiles: List[List[float]] = [
            [0.0] * profile_length for _ in range(num_trips)
        ]

        # Obtener configuración del vehículo
        battery_capacity = 50.0
        soc_current = 50.0
        try:
            entry = self.hass.config_entries.async_get_entry(self.vehicle_id)
            if entry and entry.data:
                battery_capacity = entry.data.get("battery_capacity_kwh", 50.0)
        except Exception:
            pass
        soc_current = await self.async_get_vehicle_soc(self.vehicle_id)

        # Generar perfil de potencia para cada viaje
        for idx, trip in enumerate(all_trips):
            vehicle_config = {
                "battery_capacity_kwh": battery_capacity,
                "charging_power_kw": charging_power_kw,
                "soc_current": soc_current,
            }
            energia_info = await self.async_calcular_energia_necesaria(
                trip, vehicle_config
            )
            energia_kwh = energia_info["energia_necesaria_kwh"]
            horas_carga = energia_info["horas_carga_necesarias"]

            if energia_kwh <= 0:
                continue

            # Convertir a watts
            charging_power_watts = charging_power_kw * 1000

            # Determinar las horas de carga necesarias
            horas_necesarias = int(horas_carga) + (1 if horas_carga % 1 > 0 else 0)
            if horas_necesarias == 0:
                horas_necesarias = 1

            # Obtener deadline del viaje
            trip_time = self._get_trip_time(trip)
            if not trip_time:
                continue

            # Calcular posición en el perfil (desde ahora)
            delta = trip_time - now
            horas_hasta_viaje = int(delta.total_seconds() / 3600)

            if horas_hasta_viaje < 0:
                continue  # El viaje ya pasó

            # Determinar horas de carga: las últimas horas antes del deadline
            hora_inicio_carga = max(0, horas_hasta_viaje - horas_necesarias)

            # Distribuir la carga en las horas disponibles
            for h in range(hora_inicio_carga, min(horas_hasta_viaje, profile_length)):
                if h >= 0 and h < profile_length:
                    power_profiles[idx][h] = charging_power_watts

        # Generar calendario con múltiples índices de carga diferible
        schedule = []
        now_dt = dt_util.now()  # Timezone-aware datetime from Home Assistant

        for day in range(planning_horizon_days):
            for hour in range(24):
                # Calcular timestamp con timezone
                timestamp = now_dt + timedelta(days=day, hours=hour)
                profile_idx = day * 24 + hour

                # Crear entrada con todos los índices de carga diferible
                entry = {"date": timestamp.isoformat()}

                # Añadir potencia para cada índice de viaje
                for trip_idx in range(num_trips):
                    power = (
                        power_profiles[trip_idx][profile_idx]
                        if profile_idx < len(power_profiles[trip_idx])
                        else 0.0
                    )
                    entry[f"p_deferrable{trip_idx}"] = f"{power:.1f}"

                # Si no hay viajes, asegurar que hay al menos p_deferrable0
                if num_trips == 0:
                    entry["p_deferrable0"] = "0.0"

                schedule.append(entry)

        return schedule

    async def async_create_trip_sensor(
        self, trip_id: str, trip_data: Dict[str, Any]
    ) -> None:
        """Create a Home Assistant sensor entity for a trip.

        This method creates a sensor entity for each trip when it's added.
        The sensor is registered in the entity registry so it persists
        across Home Assistant restarts.

        Args:
            trip_id: Unique identifier for the trip
            trip_data: Complete trip data including id, tipo, etc.
        """
        try:
            # Get the entity registry
            from homeassistant.helpers import entity_registry as er

            registry = er.async_get(self.hass)

            # Build entity_id from trip_id
            # Format: sensor.trip_{trip_id}
            entity_id = f"sensor.trip_{trip_id}"

            # Check if entity already exists
            existing_entry = registry.async_get(entity_id)

            if existing_entry is not None:
                # Entity already exists, just update its state
                _LOGGER.debug(
                    "Trip sensor %s already exists, skipping creation",
                    entity_id,
                )
                return

            # Create the entity in the registry
            # We use a unique_id that combines vehicle_id and trip_id
            unique_id = f"trip_{trip_id}"

            # Register the entity
            registry.async_get_or_create(
                domain="sensor",
                platform=DOMAIN,
                unique_id=unique_id,
                suggested_object_id=f"trip_{trip_id}",
                capabilities={
                    "state_class": None,
                },
                device_class=SensorDeviceClass.ENUM,
            )

            _LOGGER.info(
                "Created trip sensor %s for trip %s (vehicle: %s)",
                entity_id,
                trip_id,
                self.vehicle_id,
            )

        except Exception as err:
            _LOGGER.error(
                "Error creating trip sensor for trip %s: %s",
                trip_id,
                err,
                exc_info=True,
            )

    async def async_remove_trip_sensor(self, trip_id: str) -> None:
        """Remove a Home Assistant sensor entity for a trip.

        This method removes the sensor entity from the entity registry
        when a trip is deleted.

        Args:
            trip_id: Unique identifier for the trip
        """
        try:
            # Get the entity registry
            from homeassistant.helpers import entity_registry as er

            registry = er.async_get(self.hass)

            # Build entity_id from trip_id
            entity_id = f"sensor.trip_{trip_id}"

            # Check if entity exists
            existing_entry = registry.async_get(entity_id)

            if existing_entry is None:
                # Entity doesn't exist, nothing to remove
                _LOGGER.debug(
                    "Trip sensor %s does not exist, nothing to remove",
                    entity_id,
                )
                return

            # Remove the entity from the registry
            registry.async_remove(entity_id)

            _LOGGER.info(
                "Removed trip sensor %s for trip %s (vehicle: %s)",
                entity_id,
                trip_id,
                self.vehicle_id,
            )

        except Exception as err:
            _LOGGER.error(
                "Error removing trip sensor for trip %s: %s",
                trip_id,
                err,
                exc_info=True,
            )
