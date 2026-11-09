"""Contarina SOL: non-official read-only Home Assistant integration."""
from __future__ import annotations
from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.components.lovelace.const import LOVELACE_DATA
from homeassistant.components.lovelace.resources import ResourceStorageCollection
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_time_change, async_track_time_interval
from .alerts import async_session_expired, async_session_restored
from .api import ContarinaApi, ContarinaAuthError, ContarinaConnectionError
from .auth import ContarinaSession
from .const import CARD_URL_PATH, DOMAIN, TOKEN_REFRESH_INTERVAL
from .coordinator import ContarinaCoordinator
from .invoice_view import async_register_invoice_features
from .reconnect import async_register_views

PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR, Platform.CALENDAR]
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)
CARD_VERSION = "0.2.6b1"


async def _async_register_card(hass: HomeAssistant) -> None:
    """Bundled Lovelace card: static path + storage resource (YAML mode: extra JS url)."""
    www = Path(__file__).parent / "www"
    await hass.http.async_register_static_paths([
        StaticPathConfig(CARD_URL_PATH, str(www / "contarina-invoice-card.js"), False),
        # Bundled pdf.js (versioned URL, immutable content): cacheable.
        StaticPathConfig("/contarina_static/pdfjs", str(www / "pdfjs"), True),
    ])
    card_url = f"{CARD_URL_PATH}?v={CARD_VERSION}"
    lovelace_data = hass.data.get(LOVELACE_DATA)
    resources = lovelace_data.resources if lovelace_data else None
    if isinstance(resources, ResourceStorageCollection):
        await resources.async_get_info()
        existing = next((item for item in resources.async_items()
                         if (item.get("url") or "").split("?")[0] == CARD_URL_PATH), None)
        if existing is None:
            await resources.async_create_item({"res_type": "module", "url": card_url})
        elif existing.get("url") != card_url or existing.get("type") != "module":
            await resources.async_update_item(existing["id"], {"res_type": "module", "url": card_url})
    else:
        add_extra_js_url(hass, card_url)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Once per HA run: invoice card, authenticated PDF view and download action."""
    await _async_register_card(hass)
    async_register_invoice_features(hass)
    return True

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
