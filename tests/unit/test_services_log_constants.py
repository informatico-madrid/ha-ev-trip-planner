"""US-5: Log constant assertion tests for services module.

Asserts that extracted log format string constants exist and have
the expected values. These tests kill log_text mutations where
mutmut replaces string literals in logger calls with None.
"""



class TestUtilsLogConstants:
    """Test US-5 log constants in services/_utils.py."""

    def test_log_constants_exist(self):
        """Verify all _utils log constants are importable."""
        from custom_components.ev_trip_planner.services._utils import (
            _LOG_FIND_ENTRY_NONE,
            _LOG_MANAGER_AFTER_SETUP,
            _LOG_MANAGER_BEFORE_SETUP,
            _LOG_MANAGER_CREATED,
            _LOG_MANAGER_CREATING,
            _LOG_MANAGER_END,
            _LOG_MANAGER_ERR_NOT_FOUND,
            _LOG_MANAGER_EXISTS,
            _LOG_MANAGER_FOUND_ENTRY,
            _LOG_MANAGER_LOADED,
            _LOG_MANAGER_RUNTIME_DATA,
            _LOG_MANAGER_SETUP_CALL,
            _LOG_MANAGER_SETUP_ERR,
            _LOG_MANAGER_START,
            _LOG_MANAGER_TRIP_MGR,
        )

        for name, val in [
            ("_LOG_FIND_ENTRY_NONE", _LOG_FIND_ENTRY_NONE),
            ("_LOG_MANAGER_START", _LOG_MANAGER_START),
            ("_LOG_MANAGER_ERR_NOT_FOUND", _LOG_MANAGER_ERR_NOT_FOUND),
            ("_LOG_MANAGER_FOUND_ENTRY", _LOG_MANAGER_FOUND_ENTRY),
            ("_LOG_MANAGER_RUNTIME_DATA", _LOG_MANAGER_RUNTIME_DATA),
            ("_LOG_MANAGER_TRIP_MGR", _LOG_MANAGER_TRIP_MGR),
            ("_LOG_MANAGER_CREATING", _LOG_MANAGER_CREATING),
            ("_LOG_MANAGER_BEFORE_SETUP", _LOG_MANAGER_BEFORE_SETUP),
            ("_LOG_MANAGER_SETUP_CALL", _LOG_MANAGER_SETUP_CALL),
            ("_LOG_MANAGER_AFTER_SETUP", _LOG_MANAGER_AFTER_SETUP),
            ("_LOG_MANAGER_SETUP_ERR", _LOG_MANAGER_SETUP_ERR),
            ("_LOG_MANAGER_CREATED", _LOG_MANAGER_CREATED),
            ("_LOG_MANAGER_LOADED", _LOG_MANAGER_LOADED),
            ("_LOG_MANAGER_EXISTS", _LOG_MANAGER_EXISTS),
            ("_LOG_MANAGER_END", _LOG_MANAGER_END),
        ]:
            assert isinstance(val, str) and val, f"{name} must be non-empty string"

    def test_find_entry_none_format(self):
        """_LOG_FIND_ENTRY_NONE has one %s placeholder."""
        from custom_components.ev_trip_planner.services._utils import (
            _LOG_FIND_ENTRY_NONE,
        )

        assert "%s" in _LOG_FIND_ENTRY_NONE
        result = _LOG_FIND_ENTRY_NONE % "entry_abc"
        assert "entry_abc" in result

    def test_manager_err_not_found_format(self):
        """_LOG_MANAGER_ERR_NOT_FOUND has one %s placeholder."""
        from custom_components.ev_trip_planner.services._utils import (
            _LOG_MANAGER_ERR_NOT_FOUND,
        )

        assert "%s" in _LOG_MANAGER_ERR_NOT_FOUND
        result = _LOG_MANAGER_ERR_NOT_FOUND % "vehicle_1"
        assert "vehicle_1" in result

    def test_manager_found_entry_format(self):
        """_LOG_MANAGER_FOUND_ENTRY has two %s placeholders."""
        from custom_components.ev_trip_planner.services._utils import (
            _LOG_MANAGER_FOUND_ENTRY,
        )

        assert _LOG_MANAGER_FOUND_ENTRY.count("%s") >= 2
        result = _LOG_MANAGER_FOUND_ENTRY % ("abc123", "entry_001")
        assert "abc123" in result
        assert "entry_001" in result

    def test_manager_before_setup_format(self):
        """_LOG_MANAGER_BEFORE_SETUP has two %d placeholders."""
        from custom_components.ev_trip_planner.services._utils import (
            _LOG_MANAGER_BEFORE_SETUP,
        )

        result = _LOG_MANAGER_BEFORE_SETUP % (3, 1)
        assert "3" in result
        assert "1" in result

    def test_manager_setup_err_format(self):
        """_LOG_MANAGER_SETUP_ERR has two placeholders."""
        from custom_components.ev_trip_planner.services._utils import (
            _LOG_MANAGER_SETUP_ERR,
        )

        result = _LOG_MANAGER_SETUP_ERR % ("vehicle_1", Exception("fail"))
        assert "vehicle_1" in result

    def test_manager_loaded_format(self):
        """_LOG_MANAGER_LOADED has two %d placeholders."""
        from custom_components.ev_trip_planner.services._utils import (
            _LOG_MANAGER_LOADED,
        )

        result = _LOG_MANAGER_LOADED % (3, 1)
        assert "3" in result
        assert "1" in result

    def test_manager_exists_format(self):
        """_LOG_MANAGER_EXISTS has three placeholders."""
        from custom_components.ev_trip_planner.services._utils import (
            _LOG_MANAGER_EXISTS,
        )

        result = _LOG_MANAGER_EXISTS % ("v1", 3, 1)
        assert "v1" in result
        assert "3" in result
        assert "1" in result


