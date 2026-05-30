"""Constant-assertion tests for US-5 log string extraction.

These tests kill log_text mutations by asserting the exact values of
module-level log format string constants. Without these tests, mutmut
can mutate the constant string values and the mutants survive because
log output is not tested.
"""

from __future__ import annotations

import pytest


class TestTripCRUDLogConstants:
    """Assert values of log format string constants in _crud.py."""

    def test_log_add_recurring_debug_format(self):
        _crud = pytest.importorskip("custom_components.ev_trip_planner.trip._crud")
        assert (
            _crud._LOG_ADD_RECURRING_DEBUG
            == "Adding recurring trip for vehicle %s: dia_semana=%s, hora=%s, km=%.1f, kwh=%.2f"
        )

    def test_log_add_recurring_info_format(self):
        _crud = pytest.importorskip("custom_components.ev_trip_planner.trip._crud")
        assert _crud._LOG_ADD_RECURRING_INFO == "Added recurring trip %s for vehicle %s"

    def test_log_add_punctual_debug_format(self):
        _crud = pytest.importorskip("custom_components.ev_trip_planner.trip._crud")
        assert (
            _crud._LOG_ADD_PUNCTUAL_DEBUG
            == "Adding punctual trip for vehicle %s: datetime=%s, km=%.1f, kwh=%.2f"
        )

    def test_log_add_punctual_info_format(self):
        _crud = pytest.importorskip("custom_components.ev_trip_planner.trip._crud")
        assert _crud._LOG_ADD_PUNCTUAL_INFO == "Added punctual trip %s for vehicle %s"

    def test_log_update_debug_format(self):
        _crud = pytest.importorskip("custom_components.ev_trip_planner.trip._crud")
        assert _crud._LOG_UPDATE_DEBUG == "Updating trip %s for vehicle %s: updates=%s"

    def test_log_update_info_format(self):
        _crud = pytest.importorskip("custom_components.ev_trip_planner.trip._crud")
        assert _crud._LOG_UPDATE_INFO == "Updated %s trip %s for vehicle %s"

    def test_log_update_not_found_format(self):
        _crud = pytest.importorskip("custom_components.ev_trip_planner.trip._crud")
        assert (
            _crud._LOG_UPDATE_NOT_FOUND == "Trip %s not found for update in vehicle %s"
        )

    def test_log_delete_debug_format(self):
        _crud = pytest.importorskip("custom_components.ev_trip_planner.trip._crud")
        assert _crud._LOG_DELETE_DEBUG == "Deleting trip %s from vehicle %s"

    def test_log_delete_not_found_format(self):
        _crud = pytest.importorskip("custom_components.ev_trip_planner.trip._crud")
        assert (
            _crud._LOG_DELETE_NOT_FOUND
            == "Trip %s not found for deletion in vehicle %s"
        )

    def test_log_delete_info_format(self):
        _crud = pytest.importorskip("custom_components.ev_trip_planner.trip._crud")
        assert _crud._LOG_DELETE_INFO == "Deleted trip %s from vehicle %s"


