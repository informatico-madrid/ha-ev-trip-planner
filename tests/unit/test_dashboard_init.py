"""Tests for dashboard/__init__.py — exception classes and import result.

Covers all exception hierarchies and the DashboardImportResult data class.
"""

from __future__ import annotations

from custom_components.ev_trip_planner.dashboard import (
    DashboardError,
    DashboardImportResult,
    DashboardNotFoundError,
    DashboardStorageError,
    DashboardValidationError,
)


# ---------------------------------------------------------------------------
# DashboardError
# ---------------------------------------------------------------------------


class TestDashboardError:
    """Test DashboardError base exception."""

    def test_default_message(self):
        """Error stores the message provided at construction."""
        exc = DashboardError("something broke")
        assert exc.message == "something broke"
        assert exc.args == ("something broke",)

    def test_default_details_empty_dict(self):
        """When no details provided, .details defaults to empty dict."""
        exc = DashboardError("oops")
        assert exc.details == {}

    def test_details_preserved(self):
        """Details dict is stored as-is."""
        exc = DashboardError("bad", details={"key": "val"})
        assert exc.details == {"key": "val"}

    def test_is_exception(self):
        """DashboardError is a subclass of Exception."""
        assert issubclass(DashboardError, Exception)


# ---------------------------------------------------------------------------
# DashboardNotFoundError
# ---------------------------------------------------------------------------


class TestDashboardNotFoundError:
    """Test DashboardNotFoundError exception."""

    def test_default_message(self):
        """Message includes template_file name."""
        exc = DashboardNotFoundError("missing.yaml", ["/path/a", "/path/b"])
        assert "missing.yaml" in exc.message

    def test_details_contains_template_file(self):
        """Details dict has template_file, searched_paths, error_type."""
        exc = DashboardNotFoundError("tpl.yaml", ["/a"])
        assert exc.details["template_file"] == "tpl.yaml"
        assert exc.details["searched_paths"] == ["/a"]
        assert exc.details["error_type"] == "template_not_found"

    def test_is_subclass_of_dashboard_error(self):
        """DashboardNotFoundError is a subclass of DashboardError."""
        assert issubclass(DashboardNotFoundError, DashboardError)

    def test_exception_bubbling(self):
        """Can catch DashboardNotFoundError via DashboardError."""
        try:
            raise DashboardNotFoundError("no.yaml", [])
        except DashboardError as e:
            assert isinstance(e, DashboardNotFoundError)


# ---------------------------------------------------------------------------
# DashboardValidationError
# ---------------------------------------------------------------------------


class TestDashboardValidationError:
    """Test DashboardValidationError exception."""

    def test_default_message(self):
        """Message includes validation_message."""
        exc = DashboardValidationError("bad_type", "is wrong")
        assert "is wrong" in exc.message

    def test_details_contains_error_type(self):
        """Details dict has error_type and validation_message."""
        exc = DashboardValidationError("format", "bad format")
        assert exc.details["error_type"] == "format"
        assert exc.details["validation_message"] == "bad format"

    def test_is_subclass_of_dashboard_error(self):
        assert issubclass(DashboardValidationError, DashboardError)


# ---------------------------------------------------------------------------
# DashboardStorageError
# ---------------------------------------------------------------------------


class TestDashboardStorageError:
    """Test DashboardStorageError exception."""

    def test_default_message(self):
        """Message includes storage_method and error."""
        exc = DashboardStorageError("storage_api", "disk full")
        assert "storage_api" in exc.message
        assert "disk full" in exc.message

    def test_details(self):
        """Details has storage_method, error, error_type."""
        exc = DashboardStorageError("yaml", "write failed")
        assert exc.details["storage_method"] == "yaml"
        assert exc.details["error"] == "write failed"
        assert exc.details["error_type"] == "storage_error"

    def test_is_subclass_of_dashboard_error(self):
        assert issubclass(DashboardStorageError, DashboardError)


# ---------------------------------------------------------------------------
# DashboardImportResult
# ---------------------------------------------------------------------------


class TestDashboardImportResult:
    """Test DashboardImportResult data class."""

    def test_success_defaults(self):
        """Success=True with default values for optional fields."""
        r = DashboardImportResult(success=True, vehicle_id="v1", vehicle_name="V1")
        assert r.success is True
        assert r.vehicle_id == "v1"
        assert r.vehicle_name == "V1"
        assert r.error is None
        assert r.error_details == {}
        assert r.dashboard_type == "simple"
        assert r.storage_method == "unknown"

    def test_failure_with_error(self):
        """Failure includes error message and details."""
        r = DashboardImportResult(
            success=False,
            vehicle_id="v1",
            vehicle_name="V1",
            error="template not found",
            error_details={"stage": "load"},
        )
        assert r.success is False
        assert r.error == "template not found"
        assert r.error_details == {"stage": "load"}

    def test_to_dict_success(self):
        """to_dict returns all fields as dict."""
        r = DashboardImportResult(
            success=True,
            vehicle_id="v2",
            vehicle_name="V2",
            dashboard_type="full",
            storage_method="storage_api",
        )
        d = r.to_dict()
        assert d["success"] is True
        assert d["vehicle_id"] == "v2"
        assert d["vehicle_name"] == "V2"
        assert d["dashboard_type"] == "full"
        assert d["storage_method"] == "storage_api"
        assert d["error"] is None

    def test_to_dict_failure(self):
        """to_dict for failure includes error fields."""
        r = DashboardImportResult(
            success=False,
            vehicle_id="v3",
            vehicle_name="V3",
            error="bad",
            error_details={"x": 1},
        )
        d = r.to_dict()
        assert d["success"] is False
        assert d["error"] == "bad"
        assert d["error_details"] == {"x": 1}

    def test_str_success(self):
        """__str__ shows SUCCESS and vehicle info."""
        r = DashboardImportResult(success=True, vehicle_id="v1", vehicle_name="MyCar")
        s = str(r)
        assert "SUCCESS" in s
        assert "MyCar" in s
        assert "v1" in s

    def test_str_failure_shows_error(self):
        """__str__ shows FAILED and error details."""
        r = DashboardImportResult(
            success=False,
            vehicle_id="v1",
            vehicle_name="MyCar",
            error="template missing",
            error_details={"stage": "load"},
        )
        s = str(r)
        assert "FAILED" in s
        assert "template missing" in s