class TestCleanupLogConstants:
    """Test US-5 log constants in services/cleanup.py."""

    def test_log_constants_exist(self):
        """Verify all cleanup log constants are importable."""
        from custom_components.ev_trip_planner.services.cleanup import (
            _LOG_CASCADE_DELETE,
            _LOG_CLEANED_STALE_YAML,
            _LOG_CLEANED_YAML_FALLBACK,
            _LOG_CLEANUP_EMHASS_INDICES,
            _LOG_CLEANUP_EMHASS_INDICES_ERR,
            _LOG_CLEANUP_ENTITY_REG,
            _LOG_CLEANUP_ORPHANED_EMHASS,
            _LOG_CLEANUP_SAFETY_NET_ERROR,
            _LOG_CLEANUP_UNREGISTER_PANEL,
            _LOG_REMOVE_ENTRY_CALLED,
            _LOG_REMOVE_ENTRY_COMPLETED,
            _LOG_REMOVE_LISTENER_ERROR,
            _LOG_REMOVE_STORAGE_WARN,
            _LOG_REMOVE_TRIPS_ERROR,
            _LOG_SKIPPING_YAML_CLEANUP,
            _LOG_UNLOAD_BEFORE_REMOVE,
            _LOG_UNLOAD_CALL_CLEANUP_IDX,
            _LOG_UNLOAD_CALL_DELETE,
            _LOG_UNLOAD_CLEANUP_IDX_DONE,
            _LOG_UNLOAD_REMOVED_LISTENER,
            _LOG_YAML_REMOVAL_WARN,
        )

        for name, val in [
            ("_LOG_CLEANED_STALE_YAML", _LOG_CLEANED_STALE_YAML),
            ("_LOG_SKIPPING_YAML_CLEANUP", _LOG_SKIPPING_YAML_CLEANUP),
            ("_LOG_CLEANUP_SAFETY_NET_ERROR", _LOG_CLEANUP_SAFETY_NET_ERROR),
            ("_LOG_CLEANUP_ORPHANED_EMHASS", _LOG_CLEANUP_ORPHANED_EMHASS),
            ("_LOG_UNLOAD_BEFORE_REMOVE", _LOG_UNLOAD_BEFORE_REMOVE),
            ("_LOG_UNLOAD_REMOVED_LISTENER", _LOG_UNLOAD_REMOVED_LISTENER),
            ("_LOG_UNLOAD_CALL_DELETE", _LOG_UNLOAD_CALL_DELETE),
            ("_LOG_UNLOAD_CALL_CLEANUP_IDX", _LOG_UNLOAD_CALL_CLEANUP_IDX),
            ("_LOG_UNLOAD_CLEANUP_IDX_DONE", _LOG_UNLOAD_CLEANUP_IDX_DONE),
            ("_LOG_CLEANUP_ENTITY_REG", _LOG_CLEANUP_ENTITY_REG),
            ("_LOG_CLEANUP_UNREGISTER_PANEL", _LOG_CLEANUP_UNREGISTER_PANEL),
            ("_LOG_REMOVE_ENTRY_CALLED", _LOG_REMOVE_ENTRY_CALLED),
            ("_LOG_REMOVE_LISTENER_ERROR", _LOG_REMOVE_LISTENER_ERROR),
            ("_LOG_CASCADE_DELETE", _LOG_CASCADE_DELETE),
            ("_LOG_REMOVE_TRIPS_ERROR", _LOG_REMOVE_TRIPS_ERROR),
            ("_LOG_CLEANUP_EMHASS_INDICES", _LOG_CLEANUP_EMHASS_INDICES),
            ("_LOG_CLEANUP_EMHASS_INDICES_ERR", _LOG_CLEANUP_EMHASS_INDICES_ERR),
            ("_LOG_REMOVE_STORAGE_WARN", _LOG_REMOVE_STORAGE_WARN),
            ("_LOG_CLEANED_YAML_FALLBACK", _LOG_CLEANED_YAML_FALLBACK),
            ("_LOG_YAML_REMOVAL_WARN", _LOG_YAML_REMOVAL_WARN),
            ("_LOG_REMOVE_ENTRY_COMPLETED", _LOG_REMOVE_ENTRY_COMPLETED),
        ]:
            assert isinstance(val, str) and val, f"{name} must be non-empty string"

    def test_cleaned_stale_yaml_format(self):
        """_LOG_CLEANED_STALE_YAML has one %s placeholder."""
        from custom_components.ev_trip_planner.services.cleanup import (
            _LOG_CLEANED_STALE_YAML,
        )

        assert "%s" in _LOG_CLEANED_STALE_YAML
        result = _LOG_CLEANED_STALE_YAML % "vehicle_1"
        assert "vehicle_1" in result

    def test_skipping_yaml_cleanup_format(self):
        """_LOG_SKIPPING_YAML_CLEANUP has one %s placeholder."""
        from custom_components.ev_trip_planner.services.cleanup import (
            _LOG_SKIPPING_YAML_CLEANUP,
        )

        assert "%s" in _LOG_SKIPPING_YAML_CLEANUP
        result = _LOG_SKIPPING_YAML_CLEANUP % "vehicle_1"
        assert "vehicle_1" in result

    def test_cleanup_safety_net_error_format(self):
        """_LOG_CLEANUP_SAFETY_NET_ERROR has one %s placeholder."""
        from custom_components.ev_trip_planner.services.cleanup import (
            _LOG_CLEANUP_SAFETY_NET_ERROR,
        )

        assert "%s" in _LOG_CLEANUP_SAFETY_NET_ERROR
        result = _LOG_CLEANUP_SAFETY_NET_ERROR % Exception("fail")
        assert "fail" in result

    def test_cleanup_orphaned_emhass_format(self):
        """_LOG_CLEANUP_ORPHANED_EMHASS has one %s placeholder."""
        from custom_components.ev_trip_planner.services.cleanup import (
            _LOG_CLEANUP_ORPHANED_EMHASS,
        )

        assert "%s" in _LOG_CLEANUP_ORPHANED_EMHASS
        result = _LOG_CLEANUP_ORPHANED_EMHASS % Exception("fail")
        assert "fail" in result

    def test_unload_before_remove_format(self):
        """_LOG_UNLOAD_BEFORE_REMOVE has two %s placeholders."""
        from custom_components.ev_trip_planner.services.cleanup import (
            _LOG_UNLOAD_BEFORE_REMOVE,
        )

        assert _LOG_UNLOAD_BEFORE_REMOVE.count("%s") >= 2
        result = _LOG_UNLOAD_BEFORE_REMOVE % ("adapter", "listener")
        assert "adapter" in result
        assert "listener" in result

    def test_unload_removed_listener_format(self):
        """_LOG_UNLOAD_REMOVED_LISTENER has one %s placeholder."""
        from custom_components.ev_trip_planner.services.cleanup import (
            _LOG_UNLOAD_REMOVED_LISTENER,
        )

        assert "%s" in _LOG_UNLOAD_REMOVED_LISTENER
        result = _LOG_UNLOAD_REMOVED_LISTENER % "My Car"
        assert "My Car" in result

    def test_unload_call_delete_format(self):
        """_LOG_UNLOAD_CALL_DELETE has two %s placeholders."""
        from custom_components.ev_trip_planner.services.cleanup import (
            _LOG_UNLOAD_CALL_DELETE,
        )

        assert _LOG_UNLOAD_CALL_DELETE.count("%s") >= 2
        result = _LOG_UNLOAD_CALL_DELETE % ("My Car", "trip_mgr")
        assert "My Car" in result
        assert "trip_mgr" in result

    def test_unload_cleanup_idx_format(self):
        """_LOG_UNLOAD_CALL_CLEANUP_IDX has one %s placeholder."""
        from custom_components.ev_trip_planner.services.cleanup import (
            _LOG_UNLOAD_CALL_CLEANUP_IDX,
        )

        assert "%s" in _LOG_UNLOAD_CALL_CLEANUP_IDX
        result = _LOG_UNLOAD_CALL_CLEANUP_IDX % "My Car"
        assert "My Car" in result

    def test_unload_cleanup_idx_done_format(self):
        """_LOG_UNLOAD_CLEANUP_IDX_DONE has one %s placeholder."""
        from custom_components.ev_trip_planner.services.cleanup import (
            _LOG_UNLOAD_CLEANUP_IDX_DONE,
        )

        assert "%s" in _LOG_UNLOAD_CLEANUP_IDX_DONE
        result = _LOG_UNLOAD_CLEANUP_IDX_DONE % "My Car"
        assert "My Car" in result

    def test_cleanup_entity_reg_format(self):
        """_LOG_CLEANUP_ENTITY_REG has one %s placeholder."""
        from custom_components.ev_trip_planner.services.cleanup import (
            _LOG_CLEANUP_ENTITY_REG,
        )

        assert "%s" in _LOG_CLEANUP_ENTITY_REG
        result = _LOG_CLEANUP_ENTITY_REG % Exception("fail")
        assert "fail" in result

    def test_cleanup_unregister_panel_format(self):
        """_LOG_CLEANUP_UNREGISTER_PANEL has two %s placeholders."""
        from custom_components.ev_trip_planner.services.cleanup import (
            _LOG_CLEANUP_UNREGISTER_PANEL,
        )

        assert _LOG_CLEANUP_UNREGISTER_PANEL.count("%s") >= 2
        result = _LOG_CLEANUP_UNREGISTER_PANEL % ("vehicle_1", Exception("fail"))
        assert "vehicle_1" in result

    def test_remove_entry_called_format(self):
        """_LOG_REMOVE_ENTRY_CALLED has one %s placeholder."""
        from custom_components.ev_trip_planner.services.cleanup import (
            _LOG_REMOVE_ENTRY_CALLED,
        )

        assert "%s" in _LOG_REMOVE_ENTRY_CALLED
        result = _LOG_REMOVE_ENTRY_CALLED % "entry_abc"
        assert "entry_abc" in result

    def test_remove_listener_error_format(self):
        """_LOG_REMOVE_LISTENER_ERROR has one %s placeholder."""
        from custom_components.ev_trip_planner.services.cleanup import (
            _LOG_REMOVE_LISTENER_ERROR,
        )

        assert "%s" in _LOG_REMOVE_LISTENER_ERROR
        result = _LOG_REMOVE_LISTENER_ERROR % Exception("fail")
        assert "fail" in result

    def test_cascade_delete_format(self):
        """_LOG_CASCADE_DELETE has one %s placeholder."""
        from custom_components.ev_trip_planner.services.cleanup import (
            _LOG_CASCADE_DELETE,
        )

        assert "%s" in _LOG_CASCADE_DELETE
        result = _LOG_CASCADE_DELETE % "vehicle_1"
        assert "vehicle_1" in result

    def test_remove_trips_error_format(self):
        """_LOG_REMOVE_TRIPS_ERROR has two %s placeholders."""
        from custom_components.ev_trip_planner.services.cleanup import (
            _LOG_REMOVE_TRIPS_ERROR,
        )

        assert _LOG_REMOVE_TRIPS_ERROR.count("%s") >= 2
        result = _LOG_REMOVE_TRIPS_ERROR % ("vehicle_1", Exception("fail"))
        assert "vehicle_1" in result

    def test_cleanup_emhass_indices_format(self):
        """_LOG_CLEANUP_EMHASS_INDICES has one %s placeholder."""
        from custom_components.ev_trip_planner.services.cleanup import (
            _LOG_CLEANUP_EMHASS_INDICES,
        )

        assert "%s" in _LOG_CLEANUP_EMHASS_INDICES
        result = _LOG_CLEANUP_EMHASS_INDICES % "vehicle_1"
        assert "vehicle_1" in result

    def test_cleanup_emhass_indices_err_format(self):
        """_LOG_CLEANUP_EMHASS_INDICES_ERR has two %s placeholders."""
        from custom_components.ev_trip_planner.services.cleanup import (
            _LOG_CLEANUP_EMHASS_INDICES_ERR,
        )

        assert _LOG_CLEANUP_EMHASS_INDICES_ERR.count("%s") >= 2
        result = _LOG_CLEANUP_EMHASS_INDICES_ERR % ("vehicle_1", Exception("fail"))
        assert "vehicle_1" in result

    def test_remove_storage_warn_format(self):
        """_LOG_REMOVE_STORAGE_WARN has two %s placeholders."""
        from custom_components.ev_trip_planner.services.cleanup import (
            _LOG_REMOVE_STORAGE_WARN,
        )

        assert _LOG_REMOVE_STORAGE_WARN.count("%s") >= 2
        result = _LOG_REMOVE_STORAGE_WARN % ("vehicle_1", Exception("fail"))
        assert "vehicle_1" in result

    def test_cleaned_yaml_fallback_format(self):
        """_LOG_CLEANED_YAML_FALLBACK has one %s placeholder."""
        from custom_components.ev_trip_planner.services.cleanup import (
            _LOG_CLEANED_YAML_FALLBACK,
        )

        assert "%s" in _LOG_CLEANED_YAML_FALLBACK
        result = _LOG_CLEANED_YAML_FALLBACK % "vehicle_1"
        assert "vehicle_1" in result

    def test_yaml_removal_warn_format(self):
        """_LOG_YAML_REMOVAL_WARN has two %s placeholders."""
        from custom_components.ev_trip_planner.services.cleanup import (
            _LOG_YAML_REMOVAL_WARN,
        )

        assert _LOG_YAML_REMOVAL_WARN.count("%s") >= 2
        result = _LOG_YAML_REMOVAL_WARN % ("vehicle_1", Exception("fail"))
        assert "vehicle_1" in result

    def test_remove_entry_completed_format(self):
        """_LOG_REMOVE_ENTRY_COMPLETED has one %s placeholder."""
        from custom_components.ev_trip_planner.services.cleanup import (
            _LOG_REMOVE_ENTRY_COMPLETED,
        )

        assert "%s" in _LOG_REMOVE_ENTRY_COMPLETED
        result = _LOG_REMOVE_ENTRY_COMPLETED % "entry_abc"
        assert "entry_abc" in result


