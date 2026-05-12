"""Shared state for TripManager — composition-over-inheritance backbone.

All mixin classes receive a single `TripManagerState` instance in their
`__init__` and store it as `self._state`. Every reference to shared state
(attributes and methods) goes through `self._state.xxx`.
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields
from typing import Any, Callable, Dict, Optional

from homeassistant.core import HomeAssistant

from ..emhass import EMHASSAdapter
from ..yaml_trip_storage import YamlTripStorage
from ._sensor_callbacks import _SensorCallbacks

_UNSET: Any = object()


@dataclass
class TripManagerState:
    """All shared state between TripManager and its mixins."""

    # ── Core attributes ──────────────────────────────────────────
    hass: HomeAssistant
    vehicle_id: str
    entry_id: Optional[str] = None
    _trips: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    recurring_trips: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    punctual_trips: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    last_update: Optional[str] = None
    storage: Optional[YamlTripStorage] = None
    emhass_adapter: Optional[EMHASSAdapter] = None
    vehicle_controller: Any = None
    sensor_callbacks: _SensorCallbacks = field(default_factory=_SensorCallbacks)

    # ── Method references (bound at runtime on TripManager) ──────
    # These are set to _UNSET by default and populated by TripManager.__init__.
    # At runtime they are always bound methods, never None.
    async_save_trips: Callable[..., Any] = field(default=_UNSET, repr=False, compare=False)  # type: ignore[assignment]
    _load_trips: Callable[..., Any] = field(default=_UNSET, repr=False, compare=False)  # type: ignore[assignment]
    _save_trips_yaml: Callable[..., Any] = field(default=_UNSET, repr=False, compare=False)  # type: ignore[assignment]
    _sanitize_recurring_trips: Callable[..., Any] = field(default=_UNSET, repr=False, compare=False)  # type: ignore[assignment]
    _reset_trips: Callable[..., Any] = field(default=_UNSET, repr=False, compare=False)  # type: ignore[assignment]
    _validate_hora: Callable[..., Any] = field(default=_UNSET, repr=False, compare=False)  # type: ignore[assignment]
    _is_trip_today: Callable[..., Any] = field(default=_UNSET, repr=False, compare=False)  # type: ignore[assignment]
    _parse_trip_datetime: Callable[..., Any] = field(default=_UNSET, repr=False, compare=False)  # type: ignore[assignment]
    _get_charging_power: Callable[..., Any] = field(default=_UNSET, repr=False, compare=False)  # type: ignore[assignment]
    _get_trip_time: Callable[..., Any] = field(default=_UNSET, repr=False, compare=False)  # type: ignore[assignment]
    async_get_kwh_needed_today: Callable[..., Any] = field(default=_UNSET, repr=False, compare=False)  # type: ignore[assignment]
    async_get_next_trip_after: Callable[..., Any] = field(default=_UNSET, repr=False, compare=False)  # type: ignore[assignment]
    async_get_vehicle_soc: Callable[..., Any] = field(default=_UNSET, repr=False, compare=False)  # type: ignore[assignment]
    async_get_hours_needed_today: Callable[..., Any] = field(default=_UNSET, repr=False, compare=False)  # type: ignore[assignment]
    async_calcular_energia_necesaria: Callable[..., Any] = field(default=_UNSET, repr=False, compare=False)  # type: ignore[assignment]
    async_get_recurring_trips: Callable[..., Any] = field(default=_UNSET, repr=False, compare=False)  # type: ignore[assignment]
    async_get_punctual_trips: Callable[..., Any] = field(default=_UNSET, repr=False, compare=False)  # type: ignore[assignment]
    get_all_trips: Callable[..., Any] = field(default=_UNSET, repr=False, compare=False)  # type: ignore[assignment]
    async_get_next_trip: Callable[..., Any] = field(default=_UNSET, repr=False, compare=False)  # type: ignore[assignment]
    calcular_soc_inicio_trips: Callable[..., Any] = field(default=_UNSET, repr=False, compare=False)  # type: ignore[assignment]
    calcular_ventana_carga_multitrip: Callable[..., Any] = field(default=_UNSET, repr=False, compare=False)  # type: ignore[assignment]
    _calcular_soc_objetivo_base: Callable[..., Any] = field(default=_UNSET, repr=False, compare=False)  # type: ignore[assignment]
    _calcular_tasa_carga_soc: Callable[..., Any] = field(default=_UNSET, repr=False, compare=False)  # type: ignore[assignment]
    publish_deferrable_loads: Callable[..., Any] = field(default=_UNSET, repr=False, compare=False)  # type: ignore[assignment]
    _async_publish_new_trip_to_emhass: Callable[..., Any] = field(default=_UNSET, repr=False, compare=False)  # type: ignore[assignment]
    _async_remove_trip_from_emhass: Callable[..., Any] = field(default=_UNSET, repr=False, compare=False)  # type: ignore[assignment]
    _async_sync_trip_to_emhass: Callable[..., Any] = field(default=_UNSET, repr=False, compare=False)  # type: ignore[assignment]
    async_update_trip_sensor: Callable[..., Any] = field(default=_UNSET, repr=False, compare=False)  # type: ignore[assignment]

    def __post_init__(self) -> None:
        """Replace _UNSET sentinel with None for method fields."""
        for fld in fields(self):
            val = getattr(self, fld.name)
            if val is _UNSET:
                object.__setattr__(self, fld.name, None)
