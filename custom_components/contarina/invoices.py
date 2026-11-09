"""Invoice PDFs: on-demand retrieval from SOL and a private local archive.

PDFs are fetched only on explicit request (card button or `contarina.download_invoices`),
never by the periodic refresh. Files are stored under the Home Assistant local media
folder (`<media>/contarina/fatture/<year>/<number>.pdf`), so they are also visible in
Media → My media. Never log tokens, URLs, invoice identifiers or document contents.

Archive layout is unique per utenza and SOL invoice id:
`<media>/contarina/fatture/<utenza>/<year>/<number>_<id>.pdf`.
"""
from __future__ import annotations

import asyncio
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from homeassistant.core import HomeAssistant

from .api import ContarinaAuthError, ContarinaConnectionError
from .const import ARCHIVE_SUBDIR, DOMAIN
from .models import SAFE_INVOICE_NUMBER, date_only, invoice_pdf_id

INVOICE_ID_RE = re.compile(r"[1-9][0-9]{0,11}")
REF_RE = re.compile(r"[A-Za-z0-9_-]{1,64}")
DATA_LOCK = f"{DOMAIN}_invoice_lock"


class InvoiceError(Exception):
    """Safe-to-display failure (no identifiers, URLs or document contents)."""

    def __init__(self, reason: str, message: str) -> None:
        super().__init__(message)
        self.reason = reason


@dataclass(frozen=True)
class InvoiceRef:
    coordinator: Any
    ref: str
    invoice: dict[str, Any]
    invoice_id: str
    filename: str  # "<utenza>/<year>/<number>_<id>.pdf"


def archive_root(hass: HomeAssistant) -> Path:
    media = (hass.config.media_dirs or {}).get("local") or hass.config.path("media")
    return Path(media).joinpath(*ARCHIVE_SUBDIR)


def _relative_name(ref: str, invoice: dict[str, Any], invoice_id: str) -> str | None:
    if not REF_RE.fullmatch(str(ref)) or not INVOICE_ID_RE.fullmatch(invoice_id):
        return None
    issued = date_only(invoice.get("data_emissione"))
    if issued is None or not 2000 <= issued.year <= 2100:
        return None
    number = str(invoice.get("numero_fattura") or "").strip()
    stem = number if SAFE_INVOICE_NUMBER.fullmatch(number) else "fattura"
    return f"{ref}/{issued.year}/{stem}_{invoice_id}.pdf"


def _targets(hass: HomeAssistant):
    for entry in hass.config_entries.async_loaded_entries(DOMAIN):
        coordinator = getattr(entry, "runtime_data", None)
        for ref, info in ((coordinator.data or {}) if coordinator else {}).items():
            for invoice in info.get("invoices") or []:
                invoice_id = invoice_pdf_id(invoice)
                if invoice_id is None or invoice.get("file_esistente") != 1:
                    continue
                name = _relative_name(str(ref), invoice, invoice_id)
                if name is not None:
                    yield InvoiceRef(coordinator, str(ref), invoice, invoice_id, name)


def find_invoice(hass: HomeAssistant, ref: str, invoice_id: str) -> InvoiceRef | None:
    """Exact (utenza, id) match among loaded SOL accounts, with a PDF available on SOL."""
    if not REF_RE.fullmatch(ref or "") or not INVOICE_ID_RE.fullmatch(invoice_id or ""):
        return None
    return next((t for t in _targets(hass) if t.ref == ref and t.invoice_id == invoice_id), None)


def all_invoices(hass: HomeAssistant) -> list[InvoiceRef]:
    return list(_targets(hass))


def _safe_path(root: Path, relative: str) -> Path:
    path = root / relative
    if not path.resolve().is_relative_to(root.resolve()):
        raise InvoiceError("bad_path", "Percorso PDF non valido")
    return path


def local_file(root: Path, relative: str) -> Path | None:
    """Executor: archived file if present and inside the archive (no symlink escapes)."""
    try:
        path = _safe_path(root, relative)
    except (InvoiceError, OSError):
        return None
    return path if path.is_file() else None


def store_pdf(root: Path, relative: str, data: bytes) -> bool:
    """Executor: atomic, exclusive create. Returns False if the file already exists.

    The complete file is written to a temporary name and then published with os.link(),
    which fails with FileExistsError if the destination appeared meanwhile: an existing
    archived invoice is never overwritten and readers never see a partial file. On
    filesystems without hard links, falls back to O_CREAT|O_EXCL on the final path.
    """
    path = _safe_path(root, relative)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return False
    fd, temporary = tempfile.mkstemp(prefix=".contarina-", suffix=".part", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as output:
            output.write(data)
            output.flush()
            os.fsync(output.fileno())
        try:
            os.link(temporary, path)
            return True
        except FileExistsError:
            return False
        except OSError:
            return _store_exclusive(path, data)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _store_exclusive(path: Path, data: bytes) -> bool:
    """Fallback without hard links: exclusive create of the final path."""
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0), 0o644)
    except FileExistsError:
        return False
    try:
        with os.fdopen(fd, "wb") as output:
            output.write(data)
            output.flush()
            os.fsync(output.fileno())
    except BaseException:
        path.unlink(missing_ok=True)  # never leave a truncated invoice behind
        raise
    return True


async def fetch_pdf(target: InvoiceRef) -> bytes:
    try:
        return await target.coordinator.session.call("invoice_pdf", target.ref, target.invoice_id)
    except ContarinaAuthError:
        raise InvoiceError("session_expired", "Sessione SOL scaduta: riconnetti l'integrazione") from None
    except ContarinaConnectionError:
        raise InvoiceError("unavailable", "PDF non disponibile da Contarina SOL in questo momento") from None


async def async_get_pdf(hass: HomeAssistant, target: InvoiceRef) -> tuple[Path | None, bytes | None]:
    """Archived file if present, otherwise fetch from SOL and archive it.

    If the media folder is not writable the bytes are still returned for this request.
    """
    root = archive_root(hass)
    path = await hass.async_add_executor_job(local_file, root, target.filename)
    if path is not None:
        return path, None
    async with hass.data.setdefault(DATA_LOCK, asyncio.Lock()):
        path = await hass.async_add_executor_job(local_file, root, target.filename)
        if path is not None:
            return path, None
        data = await fetch_pdf(target)
        try:
            await hass.async_add_executor_job(store_pdf, root, target.filename, data)
        except (OSError, InvoiceError):
            return None, data
        path = await hass.async_add_executor_job(local_file, root, target.filename)
        return (path, None) if path is not None else (None, data)


async def async_download_missing(hass: HomeAssistant, only_id: str | None = None) -> dict[str, int]:
    """Archive every missing PDF (or one). Returns saved / present / errors counters."""
    targets = all_invoices(hass)
    if only_id:
        targets = [t for t in targets if t.invoice_id == only_id]
        if not targets:
            raise InvoiceError("not_found", "Fattura non trovata o senza PDF su Contarina SOL")
    root = archive_root(hass)
    counters = {"saved": 0, "present": 0, "errors": 0}
    async with hass.data.setdefault(DATA_LOCK, asyncio.Lock()):
        for target in targets:
            if await hass.async_add_executor_job(local_file, root, target.filename):
                counters["present"] += 1
                continue
            try:
                data = await fetch_pdf(target)
                saved = await hass.async_add_executor_job(store_pdf, root, target.filename, data)
            except InvoiceError as err:
                if err.reason == "session_expired":
                    raise
                counters["errors"] += 1
                continue
            except OSError:
                raise InvoiceError("storage", "Impossibile salvare i PDF nella cartella media") from None
            counters["saved" if saved else "present"] += 1
    return counters
