"""Test fixtures for ev_trip_planner."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant

from custom_components.ev_trip_planner.const import DOMAIN


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations in all tests."""
    yield


@pytest.fixture
def mock_input_text_entity():
    """Return a mocked input_text entity with empty trips."""
    state = MagicMock()
    state.state = "[]"
    return state


@pytest.fixture
def mock_input_text_entity_with_trips():
    """Return a mocked input_text entity with sample trips."""
    state = MagicMock()
    state.state = """[
        {
            "id": "rec_lun_12345678",
            "tipo": "recurrente",
            "dia_semana": "lunes",
            "hora": "09:00",
            "km": 24,
            "kwh": 3.6,
            "descripcion": "Trabajo",
            "activo": true,
            "creado": "2025-11-18T10:00:00"
        },
        {
            "id": "pun_20251119_87654321",
            "tipo": "puntual",
            "datetime": "2025-11-19T15:00:00",
            "km": 110,
            "kwh": 16.5,
            "descripcion": "Viaje a Toledo",
            "estado": "pendiente",
            "creado": "2025-11-18T10:30:00"
        }
    ]"""
    return state


@pytest.fixture
def vehicle_id():
    """Return a sample vehicle ID."""
    return "chispitas"


@pytest.fixture
def hass():
    """
    Fixture to provide a working HomeAssistant instance for tests.
    
    This creates a minimal mock hass instance that avoids compatibility issues
    with pytest-homeassistant-custom-component.
    """
    # Create a mock hass instance instead of real HomeAssistant
    hass = MagicMock()
    
    # Mock the config attributes
    hass.config = MagicMock()
    hass.config.config_dir = "/tmp/test_config"
    hass.config.time_zone = "UTC"
    hass.config.latitude = 40.0
    hass.config.longitude = -3.0
    hass.config.elevation = 0
    
    # Mock states - use a dictionary to simulate state storage
    hass.states = MagicMock()
    hass._states_dict = {}  # Internal storage for states
    
    def _mock_states_get(entity_id):
        """Get state from storage."""
        result = hass._states_dict.get(entity_id, None)
        print(f"DEBUG: hass.states.get('{entity_id}') -> {result}")
        return result
    
    def _mock_states_set(entity_id, state, attributes=None):
        """Synchronous set for states."""
        from unittest.mock import MagicMock
        state_obj = MagicMock()
        state_obj.state = state
        state_obj.attributes = attributes or {}
        hass._states_dict[entity_id] = state_obj
        print(f"DEBUG: hass.states.set('{entity_id}', '{state}', {attributes})")
        return True
    
    async def _mock_states_async_set(entity_id, state, attributes=None):
        """Asynchronous set for states."""
        print(f"DEBUG: hass.states.async_set('{entity_id}', '{state}', {attributes})")
        _mock_states_set(entity_id, state, attributes)
        return True
    
    hass.states.get = _mock_states_get
    hass.states.set = _mock_states_set
    hass.states.async_set = _mock_states_async_set
    
    # Mock services
    hass.services = MagicMock()
    hass.services.async_call = AsyncMock()
    hass.services.has_service = MagicMock(return_value=True)
    
    # FIX: Añadir async_run_hass_job para el debounce del coordinator
    # El debounce llama a hass.async_run_hass_job(self._job) y espera el resultado
    # Necesitamos que devuelva una tarea/coroutine, no un MagicMock
    import asyncio
    
    def _mock_async_run_hass_job(job, *args, **kwargs):
        """Mock async_run_hass_job for debounce - devuelve una tarea real."""
        if job is None:
            return None
        
        # Extraer la función del HassJob
        job_target = None
        job_args = args or []
        job_kwargs = kwargs or {}
        
        # Si job tiene target (es un HassJob)
        if hasattr(job, 'target'):
            job_target = job.target
            # Si el job ya tiene args/kwargs incorporados
            if hasattr(job, 'args'):
                job_args = job.args
            if hasattr(job, 'kwargs'):
                job_kwargs = job.kwargs
        else:
            # Si es una función directa
            job_target = job
        
        if job_target is None:
            return None
        
        # Crear y devolver una tarea que ejecute la función
        if asyncio.iscoroutinefunction(job_target):
            return job_target(*job_args, **job_kwargs)
        else:
            # Para funciones síncronas, envolver en coroutine
            async def _wrapper():
                return job_target(*job_args, **job_kwargs)
            return _wrapper()
    
    hass.async_run_hass_job = _mock_async_run_hass_job
    
    yield hass


@pytest.fixture
def mock_store():
    """
    Fixture to provide a mock Store instance with async methods.
    
    This is needed because Store.async_load() and Store.async_save()
    are async methods that need to be mocked with AsyncMock, not MagicMock.
    
    This implementation also provides data persistence between calls.
    """
    store = MagicMock()
    store._storage = {}  # Internal storage for data persistence
    
    async def _async_load():
        return store._storage.get("data", None)
    
    async def _async_save(data):
        store._storage["data"] = data
        return True
    
    store.async_load = _async_load
    store.async_save = _async_save
    
    yield store
