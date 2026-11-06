"""Contarina SOL: non-official read-only Home Assistant integration."""
from __future__ import annotations
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_time_change, async_track_time_interval
from .alerts import async_session_expired, async_session_restored
from .api import ContarinaApi, ContarinaAuthError, ContarinaConnectionError
from .auth import ContarinaSession
from .const import TOKEN_REFRESH_INTERVAL
from .coordinator import ContarinaCoordinator
from .reconnect import async_register_views

PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR, Platform.CALENDAR]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    # Before any auth check: the reauth flow's browser reconnect needs the views.
    async_register_views(hass)
    api = ContarinaApi(async_get_clientsession(hass))
    session = ContarinaSession(hass, entry, api)
    try:
        # Refresh at startup unless the token is <5 min old: full ~55 min of
        # validity from the first minute, not just "more than the margin".
        await session.keepalive()
    except ContarinaAuthError as exc:
        async_session_expired(hass, entry)
        raise ConfigEntryAuthFailed("Contarina browser login required") from exc
    except ContarinaConnectionError as exc:
        raise ConfigEntryNotReady("Contarina temporarily unavailable") from exc
    coordinator = ContarinaCoordinator(hass, entry, session)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    async_session_restored(hass, entry)

    async def refresh_token(_now) -> None:
        try:
            await session.keepalive()
        except ContarinaAuthError:
            async_session_expired(hass, entry)
            entry.async_start_reauth(hass)
        except ContarinaConnectionError:
            pass

    entry.async_on_unload(async_track_time_interval(hass, refresh_token, TOKEN_REFRESH_INTERVAL))

    def update_day(_now) -> None:
        coordinator.async_update_listeners()

    entry.async_on_unload(async_track_time_change(hass, update_day, hour=0, minute=0, second=1))
    # No update listener: options reload via OptionsFlowWithReload and reauth/reconfigure
    # reload via async_update_reload_and_abort (HA >= 2026.12 forbids mixing them).
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
