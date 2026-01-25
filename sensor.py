import logging
from datetime import datetime
from typing import Any, Optional

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

_LOGGER = logging.getLogger(__name__)

DOMAIN = "nissan_connect"

NISSAN_ATTR_MAP = {
    "battery_level": "batteryLevel",
    "range_hvac_off": "rangeHvacOff",
    "range_hvac_on": "rangeHvacOn",
    "charge_status": "chargeStatus",
    "plug_status": "plugStatus",
    "battery_bar_level": "batteryBarLevel",
    "battery_capacity": "batteryCapacity",
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]
    vehicles = data["vehicles"]

    entities = []

    for vehicle in vehicles:
        vin = vehicle["vin"]
        for sensor_type in list(NISSAN_ATTR_MAP) + ["last_update"]:
            entities.append(
                NissanBatterySensor(
                    coordinator,
                    vehicle,
                    vin,
                    sensor_type,
                )
            )

    async_add_entities(entities)


class NissanBatterySensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, vehicle, vin, sensor_type):
        super().__init__(coordinator)

        self._vin = vin
        self._vehicle = vehicle
        self._sensor_type = sensor_type
        self._last_value: Optional[Any] = None

        self._attr_unique_id = f"{vin}_{sensor_type}"
        self._attr_name = f"{vehicle.get('nickname', vin)} {sensor_type.replace('_', ' ').title()}"

        self._attr_device_info = {
            "identifiers": {(DOMAIN, vin)},
            "manufacturer": "Nissan",
            "model": vehicle.get("model_name"),
            "name": vehicle.get("nickname", vin),
        }

        if sensor_type == "battery_level":
            self._attr_device_class = SensorDeviceClass.BATTERY
            self._attr_native_unit_of_measurement = "%"

        if sensor_type == "last_update":
            self._attr_device_class = SensorDeviceClass.TIMESTAMP

    @property
    def native_value(self) -> Optional[Any]:
        data = self.coordinator.data or {}
        vehicle_data = data.get(self._vin)

        if not vehicle_data:
            return self._last_value

        battery = vehicle_data.get("battery", {})
        attributes = battery.get("data", {}).get("attributes", {})

        if self._sensor_type == "last_update":
            ts = attributes.get("lastUpdateTime")
            if ts:
                value = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                self._last_value = value
                return value
            return self._last_value

        attr = NISSAN_ATTR_MAP.get(self._sensor_type)
        if attr and attr in attributes:
            self._last_value = attributes[attr]
            return self._last_value

        return self._last_value

    @property
    def available(self) -> bool:
        # Entity exists even if data is missing
        return True