class TestTripPersistenceLogConstants:
    """Assert values of log format string constants in _persistence.py."""

    def test_log_setup_info_format(self):
        _persistence = pytest.importorskip(
            "custom_components.ev_trip_planner.trip._persistence"
        )
        assert (
            _persistence._LOG_SETUP_INFO
            == "Configurando gestor de viajes para vehículo: %s"
        )

    def test_log_save_start_info_format(self):
        _persistence = pytest.importorskip(
            "custom_components.ev_trip_planner.trip._persistence"
        )
        assert (
            _persistence._LOG_SAVE_START_INFO
            == "async_save_trips START - vehicle=%s, recurrentes=%d, puntuales=%d"
        )

    def test_log_save_injected(self):
        _persistence = pytest.importorskip(
            "custom_components.ev_trip_planner.trip._persistence"
        )
        assert _persistence._LOG_SAVE_INJECTED == "=== Using injected storage ==="

    def test_log_save_fallback(self):
        _persistence = pytest.importorskip(
            "custom_components.ev_trip_planner.trip._persistence"
        )
        assert _persistence._LOG_SAVE_FALLBACK == "=== Using fallback HA Store ==="

    def test_log_save_key_info(self):
        _persistence = pytest.importorskip(
            "custom_components.ev_trip_planner.trip._persistence"
        )
        assert _persistence._LOG_SAVE_KEY_INFO == "Creating store with key: %s"

    def test_log_save_success_info(self):
        _persistence = pytest.importorskip(
            "custom_components.ev_trip_planner.trip._persistence"
        )
        assert (
            _persistence._LOG_SAVE_SUCCESS_INFO
            == "Viajes guardados en HA storage: %d recurrentes, %d puntuales"
        )

    def test_log_save_error(self):
        _persistence = pytest.importorskip(
            "custom_components.ev_trip_planner.trip._persistence"
        )
        assert _persistence._LOG_SAVE_ERROR == "Error guardando viajes: %s"

    def test_log_load_skip_debug(self):
        _persistence = pytest.importorskip(
            "custom_components.ev_trip_planner.trip._persistence"
        )
        assert (
            _persistence._LOG_LOAD_SKIP_DEBUG
            == "Skipping _load_trips for %s: already have %d punctual, %d recurring trips"
        )

    def test_log_load_start_debug(self):
        _persistence = pytest.importorskip(
            "custom_components.ev_trip_planner.trip._persistence"
        )
        assert (
            _persistence._LOG_LOAD_START_DEBUG == "=== _load_trips START === vehicle=%s"
        )

    def test_log_load_cancel_warning(self):
        _persistence = pytest.importorskip(
            "custom_components.ev_trip_planner.trip._persistence"
        )
        assert (
            _persistence._LOG_LOAD_CANCEL_WARNING
            == "Storage load cancelled (known timing issue) - continuing with empty state"
        )

    def test_log_load_error(self):
        _persistence = pytest.importorskip(
            "custom_components.ev_trip_planner.trip._persistence"
        )
        assert _persistence._LOG_LOAD_ERROR == "Error cargando viajes: %s"

    def test_log_load_yaml_error(self):
        _persistence = pytest.importorskip(
            "custom_components.ev_trip_planner.trip._persistence"
        )
        assert (
            _persistence._LOG_LOAD_YAML_ERROR == "Error cargando viajes desde YAML: %s"
        )

    def test_log_save_yaml_fail_error(self):
        _persistence = pytest.importorskip(
            "custom_components.ev_trip_planner.trip._persistence"
        )
        assert (
            _persistence._LOG_SAVE_YAML_FAIL_ERROR
            == "Error guardando viajes en YAML: %s"
        )

    def test_log_sanitize_warning(self):
        _persistence = pytest.importorskip(
            "custom_components.ev_trip_planner.trip._persistence"
        )
        assert (
            _persistence._LOG_SANITIZE_WARNING
            == "%d recurring trip(s) ignored due to invalid hora format."
        )


# ============================================================================
# _trip_lifecycle.py
# ============================================================================


