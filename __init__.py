"""Nissan Connect integration for Home Assistant."""
import asyncio
import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .api import NissanConnectApi

_LOGGER = logging.getLogger(__name__)

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

    hass.data["nissan_connect"][entry.entry_id] = api

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data["nissan_connect"].pop(entry.entry_id)

    return unload_ok