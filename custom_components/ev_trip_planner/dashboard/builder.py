"""Dashboard configuration builder.

Provides a fluent builder interface for constructing dashboard configuration
dicts. Used by the orchestrator in import_dashboard to assemble the final
config before saving.
"""

from __future__ import annotations

from typing import Any


class DashboardBuilder:
    """Fluent builder for dashboard configuration dicts.

    Example::

        config = (
            DashboardBuilder()
            .with_title("EV Trip Planner")
            .add_status_view()
            .add_trip_list_view()
            .build()
        )
    """

    def __init__(self) -> None:
        self._title: str = "EV Trip Planner"
        self._views: list[dict[str, Any]] = []

    # -- fluent setters -------------------------------------------------------

    def with_title(self, title: str) -> DashboardBuilder:
        """Set the dashboard title.

        Args:
            title: Dashboard title string.

        Returns:
            self for method chaining.
        """
        self._title = title
        return self

    def add_status_view(self) -> DashboardBuilder:
        """Add a status view to the dashboard config.

        Returns:
            self for method chaining.
        """
        self._views.append({
            "title": "Status",
            "path": "ev-trip-planner",
            "cards": [
                {
                    "type": "markdown",
                    "title": "\U0001f4ca Status",
                    "content": "**EV Trip Planner**",
                },
            ],
        })
        return self

    def add_trip_list_view(self) -> DashboardBuilder:
        """Add a trip list view to the dashboard config.

        Returns:
            self for method chaining.
        """
        self._views.append({
            "title": "Trips",
            "path": "ev-trip-planner-trips",
            "cards": [
                {
                    "type": "custom:ev-trip-list",
                    "title": "Scheduled Trips",
                },
            ],
        })
        return self

    # -- build ----------------------------------------------------------------

    def build(self) -> dict[str, Any]:
        """Build and return the dashboard configuration dict.

        Returns:
            Dict with 'title' and 'views' keys.
        """
        return {
            "title": self._title,
            "views": self._views,
        }
