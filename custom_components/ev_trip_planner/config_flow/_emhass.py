"""EMHASS config-flow helpers — extracted from main.py.

Extracted to reduce EVTripPlannerFlowHandler LOC count and nesting depth.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, Optional

from homeassistant.core import HomeAssistant

from ..const import (
    CONF_MAX_DEFERRABLE_LOADS,
    CONF_PLANNING_HORIZON,
    CONF_PLANNING_SENSOR,
)

_LOGGER = logging.getLogger(__name__)


def read_emhass_config(emhass_config_path: str) -> Optional[Dict[str, Any]]:
    """Read EMHASS configuration from JSON file.

    Accepts either a directory path (appends /config.json) or a direct file path.
    Returns None if path is None, doesn't exist, or can't be parsed.
    """
    if not emhass_config_path or not os.path.exists(emhass_config_path):
        return None
    if os.path.isfile(emhass_config_path):
        config_path = emhass_config_path
    else:
        config_path = os.path.join(emhass_config_path, "config.json")

    if not os.path.exists(config_path):
        return None
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def extract_planning_horizon(config: Optional[Dict[str, Any]]) -> Optional[int]:
    """Extract planning horizon (days) from EMHASS config."""
    if not config:
        return None
    end_timesteps = config.get("end_timesteps_of_each_deferrable_load")
    if (
        not end_timesteps
        or not isinstance(end_timesteps, list)
        or len(end_timesteps) == 0
    ):
        return None
    horizon_days = end_timesteps[0] // 24
    return horizon_days if horizon_days >= 1 else None


def extract_max_deferrable_loads(config: Optional[Dict[str, Any]]) -> Optional[int]:
    """Extract max deferrable loads from EMHASS config."""
    if not config:
        return None
    num_loads = config.get("number_of_deferrable_loads")
    return num_loads if num_loads is not None and num_loads >= 1 else None


@dataclass
class _EmhassCtx:
    """Context for EMHASS validation."""

    user_input: Dict[str, Any]
    hass: HomeAssistant
    vehicle_data: Dict[str, Any]
    schema_description: str


# CC-N-ACCEPTED: cc=19 — each branch is a distinct validation rule:
# planning_horizon range, planning_horizon vs EMHASS config, planning_sensor
# existence + parsing + value comparison, max_loads range + config comparison.
# Extracting would split a coherent validation pipeline into meaningless
# fragments; the branching IS the business logic.
def validate_emhass_input(
    ctx: _EmhassCtx,
    emhass_config_path: str,
) -> Optional[str]:
    """Validate EMHASS step user input.

    Returns error key string if validation fails, None if it passes.
    On success, updates ctx.vehicle_data in place.
    """
    emhass_config = read_emhass_config(emhass_config_path)
    emhass_horizon = extract_planning_horizon(emhass_config)
    emhass_max_loads = extract_max_deferrable_loads(emhass_config)

    if emhass_horizon:
        _LOGGER.info(
            "EMHASS config: horizon=%s days, max_loads=%s",
            emhass_horizon,
            emhass_max_loads,
        )

    ui = ctx.user_input

    # Validate planning horizon
    planning_horizon = ui.get(CONF_PLANNING_HORIZON)
    if planning_horizon is not None:
        if planning_horizon < 1 or planning_horizon > 365:
            return "invalid_planning_horizon"

        if emhass_horizon and planning_horizon > emhass_horizon:
            _LOGGER.warning(
                "User planning_horizon (%d) exceeds EMHASS config (%d days). "
                "This may cause optimization issues.",
                planning_horizon,
                emhass_horizon,
            )

        planning_sensor = ui.get(CONF_PLANNING_SENSOR)
        if planning_sensor:
            sensor_state = ctx.hass.states.get(planning_sensor)
            if sensor_state and sensor_state.state not in (
                "unknown",
                "unavailable",
                "",
            ):
                try:
                    sensor_horizon = int(float(sensor_state.state))
                    _LOGGER.info(
                        "Planning sensor %s value: %d days",
                        planning_sensor,
                        sensor_horizon,
                    )
                    if planning_horizon > sensor_horizon:
                        _LOGGER.warning(
                            "User horizon (%d) > sensor (%d days). "
                            "May cause issues. Consider <= %d.",
                            planning_horizon,
                            sensor_horizon,
                            sensor_horizon,
                        )
                except (ValueError, TypeError) as err:
                    _LOGGER.warning(
                        "Could not parse planning sensor %s value: %s",
                        planning_sensor,
                        err,
                    )
            else:
                _LOGGER.info(
                    "Planning sensor %s not available, using manual input",
                    planning_sensor,
                )

    # Validate max deferrable loads
    max_loads = ui.get(CONF_MAX_DEFERRABLE_LOADS)
    if max_loads is not None:
        if max_loads < 10 or max_loads > 100:
            return "invalid_max_deferrable_loads"

        if emhass_max_loads and max_loads > emhass_max_loads:
            _LOGGER.warning(
                "User loads (%d) > EMHASS config (%d loads). "
                "This may cause optimization issues.",
                max_loads,
                emhass_max_loads,
            )

    # Update vehicle data
    ctx.vehicle_data.update(ui)

    # Logging
    if CONF_PLANNING_SENSOR in ui and ui[CONF_PLANNING_SENSOR]:
        _LOGGER.info(
            "EMHASS planning sensor configured: %s",
            ui[CONF_PLANNING_SENSOR],
        )

    _LOGGER.info(
        "EMHASS config: horizon=%s, max_loads=%s, sensor=%s",
        ctx.vehicle_data.get(CONF_PLANNING_HORIZON),
        ctx.vehicle_data.get(CONF_MAX_DEFERRABLE_LOADS),
        ctx.vehicle_data.get(CONF_PLANNING_SENSOR, "not configured"),
    )

    _LOGGER.debug(
        "Config flow step 3 (emhass): horizon=%s, max_loads=%s",
        ui.get(CONF_PLANNING_HORIZON),
        ui.get(CONF_MAX_DEFERRABLE_LOADS),
    )

    return None
