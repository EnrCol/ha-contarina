"""Invoice PDF viewer/archive on a Home Assistant test instance (no network)."""
import base64
import json
import time
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

import custom_components.contarina  # noqa: F401
from custom_components.contarina.api import ContarinaAuthError, ContarinaConnectionError

PDF = b"%PDF-1.4\n% contarina test\n"
PDF_API = "custom_components.contarina.api.ContarinaApi.invoice_pdf"
REFRESH = "custom_components.contarina.api.ContarinaApi.refresh"


def jwt(minutes=50):
    b = lambda d: base64.urlsafe_b64encode(json.dumps(d).encode()).decode().rstrip("=")  # noqa: E731
    n = int(time.time())
    return f"{b({'alg': 'HS256'})}.{b({'exp': n + 60 * minutes, 'iat': n - 60, 'crm_id': 'ACC1'})}.sig"


def invoice(i, number, issued, pdf=1, state=3):
    return {"id_fattura_emessa": i, "numero_fattura": number, "data_emissione": f"{issued}T00:00:00",
            "scadenza": f"{issued}T00:00:00", "stato_fattura": state, "tipo_perdita": 0,
            "tot_totalefatt": 100.0, "importo_pagato_totale": 100.0, "file_esistente": pdf}


INVOICES = [invoice(9001, "2026000123", "2026-03-10"), invoice(9002, "2025000777", "2025-02-01"),
            invoice(9003, "2024000001", "2024-01-15", pdf=-1)]


def coordinator_data():
    from custom_components.contarina.models import invoice_summary
    from datetime import date
    return {"123": {"contract": {"reference_code": "123", "name": "1", "tipologia_utenza_c": "1"},
                    "detail": {}, "containers": {}, "collections": {}, "invoices": INVOICES,
                    "invoice_summary": invoice_summary(INVOICES, 2026, date(2026, 11, 9)), "settled": True}}


@pytest.fixture
async def loaded(hass, tmp_path):
    hass.config.media_dirs = {"local": str(tmp_path)}
    entry = MockConfigEntry(domain="contarina", unique_id="ACC1",
                            data={"account_id": "ACC1", "access_token": jwt(54), "contracts": ["123"]})
    entry.add_to_hass(hass)
    with patch("custom_components.contarina.coordinator.ContarinaCoordinator._async_update_data",
               AsyncMock(return_value=coordinator_data())):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED
    return entry, tmp_path / "contarina" / "fatture"


async def test_view_requires_ha_authentication(hass, hass_client_no_auth, loaded):
    client = await hass_client_no_auth()
    assert (await client.get("/api/contarina/invoice/123/9001")).status == 401


async def test_unknown_unavailable_or_malformed_ids_are_404(hass, hass_client, loaded):
    client = await hass_client()
    with patch(PDF_API, AsyncMock(return_value=PDF)) as api:
        for path in ("/api/contarina/invoice/123/1", "/api/contarina/invoice/123/9003",
                     "/api/contarina/invoice/123/0", "/api/contarina/invoice/123/12a",
                     "/api/contarina/invoice/999/9001", "/api/contarina/invoice/12%203/9001"):
            assert (await client.get(path)).status == 404, path
        # traversal is already rejected by HA's security filter middleware
        assert (await client.get("/api/contarina/invoice/123/..%2F9001")).status in (400, 404)
    assert api.await_count == 0  # never asks SOL for invoices not in the loaded account / without PDF


async def test_fetch_on_first_view_then_serve_from_archive(hass, hass_client, loaded):
    _, root = loaded
    client = await hass_client()
    with patch(PDF_API, AsyncMock(return_value=PDF)) as api:
        r = await client.get("/api/contarina/invoice/123/9001")
        assert r.status == 200 and await r.read() == PDF
        assert r.headers["Content-Type"] == "application/pdf"
        assert r.headers["Content-Disposition"].startswith("inline;")
        assert r.headers["Cache-Control"] == "no-store, private"
        assert api.await_args.args[:2] == ("123", "9001")
        assert (root / "123" / "2026" / "2026000123_9001.pdf").read_bytes() == PDF
        r = await client.get("/api/contarina/invoice/123/9001?download=1")
        assert r.status == 200 and r.headers["Content-Disposition"].startswith("attachment;")
        assert await r.read() == PDF
    assert api.await_count == 1  # second request served from the local archive


