import asyncio

from types import SimpleNamespace


def test_read_write_file(tmp_path):
    """Ejecuta _write_file_content y _read_file_content."""
    from custom_components.ev_trip_planner.dashboard import (
        _read_file_content,
        _write_file_content,
    )

    p = tmp_path / "test_dashboard_io.yaml"
    _write_file_content(str(p), "hello-world")
    content = _read_file_content(str(p))
    assert content == "hello-world"


async def _fake_executor(func, *args):
    # emulate async executor that calls the function synchronously
    return func(*args)


async def test_call_async_executor_with_coroutine_hass():
    """Verifica la rama donde hass.async_add_executor_job es una coroutine function."""
    from custom_components.ev_trip_planner.dashboard import (
        _call_async_executor_sync,
        _await_executor_result,
    )

    class Hass:
        async def async_add_executor_job(self, func, *args):
            return func(*args)

    hass = Hass()

    # _call_async_executor_sync should return a coroutine when async_add_executor_job is a coroutine
    coro = _call_async_executor_sync(hass, lambda x: x + 1, 1)
    result = await _await_executor_result(coro)
    assert result == 2


async def test_import_dashboard_returns_structured_failure_when_yaml_helper_fails(monkeypatch):
    """Simula que la API de storage falla y el helper YAML devuelve un DashboardImportResult fallido."""
    from custom_components.ev_trip_planner.dashboard import (
        import_dashboard,
        DashboardImportResult,
    )

    # Mock helpers
    async def fake_load(*args, **kwargs):
        return {"title": "t", "views": [{"path": "v", "title": "T", "cards": []}]}

    async def fake_save_lovelace(*args, **kwargs):
        # simulate storage API non-success (legacy False)
        return False

    async def fake_save_yaml(*args, **kwargs):
        # simulate YAML helper returning a structured failure
        return DashboardImportResult(
            success=False,
            vehicle_id="vid",
            vehicle_name="vname",
            error="yaml failed",
            dashboard_type="simple",
            storage_method="none",
        )

    monkeypatch.setattr(
        "custom_components.ev_trip_planner.dashboard._load_dashboard_template",
        fake_load,
    )
    monkeypatch.setattr(
        "custom_components.ev_trip_planner.dashboard._save_lovelace_dashboard",
        fake_save_lovelace,
    )
    monkeypatch.setattr(
        "custom_components.ev_trip_planner.dashboard._save_dashboard_yaml_fallback",
        fake_save_yaml,
    )

    class Hass:
        config = SimpleNamespace(components=["lovelace"])  # lovelace available
        services = SimpleNamespace()

        def __init__(self):
            # has_service used in is_lovelace_available
            self.services.has_service = lambda a, b: False

    hass = Hass()

    res = await import_dashboard(hass, "vid", "vname", use_charts=False)
    assert isinstance(res, DashboardImportResult)
    assert res.success is False
    assert res.error is not None


async def test_save_yaml_creates_config_dir(tmp_path):
    """Verifica que _save_dashboard_yaml_fallback crea el directorio de config cuando no existe."""
    from custom_components.ev_trip_planner.dashboard import (
        _save_dashboard_yaml_fallback,
        DashboardImportResult,
    )

    # Create a hass-like object with no existing config dir
    class Hass:
        def __init__(self, config_dir):
            self.config = SimpleNamespace(config_dir=config_dir)

    cfg_dir = str(tmp_path / "config_dir")
    hass = Hass(cfg_dir)

    dashboard_config = {"title": "t", "views": [{"path": "p", "title": "T", "cards": []}]}

    res = await _save_dashboard_yaml_fallback(hass, dashboard_config, "vid")
    assert isinstance(res, DashboardImportResult)
    assert res.success is True
