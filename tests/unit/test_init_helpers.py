"""Tests for __init_helpers.py — US-5 extracted pure helpers.

Covers validate_runtime_fields, build_cache_report, CacheReport dataclass.
Multi-assert: every output field tested independently.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

import custom_components.ev_trip_planner.__init_helpers as ih


class TestValidateRuntimeFields:
    """Test validate_runtime_fields with all field combinations."""

    def test_all_fields_present(self):
        """All four fields present -> True."""
        rt = MagicMock()
        rt.trip_manager = MagicMock()
        rt.emhass_adapter = MagicMock()
        rt.coordinator = MagicMock()
        assert ih.validate_runtime_fields(rt) is True

    def test_none_runtime_data(self):
        """None input -> False."""
        assert ih.validate_runtime_fields(None) is False

    def test_trip_manager_none(self):
        """trip_manager=None -> False."""
        rt = MagicMock()
        rt.trip_manager = None
        rt.emhass_adapter = MagicMock()
        rt.coordinator = MagicMock()
        assert ih.validate_runtime_fields(rt) is False

    def test_emhass_adapter_none(self):
        """emhass_adapter=None -> False."""
        rt = MagicMock()
        rt.trip_manager = MagicMock()
        rt.emhass_adapter = None
        rt.coordinator = MagicMock()
        assert ih.validate_runtime_fields(rt) is False

    def test_coordinator_none(self):
        """coordinator=None -> False."""
        rt = MagicMock()
        rt.trip_manager = MagicMock()
        rt.emhass_adapter = MagicMock()
        rt.coordinator = None
        assert ih.validate_runtime_fields(rt) is False

    def test_all_fields_none(self):
        """All fields None -> False."""
        rt = MagicMock()
        rt.trip_manager = None
        rt.emhass_adapter = None
        rt.coordinator = None
        assert ih.validate_runtime_fields(rt) is False

    def test_multiple_missing_fields(self):
        """Multiple None fields -> False."""
        rt = MagicMock()
        rt.trip_manager = None
        rt.emhass_adapter = None
        rt.coordinator = MagicMock()
        assert ih.validate_runtime_fields(rt) is False


class TestBuildCacheReport:
    """Test build_cache_report with various cache states."""

    def test_empty_cache(self):
        """Empty cache -> zero counts."""
        adapter = MagicMock()
        adapter.get_cached_optimization_results.return_value = {
            "per_trip_emhass_params": {},
            "emhass_power_profile": [],
        }
        report = ih.build_cache_report(adapter)
        assert report.per_trip_count == 0
        assert report.power_nonzero == 0

    def test_single_trip_empty_params(self):
        """Single trip with empty params -> count=1, power=0."""
        adapter = MagicMock()
        adapter.get_cached_optimization_results.return_value = {
            "per_trip_emhass_params": {"trip_1": {}},
            "emhass_power_profile": [],
        }
        report = ih.build_cache_report(adapter)
        assert report.per_trip_count == 1
        assert report.power_nonzero == 0

    def test_multiple_trips_with_params(self):
        """Multiple trips with params -> correct per_trip count."""
        adapter = MagicMock()
        adapter.get_cached_optimization_results.return_value = {
            "per_trip_emhass_params": {
                "trip_1": {"def_start_timestep_array": [0, 1]},
                "trip_2": {"def_end_timestep_array": [2, 3]},
                "trip_3": {"def_total_hours_array": [1.5]},
            },
            "emhass_power_profile": [100, 200, 300],
        }
        report = ih.build_cache_report(adapter)
        assert report.per_trip_count == 3
        assert report.power_nonzero == 3

    def test_power_profile_zeros(self):
        """Zero power profile -> power_nonzero=0."""
        adapter = MagicMock()
        adapter.get_cached_optimization_results.return_value = {
            "per_trip_emhass_params": {},
            "emhass_power_profile": [0, 0, 0],
        }
        report = ih.build_cache_report(adapter)
        assert report.per_trip_count == 0
        assert report.power_nonzero == 0

    def test_power_profile_mixed(self):
        """Mixed positive/negative power -> correct nonzero count.

        Note: build_cache_report uses x > 0 (strictly positive), not x != 0.
        """
        adapter = MagicMock()
        adapter.get_cached_optimization_results.return_value = {
            "per_trip_emhass_params": {"t1": {}},
            "emhass_power_profile": [0, 100, -50, 0, 200, -300],
        }
        report = ih.build_cache_report(adapter)
        assert report.per_trip_count == 1
        assert report.power_nonzero == 2  # only 100, 200 are > 0 (strict)

    def test_none_params_fallback(self):
        """None per_trip_emhass_params -> count=0."""
        adapter = MagicMock()
        adapter.get_cached_optimization_results.return_value = {
            "per_trip_emhass_params": None,
            "emhass_power_profile": [100],
        }
        report = ih.build_cache_report(adapter)
        assert report.per_trip_count == 0
        assert report.power_nonzero == 1

    def test_none_power_profile_fallback(self):
        """None emhass_power_profile -> power_nonzero=0."""
        adapter = MagicMock()
        adapter.get_cached_optimization_results.return_value = {
            "per_trip_emhass_params": {"t1": {}},
            "emhass_power_profile": None,
        }
        report = ih.build_cache_report(adapter)
        assert report.per_trip_count == 1
        assert report.power_nonzero == 0


class TestCacheReportDataclass:
    """Test CacheReport frozen dataclass."""

    def test_immutability(self):
        """CacheReport is frozen — cannot modify."""
        report = ih.CacheReport(per_trip_count=5, power_nonzero=3)
        with pytest.raises(Exception):
            report.per_trip_count = 10

    def test_equality(self):
        """Same fields -> equal."""
        r1 = ih.CacheReport(per_trip_count=3, power_nonzero=2)
        r2 = ih.CacheReport(per_trip_count=3, power_nonzero=2)
        assert r1 == r2

    def test_inequality(self):
        """Different fields -> not equal."""
        r1 = ih.CacheReport(per_trip_count=3, power_nonzero=2)
        r2 = ih.CacheReport(per_trip_count=3, power_nonzero=3)
        assert r1 != r2

    def test_hashable(self):
        """CacheReport is hashable (frozen dataclass)."""
        report = ih.CacheReport(per_trip_count=1, power_nonzero=0)
        hash(report)  # Should not raise

    def test_repr(self):
        """CacheReport has meaningful repr."""
        report = ih.CacheReport(per_trip_count=2, power_nonzero=1)
        assert "CacheReport" in repr(report)
        assert "per_trip_count=2" in repr(report)
        assert "power_nonzero=1" in repr(report)


class TestModuleExports:
    """Test that __all__ exports are correct."""

    def test_all_exports(self):
        """__all__ contains exactly the expected names."""
        expected = {"CacheReport", "validate_runtime_fields", "build_cache_report"}
        assert set(ih.__all__) == expected

    def test_validate_runtime_fields_is_callable(self):
        """validate_runtime_fields is callable."""
        assert callable(ih.validate_runtime_fields)

    def test_build_cache_report_is_callable(self):
        """build_cache_report is callable."""
        assert callable(ih.build_cache_report)

    def test_cache_report_is_class(self):
        """CacheReport is a class."""
        assert isinstance(ih.CacheReport, type)