async def test_unwritable_media_still_serves_pdf(hass, hass_client, loaded, tmp_path):
    blocker = tmp_path / "contarina"
    blocker.write_text("not a directory")  # makes the archive path impossible to create
    client = await hass_client()
    with patch(PDF_API, AsyncMock(return_value=PDF)):
        r = await client.get("/api/contarina/invoice/123/9002")
        assert r.status == 200 and await r.read() == PDF


@pytest.mark.parametrize(("exc", "status", "reason"), [
    (ContarinaAuthError("x"), 409, "session_expired"),
    (ContarinaConnectionError("x"), 503, "unavailable"),
])
async def test_sol_errors_are_reported_without_details(hass, hass_client, loaded, exc, status, reason):
    client = await hass_client()
    with patch(PDF_API, AsyncMock(side_effect=exc)), patch(REFRESH, AsyncMock(side_effect=exc)):
        r = await client.get("/api/contarina/invoice/123/9001")
        body = await r.json()
    assert r.status == status and body["error"] == reason and "9001" not in body["message"]


async def test_download_service_archives_missing_and_skips_existing(hass, loaded):
    _, root = loaded
    with patch(PDF_API, AsyncMock(return_value=PDF)) as api:
        await hass.services.async_call("contarina", "download_invoices", {}, blocking=True)
        assert api.await_count == 2  # 9003 has no PDF on SOL
        assert sorted(p.relative_to(root).as_posix() for p in root.rglob("*.pdf")) == [
            "123/2025/2025000777_9002.pdf", "123/2026/2026000123_9001.pdf"]
        await hass.services.async_call("contarina", "download_invoices", {}, blocking=True)
        assert api.await_count == 2  # nothing re-downloaded
        await hass.services.async_call("contarina", "download_invoices", {"invoice_id": "9001"}, blocking=True)
        assert api.await_count == 2


async def test_download_service_errors(hass, loaded):
    from homeassistant.exceptions import HomeAssistantError
    with pytest.raises(HomeAssistantError):
        await hass.services.async_call("contarina", "download_invoices", {"invoice_id": "1"}, blocking=True)
    with pytest.raises(HomeAssistantError):
        await hass.services.async_call("contarina", "download_invoices", {"invoice_id": "x/y"}, blocking=True)
    with patch(PDF_API, AsyncMock(side_effect=ContarinaConnectionError("x"))), pytest.raises(HomeAssistantError):
        await hass.services.async_call("contarina", "download_invoices", {}, blocking=True)


async def test_history_sensor_attributes_for_card_and_recorder_privacy(hass, loaded):
    states = [s for s in hass.states.async_all("sensor")
              if s.attributes.get("contarina_metric") == "invoice_history"]
    assert len(states) == 1
    attrs = states[0].attributes
    assert attrs["riepilogo_annuale"]["2026"]["numero_fatture"] == 1
    row = next(x for x in attrs["storico_fatture"] if x["id"] == "9001")
    assert row["pdf_disponibile"] is True and row["numero"] == "2026000123" and row["anno"] == 2026
    assert attrs["utenza"] == "123"
    assert next(x for x in attrs["storico_fatture"] if x["id"] == "9003")["pdf_disponibile"] is False
    from custom_components.contarina.sensor import ContarinaInvoiceHistorySensor
    assert {"storico_fatture", "riepilogo_annuale", "utenza"} <= ContarinaInvoiceHistorySensor._unrecorded_attributes


async def test_due_date_sensor_is_native_and_tracks_latest_issued_invoice(hass, loaded):
    from datetime import date

    from custom_components.contarina.sensor import (
        _last_invoice_deadline,
        _last_invoice_deadline_attributes,
    )
    from homeassistant.helpers import entity_registry as er

    registry = er.async_get(hass)
    records = [
        entry for entry in registry.entities.values()
        if entry.platform == "contarina"
        and entry.unique_id == "ACC1_123_scadenza_ultima_fattura"
    ]
    assert len(records) == 1
    state = hass.states.get(records[0].entity_id)
    assert state is not None
    assert state.state == "2026-03-10"
    assert state.attributes["device_class"] == "date"
    assert state.attributes["emissione"] == "2026-03-10"
    assert state.attributes["importo"] == 100.0
    assert state.attributes["stato"] == "paid"
    assert state.attributes["tipo_importo"] == "totale_fattura_non_residuo"

    # Scadenza = campo SOL della fattura più recente PER EMISSIONE,
    # anche quando un documento più vecchio ha una scadenza più lontana.
    data = {"invoices": [
        {"data_emissione": "2025-01-10", "scadenza": "2027-01-01",
         "tot_totalefatt": 30, "stato_fattura": 3, "tipo_perdita": 0},
        {"data_emissione": "2026-11-01T08:30:00", "scadenza": "2026-12-23",
         "tot_totalefatt": "127.12", "stato_fattura": 0, "tipo_perdita": 0},
    ]}
    assert _last_invoice_deadline(data) == date(2026, 12, 23)
    attrs = _last_invoice_deadline_attributes(data)
    assert attrs["emissione"] == "2026-11-01"
    assert attrs["importo"] == 127.12
    assert attrs["stato"] == "due"

    # Nessuna fattura o scadenza SOL non valida -> stato unavailable/unknown,
    # mai una data inventata o derivata dall'importo pagato.
    assert _last_invoice_deadline({"invoices": []}) is None
    assert _last_invoice_deadline_attributes({"invoices": []}) == {}
    assert _last_invoice_deadline({"invoices": [
        {"data_emissione": "2026-11-01", "scadenza": "non disponibile"}
    ]}) is None


