import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import NissanConnectApi

_LOGGER = logging.getLogger(__name__)

DOMAIN = "nissan_connect"
PLATFORMS = ["sensor"]

SCAN_INTERVAL = timedelta(minutes=15)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})

    api = NissanConnectApi(
        username=entry.data["username"],
        password=entry.data["password"],
    )

    try:
        await api.login()
    except Exception as err:
        raise ConfigEntryNotReady(err) from err

    if not api.vehicles:
        raise ConfigEntryNotReady("No vehicles found")

    async def async_update_data():
        data = {}
        try:
            for vehicle in api.vehicles:
                vin = vehicle["vin"]
                battery = await api.get_battery_status(
                    vin,
                    vehicle["can_generation"],
                    vehicle["model_name"],
                )
                data[vin] = {
                    "vehicle": vehicle,
                    "battery": battery,
                }
            return data
        except Exception as err:
            raise UpdateFailed(err) from err

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="nissan_connect",
        update_method=async_update_data,
        update_interval=SCAN_INTERVAL,
    )

    # IMPORTANT:
    # We do NOT block entity creation on first refresh
    await coordinator.async_refresh()

    hass.data[DOMAIN][entry.entry_id] = {
        "api": api,
        "vehicles": api.vehicles,
        "coordinator": coordinator,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
