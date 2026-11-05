"""Contarina SOL: non-official read-only Home Assistant integration."""
from __future__ import annotations
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_time_change, async_track_time_interval
from .api import ContarinaApi, ContarinaAuthError, ContarinaConnectionError
from .auth import ContarinaSession
from .const import DOMAIN, TOKEN_REFRESH_INTERVAL
from .coordinator import ContarinaCoordinator

PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR, Platform.CALENDAR]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    api = ContarinaApi(async_get_clientsession(hass))
    session = ContarinaSession(hass, entry, api)
    try:
        await session.ensure_valid()
    except ContarinaAuthError as exc:
        raise ConfigEntryAuthFailed("Contarina browser login required") from exc
    except ContarinaConnectionError as exc:
        raise ConfigEntryNotReady("Contarina temporarily unavailable") from exc
    coordinator = ContarinaCoordinator(hass, entry, session)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    async def refresh_token(_now) -> None:
        try:
            await session.ensure_valid()
        except ContarinaAuthError:
            entry.async_start_reauth(hass)
        except ContarinaConnectionError:
            pass

    entry.async_on_unload(async_track_time_interval(hass, refresh_token, TOKEN_REFRESH_INTERVAL))

    def update_day(_now) -> None:
        coordinator.async_update_listeners()

    entry.async_on_unload(async_track_time_change(hass, update_day, hour=0, minute=0, second=1))
    previous_options = dict(entry.options)

    async def options_updated(_hass: HomeAssistant, current_entry: ConfigEntry) -> None:
        nonlocal previous_options
        if dict(current_entry.options) != previous_options:
            previous_options = dict(current_entry.options)
            await hass.config_entries.async_reload(current_entry.entry_id)

    entry.async_on_unload(entry.add_update_listener(options_updated))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