async def test_card_is_served_and_registered_as_lovelace_resource(hass, hass_client, loaded):
    client = await hass_client()
    r = await client.get("/contarina_static/contarina-invoice-card.js")
    assert r.status == 200 and "contarina-invoice-card" in await r.text()
    from homeassistant.components.lovelace.const import LOVELACE_DATA
    resources = hass.data[LOVELACE_DATA].resources
    await resources.async_get_info()
    urls = [x["url"] for x in resources.async_items()]
    assert any(u.startswith("/contarina_static/contarina-invoice-card.js?v=") for u in urls)


async def test_services_registered_once(hass, loaded):
    assert hass.services.has_service("contarina", "download_invoices")


# ------------------------------------------------------------------ two utenze, same identifiers
PDF_A = b"%PDF-1.4\n% utenza A\n"
PDF_B = b"%PDF-1.4\n% utenza B\n"


def two_utenze_data():
    from custom_components.contarina.models import invoice_summary
    from datetime import date
    same_number = "2026000123"
    a = [invoice(9001, same_number, "2026-03-10"), invoice(7000, "X1", "2026-01-01")]
    b = [invoice(9555, same_number, "2026-03-10"), invoice(7000, "X1", "2026-01-01")]  # same numero; same id 7000
    data = {}
    for ref, inv in (("111", a), ("222", b)):
        data[ref] = {"contract": {"reference_code": ref, "name": ref, "tipologia_utenza_c": "1"},
                     "detail": {}, "containers": {}, "collections": {}, "invoices": inv,
                     "invoice_summary": invoice_summary(inv, 2026, date(2026, 11, 9)), "settled": True}
    return data


@pytest.fixture
async def two_utenze(hass, tmp_path):
    hass.config.media_dirs = {"local": str(tmp_path)}
    entry = MockConfigEntry(domain="contarina", unique_id="ACC1",
                            data={"account_id": "ACC1", "access_token": jwt(54), "contracts": ["111", "222"]})
    entry.add_to_hass(hass)
    with patch("custom_components.contarina.coordinator.ContarinaCoordinator._async_update_data",
               AsyncMock(return_value=two_utenze_data())):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    return tmp_path / "contarina" / "fatture"


def _pdf_by_utenza(ref, invoice_id, token):
    return PDF_A if ref == "111" else PDF_B


async def test_same_invoice_number_or_id_on_two_utenze_never_share_a_pdf(hass, hass_client, two_utenze):
    root = two_utenze
    client = await hass_client()
    with patch(PDF_API, AsyncMock(side_effect=_pdf_by_utenza)) as api:
        for ref, invoice_id, expected in (("111", "9001", PDF_A), ("222", "9555", PDF_B),
                                          ("111", "7000", PDF_A), ("222", "7000", PDF_B)):
            r = await client.get(f"/api/contarina/invoice/{ref}/{invoice_id}")
            assert r.status == 200 and await r.read() == expected, (ref, invoice_id)
        # second round comes from the archive and still matches the right utenza
        for ref, invoice_id, expected in (("222", "7000", PDF_B), ("111", "7000", PDF_A)):
            r = await client.get(f"/api/contarina/invoice/{ref}/{invoice_id}")
            assert await r.read() == expected
    assert api.await_count == 4
    files = sorted(p.relative_to(root).as_posix() for p in root.rglob("*.pdf"))
    assert files == ["111/2026/2026000123_9001.pdf", "111/2026/X1_7000.pdf",
                     "222/2026/2026000123_9555.pdf", "222/2026/X1_7000.pdf"]


