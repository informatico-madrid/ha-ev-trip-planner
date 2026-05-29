"""Tests for EMHASSAdapter facade in emhass.adapter."""

from unittest.mock import MagicMock

import pytest

from custom_components.ev_trip_planner.emhass.adapter import (
    EMHASSAdapter,
)
from custom_components.ev_trip_planner.emhass.error_handler import (
    ErrorHandler,
)
from custom_components.ev_trip_planner.emhass.index_manager import (
    IndexManager,
)


@pytest.fixture
def mock_hass():
    """Minimal MagicMock HomeAssistant."""
    hass = MagicMock()
    return hass


@pytest.fixture
def mock_entry():
    """Minimal MagicMock ConfigEntry with required fields."""
    entry = MagicMock()
    entry.entry_id = "test_vehicle"
    entry.data = {
        "charging_power_kw": 3.6,
        "battery_capacity_kwh": 50.0,
        "safety_margin_percent": 10.0,
    }
    entry.options = {}
    return entry


class TestEMHASSAdapterFacade:
    """Test that EMHASSAdapter in emhass.adapter delegates to sub-components."""

    def test_emhass_adapter_is_facade_with_subcomponents(self, mock_hass, mock_entry):
        """EMHASSAdapter in emhass.adapter is a facade with composed sub-components."""
        adapter = EMHASSAdapter(hass=mock_hass, entry=mock_entry)

        # Facade exposes composed sub-components
        assert hasattr(adapter, "_error_handler")
        assert hasattr(adapter, "_index_manager")
        assert hasattr(adapter, "_load_publisher")

        # Facade exposes vehicle_id attribute
        assert hasattr(adapter, "vehicle_id")
        assert adapter.vehicle_id == "test_vehicle"

        # Facade exposes state attributes
        assert hasattr(adapter, "_published_trips")
        assert hasattr(adapter, "_cached_per_trip_params")
        assert hasattr(adapter, "_cached_power_profile")
        assert hasattr(adapter, "_cached_deferrables_schedule")
        assert hasattr(adapter, "_config_entry_listener")

    def test_emhass_adapter_has_error_handler_attribute(self, mock_hass, mock_entry):
        """EMHASSAdapter instances have an ErrorHandler."""
        adapter = EMHASSAdapter(hass=mock_hass, entry=mock_entry)
        assert hasattr(adapter, "_error_handler")
        assert isinstance(adapter._error_handler, ErrorHandler)

    def test_emhass_adapter_has_index_manager_attribute(self, mock_hass, mock_entry):
        """EMHASSAdapter instances have an IndexManager."""
        adapter = EMHASSAdapter(hass=mock_hass, entry=mock_entry)
        assert hasattr(adapter, "_index_manager")
        assert isinstance(adapter._index_manager, IndexManager)
