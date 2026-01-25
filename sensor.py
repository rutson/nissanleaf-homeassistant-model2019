"""Sensor platform for Nissan Connect integration."""
import logging
from datetime import datetime
from typing import Any, Dict, Optional

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

_LOGGER = logging.getLogger(__name__)

DOMAIN = "nissan_connect"

# Explicit mapping: sensor name -> Nissan API attribute (camelCase)
NISSAN_ATTR_MAP = {
    "battery_level": "batteryLevel",
    "range_hvac_off": "rangeHvacOff",
    "range_hvac_on": "rangeHvacOn",
    "battery_bar_level": "batteryBarLevel",
    "charge_power": "chargePower",
    "plug_status": "plugStatus",
    "charge_status": "chargeStatus",
    "plugStatusDetail": "plugStatusDetail",
    "timeRequiredToFullSlow": "timeRequiredToFullSlow",
    "timeRequiredToFullNormal": "timeRequiredToFullNormal",
    "timeRequiredToFullFast": "timeRequiredToFullFast",
    "batteryCapacity": "batteryCapacity",
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    entities = []

    for vin, vehicle_data in (coordinator.data or {}).items():
        vehicle = vehicle_data.get("vehicle", {})

        for sensor_type in [
            "battery_level",
            "range_hvac_off",
            "range_hvac_on",
            "battery_bar_level",
            "charge_power",
            "plug_status",
            "charge_status",
            "plugStatusDetail",
            "timeRequiredToFullSlow",
            "timeRequiredToFullNormal",
            "timeRequiredToFullFast",
            "batteryCapacity",
            "lastUpdateTime",
        ]:
            entities.append(
                NissanConnectBatterySensor(
                    coordinator,
                    vin,
                    sensor_type,
                    vehicle,
                )
            )

    async_add_entities(entities)


class NissanConnectBatterySensor(CoordinatorEntity, SensorEntity):
    """Representation of a Nissan Connect battery sensor."""

    def __init__(self, coordinator, vin, sensor_type, vehicle):
        super().__init__(coordinator)

        self._vin = vin
        self._sensor_type = sensor_type
        self._vehicle = vehicle
        self._last_value: Optional[Any] = None

        name = vehicle.get("nickname") or vin
        self._attr_name = f"{name} {sensor_type.replace('_', ' ').title()}"
        self._attr_unique_id = f"{vin}_{sensor_type}"

        self._attr_device_info = {
            "identifiers": {(DOMAIN, vin)},
            "manufacturer": "Nissan",
            "model": vehicle.get("model_name"),
            "name": name,
        }

        SENSOR_META = {
            "battery_level": (SensorDeviceClass.BATTERY, "%", SensorStateClass.MEASUREMENT),
            "range_hvac_off": (SensorDeviceClass.DISTANCE, "km", SensorStateClass.MEASUREMENT),
            "range_hvac_on": (SensorDeviceClass.DISTANCE, "km", SensorStateClass.MEASUREMENT),
            "battery_bar_level": (None, None, SensorStateClass.MEASUREMENT),
            "charge_power": (SensorDeviceClass.POWER, "kW", SensorStateClass.MEASUREMENT),
            "plug_status": (None, None, None),
            "charge_status": (None, None, None),
            "plugStatusDetail": (None, None, None),
            "timeRequiredToFullSlow": (SensorDeviceClass.DURATION, "min", SensorStateClass.MEASUREMENT),
            "timeRequiredToFullNormal": (SensorDeviceClass.DURATION, "min", SensorStateClass.MEASUREMENT),
            "timeRequiredToFullFast": (SensorDeviceClass.DURATION, "min", SensorStateClass.MEASUREMENT),
            "batteryCapacity": (SensorDeviceClass.ENERGY, "kWh", SensorStateClass.TOTAL),
            "lastUpdateTime": (SensorDeviceClass.TIMESTAMP, None, None),
        }

        device_class, unit, state_class = SENSOR_META[sensor_type]
        self._attr_device_class = device_class
        self._attr_native_unit_of_measurement = unit
        self._attr_state_class = state_class

    @property
    def native_value(self) -> Optional[Any]:
        data = self.coordinator.data or {}
        vehicle_data = data.get(self._vin, {})
        battery = vehicle_data.get("battery", {})
        attributes = battery.get("data", {}).get("attributes", {})

        value: Optional[Any] = None

        if self._sensor_type == "lastUpdateTime":
            ts = attributes.get("lastUpdateTime")
            if ts:
                value = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        else:
            attr_name = NISSAN_ATTR_MAP.get(self._sensor_type)
            if attr_name:
                value = attributes.get(attr_name)

        if value is not None:
            self._last_value = value
            return value

        # Keep last known value if Nissan returns cached / empty data
        return self._last_value

    @property
    def available(self) -> bool:
        # Sensor remains available as long as VIN exists
        return self._vin in (self.coordinator.data or {})

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        data = self.coordinator.data or {}
        vehicle_data = data.get(self._vin, {})
        battery = vehicle_data.get("battery", {})
        attributes = battery.get("data", {}).get("attributes", {})

        return {
            "vin": self._vin,
            "nissan_cache_age_s": battery.get("cache_age"),
            "nissan_status": battery.get("status"),
            "charge_status": attributes.get("chargeStatus"),
            "plug_status": attributes.get("plugStatus"),
        }
