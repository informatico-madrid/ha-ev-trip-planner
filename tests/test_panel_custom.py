"""Tests for panel_custom.py."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_async_setup_calls_async_register_panel():
    """async_setup registers the panel correctly."""
    from custom_components.ev_trip_planner.panel_custom import async_setup

    mock_hass = MagicMock()

    with patch(
        "custom_components.ev_trip_planner.panel_custom.async_register_panel",
        new_callable=AsyncMock,
    ) as mock_register:
        result = await async_setup(mock_hass, {})

    mock_register.assert_called_once_with(
        mock_hass,
        frontend_url_path="ev-trip-planner",
        webcomponent_name="ev-trip-planner-panel",
        sidebar_title="EV Trip Planner",
        sidebar_icon="mdi:car",
        config={},
    )
    assert result is True


@pytest.mark.asyncio
async def test_async_setup_returns_true_on_success():
    """async_setup returns True when panel registration succeeds."""
    from custom_components.ev_trip_planner.panel_custom import async_setup

    mock_hass = MagicMock()

    with patch(
        "custom_components.ev_trip_planner.panel_custom.async_register_panel",
        new_callable=AsyncMock,
    ):
        result = await async_setup(mock_hass, {})

    assert result is True
