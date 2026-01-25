"""Nissan Connect integration for Home Assistant."""
import asyncio
import logging
from datetime import timedelta
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

from .api import NissanConnectApi

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=900)  # 15 minutes

PLATFORMS = ["sensor"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Nissan Connect from a config entry."""
    hass.data.setdefault("nissan_connect", {})

    api = NissanConnectApi(
        username=entry.data["username"],
        password=entry.data["password"],
    )

    try:
        await api.login()
    except Exception as e:
        _LOGGER.error("Failed to authenticate with Nissan Connect: %s", e)
        raise ConfigEntryNotReady from e

    if not api.vehicles:
        _LOGGER.error("No vehicles found for this Nissan Connect account")
        raise ConfigEntryNotReady("No vehicles found for this account")

    async def async_update_data() -> dict:
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
        config_entry=entry,
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data["nissan_connect"][entry.entry_id] = {"api": api, "coordinator": coordinator}

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data["nissan_connect"].pop(entry.entry_id)

    return unload_ok