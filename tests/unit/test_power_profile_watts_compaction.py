"""Tests para verificar que power_profile_watts compacta carga al final de la ventana.

RED phase: Este test DEBE FALLAR con el código actual porque
async_publish_all_deferrable_loads() líneas 297-303 llena el rango [start, end)
completo en lugar de solo def_total slots al final.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.ev_trip_planner.emhass.adapter import EMHASSAdapter


@pytest.fixture
def mock_store():
    """Mock Store for adapter persistence."""
    store = MagicMock()
    store.async_load = AsyncMock(return_value={})
    store.async_save = AsyncMock()
    return store


@pytest.fixture
def mock_hass(tmp_path, mock_store):
    """Mock Home Assistant instance."""
    hass = MagicMock()
    hass.config = MagicMock()
    hass.config.config_dir = str(tmp_path)
    hass.config.time_zone = "UTC"
    hass.data = {}
    hass.services = MagicMock()
    hass.services.async_call = AsyncMock()
    hass.services.has_service = MagicMock(return_value=True)
    with patch(
        "custom_components.ev_trip_planner.emhass.adapter.Store",
        return_value=mock_store,
    ):
        yield hass


@pytest.fixture
def mock_entry():
    """Minimal MagicMock ConfigEntry."""
    entry = MagicMock()
    entry.entry_id = "test_vehicle"
    entry.data = {"charging_power_kw": 3.6}
    entry.options = {}
    return entry


class TestPowerProfileWattsCompaction:
    """Test that power_profile_watts has charging slots ONLY at END of window."""

    @pytest.mark.asyncio
    async def test_power_profile_watts_compacted_at_end_not_full_range(
        self, mock_hass, mock_entry, mock_store
    ):
        """Bug detection: power_profile_watts debe tener solo def_total slots al final.

        Escenario: trip con def_start=10, def_end=20, def_total=5, power_watts=3600

        CORRECTO: power_profile tiene 5 slots de 3600W en posiciones [15, 16, 17, 18, 19]
                  y 0 en todas las demás posiciones (incluyendo [10, 11, 12, 13, 14])

        BUG: power_profile tiene 10 slots de 3600W en posiciones [10..19]
             porque líneas 297-303 usan range(start, end) en lugar de compactar al final.
        """
        with patch(
            "custom_components.ev_trip_planner.emhass.adapter.Store",
            return_value=mock_store,
        ):
            adapter = EMHASSAdapter(hass=mock_hass, entry=mock_entry)
            await adapter.async_load()

        # Patch _get_current_soc to return a known SOC
        with patch.object(
            adapter, "_get_current_soc", new_callable=AsyncMock
        ) as mock_soc:
            mock_soc.return_value = 50.0  # 50% SOC

            # Patch _get_hora_regreso to return a known value
            with patch.object(
                adapter, "_get_hora_regreso", new_callable=AsyncMock
            ) as mock_hora:
                mock_hora.return_value = (
                    datetime.now(timezone.utc) - timedelta(hours=2)
                )

                now = datetime.now(timezone.utc)

                # Trip: departure in 20 hours from now
                # Window should be [10, 20] (10h available for charging before departure)
                # def_total_hours should be ~5 (based on kwh/charging_power)
                trip = {
                    "id": "trip_001",
                    "tipo": "puntual",
                    "datetime": (now + timedelta(hours=20)).isoformat(),
                    "kwh": 18.0,  # 18 kWh needed / 3.6 kW = 5 hours
                }

                trips = [trip]

                # Disable deficit propagation to keep test predictable
                with patch.object(adapter, "_apply_deficit_propagation"):
                    result = await adapter.async_publish_all_deferrable_loads(
                        trips, charging_power_kw=3.6
                    )

        assert result is True

        # Get the cached params to see what was calculated
        cache = adapter._cached_per_trip_params.get("trip_001", {})
        def_start = cache.get("def_start_timestep", 0)
        def_end = cache.get("def_end_timestep", 0)
        def_total = cache.get("def_total_hours", 0)

        print(f"\n=== DEBUG ===")
        print(f"def_start_timestep: {def_start}")
        print(f"def_end_timestep: {def_end}")
        print(f"def_total_hours: {def_total}")
        print(f"charging_power_kw: {cache.get('power_watts', 0) / 1000}")

        # Get power_profile
        power_profile = adapter._cached_power_profile
        non_zero_count = sum(1 for v in power_profile if v > 0)

        print(f"non_zero_count in power_profile: {non_zero_count}")
        print(f"Expected: {def_total} (compactado al final)")
        print(f"Bug shows: {def_end - def_start} (rango completo [start, end))")

        # THE KEY ASSERTION: non_zero_count should equal def_total (compacted at end)
        # But with the bug, it equals (def_end - def_start) which is larger
        assert non_zero_count == def_total, (
            f"power_profile_watts debería tener {def_total} slots no-cero (def_total_hours), "
            f"pero tiene {non_zero_count}. "
            f"El bug está en adapter.py líneas 297-303: llena range(start={def_start}, end={def_end}) "
            f"= {def_end - def_start} slots en lugar de compactar {def_total} slots al final."
        )

        # Verify positions before charging_start are 0
        # charging_start = def_end - def_total
        charging_start = def_end - def_total
        for t in range(0, charging_start):
            if t < len(power_profile):
                assert power_profile[t] == 0, (
                    f"Posición {t} debería ser 0 (antes de charging_start={charging_start}), "
                    f"pero es {power_profile[t]}"
                )

        # Verify positions in the "middle" of window (before charging_start) are 0
        for t in range(charging_start, def_end - def_total):
            if t < len(power_profile):
                assert power_profile[t] == 0, (
                    f"Posición {t} debería ser 0 (entre def_start={def_start} y charging_start={charging_start}), "
                    f"pero es {power_profile[t]}"
                )

    @pytest.mark.asyncio
    async def test_power_profile_watts_multiple_trips_overlapping_windows(
        self, mock_hass, mock_entry, mock_store
    ):
        """Bug detection con múltiples trips con ventanas solapadas.

        Trip 1: departure in ~15h, window [5, 15], def_total=3 → charging en [12, 13, 14]
        Trip 2: departure in ~20h, window [10, 20], def_total=5 → charging en [15, 16, 17, 18, 19]

        CORRECTO: power_profile tiene 8 slots no-cero en posiciones correctas
        BUG: power_profile tiene 15 slots no-cero (5-15 + 10-20 = 10 + 10 = 20)
        """
        with patch(
            "custom_components.ev_trip_planner.emhass.adapter.Store",
            return_value=mock_store,
        ):
            adapter = EMHASSAdapter(hass=mock_hass, entry=mock_entry)
            await adapter.async_load()

        with patch.object(
            adapter, "_get_current_soc", new_callable=AsyncMock
        ) as mock_soc:
            mock_soc.return_value = 50.0

            with patch.object(
                adapter, "_get_hora_regreso", new_callable=AsyncMock
            ) as mock_hora:
                mock_hora.return_value = (
                    datetime.now(timezone.utc) - timedelta(hours=2)
                )

                now = datetime.now(timezone.utc)

                trip1 = {
                    "id": "trip_001",
                    "tipo": "puntual",
                    "datetime": (now + timedelta(hours=15)).isoformat(),
                    "kwh": 10.8,  # 10.8 kWh / 3.6 kW = 3 hours
                }

                trip2 = {
                    "id": "trip_002",
                    "tipo": "puntual",
                    "datetime": (now + timedelta(hours=20)).isoformat(),
                    "kwh": 18.0,  # 18 kWh / 3.6 kW = 5 hours
                }

                trips = [trip1, trip2]

                with patch.object(adapter, "_apply_deficit_propagation"):
                    result = await adapter.async_publish_all_deferrable_loads(
                        trips, charging_power_kw=3.6
                    )

        assert result is True

        # Get cached params
        cache1 = adapter._cached_per_trip_params.get("trip_001", {})
        cache2 = adapter._cached_per_trip_params.get("trip_002", {})

        def_total_1 = cache1.get("def_total_hours", 0)
        def_total_2 = cache2.get("def_total_hours", 0)
        expected_total = def_total_1 + def_total_2

        print(f"\n=== DEBUG ===")
        print(f"Trip 1: def_start={cache1.get('def_start_timestep')}, def_end={cache1.get('def_end_timestep')}, def_total={def_total_1}")
        print(f"Trip 2: def_start={cache2.get('def_start_timestep')}, def_end={cache2.get('def_end_timestep')}, def_total={def_total_2}")
        print(f"Expected non-zero: {expected_total}")

        power_profile = adapter._cached_power_profile
        non_zero_count = sum(1 for v in power_profile if v > 0)

        print(f"Actual non-zero: {non_zero_count}")

        # CORRECTO: expected_total slots (3 + 5 = 8)
        # BUG: 15-5 + 20-10 = 10 + 10 = 20 slots
        assert non_zero_count == expected_total, (
            f"power_profile_watts debería tener {expected_total} slots no-cero ({def_total_1}+{def_total_2}), "
            f"pero tiene {non_zero_count}. "
            f"Bug en líneas 297-303: range(start, end) en lugar de compactar al final."
        )

        # NEW: Verify windows are correctly separated by return_buffer_hours
        def_start_trip1 = cache1.get("def_start_timestep", 0)
        def_end_trip1 = cache1.get("def_end_timestep", 0)
        def_start_trip2 = cache2.get("def_start_timestep", 0)

        # def_start_trip2 debe ser exactamente def_end_trip1 + return_buffer_hours
        # El código usa return_buffer_hours=4.0 por defecto
        RETURN_BUFFER = 4.0  # hours between trips in the real code
        assert def_start_trip2 == def_end_trip1 + RETURN_BUFFER, (
            f"Trip 2 def_start={def_start_trip2} debería ser exactamente "
            f"Trip 1 def_end={def_end_trip1} + return_buffer={RETURN_BUFFER}h = {def_end_trip1 + RETURN_BUFFER}. "
            f"Las ventanas de trips consecutivos deben estar separadas por return_buffer_hours."
        )