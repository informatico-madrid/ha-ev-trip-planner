"""Type definitions extracted from trip_manager.py.

This module holds TypedDict definitions used across the trip package
and by the top-level trip_manager module.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional, TypedDict


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
