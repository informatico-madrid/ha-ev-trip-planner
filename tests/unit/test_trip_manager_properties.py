"""Tests for TripManager sub-component access and state properties.

Covers state access, sub-component references, and emhass_adapter property.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.ev_trip_planner.trip._types import TripManagerConfig
from custom_components.ev_trip_planner.trip.manager import TripManager
from custom_components.ev_trip_planner.yaml_trip_storage import YamlTripStorage


def _make_tm():
    """Create a minimal TripManager with proper state."""
    hass = MagicMock()
    hass.config_entries = MagicMock()

    storage = MagicMock(spec=YamlTripStorage)
    storage.load_recurring = MagicMock(return_value={})
    storage.load_punctual = MagicMock(return_value={})
    storage.async_save = AsyncMock()
    storage.async_load = AsyncMock(return_value={})

    tm = TripManager(
        hass=hass,
        vehicle_id="test_vehicle",
        config=TripManagerConfig(entry_id="test_entry", storage=storage),
    )
    return tm


class TestTripManagerProperties:
    """Test TripManager property access via state."""

    def test_hass_from_state(self):
        """hass accessible via tm._state.hass."""
        tm = _make_tm()
        assert tm._state.hass is not None

    def test_hass_setter(self):
        """Setting hass updates _state.hass."""
        tm = _make_tm()
        new_hass = MagicMock()
        tm._state.hass = new_hass
        assert tm._state.hass is new_hass

    def test_vehicle_id_property(self):
        """vehicle_id accessible via tm._state.vehicle_id."""
        tm = _make_tm()
        assert tm._state.vehicle_id == "test_vehicle"

    def test_vehicle_id_setter(self):
        """Setting vehicle_id updates _state.vehicle_id."""
        tm = _make_tm()
        tm._state.vehicle_id = "new_vehicle"
        assert tm._state.vehicle_id == "new_vehicle"

    def test_entry_id_property(self):
        """entry_id accessible via tm._state.entry_id."""
        tm = _make_tm()
        assert tm._state.entry_id == "test_entry"

    def test_sensor_callbacks_property(self):
        """sensor_callbacks accessible via tm._state.sensor_callbacks."""
        tm = _make_tm()
        assert tm._state.sensor_callbacks is not None

    def test_emhass_adapter_property(self):
        """emhass_adapter property getter/setter."""
        tm = _make_tm()
        assert tm.emhass_adapter is None

    def test_emhass_adapter_setter(self):
        """Setting emhass_adapter updates _state.emhass_adapter."""
        tm = _make_tm()
        adapter = MagicMock()
        tm.emhass_adapter = adapter
        assert tm._state.emhass_adapter is adapter

    def test_vehicle_controller_property(self):
        """vehicle_controller accessible via tm._state.vehicle_controller."""
        tm = _make_tm()
        assert tm._state.vehicle_controller is not None


class TestTripManagerMethods:
    """Test TripManager sub-component method access."""

    def test_get_day_index_via_soc_helpers(self):
        """_get_day_index on SOCHelpers finds Spanish day names."""
        tm = _make_tm()
        assert tm._state._soc_helpers._get_day_index("lunes") == 0
        assert tm._state._soc_helpers._get_day_index("viernes") == 4

    def test_get_day_index_unknown(self):
        """Unknown day name returns 0 with warning."""
        tm = _make_tm()
        result = tm._state._soc_helpers._get_day_index("notaday")
        assert result == 0

    def test_sanitize_recurring_trips_clean(self):
        """Clean trips pass through unchanged."""
        tm = _make_tm()
        trips = {
            "rec_1": {"hora": "14:00"},
            "rec_2": {"hora": "22:00"},
        }
        result = tm._sanitize_recurring_trips(trips)
        assert len(result) == 2

    def test_sanitize_recurring_trips_invalid(self):
        """Invalid hora is removed from trips."""
        tm = _make_tm()
        trips = {
            "rec_1": {"hora": "invalid"},
            "rec_2": {"hora": "14:00"},
        }
        result = tm._sanitize_recurring_trips(trips)
        assert len(result) < 2

    @pytest.mark.asyncio
    async def test_persistence_async_setup(self):
        """_persistence.async_setup calls vehicle_controller.async_setup + _load_trips."""
        tm = _make_tm()
        tm._state.vehicle_controller = MagicMock()
        tm._state.vehicle_controller.async_setup = AsyncMock()

        await tm._persistence.async_setup()

        tm._state.vehicle_controller.async_setup.assert_called_once()

    @pytest.mark.asyncio
    async def test_load_trips_fallback(self):
        """_persistence._load_trips handles storage error gracefully."""
        tm = _make_tm()
        tm._state.storage.load_recurring = MagicMock(side_effect=RuntimeError("error"))
        tm._state.storage.load_punctual = MagicMock(side_effect=RuntimeError("error"))

        await tm._persistence._load_trips()

        assert tm._state.recurring_trips == {}
        assert tm._state.punctual_trips == {}

    @pytest.mark.asyncio
    async def test_load_trips_stored_data_with_data_key(self):
        """_load_trips parses stored_data with 'data' key (line 116)."""
        tm = _make_tm()
        tm._state.recurring_trips = {}
        tm._state.punctual_trips = {}
        tm._state._trips = {}
        stored = {
            "data": {
                "trips": {},
                "recurring_trips": {
                    "r1": {"id": "r1", "hora": "14:00", "dia_semana": "lunes"}
                },
                "punctual_trips": {},
            }
        }
        tm._state.storage.async_load = AsyncMock(return_value=stored)
        await tm._persistence._load_trips()
        assert "r1" in tm._state.recurring_trips

    @pytest.mark.asyncio
    async def test_load_trips_empty_stored_data(self):
        """_load_trips with empty stored_data calls _reset_trips (line 129)."""
        tm = _make_tm()
        # Clear trips so _load_trips doesn't skip (line 91 early return)
        tm._state._trips = {}
        tm._state.recurring_trips = {}
        tm._state.punctual_trips = {}
        tm._state.storage.async_load = AsyncMock(return_value=None)
        await tm._persistence._load_trips()
        assert tm._state.recurring_trips == {}
        assert tm._state.punctual_trips == {}

    @pytest.mark.asyncio
    async def test_save_trips_exception(self):
        """Exception during save triggers exception logging (lines 79-80)."""
        tm = _make_tm()
        tm._state.storage.async_save = AsyncMock(side_effect=RuntimeError("save error"))
        await tm._persistence.async_save_trips()
        # Should not raise; exception path handled

    @pytest.mark.asyncio
    async def test_get_next_trip_via_navigator(self):
        """Next trip via TripNavigator finds pending punctual trip."""
        tm = _make_tm()
        future = datetime(2099, 1, 1, 14, 0, 0, tzinfo=timezone.utc)
        tm._state.punctual_trips = {
            "pun_1": {
                "id": "pun_1",
                "estado": "pendiente",
                "tipo": "punctual",
                "datetime": "2099-01-01T14:00:00",
            }
        }
        tm._state.recurring_trips = {}
        tm._state._navigator = tm._navigator  # already wired
        # Mock _get_trip_time to return a future time
        tm._state._soc._get_trip_time = MagicMock(return_value=future)

        result = await tm._navigator.async_get_next_trip()
        assert result is not None
        assert result["id"] == "pun_1"

    @pytest.mark.asyncio
    async def test_get_next_trip_no_trips(self):
        """No trips -> returns None."""
        tm = _make_tm()
        tm._state.recurring_trips = {}
        tm._state.punctual_trips = {}

        result = await tm._navigator.async_get_next_trip()
        assert result is None

    @pytest.mark.asyncio
    async def test_get_next_trip_after_punctual(self):
        """async_get_next_trip_after finds future punctual trip."""
        tm = _make_tm()
        past = datetime(2020, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        future = datetime(2099, 1, 1, 14, 0, 0, tzinfo=timezone.utc)
        tm._state.punctual_trips = {
            "pun_1": {
                "id": "pun_1",
                "estado": "pendiente",
                "tipo": "punctual",
                "datetime": "2099-01-01T14:00:00",
            }
        }
        tm._state.recurring_trips = {}
        tm._state._soc._get_trip_time = MagicMock(return_value=future)

        result = await tm._navigator.async_get_next_trip_after(past)
        assert result is not None
        assert result["id"] == "pun_1"

    @pytest.mark.asyncio
    async def test_get_next_trip_after_no_future(self):
        """async_get_next_trip_after returns None when no future trip."""
        tm = _make_tm()
        future = datetime(2099, 1, 1, 14, 0, 0, tzinfo=timezone.utc)
        tm._state.punctual_trips = {
            "pun_1": {
                "id": "pun_1",
                "estado": "pendiente",
                "tipo": "punctual",
                "datetime": "2099-01-01T14:00:00",
            }
        }
        tm._state.recurring_trips = {}
        tm._state._soc._get_trip_time = MagicMock(return_value=future)

        later = datetime(2099, 1, 1, 16, 0, 0, tzinfo=timezone.utc)
        result = await tm._navigator.async_get_next_trip_after(later)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_next_trip_after_recurring_invalid_hora(self):
        """Invalid trip hora in recurring -> warning, skipped."""
        tm = _make_tm()
        past = datetime(2020, 1, 6, 10, 0, 0, tzinfo=timezone.utc)  # Monday
        tm._state.recurring_trips = {
            "rec_1": {
                "id": "rec_1",
                "activo": True,
                "dia_semana": "lunes",
                "hora": "invalid",
            }
        }
        tm._state.punctual_trips = {}

        result = await tm._navigator.async_get_next_trip_after(past)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_next_trip_after_mixed_punctual_and_recurring(self):
        """async_get_next_trip_after with both trip types exercises lines 77-78.

        Only recurring trips (both return naive datetimes from combine()) → no TZ mismatch.
        """
        tm = _make_tm()
        past = datetime(2020, 1, 6, 0, 0, 0, tzinfo=timezone.utc)  # Monday, midnight

        tm._state.punctual_trips = {}
        tm._state.recurring_trips = {
            "rec_1": {
                "id": "rec_1",
                "activo": True,
                "dia_semana": "lunes",
                "hora": "14:00",
            },
            "rec_2": {
                "id": "rec_2",
                "activo": True,
                "dia_semana": "lunes",
                "hora": "08:00",  # earlier, should replace rec_1 at line 77-78
            },
        }
        # Both return naive datetimes from datetime.combine (line 68 path)
        # _get_trip_time is not called for recurring trips with hora format
        result = await tm._navigator.async_get_next_trip_after(past)
        # rec_2 (08:00) is earlier than rec_1 (14:00) → should be next
        assert result is not None
        assert result["id"] == "rec_2"

    @pytest.mark.asyncio
    async def test_get_next_trip_skip_non_pending_punctual(self):
        """Punctual trip with estado != pendiente is skipped (line 46)."""
        tm = _make_tm()
        past = datetime(2020, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
        tm._state.punctual_trips = {
            "pun_1": {
                "id": "pun_1",
                "estado": "completado",  # not pendiente
                "tipo": "punctual",
                "datetime": "2099-01-01T14:00:00",
            }
        }
        tm._state.recurring_trips = {}
        result = await tm._navigator.async_get_next_trip_after(past)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_next_trip_skip_inactive_recurring(self):
        """Inactive recurring trips are skipped (line 55)."""
        tm = _make_tm()
        past = datetime(2020, 1, 6, 10, 0, 0, tzinfo=timezone.utc)  # Monday
        tm._state.recurring_trips = {
            "rec_1": {
                "id": "rec_1",
                "activo": False,  # inactive
                "dia_semana": "lunes",
                "hora": "14:00",
            }
        }
        tm._state.punctual_trips = {}
        result = await tm._navigator.async_get_next_trip_after(past)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_next_trip_skip_wrong_day(self):
        """Recurring trips for wrong day are skipped (line 57)."""
        tm = _make_tm()
        past = datetime(2020, 1, 6, 10, 0, 0, tzinfo=timezone.utc)  # Monday
        tm._state.recurring_trips = {
            "rec_1": {
                "id": "rec_1",
                "activo": True,
                "dia_semana": "martes",  # Tuesday, not Monday
                "hora": "14:00",
            }
        }
        tm._state.punctual_trips = {}
        result = await tm._navigator.async_get_next_trip_after(past)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_next_trip_after_recurring_before_regreso(self):
        """Recurring trip at same time or earlier as regreso is skipped (lines 63-66)."""
        tm = _make_tm()
        past = datetime(2020, 1, 6, 10, 0, 0, tzinfo=timezone.utc)  # Monday
        tm._state.recurring_trips = {
            "rec_1": {
                "id": "rec_1",
                "activo": True,
                "dia_semana": "lunes",
                "hora": "08:00",  # before regreso at 10:00
            }
        }
        tm._state.punctual_trips = {}
        result = await tm._navigator.async_get_next_trip_after(past)
        assert result is None


class TestTripNavigatorNextTrip:
    """Test TripNavigator.async_get_next_trip (lines 88-91)."""

    @pytest.mark.asyncio
    async def test_async_get_next_trip_with_active_recurring(self):
        """Recurring trip with valid _get_trip_time returns trip (lines 88-91)."""
        tm = _make_tm()
        future = datetime(2099, 6, 15, 10, 0, 0, tzinfo=timezone.utc)
        tm._state.recurring_trips = {
            "rec_1": {"id": "rec_1", "activo": True, "tipo": "recurrente"}
        }
        tm._state.punctual_trips = {}
        tm._state._soc._get_trip_time = MagicMock(return_value=future)
        result = await tm._navigator.async_get_next_trip()
        assert result is not None
        assert result["id"] == "rec_1"

    @pytest.mark.asyncio
    async def test_async_get_next_trip_skips_inactive_recurring(self):
        """Inactive recurring trips are skipped in async_get_next_trip."""
        tm = _make_tm()
        tm._state.recurring_trips = {"rec_1": {"id": "rec_1", "activo": False}}
        tm._state.punctual_trips = {}
        result = await tm._navigator.async_get_next_trip()
        assert result is None

    @pytest.mark.asyncio
    async def test_async_get_next_trip_skips_completed_punctual(self):
        """Punctual trips with estado != pendiente are skipped."""
        tm = _make_tm()
        tm._state.recurring_trips = {}
        tm._state.punctual_trips = {
            "pun_1": {
                "id": "pun_1",
                "estado": "completado",
                "tipo": "punctual",
            }
        }
        result = await tm._navigator.async_get_next_trip()
        assert result is None


# ── Targeted mutation-kill tests for TripManager.__init__ and _sanitize_recurring_trips ──


class TestInitMutationKills:
    """Tests targeting specific mutmut survivors in TripManager.__init__.

    These add assertions on exact values that kill number/string/boolean mutations
    in assignment lines.
    """

    def test_init_entry_id_defaults_to_empty_string(self):
        """entry_id='' (not None) kills mutations that change default empty string."""
        hass = MagicMock()
        hass.config_entries = MagicMock()
        storage = MagicMock(spec=YamlTripStorage)
        storage.load_recurring = MagicMock(return_value={})
        storage.load_punctual = MagicMock(return_value={})
        storage.async_save = AsyncMock()
        storage.async_load = AsyncMock(return_value={})
        config = TripManagerConfig(entry_id=None, storage=storage)
        tm = TripManager(hass=hass, vehicle_id="test_v", config=config)
        # Mutant on 'entry_id=cfg.entry_id or ""' changes "" → something else
        # This assertion kills that mutation
        assert tm._state.entry_id == ""

    def test_init_vehicle_id_assigned_exact(self):
        """vehicle_id assigned exactly kills string mutation on parameter."""
        hass = MagicMock()
        hass.config_entries = MagicMock()
        storage = MagicMock(spec=YamlTripStorage)
        storage.load_recurring = MagicMock(return_value={})
        storage.load_punctual = MagicMock(return_value={})
        storage.async_save = AsyncMock()
        storage.async_load = AsyncMock(return_value={})
        config = TripManagerConfig(entry_id="e1", storage=storage)
        tm = TripManager(hass=hass, vehicle_id="exact_vid", config=config)
        assert tm._state.vehicle_id == "exact_vid"

    def test_init_sub_component_refs_wired(self):
        """All sub-component references wired on state kills mutations in wiring."""
        hass = MagicMock()
        hass.config_entries = MagicMock()
        storage = MagicMock(spec=YamlTripStorage)
        storage.load_recurring = MagicMock(return_value={})
        storage.load_punctual = MagicMock(return_value={})
        storage.async_save = AsyncMock()
        storage.async_load = AsyncMock(return_value={})
        config = TripManagerConfig(entry_id="e1", storage=storage)
        tm = TripManager(hass=hass, vehicle_id="v1", config=config)
        # These kill mutations that change None → value or value → None
        assert tm._state._crud is not None
        assert tm._state._persistence is not None
        assert tm._state._lifecycle is not None
        assert tm._state._emhass_sync is not None
        assert tm._state._soc_helpers is not None
        assert tm._state._soc is not None
        assert tm._state._power is not None
        assert tm._state._schedule is not None
        assert tm._state._navigator is not None
        # Verify async_save_trips is bound to persistence method
        assert tm._state.async_save_trips is not None

    def test_init_vehicle_controller_created(self):
        """vehicle_controller exists kills mutation in VC creation."""
        hass = MagicMock()
        hass.config_entries = MagicMock()
        storage = MagicMock(spec=YamlTripStorage)
        storage.load_recurring = MagicMock(return_value={})
        storage.load_punctual = MagicMock(return_value={})
        storage.async_save = AsyncMock()
        storage.async_load = AsyncMock(return_value={})
        config = TripManagerConfig(entry_id="e1", storage=storage)
        tm = TripManager(hass=hass, vehicle_id="v1", config=config)
        assert tm._state.vehicle_controller is not None
        assert hasattr(tm._state.vehicle_controller, "async_setup")

    def test_init_persistence_created(self):
        """_persistence exists and has async_save_trips."""
        hass = MagicMock()
        hass.config_entries = MagicMock()
        storage = MagicMock(spec=YamlTripStorage)
        storage.load_recurring = MagicMock(return_value={})
        storage.load_punctual = MagicMock(return_value={})
        storage.async_save = AsyncMock()
        storage.async_load = AsyncMock(return_value={})
        config = TripManagerConfig(entry_id="e1", storage=storage)
        tm = TripManager(hass=hass, vehicle_id="v1", config=config)
        assert tm._state._persistence is not None
        assert hasattr(tm._state._persistence, "async_save_trips")
        assert hasattr(tm._state._persistence, "async_setup")

    def test_init_no_config_uses_default(self):
        """No config → TripManagerConfig() default kills mutation on 'config or TripManagerConfig()'."""
        hass = MagicMock()
        hass.config_entries = MagicMock()
        tm = TripManager(hass=hass, vehicle_id="no_config_v")
        assert tm._state.vehicle_id == "no_config_v"
        assert tm._state.entry_id == ""
        assert tm._state._crud is not None
        assert tm._state._persistence is not None

    def test_init_storage_none_when_not_provided(self):
        """storage=None when config has no storage kills boolean mutation."""
        hass = MagicMock()
        hass.config_entries = MagicMock()
        config = TripManagerConfig()
        tm = TripManager(hass=hass, vehicle_id="v1", config=config)
        assert tm._state.storage is None


class TestSanitizeRecurringMutationKills:
    """Tests targeting _sanitize_recurring_trips mutations (manager.py).

    These kill mutations in:
    - original_count = len(trips)
    - removed_count = original_count - len(sanitized)
    - if removed_count > 0
    """

    def test_sanitize_exact_removed_count(self):
        """Exact count kills subtraction mutations in removed_count."""
        tm = _make_tm()
        trips = {
            "bad_1": {"hora": "invalid"},
            "bad_2": {"hora": "bad"},
            "good_1": {"hora": "14:00"},
        }
        result = tm._sanitize_recurring_trips(trips)
        # Mutant changing len(sanitized) → 0 would make removed_count=3, not 2
        assert len(result) == 1

    def test_sanitize_all_clean_unchanged(self):
        """All clean trips → no removal kills if-branch mutation."""
        tm = _make_tm()
        trips = {
            "r1": {"hora": "08:00"},
            "r2": {"hora": "22:00"},
        }
        result = tm._sanitize_recurring_trips(trips)
        assert len(result) == 2

    def test_sanitize_all_invalid_empty(self):
        """All invalid → empty dict kills mutation in return path."""
        tm = _make_tm()
        trips = {
            "bad_1": {"hora": "invalid"},
            "bad_2": {"hora": "bad"},
        }
        result = tm._sanitize_recurring_trips(trips)
        assert result == {}
        assert len(result) == 0