class TestDashboardHelpersLogConstants:
    """Test US-5 log constants in services/dashboard_helpers.py."""

    def test_log_constants_exist(self):
        """Verify all dashboard_helpers log constants are importable."""
        from custom_components.ev_trip_planner.services.dashboard_helpers import (
            _LOG_LEGACY_STATIC_PATHS,
            _LOG_PANEL_REG_FAILED,
            _LOG_PANEL_REG_FALSE,
            _LOG_STATIC_PATHS_CANT_REG,
            _LOG_STATIC_PATHS_REGISTERED,
        )

        for name, val in [
            ("_LOG_LEGACY_STATIC_PATHS", _LOG_LEGACY_STATIC_PATHS),
            ("_LOG_STATIC_PATHS_CANT_REG", _LOG_STATIC_PATHS_CANT_REG),
            ("_LOG_STATIC_PATHS_REGISTERED", _LOG_STATIC_PATHS_REGISTERED),
            ("_LOG_PANEL_REG_FALSE", _LOG_PANEL_REG_FALSE),
            ("_LOG_PANEL_REG_FAILED", _LOG_PANEL_REG_FAILED),
        ]:
            assert isinstance(val, str) and val, f"{name} must be non-empty string"

    def test_legacy_static_paths_format(self):
        """_LOG_LEGACY_STATIC_PATHS has one %s placeholder."""
        from custom_components.ev_trip_planner.services.dashboard_helpers import (
            _LOG_LEGACY_STATIC_PATHS,
        )

        assert "%s" in _LOG_LEGACY_STATIC_PATHS
        result = _LOG_LEGACY_STATIC_PATHS % "early"
        assert "early" in result

    def test_static_paths_cant_reg_format(self):
        """_LOG_STATIC_PATHS_CANT_REG has two %s placeholders."""
        from custom_components.ev_trip_planner.services.dashboard_helpers import (
            _LOG_STATIC_PATHS_CANT_REG,
        )

        assert _LOG_STATIC_PATHS_CANT_REG.count("%s") >= 2
        result = _LOG_STATIC_PATHS_CANT_REG % ("early", "hass.http is None")
        assert "early" in result
        assert "hass.http is None" in result

    def test_static_paths_registered_format(self):
        """_LOG_STATIC_PATHS_REGISTERED has one %d placeholder."""
        from custom_components.ev_trip_planner.services.dashboard_helpers import (
            _LOG_STATIC_PATHS_REGISTERED,
        )

        assert "%d" in _LOG_STATIC_PATHS_REGISTERED
        result = _LOG_STATIC_PATHS_REGISTERED % 3
        assert "3" in result

    def test_panel_reg_false_format(self):
        """_LOG_PANEL_REG_FALSE has one %s placeholder."""
        from custom_components.ev_trip_planner.services.dashboard_helpers import (
            _LOG_PANEL_REG_FALSE,
        )

        assert "%s" in _LOG_PANEL_REG_FALSE
        result = _LOG_PANEL_REG_FALSE % "My Car"
        assert "My Car" in result

    def test_panel_reg_failed_format(self):
        """_LOG_PANEL_REG_FAILED has two %s and one exception placeholder."""
        from custom_components.ev_trip_planner.services.dashboard_helpers import (
            _LOG_PANEL_REG_FAILED,
        )

        assert _LOG_PANEL_REG_FAILED.count("%s") >= 2
        result = _LOG_PANEL_REG_FAILED % ("My Car", Exception("fail"))
        assert "My Car" in result