class TestTripLifecycleLogConstants:
    """Assert values of log format string constants in _trip_lifecycle.py."""

    def test_log_coordinator_cleanup_warning_format(self):
        m = pytest.importorskip(
            "custom_components.ev_trip_planner.trip._trip_lifecycle"
        )
        assert (
            m._LOG_COORDINATOR_CLEANUP_WARNING
            == "Coordinator cleanup during delete_all: %s"
        )

    def test_log_deleted_all_info_format(self):
        m = pytest.importorskip(
            "custom_components.ev_trip_planner.trip._trip_lifecycle"
        )
        assert m._LOG_DELETED_ALL_INFO == "Deleted all trips for vehicle %s"

    def test_log_paused_recurring_info_format(self):
        m = pytest.importorskip(
            "custom_components.ev_trip_planner.trip._trip_lifecycle"
        )
        assert m._LOG_PAUSED_RECURRING_INFO == "Paused recurring trip %s for vehicle %s"

    def test_log_resumed_recurring_info_format(self):
        m = pytest.importorskip(
            "custom_components.ev_trip_planner.trip._trip_lifecycle"
        )
        assert (
            m._LOG_RESUMED_RECURRING_INFO == "Resumed recurring trip %s for vehicle %s"
        )

    def test_log_completed_punctual_info_format(self):
        m = pytest.importorskip(
            "custom_components.ev_trip_planner.trip._trip_lifecycle"
        )
        assert (
            m._LOG_COMPLETED_PUNCTUAL_INFO
            == "Completed punctual trip %s for vehicle %s"
        )

    def test_log_cancelled_punctual_info_format(self):
        m = pytest.importorskip(
            "custom_components.ev_trip_planner.trip._trip_lifecycle"
        )
        assert (
            m._LOG_CANCELLED_PUNCTUAL_INFO
            == "Cancelled punctual trip %s for vehicle %s"
        )

    def test_log_recurring_not_found_pause_warning_format(self):
        m = pytest.importorskip(
            "custom_components.ev_trip_planner.trip._trip_lifecycle"
        )
        assert (
            m._LOG_RECURRING_NOT_FOUND_PAUSE_WARNING
            == "Recurring trip %s not found for pause in vehicle %s"
        )

    def test_log_recurring_not_found_resume_warning_format(self):
        m = pytest.importorskip(
            "custom_components.ev_trip_planner.trip._trip_lifecycle"
        )
        assert (
            m._LOG_RECURRING_NOT_FOUND_RESUME_WARNING
            == "Recurring trip %s not found for resume in vehicle %s"
        )

    def test_log_punctual_not_found_complete_warning_format(self):
        m = pytest.importorskip(
            "custom_components.ev_trip_planner.trip._trip_lifecycle"
        )
        assert (
            m._LOG_PUNCTUAL_NOT_FOUND_COMPLETE_WARNING
            == "Punctual trip %s not found for completion in vehicle %s"
        )

    def test_log_punctual_not_found_cancel_warning_format(self):
        m = pytest.importorskip(
            "custom_components.ev_trip_planner.trip._trip_lifecycle"
        )
        assert (
            m._LOG_PUNCTUAL_NOT_FOUND_CANCEL_WARNING
            == "Punctual trip %s not found for cancellation in vehicle %s"
        )

    def test_log_trip_not_found_sensor_update_warning_format(self):
        m = pytest.importorskip(
            "custom_components.ev_trip_planner.trip._trip_lifecycle"
        )
        assert (
            m._LOG_TRIP_NOT_FOUND_SENSOR_UPDATE_WARNING
            == "Trip %s not found for sensor update in vehicle %s"
        )

    def test_log_error_updating_trip_sensor_error_format(self):
        m = pytest.importorskip(
            "custom_components.ev_trip_planner.trip._trip_lifecycle"
        )
        assert (
            m._LOG_ERROR_UPDATING_TRIP_SENSOR_ERROR
            == "Error updating trip sensor for trip %s: %s"
        )


# ============================================================================
# _soc_helpers.py
# ============================================================================


class TestTripSocHelpersLogConstants:
    """Assert values of log format string constants in _soc_helpers.py."""

    def test_log_parse_failed_warning_format(self):
        m = pytest.importorskip("custom_components.ev_trip_planner.trip._soc_helpers")
        assert (
            m._LOG_PARSE_FAILED_WARNING
            == "Failed to parse trip datetime: %s, falling back to now"
        )

    def test_log_parse_repr_warning_format(self):
        m = pytest.importorskip("custom_components.ev_trip_planner.trip._soc_helpers")
        assert m._LOG_PARSE_REPR_WARNING == "Failed to parse trip datetime: %s"


# ============================================================================
# _soc_query.py
# ============================================================================


