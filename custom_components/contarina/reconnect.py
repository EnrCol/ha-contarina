"""HTTP views for the browser reconnect (external step of the reauth/reconfigure flow)."""
from __future__ import annotations

from aiohttp import web
from homeassistant.components.http import KEY_HASS, HomeAssistantView
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import UnknownFlow
from homeassistant.helpers.network import is_cloud_connection

from .const import CONF_TOKEN, DOMAIN
from .pairing import (
    MAX_BODY_BYTES, OUTCOME_MESSAGES, RECEIVE_PATH, SECURITY_HEADERS, START_PATH,
    PendingStore, origin_allowed, parse_receive_body, receive_page, start_page,
)

DATA_STORE = f"{DOMAIN}_reconnect_store"
DATA_VIEWS = f"{DOMAIN}_reconnect_views"


@callback
def get_store(hass: HomeAssistant) -> PendingStore:
    store = hass.data.get(DATA_STORE)
    if store is None:
        store = hass.data[DATA_STORE] = PendingStore()
    return store


@callback
def async_register_views(hass: HomeAssistant) -> None:
    """Idempotent: views are registered once per HA run."""
    if hass.data.get(DATA_VIEWS):
        return
    hass.data[DATA_VIEWS] = True
    get_store(hass)
    hass.http.register_view(ReconnectStartView())
    hass.http.register_view(ReconnectReceiveView())


def _html(text: str, status: int = 200) -> web.Response:
    return web.Response(text=text, status=status, content_type="text/html", charset="utf-8",
                        headers=SECURITY_HEADERS)


def _json(result: str, status: int) -> web.Response:
    return web.json_response(
        {"result": result, "message": OUTCOME_MESSAGES.get(result, "Riconnessione non riuscita.")},
        status=status, headers={k: v for k, v in SECURITY_HEADERS.items() if k != "Content-Security-Policy"},
    )


class ReconnectStartView(HomeAssistantView):
    """Opened by the HA frontend from the external step; authorized by the one-time state."""

    url = START_PATH
    name = "api:contarina:reconnect:start"
    requires_auth = False  # same model as HA's OAuth2 external callback: the state is the authorization

    async def get(self, request: web.Request) -> web.Response:
        hass = request.app[KEY_HASS]
        store = get_store(hass)
        flow_id = request.query.get("flow_id", "")
        valid = store.is_valid(flow_id, request.query.get("state", ""))
        # The pairing code is shown only to whoever holds the flow's one-time state.
        return _html(start_page(valid, store.code_for(flow_id) or "" if valid else ""), 200 if valid else 410)


class ReconnectReceiveView(HomeAssistantView):
    """GET: static page reading the JWT from the URL fragment. POST: same-origin delivery."""

    url = RECEIVE_PATH
    name = "api:contarina:reconnect:receive"
    requires_auth = False

    async def get(self, request: web.Request) -> web.Response:
        return _html(receive_page())

    async def post(self, request: web.Request) -> web.Response:
        hass = request.app[KEY_HASS]
        # request.scheme/host already reflect trusted-proxy headers (HA forwarded middleware);
        # Nabu Casa remote UI terminates TLS inside HA and is always https.
        scheme = "https" if is_cloud_connection(hass) else request.scheme
        if not origin_allowed(request.headers.get("Origin"), scheme, request.host):
            return _json("forbidden_origin", 403)
        if request.content_type != "application/json" or (request.content_length or 0) > MAX_BODY_BYTES:
            return _json("bad_request", 400)
        parsed = parse_receive_body(await request.content.read(MAX_BODY_BYTES + 1))
        if parsed is None:
            return _json("bad_request", 400)
        store = get_store(hass)
        if parsed[0] == "code":
            _, code, token = parsed
            if store.code_locked():
                return _json("code_locked", 429)
            flow_id = store.consume_code(code)
            if flow_id is None:
                return _json("code_locked" if store.code_locked() else "bad_code", 429 if store.code_locked() else 403)
        else:
            _, flow_id, state, token = parsed
            if store.consume(flow_id, state) is None:
                return _json("expired", 403)
        try:
            await hass.config_entries.flow.async_configure(flow_id, {CONF_TOKEN: token})
        except UnknownFlow:
            store.discard(flow_id)
            return _json("expired", 410)
        outcome = store.pop_outcome(flow_id) or "cannot_connect"
        return _json(outcome, 200 if outcome.startswith("ok") else 400)