class TestHandlerFactoriesLogConstants:
    """Test US-5 log constants in services/_handler_factories.py."""

    def _assert_all_non_empty(self, items):
        """Assert each (name, value) pair is a non-empty string."""
        for name, val in items:
            assert isinstance(val, str) and val, f"{name} must be non-empty string"

    def test_log_constants_exist(self):
        """Verify all _handler_factories log constants are importable."""
        from custom_components.ev_trip_planner.services._handler_factories import (
            _LOG_CALL_DATA,
            _LOG_CALL_DATA_TRIP_GET,
            _LOG_CREATED_PUNCTUAL,
            _LOG_CREATED_RECURRING,
            _LOG_ENTRY_NOT_FOUND,
            _LOG_ERROR_GETTING_TRIP,
            _LOG_ERROR_LISTING,
            _LOG_FINDING_ALL_TO_FIND_ID,
            _LOG_FIRST_PUNCTUAL,
            _LOG_FIRST_RECURRING,
            _LOG_FOUND_TRIP,
            _LOG_FOUND_TRIPS_COUNT,
            _LOG_GETTING_ALL_TO_FIND,
            _LOG_GETTING_PUNCTUAL,
            _LOG_GETTING_RECURRING,
            _LOG_GOT_PUNCTUAL,
            _LOG_GOT_RECURRING,
            _LOG_HANDLER_GET_MANAGER_OK,
            _LOG_HANDLER_TRIP_GET_CALLED,
            _LOG_HANDLER_TRIP_LIST_CALLED,
            _LOG_HANDLER_TRIP_LIST_RESULT,
            _LOG_INVALID_TRIP_TYPE,
            _LOG_PUNCTUAL_COUNT,
            _LOG_PUNCTUAL_TRIP_ENTRY,
            _LOG_PUNCTUAL_TRIPS_BEFORE,
            _LOG_RECURRING_COUNT,
            _LOG_RECURRING_TRIP_ENTRY,
            _LOG_RECURRING_TRIPS_BEFORE,
            _LOG_REFRESH,
            _LOG_RETRIEVED,
            _LOG_SEARCHING_FOR_ID,
            _LOG_TOTAL_COUNT,
            _LOG_TRIP_GET_NOT_FOUND,
            _LOG_TRIP_GET_SERVICE_CALLED,
            _LOG_TRIP_GET_SUCCESS,
            _LOG_TRIP_LIST_SERVICE_CALLED,
            _LOG_UPDATE_FAILED,
            _LOG_UPDATING_TRIP,
        )

        self._assert_all_non_empty([
            ("_LOG_HANDLER_TRIP_LIST_CALLED", _LOG_HANDLER_TRIP_LIST_CALLED),
            ("_LOG_HANDLER_GET_MANAGER_OK", _LOG_HANDLER_GET_MANAGER_OK),
            ("_LOG_HANDLER_TRIP_GET_CALLED", _LOG_HANDLER_TRIP_GET_CALLED),
            ("_LOG_HANDLER_TRIP_LIST_RESULT", _LOG_HANDLER_TRIP_LIST_RESULT),
            ("_LOG_REFRESH", _LOG_REFRESH),
            ("_LOG_CALL_DATA", _LOG_CALL_DATA),
            ("_LOG_TRIP_LIST_SERVICE_CALLED", _LOG_TRIP_LIST_SERVICE_CALLED),
            ("_LOG_RECURRING_TRIPS_BEFORE", _LOG_RECURRING_TRIPS_BEFORE),
            ("_LOG_PUNCTUAL_TRIPS_BEFORE", _LOG_PUNCTUAL_TRIPS_BEFORE),
            ("_LOG_GETTING_RECURRING", _LOG_GETTING_RECURRING),
            ("_LOG_GOT_RECURRING", _LOG_GOT_RECURRING),
            ("_LOG_GETTING_PUNCTUAL", _LOG_GETTING_PUNCTUAL),
            ("_LOG_GOT_PUNCTUAL", _LOG_GOT_PUNCTUAL),
            ("_LOG_RETRIEVED", _LOG_RETRIEVED),
            ("_LOG_RECURRING_TRIP_ENTRY", _LOG_RECURRING_TRIP_ENTRY),
            ("_LOG_PUNCTUAL_TRIP_ENTRY", _LOG_PUNCTUAL_TRIP_ENTRY),
            ("_LOG_RECURRING_COUNT", _LOG_RECURRING_COUNT),
            ("_LOG_PUNCTUAL_COUNT", _LOG_PUNCTUAL_COUNT),
            ("_LOG_TOTAL_COUNT", _LOG_TOTAL_COUNT),
            ("_LOG_FIRST_RECURRING", _LOG_FIRST_RECURRING),
            ("_LOG_FIRST_PUNCTUAL", _LOG_FIRST_PUNCTUAL),
            ("_LOG_ERROR_LISTING", _LOG_ERROR_LISTING),
            ("_LOG_UPDATING_TRIP", _LOG_UPDATING_TRIP),
            ("_LOG_ENTRY_NOT_FOUND", _LOG_ENTRY_NOT_FOUND),
            ("_LOG_UPDATE_FAILED", _LOG_UPDATE_FAILED),
            ("_LOG_CREATED_RECURRING", _LOG_CREATED_RECURRING),
            ("_LOG_CREATED_PUNCTUAL", _LOG_CREATED_PUNCTUAL),
            ("_LOG_INVALID_TRIP_TYPE", _LOG_INVALID_TRIP_TYPE),
            ("_LOG_CALL_DATA_TRIP_GET", _LOG_CALL_DATA_TRIP_GET),
            ("_LOG_TRIP_GET_SERVICE_CALLED", _LOG_TRIP_GET_SERVICE_CALLED),
            ("_LOG_TRIP_GET_SUCCESS", _LOG_TRIP_GET_SUCCESS),
            ("_LOG_TRIP_GET_NOT_FOUND", _LOG_TRIP_GET_NOT_FOUND),
            ("_LOG_GETTING_ALL_TO_FIND", _LOG_GETTING_ALL_TO_FIND),
            ("_LOG_FOUND_TRIPS_COUNT", _LOG_FOUND_TRIPS_COUNT),
            ("_LOG_SEARCHING_FOR_ID", _LOG_SEARCHING_FOR_ID),
            ("_LOG_FOUND_TRIP", _LOG_FOUND_TRIP),
            ("_LOG_ERROR_GETTING_TRIP", _LOG_ERROR_GETTING_TRIP),
            ("_LOG_FINDING_ALL_TO_FIND_ID", _LOG_FINDING_ALL_TO_FIND_ID),
        ])

    def test_refresh_format(self):
        """_LOG_REFRESH has one %s placeholder."""
        from custom_components.ev_trip_planner.services._handler_factories import (
            _LOG_REFRESH,
        )

        assert "%s" in _LOG_REFRESH
        result = _LOG_REFRESH % "My Car"
        assert "My Car" in result

    def test_trip_list_service_called_format(self):
        """_LOG_TRIP_LIST_SERVICE_CALLED has one %s placeholder."""
        from custom_components.ev_trip_planner.services._handler_factories import (
            _LOG_TRIP_LIST_SERVICE_CALLED,
        )

        assert "%s" in _LOG_TRIP_LIST_SERVICE_CALLED
        result = _LOG_TRIP_LIST_SERVICE_CALLED % "My Car"
        assert "My Car" in result

    def test_recurring_trips_before_format(self):
        """_LOG_RECURRING_TRIPS_BEFORE has one %d placeholder."""
        from custom_components.ev_trip_planner.services._handler_factories import (
            _LOG_RECURRING_TRIPS_BEFORE,
        )

        assert "%d" in _LOG_RECURRING_TRIPS_BEFORE
        result = _LOG_RECURRING_TRIPS_BEFORE % 3
        assert "3" in result

    def test_retrieved_format(self):
        """_LOG_RETRIEVED has three placeholders."""
        from custom_components.ev_trip_planner.services._handler_factories import (
            _LOG_RETRIEVED,
        )

        result = _LOG_RETRIEVED % (3, 1, "vehicle_1")
        assert "3" in result
        assert "1" in result
        assert "vehicle_1" in result

    def test_recurring_trip_entry_format(self):
        """_LOG_RECURRING_TRIP_ENTRY has four placeholders."""
        from custom_components.ev_trip_planner.services._handler_factories import (
            _LOG_RECURRING_TRIP_ENTRY,
        )

        result = _LOG_RECURRING_TRIP_ENTRY % (1, "id1", "recurrente", "true")
        assert "1" in result
        assert "id1" in result

    def test_punctual_trip_entry_format(self):
        """_LOG_PUNCTUAL_TRIP_ENTRY has four placeholders."""
        from custom_components.ev_trip_planner.services._handler_factories import (
            _LOG_PUNCTUAL_TRIP_ENTRY,
        )

        result = _LOG_PUNCTUAL_TRIP_ENTRY % (1, "id1", "puntual", "pending")
        assert "1" in result
        assert "id1" in result

    def test_error_listing_format(self):
        """_LOG_ERROR_LISTING has two %s placeholders."""
        from custom_components.ev_trip_planner.services._handler_factories import (
            _LOG_ERROR_LISTING,
        )

        assert _LOG_ERROR_LISTING.count("%s") >= 2
        result = _LOG_ERROR_LISTING % ("vehicle_1", Exception("fail"))
        assert "vehicle_1" in result

    def test_updating_trip_format(self):
        """_LOG_UPDATING_TRIP has three %s placeholders."""
        from custom_components.ev_trip_planner.services._handler_factories import (
            _LOG_UPDATING_TRIP,
        )

        assert _LOG_UPDATING_TRIP.count("%s") >= 3
        result = _LOG_UPDATING_TRIP % ("id1", "vehicle_1", {"key": "val"})
        assert "id1" in result
        assert "vehicle_1" in result

    def test_entry_not_found_format(self):
        """_LOG_ENTRY_NOT_FOUND has one %s placeholder."""
        from custom_components.ev_trip_planner.services._handler_factories import (
            _LOG_ENTRY_NOT_FOUND,
        )

        assert "%s" in _LOG_ENTRY_NOT_FOUND
        result = _LOG_ENTRY_NOT_FOUND % "vehicle_1"
        assert "vehicle_1" in result

    def test_update_failed_format(self):
        """_LOG_UPDATE_FAILED has one %s placeholder."""
        from custom_components.ev_trip_planner.services._handler_factories import (
            _LOG_UPDATE_FAILED,
        )

        assert "%s" in _LOG_UPDATE_FAILED
        result = _LOG_UPDATE_FAILED % Exception("fail")
        assert "fail" in result

    def test_created_recurring_format(self):
        """_LOG_CREATED_RECURRING has four %s placeholders."""
        from custom_components.ev_trip_planner.services._handler_factories import (
            _LOG_CREATED_RECURRING,
        )

        assert _LOG_CREATED_RECURRING.count("%s") >= 4
        result = _LOG_CREATED_RECURRING % ("vehicle_1", "Monday", "07:00", "50")
        assert "vehicle_1" in result

    def test_created_punctual_format(self):
        """_LOG_CREATED_PUNCTUAL has three %s placeholders."""
        from custom_components.ev_trip_planner.services._handler_factories import (
            _LOG_CREATED_PUNCTUAL,
        )

        assert _LOG_CREATED_PUNCTUAL.count("%s") >= 3
        result = _LOG_CREATED_PUNCTUAL % ("vehicle_1", "2024-01-01", "50")
        assert "vehicle_1" in result

    def test_invalid_trip_type_format(self):
        """_LOG_INVALID_TRIP_TYPE has two %s placeholders."""
        from custom_components.ev_trip_planner.services._handler_factories import (
            _LOG_INVALID_TRIP_TYPE,
        )

        assert _LOG_INVALID_TRIP_TYPE.count("%s") >= 2
        result = _LOG_INVALID_TRIP_TYPE % ("bad", "vehicle_1")
        assert "bad" in result
        assert "vehicle_1" in result

    def test_trip_get_service_called_format(self):
        """_LOG_TRIP_GET_SERVICE_CALLED has two %s placeholders."""
        from custom_components.ev_trip_planner.services._handler_factories import (
            _LOG_TRIP_GET_SERVICE_CALLED,
        )

        assert _LOG_TRIP_GET_SERVICE_CALLED.count("%s") >= 2
        result = _LOG_TRIP_GET_SERVICE_CALLED % ("My Car", "trip_1")
        assert "My Car" in result
        assert "trip_1" in result

    def test_found_trips_count_format(self):
        """_LOG_FOUND_TRIPS_COUNT has two %d placeholders."""
        from custom_components.ev_trip_planner.services._handler_factories import (
            _LOG_FOUND_TRIPS_COUNT,
        )

        result = _LOG_FOUND_TRIPS_COUNT % (3, 1)
        assert "3" in result
        assert "1" in result

    def test_searching_for_id_format(self):
        """_LOG_SEARCHING_FOR_ID has two placeholders."""
        from custom_components.ev_trip_planner.services._handler_factories import (
            _LOG_SEARCHING_FOR_ID,
        )

        result = _LOG_SEARCHING_FOR_ID % (4, "trip_1")
        assert "4" in result
        assert "trip_1" in result

    def test_error_getting_trip_format(self):
        """_LOG_ERROR_GETTING_TRIP has three placeholders."""
        from custom_components.ev_trip_planner.services._handler_factories import (
            _LOG_ERROR_GETTING_TRIP,
        )

        result = _LOG_ERROR_GETTING_TRIP % ("trip_1", "vehicle_1", Exception("fail"))
        assert "trip_1" in result
        assert "vehicle_1" in result
