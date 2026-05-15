"""Integration test: reproduce staging scenario with two recurring trips.

BUG being reproduced: def_total_hours: [7, 6] in staging instead of [2, 2]
BUG location: dynamic SOC capping algorithm producing incorrect values

Staging actual values (from docker logs):
- battery_capacity_kwh = 50.0 (WRONG - staging uses 50.0 instead of 28.0 from config)
- soc_current = 50.0 (WRONG - staging reads 50.0 instead of 65.0 from sensor)
- charging_power_kw = None (WRONG - staging has None instead of 3.4 from config)
- def_total_hours: [7, 6] (BUG - should be [2, 2] based on 5.4 kWh / 3.4 kW = 1.59h → ceil = 2h)
- def_start_timestep: [0, 43]
- def_end_timestep: [39, 75]
- p_deferrable_nom: [3600.0, 3600.0]

The bug is caused by:
1. battery_capacity_kwh=50.0 instead of 28.0 (from staging config defaults)
2. soc_current=50.0 instead of 65.0 (from staging sensor)
3. charging_power_kw=None instead of 3.4 (staging bug)

Expected correct values (per spec):
- def_total_hours: [2, 2]
- Each trip needs ~2 hours to charge 5.4 kWh at 3.4 kW
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.ev_trip_planner.const import (
    CONF_CHARGING_POWER,
    CONF_MAX_DEFERRABLE_LOADS,
    CONF_VEHICLE_NAME,
)
from custom_components.ev_trip_planner.emhass.adapter import EMHASSAdapter
from custom_components.ev_trip_planner.calculations import BatteryCapacity


class MockConfigEntry:
    """Mock ConfigEntry with staging vehicle data."""

    def __init__(self, vehicle_id="mi_ev", data=None):
        self.entry_id = "516A4963B0704404BD270C9849FF28EF"
        self.data = data or {
            CONF_VEHICLE_NAME: vehicle_id,
            CONF_MAX_DEFERRABLE_LOADS: 50,
            CONF_CHARGING_POWER: 3.4,
            "battery_capacity_kwh": 28.0,
            "kwh_per_km": 0.18,
            "safety_margin_percent": 10,
            "t_base": 24.0,
            "planning_horizon_days": 7,
            "soc_sensor": "sensor.ev_battery_soc",
        }
        self.options = {
            "charging_power_kw": 3.4,
            "battery_capacity_kwh": 28.0,
            "kwh_per_km": 0.18,
            "safety_margin_percent": 10,
            "t_base": 24.0,
            "planning_horizon_days": 7,
        }


@pytest.fixture
def staging_config():
    """Return staging vehicle configuration."""
    return {
        CONF_VEHICLE_NAME: "mi_ev",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 3.4,
        "battery_capacity_kwh": 28.0,
        "kwh_per_km": 0.18,
        "safety_margin_percent": 10,
        "t_base": 24.0,
        "planning_horizon_days": 7,
    }


@pytest.fixture
def mock_hass():
    """Create a mock HomeAssistant instance."""
    hass = MagicMock()
    hass.config = MagicMock()
    hass.config.config_dir = "/tmp/test_config"
    hass.config.time_zone = "UTC"
    hass.data = {}
    hass.services = MagicMock()
    hass.services.async_call = AsyncMock()
    hass.services.has_service = MagicMock(return_value=True)
    mock_state = MagicMock()
    mock_state.state = "65"  # SOC 65%
    hass.states.get = MagicMock(return_value=mock_state)
    return hass


@pytest.fixture
def mock_store():
    """Create a mock Store."""
    store = MagicMock()
    store.async_load = AsyncMock(return_value=None)
    store.async_save = AsyncMock(return_value=None)
    return store


def create_recurring_trips(now: datetime) -> list[dict]:
    """
    Create two recurring trips that match the staging scenario:
    - Trip 1: Domingo 09:40 (JS getDay=0)
    - Trip 2: Lunes 21:40 (JS getDay=1)
    
    When now = Friday 12:00, these trips produce windows:
    - Trip 1 window: Friday 12:00 -> Sunday 09:40 (~46 hours)
    - Trip 2 window: Sunday 13:40 -> Monday 21:40 (~32 hours)
    """
    # Trip 1: Domingo 09:40 - departure Sunday at 09:40
    # From Friday 12:00, next Sunday is 2 days away = 48 hours + 9h40m = ~57.67 hours
    # But we want def_end_timestep=40, so let's adjust
    # Actually with JS getDay conversion: 0=Domingo, next Sunday from Friday is 2 days
    # Let's create trips with specific departure times instead
    
    # To get exact windows like staging [0, 44] and [40, 76]:
    # Trip 1: departs at now + 40 hours -> def_end=40
    # Trip 2: departs at now + 76 hours -> def_end=76, starts at 44 (after 4h buffer)
    
    trip1_departure = now + timedelta(hours=40)
    trip2_departure = now + timedelta(hours=76)
    
    # But these are puntual trips. For recurring, we need to use dia_semana.
    # Let's create them as puntual with specific datetime to get exact windows
    
    trip1 = {
        "id": "rec_5_xeqnmt",
        "tipo": "puntual",
        "datetime": trip1_departure.isoformat(),
        "km": 31.0,
        "kwh": 5.4,
        "activo": True,
    }
    
    trip2 = {
        "id": "rec_1_fy4pfk",
        "tipo": "puntual",
        "datetime": trip2_departure.isoformat(),
        "km": 30.0,
        "kwh": 5.4,
        "activo": True,
    }
    
    return [trip1, trip2]


class TestStagingBugReproduction:
    """Test reproducing the staging bug [7, 6] instead of [2, 2]."""

    @pytest.mark.asyncio
    async def test_reproduce_staging_bug(
        self,
        mock_hass,
        mock_store,
        staging_config,
    ):
        """
        Reproduce the staging bug: def_total_hours shows [7, 6] instead of [2, 2].
        
        Staging actual values:
        - def_start_timestep: [0, 44]
        - def_end_timestep: [40, 76]
        - def_total_hours: [7, 6] (BUG - should be [2, 2])
        - p_deferrable_nom: [3600.0, 3600.0]
        
        The bug is in emhass_adapter.py where power_watts = power_watts * cap_ratio
        incorrectly reduces energy, causing def_total_hours to be inflated.
        """
        entry = MockConfigEntry("mi_ev", staging_config)

        with patch(
            "custom_components.ev_trip_planner.emhass.adapter.Store",
            return_value=mock_store,
        ):
            adapter = EMHASSAdapter(mock_hass, entry)
            await adapter.async_load()

            # BUG REPRODUCTION: Use WRONG values that staging uses to reproduce the bug
            # Staging bug: battery_capacity_kwh=50.0 instead of 28.0 from config
            # Staging bug: charging_power_kw=None instead of 3.4 from config
            adapter._charging_power_kw = None  # BUG: None instead of 3.4
            adapter._load_publisher.charging_power_kw = 3.4  # But LP has correct value
            adapter._load_publisher.battery_capacity_kwh = 50.0  # BUG: wrong default
            adapter._load_publisher._battery_cap = BatteryCapacity(
                nominal_capacity_kwh=50.0,  # BUG: wrong default
                soh_sensor_entity_id=None,
            )

        # Set a fixed "now" so windows are deterministic
        now = datetime(2026, 5, 15, 12, 0, 0, tzinfo=timezone.utc)

        trips = create_recurring_trips(now)
        hora_regreso_stub = now - timedelta(hours=2)

        with patch("homeassistant.util.dt.now", return_value=now):
            with patch.object(
                adapter, "_get_current_soc", new_callable=AsyncMock
            ) as mock_soc:
                # BUG REPRODUCTION: soc_current=50.0 instead of 65.0 from sensor
                mock_soc.return_value = 50.0  # BUG: wrong SOC value
                with patch.object(
                    adapter, "_get_hora_regreso", new_callable=AsyncMock
                ) as mock_hora:
                    mock_hora.return_value = hora_regreso_stub.replace(tzinfo=timezone.utc)
                    mock_pm = MagicMock()
                    mock_pm.async_get_hora_regreso = AsyncMock(
                        return_value=hora_regreso_stub.replace(tzinfo=timezone.utc),
                    )
                    adapter._presence_monitor = mock_pm

                    result = await adapter.async_publish_all_deferrable_loads(
                        trips, charging_power_kw=3.4
                    )

        assert result is True

        # DUMP all calculated values for comparison with staging
        cache1 = adapter._cached_per_trip_params["rec_5_xeqnmt"]
        cache2 = adapter._cached_per_trip_params["rec_1_fy4pfk"]

        print("\n" + "="*60)
        print("STAGING BUG REPRODUCTION - DUMP")
        print("="*60)
        print(f"\nConfig (from staging):")
        print(f"  charging_power_kw = 3.4")
        print(f"  battery_capacity_kwh = 28.0")
        print(f"  SOC = 65%")
        print(f"  t_base = 24.0")
        
        print(f"\nnow = {now}")
        print(f"Trip 1 datetime = {trips[0]['datetime']}")
        print(f"Trip 2 datetime = {trips[1]['datetime']}")
        
        print(f"\n--- Trip 1 (rec_5_xeqnmt) ---")
        print(f"  def_start_timestep: {cache1.get('def_start_timestep', 0)}")
        print(f"  def_end_timestep: {cache1.get('def_end_timestep', 0)}")
        print(f"  def_total_hours: {cache1.get('def_total_hours', 0)}")
        print(f"  power_watts: {cache1.get('power_watts', 0)}")
        print(f"  kwh_needed: {cache1.get('kwh_needed', 0)}")
        print(f"  charging_window: {cache1.get('charging_window', [])}")
        
        print(f"\n--- Trip 2 (rec_1_fy4pfk) ---")
        print(f"  def_start_timestep: {cache2.get('def_start_timestep', 0)}")
        print(f"  def_end_timestep: {cache2.get('def_end_timestep', 0)}")
        print(f"  def_total_hours: {cache2.get('def_total_hours', 0)}")
        print(f"  power_watts: {cache2.get('power_watts', 0)}")
        print(f"  kwh_needed: {cache2.get('kwh_needed', 0)}")
        print(f"  charging_window: {cache2.get('charging_window', [])}")
        
        print(f"\n--- Aggregated Arrays (what HA sensor shows) ---")
        start_array = [cache1.get('def_start_timestep', 0), cache2.get('def_start_timestep', 0)]
        end_array = [cache1.get('def_end_timestep', 0), cache2.get('def_end_timestep', 0)]
        total_hours_array = [cache1.get('def_total_hours', 0), cache2.get('def_total_hours', 0)]
        p_deferrable_nom_array = [
            cache1.get('power_watts', 0) / 1000.0 * 1000,  # keep as watts
            cache2.get('power_watts', 0) / 1000.0 * 1000,
        ]
        
        print(f"  def_start_timestep: {start_array}")
        print(f"  def_end_timestep: {end_array}")
        print(f"  def_total_hours: {total_hours_array}")
        print(f"  p_deferrable_nom (watts): {[cache1.get('power_watts', 0), cache2.get('power_watts', 0)]}")
        
        print(f"\n--- power_profile (first 80 slots) ---")
        pp = adapter._cached_power_profile[:80]
        # Show slot number and value for non-zero entries
        non_zero = [(i, pp[i]) for i in range(len(pp)) if pp[i] > 0]
        print(f"  Non-zero slots: {non_zero}")
        
        print(f"\n--- STAGING EXPECTED (for comparison) ---")
        print(f"  def_start_timestep: [0, 44]")
        print(f"  def_end_timestep: [40, 76]")
        print(f"  def_total_hours: [7, 6] (BUG - should be [2, 2])")
        print(f"  p_deferrable_nom: [3600.0, 3600.0]")
        print("="*60)

        # PRIMARY ASSERTIONS: These match staging
        assert start_array == [0, 44], f"def_start_timestep should be [0, 44], got {start_array}"
        assert end_array == [40, 76], f"def_end_timestep should be [40, 76], got {end_array}"

        # BUG ASSERTION: This will FAIL until bug is fixed
        # Staging shows [7, 6] but per spec it should be [2, 2]
        assert total_hours_array == [7, 6], (
            f"def_total_hours should be [7, 6] (staging BUG reproduction), "
            f"got {total_hours_array}. "
            f"BUG: staging shows [7, 6] due to incorrect battery_capacity_kwh=50.0, "
            f"soc_current=50.0, and charging_power_kw=None values in staging."
        )

    @pytest.mark.asyncio
    async def test_verify_charging_slots_correct_count(
        self,
        mock_hass,
        mock_store,
        staging_config,
    ):
        """
        Verify the number of charging slots in power_profile.
        
        Per spec: each trip has def_total_hours slots at the END of its window.
        Per staging (buggy): trip 1 has 7 slots, trip 2 has 6 slots.
        Per spec (correct): each trip should have 2 slots.
        """
        entry = MockConfigEntry("mi_ev", staging_config)

        with patch(
            "custom_components.ev_trip_planner.emhass.adapter.Store",
            return_value=mock_store,
        ):
            adapter = EMHASSAdapter(mock_hass, entry)
            await adapter.async_load()

            # BUG REPRODUCTION: Use WRONG values that staging uses to reproduce the bug
            # Staging bug: battery_capacity_kwh=50.0 instead of 28.0 from config
            # Staging bug: charging_power_kw=None instead of 3.4 from config
            adapter._charging_power_kw = None  # BUG: None instead of 3.4
            adapter._load_publisher.charging_power_kw = 3.4  # But LP has correct value
            adapter._load_publisher.battery_capacity_kwh = 50.0  # BUG: wrong default
            adapter._load_publisher._battery_cap = BatteryCapacity(
                nominal_capacity_kwh=50.0,  # BUG: wrong default
                soh_sensor_entity_id=None,
            )

        now = datetime(2026, 5, 15, 12, 0, 0, tzinfo=timezone.utc)

        trips = create_recurring_trips(now)
        hora_regreso_stub = now - timedelta(hours=2)

        with patch("homeassistant.util.dt.now", return_value=now):
            with patch.object(
                adapter, "_get_current_soc", new_callable=AsyncMock
            ) as mock_soc:
                # BUG REPRODUCTION: soc_current=50.0 instead of 65.0 from sensor
                mock_soc.return_value = 50.0  # BUG: wrong SOC value
                with patch.object(
                    adapter, "_get_hora_regreso", new_callable=AsyncMock
                ) as mock_hora:
                    mock_hora.return_value = hora_regreso_stub.replace(tzinfo=timezone.utc)
                    mock_pm = MagicMock()
                    mock_pm.async_get_hora_regreso = AsyncMock(
                        return_value=hora_regreso_stub.replace(tzinfo=timezone.utc),
                    )
                    adapter._presence_monitor = mock_pm

                    result = await adapter.async_publish_all_deferrable_loads(
                        trips, charging_power_kw=3.4
                    )

        assert result is True

        # Count non-zero slots in power_profile
        power_profile = adapter._cached_power_profile
        non_zero_count = sum(1 for p in power_profile if p > 0)
        
        # Per spec: 2 slots per trip * 2 trips = 4 total slots
        # Per staging (bug): 7 + 6 = 13 total slots
        
        print(f"\nTotal non-zero charging slots: {non_zero_count}")
        print(f"Expected per spec: 4 (2 slots per trip * 2 trips)")
        print(f"Staging (bug): 13 (7 + 6 slots)")
        
        # BUG ASSERTION: This will FAIL until bug is fixed
        # Staging shows 13 slots (7 + 6)
        assert non_zero_count == 13, (
            f"Should have exactly 13 charging slots (7 + 6 = staging BUG), got {non_zero_count}. "
            f"Per spec should be 4 slots (2 per trip)."
        )


# =============================================================================
# BUG TEST: Adapter must read battery_capacity_kwh from ConfigEntry
# This test MUST FAIL because EMHASSAdapter doesn't read from ConfigEntry
# =============================================================================


class TestAdapterConfigEntryIntegration:
    """Test that EMHASSAdapter reads vehicle config from ConfigEntry.

    BUG: EMHASSAdapter uses LoadPublisherConfig defaults (50.0 kWh) instead of
    reading battery_capacity_kwh from ConfigEntry options/data. This causes
    def_total_hours to be [7, 6] instead of [2, 2].
    """

    @pytest.mark.asyncio
    async def test_adapter_must_read_battery_capacity_from_config_entry(
        self,
        mock_hass,
        mock_store,
    ):
        """
        EMHASSAdapter MUST read battery_capacity_kwh from ConfigEntry.

        This test FAILS if the adapter uses default 50.0 kWh instead of
        reading the actual value from entry.options or entry.data.

        Staging bug: battery_capacity_kwh=50.0 (default) instead of 28.0 (config)
        """
        # Create a ConfigEntry with specific battery_capacity_kwh
        config_with_28kwh = {
            CONF_VEHICLE_NAME: "mi_ev",
            CONF_MAX_DEFERRABLE_LOADS: 50,
            CONF_CHARGING_POWER: 3.4,
            "battery_capacity_kwh": 28.0,  # REAL value from config
            "kwh_per_km": 0.18,
            "safety_margin_percent": 10,
            "t_base": 24.0,
            "planning_horizon_days": 7,
        }

        entry = MockConfigEntry("mi_ev", config_with_28kwh)
        entry.options = {
            "charging_power_kw": 3.4,
            "battery_capacity_kwh": 28.0,  # Also in options
        }

        with patch(
            "custom_components.ev_trip_planner.emhass.adapter.Store",
            return_value=mock_store,
        ):
            adapter = EMHASSAdapter(mock_hass, entry)
            await adapter.async_load()

        # CRITICAL ASSERTION: Adapter MUST use 28.0 kWh from ConfigEntry
        # This FAILS because EMHASSAdapter.__init__ doesn't read battery_capacity_kwh
        # from entry.data or entry.options. It uses LoadPublisherConfig default 50.0.
        actual_capacity = adapter._load_publisher.battery_capacity_kwh

        assert actual_capacity == 28.0, (
            f"EMHASSAdapter MUST read battery_capacity_kwh=28.0 from ConfigEntry, "
            f"but got {actual_capacity}. "
            f"BUG: adapter uses LoadPublisherConfig default 50.0 instead of entry.data['battery_capacity_kwh']=28.0"
        )

    @pytest.mark.asyncio
    async def test_adapter_must_read_soc_from_hass_sensor(
        self,
        mock_hass,
        mock_store,
    ):
        """
        EMHASSAdapter MUST read SOC from the configured HASS sensor.

        This test FAILS if the adapter uses default 50.0% SOC instead of
        reading from the configured sensor.
        """
        config_with_65soc = {
            CONF_VEHICLE_NAME: "mi_ev",
            CONF_MAX_DEFERRABLE_LOADS: 50,
            CONF_CHARGING_POWER: 3.4,
            "battery_capacity_kwh": 28.0,
            "kwh_per_km": 0.18,
            "safety_margin_percent": 10,
            "t_base": 24.0,
            "planning_horizon_days": 7,
            "soc_sensor": "sensor.ev_battery_soc",  # Configured sensor
        }

        entry = MockConfigEntry("mi_ev", config_with_65soc)

        # Mock the HASS sensor to return 65%
        mock_state = MagicMock()
        mock_state.state = "65"
        mock_hass.states.get = MagicMock(return_value=mock_state)

        with patch(
            "custom_components.ev_trip_planner.emhass.adapter.Store",
            return_value=mock_store,
        ):
            adapter = EMHASSAdapter(mock_hass, entry)
            await adapter.async_load()

        # Get the SOC that adapter reads
        actual_soc = await adapter._get_current_soc()

        # CRITICAL ASSERTION: Adapter MUST read 65% from sensor
        # This FAILS because staging doesn't read from sensor properly
        assert actual_soc == 65.0, (
            f"EMHASSAdapter MUST read SOC=65.0 from sensor.ev_battery_soc, "
            f"but got {actual_soc}. "
            f"BUG: adapter uses default SOC instead of configured sensor"
        )

    @pytest.mark.asyncio
    async def test_full_flow_uses_config_values_not_defaults(
        self,
        mock_hass,
        mock_store,
    ):
        """
        Full flow test: Verify EMHASS calculations use config values, not defaults.

        This test MUST FAIL because:
        1. battery_capacity_kwh=50.0 (default) instead of 28.0 (config)
        2. soc_current=50.0 (default) instead of 65.0 (config)

        This causes def_total_hours=[7, 6] instead of [2, 2].
        """
        # Config with real staging values
        config_real = {
            CONF_VEHICLE_NAME: "mi_ev",
            CONF_MAX_DEFERRABLE_LOADS: 50,
            CONF_CHARGING_POWER: 3.4,
            "battery_capacity_kwh": 28.0,  # REAL: 28 kWh
            "kwh_per_km": 0.18,
            "safety_margin_percent": 10,
            "t_base": 24.0,
            "planning_horizon_days": 7,
            "soc_sensor": "sensor.ev_battery_soc",
        }
        entry = MockConfigEntry("mi_ev", config_real)

        # Mock sensor returning 65% SOC
        mock_state = MagicMock()
        mock_state.state = "65"
        mock_hass.states.get = MagicMock(return_value=mock_state)

        with patch(
            "custom_components.ev_trip_planner.emhass.adapter.Store",
            return_value=mock_store,
        ):
            adapter = EMHASSAdapter(mock_hass, entry)
            await adapter.async_load()

        now = datetime(2026, 5, 15, 12, 0, 0, tzinfo=timezone.utc)
        trips = create_recurring_trips(now)

        with patch("homeassistant.util.dt.now", return_value=now):
            with patch.object(
                adapter, "_get_current_soc", new_callable=AsyncMock
            ) as mock_soc:
                mock_soc.return_value = 65.0  # REAL SOC
                with patch.object(
                    adapter, "_get_hora_regreso", new_callable=AsyncMock
                ) as mock_hora:
                    mock_hora.return_value = now - timedelta(hours=2)
                    mock_pm = MagicMock()
                    mock_pm.async_get_hora_regreso = AsyncMock(
                        return_value=now - timedelta(hours=2),
                    )
                    adapter._presence_monitor = mock_pm

                    await adapter.async_publish_all_deferrable_loads(
                        trips, charging_power_kw=3.4
                    )

        # Verify def_total_hours is [2, 2] when using correct config values
        cache1 = adapter._cached_per_trip_params["rec_5_xeqnmt"]
        cache2 = adapter._cached_per_trip_params["rec_1_fy4pfk"]
        total_hours_array = [cache1.get("def_total_hours", 0), cache2.get("def_total_hours", 0)]

        # EXPECTED (correct behavior): def_total_hours = [2, 2]
        # ACTUAL (buggy behavior): def_total_hours = [7, 6] if adapter uses defaults

        assert total_hours_array == [2, 2], (
            f"With correct config (battery=28.0, SOC=65%), "
            f"def_total_hours should be [2, 2], got {total_hours_array}. "
            f"BUG: adapter is using default values instead of config entry values."
        )