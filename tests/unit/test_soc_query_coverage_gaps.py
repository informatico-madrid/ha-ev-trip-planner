"""Tests for uncovered _soc_query.py paths (lines 66-78)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from custom_components.ev_trip_planner.trip._soc_query import SOCQuery


class TestAsyncCalcularEnergiaNecesaria:
    """Test async_calcular_energia_necesaria validation branches (lines 66-78)."""

    @pytest.mark.asyncio
    async def test_missing_battery_capacity_kwh_returns_zero_with_alerta(self):
        """Lines 66-78: Missing battery_capacity_kwh → returns zero energy with alerta=true."""
        state = MagicMock()
        query = SOCQuery(state)

        trip = {"id": "trip_1", "kwh": 10.0}
        vehicle_config = {
            "charging_power_kw": 7.0,
            "safety_margin_percent": 10.0,
        }

        result = await query.async_calcular_energia_necesaria(trip, vehicle_config)

        assert result["energia_necesaria_kwh"] == 0.0
        assert result["horas_carga_necesarias"] == 0
        assert result["alerta_tiempo_insuficiente"] is True
        assert result["horas_disponibles"] == 0.0
        assert result["margen_seguridad_aplicado"] == 0.0

    @pytest.mark.asyncio
    async def test_missing_charging_power_kw_returns_zero_with_alerta(self):
        """Lines 66-78: Missing charging_power_kw → returns zero energy with alerta=true."""
        state = MagicMock()
        query = SOCQuery(state)

        trip = {"id": "trip_2", "kwh": 15.0}
        vehicle_config = {
            "battery_capacity_kwh": 60.0,
            # Missing charging_power_kw
            "safety_margin_percent": 10.0,
        }

        result = await query.async_calcular_energia_necesaria(trip, vehicle_config)

        assert result["energia_necesaria_kwh"] == 0.0
        assert result["horas_carga_necesarias"] == 0
        assert result["alerta_tiempo_insuficiente"] is True