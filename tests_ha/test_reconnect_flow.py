"""Contarina on a real Home Assistant test instance: session keep-alive, options reload,
reauth/reconfigure browser reconnect (HTTP views) and an end-to-end run in Chrome."""
import base64
import json
import os
import shutil
import time
from unittest.mock import AsyncMock, patch
from urllib.parse import parse_qs, unquote, urlsplit

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

import custom_components.contarina  # noqa: F401  (patch targets)
import custom_components.contarina.config_flow  # noqa: F401
from custom_components.contarina.api import ContarinaAuthError
from custom_components.contarina.auth import ContarinaSession

CONTRACTS = [{"reference_code": "123", "name": "1", "end_date": None}]
GET_CONTRACTS = "custom_components.contarina.config_flow.ContarinaApi.get_contracts"
SETUP = "custom_components.contarina.async_setup_entry"


def jwt(acc="ACC1", minutes=50, age_minutes=None):
    b = lambda d: base64.urlsafe_b64encode(json.dumps(d).encode()).decode().rstrip("=")  # noqa: E731
    now = int(time.time())
    exp = now + 60 * minutes
    iat = exp - 3300 if age_minutes is None else now - 60 * age_minutes
    return f"{b({'alg': 'HS256'})}.{b({'exp': exp, 'iat': iat, 'crm_id': acc})}.sig"


def exp_of(token):
    p = token.split(".")[1]
    return json.loads(base64.urlsafe_b64decode(p + "=" * (-len(p) % 4)))["exp"]


async def _make_entry(hass, http_conf):
    assert await async_setup_component(hass, "http", {"http": http_conf})
    # Real HA disables aiohttp router freezing (http/server.py) so views can be added late;
    # the test client freezes it, so register before any client is created.
    from custom_components.contarina.reconnect import async_register_views
    async_register_views(hass)
    e = MockConfigEntry(domain="contarina", unique_id="ACC1",
                        data={"account_id": "ACC1", "access_token": jwt(), "contracts": ["123"]})
    e.add_to_hass(hass)
    return e


@pytest.fixture
async def entry(hass: HomeAssistant):
    return await _make_entry(hass, {})


@pytest.fixture
async def entry_behind_proxy(hass: HomeAssistant):
    return await _make_entry(hass, {"use_x_forwarded_for": True, "trusted_proxies": ["127.0.0.1"]})


class _Req:
    def __init__(self, base):
        self.headers = {"HA-Frontend-Base": base}


async def start(hass, entry, source, base="http://ha.test:8123"):
    """Simulate the frontend request context (HA-Frontend-Base), as HA's OAuth2 flows expect."""
    from homeassistant.components import http
    tok = http.current_request.set(_Req(base) if base else None)
    try:
        return (await _start(hass, entry, source, base))[:2]
    finally:
        http.current_request.reset(tok)


async def _start(hass, entry, source, base):
    with patch(SETUP, return_value=True):
        r = await (entry.start_reconfigure_flow(hass) if source == "reconfigure" else entry.start_reauth_flow(hass))
    assert r["type"] is FlowResultType.MENU and r["menu_options"] == ["reconnect_browser", "reconnect_paste"]
    r = await hass.config_entries.flow.async_configure(r["flow_id"], {"next_step_id": "reconnect_browser"})
    assert r["type"] is FlowResultType.EXTERNAL_STEP
    if base:
        assert r["url"].startswith(f"{base}/api/contarina/reconnect/start?"), r["url"]
    assert len(r["description_placeholders"]["code"]) == 9  # XXXX-XXXX shown in the HA dialog
    return r["flow_id"], parse_qs(urlsplit(r["url"]).query)["state"][0], r["url"]


async def post(client, payload, origin="same", extra=None):
    headers = dict(extra or {})
    if origin == "same":
        u = urlsplit(str(client.make_url("/")))
        headers["Origin"] = f"{u.scheme}://{u.netloc}"
    elif origin:
        headers["Origin"] = origin
    return await client.post("/api/contarina/reconnect/receive", json=payload, headers=headers)


# ------------------------------------------------------------------ session keep-alive
class _Api:
    def __init__(self):
        self.calls = 0

    async def refresh(self, token):
        self.calls += 1
        return jwt(minutes=55)


