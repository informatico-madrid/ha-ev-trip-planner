"""Tests for sensor/_helpers.py pure helper functions.

Covers all extracted pure helpers:
- format_window_time
- get_trip_data
- determine_trip_estado
- build_trip_attributes
- build_emhass_zeroed_attributes
- filter_emhass_attributes
- build_emhass_attributes
- extract_active_trips
- extract_matrix_and_count
- collect_deferrable_arrays
- build_aggregate_result
- scan_sensors_for_entities
- find_trip_entity_ids

Follows NFR-8 (multi-assert): every test asserts on all output fields, not just
truthiness.
"""

from __future__ import annotations

from datetime import datetime

from custom_components.ev_trip_planner.const import (
    TRIP_EMHASS_ATTR_KEYS,
)
from custom_components.ev_trip_planner.definitions import TripSensorEntityDescription
from custom_components.ev_trip_planner.sensor._helpers import (
    build_aggregate_result,
    build_emhass_attributes,
    build_emhass_zeroed_attributes,
    build_trip_attributes,
    collect_deferrable_arrays,
    determine_trip_estado,
    extract_active_trips,
    extract_matrix_and_count,
    filter_emhass_attributes,
    find_entity_id_by_trip,
    format_window_time,
    get_trip_data,
    scan_sensors_for_entities,
)

# =============================================================================
# format_window_time
# =============================================================================


class TestFormatWindowTime:
    """Test format_window_time pure helper."""

    def test_datetime(self):
        dt = datetime(2026, 5, 15, 14, 30)
        assert format_window_time(dt) == "14:30"

    def test_iso_string(self):
        assert format_window_time("2026-05-15T07:45:00") == "07:45"

    def test_iso_string_short(self):
        # "09:30" alone is not a valid ISO datetime, so fromisoformat raises
        assert format_window_time("09:30") is None

    def test_none_returns_none(self):
        assert format_window_time(None) is None

    def test_int_returns_none(self):
        assert format_window_time(123) is None

    def test_invalid_string_returns_none(self):
        assert format_window_time("not-a-date") is None

    def test_midnight(self):
        dt = datetime(2026, 1, 1, 0, 0)
        assert format_window_time(dt) == "00:00"

    def test_leading_zero_preserved(self):
        dt = datetime(2026, 1, 1, 9, 5)
        assert format_window_time(dt) == "09:05"


# =============================================================================
# get_trip_data
# =============================================================================


class TestGetTripData:
    """Test get_trip_data pure helper."""

    def test_coordinator_none(self):
        assert get_trip_data(None, "t1") == {}

    def test_from_recurring(self):
        data = {
            "recurring_trips": {"t1": {"id": "t1", "tipo": "recurrente", "km": 50.0}},
            "punctual_trips": {},
        }
        result = get_trip_data(data, "t1")
        assert result == {"id": "t1", "tipo": "recurrente", "km": 50.0}

    def test_from_punctual(self):
        data = {
            "recurring_trips": {},
            "punctual_trips": {"t1": {"id": "t1", "tipo": "puntual"}},
        }
        result = get_trip_data(data, "t1")
        assert result == {"id": "t1", "tipo": "puntual"}

    def test_not_found(self):
        data = {"recurring_trips": {}, "punctual_trips": {}}
        assert get_trip_data(data, "nonexistent") == {}

    def test_recurring_takes_precedence(self):
        data = {
            "recurring_trips": {"t1": {"source": "recurring"}},
            "punctual_trips": {"t1": {"source": "punctual"}},
        }
        assert get_trip_data(data, "t1")["source"] == "recurring"

    def test_empty_recurring_falls_to_punctual(self):
        data = {
            "recurring_trips": {},
            "punctual_trips": {"t1": {"id": "t1", "source": "punctual"}},
        }
        assert get_trip_data(data, "t1")["source"] == "punctual"

    def test_missing_recurring_key_uses_punctual(self):
        data = {"punctual_trips": {"t1": {"id": "t1"}}}
        assert get_trip_data(data, "t1")["id"] == "t1"

    def test_missing_punctual_key_returns_empty(self):
        data = {"recurring_trips": {}}
        assert get_trip_data(data, "t1") == {}


