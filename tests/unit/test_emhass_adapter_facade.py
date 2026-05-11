"""Tests for EMHASSAdapter facade in emhass.adapter."""

import pytest  # noqa: F401


class TestEMHASSAdapterFacade:
    """Test that EMHASSAdapter in emhass.adapter delegates to sub-components."""

    def test_emhass_adapter_is_facade_not_reexport(self):
        """EMHASSAdapter in emhass.adapter is a facade class, not the original."""
        from custom_components.ev_trip_planner.emhass.adapter import (
            EMHASSAdapter as FacadeAdapter,
        )
        from custom_components.ev_trip_planner.emhass_adapter import (
            EMHASSAdapter as OriginalAdapter,
        )

        # The facade should be a distinct class, not the original
        assert FacadeAdapter is not OriginalAdapter

    def test_emhass_adapter_has_error_handler_attribute(self):
        """EMHASSAdapter instances have an ErrorHandler."""
        from unittest.mock import MagicMock

        from custom_components.ev_trip_planner.emhass.adapter import (
            EMHASSAdapter,
        )
        from custom_components.ev_trip_planner.emhass.error_handler import (
            ErrorHandler,
        )

        hass = MagicMock()
        entry = MagicMock()
        adapter = EMHASSAdapter(hass=hass, entry=entry)
        assert hasattr(adapter, "_error_handler")
        assert isinstance(adapter._error_handler, ErrorHandler)

    def test_emhass_adapter_has_index_manager_attribute(self):
        """EMHASSAdapter instances have an IndexManager."""
        from unittest.mock import MagicMock

        from custom_components.ev_trip_planner.emhass.adapter import (
            EMHASSAdapter,
        )
        from custom_components.ev_trip_planner.emhass.index_manager import (
            IndexManager,
        )

        hass = MagicMock()
        entry = MagicMock()
        adapter = EMHASSAdapter(hass=hass, entry=entry)
        assert hasattr(adapter, "_index_manager")
        assert isinstance(adapter._index_manager, IndexManager)
