"""Sensor definitions for EV Trip Planner.

Contains TripSensorEntityDescription dataclass and TRIP_SENSORS tuple.
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from homeassistant.components.sensor import SensorEntityDescription

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import UnitOfEnergy


def default_attrs_fn(data: dict[str, Any]) -> dict[str, Any]:
    """Default attrs_fn that includes recurring and punctual trips.

    Returns trips data from coordinator.data for use as sensor attributes.
    This is the default behavior for most sensors.
    """
    return {
        "recurring_trips": (
            list(data.get("recurring_trips", {}).values()) if data else []
        ),
        "punctual_trips": list(data.get("punctual_trips", {}).values()) if data else [],
    }


@dataclass(frozen=True)
class TripSensorEntityDescription(SensorEntityDescription):
    """Entity description for trip sensors.

    Extends SensorEntityDescription with
    custom fields for trip data processing.
    """

    value_fn: Callable[[dict[str, Any]], Any] = field(
        default_factory=lambda: lambda data: None
    )
    attrs_fn: Callable[[dict[str, Any]], dict[str, Any]] = field(
        default_factory=lambda: default_attrs_fn
    )
    restore: bool = False
    exists_fn: Callable[[dict[str, Any]], bool] = field(
        default_factory=lambda: lambda _: True
    )


TRIP_SENSORS = (
    TripSensorEntityDescription(
        key="recurring_trips_count",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: len(data.get("recurring_trips", {})) if data else 0,
    ),
    TripSensorEntityDescription(
        key="punctual_trips_count",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: len(data.get("punctual_trips", {})) if data else 0,
    ),
    TripSensorEntityDescription(
        key="trips_list",
        value_fn=lambda data: (
            str(list(data.get("recurring_trips", {}).keys())) if data else "[]"
        ),
    ),
    TripSensorEntityDescription(
        key="kwh_needed_today",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        value_fn=lambda data: data.get("kwh_today", 0.0) if data else 0.0,
        restore=True,
    ),
    TripSensorEntityDescription(
        key="hours_needed_today",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("hours_today", 0.0) if data else 0.0,
        restore=True,
    ),
    TripSensorEntityDescription(
        key="next_trip",
        value_fn=lambda data: (data.get("next_trip") or {}).get("id") if data else None,
        restore=True,
    ),
    TripSensorEntityDescription(
        key="next_deadline",
        value_fn=lambda data: (
            (data.get("next_trip") or {}).get("_deadline") if data else None
        ),
        restore=True,
    ),
)
