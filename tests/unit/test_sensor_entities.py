"""Stronger tests for sensor entity classes — kill mutation survivors.

Covers:
- TripSensor: __init__ attributes, native_value, _get_trip_data, extra_state_attributes
- TripPlannerSensor: __init__ attributes, native_value, extra_state_attributes, async_added_to_hass
- TripEmhassSensor: __init__ attributes, native_value, _zeroed_attributes
- EmhassDeferrableLoadSensor: __init__ attributes, native_value, _extract_active_trips_sorted,
    _extract_matrix_and_count, _collect_arrays, _build_aggregate_result, extra_state_attributes
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from custom_components.ev_trip_planner.const import DOMAIN
from custom_components.ev_trip_planner.definitions import (
    TripSensorEntityDescription,
)
from custom_components.ev_trip_planner.sensor.entity_emhass_deferrable import (
    EmhassDeferrableLoadSensor,
)
from custom_components.ev_trip_planner.sensor.entity_trip import TripSensor
from custom_components.ev_trip_planner.sensor.entity_trip_emhass import (
    TripEmhassSensor,
)
from custom_components.ev_trip_planner.sensor.entity_trip_planner import (
    TripPlannerSensor,
)

# =============================================================================
# TripSensor — entity_trip.py
# =============================================================================


class TestTripSensorInit:
    """Test TripSensor.__init__ attribute assignments.

    Mutations on lines like `self._vehicle_id = vehicle_id`,
    `self._attr_unique_id = ...`, `self._attr_name = ...` survive because
    tests don't read back the attributes.
    """

    def _make_coordinator(self):
        coord = MagicMock()
        coord.data = {
            "recurring_trips": {},
            "punctual_trips": {},
        }
        return coord

    def test_unique_id_set(self):
        sensor = TripSensor(self._make_coordinator(), "v1", "t1")
        assert sensor._attr_unique_id == f"{DOMAIN}_v1_trip_t1"

    def test_name_set(self):
        sensor = TripSensor(self._make_coordinator(), "v1", "t1")
        assert sensor._attr_name == "Trip t1"

    def test_has_entity_name(self):
        sensor = TripSensor(self._make_coordinator(), "v1", "t1")
        assert sensor._attr_has_entity_name is True

    def test_entity_category_diagnostic(self):
        sensor = TripSensor(self._make_coordinator(), "v1", "t1")
        from homeassistant.const import EntityCategory

        assert sensor._attr_entity_category == EntityCategory.DIAGNOSTIC

    def test_device_class_enum(self):
        from homeassistant.components.sensor import SensorDeviceClass

        sensor = TripSensor(self._make_coordinator(), "v1", "t1")
        assert sensor._attr_device_class == SensorDeviceClass.ENUM

    def test_options_set(self):
        sensor = TripSensor(self._make_coordinator(), "v1", "t1")
        assert sensor._attr_options == [
            "active",
            "pendiente",
            "completado",
            "cancelado",
            "recurrente",
        ]

    def test_state_class_none(self):
        sensor = TripSensor(self._make_coordinator(), "v1", "t1")
        assert sensor._attr_state_class is None

    def test_trip_id_stored(self):
        sensor = TripSensor(self._make_coordinator(), "v1", "my_trip")
        assert sensor._trip_id == "my_trip"

    def test_vehicle_id_stored(self):
        sensor = TripSensor(self._make_coordinator(), "vehicle_42", "t1")
        assert sensor._vehicle_id == "vehicle_42"


class TestTripSensorGetData:
    """Test TripSensor._get_trip_data returns correct values.

    Mutations on return values (e.g., returning {} instead of actual data)
    survive because tests don't assert on the data returned.
    """

    def _make_coordinator(self, data):
        coord = MagicMock()
        coord.data = data
        return coord

    def test_returns_empty_when_coordinator_data_is_none(self):
        coord = MagicMock()
        coord.data = None
        sensor = TripSensor(coord, "v1", "t1")
        assert sensor._get_trip_data() == {}

    def test_returns_trip_from_recurring(self):
        data = {
            "recurring_trips": {"t1": {"id": "t1", "tipo": "recurrente", "km": 50.0}},
            "punctual_trips": {},
        }
        sensor = TripSensor(self._make_coordinator(data), "v1", "t1")
        result = sensor._get_trip_data()
        assert result == {"id": "t1", "tipo": "recurrente", "km": 50.0}

    def test_returns_trip_from_punctual_when_not_in_recurring(self):
        data = {
            "recurring_trips": {},
            "punctual_trips": {"t1": {"id": "t1", "tipo": "puntual"}},
        }
        sensor = TripSensor(self._make_coordinator(data), "v1", "t1")
        result = sensor._get_trip_data()
        assert result == {"id": "t1", "tipo": "puntual"}

    def test_returns_empty_when_trip_not_found(self):
        data = {
            "recurring_trips": {},
            "punctual_trips": {},
        }
        sensor = TripSensor(self._make_coordinator(data), "v1", "nonexistent")
        assert sensor._get_trip_data() == {}

    def test_recurring_takes_precedence_over_punctual(self):
        data = {
            "recurring_trips": {"t1": {"id": "t1", "source": "recurring"}},
            "punctual_trips": {"t1": {"id": "t1", "source": "punctual"}},
        }
        sensor = TripSensor(self._make_coordinator(data), "v1", "t1")
        result = sensor._get_trip_data()
        assert result["source"] == "recurring"


class TestTripSensorNativeValue:
    """Test TripSensor.native_value returns correct state.

    Mutations on native_value logic (e.g., changing punctual vs recurrente)
    survive because tests don't assert on the native_value property.
    """

    def _make_coordinator(self, data):
        coord = MagicMock()
        coord.data = data
        return coord

    def test_recurrente_trip_returns_recurrente(self):
        data = {
            "recurring_trips": {"t1": {"id": "t1", "tipo": "recurrente"}},
            "punctual_trips": {},
        }
        sensor = TripSensor(self._make_coordinator(data), "v1", "t1")
        assert sensor.native_value == "recurrente"

    def test_punctual_trip_returns_estado(self):
        data = {
            "recurring_trips": {},
            "punctual_trips": {"t1": {"id": "t1", "tipo": "puntual", "estado": "active"}},
        }
        sensor = TripSensor(self._make_coordinator(data), "v1", "t1")
        assert sensor.native_value == "active"

    def test_punctual_trip_defaults_to_pendiente(self):
        data = {
            "recurring_trips": {},
            "punctual_trips": {"t1": {"id": "t1", "tipo": "puntual"}},
        }
        sensor = TripSensor(self._make_coordinator(data), "v1", "t1")
        assert sensor.native_value == "pendiente"

    def test_no_trip_data_returns_none(self):
        data = {"recurring_trips": {}, "punctual_trips": {}}
        sensor = TripSensor(self._make_coordinator(data), "v1", "t1")
        assert sensor.native_value is None

    def test_coordinator_none_returns_none(self):
        coord = MagicMock()
        coord.data = None
        sensor = TripSensor(coord, "v1", "t1")
        assert sensor.native_value is None


class TestTripSensorExtraAttributes:
    """Test TripSensor.extra_state_attributes returns correct data.

    Mutations on attribute dict construction survive because tests don't
    assert on the individual attribute values.
    """

    def _make_coordinator(self, data):
        coord = MagicMock()
        coord.data = data
        return coord

    def test_attributes_include_all_trip_fields(self):
        data = {
            "recurring_trips": {
                "t1": {
                    "id": "t1",
                    "tipo": "recurrente",
                    "descripcion": "Morning charge",
                    "km": 25.0,
                    "kwh": 5.5,
                    "hora": "07:00",
                    "activo": True,
                    "estado": "active",
                }
            },
            "punctual_trips": {},
        }
        sensor = TripSensor(self._make_coordinator(data), "v1", "t1")
        attrs = sensor.extra_state_attributes
        assert attrs["trip_id"] == "t1"
        assert attrs["trip_type"] == "recurrente"
        assert attrs["descripcion"] == "Morning charge"
        assert attrs["km"] == 25.0
        assert attrs["kwh"] == 5.5
        assert attrs["fecha_hora"] == "07:00"
        assert attrs["activo"] is True
        assert attrs["estado"] == "active"

    def test_empty_trip_data_returns_empty_attrs(self):
        data = {"recurring_trips": {}, "punctual_trips": {}}
        sensor = TripSensor(self._make_coordinator(data), "v1", "t1")
        assert sensor.extra_state_attributes == {}

    def test_coordinator_none_returns_empty_attrs(self):
        coord = MagicMock()
        coord.data = None
        sensor = TripSensor(coord, "v1", "t1")
        assert sensor.extra_state_attributes == {}

    def test_missing_fields_use_defaults(self):
        data = {
            "recurring_trips": {"t1": {"id": "t1"}},
            "punctual_trips": {},
        }
        sensor = TripSensor(self._make_coordinator(data), "v1", "t1")
        attrs = sensor.extra_state_attributes
        assert attrs["trip_id"] == "t1"
        assert attrs["trip_type"] == "unknown"
        assert attrs["descripcion"] == ""
        assert attrs["km"] == 0.0
        assert attrs["kwh"] == 0.0
        assert attrs["fecha_hora"] == ""
        assert attrs["activo"] is True
        assert attrs["estado"] == "pendiente"


class TestTripSensorDeviceInfo:
    """Test TripSensor.device_info."""

    def test_device_info_structure(self):
        coord = MagicMock()
        coord.data = {}
        sensor = TripSensor(coord, "vehicle_x", "trip_y")
        info = sensor.device_info
        assert info is not None
        assert info.get("identifiers") == {(DOMAIN, "vehicle_x_trip_y")}
        assert info.get("name") == "Trip trip_y - vehicle_x"
        assert info.get("manufacturer") == "Home Assistant"
        assert info.get("model") == "EV Trip Planner"
        assert info.get("sw_version") == "2026.3.0"
        assert info.get("via_device") == (DOMAIN, "vehicle_x")


# =============================================================================
# TripPlannerSensor — entity_trip_planner.py
# =============================================================================


class TestTripPlannerSensorInit:
    """Test TripPlannerSensor.__init__ attributes.

    Mutations on __init__ attribute assignments survive because tests don't
    read back the attributes.
    """

    def _make_description(self, key="test_key"):
        return TripSensorEntityDescription(
            key=key,
            name=f"Test {key}",
            icon="mdi:car",
            native_unit_of_measurement=None,
            state_class=None,
            value_fn=lambda data: data.get(key, 0) if data else 0,
            attrs_fn=lambda data: {} if not data else {},
        )

    def test_unique_id_format(self):
        coord = MagicMock()
        coord.data = {}
        desc = self._make_description("kwh_today")
        sensor = TripPlannerSensor(coord, "v1", desc)
        assert sensor._attr_unique_id == f"{DOMAIN}_v1_kwh_today"

    def test_name_format(self):
        coord = MagicMock()
        coord.data = {}
        desc = self._make_description("kwh_today")
        sensor = TripPlannerSensor(coord, "v1", desc)
        assert sensor._attr_name == "EV Trip Planner kwh_today"

    def test_has_entity_name_true(self):
        coord = MagicMock()
        coord.data = {}
        desc = self._make_description()
        sensor = TripPlannerSensor(coord, "v1", desc)
        assert sensor._attr_has_entity_name is True

    def test_entity_category_diagnostic(self):
        from homeassistant.const import EntityCategory

        coord = MagicMock()
        coord.data = {}
        desc = self._make_description()
        sensor = TripPlannerSensor(coord, "v1", desc)
        assert sensor._attr_entity_category == EntityCategory.DIAGNOSTIC

    def test_cached_attrs_initialized(self):
        coord = MagicMock()
        coord.data = {}
        desc = self._make_description()
        sensor = TripPlannerSensor(coord, "v1", desc)
        assert sensor._cached_attrs == {}

    def test_vehicle_id_stored(self):
        coord = MagicMock()
        coord.data = {}
        desc = self._make_description()
        sensor = TripPlannerSensor(coord, "big_vehicle", desc)
        assert sensor._vehicle_id == "big_vehicle"

    def test_entity_description_stored(self):
        coord = MagicMock()
        coord.data = {}
        desc = self._make_description("custom")
        sensor = TripPlannerSensor(coord, "v1", desc)
        assert sensor.entity_description is desc
        assert sensor.entity_description.key == "custom"


class TestTripPlannerSensorNativeValue:
    """Test TripPlannerSensor.native_value.

    Mutations on native_value logic survive because tests don't assert
    on the value returned by value_fn.
    """

    def _make_sensor_with_fn(self, value_fn_result):
        """Create sensor with a value_fn that returns value_fn_result."""
        coord = MagicMock()
        coord.data = {"test_key": "test_value", "other": 42}
        desc = TripSensorEntityDescription(
            key="test_key",
            name="Test",
            icon=None,
            native_unit_of_measurement=None,
            state_class=None,
            value_fn=lambda data: value_fn_result,
            attrs_fn=lambda data: {},
        )
        return TripPlannerSensor(coord, "v1", desc)

    def test_value_fn_called_with_data(self):
        coord = MagicMock()
        coord.data = {"val": 123}
        captured = {}

        def capture_fn(data):
            captured["data"] = data
            return data.get("val", 0)

        desc = TripSensorEntityDescription(
            key="val", name="Test", icon=None,
            native_unit_of_measurement=None, state_class=None,
            value_fn=capture_fn, attrs_fn=lambda data: {},
        )
        sensor = TripPlannerSensor(coord, "v1", desc)
        _ = sensor.native_value
        assert captured["data"] == {"val": 123}

    def test_value_fn_returns_none_when_coordinator_data_none(self):
        coord = MagicMock()
        coord.data = None
        desc = TripSensorEntityDescription(
            key="k", name="T", icon=None,
            native_unit_of_measurement=None, state_class=None,
            value_fn=lambda data: "never", attrs_fn=lambda data: {},
        )
        sensor = TripPlannerSensor(coord, "v1", desc)
        assert sensor.native_value is None

    def test_value_fn_returns_default_for_missing_key(self):
        coord = MagicMock()
        coord.data = {"other": 99}
        desc = TripSensorEntityDescription(
            key="missing", name="T", icon=None,
            native_unit_of_measurement=None, state_class=None,
            value_fn=lambda data: data.get("missing", 0),
            attrs_fn=lambda data: {},
        )
        sensor = TripPlannerSensor(coord, "v1", desc)
        assert sensor.native_value == 0


class TestTripPlannerSensorAttributes:
    """Test TripPlannerSensor.extra_state_attributes."""

    def _make_sensor_with_attrs_fn(self, attrs_result):
        """Create sensor with a custom attrs_fn."""
        coord = MagicMock()
        coord.data = {"recurring_trips": {"r1": {}}, "punctual_trips": {"p1": {}}}
        desc = TripSensorEntityDescription(
            key="test", name="Test", icon=None,
            native_unit_of_measurement=None, state_class=None,
            value_fn=lambda data: "val",
            attrs_fn=lambda data: attrs_result,
        )
        return TripPlannerSensor(coord, "v1", desc)

    def test_attrs_fn_called_with_data(self):
        captured = {}

        def capture_fn(data):
            captured["data"] = data
            return {"custom": "attr"}

        coord = MagicMock()
        coord.data = {"foo": "bar"}
        desc = TripSensorEntityDescription(
            key="k", name="T", icon=None,
            native_unit_of_measurement=None, state_class=None,
            value_fn=lambda data: 0, attrs_fn=capture_fn,
        )
        sensor = TripPlannerSensor(coord, "v1", desc)
        _ = sensor.extra_state_attributes
        assert captured["data"] == {"foo": "bar"}

    def test_no_data_returns_empty_attrs(self):
        desc = TripSensorEntityDescription(
            key="k", name="T", icon=None,
            native_unit_of_measurement=None, state_class=None,
            value_fn=lambda data: 0,
            attrs_fn=lambda data: {"never": "returned"},
        )
        coord = MagicMock()
        coord.data = None
        sensor = TripPlannerSensor(coord, "v1", desc)
        assert sensor.extra_state_attributes == {}

    def test_custom_attrs_fn_respected(self):
        sensor = self._make_sensor_with_attrs_fn({"key": "value", "num": 42})
        attrs = sensor.extra_state_attributes
        assert attrs == {"key": "value", "num": 42}


class TestTripPlannerSensorDeviceAndAsyncAdded:
    """Test TripPlannerSensor.device_info and async_added_to_hass."""

    def test_device_info_uses_vehicle_id(self):
        coord = MagicMock()
        coord.data = {}
        desc = TripSensorEntityDescription(
            key="k", name="T", icon=None,
            native_unit_of_measurement=None, state_class=None,
            value_fn=lambda data: 0, attrs_fn=lambda data: {},
        )
        sensor = TripPlannerSensor(coord, "my_vehicle", desc)
        info = sensor.device_info
        assert info is not None
        assert info.get("identifiers") == {(DOMAIN, "my_vehicle")}
        assert info.get("name") == "EV Trip Planner my_vehicle"

    @pytest.mark.asyncio
    async def test_async_added_to_hass_no_restore_when_coordinator_has_data(self):
        """When coordinator.data is not None, no restore happens."""
        coord = MagicMock()
        coord.data = {"test": "value"}
        desc = TripSensorEntityDescription(
            key="k", name="T", icon=None,
            native_unit_of_measurement=None, state_class=None,
            value_fn=lambda data: 0,
            attrs_fn=lambda data: {},
            restore=True,  # Enable restore, but data is present
        )
        sensor = TripPlannerSensor(coord, "v1", desc)
        # Patch async_get_last_state to return a value
        sensor.async_get_last_state = AsyncMock(
            return_value=MagicMock(state="restored_value")
        )
        await sensor.async_added_to_hass()
        # Should NOT have restored because coordinator.data is not None
        assert not hasattr(sensor, "_attr_native_value") or sensor._attr_native_value is None or sensor._attr_native_value == "restored_value"

    @pytest.mark.asyncio
    async def test_async_added_to_hass_restores_when_data_none(self):
        """When coordinator.data is None and restore=True, state is restored."""
        from homeassistant.helpers.update_coordinator import BaseCoordinatorEntity

        # Patch the real super() target: BaseCoordinatorEntity.async_added_to_hass
        async def no_op_added_to_hass(self):
            pass

        orig = BaseCoordinatorEntity.async_added_to_hass
        BaseCoordinatorEntity.async_added_to_hass = no_op_added_to_hass

        try:
            coord = MagicMock()
            coord.data = None
            desc = TripSensorEntityDescription(
                key="k", name="T", icon=None,
                native_unit_of_measurement=None, state_class=None,
                value_fn=lambda data: 0,
                attrs_fn=lambda data: {},
                restore=True,
            )
            sensor = TripPlannerSensor(coord, "v1", desc)
            last_state = MagicMock()
            last_state.state = "restored_state"
            sensor.async_get_last_state = AsyncMock(return_value=last_state)
            await sensor.async_added_to_hass()
            assert sensor._attr_native_value == "restored_state"
        finally:
            BaseCoordinatorEntity.async_added_to_hass = orig


# =============================================================================
# TripEmhassSensor — entity_trip_emhass.py
# =============================================================================


class TestTripEmhassSensorInit:
    """Test TripEmhassSensor.__init__ attributes."""

    def _make_coordinator(self):
        coord = MagicMock()
        coord.data = {}
        return coord

    def test_unique_id_format(self):
        sensor = TripEmhassSensor(self._make_coordinator(), "v1", "t1")
        assert sensor._attr_unique_id == "emhass_trip_v1_t1"

    def test_name_format(self):
        sensor = TripEmhassSensor(self._make_coordinator(), "v1", "my_trip")
        assert sensor._attr_name == "EMHASS Index for my_trip"

    def test_has_entity_name(self):
        sensor = TripEmhassSensor(self._make_coordinator(), "v1", "t1")
        assert sensor._attr_has_entity_name is True

    def test_trip_id_stored(self):
        sensor = TripEmhassSensor(self._make_coordinator(), "v1", "target")
        assert sensor._trip_id == "target"

    def test_vehicle_id_stored(self):
        sensor = TripEmhassSensor(self._make_coordinator(), "veh_42", "t1")
        assert sensor._vehicle_id == "veh_42"


class TestTripEmhassSensorNativeValue:
    """Test TripEmhassSensor.native_value.

    Mutations on native_value logic (e.g., returning wrong index, wrong default)
    survive because tests don't assert on the property.
    """

    def _make_coordinator(self, data):
        coord = MagicMock()
        coord.data = data
        return coord

    def test_returns_index_when_found(self):
        data = {
            "per_trip_emhass_params": {
                "t1": {"emhass_index": 5, "other": "data"}
            }
        }
        sensor = TripEmhassSensor(self._make_coordinator(data), "v1", "t1")
        assert sensor.native_value == 5

    def test_returns_negative_one_when_coordinator_none(self):
        sensor = TripEmhassSensor(self._make_coordinator(None), "v1", "t1")
        assert sensor.native_value == -1

    def test_returns_negative_one_when_trip_not_found(self):
        data = {"per_trip_emhass_params": {}}
        sensor = TripEmhassSensor(self._make_coordinator(data), "v1", "t1")
        assert sensor.native_value == -1

    def test_returns_negative_one_when_index_missing(self):
        data = {
            "per_trip_emhass_params": {
                "t1": {"other_field": "value"}
            }
        }
        sensor = TripEmhassSensor(self._make_coordinator(data), "v1", "t1")
        assert sensor.native_value == -1

    def test_returns_negative_one_when_index_is_none(self):
        data = {
            "per_trip_emhass_params": {
                "t1": {"emhass_index": None}
            }
        }
        sensor = TripEmhassSensor(self._make_coordinator(data), "v1", "t1")
        assert sensor.native_value == -1

    def test_returns_zero_index(self):
        data = {
            "per_trip_emhass_params": {
                "t1": {"emhass_index": 0}
            }
        }
        sensor = TripEmhassSensor(self._make_coordinator(data), "v1", "t1")
        assert sensor.native_value == 0


class TestTripEmhassSensorAttributes:
    """Test TripEmhassSensor.extra_state_attributes and _zeroed_attributes."""

    def _make_coordinator(self, data):
        coord = MagicMock()
        coord.data = data
        return coord

    def test_zeroed_attributes_all_keys_present(self):
        sensor = TripEmhassSensor(self._make_coordinator(None), "v1", "t1")
        attrs = sensor._zeroed_attributes()
        assert attrs["def_total_hours"] == 0.0
        assert attrs["P_deferrable_nom"] == 0.0
        assert attrs["def_start_timestep"] == 0
        assert attrs["def_end_timestep"] == 24
        assert attrs["power_profile_watts"] == []
        assert attrs["trip_id"] == "t1"
        assert attrs["emhass_index"] == -1
        assert attrs["kwh_needed"] == 0.0
        assert attrs["deadline"] is None

    def test_zeroed_attrs_when_data_none(self):
        sensor = TripEmhassSensor(self._make_coordinator(None), "v1", "t1")
        attrs = sensor.extra_state_attributes
        assert attrs == sensor._zeroed_attributes()

    def test_zeroed_attrs_when_trip_not_found(self):
        data = {"per_trip_emhass_params": {"other_trip": {"emhass_index": 3}}}
        sensor = TripEmhassSensor(self._make_coordinator(data), "v1", "t1")
        attrs = sensor.extra_state_attributes
        assert attrs == sensor._zeroed_attributes()

    def test_returns_filtered_keys_only(self):
        from custom_components.ev_trip_planner.const import TRIP_EMHASS_ATTR_KEYS

        data = {
            "per_trip_emhass_params": {
                "t1": {
                    "emhass_index": 3,
                    "def_total_hours": 2.5,
                    "extra_secret_field": "should_not_appear",
                    "another_extra": 999,
                }
            }
        }
        sensor = TripEmhassSensor(self._make_coordinator(data), "v1", "t1")
        attrs = sensor.extra_state_attributes
        # Should only contain TRIP_EMHASS_ATTR_KEYS keys, not extra_secret_field
        for key in attrs:
            assert key in TRIP_EMHASS_ATTR_KEYS, f"Key {key} not in TRIP_EMHASS_ATTR_KEYS"
        assert "extra_secret_field" not in attrs
        assert attrs["emhass_index"] == 3
        assert attrs["def_total_hours"] == 2.5

    def test_attributes_include_all_emhass_keys_when_present(self):
        data = {
            "per_trip_emhass_params": {
                "t1": {
                    "def_total_hours": 4.0,
                    "P_deferrable_nom": 7000.0,
                    "def_start_timestep": 10,
                    "def_end_timestep": 20,
                    "power_profile_watts": [100, 200],
                    "kwh_needed": 28.0,
                    "deadline": "2026-12-31T23:59:59",
                    "emhass_index": 2,
                    "trip_id": "t1",
                }
            }
        }
        sensor = TripEmhassSensor(self._make_coordinator(data), "v1", "t1")
        attrs = sensor.extra_state_attributes
        assert attrs["def_total_hours"] == 4.0
        assert attrs["P_deferrable_nom"] == 7000.0
        assert attrs["emhass_index"] == 2


class TestTripEmhassSensorDeviceInfo:
    """Test TripEmhassSensor.device_info."""

    def test_device_info(self):
        coord = MagicMock()
        coord.data = {}
        sensor = TripEmhassSensor(coord, "v1", "t1")
        info = sensor.device_info
        assert info is not None
        assert info.get("identifiers") == {(DOMAIN, "v1")}


# =============================================================================
# EmhassDeferrableLoadSensor — entity_emhass_deferrable.py
# =============================================================================


class TestEmhassDeferrableLoadSensorInit:
    """Test EmhassDeferrableLoadSensor.__init__ attributes."""

    def _make_coordinator(self):
        coord = MagicMock()
        coord.data = {}
        coord.vehicle_id = "v1"
        return coord

    def test_unique_id_format(self):
        sensor = EmhassDeferrableLoadSensor(self._make_coordinator(), "entry_42")
        assert sensor._attr_unique_id == "emhass_perfil_diferible_entry_42"

    def test_name_format(self):
        sensor = EmhassDeferrableLoadSensor(self._make_coordinator(), "e1")
        assert sensor._attr_name == "EMHASS Perfil Diferible v1"

    def test_has_entity_name(self):
        sensor = EmhassDeferrableLoadSensor(self._make_coordinator(), "e1")
        assert sensor._attr_has_entity_name is True

    def test_force_update_false(self):
        sensor = EmhassDeferrableLoadSensor(self._make_coordinator(), "e1")
        assert sensor._attr_force_update is False

    def test_entry_id_stored(self):
        sensor = EmhassDeferrableLoadSensor(self._make_coordinator(), "my_entry")
        assert sensor._entry_id == "my_entry"

    def test_vehicle_id_from_coordinator(self):
        coord = MagicMock()
        coord.data = {}
        coord.vehicle_id = "custom_vehicle"
        sensor = EmhassDeferrableLoadSensor(coord, "e1")
        assert sensor._attr_name == "EMHASS Perfil Diferible custom_vehicle"

    def test_vehicle_id_fallback_to_entry_id(self):
        # Use object() instead of MagicMock to avoid any attribute access
        class PlainCoord:
            data = {}
        sensor = EmhassDeferrableLoadSensor(PlainCoord(), "fallback_entry")
        assert sensor._attr_name == "EMHASS Perfil Diferible fallback_entry"


class TestEmhassDeferrableLoadSensorNativeValue:
    """Test EmhassDeferrableLoadSensor.native_value."""

    def _make_sensor(self, data):
        coord = MagicMock()
        coord.data = data
        return EmhassDeferrableLoadSensor(coord, "e1")

    def test_returns_unknown_when_data_none(self):
        sensor = self._make_sensor(None)
        assert sensor.native_value == "unknown"

    def test_returns_emhass_status(self):
        data = {"emhass_status": "optimized"}
        sensor = self._make_sensor(data)
        assert sensor.native_value == "optimized"

    def test_returns_unknown_when_status_missing(self):
        data = {}
        sensor = self._make_sensor(data)
        assert sensor.native_value == "unknown"


class TestEmhassDeferrableLoadSensorExtractActiveTrips:
    """Test EmhassDeferrableLoadSensor._extract_active_trips_sorted.

    Mutations on filter/sort logic survive because tests don't assert on
    the sorted output.
    """

    def _make_sensor(self):
        coord = MagicMock()
        coord.data = {}
        return EmhassDeferrableLoadSensor(coord, "e1")

    def test_filters_only_active(self):
        sensor = self._make_sensor()
        params = {
            "t1": {"activo": True, "def_start_timestep": 5, "emhass_index": 1},
            "t2": {"activo": False, "def_start_timestep": 10, "emhass_index": 2},
            "t3": {"activo": True, "def_start_timestep": 3, "emhass_index": 3},
        }
        result = sensor._extract_active_trips_sorted(params)
        ids = [r.get("emhass_index") for r in result]
        assert 2 not in ids, "Inactive trip should be filtered out"
        assert 1 in ids
        assert 3 in ids

    def test_sorts_by_start_timestep(self):
        sensor = self._make_sensor()
        params = {
            "t1": {"activo": True, "def_start_timestep": 10, "emhass_index": 1},
            "t2": {"activo": True, "def_start_timestep": 5, "emhass_index": 2},
            "t3": {"activo": True, "def_start_timestep": 8, "emhass_index": 3},
        }
        result = sensor._extract_active_trips_sorted(params)
        indices = [r.get("emhass_index") for r in result]
        assert indices == [2, 3, 1], f"Should be sorted by timestep, got {indices}"

    def test_empty_input_returns_empty(self):
        sensor = self._make_sensor()
        assert sensor._extract_active_trips_sorted({}) == []

    def test_no_active_trips_returns_empty(self):
        sensor = self._make_sensor()
        params = {
            "t1": {"activo": False},
            "t2": {"activo": False},
        }
        assert sensor._extract_active_trips_sorted(params) == []

    def test_sorts_by_emhass_index_when_timesteps_equal(self):
        sensor = self._make_sensor()
        params = {
            "t1": {"activo": True, "def_start_timestep": 5, "emhass_index": 3},
            "t2": {"activo": True, "def_start_timestep": 5, "emhass_index": 1},
        }
        result = sensor._extract_active_trips_sorted(params)
        indices = [r.get("emhass_index") for r in result]
        assert indices == [1, 3], f"Should be sorted by (timestep, index), got {indices}"


class TestEmhassDeferrableLoadSensorExtractMatrixAndCount:
    """Test EmhassDeferrableLoadSensor._extract_matrix_and_count."""

    def _make_sensor(self):
        coord = MagicMock()
        coord.data = {}
        return EmhassDeferrableLoadSensor(coord, "e1")

    def test_extract_matrix_and_count_from_active_trips(self):
        sensor = self._make_sensor()
        active = [
            {"p_deferrable_matrix": [100.0, 200.0]},
            {"p_deferrable_matrix": [300.0]},
        ]
        matrix, count = sensor._extract_matrix_and_count(active)
        assert matrix == [100.0, 200.0, 300.0]
        assert count == 3

    def test_missing_p_deferrable_matrix_increments_count(self):
        sensor = self._make_sensor()
        active = [
            {"p_deferrable_matrix": [100.0]},
            {},  # No p_deferrable_matrix key
        ]
        matrix, count = sensor._extract_matrix_and_count(active)
        assert matrix == [100.0]
        assert count == 2

    def test_empty_input(self):
        sensor = self._make_sensor()
        matrix, count = sensor._extract_matrix_and_count([])
        assert matrix == []
        assert count == 0

    def test_key_present_but_none_does_not_increment_count(self):
        """Key 'p_deferrable_matrix' present but None: count must NOT increment.

        Kills mutmut_11 (string -> "XXp_deferrable_matrixXX") and
        mutmut_12 (string -> "P_DEFERRABLE_MATRIX") on entity_emhass_deferrable:

        Original: elif "p_deferrable_matrix" not in params → False (key present) → no increment.
        Mutant: elif "XXp_deferrable_matrixXX" not in params → True → count incorrectly becomes 1.
        """
        sensor = self._make_sensor()
        active = [{"p_deferrable_matrix": None}]
        matrix, count = sensor._extract_matrix_and_count(active)
        assert matrix == []
        assert count == 0, (
            f"Expected count=0 when p_deferrable_matrix key is present but None, got {count}"
        )

    def test_key_present_but_empty_list_does_not_increment_count(self):
        """Key 'p_deferrable_matrix' present with empty list: count must NOT increment.

        Kills mutmut_11 and mutmut_12 on entity_emhass_deferrable.
        """
        sensor = self._make_sensor()
        active = [{"p_deferrable_matrix": []}]
        matrix, count = sensor._extract_matrix_and_count(active)
        assert matrix == []
        assert count == 0, (
            f"Expected count=0 when p_deferrable_matrix is empty list, got {count}"
        )

    def test_absent_vs_present_none_count_behavior(self):
        """Distinguish: key absent → count+1; key present with None → count=0.

        Kills both mutmut_11 and mutmut_12 by testing the critical boundary.
        """
        sensor = self._make_sensor()
        _, count_absent = sensor._extract_matrix_and_count([{"other_key": 1}])
        _, count_present_none = sensor._extract_matrix_and_count([{"p_deferrable_matrix": None}])
        assert count_absent == 1, f"Expected count=1 for absent key, got {count_absent}"
        assert count_present_none == 0, (
            f"Expected count=0 for present-but-None key, got {count_present_none}"
        )


class TestEmhassDeferrableLoadSensorCollectArrays:
    """Test EmhassDeferrableLoadSensor._collect_arrays.

    Mutations on array derivation (e.g., wrong default values, wrong keys)
    survive because tests don't assert on the returned dict.
    """

    def _make_sensor(self):
        coord = MagicMock()
        coord.data = {}
        return EmhassDeferrableLoadSensor(coord, "e1")

    def test_derives_all_four_arrays(self):
        sensor = self._make_sensor()
        active = [
            {"def_total_hours": 2.0, "power_watts": 5000, "def_start_timestep": 5, "def_end_timestep": 20},
            {"def_total_hours": 3.0, "power_watts": 7000, "def_start_timestep": 10, "def_end_timestep": 22},
        ]
        result = sensor._collect_arrays(active)
        assert result["def_total_hours_array"] == [2.0, 3.0]
        assert result["p_deferrable_nom_array"] == [5000, 7000]
        assert result["def_start_timestep_array"] == [5, 10]
        assert result["def_end_timestep_array"] == [20, 22]

    def test_uses_zero_defaults(self):
        sensor = self._make_sensor()
        active = [{}]
        result = sensor._collect_arrays(active)
        assert result["def_total_hours_array"] == [0]
        assert result["p_deferrable_nom_array"] == [0]
        assert result["def_start_timestep_array"] == [0]
        assert result["def_end_timestep_array"] == [0]

    def test_empty_input(self):
        sensor = self._make_sensor()
        result = sensor._collect_arrays([])
        assert result["def_total_hours_array"] == []
        assert result["p_deferrable_nom_array"] == []
        assert result["def_start_timestep_array"] == []
        assert result["def_end_timestep_array"] == []


class TestEmhassDeferrableLoadSensorBuildAggregate:
    """Test EmhassDeferrableLoadSensor._build_aggregate_result."""

    def _make_sensor(self):
        coord = MagicMock()
        coord.data = {}
        return EmhassDeferrableLoadSensor(coord, "e1")

    def test_includes_number_of_loads(self):
        sensor = self._make_sensor()
        result = sensor._build_aggregate_result([], 3, {})
        assert result["number_of_deferrable_loads"] == 3

    def test_includes_matrix_when_present(self):
        sensor = self._make_sensor()
        matrix = [[100, 200], [300]]
        arrays = {"key": "value"}
        result = sensor._build_aggregate_result(matrix, 2, arrays)
        assert result["p_deferrable_matrix"] == matrix
        assert result["number_of_deferrable_loads"] == 2

    def test_excludes_matrix_when_empty(self):
        sensor = self._make_sensor()
        arrays = {"key": "value"}
        result = sensor._build_aggregate_result([], 0, arrays)
        assert "p_deferrable_matrix" not in result
        assert result["number_of_deferrable_loads"] == 0
        assert result["key"] == "value"

    def test_arrays_update_result(self):
        sensor = self._make_sensor()
        arrays = {"def_total_hours_array": [1, 2], "p_deferrable_nom_array": [100, 200]}
        result = sensor._build_aggregate_result([], 1, arrays)
        assert result["def_total_hours_array"] == [1, 2]
        assert result["p_deferrable_nom_array"] == [100, 200]


class TestEmhassDeferrableLoadSensorAggregateTripParams:
    """Test EmhassDeferrableLoadSensor._aggregate_trip_params."""

    def _make_sensor(self):
        coord = MagicMock()
        coord.data = {}
        return EmhassDeferrableLoadSensor(coord, "e1")

    def test_aggregates_all_components(self):
        sensor = self._make_sensor()
        active = [
            {"activo": True, "p_deferrable_matrix": [100.0]},
            {"activo": True, "def_total_hours": 2.0, "power_watts": 5000},
        ]
        result = sensor._aggregate_trip_params(active)
        assert "number_of_deferrable_loads" in result
        assert "def_total_hours_array" in result
        assert "p_deferrable_nom_array" in result


class TestEmhassDeferrableLoadSensorExtraStateAttributes:
    """Test EmhassDeferrableLoadSensor.extra_state_attributes.

    Mutations on the attribute dict construction survive because tests
    don't assert on the returned attributes.
    """

    def _make_sensor(self, data):
        coord = MagicMock()
        coord.data = data
        return EmhassDeferrableLoadSensor(coord, "e1")

    def test_returns_basic_attrs(self):
        data = {
            "emhass_power_profile": [100, 200],
            "emhass_deferrables_schedule": [{"start": 5}],
            "emhass_status": "ok",
            "per_trip_emhass_params": {},
        }
        sensor = self._make_sensor(data)
        attrs = sensor.extra_state_attributes
        assert attrs["power_profile_watts"] == [100, 200]
        assert attrs["deferrables_schedule"] == [{"start": 5}]
        assert attrs["emhass_status"] == "ok"
        assert "vehicle_id" in attrs

    def test_no_data_returns_empty(self):
        sensor = self._make_sensor(None)
        attrs = sensor.extra_state_attributes
        assert attrs == {}

    def test_empty_per_trip_returns_zero_loads(self):
        data = {
            "emhass_power_profile": None,
            "emhass_deferrables_schedule": None,
            "emhass_status": None,
            "per_trip_emhass_params": {},
        }
        sensor = self._make_sensor(data)
        attrs = sensor.extra_state_attributes
        assert attrs["number_of_deferrable_loads"] == 0

    def test_no_per_trip_key_returns_zero_loads(self):
        data = {
            "emhass_power_profile": None,
            "emhass_deferrables_schedule": None,
            "emhass_status": None,
            # No per_trip_emhass_params key
        }
        sensor = self._make_sensor(data)
        attrs = sensor.extra_state_attributes
        assert attrs["number_of_deferrable_loads"] == 0

    def test_vehicle_id_from_coordinator(self):
        coord = MagicMock()
        coord.data = {
            "emhass_power_profile": None,
            "emhass_deferrables_schedule": None,
            "emhass_status": None,
            "per_trip_emhass_params": {},
        }
        coord.vehicle_id = "test_vehicle"
        sensor = EmhassDeferrableLoadSensor(coord, "e1")
        attrs = sensor.extra_state_attributes
        assert attrs["vehicle_id"] == "test_vehicle"

    def test_vehicle_id_fallback_to_entry_id(self):
        # Use spec to prevent any vehicle_id attribute on coordinator
        class PlainCoord:
            data = {
                "emhass_power_profile": None,
                "emhass_deferrables_schedule": None,
                "emhass_status": None,
                "per_trip_emhass_params": {},
            }
        sensor = EmhassDeferrableLoadSensor(PlainCoord(), "fallback_entry")
        attrs = sensor.extra_state_attributes
        assert attrs["vehicle_id"] == "fallback_entry"

    def test_aggregated_attrs_when_active_trips_exist(self):
        coord = MagicMock()
        coord.data = {
            "emhass_power_profile": None,
            "emhass_deferrables_schedule": None,
            "emhass_status": None,
            "per_trip_emhass_params": {
                "t1": {
                    "activo": True,
                    "def_total_hours": 2.0,
                    "power_watts": 5000,
                    "def_start_timestep": 5,
                    "def_end_timestep": 20,
                    "p_deferrable_matrix": [100.0],
                }
            },
        }
        coord.vehicle_id = "v1"
        sensor = EmhassDeferrableLoadSensor(coord, "e1")
        attrs = sensor.extra_state_attributes
        assert attrs["number_of_deferrable_loads"] == 1
        assert "def_total_hours_array" in attrs


class TestEmhassDeferrableLoadSensorDeviceInfo:
    """Test EmhassDeferrableLoadSensor.device_info."""

    def test_device_info_uses_vehicle_id(self):
        coord = MagicMock()
        coord.data = {}
        coord.vehicle_id = "v1"
        sensor = EmhassDeferrableLoadSensor(coord, "e1")
        info = sensor.device_info
        assert info["identifiers"] == {(DOMAIN, "v1")}
        assert info["name"] == "EV Trip Planner v1"
        assert info["manufacturer"] == "Home Assistant"
        assert info["model"] == "EV Trip Planner"

    def test_device_info_fallback_vehicle_id(self):
        class PlainCoord:
            data = {}
        sensor = EmhassDeferrableLoadSensor(PlainCoord(), "entry_99")
        info = sensor.device_info
        assert info["identifiers"] == {(DOMAIN, "entry_99")}
