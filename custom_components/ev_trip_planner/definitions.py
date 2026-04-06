"""Sensor definitions for EV Trip Planner.

Contains TripSensorEntityDescription dataclass and TRIP_SENSORS tuple.
"""

from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import UnitOfEnergy
from typing import Any, Callable


@dataclass(frozen=True)
class TripSensorEntityDescription(SensorEntityDescription):
    """Entity description for trip sensors.

    Extends SensorEntityDescription with
    custom fields for trip data processing.
    """

    value_fn: Callable[[dict], Any] = lambda data: None
    attrs_fn: Callable[[dict], dict] = lambda data: {}
    restore: bool = False


TRIP_SENSORS = (
    TripSensorEntityDescription(
        key="recurring_trips_count",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: len(data.get("recurring_trips", {})),
    ),
    TripSensorEntityDescription(
        key="punctual_trips_count",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: len(data.get("punctual_trips", {})),
    ),
    TripSensorEntityDescription(
        key="trips_list",
        value_fn=lambda data: str(
            list(data.get("recurring_trips", {}).keys())
        ),
    ),
    TripSensorEntityDescription(
        key="kwh_needed_today",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        value_fn=lambda data: data.get("kwh_today", 0.0),
        restore=True,
    ),
    TripSensorEntityDescription(
        key="hours_needed_today",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("hours_today", 0.0),
        restore=True,
    ),
    TripSensorEntityDescription(
        key="next_trip",
        value_fn=lambda data: data.get("next_trip", {}).get("id"),
        restore=True,
    ),
    TripSensorEntityDescription(
        key="next_deadline",
        value_fn=lambda data: data.get("next_trip", {}).get("_deadline"),
        restore=True,
    ),
)