# =============================================================================
# determine_trip_estado
# =============================================================================


class TestDetermineTripEstado:
    """Test determine_trip_estado pure helper."""

    def test_recurrente(self):
        assert determine_trip_estado({"tipo": "recurrente"}) == "recurrente"

    def test_punctual_returns_estado(self):
        assert (
            determine_trip_estado({"tipo": "puntual", "estado": "active"}) == "active"
        )

    def test_punctual_defaults_to_pendiente(self):
        assert determine_trip_estado({"tipo": "puntual"}) == "pendiente"

    def test_empty_returns_none(self):
        assert determine_trip_estado({}) is None

    def test_non_punctual_defaults_to_recurrente(self):
        """Non-punctual types (including unknown) return 'recurrente'."""
        assert determine_trip_estado({"tipo": "unknown"}) == "recurrente"
        assert determine_trip_estado({"tipo": "recurrente"}) == "recurrente"

    def test_none_coordinator_data_returns_none(self):
        assert determine_trip_estado({}) is None


# =============================================================================
# build_trip_attributes
# =============================================================================


class TestBuildTripAttributes:
    """Test build_trip_attributes pure helper.

    NFR-8: multi-assert on every attribute key.
    """

    def test_all_fields_full_data(self):
        data = {
            "id": "t1",
            "tipo": "recurrente",
            "descripcion": "Morning charge",
            "km": 25.0,
            "kwh": 5.5,
            "hora": "07:00",
            "activo": True,
            "estado": "active",
        }
        attrs = build_trip_attributes(data)
        assert attrs["trip_id"] == "t1"
        assert attrs["trip_type"] == "recurrente"
        assert attrs["descripcion"] == "Morning charge"
        assert attrs["km"] == 25.0
        assert attrs["kwh"] == 5.5
        assert attrs["fecha_hora"] == "07:00"
        assert attrs["activo"] is True
        assert attrs["estado"] == "active"

    def test_all_fields_datetime_key(self):
        """Should prefer 'datetime' over 'hora'."""
        data = {
            "id": "t1",
            "datetime": "2026-05-15T14:30:00",
        }
        attrs = build_trip_attributes(data)
        assert attrs["fecha_hora"] == "2026-05-15T14:30:00"
        assert attrs["trip_id"] == "t1"
        assert attrs["trip_type"] == "unknown"
        assert attrs["descripcion"] == ""
        assert attrs["km"] == 0.0
        assert attrs["kwh"] == 0.0
        assert attrs["activo"] is True
        assert attrs["estado"] == "pendiente"

    def test_empty_data_returns_empty(self):
        assert build_trip_attributes({}) == {}

    def test_all_defaults(self):
        attrs = build_trip_attributes({"id": "t1"})
        assert attrs["trip_type"] == "unknown"
        assert attrs["descripcion"] == ""
        assert attrs["km"] == 0.0
        assert attrs["kwh"] == 0.0
        assert attrs["fecha_hora"] == ""
        assert attrs["activo"] is True
        assert attrs["estado"] == "pendiente"

    def test_all_exactly_eight_keys(self):
        """Ensure no extra keys and no missing keys."""
        data = {
            "id": "t1",
            "tipo": "recurrente",
            "descripcion": "",
            "km": 0.0,
            "kwh": 0.0,
            "hora": "",
            "activo": True,
            "estado": "active",
        }
        attrs = build_trip_attributes(data)
        assert set(attrs.keys()) == {
            "trip_id",
            "trip_type",
            "descripcion",
            "km",
            "kwh",
            "fecha_hora",
            "activo",
            "estado",
        }
        assert len(attrs) == 8


# =============================================================================
# build_emhass_zeroed_attributes
# =============================================================================


