"""Test that dashboard template files exist in templates/ subdirectory.

VERIFIES: All 11 template files are in dashboard/templates/
"""

import os

TEMPLATES_DIR = os.path.join(
    os.path.dirname(__file__),
    "..",
    "..",
    "custom_components",
    "ev_trip_planner",
    "dashboard",
    "templates",
)
TEMPLATES_DIR = os.path.abspath(TEMPLATES_DIR)

EXPECTED_TEMPLATES = [
    "dashboard.yaml",
    "dashboard-create.yaml",
    "dashboard-edit.yaml",
    "dashboard-delete.yaml",
    "dashboard-list.yaml",
    "dashboard_chispitas_test.yaml",
    "ev-trip-planner-full.yaml",
    "ev-trip-planner-simple.yaml",
    "ev-trip-planner-{vehicle_id}.yaml",
    "dashboard.js",
    "ev-trip-planner-simple.js",
]


class TestDashboardTemplates:
    """Verify template files exist in dashboard/templates/."""

    def test_templates_directory_exists(self):
        """The templates/ directory must exist under dashboard/."""
        assert os.path.isdir(TEMPLATES_DIR)

    def test_all_template_files_exist(self):
        """All 11 expected template files must exist in templates/."""
        missing = []
        for template in EXPECTED_TEMPLATES:
            path = os.path.join(TEMPLATES_DIR, template)
            if not os.path.isfile(path):
                missing.append(template)
        assert not missing, f"Missing template files: {missing}"
