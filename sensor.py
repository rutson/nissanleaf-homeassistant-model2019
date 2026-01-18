"""Sensor platform for Nissan Connect integration."""
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

from .api import NissanConnectApi

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=900)  # 15 minutes


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Nissan Connect sensor platform."""
    api: NissanConnectApi = hass.data["nissan_connect"][entry.entry_id]

    async def async_update_data() -> Dict[str, Any]:
        """Fetch data from API."""
        _LOGGER.info("Starting data update")
        try:
            data = {}
            for vehicle in api.vehicles:
                _LOGGER.info(f"Fetching battery data for {vehicle['vin']}")
                battery_data = await api.get_battery_status(
                    vehicle['vin'], vehicle['can_generation'], vehicle['model_name']
                )
                _LOGGER.info(f"Battery data received: {battery_data}")
                data[vehicle['vin']] = {
                    'vehicle': vehicle,
                    'battery': battery_data
                }
                _LOGGER.info(f"Got battery data for {vehicle['vin']}")
            _LOGGER.info("Data update completed successfully")
            return data
        except Exception as e:
            _LOGGER.error(f"Error fetching data: {e}")
            raise UpdateFailed(f"Error fetching data: {e}")

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="nissan_connect",
        update_method=async_update_data,
        update_interval=SCAN_INTERVAL,
    )

    await coordinator.async_config_entry_first_refresh()

    entities = []
    for vin, vehicle_data in coordinator.data.items():
        vehicle = vehicle_data['vehicle']
        battery = vehicle_data['battery']

        entities.append(
            NissanConnectBatterySensor(coordinator, vin, "battery_level", vehicle, battery)
        )
        entities.append(
            NissanConnectBatterySensor(coordinator, vin, "range_hvac_off", vehicle, battery)
        )
        entities.append(
            NissanConnectBatterySensor(coordinator, vin, "battery_bar_level", vehicle, battery)
        )
        entities.append(
            NissanConnectBatterySensor(coordinator, vin, "range_hvac_on", vehicle, battery)
        )
        entities.append(
            NissanConnectBatterySensor(coordinator, vin, "charge_power", vehicle, battery)
        )
        entities.append(
            NissanConnectBatterySensor(coordinator, vin, "plug_status", vehicle, battery)
        )
        entities.append(
            NissanConnectBatterySensor(coordinator, vin, "charge_status", vehicle, battery)
        )
        entities.append(
            NissanConnectBatterySensor(coordinator, vin, "lastUpdateTime", vehicle, battery)
        )
        entities.append(
            NissanConnectBatterySensor(coordinator, vin, "plugStatusDetail", vehicle, battery)
        )
        entities.append(
            NissanConnectBatterySensor(coordinator, vin, "timeRequiredToFullSlow", vehicle, battery)
        )
        entities.append(
            NissanConnectBatterySensor(coordinator, vin, "timeRequiredToFullNormal", vehicle, battery)
        )
        entities.append(
            NissanConnectBatterySensor(coordinator, vin, "timeRequiredToFullFast", vehicle, battery)
        )
        entities.append(
            NissanConnectBatterySensor(coordinator, vin, "batteryCapacity", vehicle, battery)
        )

    async_add_entities(entities)


class NissanConnectBatterySensor(CoordinatorEntity, SensorEntity):
    """Representation of a Nissan Connect battery sensor."""

    def __init__(self, coordinator, vin, sensor_type, vehicle, battery_data):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._vin = vin
        self._sensor_type = sensor_type
        self._vehicle = vehicle
        self._battery_data = battery_data

        self._attr_name = f"{vehicle['nickname']} {sensor_type.replace('_', ' ').title()}"
        self._attr_unique_id = f"{vin}_{sensor_type}"
        self._attr_device_info = {
            "identifiers": {(coordinator.config_entry.domain, vin)},
            "name": vehicle['nickname'],
            "manufacturer": "Nissan",
            "model": vehicle['model_name'],
        }

        if sensor_type == "battery_level":
            self._attr_device_class = SensorDeviceClass.BATTERY
            self._attr_state_class = SensorStateClass.MEASUREMENT
            self._attr_unit_of_measurement = "%"
            self._attr_native_unit_of_measurement = "%"
        elif sensor_type == "range_hvac_off":
            self._attr_device_class = SensorDeviceClass.DISTANCE
            self._attr_state_class = SensorStateClass.MEASUREMENT
            self._attr_unit_of_measurement = "km"
            self._attr_native_unit_of_measurement = "km"
        elif sensor_type == "battery_bar_level":
            self._attr_device_class = None
            self._attr_state_class = SensorStateClass.MEASUREMENT
            self._attr_unit_of_measurement = None  # Raw value
        elif sensor_type == "range_hvac_on":
            self._attr_device_class = SensorDeviceClass.DISTANCE
            self._attr_state_class = SensorStateClass.MEASUREMENT
            self._attr_unit_of_measurement = "km"
            self._attr_native_unit_of_measurement = "km"
        elif sensor_type == "charge_power":
            self._attr_device_class = SensorDeviceClass.POWER
            self._attr_state_class = SensorStateClass.MEASUREMENT
            self._attr_unit_of_measurement = "kW"
            self._attr_native_unit_of_measurement = "kW"
        elif sensor_type == "plug_status":
            self._attr_device_class = None
            self._attr_state_class = SensorStateClass.MEASUREMENT
            self._attr_unit_of_measurement = None
        elif sensor_type == "charge_status":
            self._attr_device_class = None
            self._attr_state_class = SensorStateClass.MEASUREMENT
            self._attr_unit_of_measurement = None
        elif sensor_type == "lastUpdateTime":
            self._attr_device_class = SensorDeviceClass.TIMESTAMP
            self._attr_state_class = None
            self._attr_unit_of_measurement = None
        elif sensor_type == "plugStatusDetail":
            self._attr_device_class = None
            self._attr_state_class = SensorStateClass.MEASUREMENT
            self._attr_unit_of_measurement = None
        elif sensor_type == "timeRequiredToFullSlow":
            self._attr_device_class = SensorDeviceClass.DURATION
            self._attr_state_class = SensorStateClass.MEASUREMENT
            self._attr_unit_of_measurement = "min"
            self._attr_native_unit_of_measurement = "min"
        elif sensor_type == "timeRequiredToFullNormal":
            self._attr_device_class = SensorDeviceClass.DURATION
            self._attr_state_class = SensorStateClass.MEASUREMENT
            self._attr_unit_of_measurement = "min"
            self._attr_native_unit_of_measurement = "min"
        elif sensor_type == "timeRequiredToFullFast":
            self._attr_device_class = SensorDeviceClass.DURATION
            self._attr_state_class = SensorStateClass.MEASUREMENT
            self._attr_unit_of_measurement = "min"
            self._attr_native_unit_of_measurement = "min"
        elif sensor_type == "batteryCapacity":
            self._attr_device_class = SensorDeviceClass.ENERGY
            self._attr_state_class = SensorStateClass.TOTAL
            self._attr_unit_of_measurement = "kWh"
            self._attr_native_unit_of_measurement = "kWh"
        

    @property
    def native_value(self) -> Optional[float]:
        """Return the state of the sensor."""
        battery = self.coordinator.data[self._vin]['battery']
        attributes = battery.get('data', {}).get('attributes', {})
        if self._sensor_type == "battery_level":
            return attributes.get('batteryLevel')
        elif self._sensor_type == "range_hvac_off":
            return attributes.get('rangeHvacOff')
        elif self._sensor_type == "battery_bar_level":
            return attributes.get('batteryBarLevel')
        elif self._sensor_type == "range_hvac_on":
            return attributes.get('rangeHvacOn')
        elif self._sensor_type == "charge_power":
            return attributes.get('chargePower')
        elif self._sensor_type == "plug_status":
            return attributes.get('plugStatus')
        elif self._sensor_type == "charge_status":
            return attributes.get('chargeStatus')
        elif self._sensor_type == "lastUpdateTime":
            time_str = attributes.get('lastUpdateTime')
            if time_str:
                # Parse ISO format string to datetime, handling 'Z' as UTC
                return datetime.fromisoformat(time_str.replace('Z', '+00:00'))
            return None
        elif self._sensor_type == "plugStatusDetail":
            return attributes.get('plugStatusDetail')
        elif self._sensor_type == "timeRequiredToFullSlow":
            return attributes.get('timeRequiredToFullSlow')
        elif self._sensor_type == "timeRequiredToFullNormal":
            return attributes.get('timeRequiredToFullNormal')
        elif self._sensor_type == "timeRequiredToFullFast":
            return attributes.get('timeRequiredToFullFast')
        elif self._sensor_type == "batteryCapacity":
            return attributes.get('batteryCapacity')
        return None

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional attributes."""
        battery = self.coordinator.data[self._vin]['battery']
        attributes = battery.get('data', {}).get('attributes', {})
        return {
            "vin": self._vin,
            "charge_power": attributes.get('chargePower'),
            "charge_status": attributes.get('chargeStatus'),
            "plug_status": attributes.get('plugStatus'),
        }