class TestBuildEmhassZeroedAttributes:
    """Test build_emhass_zeroed_attributes pure helper."""

    def test_all_nine_keys(self):
        attrs = build_emhass_zeroed_attributes("t1")
        assert set(attrs.keys()) == {
            "def_total_hours",
            "P_deferrable_nom",
            "def_start_timestep",
            "def_end_timestep",
            "power_profile_watts",
            "trip_id",
            "emhass_index",
            "kwh_needed",
            "deadline",
        }
        assert len(attrs) == 9

    def test_correct_defaults(self):
        attrs = build_emhass_zeroed_attributes("x")
        assert attrs["def_total_hours"] == 0.0
        assert attrs["P_deferrable_nom"] == 0.0
        assert attrs["def_start_timestep"] == 0
        assert attrs["def_end_timestep"] == 24
        assert attrs["power_profile_watts"] == []
        assert attrs["trip_id"] == "x"
        assert attrs["emhass_index"] == -1
        assert attrs["kwh_needed"] == 0.0
        assert attrs["deadline"] is None


# =============================================================================
# filter_emhass_attributes
# =============================================================================


class TestFilterEmhassAttributes:
    """Test filter_emhass_attributes pure helper."""

    def test_filters_only_allowed_keys(self):
        data = {
            "emhass_index": 5,
            "def_total_hours": 3.0,
            "secret_key": "should_not_appear",
            "another_extra": 999,
        }
        attrs = filter_emhass_attributes(data)
        for key in attrs:
            assert key in TRIP_EMHASS_ATTR_KEYS
        assert "secret_key" not in attrs
        assert "another_extra" not in attrs
        assert attrs["emhass_index"] == 5
        assert attrs["def_total_hours"] == 3.0

    def test_empty_input(self):
        assert filter_emhass_attributes({}) == {}

    def test_all_keys_included_when_present(self):
        data = {k: i for i, k in enumerate(TRIP_EMHASS_ATTR_KEYS)}
        attrs = filter_emhass_attributes(data)
        assert set(attrs.keys()) == set(TRIP_EMHASS_ATTR_KEYS)
        for i, k in enumerate(TRIP_EMHASS_ATTR_KEYS):
            assert attrs[k] == i


# =============================================================================
# build_emhass_attributes
# =============================================================================


class TestBuildEmhassAttributes:
    """Test build_emhass_attributes pure helper."""

    def test_coordinator_none(self):
        attrs = build_emhass_attributes(None, "t1")
        assert attrs["emhass_index"] == -1
        assert attrs["trip_id"] == "t1"

    def test_trip_not_found(self):
        data = {"per_trip_emhass_params": {"other": {"emhass_index": 1}}}
        attrs = build_emhass_attributes(data, "t1")
        assert attrs["emhass_index"] == -1
        assert attrs["trip_id"] == "t1"

    def test_trip_found_filtered(self):
        data = {
            "per_trip_emhass_params": {
                "t1": {
                    "emhass_index": 3,
                    "def_total_hours": 2.5,
                    "leaked": "value",
                }
            }
        }
        attrs = build_emhass_attributes(data, "t1")
        assert attrs["emhass_index"] == 3
        assert attrs["def_total_hours"] == 2.5
        assert "leaked" not in attrs


# =============================================================================
# extract_active_trips
# =============================================================================


class TestExtractActiveTrips:
    """Test extract_active_trips pure helper."""

    def test_filters_inactive(self):
        params = {
            "t1": {"activo": True, "def_start_timestep": 5, "emhass_index": 1},
            "t2": {"activo": False, "def_start_timestep": 10, "emhass_index": 2},
        }
        result = extract_active_trips(params)
        assert len(result) == 1
        assert result[0]["emhass_index"] == 1

    def test_sorts_by_timestep(self):
        params = {
            "t1": {"activo": True, "def_start_timestep": 10, "emhass_index": 1},
            "t2": {"activo": True, "def_start_timestep": 5, "emhass_index": 2},
        }
        result = extract_active_trips(params)
        assert [r["emhass_index"] for r in result] == [2, 1]

    def test_sorts_by_emhass_index_when_equal(self):
        params = {
            "t1": {"activo": True, "def_start_timestep": 5, "emhass_index": 3},
            "t2": {"activo": True, "def_start_timestep": 5, "emhass_index": 1},
        }
        result = extract_active_trips(params)
        assert [r["emhass_index"] for r in result] == [1, 3]

    def test_empty_input(self):
        assert extract_active_trips({}) == []

    def test_no_active_returns_empty(self):
        params = {"t1": {"activo": False}, "t2": {"activo": False}}
        assert extract_active_trips(params) == []