async def test_keepalive_refreshes_partially_used_token(hass, entry):
    hass.config_entries.async_update_entry(entry, data={**entry.data, "access_token": jwt(minutes=31)})
    api = _Api()
    s = ContarinaSession(hass, entry, api)
    await s.keepalive()
    assert api.calls == 1 and exp_of(entry.data["access_token"]) - time.time() > 54 * 60


async def test_keepalive_skips_fresh_token_and_rejects_expired(hass, entry):
    hass.config_entries.async_update_entry(entry, data={**entry.data, "access_token": jwt(minutes=54)})
    api = _Api()
    s = ContarinaSession(hass, entry, api)
    await s.keepalive()
    assert api.calls == 0
    hass.config_entries.async_update_entry(entry, data={**entry.data, "access_token": jwt(minutes=-1)})
    s = ContarinaSession(hass, entry, api)
    with pytest.raises(ContarinaAuthError):
        await s.keepalive()
    assert api.calls == 0


async def test_setup_refreshes_token_immediately_and_has_no_update_listener(hass, entry):
    hass.config_entries.async_update_entry(entry, data={**entry.data, "access_token": jwt(minutes=31)})
    with patch("custom_components.contarina.ContarinaApi.refresh", AsyncMock(return_value=jwt(minutes=55))) as ref, \
         patch("custom_components.contarina.coordinator.ContarinaCoordinator._async_update_data",
               AsyncMock(return_value={})), \
         patch("homeassistant.config_entries.ConfigEntries.async_forward_entry_setups", AsyncMock()):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED
    assert ref.await_count == 1
    assert exp_of(entry.data["access_token"]) - time.time() > 54 * 60
    assert entry.update_listeners == []


