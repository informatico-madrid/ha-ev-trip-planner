"""Detailed tests for DashboardBuilder in dashboard/builder.py.

Tests fluent API, build output structure, defaults, and method chaining.
"""

from __future__ import annotations

from custom_components.ev_trip_planner.dashboard.builder import DashboardBuilder


class TestDashboardBuilderDefaults:
    """Test DashboardBuilder default state."""

    def test_default_title(self):
        """Builder starts with default title 'EV Trip Planner'."""
        b = DashboardBuilder()
        config = b.build()
        assert config["title"] == "EV Trip Planner"

    def test_default_no_views(self):
        """Builder starts with empty views list."""
        b = DashboardBuilder()
        config = b.build()
        assert config["views"] == []

    def test_build_returns_dict(self):
        """build() returns a dict."""
        b = DashboardBuilder()
        assert isinstance(b.build(), dict)

    def test_build_has_title_key(self):
        """build() dict always has 'title' key."""
        b = DashboardBuilder()
        config = b.build()
        assert "title" in config
        assert isinstance(config["title"], str)

    def test_build_has_views_key(self):
        """build() dict always has 'views' key."""
        b = DashboardBuilder()
        config = b.build()
        assert "views" in config
        assert isinstance(config["views"], list)


class TestDashboardBuilderWithTitle:
    """Test with_title fluent setter."""

    def test_sets_title(self):
        """with_title sets the title in the built config."""
        config = DashboardBuilder().with_title("Custom Title").build()
        assert config["title"] == "Custom Title"

    def test_returns_self(self):
        """with_title returns self for chaining."""
        b = DashboardBuilder()
        assert b.with_title("X") is b

    def test_overrides_default(self):
        """with_title overrides the default title."""
        config = DashboardBuilder().with_title("Override").build()
        assert config["title"] == "Override"


class TestDashboardBuilderStatusView:
    """Test add_status_view."""

    def test_adds_one_view(self):
        """add_status_view adds exactly one view."""
        b = DashboardBuilder()
        b.add_status_view()
        config = b.build()
        assert len(config["views"]) == 1

    def test_status_view_has_title(self):
        """Status view has title 'Status'."""
        config = DashboardBuilder().add_status_view().build()
        assert config["views"][0]["title"] == "Status"

    def test_status_view_has_path(self):
        """Status view has path 'ev-trip-planner'."""
        config = DashboardBuilder().add_status_view().build()
        assert config["views"][0]["path"] == "ev-trip-planner"

    def test_status_view_has_cards(self):
        """Status view has cards list."""
        config = DashboardBuilder().add_status_view().build()
        assert "cards" in config["views"][0]
        assert len(config["views"][0]["cards"]) == 1

    def test_status_view_card_type(self):
        """Status view card is a markdown card."""
        config = DashboardBuilder().add_status_view().build()
        card = config["views"][0]["cards"][0]
        assert card["type"] == "markdown"
        assert "EV Trip Planner" in card["content"]

    def test_returns_self(self):
        """add_status_view returns self."""
        b = DashboardBuilder()
        assert b.add_status_view() is b


class TestDashboardBuilderTripListView:
    """Test add_trip_list_view."""

    def test_adds_one_view(self):
        """add_trip_list_view adds exactly one view."""
        b = DashboardBuilder()
        b.add_trip_list_view()
        config = b.build()
        assert len(config["views"]) == 1

    def test_trip_view_title(self):
        """Trip view has title 'Trips'."""
        config = DashboardBuilder().add_trip_list_view().build()
        assert config["views"][0]["title"] == "Trips"

    def test_trip_view_path(self):
        """Trip view has path 'ev-trip-planner-trips'."""
        config = DashboardBuilder().add_trip_list_view().build()
        assert config["views"][0]["path"] == "ev-trip-planner-trips"

    def test_trip_view_card_type(self):
        """Trip view card is a custom ev-trip-list card."""
        config = DashboardBuilder().add_trip_list_view().build()
        card = config["views"][0]["cards"][0]
        assert card["type"] == "custom:ev-trip-list"

    def test_returns_self(self):
        """add_trip_list_view returns self."""
        b = DashboardBuilder()
        assert b.add_trip_list_view() is b


class TestDashboardBuilderFluentChaining:
    """Test fluent method chaining (builder pattern)."""

    def test_chained_title_status(self):
        """Chaining with_title then add_status_view works."""
        config = DashboardBuilder().with_title("My Dashboard").add_status_view().build()
        assert config["title"] == "My Dashboard"
        assert len(config["views"]) == 1
        assert config["views"][0]["title"] == "Status"

    def test_chained_title_trip_list(self):
        """Chaining with_title then add_trip_list_view works."""
        config = (
            DashboardBuilder().with_title("My Dashboard").add_trip_list_view().build()
        )
        assert config["title"] == "My Dashboard"
        assert config["views"][0]["title"] == "Trips"

    def test_full_chain_status_then_trip(self):
        """Full chain: title + status view + trip list view."""
        config = (
            DashboardBuilder()
            .with_title("EV Trip Planner")
            .add_status_view()
            .add_trip_list_view()
            .build()
        )
        assert config["title"] == "EV Trip Planner"
        assert len(config["views"]) == 2
        assert config["views"][0]["title"] == "Status"
        assert config["views"][1]["title"] == "Trips"

    def test_multiple_add_status_views(self):
        """Adding status view twice creates two views."""
        config = DashboardBuilder().add_status_view().add_status_view().build()
        assert len(config["views"]) == 2
        assert all(v["title"] == "Status" for v in config["views"])

    def test_build_does_not_mutate_builder(self):
        """Calling build() multiple times returns same structure."""
        b = DashboardBuilder().with_title("X").add_status_view()
        c1 = b.build()
        c2 = b.build()
        assert c1 == c2


class TestDashboardBuilderViewStructure:
    """Test that built views have the required structure."""

    def test_view_has_required_keys(self):
        """Each view dict has title, path, and cards keys."""
        config = (
            DashboardBuilder()
            .with_title("Test")
            .add_status_view()
            .add_trip_list_view()
            .build()
        )
        for view in config["views"]:
            assert "title" in view
            assert "path" in view
            assert "cards" in view
            assert isinstance(view["cards"], list)

    def test_view_path_is_string(self):
        """View path is a non-empty string."""
        config = DashboardBuilder().add_status_view().add_trip_list_view().build()
        for view in config["views"]:
            assert isinstance(view["path"], str)
            assert len(view["path"]) > 0

    def test_card_has_type(self):
        """Each card has a 'type' key."""
        config = DashboardBuilder().add_status_view().add_trip_list_view().build()
        for view in config["views"]:
            for card in view["cards"]:
                assert "type" in card
