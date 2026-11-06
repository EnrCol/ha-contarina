"""Make an expired SOL session visible: persistent notification, event, optional push.

HA already creates a Repairs issue for every reauth flow; this adds what Repairs lacks:
a direct link, an event for automations and an optional push to the Companion app.
"""
from __future__ import annotations

import logging

from homeassistant.components import persistent_notification
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback

from .const import CONF_NOTIFY, DOMAIN, EVENT_SESSION_EXPIRED

_LOGGER = logging.getLogger(__name__)
DATA_ALERTED = f"{DOMAIN}_alerted"
LINK = f"/config/integrations/integration/{DOMAIN}"
TITLE = "Contarina SOL: sessione scaduta"
MESSAGE = (
    "La sessione dello Sportello Online Contarina è scaduta (Home Assistant è rimasto offline "
    "troppo a lungo). Apri [Contarina SOL]({link}) e scegli **Riconnetti dal browser**: "
    "accedi a SOL e usa il preferito «Invia token a Home Assistant». "
    "Dal telefono puoi usare il codice di abbinamento mostrato da Home Assistant."
)


def _notification_id(entry: ConfigEntry) -> str:
    return f"{DOMAIN}_session_expired_{entry.entry_id}"


@callback
def async_session_expired(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Alert once per expiry (deduplicated until the entry loads again)."""
    alerted: set[str] = hass.data.setdefault(DATA_ALERTED, set())
    if entry.entry_id in alerted:
        return
    alerted.add(entry.entry_id)
    persistent_notification.async_create(
        hass, MESSAGE.format(link=LINK), title=TITLE, notification_id=_notification_id(entry),
    )
    hass.bus.async_fire(EVENT_SESSION_EXPIRED, {"entry_id": entry.entry_id, "url": LINK})
    service = str(entry.options.get(CONF_NOTIFY) or "")
    if service and hass.services.has_service("notify", service):
        hass.async_create_task(_push(hass, service), eager_start=False)


async def _push(hass: HomeAssistant, service: str) -> None:
    try:
        await hass.services.async_call("notify", service, {
            "title": TITLE,
            "message": "Tocca per riconnettere Contarina SOL dal browser.",
            # Companion app: open the integration page when the notification is tapped.
            "data": {"url": LINK, "clickAction": LINK},
        }, blocking=True)
    except Exception:  # noqa: BLE001 - a broken notifier must never break the integration
        _LOGGER.warning("Contarina: push notification via notify.%s failed", service)


@callback
def async_session_restored(hass: HomeAssistant, entry: ConfigEntry) -> None:
    hass.data.setdefault(DATA_ALERTED, set()).discard(entry.entry_id)
    persistent_notification.async_dismiss(hass, _notification_id(entry))