# =============================================================================
# extract_matrix_and_count
# =============================================================================


class TestExtractMatrixAndCount:
    """Test extract_matrix_and_count pure helper."""

    def test_concatenates_matrices(self):
        active = [
            {"p_deferrable_matrix": [100.0, 200.0]},
            {"p_deferrable_matrix": [300.0]},
        ]
        matrix, count = extract_matrix_and_count(active)
        assert matrix == [100.0, 200.0, 300.0]
        assert count == 3

    def test_missing_matrix_increments_count(self):
        active = [
            {"p_deferrable_matrix": [100.0]},
            {},
        ]
        matrix, count = extract_matrix_and_count(active)
        assert matrix == [100.0]
        assert count == 2

    def test_empty_input(self):
        matrix, count = extract_matrix_and_count([])
        assert matrix == []
        assert count == 0

    def test_key_present_but_none_does_not_increment_count(self):
        """Key 'p_deferrable_matrix' present but None: count must NOT increment.

        Kills mutmut_11 (string -> "XXp_deferrable_matrixXX") and
        mutmut_12 (string -> "P_DEFERRABLE_MATRIX"):

        Original logic: if p_matrix (falsy) → elif "p_deferrable_matrix" not in params
          → False (key IS present) → count stays 0.
        Mutant logic: elif "XXp_deferrable_matrixXX" not in params
          → True (mutated key is never present) → count incorrectly becomes 1.
        """
        active = [{"p_deferrable_matrix": None}]
        matrix, count = extract_matrix_and_count(active)
        assert matrix == []
        assert count == 0, (
            f"Expected count=0 when p_deferrable_matrix key is present but None, got {count}"
        )

    def test_key_present_but_empty_list_does_not_increment_count(self):
        """Key 'p_deferrable_matrix' present with empty list: count must NOT increment.

        Kills same mutmut_11/12 mutations.
        An empty list is falsy, so p_matrix check fails, falls through to elif.
        """
        active = [{"p_deferrable_matrix": []}]
        matrix, count = extract_matrix_and_count(active)
        assert matrix == []
        assert count == 0, (
            f"Expected count=0 when p_deferrable_matrix is empty list, got {count}"
        )

    def test_key_absent_increments_count_not_key_present_none(self):
        """Distinguish: key absent → count+1; key present with None → count stays.

        Kills both mutations by testing the exact boundary:
        - {'other_key': 1}: p_deferrable_matrix NOT in params → count=1 (correct)
        - {'p_deferrable_matrix': None}: p_deferrable_matrix IS in params → count=0 (correct)
        """
        active_absent = [{"other_key": 1}]
        active_present_none = [{"p_deferrable_matrix": None}]

        _, count_absent = extract_matrix_and_count(active_absent)
        _, count_present_none = extract_matrix_and_count(active_present_none)

        assert count_absent == 1, f"Expected count=1 for absent key, got {count_absent}"
        assert count_present_none == 0, (
            f"Expected count=0 for present-but-None key, got {count_present_none}"
        )


# =============================================================================
# collect_deferrable_arrays
# =============================================================================


class TestCollectDeferrableArrays:
    """Test collect_deferrable_arrays pure helper.

    NFR-8: multi-assert on all four arrays.
    """

    def test_all_arrays_correct(self):
        active = [
            {
                "def_total_hours": 2.0,
                "power_watts": 5000,
                "def_start_timestep": 5,
                "def_end_timestep": 20,
            },
            {
                "def_total_hours": 3.0,
                "power_watts": 7000,
                "def_start_timestep": 10,
                "def_end_timestep": 22,
            },
        ]
        result = collect_deferrable_arrays(active)
        assert result["def_total_hours_array"] == [2.0, 3.0]
        assert result["p_deferrable_nom_array"] == [5000, 7000]
        assert result["def_start_timestep_array"] == [5, 10]
        assert result["def_end_timestep_array"] == [20, 22]

    def test_zero_defaults(self):
        result = collect_deferrable_arrays([{}])
        assert result["def_total_hours_array"] == [0]
        assert result["p_deferrable_nom_array"] == [0]
        assert result["def_start_timestep_array"] == [0]
        assert result["def_end_timestep_array"] == [0]

    def test_empty_input(self):
        result = collect_deferrable_arrays([])
        assert result["def_total_hours_array"] == []
        assert result["p_deferrable_nom_array"] == []
        assert result["def_start_timestep_array"] == []
        assert result["def_end_timestep_array"] == []


