"""Pure helper functions for the sensor module.

Extracted from _async_setup.py and entity classes as part of US-5 testability
refactor (Spec 3). Each helper takes explicit inputs and returns deterministic
outputs — no HA runtime dependency.
"""

from __future__ import annotations

import logging  # pragma: no mutate  # EQ-104
from datetime import datetime
from typing import Any, Dict, List

from ..const import TRIP_TYPE_PUNCTUAL
from ..definitions import TRIP_SENSORS

_LOGGER = logging.getLogger(__name__)


# =============================================================================
# Time formatting
# =============================================================================


def format_window_time(value: Any) -> str | None:
    """Format window time to HH:MM from datetime or ISO string.

    Args:
        value: Either a datetime object or an ISO format string.

    Returns:
        Time formatted as HH:MM, or None if formatting fails.
    """
    if value is None:
        return None
    try:
        if isinstance(value, datetime):
            dt_value = value
        elif isinstance(value, str):
            dt_value = datetime.fromisoformat(value)
        else:
            return None
        return dt_value.strftime("%H:%M")
    except (ValueError, TypeError, AttributeError):
        return None


# =============================================================================
# Trip data extraction
# =============================================================================


def get_trip_data(
    coordinator_data: Dict[str, Any] | None, trip_id: str
) -> Dict[str, Any]:
    """Get trip data from coordinator data by trip_id.

    Search order: recurring_trips first, then punctual_trips.
    Returns empty dict if not found.

    Args:
        coordinator_data: coordinator.data dict.
        trip_id: The trip identifier to look up.

    Returns:
        Trip data dict or empty dict if not found.
    """
    if coordinator_data is None:
        return {}
    recurring_trips = coordinator_data.get("recurring_trips", {})
    punctual_trips = coordinator_data.get("punctual_trips", {})
    trip_data = recurring_trips.get(trip_id)
    if trip_data is None:
        trip_data = punctual_trips.get(trip_id)
    return trip_data if trip_data is not None else {}


def determine_trip_estado(trip_data: Dict[str, Any]) -> str | None:
    """Determine the estado (state) string for a trip.

    Args:
        trip_data: Trip data dict from coordinator.

    Returns:
        "recurrente" for recurring trips, the trip's "estado" for punctual trips,
        or None if trip_data is empty.
    """
    if not trip_data:
        return None
    trip_type = trip_data.get("tipo", "unknown")
    if trip_type == TRIP_TYPE_PUNCTUAL:
        return trip_data.get("estado", "pendiente")
    return "recurrente"


# =============================================================================
# Trip attribute building
# =============================================================================

TRIP_ATTR_KEYS: tuple[str, ...] = (
    "trip_id",
    "trip_type",
    "descripcion",
    "km",
    "kwh",
    "fecha_hora",
    "activo",
    "estado",
)


def build_trip_attributes(trip_data: Dict[str, Any]) -> Dict[str, Any]:
    """Build extra_state_attributes dict from trip data.

    All defaults are applied for missing keys.

    Args:
        trip_data: Trip data dict from coordinator.

    Returns:
        Dict with keys from TRIP_ATTR_KEYS, or empty dict if trip_data is empty.
    """
    if not trip_data:
        return {}
    return {
        "trip_id": trip_data.get("id", ""),
        "trip_type": trip_data.get("tipo", "unknown"),
        "descripcion": trip_data.get("descripcion", ""),
        "km": trip_data.get("km", 0.0),
        "kwh": trip_data.get("kwh", 0.0),
        "fecha_hora": trip_data.get("datetime", trip_data.get("hora", "")),
        "activo": trip_data.get("activo", True),
        "estado": trip_data.get("estado", "pendiente"),
    }


# =============================================================================
# EMHASS attribute building
# =============================================================================


def build_emhass_zeroed_attributes(trip_id: str) -> Dict[str, Any]:
    """Return zeroed/default values for all 9 EMHASS attributes.

    Args:
        trip_id: The trip identifier to include in the output.

    Returns:
        Dict with all 9 keys set to zero/None/empty values.
    """
    return {
        "def_total_hours": 0.0,
        "P_deferrable_nom": 0.0,
        "def_start_timestep": 0,
        # qg-accepted: AP05 — timesteps per day
        "def_end_timestep": 24,
        "power_profile_watts": [],
        "trip_id": trip_id,
        "emhass_index": -1,
        "kwh_needed": 0.0,
        "deadline": None,
    }


def filter_emhass_attributes(
    trip_params: Dict[str, Any],
) -> Dict[str, Any]:
    """Filter trip params to only the documented EMHASS attribute keys.

    Args:
        trip_params: Full trip params dict from coordinator.

    Returns:
        Dict with only TRIP_EMHASS_ATTR_KEYS keys.
    """
    from ..const import TRIP_EMHASS_ATTR_KEYS

    return {k: v for k, v in trip_params.items() if k in TRIP_EMHASS_ATTR_KEYS}


