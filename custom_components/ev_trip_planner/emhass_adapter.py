"""EMHASS Adapter for EV Trip Planner."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from homeassistant.core import HomeAssistant, HomeAssistantError
from homeassistant.helpers.storage import Store

from .const import (
    CONF_CHARGING_POWER,
    CONF_INDEX_COOLDOWN_HOURS,
    CONF_MAX_DEFERRABLE_LOADS,
    CONF_NOTIFICATION_SERVICE,
    CONF_VEHICLE_NAME,
    DEFAULT_INDEX_COOLDOWN_HOURS,
    EMHASS_STATE_ACTIVE,
    EMHASS_STATE_ERROR,
    EMHASS_STATE_READY,
)

_LOGGER = logging.getLogger(__name__)


class EMHASSAdapter:
    """Adapter to publish trips as EMHASS deferrable loads."""

    def __init__(self, hass: HomeAssistant, vehicle_config: Dict[str, Any]):
        """Initialize adapter."""
        self.hass = hass
        self.vehicle_id = vehicle_config[CONF_VEHICLE_NAME]
        self.max_deferrable_loads = vehicle_config.get(CONF_MAX_DEFERRABLE_LOADS, 50)
        self.charging_power = vehicle_config.get(CONF_CHARGING_POWER, 7.4)

        # Notification configuration
        self.notification_service = vehicle_config.get(CONF_NOTIFICATION_SERVICE)

        # Storage for trip_id → emhass_index mapping
        store_key = f"ev_trip_planner_{self.vehicle_id}_emhass_indices"
        self._store = Store(hass, version=1, key=store_key)
        self._index_map: Dict[str, int] = {}  # trip_id → emhass_index
        self._available_indices: List[int] = list(range(self.max_deferrable_loads))

        # Soft delete: released indices with timestamp for cooldown
        self._released_indices: Dict[int, datetime] = {}
        self._index_cooldown_hours: int = vehicle_config.get(
            CONF_INDEX_COOLDOWN_HOURS, DEFAULT_INDEX_COOLDOWN_HOURS
        )

        # Error tracking
        self._last_error: Optional[str] = None
        self._last_error_time: Optional[datetime] = None

        _LOGGER.debug(
            "Created EMHASSAdapter for %s, %d indices, notification_service=%s",
            self.vehicle_id,
            len(self._available_indices),
            self.notification_service,
        )

    async def async_load(self):
        """Load index mapping from storage."""
        try:
            data = await self._store.async_load()
            if data:
                self._index_map = data.get("index_map", {})
                # Rebuild available indices
                used_indices = set(self._index_map.values())
                self._available_indices = [
                    i for i in range(self.max_deferrable_loads) if i not in used_indices
                ]
                _LOGGER.info(
                    "Loaded %d trip-index mappings for %s, %d indices still available",
                    len(self._index_map),
                    self.vehicle_id,
                    len(self._available_indices),
                )
        except Exception as err:
            _LOGGER.error("Failed to load index mapping from storage: %s", err)
            await self.async_notify_error(
                error_type="storage_error",
                message=f"Failed to load data: {err}",
            )

    async def async_save(self):
        """Save index mapping to storage."""
        await self._store.async_save(
            {
                "index_map": self._index_map,
                "vehicle_id": self.vehicle_id,
            }
        )

    async def async_assign_index_to_trip(self, trip_id: str) -> Optional[int]:
        """
        Assign an available EMHASS index to a trip.

        Returns:
            Assigned index or None if no indices available
        """
        if trip_id in self._index_map:
            # Trip already has an index, reuse it
            return self._index_map[trip_id]

        available = self.get_available_indices()
        if not available:
            _LOGGER.error(
                "No available EMHASS indices for vehicle %s. "
                "Max deferrable loads: %d, currently used: %d",
                self.vehicle_id,
                self.max_deferrable_loads,
                len(self._index_map),
            )
            return None

        # Assign the smallest available index
        assigned_index = min(available)
        self._available_indices.remove(assigned_index)
        self._index_map[trip_id] = assigned_index

        await self.async_save()

        _LOGGER.info(
            "Assigned EMHASS index %d to trip %s for vehicle %s. "
            "%d indices remaining available",
            assigned_index,
            trip_id,
            self.vehicle_id,
            len(self._available_indices),
        )

        return assigned_index

    async def async_release_trip_index(self, trip_id: str) -> bool:
        """
        Release an EMHASS index when trip is deleted/completed.
        Uses soft delete - index goes to cooldown for 24h before reuse.

        Returns:
            True if index was released, False if trip not found
        """
        if trip_id not in self._index_map:
            _LOGGER.warning("Attempted to release index for unknown trip %s", trip_id)
            return False

        released_index = self._index_map.pop(trip_id)
        # Soft delete: store in released_indices with timestamp instead of returning to available
        self._released_indices[released_index] = datetime.now()

        await self.async_save()

        _LOGGER.info(
            "Released EMHASS index %d from trip %s for vehicle %s. "
            "Index in soft-delete cooldown for %d hours",
            released_index,
            trip_id,
            self.vehicle_id,
            self._index_cooldown_hours,
        )

        return True

    def _get_config_sensor_id(self, emhass_index: int) -> str:
        """Get entity ID for EMHASS config sensor."""
        return f"sensor.emhass_deferrable_load_config_{emhass_index}"

    async def async_publish_deferrable_load(self, trip: Dict[str, Any]) -> bool:
        """
        Publish a trip as deferrable load configuration.

        Args:
            trip: Trip dictionary with kwh, deadline, etc.

        Returns:
            True if successful, False otherwise
        """
        try:
            trip_id = trip.get("id")
            if not trip_id:
                _LOGGER.error("Trip missing ID")
                return False

            # Assign index to trip
            emhass_index = await self.async_assign_index_to_trip(trip_id)
            if emhass_index is None:
                return False

            # Calculate parameters
            kwh = float(trip.get("kwh", 0))
            deadline = trip.get("datetime")

            if not deadline:
                _LOGGER.error("Trip missing deadline: %s", trip_id)
                await self.async_release_trip_index(trip_id)
                return False

            # Calculate hours available
            now = datetime.now()
            if isinstance(deadline, str):
                deadline_dt = datetime.fromisoformat(deadline)
            else:
                deadline_dt = deadline

            hours_available = (deadline_dt - now).total_seconds() / 3600

            if hours_available <= 0:
                _LOGGER.warning("Trip deadline in past: %s", trip_id)
                await self.async_release_trip_index(trip_id)
                return False

            # Calculate EMHASS parameters
            total_hours = kwh / self.charging_power
            power_watts = self.charging_power * 1000  # Convert to Watts
            end_timestep = min(int(hours_available), 168)  # Max 7 days

            # Create attributes
            attributes = {
                "def_total_hours": round(total_hours, 2),
                "P_deferrable_nom": round(power_watts, 0),
                "def_start_timestep": 0,
                "def_end_timestep": end_timestep,
                "trip_id": trip_id,
                "vehicle_id": self.vehicle_id,
                "trip_description": trip.get("descripcion", ""),
                "status": "pending",
                "kwh_needed": kwh,
                "deadline": deadline_dt.isoformat(),
                "emhass_index": emhass_index,
            }

            # Set state
            config_sensor_id = self._get_config_sensor_id(emhass_index)
            await self.hass.states.async_set(config_sensor_id, EMHASS_STATE_ACTIVE, attributes)

            _LOGGER.info(
                "Published deferrable load for trip %s (index %d): %s hours, %s W",
                trip_id,
                emhass_index,
                round(total_hours, 2),
                round(power_watts, 0),
            )

            return True

        except HomeAssistantError as err:
            _LOGGER.error("Error publishing deferrable load: %s", err)
            # Release index on error
            if "trip_id" in locals() and trip_id in self._index_map:
                await self.async_release_trip_index(trip_id)
            return False

    async def async_remove_deferrable_load(self, trip_id: str) -> bool:
        """Remove a trip from deferrable load configuration."""
        try:
            if trip_id not in self._index_map:
                _LOGGER.warning("Attempted to remove unknown trip %s", trip_id)
                return False

            emhass_index = self._index_map[trip_id]
            config_sensor_id = self._get_config_sensor_id(emhass_index)

            # Clear the configuration
            await self.hass.states.async_set(config_sensor_id, "idle", {})

            # Release the index
            await self.async_release_trip_index(trip_id)

            _LOGGER.info(
                "Removed deferrable load for trip %s (index %d)", trip_id, emhass_index
            )

            return True

        except Exception as err:
            _LOGGER.error("Error removing deferrable load: %s", err)
            return False

    async def async_update_deferrable_load(self, trip: Dict[str, Any]) -> bool:
        """Update existing deferrable load with new parameters."""
        return await self.async_publish_deferrable_load(trip)

    async def async_publish_all_deferrable_loads(
        self, trips: List[Dict[str, Any]]
    ) -> bool:
        """
        Publish multiple trips, each with its own index.

        Returns:
            True if all trips published successfully, False otherwise
        """
        success_count = 0

        for trip in trips:
            if await self.async_publish_deferrable_load(trip):
                success_count += 1

        _LOGGER.info(
            "Published %d/%d deferrable loads for vehicle %s",
            success_count,
            len(trips),
            self.vehicle_id,
        )

        return success_count == len(trips)

    def get_assigned_index(self, trip_id: str) -> Optional[int]:
        """Get the EMHASS index assigned to a trip."""
        return self._index_map.get(trip_id)

    def get_all_assigned_indices(self) -> Dict[str, int]:
        """Get all trip-index mappings."""
        return self._index_map.copy()

    def get_available_indices(self) -> List[int]:
        """
        Get list of available indices, excluding those in soft-delete cooldown.

        Returns:
            List of available EMHASS indices
        """
        # Clean up expired cooldown indices first
        now = datetime.now()
        expired = [
            idx
            for idx, released_time in self._released_indices.items()
            if (now - released_time).total_seconds() >= self._index_cooldown_hours * 3600
        ]
        for idx in expired:
            del self._released_indices[idx]
            self._available_indices.append(idx)

        if expired:
            self._available_indices.sort()

        return self._available_indices

    def calculate_deferrable_parameters(
        self,
        trip: Dict[str, Any],
        charging_power_kw: float,
    ) -> Dict[str, Any]:
        """
        Calculate deferrable load parameters from trip data.

        Args:
            trip: Trip dictionary with kwh, deadline, etc.
            charging_power_kw: Charging power in kW

        Returns:
            Dictionary with calculated deferrable parameters:
            - total_energy_kwh: Energy needed in kWh
            - power_watts: Charging power in watts
            - total_hours: Hours needed to charge
            - end_timestep: End timestep for EMHASS
            - start_timestep: Start timestep for EMHASS
        """
        try:
            kwh = float(trip.get("kwh", 0))
            deadline = trip.get("datetime")

            if kwh <= 0:
                _LOGGER.warning("Trip %s has no energy requirement", trip.get("id"))
                return {}

            # Calculate hours needed to charge
            total_hours = kwh / charging_power_kw

            # Power in watts (positive value = charging)
            power_watts = charging_power_kw * 1000

            # Calculate available time until deadline
            if deadline:
                now = datetime.now()
                if isinstance(deadline, str):
                    deadline_dt = datetime.fromisoformat(deadline)
                else:
                    deadline_dt = deadline

                hours_available = (deadline_dt - now).total_seconds() / 3600
                end_timestep = max(1, min(int(hours_available), 168))  # Max 7 days
            else:
                # Default to 24 hours if no deadline
                end_timestep = 24

            params = {
                "total_energy_kwh": round(kwh, 3),
                "power_watts": round(power_watts, 0),
                "total_hours": round(total_hours, 2),
                "end_timestep": end_timestep,
                "start_timestep": 0,
                "is_semi_continuous": False,
                "minimum_power": 0.0,
                "operating_hours": 0,
                "startup_penalty": 0.0,
                "is_single_constant": True,
            }

            _LOGGER.debug(
                "Calculated deferrable parameters for trip %s: %s kWh, %s W, %s hours",
                trip.get("id"),
                params["total_energy_kwh"],
                params["power_watts"],
                params["total_hours"],
            )

            return params

        except Exception as err:
            _LOGGER.error("Error calculating deferrable parameters: %s", err)
            return {}

    async def publish_deferrable_loads(
        self,
        trips: List[Dict[str, Any]],
        charging_power_kw: Optional[float] = None,
    ) -> bool:
        """
        Publish multiple trips as deferrable loads to EMHASS.

        This method:
        1. Calculates deferrable parameters for each trip
        2. Updates the template sensor with power_profile_watts and deferrables_schedule
        3. Ensures power profile: 0W = no charging, positive values = charging power

        Args:
            trips: List of trip dictionaries
            charging_power_kw: Charging power in kW (defaults to self.charging_power)

        Returns:
            True if all trips published successfully
        """
        if charging_power_kw is None:
            charging_power_kw = self.charging_power

        _LOGGER.info(
            "Publishing %d deferrable loads for vehicle %s with %s kW charging power",
            len(trips),
            self.vehicle_id,
            charging_power_kw,
        )

        # Calculate power profile for all trips
        # 0W = no charging, positive values = charging power
        power_profile = self._calculate_power_profile_from_trips(
            trips, charging_power_kw
        )

        # Generate schedule
        deferrables_schedule = self._generate_schedule_from_trips(
            trips, charging_power_kw
        )

        # Update the template sensor
        sensor_id = f"sensor.emhass_perfil_diferible_{self.vehicle_id}"
        await self.hass.states.async_set(
            sensor_id,
            EMHASS_STATE_READY,
            {
                "power_profile_watts": power_profile,
                "deferrables_schedule": deferrables_schedule,
                "vehicle_id": self.vehicle_id,
                "trips_count": len(trips),
            },
        )

        _LOGGER.info(
            "Published deferrable loads for %s: %d trips, profile length: %d",
            self.vehicle_id,
            len(trips),
            len(power_profile),
        )

        # Also publish individual trip configs
        success = True
        for trip in trips:
            if not await self.async_publish_deferrable_load(trip):
                success = False

        return success

    async def async_verify_shell_command_integration(self) -> Dict[str, Any]:
        """
        Verify that the EMHASS shell command integration is working.

        This method does NOT execute shell commands - it only verifies that:
        1. Our deferrable load sensors exist and contain data
        2. EMHASS response sensors are available to receive our data

        Returns:
            Dictionary with verification results:
            - is_configured: Whether shell command is likely configured
            - deferrable_sensor_exists: Whether our sensor exists
            - deferrable_sensor_has_data: Whether sensor has valid data
            - emhass_response_sensors: List of available EMHASS response sensors
            - errors: List of any issues found
        """
        result = {
            "is_configured": False,
            "deferrable_sensor_exists": False,
            "deferrable_sensor_has_data": False,
            "emhass_response_sensors": [],
            "errors": [],
        }

        # Check our deferrable sensor exists
        sensor_id = f"sensor.emhass_perfil_diferible_{self.vehicle_id}"
        deferrable_sensor = self.hass.states.get(sensor_id)

        if deferrable_sensor is None:
            result["errors"].append(
                f"Deferrable sensor {sensor_id} not found. "
                "Please configure the shell command in configuration.yaml"
            )
            return result

        result["deferrable_sensor_exists"] = True

        # Check sensor has valid data
        attrs = deferrable_sensor.attributes
        if not attrs or "power_profile_watts" not in attrs:
            result["errors"].append(
                f"Deferrable sensor {sensor_id} missing power_profile_watts attribute"
            )
            return result

        profile = attrs.get("power_profile_watts", [])
        if not profile or len(profile) == 0:
            result["errors"].append(
                f"Deferrable sensor {sensor_id} has empty power profile"
            )
            return result

        result["deferrable_sensor_has_data"] = True

        # Check for EMHASS response sensors (these are created by user's shell command)
        # Common EMHASS response sensor patterns
        response_sensor_patterns = [
            "sensor.emhass_",
            "sensor.p_deferrable",
            "sensor.emhass_opt",
        ]

        # Get all states and filter for EMHASS sensors
        all_states = self.hass.states.async_all()
        emhass_sensors = [
            state.entity_id
            for state in all_states
            if any(pattern in state.entity_id for pattern in response_sensor_patterns)
        ]

        result["emhass_response_sensors"] = emhass_sensors

        # If we have published trips, check if EMHASS sensors acknowledge them
        if self._index_map:
            result["is_configured"] = len(emhass_sensors) > 0

            if not emhass_sensors:
                result["errors"].append(
                    "No EMHASS response sensors found. "
                    "Verify shell command in configuration.yaml. "
                    "Should use curl to POST to EMHASS API."
                )

        _LOGGER.info(
            "EMHASS integration verification for %s: %s",
            self.vehicle_id,
            "configured" if result["is_configured"] else "not configured",
        )

        return result

    async def async_check_emhass_response_sensors(
        self, trip_ids: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Check if EMHASS response sensors include our deferrable loads.

        This method monitors the EMHASS response sensors to verify they
        contain our deferrable load configurations.

        Args:
            trip_ids: Optional list of trip IDs to check. If None, checks all trips.

        Returns:
            Dictionary with check results:
            - all_trips_verified: Whether all trips are in EMHASS sensors
            - verified_trips: List of trip IDs found in EMHASS
            - missing_trips: List of trip IDs not found
            - sensor_values: Current values from EMHASS sensors
        """
        result = {
            "all_trips_verified": False,
            "verified_trips": [],
            "missing_trips": [],
            "sensor_values": {},
        }

        # Get trips to check
        if trip_ids is None:
            trip_ids = list(self._index_map.keys())

        if not trip_ids:
            result["all_trips_verified"] = True
            return result

        # Get all EMHASS-related sensors using hass.states.get directly
        # This is more reliable than async_all() in test environments
        emhass_states: Dict[str, Any] = {}

        # Check our config sensors directly
        for trip_id in trip_ids:
            index = self._index_map.get(trip_id)
            if index is None:
                result["missing_trips"].append(trip_id)
                continue

            # Check for config sensor (our published data)
            config_sensor = f"sensor.emhass_deferrable_load_config_{index}"
            config_state = self.hass.states.get(config_sensor)

            if config_state:
                emhass_states[config_sensor] = config_state

                if config_state.state == EMHASS_STATE_ACTIVE:
                    result["verified_trips"].append(trip_id)
                    continue

            # Also check if EMHASS has picked up the load (in response sensors)
            # EMHASS typically creates sensors like p_deferrable0, p_deferrable1, etc.
            # Get all states and check for trip_id in attributes
            all_states = self.hass.states.async_all()
            found = False
            for state in all_states:
                if state.entity_id == config_sensor:
                    continue  # Already checked
                attrs = state.attributes or {}
                if attrs.get("trip_id") == trip_id:
                    result["verified_trips"].append(trip_id)
                    found = True
                    break

            if not found:
                result["missing_trips"].append(trip_id)

        # Collect sensor values for our config sensors
        result["sensor_values"] = {
            entity_id: {
                "state": state.state,
                "attributes": dict(state.attributes) if state.attributes else {},
            }
            for entity_id, state in emhass_states.items()
        }

        result["all_trips_verified"] = len(result["missing_trips"]) == 0

        _LOGGER.debug(
            "EMHASS response check for %s: %d/%d trips verified",
            self.vehicle_id,
            len(result["verified_trips"]),
            len(trip_ids),
        )

        return result

    async def async_get_integration_status(self) -> Dict[str, Any]:
        """
        Get overall EMHASS integration status.

        Returns:
            Dictionary with integration status:
            - status: overall status (ok, warning, error)
            - message: human-readable status message
            - details: detailed information
        """
        details = {}

        # Verify integration
        verification = await self.async_verify_shell_command_integration()
        details["verification"] = verification

        # Check response sensors
        response_check = await self.async_check_emhass_response_sensors()
        details["response_check"] = response_check

        # Determine overall status
        if not verification["deferrable_sensor_exists"]:
            status = EMHASS_STATE_ERROR
            message = "Deferrable sensor not found. Configure shell command."
        elif not verification["deferrable_sensor_has_data"]:
            status = "warning"
            message = "Deferrable sensor has no data. Add trips to publish."
        elif not verification["is_configured"]:
            status = "warning"
            message = "Shell command may not be configured."
        elif not response_check["all_trips_verified"]:
            status = "warning"
            missing = len(response_check["missing_trips"])
            message = f"EMHASS not responding to {missing} trip(s)."
        else:
            status = EMHASS_STATE_READY
            message = "EMHASS integration working correctly."

        return {
            "status": status,
            "message": message,
            "vehicle_id": self.vehicle_id,
            "details": details,
        }

    async def async_notify_error(
        self,
        error_type: str,
        message: str,
        trip_id: Optional[str] = None,
    ) -> bool:
        """
        Send notification about EMHASS integration error.

        This method:
        - Logs the error at appropriate HA level (WARNING or ERROR)
        - Sends notification via configured notification service
        - Updates dashboard status sensor
        - Stores error for later reference

        Args:
            error_type: Type of error (emhass_unavailable, sensor_missing, etc.)
            message: Human-readable error message
            trip_id: Optional trip ID related to the error

        Returns:
            True if notification sent successfully, False otherwise
        """
        # Store error for reference
        self._last_error = message
        self._last_error_time = datetime.now()

        # Log at appropriate level based on error type
        if error_type in ["emhass_unavailable", "critical"]:
            _LOGGER.error(
                "EMHASS error for vehicle %s [%s]: %s%s",
                self.vehicle_id,
                error_type,
                message,
                f" (trip: {trip_id})" if trip_id else "",
            )
        else:
            _LOGGER.warning(
                "EMHASS warning for vehicle %s [%s]: %s%s",
                self.vehicle_id,
                error_type,
                message,
                f" (trip: {trip_id})" if trip_id else "",
            )

        # Update dashboard status sensor
        await self._async_update_error_status(error_type, message, trip_id)

        # Send notification if configured
        return await self._async_send_error_notification(error_type, message, trip_id)

    async def _async_update_error_status(
        self,
        error_type: str,
        message: str,
        trip_id: Optional[str] = None,
    ) -> None:
        """Update dashboard status sensor with error information."""
        try:
            sensor_id = f"sensor.emhass_perfil_diferible_{self.vehicle_id}"
            attributes = {
                "power_profile_watts": [0.0] * 168,
                "deferrables_schedule": [],
                "vehicle_id": self.vehicle_id,
                "trips_count": 0,
                "emhass_status": EMHASS_STATE_ERROR,
                "error_type": error_type,
                "error_message": message,
                "error_time": datetime.now().isoformat(),
            }

            if trip_id:
                attributes["error_trip_id"] = trip_id

            await self.hass.states.async_set(
                sensor_id,
                EMHASS_STATE_ERROR,
                attributes,
            )

            _LOGGER.debug(
                "Updated dashboard status for vehicle %s: error=%s",
                self.vehicle_id,
                error_type,
            )
        except HomeAssistantError as err:
            _LOGGER.error("Failed to update error status sensor: %s", err)

    async def _async_send_error_notification(
        self,
        error_type: str,
        message: str,
        trip_id: Optional[str] = None,
    ) -> bool:
        """
        Send error notification via configured notification service.

        Args:
            error_type: Type of error
            message: Error message to send
            trip_id: Optional trip ID

        Returns:
            True if notification sent successfully
        """
        if not self.notification_service:
            _LOGGER.debug(
                "No notification service for %s, skipping",
                self.vehicle_id,
            )
            return False

        # Build notification message
        title = f"⚠️ EV Trip Planner - EMHASS Error: {self.vehicle_id}"

        # Detailed message based on error type
        if error_type == "emhass_unavailable":
            body = (
                "EMHASS no está disponible.\n\n"
                f"Mensaje: {message}\n\n"
                "El viaje se ha guardado pero NO tiene carga diferible en EMHASS. "
                "Revisión manual requerida."
            )
        elif error_type == "sensor_missing":
            body = (
                "Sensor EMHASS no encontrado.\n\n"
                f"Mensaje: {message}\n\n"
                "Verifica shell command en configuration.yaml."
            )
        elif error_type == "shell_command_failure":
            body = (
                "Error en shell command de EMHASS.\n\n"
                f"Mensaje: {message}\n\n"
                "EMHASS maneja este error."
            )
        else:
            body = f"Error: {message}"

        if trip_id:
            body += f"\n\nViaje afectado: {trip_id}"

        body += "\n\nConsulta el panel de control para más detalles."

        return await self._async_call_notification_service(title, body)

    async def _async_call_notification_service(
        self,
        title: str,
        message: str,
    ) -> bool:
        """
        Call the configured notification service.

        Args:
            title: Notification title
            message: Notification body

        Returns:
            True if notification sent successfully
        """
        if not self.notification_service:
            return False

        try:
            domain, service = self.notification_service.split(".", 1)
            await self.hass.services.async_call(
                domain,
                service,
                {
                    "title": title,
                    "message": message,
                    "notification_id": f"ev_trip_planner_emhass_{self.vehicle_id}",
                },
            )
            _LOGGER.info(
                "Error notification sent for vehicle %s: %s",
                self.vehicle_id,
                title,
            )
            return True
        except Exception as err:  # pylint: disable=broad-except
            _LOGGER.error(
                "Failed to send error notification for vehicle %s: %s",
                self.vehicle_id,
                err,
            )
            return False

    async def async_handle_emhass_unavailable(
        self,
        reason: str,
        trip_id: Optional[str] = None,
    ) -> bool:
        """
        Handle EMHASS API unavailability.

        When EMHASS is unavailable:
        - Trip is saved but has no deferrable load in EMHASS
        - User is notified via dashboard and notifications
        - Operation continues (trip is still managed)

        Args:
            reason: Why EMHASS is unavailable
            trip_id: Optional trip ID that was being published

        Returns:
            True if error handled successfully
        """
        message = (
            f"EMHASS API no disponible: {reason}. "
            "El viaje se ha guardado sin carga diferible - revisión manual requerida."
        )

        _LOGGER.warning(
            "EMHASS unavailable for vehicle %s: %s%s",
            self.vehicle_id,
            reason,
            f" (trip: {trip_id})" if trip_id else "",
        )

        return await self.async_notify_error(
            error_type="emhass_unavailable",
            message=message,
            trip_id=trip_id,
        )

    async def async_handle_sensor_error(
        self,
        sensor_id: str,
        error_details: str,
        trip_id: Optional[str] = None,
    ) -> bool:
        """
        Handle sensor-related errors.

        Args:
            sensor_id: The sensor that has an error
            error_details: Details about the error
            trip_id: Optional trip ID

        Returns:
            True if error handled successfully
        """
        message = f"Sensor {sensor_id}: {error_details}"

        return await self.async_notify_error(
            error_type="sensor_missing",
            message=message,
            trip_id=trip_id,
        )

    async def async_handle_shell_command_failure(
        self,
        trip_id: Optional[str] = None,
    ) -> bool:
        """
        Handle shell command failure.

        Note: Shell command failures are handled by EMHASS itself.
        We only verify sensors and notify the user.

        Args:
            trip_id: Optional trip ID

        Returns:
            True if error handled successfully
        """
        message = (
            "El shell command de EMHASS ha fallado. "
            "EMHASS maneja este error. Verifica los sensores de respuesta de EMHASS "
            "para confirmar que las cargas diferibles están activas."
        )

        _LOGGER.warning(
            "Shell command failure for vehicle %s%s",
            self.vehicle_id,
            f" (trip: {trip_id})" if trip_id else "",
        )

        return await self.async_notify_error(
            error_type="shell_command_failure",
            message=message,
            trip_id=trip_id,
        )

    def get_last_error(self) -> Optional[Dict[str, Any]]:
        """
        Get the last error that occurred.

        Returns:
            Dict with error info or None if no errors
        """
        if not self._last_error:
            return None

        error_time = (
            self._last_error_time.isoformat() if self._last_error_time else None
        )
        return {
            "message": self._last_error,
            "time": error_time,
        }

    async def async_clear_error(self) -> None:
        """Clear the last error and restore normal status."""
        self._last_error = None
        self._last_error_time = None

        # Restore normal status
        try:
            sensor_id = f"sensor.emhass_perfil_diferible_{self.vehicle_id}"
            current_state = self.hass.states.get(sensor_id)

            if current_state:
                # Keep existing data but clear error
                attributes = dict(current_state.attributes)
                attributes.pop("error_type", None)
                attributes.pop("error_message", None)
                attributes.pop("error_time", None)
                attributes.pop("error_trip_id", None)
                attributes["emhass_status"] = EMHASS_STATE_READY

                await self.hass.states.async_set(
                    sensor_id,
                    current_state.state,
                    attributes,
                )

            _LOGGER.info("Cleared error status for vehicle %s", self.vehicle_id)
        except HomeAssistantError as err:
            _LOGGER.error("Failed to clear error status: %s", err)

    async def async_cleanup_vehicle_indices(self) -> None:
        """
        Clean up all EMHASS indices for this vehicle when it is deleted.

        This is a HARD cleanup - immediately releases all indices without cooldown
        since the vehicle is being deleted. Clears all deferrable load sensors.

        Called during vehicle deletion cascade to ensure no orphaned indices remain.
        """
        # Clear all trip-to-index mappings immediately
        assigned_trips = list(self._index_map.keys())

        # Clear all deferrable load config sensors for this vehicle
        for trip_id in assigned_trips:
            emhass_index = self._index_map.get(trip_id)
            if emhass_index is not None:
                config_sensor_id = self._get_config_sensor_id(emhass_index)
                try:
                    await self.hass.states.async_set(config_sensor_id, "idle", {})
                except HomeAssistantError as err:
                    _LOGGER.warning(
                        "Failed to clear sensor %s during vehicle cleanup: %s",
                        config_sensor_id,
                        err,
                    )

        # Hard reset: clear all mappings and released indices
        self._index_map.clear()
        self._released_indices.clear()
        self._available_indices = list(range(self.max_deferrable_loads))

        # Clear the main vehicle sensor
        try:
            sensor_id = f"sensor.emhass_perfil_diferible_{self.vehicle_id}"
            await self.hass.states.async_set(
                sensor_id,
                "idle",
                {
                    "power_profile_watts": [0.0] * 168,
                    "deferrables_schedule": [],
                    "vehicle_id": self.vehicle_id,
                    "trips_count": 0,
                },
            )
        except HomeAssistantError as err:
            _LOGGER.warning(
                "Failed to clear vehicle sensor %s during cleanup: %s",
                sensor_id,
                err,
            )

        # Persist the cleared state
        await self.async_save()

        _LOGGER.info(
            "Cleaned up all EMHASS indices for vehicle %s. Released %d trip indices.",
            self.vehicle_id,
            len(assigned_trips),
        )

    def _calculate_power_profile_from_trips(
        self,
        trips: List[Dict[str, Any]],
        charging_power_kw: float,
        planning_horizon_hours: int = 168,
    ) -> List[float]:
        """
        Calculate power profile from trips.

        Power profile format: 0W = no charging, positive values = charging power

        Args:
            trips: List of trip dictionaries
            charging_power_kw: Charging power in kW
            planning_horizon_hours: Number of hours in the profile

        Returns:
            List of power values in watts
        """
        # Initialize with 0 (no charging)
        power_profile = [0.0] * planning_horizon_hours

        now = datetime.now()
        charging_power_watts = charging_power_kw * 1000

        for trip in trips:
            # Calculate energy needed
            params = self.calculate_deferrable_parameters(trip, charging_power_kw)
            if not params:
                continue

            kwh = params.get("total_energy_kwh", 0)
            if kwh <= 0:
                continue

            # Calculate hours needed
            horas_necesarias = int(params.get("total_hours", 0)) + (
                1 if params.get("total_hours", 0) % 1 > 0 else 0
            )
            if horas_necesarias == 0:
                horas_necesarias = 1

            # Get deadline
            deadline = trip.get("datetime")
            if not deadline:
                continue

            if isinstance(deadline, str):
                deadline_dt = datetime.fromisoformat(deadline)
            else:
                deadline_dt = deadline

            # Calculate position in profile
            delta = deadline_dt - now
            horas_hasta_viaje = int(delta.total_seconds() / 3600)

            if horas_hasta_viaje < 0:
                continue

            # Set charging hours (last hours before deadline)
            hora_inicio_carga = max(0, horas_hasta_viaje - horas_necesarias)

            hora_fin = min(horas_hasta_viaje, planning_horizon_hours)
            for h in range(hora_inicio_carga, hora_fin):
                if h >= 0 and h < planning_horizon_hours:
                    # Set positive value = charging
                    power_profile[h] = charging_power_watts

        return power_profile

    def _generate_schedule_from_trips(
        self,
        trips: List[Dict[str, Any]],
        charging_power_kw: float,
    ) -> List[Dict[str, Any]]:
        """
        Generate deferrables schedule from trips.

        Format:
            [{"date": "2026-03-17T14:00:00+01:00", "p_deferrable0": "0.0"}, ...]

        Args:
            trips: List of trip dictionaries
            charging_power_kw: Charging power in kW

        Returns:
            List of schedule dictionaries
        """
        schedule = []
        now = datetime.now()

        # Generate schedule for next 7 days (168 hours)
        for hour_offset in range(168):
            schedule_time = now.replace(minute=0, second=0, microsecond=0)
            schedule_time = schedule_time.replace(hour=(now.hour + hour_offset) % 24)

            # Add days if needed
            days_to_add = (now.hour + hour_offset) // 24
            from datetime import timedelta

            schedule_time = schedule_time + timedelta(days=days_to_add)

            schedule_entry = {
                "date": schedule_time.isoformat(),
            }

            # Add power values for each trip (index)
            # 0 = no charging, positive = charging
            for idx, trip in enumerate(trips):
                power_key = f"p_deferrable{idx}"
                params = self.calculate_deferrable_parameters(trip, charging_power_kw)

                if not params:
                    schedule_entry[power_key] = "0.0"
                    continue

                # Check if this hour is a charging hour for this trip
                deadline = trip.get("datetime")
                if not deadline:
                    schedule_entry[power_key] = "0.0"
                    continue

                if isinstance(deadline, str):
                    deadline_dt = datetime.fromisoformat(deadline)
                else:
                    deadline_dt = deadline

                delta = deadline_dt - now
                horas_hasta_viaje = int(delta.total_seconds() / 3600)

                if horas_hasta_viaje < 0:
                    schedule_entry[power_key] = "0.0"
                    continue

                horas_necesarias = int(params.get("total_hours", 0)) + (
                    1 if params.get("total_hours", 0) % 1 > 0 else 0
                )
                hora_inicio_carga = max(0, horas_hasta_viaje - horas_necesarias)

                # Check if current hour is within charging window
                if hora_inicio_carga <= hour_offset < horas_hasta_viaje:
                    schedule_entry[power_key] = str(params.get("power_watts", 0))
                else:
                    schedule_entry[power_key] = "0.0"

            schedule.append(schedule_entry)

        return schedule
