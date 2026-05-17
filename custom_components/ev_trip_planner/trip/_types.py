"""Type definitions extracted from trip_manager.py.

This module holds TypedDict definitions used across the trip package
and by the top-level trip_manager module.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional, TypedDict

if TYPE_CHECKING:
    from custom_components.ev_trip_planner.emhass import EMHASSAdapter
    from custom_components.ev_trip_planner.yaml_trip_storage import YamlTripStorage


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


@dataclass(frozen=True)
class TripManagerConfig:
    """Configuration passed to TripManager to reduce __init__ arity."""

    entry_id: str | None = None
    presence_config: dict[str, Any] | None = None
    storage: YamlTripStorage | None = None
    emhass_adapter: EMHASSAdapter | None = None