# =============================================================================
# build_aggregate_result
# =============================================================================


class TestBuildAggregateResult:
    """Test build_aggregate_result pure helper."""

    def test_includes_number_of_loads(self):
        result = build_aggregate_result([], 3, {})
        assert result["number_of_deferrable_loads"] == 3

    def test_includes_matrix_when_present(self):
        result = build_aggregate_result([[100]], 2, {"a": [1]})
        assert result["p_deferrable_matrix"] == [[100]]
        assert result["number_of_deferrable_loads"] == 2
        assert result["a"] == [1]

    def test_excludes_matrix_when_empty(self):
        result = build_aggregate_result([], 0, {"a": [1]})
        assert "p_deferrable_matrix" not in result
        assert result["number_of_deferrable_loads"] == 0

    def test_arrays_update_result(self):
        arrays = {"def_total_hours_array": [1, 2]}
        result = build_aggregate_result([], 1, arrays)
        assert result["def_total_hours_array"] == [1, 2]


# =============================================================================
# scan_sensors_for_entities
# =============================================================================


class TestScanSensorsForEntities:
    """Test scan_sensors_for_entities pure helper."""

    def test_filters_by_exists_fn(self):
        """Only descriptions with exists_fn returning True are included."""
        desc1 = TripSensorEntityDescription(
            key="always_true",
            exists_fn=lambda data: True,
        )
        desc2 = TripSensorEntityDescription(
            key="always_false",
            exists_fn=lambda data: False,
        )
        # Temporarily replace TRIP_SENSORS
        import custom_components.ev_trip_planner.sensor._helpers as helpers_mod

        orig = helpers_mod.TRIP_SENSORS
        helpers_mod.TRIP_SENSORS = (desc1, desc2)
        try:
            result = scan_sensors_for_entities({})
            assert len(result) == 1
            assert result[0].key == "always_true"
        finally:
            helpers_mod.TRIP_SENSORS = orig

    def test_empty_coordinator_data(self):
        desc = TripSensorEntityDescription(
            key="k",
            exists_fn=lambda data: data is not None and len(data) > 0,
        )
        import custom_components.ev_trip_planner.sensor._helpers as helpers_mod

        orig = helpers_mod.TRIP_SENSORS
        helpers_mod.TRIP_SENSORS = (desc,)
        try:
            result = scan_sensors_for_entities({})
            assert len(result) == 0
        finally:
            helpers_mod.TRIP_SENSORS = orig


# =============================================================================
# find_trip_entity_ids
# =============================================================================


class TestFindEntityIdByTrip:
    """Test find_entity_id_by_trip pure helper."""

    def test_trip_match(self):
        assert find_entity_id_by_trip("sensor.ev_trip_planner_e1_trip_t1", "t1") is True

    def test_no_match(self):
        assert (
            find_entity_id_by_trip("sensor.ev_trip_planner_e1_trip_t2", "t1") is False
        )

    def test_emhass_match(self):
        assert (
            find_entity_id_by_trip(
                "sensor.ev_trip_planner_e1_emhass_t1", "t1", match_emhass=True
            )
            is True
        )

    def test_emhass_no_match(self):
        assert (
            find_entity_id_by_trip(
                "sensor.ev_trip_planner_e1_trip_t1", "t1", match_emhass=True
            )
            is False
        )

    def test_trip_id_substring(self):
        """Trip ID substring matching — 't1' should match in 't10' too."""
        assert (
            find_entity_id_by_trip("sensor.ev_trip_planner_e1_trip_t10", "t1") is True
        )

    def test_empty_entity_id(self):
        assert find_entity_id_by_trip("", "t1") is False
