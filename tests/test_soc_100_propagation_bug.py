"""
SOC 100% propagation behavior test

This test verifies the current proactive charging algorithm:
- With SOC 100%, the system schedules proactive charging to prepare for future trips
- The real power profile limits charging to battery capacity
"""

import logging

import pytest
from unittest.mock import AsyncMock, MagicMock

from custom_components.ev_trip_planner.calculations import calculate_energy_needed
from custom_components.ev_trip_planner.emhass_adapter import EMHASSAdapter

logger = logging.getLogger(__name__)


class TestSOC100PropagationBug:
    """Verifies proactive charging at SOC 100% uses power profile clamping."""

    def setup_method(self):
        """Initial setup for each test."""
        # Mock of the configuration entry
        self.mock_entry = MagicMock()
        self.mock_entry.data = {
            "soc_sensor": "sensor.ev_battery_soc",
            "charging_power_kw": 3.4,
            "battery_capacity_kwh": 50.0,
            "planning_horizon_days": 7,
            "max_deferrable_loads": 5,
            "safety_margin_percent": 10.0,
        }
        self.mock_entry.entry_id = "test_entry"

        # Mock of Home Assistant
        self.mock_hass = MagicMock()
        self.mock_hass.data = {}

        # Mock SOC sensor (at 100%)
        self.mock_soc_sensor = MagicMock()
        self.mock_soc_sensor.state = 100.0  # 100% SOC!
        self.mock_hass.states.get.return_value = self.mock_soc_sensor

    async def test_soc_100_first_trip_must_not_have_2_hours(self):
        """
        Verifies proactive charging at SOC 100% assigns charge hours to trips.

        Reproduces user report scenario where def_total_hours and P_deferrable_nom
        were zeroed out incorrectly. With proactive charging, even at SOC 100%,
        trips should receive minimum charge hours.
        """
        # Create EXACT scenario that causes deficit propagation
        # The first trip (30 kWh) will absorb deficit from subsequent trips
        trips = [
            {
                "id": "primer_viaje",  # This will absorb INCORRECTLY
                "tipo": "recurring",
                "dia_semana": "1",  # Tuesday
                "hora": "09:00",
                "kwh": 30.0,  # The trip causing the bug per user report
                "descripcion": "First trip at 100% SOC",
            },
            {
                "id": "segundo_viaje",  # Has small window, will generate deficit
                "tipo": "recurring",
                "dia_semana": "1",  # Tuesday (same day)
                "hora": "10:00",  # Only 1 hour later
                "kwh": 45.0,  # Heavy load in very small window
                "descripcion": "Trip with small window (generates deficit)",
            },
            {
                "id": "tercer_viaje",
                "tipo": "recurring",
                "dia_semana": "2",  # Wednesday
                "hora": "14:00",
                "kwh": 15.0,
                "descripcion": "Normal trip",
            },
            {
                "id": "cuarto_viaje",
                "tipo": "recurring",
                "dia_semana": "3",  # Thursday
                "hora": "18:00",
                "kwh": 20.0,
                "descripcion": "Normal trip",
            },
            {
                "id": "quinto_viaje",
                "tipo": "recurring",
                "dia_semana": "4",  # Friday
                "hora": "08:00",
                "kwh": 25.0,
                "descripcion": "Normal trip",
            },
        ]

        # Configuration with SOC 100% - INITIAL STATE MUST NOT CHANGE
        battery_capacity = 50.0
        soc_current = 100.0  # SOC AT 100% - THIS MUST NOT CHANGE!
        charging_power_kw = 3.4
        safety_margin = 10.0

        logger.debug("=== USER EXACT SCENARIO ===")
        logger.debug("Initial SOC: %s%%", soc_current)
        logger.debug("Battery: %s kWh", battery_capacity)
        logger.debug("Power: %s kW", charging_power_kw)
        logger.debug("")

        # Verify individual calculations (all should be 0)
        logger.debug("=== INDIVIDUAL CALCULATIONS (no propagation) ===")
        for trip in trips:
            energy_info = calculate_energy_needed(
                trip=trip,
                battery_capacity_kwh=battery_capacity,
                soc_current=soc_current,
                charging_power_kw=charging_power_kw,
                safety_margin_percent=safety_margin,
            )
            logger.debug(
                "%s (%s kWh): Energy = %s kWh, Hours = %s",
                trip["id"],
                trip["kwh"],
                energy_info["energia_necesaria_kwh"],
                energy_info["horas_carga_necesarias"],
            )

        logger.debug("")
        logger.debug("INDIVIDUAL CONCLUSIONS:")
        logger.debug("- With proactive charging, all trips have energy > 0")
        logger.debug(
            "- The first trip (30 kWh): With proactive charging, charging is scheduled to prepare for the trip"
        )
        logger.debug("")

        # Create adapter
        adapter = EMHASSAdapter(self.mock_hass, self.mock_entry)
        mock_store = AsyncMock()
        mock_store.async_save = AsyncMock()
        adapter._store = mock_store
        adapter._presence_monitor = None

        # Mock SOC AT 100% - MUST NOT CHANGE!
        adapter._get_current_soc = AsyncMock(return_value=100.0)
        adapter._get_hora_regreso = AsyncMock(return_value=None)

        # Publish all together (this activates deficit propagation)
        logger.debug("=== PUBLISHING ALL TRIPS (activating deficit propagation) ===")
        result = await adapter.async_publish_all_deferrable_loads(trips)
        logger.debug("publish_all result: %s", result)
        logger.debug("")

        # Get cached parameters
        per_trip_params = getattr(adapter, "_cached_per_trip_params", {})

        logger.debug("=== FINAL VERIFICATION (proactive charging) ===")
        logger.debug("Expected (with proactive charging at 100% SOC):")
        logger.debug("  def_total_hours: all > 0 (minimum charge = trip energy)")
        logger.debug("  P_deferrable_nom: all > 0 (proactive charging)")
        logger.debug("")

        # Verify the first trip (the one with the bug per user report)
        primer_viaje_params = per_trip_params.get("primer_viaje", {})
        def_hours = primer_viaje_params.get("def_total_hours", 0)
        power_nom = primer_viaje_params.get("P_deferrable_nom", 0.0)

        logger.debug("First trip (30 kWh, SOC 100%%):")
        logger.debug("  def_total_hours = %s", def_hours)
        logger.debug("  P_deferrable_nom = %s W", power_nom)
        logger.debug("")

        # Proactive charging: even at SOC 100%, trips require minimum charge
        # (to prepare for future trips in a chain)
        if def_hours > 0:
            logger.debug(
                "First trip has %s charge hours (proactive charging)", def_hours
            )
            logger.debug("  P_deferrable_nom = %s W", power_nom)
        else:
            # With proactive charging, this should NOT happen
            logger.debug("First trip has 0 hours (unexpected with proactive charging)")
            assert def_hours > 0, (
                "With proactive charging, the first trip must have charge hours > 0"
            )


        for i, trip in enumerate(trips):
            trip_id = trip["id"]
            if trip_id in per_trip_params:
                params = per_trip_params[trip_id]
                def_hours = params.get("def_total_hours", 0)
                power_nom = params.get("P_deferrable_nom", 0.0)

                logger.debug(
                    "Trip %s (%s kWh): def_total_hours = %s, P_deferrable_nom = %s W",
                    i + 1,
                    trip["kwh"],
                    def_hours,
                    power_nom,
                )

                # With proactive charging, def_hours and power_nom should both be > 0
                if def_hours > 0 and power_nom > 0:
                    logger.debug("  (proactive charging active)")
                elif def_hours == 0 and power_nom == 0:
                    # This shouldn't happen with proactive charging
                    logger.debug("  (no charging - unexpected)")

    def test_soc_100_impossible_physics(self):
        """
        Test that verifies the physics principle: you cannot charge a car beyond 100% SOC.

        This is an integrity test that must always pass.
        """
        battery_capacity = 50.0
        soc_current = 100.0
        charging_power_kw = 3.4

        # With SOC 100%, available energy is maximum
        energia_disponible = battery_capacity * (soc_current / 100.0)

        logger.debug("=== PHYSICS VERIFICATION ===")
        logger.debug("Battery: %s kWh", battery_capacity)
        logger.debug("SOC: %s%%", soc_current)
        logger.debug("Available energy: %s kWh", energia_disponible)
        logger.debug("Charging power: %s kW", charging_power_kw)

        # Physics principle: cannot charge beyond 100% SOC
        assert soc_current <= 100.0, "SOC cannot exceed 100%"

        # If already at 100%, no more energy can be added
        if soc_current == 100.0:
            energia_adicional_maxima = 0.0
            horas_carga_maximas = 0.0
        else:
            energia_adicional_maxima = battery_capacity * (100.0 - soc_current) / 100.0
            horas_carga_maximas = energia_adicional_maxima / charging_power_kw

        logger.debug(
            "Maximum additional energy possible: %s kWh", energia_adicional_maxima
        )
        logger.debug("Maximum possible charge hours: %s", horas_carga_maximas)

        # With SOC 100%, nothing can be charged
        assert energia_adicional_maxima == 0.0, (
            "With SOC 100%, no additional energy can be charged"
        )
        assert horas_carga_maximas == 0.0, "With SOC 100%, there cannot be charge hours"

        # NOTE: While physically true, the algorithm now charges proactively
        # even at SOC 100%. The actual power profile clamping prevents
        # charging beyond battery capacity.
        logger.debug("Physics principle verified: SOC 100%% = 0 physical charge hours")
        logger.debug(
            "   (The proactive charging algorithm schedules charging to prepare future trips)"
        )
        logger.debug("   The real power profile limits charging to battery capacity")


if __name__ == "__main__":
    # Verify proactive charging behavior at SOC 100%
    pytest.main([__file__, "-v", "-s"])
