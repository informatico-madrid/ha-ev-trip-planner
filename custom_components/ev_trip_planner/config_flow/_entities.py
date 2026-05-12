"""Entity registry scanning helpers for config flow.

Extracted from main.py to reduce EVTripPlannerFlowHandler LOC count.
Provides unified entity registry queries used by presence and notifications steps.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

_LOGGER = logging.getLogger(__name__)


def scan_entities(
    hass: HomeAssistant,
    domain_prefixes: List[str],
) -> List[str]:
    """Scan entity registry for entities matching given domain prefixes.

    Args:
        hass: HomeAssistant instance.
        domain_prefixes: List of entity ID prefixes to match (e.g. ["binary_sensor.", "input_boolean."]).

    Returns:
        Sorted list of matching entity IDs.
    """
    try:
        entity_registry = er.async_get(hass)
        entities = [
            entity_id
            for entity_id in entity_registry.entities.keys()
            if any(entity_id.startswith(prefix) for prefix in domain_prefixes)
        ]
        _LOGGER.debug(
            "Found %d entities matching prefixes %s",
            len(entities),
            domain_prefixes,
        )
        return sorted(entities)
    except Exception as e:
        _LOGGER.error("Error scanning entity registry: %s", e)
        return []


def scan_notify_entities(
    hass: HomeAssistant,
) -> List[str]:
    """Scan entity registry for notify-domain entities.

    Falls back to services API if entity registry is unavailable.
    Used by the notifications config flow step.

    Args:
        hass: HomeAssistant instance.

    Returns:
        Sorted list of notify entity IDs.
    """
    try:
        entity_registry_obj = er.async_get(hass)
        notify_entities = [
            entity.entity_id
            for entity in entity_registry_obj.entities.values()
            if entity.domain == "notify"
        ]
        available = sorted(notify_entities)
        _LOGGER.info("Notification step: %d notify entities available", len(available))
        return available
    except Exception as err:
        _LOGGER.warning(
            "Failed to get notify entities from registry: %s, using services API",
            err,
        )
        notify_services = hass.services.async_services().get("notify", {})
        available = sorted(notify_services.keys())
        _LOGGER.info(
            "Using services API: %d notify services available",
            len(available),
        )
        return available


def auto_select_sensor(
    hass: HomeAssistant,
    domain_prefixes: List[str],
    user_input: Dict[str, Any],
    sensor_key: str,
) -> Dict[str, Any]:
    """Auto-select first available sensor if not provided by user.

    Helper for config flow steps that need a mandatory sensor but want
    to auto-select from the registry when the user doesn't provide one.

    Args:
        hass: HomeAssistant instance.
        domain_prefixes: Entity ID prefixes to search.
        user_input: The current user input dict (will be modified and returned).
        sensor_key: The config key to set (e.g. CONF_CHARGING_SENSOR).

    Returns:
        Modified user_input dict with sensor_key set if an entity was found.
    """
    if user_input.get(sensor_key):
        return user_input

    _LOGGER.warning(
        "No %s selected, auto-selecting first available from %s",
        sensor_key,
        domain_prefixes,
    )
    entities = scan_entities(hass, domain_prefixes)
    if entities:
        selected = entities[0]
        user_input = {**user_input, sensor_key: selected}
        _LOGGER.info("Auto-selected %s=%s", sensor_key, selected)
    else:
        _LOGGER.error("No entities available for auto-selection from %s", domain_prefixes)

    return user_input