async def test_concurrent_requests_fetch_once_and_serve_same_file(hass, hass_client, loaded):
    import asyncio
    client = await hass_client()
    calls = 0

    async def slow_pdf(ref, invoice_id, token):
        nonlocal calls
        calls += 1
        await asyncio.sleep(0.05)
        return PDF
    with patch(PDF_API, side_effect=slow_pdf):
        responses = await asyncio.gather(*(client.get("/api/contarina/invoice/123/9001") for _ in range(8)))
        bodies = [await r.read() for r in responses]
    assert all(r.status == 200 for r in responses) and set(bodies) == {PDF}
    assert calls == 1


# ------------------------------------------------------------------ viewer offline in Chrome
import os  # noqa: E402
import shutil  # noqa: E402

CHROME = os.environ.get("CHROME_PATH") or shutil.which("google-chrome") or shutil.which("chromium")


def _real_pdf() -> bytes:
    """Small, valid 2-page PDF (no external tools)."""
    objects = [b"<< /Type /Catalog /Pages 2 0 R >>",
               b"<< /Type /Pages /Kids [3 0 R 4 0 R] /Count 2 >>"]
    for page in (5, 6):
        objects.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 200] /Contents {page} 0 R "
                       f"/Resources << /Font << /F1 7 0 R >> >> >>".encode())
    for text in (b"Pagina 1", b"Pagina 2"):
        stream = b"BT /F1 24 Tf 40 100 Td (" + text + b") Tj ET"
        objects.append(b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream")
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    out, offsets = bytearray(b"%PDF-1.4\n"), []
    for i, body in enumerate(objects, 1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % i + body + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    out += b"".join(b"%010d 00000 n \n" % o for o in offsets)
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objects) + 1, xref)
    return bytes(out)


@pytest.mark.skipif(not CHROME, reason="Chrome/Chromium not available")
async def test_viewer_works_fully_offline_in_chrome(hass, hass_client, hass_access_token, loaded, socket_enabled):
    """Card + bundled pdf.js + authenticated view; every request outside HA is blocked."""
    playwright = pytest.importorskip("playwright.async_api")
    client = await hass_client()
    base = str(client.make_url("/")).rstrip("/")
    external = []
    with patch(PDF_API, AsyncMock(return_value=_real_pdf())):
        async with playwright.async_playwright() as pw:
            browser = await pw.chromium.launch(executable_path=CHROME, headless=True, args=["--no-sandbox"])
            ctx = await browser.new_context()

            async def guard(route):
                if route.request.url.startswith(base):
                    await route.continue_()
                else:
                    external.append(route.request.url)
                    await route.abort()
            await ctx.route("**/*", guard)
            page = await ctx.new_page()
            await page.goto(base + "/contarina_static/contarina-invoice-card.js")  # same origin as HA
            await page.set_content("<html><body></body></html>")
            await page.add_script_tag(type="module", content="""
              await import('/contarina_static/contarina-invoice-card.js');
              const card = document.createElement('contarina-invoice-card');
              card.setConfig({});
              document.body.appendChild(card);
              window.__card = card;
            """)
            await page.wait_for_function("() => !!window.__card")
            state = hass.states.get(next(s.entity_id for s in hass.states.async_all("sensor")
                                         if s.attributes.get("contarina_metric") == "invoice_history"))
            await page.evaluate("""([token, entityId, attrs]) => {
              window.__card.hass = {
                states: {[entityId]: {attributes: attrs}},
                fetchWithAuth: (url, init) => fetch(url, {...init, headers: {Authorization: 'Bearer ' + token}})
              };
            }""", [hass_access_token, state.entity_id, dict(state.attributes)])
            await page.get_by_role("button", name="Apri PDF").first.click()
            await page.locator("dialog canvas").wait_for(timeout=20000)
            indicator = page.locator("dialog span").first
            for _ in range(40):
                if (await indicator.inner_text()).strip() == "1 / 2":
                    break
                await page.wait_for_timeout(250)
            assert (await indicator.inner_text()).strip() == "1 / 2"
            await page.get_by_role("button", name="›").click()
            for _ in range(40):
                if (await indicator.inner_text()).strip() == "2 / 2":
                    break
                await page.wait_for_timeout(250)
            assert (await indicator.inner_text()).strip() == "2 / 2"
            # canvas actually painted (not blank)
            painted = await page.evaluate("""() => {
              const c = document.querySelector('body > div').shadowRoot.querySelector('canvas');
              const d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data;
              for (let i = 0; i < d.length; i += 4) if (d[i] < 128) return true;
              return false;
            }""")
            assert painted
            await browser.close()
    assert external == []  # nothing loaded from CDNs or any other host
