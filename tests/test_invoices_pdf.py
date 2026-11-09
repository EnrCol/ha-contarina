"""Invoice PDF: history identifiers, API download validation and atomic archive (no HA, no network)."""
import asyncio
import importlib.util
import sys
import tempfile
import types
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "custom_components" / "contarina"
PACKAGE = "_isolated_contarina"
if PACKAGE not in sys.modules:
    package = types.ModuleType(PACKAGE)
    package.__path__ = [str(ROOT)]
    sys.modules[PACKAGE] = package
for module_name in ("const", "models", "api"):
    name = f"{PACKAGE}.{module_name}"
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, ROOT / (module_name + ".py"))
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
api = sys.modules[f"{PACKAGE}.api"]
models = sys.modules[f"{PACKAGE}.models"]

# invoices.py imports homeassistant.core only for typing: stub it.
if "homeassistant.core" not in sys.modules:
    ha = types.ModuleType("homeassistant"); core = types.ModuleType("homeassistant.core")
    core.HomeAssistant = object; sys.modules.setdefault("homeassistant", ha); sys.modules["homeassistant.core"] = core
name = f"{PACKAGE}.invoices"
if name not in sys.modules:
    spec = importlib.util.spec_from_file_location(name, ROOT / "invoices.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
invoices = sys.modules[name]

PDF = b"%PDF-1.4\n%fake\n"


def inv(**kw):
    base = {"id_fattura_emessa": 9001, "numero_fattura": "2026000123", "data_emissione": "2026-03-10T00:00:00",
            "scadenza": "2026-04-10T00:00:00", "stato_fattura": 3, "tipo_perdita": 0,
            "tot_totalefatt": 120.5, "importo_pagato_totale": 120.5, "file_esistente": 1}
    base.update(kw)
    return base


class HistoryTest(unittest.TestCase):
    def test_history_has_pdf_identifiers_and_year_summary(self):
        s = models.invoice_summary([inv(), inv(id_fattura_emessa=9002, numero_fattura="2025000777",
                                                data_emissione="2025-02-01T00:00:00", file_esistente=-1)],
                                   2026, date(2026, 11, 9))
        first, second = s["history"]
        self.assertEqual((first["id"], first["numero"], first["anno"], first["pdf_disponibile"]),
                         ("9001", "2026000123", 2026, True))
        self.assertFalse(second["pdf_disponibile"])  # file_esistente == -1 is "absent", not truthy
        self.assertEqual(s["per_year"], {"2026": {"numero_fatture": 1, "totale_fatturato": 120.5},
                                         "2025": {"numero_fatture": 1, "totale_fatturato": 120.5}})

    def test_unsafe_identifiers_are_dropped(self):
        h = models.invoice_summary([inv(id_fattura_emessa="../1", numero_fattura="a/b")], 2026, date(2026, 1, 1))["history"][0]
        self.assertIsNone(h["id"]); self.assertIsNone(h["numero"]); self.assertFalse(h["pdf_disponibile"])
        for bad in (True, 0, -3, "abc", "", None, 10**13):
            self.assertIsNone(models.invoice_pdf_id({"id_fattura_emessa": bad}), bad)
        self.assertEqual(models.invoice_pdf_id({"id_fattura_emessa": "0042"}), "42")

    def test_excluded_documents_are_counted_but_not_totalled(self):
        s = models.invoice_summary([inv(), inv(id_fattura_emessa=9003, stato_fattura=41)], 2026, date(2026, 6, 1))
        self.assertEqual(s["per_year"]["2026"], {"numero_fatture": 2, "totale_fatturato": 120.5})


class PdfResponse:
    def __init__(self, body=PDF, status=200, content_type="application/pdf", length=None, chunk=4):
        self.status, self.content_type, self._body = status, content_type, body
        self.content_length = len(body) if length is None else length
        outer = self

        class _Content:
            async def iter_chunked(self, size):
                for i in range(0, len(outer._body), chunk):
                    yield outer._body[i:i + chunk]
        self.content = _Content()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return None


class Session:
    def __init__(self, response):
        self.response, self.calls = response, []

    def get(self, url, **kw):
        self.calls.append((url, kw))
        return self.response


class ApiPdfTest(unittest.TestCase):
    def run_pdf(self, response, ref="123", invoice_id="9001"):
        session = Session(response)
        client = api.ContarinaApi(session)
        return asyncio.run(client.invoice_pdf(ref, invoice_id, "jwt")), session

    def test_valid_pdf_and_endpoint(self):
        data, session = self.run_pdf(PdfResponse())
        self.assertEqual(data, PDF)
        url, kw = session.calls[0]
        self.assertTrue(url.endswith("/api/contracts/123/bill/9001/file"))
        self.assertEqual(kw["headers"]["Authorization"], "Bearer jwt")
        self.assertFalse(kw["allow_redirects"])

    def test_rejections(self):
        cases = [
            (PdfResponse(status=401), api.ContarinaAuthError),
            (PdfResponse(status=500), api.ContarinaConnectionError),
            (PdfResponse(content_type="text/html"), api.ContarinaConnectionError),
            (PdfResponse(body=b"<html>no</html>"), api.ContarinaConnectionError),
            (PdfResponse(length=50 * 1024 * 1024), api.ContarinaConnectionError),
        ]
        for response, exc in cases:
            with self.assertRaises(exc):
                self.run_pdf(response)

    def test_stream_size_limit_without_content_length(self):
        big = b"%PDF-" + b"0" * (api.PDF_MAX_BYTES + 10)
        with self.assertRaises(api.ContarinaConnectionError):
            self.run_pdf(PdfResponse(body=big, length=None, chunk=1024 * 1024), invoice_id="1")

    def test_unsafe_identifiers(self):
        with self.assertRaises(api.ContarinaConnectionError):
            self.run_pdf(PdfResponse(), invoice_id="../x")


class ArchiveTest(unittest.TestCase):
    def test_relative_name_is_unique_per_utenza_and_id(self):
        self.assertEqual(invoices._relative_name("123", inv(), "9001"), "123/2026/2026000123_9001.pdf")
        self.assertEqual(invoices._relative_name("123", inv(numero_fattura=""), "9001"), "123/2026/fattura_9001.pdf")
        self.assertIsNone(invoices._relative_name("123", inv(data_emissione=None), "9001"))
        self.assertIsNone(invoices._relative_name("../x", inv(), "9001"))
        # same invoice number on two utenze, or same number with different ids: never the same file
        names = {invoices._relative_name("123", inv(), "9001"), invoices._relative_name("456", inv(), "9001"),
                 invoices._relative_name("123", inv(), "9002")}
        self.assertEqual(len(names), 3)

    def test_store_is_atomic_and_never_overwrites(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "contarina" / "fatture"
            self.assertTrue(invoices.store_pdf(root, "123/2026/1_9.pdf", PDF))
            self.assertFalse(invoices.store_pdf(root, "123/2026/1_9.pdf", b"%PDF-other"))
            self.assertEqual((root / "123/2026/1_9.pdf").read_bytes(), PDF)
            self.assertEqual([p.name for p in (root / "123/2026").iterdir()], ["1_9.pdf"])  # no .part left
            self.assertEqual(invoices.local_file(root, "123/2026/1_9.pdf"), root / "123/2026/1_9.pdf")
            self.assertIsNone(invoices.local_file(root, "123/2026/2_9.pdf"))

    def test_file_created_between_check_and_publish_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "123/2026/1_9.pdf"
            real_link = invoices.os.link

            def racing_link(src, dst):
                Path(dst).write_bytes(b"%PDF-winner")  # another writer publishes first
                return real_link(src, dst)
            invoices.os.link = racing_link
            try:
                self.assertFalse(invoices.store_pdf(root, "123/2026/1_9.pdf", PDF))
            finally:
                invoices.os.link = real_link
            self.assertEqual(target.read_bytes(), b"%PDF-winner")
            self.assertEqual([p.name for p in target.parent.iterdir()], ["1_9.pdf"])

    def test_concurrent_writers_exactly_one_wins_and_file_is_complete(self):
        import threading
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            payloads = [b"%PDF-" + bytes([65 + i]) * 200_000 for i in range(16)]
            results, barrier = [None] * 16, threading.Barrier(16)

            def worker(i):
                barrier.wait()
                results[i] = invoices.store_pdf(root, "123/2026/1_9.pdf", payloads[i])
            threads = [threading.Thread(target=worker, args=(i,)) for i in range(16)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()
            self.assertEqual(results.count(True), 1)
            stored = (root / "123/2026/1_9.pdf").read_bytes()
            self.assertEqual(stored, payloads[results.index(True)])  # complete, never mixed or truncated
            self.assertEqual([p.name for p in (root / "123/2026").iterdir()], ["1_9.pdf"])

    def test_fallback_without_hard_links_is_still_exclusive(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            real_link = invoices.os.link

            def no_links(src, dst):
                raise OSError(95, "Operation not supported")
            invoices.os.link = no_links
            try:
                self.assertTrue(invoices.store_pdf(root, "123/2026/1_9.pdf", PDF))
                self.assertFalse(invoices.store_pdf(root, "123/2026/1_9.pdf", b"%PDF-other"))
            finally:
                invoices.os.link = real_link
            self.assertEqual((root / "123/2026/1_9.pdf").read_bytes(), PDF)
            self.assertEqual([p.name for p in (root / "123/2026").iterdir()], ["1_9.pdf"])

    def test_symlink_and_traversal_escape_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "archive"; (root / "2026").mkdir(parents=True)
            outside = Path(tmp) / "secret.pdf"; outside.write_bytes(PDF)
            (root / "2026" / "evil.pdf").symlink_to(outside)
            self.assertIsNone(invoices.local_file(root, "2026/evil.pdf"))
            self.assertIsNone(invoices.local_file(root, "../secret.pdf"))
            with self.assertRaises(invoices.InvoiceError):
                invoices.store_pdf(root, "../x.pdf", PDF)


class BundledPdfJsTest(unittest.TestCase):
    def test_pdfjs_is_bundled_pinned_and_card_has_no_cdn(self):
        import hashlib
        www = ROOT / "www"
        sums = dict(reversed(line.split()) for line in (www / "pdfjs" / "SHA256SUMS").read_text().splitlines())
        for name in ("pdf.min.mjs", "pdf.worker.min.mjs"):
            self.assertEqual(hashlib.sha256((www / "pdfjs" / name).read_bytes()).hexdigest(), sums[name])
        self.assertIn("Apache License", (www / "pdfjs" / "LICENSE").read_text())
        card = (www / "contarina-invoice-card.js").read_text()
        self.assertNotIn("https://", card)
        self.assertIn("/contarina_static/pdfjs/pdf.min.mjs", card)
        self.assertIn("isEvalSupported: false", card)


if __name__ == "__main__":
    unittest.main()
