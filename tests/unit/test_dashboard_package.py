"""Test that dashboard package re-exports public API.

VERIFIES: All public names are importable from the dashboard package.
"""

from custom_components.ev_trip_planner.dashboard import (
    DashboardError,
    DashboardImportResult,
    DashboardNotFoundError,
    DashboardStorageError,
    DashboardValidationError,
    import_dashboard,
    is_lovelace_available,
)


class TestDashboardPackageExports:
    """Verify dashboard package re-exports."""

    def test_import_dashboard_callable(self):
        """import_dashboard must be callable."""
        assert callable(import_dashboard)

    def test_is_lovelace_available_callable(self):
        """is_lovelace_available must be callable."""
        assert callable(is_lovelace_available)

    def test_dashboard_error_class(self):
        """DashboardError must be importable."""
        assert DashboardError is not None

    def test_dashboard_not_found_error_class(self):
        """DashboardNotFoundError must be importable."""
        assert DashboardNotFoundError is not None

    def test_dashboard_validation_error_class(self):
        """DashboardValidationError must be importable."""
        assert DashboardValidationError is not None

    def test_dashboard_storage_error_class(self):
        """DashboardStorageError must be importable."""
        assert DashboardStorageError is not None

    def test_dashboard_import_result_class(self):
        """DashboardImportResult must be importable."""
        assert DashboardImportResult is not None
