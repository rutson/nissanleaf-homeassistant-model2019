import logging
import async_timeout
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.util import dt as dt_util

from .api import NissanConnectApi

_LOGGER = logging.getLogger(__name__)

DOMAIN = "nissan_connect"
PLATFORMS = ["sensor"]

SCAN_INTERVAL = timedelta(minutes=15)
API_TIMEOUT = 30  # seconds

# Charger cable sensor (true / false)
CABLE_SENSOR = "sensor.gsdbpugpjr_cable_connected_name"


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})

    api = NissanConnectApi(
        username=entry.data["username"],
        password=entry.data["password"],
    )

    try:
        await api.login()
    except Exception as err:
        _LOGGER.error("Failed to authenticate with Nissan Connect: %s", err)
        raise ConfigEntryNotReady from err

    if not api.vehicles:
        raise ConfigEntryNotReady("No vehicles found for this account")

    # --- manual refresh override flag ---
    manual_refresh_requested = False

    async def async_update_data() -> dict:
        """Fetch data from Nissan Connect API (conditionally)."""
        nonlocal manual_refresh_requested

        now = dt_util.utcnow()
        cable_state = hass.states.get(CABLE_SENSOR)

        # --- Guard: skip polling unless cable connected OR manual refresh ---
        if not manual_refresh_requested:
            if not cable_state or cable_state.state != "true":
                _LOGGER.debug(
                    "Skipping Nissan poll at %s (cable not connected, not manual)",
                    now,
                )
                return coordinator.data or {}

        _LOGGER.info(
            "Coordinator update started at %s (manual=%s, cable=%s)",
            now,
            manual_refresh_requested,
            cable_state.state if cable_state else "unknown",
        )

        data = {}

        try:
            async with async_timeout.timeout(API_TIMEOUT):
                for vehicle in api.vehicles:
                    vin = vehicle["vin"]
                    _LOGGER.info("Fetching battery data for %s", vin)

                    battery_data = await api.get_battery_status(
                        vin,
                        vehicle["can_generation"],
                        vehicle["model_name"],
                    )

                    data[vin] = {
                        "vehicle": vehicle,
                        "battery": battery_data,
                    }

            _LOGGER.info("Coordinator update finished successfully")
            return data

        except Exception as err:
            _LOGGER.error("Error fetching Nissan data: %s", err)
            raise UpdateFailed(err) from err

        finally:
            # Manual refresh is one-shot
            manual_refresh_requested = False

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=DOMAIN,
        update_method=async_update_data,
        update_interval=SCAN_INTERVAL,
        config_entry=entry,
    )

    # --- Manual refresh service ---
    async def async_manual_refresh(call: ServiceCall) -> None:
        nonlocal manual_refresh_requested
        manual_refresh_requested = True
        _LOGGER.info("Manual Nissan refresh requested")
        await coordinator.async_request_refresh()

    hass.services.async_register(
        DOMAIN,
        "manual_refresh",
        async_manual_refresh,
    )

    # First refresh (will only fetch if cable connected)
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = {
        "api": api,
        "coordinator": coordinator,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data[DOMAIN].pop(entry.entry_id)
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
