"""Test for post-restart persistence bug.

Bug description:
- After HA restart, trips disappear from frontend panel
- EMHASS sensor shows empty arrays []
- Individual trip sensors no longer exist in hass.states
- But trip data still exists in storage (not deleted)

Root cause: publish_deferrable_loads() is NOT called after _load_trips()
in async_setup(). When HA restarts, trips are loaded from storage but
the EMHASS adapter never gets updated.

This test verifies the bug at the integration level using real storage
with mock EMHASS adapter.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from homeassistant.core import HomeAssistant

from custom_components.ev_trip_planner.trip_manager import TripManager
from custom_components.ev_trip_planner.emhass_adapter import EMHASSAdapter


@pytest.fixture
def enable_custom_integrations():
    """Enable custom integrations for testing."""
    return True


class TestPostRestartPersistenceBug:
    """Test suite for the post-restart persistence bug.

    Bug: async_setup() loads trips from storage but does NOT call
    publish_deferrable_loads(), so EMHASS sensor never gets updated.
    """

    @pytest.mark.asyncio
    async def test_emhass_not_updated_after_setup_loads_from_storage(self, hass, mock_store):
        """Test that EMHASS adapter is NOT updated after async_setup loads trips from storage.

        This is the ROOT CAUSE of the post-restart bug:
        - async_setup() calls _load_trips() which loads from storage
        - But async_setup() NEVER calls publish_deferrable_loads()
        - So EMHASS sensor keeps showing empty arrays

        RED PHASE: This test should FAIL, proving the bug exists.
        GREEN PHASE: After fix (adding publish_deferrable_loads to async_setup),
        this test should PASS.
        """
        # Setup: Pre-populate storage with trips (simulating prior to restart)
        stored_trips = {
            "data": {
                "trips": {
                    "trip_1": {
                        "id": "pun_20260418_z9ryxq",
                        "trip_type": "puntual",
                        "datetime": "2026-04-18T10:00",
                        "km": 20.0,
                        "kwh": 5.0,
                        "descripcion": "Restart Test Trip 1",
                        "estado": "pendiente",
                    },
                    "trip_2": {
                        "id": "pun_20260419_62qe8m",
                        "trip_type": "puntual",
                        "datetime": "2026-04-19T14:00",
                        "km": 30.0,
                        "kwh": 7.0,
                        "descripcion": "Restart Test Trip 2",
                        "estado": "pendiente",
                    },
                },
                "recurring_trips": {},
                "punctual_trips": {
                    "trip_1": {
                        "id": "pun_20260418_z9ryxq",
                        "trip_type": "puntual",
                        "datetime": "2026-04-18T10:00",
                        "km": 20.0,
                        "kwh": 5.0,
                        "descripcion": "Restart Test Trip 1",
                        "estado": "pendiente",
                    },
                    "trip_2": {
                        "id": "pun_20260419_62qe8m",
                        "trip_type": "puntual",
                        "datetime": "2026-04-19T14:00",
                        "km": 30.0,
                        "kwh": 7.0,
                        "descripcion": "Restart Test Trip 2",
                        "estado": "pendiente",
                    },
                },
            }
        }
        mock_store._storage = stored_trips

        # Create TripManager with the mock store (DI pattern)
        trip_manager = TripManager(
            hass,
            "test_vehicle",
            "test_entry_id",
            None,  # presence_config
        )
        trip_manager._storage = mock_store

        # Create and attach EMHASS adapter
        with patch("custom_components.ev_trip_planner.emhass_adapter.Store", return_value=mock_store):
            emhass_adapter = EMHASSAdapter(hass, MagicMock(
                data={"vehicle_name": "test_vehicle"},
                entry_id="test_entry_id",
            ))
            await emhass_adapter.async_load()

        trip_manager.set_emhass_adapter(emhass_adapter)

        # Verify initial state: EMHASS _cached_per_trip_params should be empty
        assert len(emhass_adapter._cached_per_trip_params) == 0, "Initial: no cached trip params"

        # ACT: Call async_setup (simulates what happens on HA restart)
        await trip_manager.async_setup()

        # VERIFY: Trips are loaded from storage
        assert len(trip_manager._trips) == 2, "Trips should be loaded from storage"
        assert len(trip_manager._punctual_trips) == 2, "Punctual trips should be loaded"

        # VERIFY FIX: EMHASS adapter SHOULD have cached params after async_setup
        # This is what the EMHASS template reads to show data
        #
        # RED PHASE: This assertion FAILS (before fix), PASSES (after fix)
        assert len(emhass_adapter._cached_per_trip_params) == 2, \
            "BUG: EMHASS _cached_per_trip_params should have 2 trips after async_setup"

        # Verify the cached params have the expected structure (what EMHASS template uses)
        for trip_id in ["pun_20260418_z9ryxq", "pun_20260419_62qe8m"]:
            assert trip_id in emhass_adapter._cached_per_trip_params, \
                f"BUG: trip {trip_id} should be in _cached_per_trip_params"
            params = emhass_adapter._cached_per_trip_params[trip_id]
            assert "def_total_hours" in params, \
                f"BUG: trip {trip_id} should have def_total_hours in cached params"
            assert "P_deferrable_nom" in params, \
                f"BUG: trip {trip_id} should have P_deferrable_nom in cached params"


class TestIntegrationDeletionBug:
    """Test that integration deletion properly cleans up trips.

    Bug: When integration is deleted, trips are NOT deleted from storage,
    causing orphaned data in EMHASS template.
    """

    @pytest.mark.asyncio
    async def test_delete_all_trips_removes_from_storage(self, hass, mock_store):
        """Test that async_delete_all_trips properly removes trips from storage."""
        # Setup: Pre-populate storage with trips
        stored_trips = {
            "data": {
                "trips": {
                    "trip_1": {"id": "pun_20260418_z9ryxq", "trip_type": "puntual"},
                },
                "recurring_trips": {},
                "punctual_trips": {
                    "trip_1": {"id": "pun_20260418_z9ryxq", "trip_type": "puntual"},
                },
            }
        }
        mock_store._storage = stored_trips

        # Create TripManager with storage
        trip_manager = TripManager(
            hass,
            "test_vehicle",
            "test_entry_id",
            None,
        )
        trip_manager._storage = mock_store

        # Verify trips exist
        await trip_manager.async_setup()
        assert len(trip_manager._trips) == 1, "Trip should exist before deletion"

        # Act: Delete all trips
        await trip_manager.async_delete_all_trips()

        # Assert: Trips are removed
        assert len(trip_manager._trips) == 0, "Trips should be deleted"
        assert len(trip_manager._punctual_trips) == 0, "Punctual trips should be deleted"
        assert len(trip_manager._recurring_trips) == 0, "Recurring trips should be deleted"