class TestTripSocQueryLogConstants:
    """Assert values of log format string constants in _soc_query.py."""

    def test_log_soc_sensor_not_available_warning_format(self):
        m = pytest.importorskip("custom_components.ev_trip_planner.trip._soc_query")
        assert (
            m._LOG_SOC_SENSOR_NOT_AVAILABLE_WARNING
            == "Sensor SOC no disponible para %s"
        )

    def test_log_config_entry_not_found_warning_format(self):
        m = pytest.importorskip("custom_components.ev_trip_planner.trip._soc_query")
        assert (
            m._LOG_CONFIG_ENTRY_NOT_FOUND_WARNING
            == "Config entry no encontrada para %s"
        )

    def test_log_soc_fetch_error_format(self):
        m = pytest.importorskip("custom_components.ev_trip_planner.trip._soc_query")
        assert m._LOG_SOC_FETCH_ERROR == "Error obteniendo SOC: %s"

    def test_log_missing_required_field_error_format(self):
        m = pytest.importorskip("custom_components.ev_trip_planner.trip._soc_query")
        assert (
            m._LOG_MISSING_REQUIRED_FIELD_ERROR
            == "async_calcular_energia_necesaria: missing required field '%s' in vehicle_config for trip %s"
        )


# ============================================================================
# _emhass_sync.py
# ============================================================================


class TestTripEmhassSyncLogConstants:
    """Assert values of log format string constants in _emhass_sync.py."""

    def test_log_inactive_trip_info_format(self):
        m = pytest.importorskip("custom_components.ev_trip_planner.trip._emhass_sync")
        assert m._LOG_INACTIVE_TRIP_INFO == "Trip %s is inactive, removed from EMHASS"

    def test_log_recaculated_info_format(self):
        m = pytest.importorskip("custom_components.ev_trip_planner.trip._emhass_sync")
        assert (
            m._LOG_RECALCULATED_INFO
            == "Trip %s updated in EMHASS (recalculated): fields=%s"
        )

    def test_log_attributes_info_format(self):
        m = pytest.importorskip("custom_components.ev_trip_planner.trip._emhass_sync")
        assert (
            m._LOG_ATTRIBUTES_INFO
            == "Trip %s updated in EMHASS (attributes): fields=%s"
        )

    def test_log_sync_error_format(self):
        m = pytest.importorskip("custom_components.ev_trip_planner.trip._emhass_sync")
        assert m._LOG_SYNC_ERROR == "Error syncing trip %s to EMHASS: %s"

    def test_log_removed_info_format(self):
        m = pytest.importorskip("custom_components.ev_trip_planner.trip._emhass_sync")
        assert m._LOG_REMOVED_INFO == "Trip %s removed from EMHASS"

    def test_log_remove_error_format(self):
        m = pytest.importorskip("custom_components.ev_trip_planner.trip._emhass_sync")
        assert m._LOG_REMOVE_ERROR == "Error removing trip %s from EMHASS: %s"

    def test_log_published_info_format(self):
        m = pytest.importorskip("custom_components.ev_trip_planner.trip._emhass_sync")
        assert m._LOG_PUBLISHED_INFO == "Published new trip %s to EMHASS"

    def test_log_publish_error_format(self):
        m = pytest.importorskip("custom_components.ev_trip_planner.trip._emhass_sync")
        assert m._LOG_PUBLISH_ERROR == "Error publishing trip %s to EMHASS: %s"


# ============================================================================
# _schedule.py
# ============================================================================


class TestTripScheduleLogConstants:
    """Assert values of log format string constants in _schedule.py."""

    def test_log_defferrables_publish_error_format(self):
        m = pytest.importorskip("custom_components.ev_trip_planner.trip._schedule")
        assert (
            m._LOG_DEFFERABLES_PUBLISH_ERROR
            == "Error publishing deferrable loads to EMHASS"
        )


# ============================================================================
# _power_profile.py
# ============================================================================