async def test_options_flow_reloads_once_without_listener(hass, entry):
    with patch(SETUP, return_value=True) as setup:
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        r = await hass.config_entries.options.async_init(entry.entry_id)
        r = await hass.config_entries.options.async_configure(r["flow_id"], {
            "calendar_horizon_days": 30, "poll_interval_hours": 6,
            "billing_interval_hours": 12, "include_condominium": False})
        await hass.async_block_till_done()
    assert r["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options["calendar_horizon_days"] == 30
    assert setup.call_count == 2  # initial setup + exactly one reload


# ------------------------------------------------------------------ browser reconnect (HTTP)
@pytest.mark.parametrize("source", ["reconfigure", "reauth"])
async def test_browser_reconnect_ok(hass, hass_client_no_auth, entry, source, caplog):
    flow_id, state = await start(hass, entry, source)
    client = await hass_client_no_auth()
    r = await client.get(f"/api/contarina/reconnect/start?flow_id={flow_id}&state={state}")
    assert r.status == 200 and "Invia token" in await r.text()
    assert r.headers["Referrer-Policy"] == "no-referrer" and "frame-ancestors" in r.headers["Content-Security-Policy"]
    assert (await client.get(f"/api/contarina/reconnect/start?flow_id={flow_id}&state={'x' * 43}")).status == 410
    new = jwt()
    with patch(GET_CONTRACTS, return_value=CONTRACTS), patch(SETUP, return_value=True):
        r = await post(client, {"flow_id": flow_id, "state": state, "token": new})
        body = await r.json()
        assert r.status == 200 and body["result"] == "ok", body
        assert entry.data["access_token"] == new
        assert (await post(client, {"flow_id": flow_id, "state": state, "token": new})).status == 403
        res = await hass.config_entries.flow.async_configure(flow_id)
        assert res["type"] is FlowResultType.ABORT
        assert res["reason"] == ("reconfigure_successful" if source == "reconfigure" else "reauth_successful")
        await hass.async_block_till_done()
    assert "update listener" not in caplog.text
    assert new not in caplog.text


async def test_external_url_is_absolute_and_falls_back(hass, entry):
    from homeassistant.components import http
    await hass.config.async_update(internal_url="http://192.168.1.10:8123")
    # no request context -> configured HA URL, absolute
    _, _, url = await _start(hass, entry, "reconfigure", None)
    assert url.startswith("http://192.168.1.10:8123/api/contarina/reconnect/start?")
    # malformed header is ignored, never echoed into the URL
    tok = http.current_request.set(_Req("javascript:alert(1)//"))
    try:
        _, _, url = await _start(hass, entry, "reauth", None)
    finally:
        http.current_request.reset(tok)
    assert url.startswith("http://192.168.1.10:8123/") and "javascript" not in url


async def test_no_url_falls_back_to_paste(hass, entry):
    from homeassistant.helpers.network import NoURLAvailableError
    with patch(SETUP, return_value=True):
        r = await entry.start_reconfigure_flow(hass)
    with patch("custom_components.contarina.config_flow.get_url", side_effect=NoURLAvailableError):
        r = await hass.config_entries.flow.async_configure(r["flow_id"], {"next_step_id": "reconnect_browser"})
    assert r["type"] is FlowResultType.FORM and r["step_id"] == "reconnect_paste"
    assert r["errors"] == {"base": "no_url"}


async def test_origin_is_enforced(hass, hass_client_no_auth, entry):
    flow_id, state = await start(hass, entry, "reconfigure")
    client = await hass_client_no_auth()
    payload = {"flow_id": flow_id, "state": state, "token": jwt()}
    for origin in (None, "null", "https://evil.example"):
        r = await post(client, payload, origin=origin)
        assert r.status == 403 and (await r.json())["result"] == "forbidden_origin"
    with patch(GET_CONTRACTS, return_value=CONTRACTS):  # state not consumed by refused origins
        assert (await post(client, payload)).status == 200


async def test_origin_scheme_and_port_must_match(hass, hass_client_no_auth, entry):
    flow_id, state = await start(hass, entry, "reconfigure")
    client = await hass_client_no_auth()
    u = urlsplit(str(client.make_url("/")))
    payload = {"flow_id": flow_id, "state": state, "token": jwt()}
    for origin in (f"https://{u.netloc}", f"http://{u.hostname}:{(u.port or 80) + 1}", f"http://{u.hostname}"):
        r = await post(client, payload, origin=origin)
        assert r.status == 403 and (await r.json())["result"] == "forbidden_origin", origin


async def test_untrusted_forwarded_headers_are_ignored_or_rejected(hass, hass_client_no_auth, entry):
    """No trusted proxy configured: X-Forwarded-Host can never make a foreign Origin acceptable."""
    flow_id, state = await start(hass, entry, "reconfigure")
    client = await hass_client_no_auth()
    payload = {"flow_id": flow_id, "state": state, "token": jwt()}
    # forwarded host alone: HA leaves request.host untouched -> foreign Origin refused by us
    r = await post(client, payload, origin="https://evil.example",
                   extra={"X-Forwarded-Host": "evil.example", "X-Forwarded-Proto": "https"})
    assert r.status == 403 and (await r.json())["result"] == "forbidden_origin"
    # full forwarded set from a proxy HA does not trust: rejected by HA before the view
    r = await post(client, payload, origin="https://evil.example",
                   extra={"X-Forwarded-For": "1.2.3.4", "X-Forwarded-Host": "evil.example",
                          "X-Forwarded-Proto": "https"})
    assert r.status == 400
    with patch(GET_CONTRACTS, return_value=CONTRACTS):  # state still unused
        assert (await post(client, payload)).status == 200


async def test_trusted_reverse_proxy_https(hass, hass_client_no_auth, entry_behind_proxy):
    """Trusted proxy: HA resolves scheme/host from X-Forwarded-*; Origin must match exactly."""
    flow_id, state = await start(hass, entry_behind_proxy, "reconfigure", base="https://ha.example.com")
    client = await hass_client_no_auth()
    fwd = {"X-Forwarded-For": "203.0.113.7", "X-Forwarded-Proto": "https", "X-Forwarded-Host": "ha.example.com"}
    payload = {"flow_id": flow_id, "state": state, "token": jwt()}
    for origin in ("http://ha.example.com", "https://ha.example.com:8443", "https://other.example.com"):
        r = await post(client, payload, origin=origin, extra=fwd)
        assert r.status == 403, origin
    with patch(GET_CONTRACTS, return_value=CONTRACTS):
        r = await post(client, payload, origin="https://ha.example.com", extra=fwd)
        assert r.status == 200 and (await r.json())["result"] == "ok"


# ------------------------------------------------------------------ first setup + pairing code
async def _start_setup(hass, base="http://ha.test:8123"):
    from homeassistant.components import http
    tok = http.current_request.set(_Req(base))
    try:
        r = await hass.config_entries.flow.async_init("contarina", context={"source": "user"})
        assert r["type"] is FlowResultType.MENU and r["menu_options"] == ["setup_browser", "setup_paste"]
        r = await hass.config_entries.flow.async_configure(r["flow_id"], {"next_step_id": "setup_browser"})
    finally:
        http.current_request.reset(tok)
    assert r["type"] is FlowResultType.EXTERNAL_STEP and r["url"].startswith(f"{base}/api/contarina/reconnect/start?")
    return r["flow_id"], parse_qs(urlsplit(r["url"]).query)["state"][0], r["description_placeholders"]["code"]


async def test_first_setup_from_browser(hass, hass_client_no_auth):
    assert await async_setup_component(hass, "http", {})
    from custom_components.contarina.reconnect import async_register_views
    async_register_views(hass)
    flow_id, state, _ = await _start_setup(hass)
    client = await hass_client_no_auth()
    token = jwt()
    with patch(GET_CONTRACTS, return_value=CONTRACTS):
        r = await post(client, {"flow_id": flow_id, "state": state, "token": token})
        body = await r.json()
    assert r.status == 200 and body["result"] == "ok_setup", body
    res = await hass.config_entries.flow.async_configure(flow_id)
    assert res["type"] is FlowResultType.FORM and res["step_id"] == "contracts"
    with patch(SETUP, return_value=True):
        res = await hass.config_entries.flow.async_configure(flow_id, {"contracts": ["123"]})
        await hass.async_block_till_done()
    assert res["type"] is FlowResultType.CREATE_ENTRY
    assert res["data"] == {"account_id": "ACC1", "access_token": token, "contracts": ["123"]}
    assert res["result"].unique_id == "ACC1"


async def test_first_setup_with_pairing_code_from_phone(hass, hass_client_no_auth):
    assert await async_setup_component(hass, "http", {})
    from custom_components.contarina.reconnect import async_register_views
    async_register_views(hass)
    flow_id, _, code = await _start_setup(hass)
    client = await hass_client_no_auth()
    with patch(GET_CONTRACTS, return_value=CONTRACTS):
        r = await post(client, {"code": code.lower(), "token": jwt()})
        assert r.status == 200 and (await r.json())["result"] == "ok_setup"
        assert (await post(client, {"code": code, "token": jwt()})).status == 403  # single use
    res = await hass.config_entries.flow.async_configure(flow_id)
    assert res["step_id"] == "contracts"


async def test_first_setup_already_configured(hass, hass_client_no_auth, entry):
    flow_id, state, _ = await _start_setup(hass)
    client = await hass_client_no_auth()
    with patch(GET_CONTRACTS, return_value=CONTRACTS):
        r = await post(client, {"flow_id": flow_id, "state": state, "token": jwt("ACC1")})
    assert r.status == 400 and (await r.json())["result"] == "already_configured"
    res = await hass.config_entries.flow.async_configure(flow_id)
    assert res["step_id"] == "setup_paste" and res["errors"] == {"base": "already_configured"}


async def test_first_setup_paste_still_works(hass):
    r = await hass.config_entries.flow.async_init("contarina", context={"source": "user"})
    r = await hass.config_entries.flow.async_configure(r["flow_id"], {"next_step_id": "setup_paste"})
    assert r["step_id"] == "setup_paste"
    with patch(GET_CONTRACTS, return_value=CONTRACTS):
        r = await hass.config_entries.flow.async_configure(r["flow_id"], {"access_token": jwt()})
    assert r["step_id"] == "contracts"


async def test_reconnect_with_pairing_code_and_guess_lockout(hass, hass_client_no_auth, entry):
    flow_id, _ = await start(hass, entry, "reconfigure")
    from custom_components.contarina.reconnect import get_store
    code = get_store(hass).code_for(flow_id)
    client = await hass_client_no_auth()
    wrong = "".join("A" if c != "A" else "B" for c in code)
    statuses = [(await post(client, {"code": wrong, "token": jwt()})).status for _ in range(10)]
    assert statuses[:9] == [403] * 9 and statuses[9] == 429
    r = await post(client, {"code": code, "token": jwt()})
    assert r.status == 429 and (await r.json())["result"] == "code_locked"


async def test_reconnect_with_pairing_code(hass, hass_client_no_auth, entry):
    flow_id, _ = await start(hass, entry, "reauth")
    from custom_components.contarina.reconnect import get_store
    code = get_store(hass).code_for(flow_id)
    client = await hass_client_no_auth()
    token = jwt()
    with patch(GET_CONTRACTS, return_value=CONTRACTS), patch(SETUP, return_value=True):
        r = await post(client, {"code": code, "token": token})
        assert r.status == 200 and (await r.json())["result"] == "ok"
        res = await hass.config_entries.flow.async_configure(flow_id)
        await hass.async_block_till_done()
    assert res["reason"] == "reauth_successful" and entry.data["access_token"] == token


# ------------------------------------------------------------------ expiry alerts
async def test_session_expired_alerts_once_and_clears(hass, entry):
    from homeassistant.components import persistent_notification as pn
    assert await async_setup_component(hass, "persistent_notification", {})
    pushes, events = [], []
    hass.services.async_register("notify", "mobile_app_phone", lambda call: pushes.append(call.data))
    hass.bus.async_listen("contarina_session_expired", lambda e: events.append(e.data))
    hass.config_entries.async_update_entry(entry, data={**entry.data, "access_token": jwt(minutes=-1)},
                                           options={"notify_service": "mobile_app_phone"})
    assert not await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.SETUP_ERROR
    notes = pn._async_get_or_create_notifications(hass)
    nid = f"contarina_session_expired_{entry.entry_id}"
    assert nid in notes and "/config/integrations/integration/contarina" in notes[nid]["message"]
    assert len(events) == 1 and events[0]["entry_id"] == entry.entry_id
    assert len(pushes) == 1 and pushes[0]["data"]["url"] == "/config/integrations/integration/contarina"
    assert any(f["context"]["source"] == "reauth" for f in hass.config_entries.flow.async_progress())
    # repeated failures do not spam
    from custom_components.contarina.alerts import async_session_expired
    async_session_expired(hass, entry)
    await hass.async_block_till_done()
    assert len(pushes) == 1 and len(events) == 1
    # successful setup dismisses the notification and re-arms the alert
    hass.config_entries.async_update_entry(entry, data={**entry.data, "access_token": jwt(minutes=54)})
    with patch("custom_components.contarina.coordinator.ContarinaCoordinator._async_update_data",
               AsyncMock(return_value={})), \
         patch("homeassistant.config_entries.ConfigEntries.async_forward_entry_setups", AsyncMock()):
        await hass.config_entries.async_reload(entry.entry_id)
        await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED
    assert nid not in pn._async_get_or_create_notifications(hass)


async def test_alert_without_notify_service_and_with_missing_service(hass, entry):
    from custom_components.contarina.alerts import async_session_expired
    events = []
    hass.bus.async_listen("contarina_session_expired", lambda e: events.append(1))
    hass.config_entries.async_update_entry(entry, options={"notify_service": "does_not_exist"})
    async_session_expired(hass, entry)  # must not raise
    await hass.async_block_till_done()
    assert events == [1]


async def test_wrong_account_falls_back_to_paste(hass, hass_client_no_auth, entry):
    flow_id, state = await start(hass, entry, "reconfigure")
    client = await hass_client_no_auth()
    old = entry.data["access_token"]
    with patch(GET_CONTRACTS, return_value=CONTRACTS):
        r = await post(client, {"flow_id": flow_id, "state": state, "token": jwt("OTHER")})
        assert r.status == 400 and (await r.json())["result"] == "wrong_account"
    assert entry.data["access_token"] == old
    res = await hass.config_entries.flow.async_configure(flow_id)
    assert res["type"] is FlowResultType.FORM and res["step_id"] == "reconnect_paste"
    assert res["errors"] == {"base": "wrong_account"}
    good = jwt()
    with patch(GET_CONTRACTS, return_value=CONTRACTS), patch(SETUP, return_value=True):
        res = await hass.config_entries.flow.async_configure(flow_id, {"access_token": good})
        assert res["type"] is FlowResultType.ABORT and res["reason"] == "reconfigure_successful"
        await hass.async_block_till_done()
    assert entry.data["access_token"] == good


async def test_bad_requests_and_aborted_flow(hass, hass_client_no_auth, entry):
    flow_id, state = await start(hass, entry, "reconfigure")
    client = await hass_client_no_auth()
    u = urlsplit(str(client.make_url("/")))
    r = await client.post("/api/contarina/reconnect/receive", data="x",
                          headers={"Origin": f"{u.scheme}://{u.netloc}"})
    assert r.status == 400
    assert (await post(client, {"flow_id": flow_id, "state": "y" * 43, "token": jwt()})).status == 403
    hass.config_entries.flow.async_abort(flow_id)
    assert (await post(client, {"flow_id": flow_id, "state": state, "token": jwt()})).status == 403


async def test_expired_token_refused(hass, hass_client_no_auth, entry):
    flow_id, state = await start(hass, entry, "reauth")
    client = await hass_client_no_auth()
    r = await post(client, {"flow_id": flow_id, "state": state, "token": jwt(minutes=-1)})
    assert r.status == 400 and (await r.json())["result"] == "invalid_auth"


# ------------------------------------------------------------------ end-to-end in Chrome
CHROME = os.environ.get("CHROME_PATH") or shutil.which("google-chrome") or shutil.which("chromium")


@pytest.mark.skipif(not CHROME, reason="Chrome/Chromium not available")
@pytest.mark.parametrize("mode", ["same_tab", "second_tab", "other_device"])
async def test_end_to_end_in_chrome(hass, hass_client_no_auth, entry, socket_enabled, mode):
    """Start page -> Apri SOL -> real bookmarklet href on a (locally served) SOL page -> HA."""
    playwright = pytest.importorskip("playwright.async_api")
    client = await hass_client_no_auth()
    u = urlsplit(str(client.make_url("/")))
    base = f"{u.scheme}://{u.netloc}"
    flow_id, state = await start(hass, entry, "reauth", base=base)
    start_url = f"{base}/api/contarina/reconnect/start?flow_id={flow_id}&state={state}"
    token = jwt()
    async with playwright.async_playwright() as pw:
        browser = await pw.chromium.launch(executable_path=CHROME, headless=True, args=["--no-sandbox"])
        ctx = await browser.new_context()
        await ctx.route("https://sol.servizicontarina.it/**", lambda route: route.fulfill(
            status=200, content_type="text/html", body="<html><body>SOL (fake)</body></html>"))
        await ctx.add_cookies([{"name": "accessToken", "value": token, "domain": "sol.servizicontarina.it",
                                "path": "/", "secure": True, "httpOnly": False}])
        page = await ctx.new_page()
        await page.goto(start_url)
        assert "state=" not in page.url  # state removed from the address bar
        href = await page.get_attribute("#bm", "href")
        assert href.startswith("javascript:")
        code = unquote(href[len("javascript:"):])
        assert state not in code and flow_id not in code  # bookmarklet holds no secret
        code_shown = (await page.inner_text("#pair")).strip()
        if mode == "other_device":
            # e.g. phone: separate browser profile, no local binding -> pairing code form
            ctx = await browser.new_context()
            await ctx.route("https://sol.servizicontarina.it/**", lambda route: route.fulfill(
                status=200, content_type="text/html", body="<html><body>SOL (fake)</body></html>"))
            await ctx.add_cookies([{"name": "accessToken", "value": token, "domain": "sol.servizicontarina.it",
                                    "path": "/", "secure": True, "httpOnly": False}])
            page = await ctx.new_page()
            await page.goto("https://sol.servizicontarina.it/")
        elif mode == "second_tab":
            page = await ctx.new_page()  # bookmarklet used in another tab: localStorage fallback
            await page.goto("https://sol.servizicontarina.it/")
        else:
            async with page.expect_navigation(url="https://sol.servizicontarina.it/**"):
                await page.click("a.go")
        with patch(GET_CONTRACTS, return_value=CONTRACTS), patch(SETUP, return_value=True):
            async with page.expect_navigation(url="**/api/contarina/reconnect/receive*"):
                # exactly what the browser runs from the bookmark; deferred so evaluate()
                # returns before the navigation destroys the execution context
                await page.evaluate("c => { setTimeout(() => (0, eval)(c), 0); }", code)
            if mode == "other_device":
                await page.locator("#codeform:not([hidden])").wait_for(timeout=10000)
                assert "#" not in page.url  # token already removed from the address bar
                await page.fill("#code", code_shown.lower())
                await page.click("#codeform button")
            await page.locator('#msg.ok, #msg.err').wait_for(timeout=10000)  # no eval: page CSP forbids it
            text = await page.inner_text("#msg")
            assert "ricollegata" in text, text
            assert "#" not in page.url  # token removed from the address bar
            if mode != "other_device":
                assert await page.evaluate("localStorage.getItem('contarina_reconnect')") is None
        with patch(SETUP, return_value=True):  # reload scheduled by the abort stays offline
            res = await hass.config_entries.flow.async_configure(flow_id)
            await hass.async_block_till_done()
        assert res["reason"] == "reauth_successful"
        assert entry.data["access_token"] == token
        await browser.close()
