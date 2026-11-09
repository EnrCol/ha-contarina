"""Authenticated PDF viewer endpoint and download service for Contarina invoices."""
from __future__ import annotations

import logging

import voluptuous as vol
from aiohttp import web
from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN
from .invoices import INVOICE_ID_RE, REF_RE, InvoiceError, async_download_missing, async_get_pdf, find_invoice

_LOGGER = logging.getLogger(__name__)
SERVICE_DOWNLOAD = "download_invoices"
PDF_HEADERS = {
    "Content-Type": "application/pdf",
    "Cache-Control": "no-store, private",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
}
_STATUS = {"session_expired": 409, "unavailable": 503, "not_found": 404, "storage": 500, "bad_path": 404}


class ContarinaInvoicePDFView(HomeAssistantView):
    """Serve invoice PDFs to authenticated HA users only, for loaded SOL accounts only."""

    url = "/api/contarina/invoice/{ref}/{invoice_id}"
    name = "api:contarina:invoice"
    requires_auth = True

    def __init__(self, hass: HomeAssistant) -> None:
        self._hass = hass

    async def get(self, request: web.Request, ref: str, invoice_id: str) -> web.StreamResponse:
        if not REF_RE.fullmatch(ref) or not INVOICE_ID_RE.fullmatch(invoice_id):
            raise web.HTTPNotFound()
        target = find_invoice(self._hass, ref, invoice_id)
        if target is None:
            raise web.HTTPNotFound()
        try:
            path, data = await async_get_pdf(self._hass, target)
        except InvoiceError as err:
            return web.json_response({"error": err.reason, "message": str(err)},
                                     status=_STATUS.get(err.reason, 503),
                                     headers={"Cache-Control": "no-store"})
        disposition = "attachment" if request.query.get("download") == "1" else "inline"
        filename = target.filename.rsplit("/", 1)[-1]  # "<number>_<id>.pdf"
        headers = {**PDF_HEADERS, "Content-Disposition": f'{disposition}; filename="contarina_{filename}"'}
        if path is not None:
            return web.FileResponse(path, headers=headers)
        return web.Response(body=data, headers=headers)


@callback
def async_register_invoice_features(hass: HomeAssistant) -> None:
    hass.http.register_view(ContarinaInvoicePDFView(hass))

    async def _download(call: ServiceCall) -> None:
        only = str(call.data.get("invoice_id") or "").strip() or None
        if only is not None and not INVOICE_ID_RE.fullmatch(only):
            raise HomeAssistantError("Contarina: identificativo fattura non valido")
        try:
            result = await async_download_missing(hass, only)
        except InvoiceError as err:
            raise HomeAssistantError(f"Contarina: {err}") from None
        _LOGGER.info("Contarina PDF: salvate=%s, già presenti=%s, errori=%s",
                     result["saved"], result["present"], result["errors"])
        if result["errors"]:
            raise HomeAssistantError(
                f"Contarina: {result['errors']} fatture non scaricate. "
                "Ritenta l'azione; i PDF già presenti vengono saltati."
            )

    hass.services.async_register(
        DOMAIN, SERVICE_DOWNLOAD, _download,
        schema=vol.Schema({vol.Optional("invoice_id"): cv.string}),
    )