class TestTripPowerProfileLogConstants:
    """Assert values of log format string constants in _power_profile.py."""

    def test_log_missing_battery_config_format(self):
        m = pytest.importorskip("custom_components.ev_trip_planner.trip._power_profile")
        assert (
            m._LOG_MISSING_BATTERY_CONFIG
            == "Missing 'battery_capacity_kwh' in vehicle_config"
        )

    def test_log_missing_safety_margin_config_format(self):
        m = pytest.importorskip("custom_components.ev_trip_planner.trip._power_profile")
        assert (
            m._LOG_MISSING_SAFETY_MARGIN_CONFIG
            == "Missing 'safety_margin_percent' in vehicle_config"
        )

    def test_log_missing_battery_entry_format(self):
        m = pytest.importorskip("custom_components.ev_trip_planner.trip._power_profile")
        assert (
            m._LOG_MISSING_BATTERY_ENTRY
            == "Missing 'battery_capacity_kwh' in config entry"
        )

    def test_log_missing_safety_margin_entry_format(self):
        m = pytest.importorskip("custom_components.ev_trip_planner.trip._power_profile")
        assert (
            m._LOG_MISSING_SAFETY_MARGIN_ENTRY
            == "Missing 'safety_margin_percent' in config entry"
        )


# ============================================================================
# _sensor_callbacks.py
# ============================================================================


class TestTripSensorCallbacksLogConstants:
    """Assert values of log format string constants in _sensor_callbacks.py."""

    def test_log_trip_data_required_for_trip_created_recurring_event_format(self):
        m = pytest.importorskip(
            "custom_components.ev_trip_planner.trip._sensor_callbacks"
        )
        assert (
            m._LOG_TRIP_DATA_REQUIRED_FOR_TRIP_CREATED_RECURRING_EVEN
            == "trip_data required for trip_created_recurring event"
        )

    def test_log_trip_data_required_for_trip_created_punctual_event_format(self):
        m = pytest.importorskip(
            "custom_components.ev_trip_planner.trip._sensor_callbacks"
        )
        assert (
            m._LOG_TRIP_DATA_REQUIRED_FOR_TRIP_CREATED_PUNCTUAL_EVENT
            == "trip_data required for trip_created_punctual event"
        )

    def test_log_trip_id_required_for_trip_sensor_created_emhass_ev_format(self):
        m = pytest.importorskip(
            "custom_components.ev_trip_planner.trip._sensor_callbacks"
        )
        assert (
            m._LOG_TRIP_ID_REQUIRED_FOR_TRIP_SENSOR_CREATED_EMHASS_EV
            == "trip_id required for trip_sensor_created_emhass event"
        )

    def test_log_trip_id_required_for_trip_removed_event_format(self):
        m = pytest.importorskip(
            "custom_components.ev_trip_planner.trip._sensor_callbacks"
        )
        assert (
            m._LOG_TRIP_ID_REQUIRED_FOR_TRIP_REMOVED_EVENT
            == "trip_id required for trip_removed event"
        )

    def test_log_trip_id_required_for_trip_sensor_removed_emhass_ev_format(self):
        m = pytest.importorskip(
            "custom_components.ev_trip_planner.trip._sensor_callbacks"
        )
        assert (
            m._LOG_TRIP_ID_REQUIRED_FOR_TRIP_SENSOR_REMOVED_EMHASS_EV
            == "trip_id required for trip_sensor_removed_emhass event"
        )

    def test_log_trip_data_required_for_trip_sensor_updated_event_format(self):
        m = pytest.importorskip(
            "custom_components.ev_trip_planner.trip._sensor_callbacks"
        )
        assert (
            m._LOG_TRIP_DATA_REQUIRED_FOR_TRIP_SENSOR_UPDATED_EVENT
            == "trip_data required for trip_sensor_updated event"
        )


# ============================================================================
# manager.py
# ============================================================================


class TestTripManagerLogConstants:
    """Assert values of log format string constants in manager.py."""

    def test_log_emhass_adapter_set_debug_format(self):
        m = pytest.importorskip("custom_components.ev_trip_planner.trip.manager")
        assert m._LOG_EMHASS_ADAPTER_SET_DEBUG == "EMHASS adapter set for vehicle %s"

    def test_log_sanitize_recurring_warning_format(self):
        m = pytest.importorskip("custom_components.ev_trip_planner.trip.manager")
        assert (
            m._LOG_SANITIZE_RECURRING_WARNING
            == "%d recurring trip(s) ignored due to invalid hora format. Fix or remove invalid entries from storage."
        )