def build_emhass_attributes(
    coordinator_data: Dict[str, Any] | None, trip_id: str
) -> Dict[str, Any]:
    """Build extra_state_attributes for a trip EMHASS sensor.

    Args:
        coordinator_data: coordinator.data dict.
        trip_id: The trip identifier.

    Returns:
        Filtered EMHASS attributes or zeroed defaults.
    """
    if coordinator_data is None:
        return build_emhass_zeroed_attributes(trip_id)

    per_trip_params = coordinator_data.get("per_trip_emhass_params", {})
    trip_params = per_trip_params.get(trip_id)

    if trip_params is None:
        return build_emhass_zeroed_attributes(trip_id)

    return filter_emhass_attributes(trip_params)


# =============================================================================
# Deferrable load aggregation
# =============================================================================


def extract_active_trips(  # pragma: no mutate  # EQ-102
    per_trip_params: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Filter active trips and sort by (def_start_timestep, emhass_index).

    Args:
        per_trip_params: Full per_trip_emhass_params dict from coordinator.

    Returns:
        Sorted list of active trip param dicts.
    """
    active: List[Dict[str, Any]] = [
        params
        for params in per_trip_params.values()
        if params.get("activo", False)
    ]
    active.sort(
        key=lambda x: (x.get("def_start_timestep", 0), x.get("emhass_index", 0))
    )
    return active


def extract_matrix_and_count(
    active_trips: List[Dict[str, Any]],
) -> tuple[List[List[float]], int]:
    """Extract p_deferrable_matrix and count loads from active trips.

    Args:
        active_trips: Sorted list of active trip param dicts.

    Returns:
        Tuple of (matrix flattened, load count).
    """
    matrix: List[List[float]] = []
    count = 0
    for params in active_trips:
        p_matrix = params.get("p_deferrable_matrix")
        if p_matrix:
            matrix.extend(p_matrix)
            count += len(p_matrix)
        elif "p_deferrable_matrix" not in params:
            count += 1
    return matrix, count


def collect_deferrable_arrays(
    active_trips: List[Dict[str, Any]],
) -> Dict[str, List[float]]:
    """Derive deferrable arrays from scalar cache fields.

    Args:
        active_trips: Sorted list of active trip param dicts.

    Returns:
        Dict with four array keys derived from scalar fields.
    """
    return {
        "def_total_hours_array": [p.get("def_total_hours", 0) for p in active_trips],
        "p_deferrable_nom_array": [p.get("power_watts", 0) for p in active_trips],
        "def_start_timestep_array": [
            p.get("def_start_timestep", 0) for p in active_trips
        ],
        "def_end_timestep_array": [p.get("def_end_timestep", 0) for p in active_trips],
    }


def build_aggregate_result(
    matrix: List[List[float]],
    number_of_loads: int,
    arrays: Dict[str, List],
) -> Dict[str, Any]:
    """Build final aggregate result dict with conditional keys.

    Args:
        matrix: Flattened p_deferrable_matrix.
        number_of_loads: Count of deferrable loads.
        arrays: Dict of derived arrays.

    Returns:
        Aggregate result dict.
    """
    result: Dict[str, Any] = {"number_of_deferrable_loads": number_of_loads}
    if matrix:
        result["p_deferrable_matrix"] = matrix
    result.update(arrays)
    return result


# =============================================================================
# Sensor entity description scanning
# =============================================================================


def scan_sensors_for_entities(
    coordinator_data: Dict[str, Any] | None,
) -> List:
    """Filter TRIP_SENSORS based on exists_fn.

    Args:
        coordinator_data: coordinator.data dict.

    Returns:
        List of TripSensorEntityDescriptions that should be created.
    """
    test_data = coordinator_data if coordinator_data is not None else {}
    return [desc for desc in TRIP_SENSORS if desc.exists_fn(test_data)]


# =============================================================================
# Registry scanning helpers
# =============================================================================


def find_entity_id_by_trip(
    entity_id: str,
    trip_id: str,
    *,
    match_emhass: bool = False,
) -> bool:
    """Check if an entity_id belongs to a specific trip.

    Args:
        entity_id: The entity_id to check (e.g., "sensor.ev_trip_planner_v1_trip_t1").
        trip_id: Trip identifier to look for.
        match_emhass: If True, also require 'emhass' in the entity_id.

    Returns:
        True if the entity_id matches the trip (and optionally emhass filter).
    """
    if trip_id not in entity_id:
        return False
    if match_emhass and "emhass" not in entity_id:
        return False
    return True
