import pytest

from custom_components.ev_trip_planner import dashboard
from custom_components.ev_trip_planner.dashboard import import_dashboard, DashboardImportResult


@pytest.mark.asyncio
async def test_import_dashboard_yaml_other_result(monkeypatch):
    async def fake_load(hass, vehicle_id, vehicle_name, use_charts):
        return {"title": "t", "views": [{"path": "v", "title": "T", "cards": []}]}

    async def fake_save_lovelace(hass, dashboard_config, vehicle_id):
        # Force storage helper to indicate failure and proceed to YAML fallback
        return False

    async def fake_save_yaml(hass, dashboard_config, vehicle_id):
        # Return a non-bool, non-DashboardImportResult to exercise the
        # "Any other result is a failure" branch.
        return {}

    monkeypatch.setattr(dashboard, "_load_dashboard_template", fake_load)
    monkeypatch.setattr(dashboard, "_save_lovelace_dashboard", fake_save_lovelace)
    monkeypatch.setattr(dashboard, "_save_dashboard_yaml_fallback", fake_save_yaml)

    class Hass:
        def __init__(self):
            self.config = type("C", (), {"components": ["lovelace"]})
            self.services = type("S", (), {})()
            self.services.has_service = lambda a, b: False

    hass = Hass()

    res = await import_dashboard(hass, "vid", "vname")

    assert isinstance(res, DashboardImportResult)
    assert res.success is False
    assert res.error == "All import methods failed"
