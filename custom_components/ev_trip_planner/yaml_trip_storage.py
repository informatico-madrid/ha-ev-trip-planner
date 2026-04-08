"""YAML-based trip storage implementation."""

from typing import Any, Dict

from homeassistant.core import HomeAssistant

from .const import DOMAIN


class YamlTripStorage:
    """YAML-based storage for trips using Home Assistant's Store API.

    This storage backend uses HA's Store API which persists data as JSON
    in the .storage directory. The YAML name is retained for historical
    compatibility with the original design intent.
    """

    def __init__(self, hass: HomeAssistant, vehicle_id: str) -> None:
        """Initialize storage for a vehicle.

        Args:
            hass: HomeAssistant instance
            vehicle_id: Vehicle identifier
        """
        self._hass = hass
        self._vehicle_id = vehicle_id

    async def async_load(self) -> Dict[str, Any]:
        """Load trips from storage.

        Returns:
            Dictionary with trips data or empty dict if no data.
        """
        from homeassistant.helpers import storage as ha_storage

        storage_key = f"{DOMAIN}_{self._vehicle_id}"
        store = ha_storage.Store(self._hass, version=1, key=storage_key)
        stored_data = await store.async_load()

        if stored_data:
            if isinstance(stored_data, dict) and "data" in stored_data:
                return stored_data.get("data", {})
            return stored_data
        return {}

    async def async_save(self, data: Dict[str, Any]) -> None:
        """Save trips to storage.

        Args:
            data: Dictionary with trips data to save.
        """
        from datetime import datetime

        from homeassistant.helpers import storage as ha_storage

        storage_key = f"{DOMAIN}_{self._vehicle_id}"
        store = ha_storage.Store(self._hass, version=1, key=storage_key)

        save_data = {
            "trips": data.get("trips", {}),
            "recurring_trips": data.get("recurring_trips", {}),
            "punctual_trips": data.get("punctual_trips", {}),
            "last_update": datetime.now().isoformat(),
        }

        await store.async_save(save_data)