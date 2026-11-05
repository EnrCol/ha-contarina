"""Pure unit tests; no Home Assistant installation or SOL credentials required."""
import base64
import importlib.util
import json
from datetime import date
from pathlib import Path
import unittest
path = Path(__file__).resolve().parents[1] / "custom_components" / "contarina" / "models.py"
spec = importlib.util.spec_from_file_location("contarina_models_under_test", path)
models = importlib.util.module_from_spec(spec)
spec.loader.exec_module(models)

def token(claims):
    payload = base64.urlsafe_b64encode(json.dumps(claims).encode()).decode().rstrip("=")
    return f"eyJhbGciOiJIUzI1NiJ9.{payload}.signature"

class ModelsTests(unittest.TestCase):
    def test_valid_jwt_exp(self):
        claims = models.jwt_claims(token({"exp": 123, "crm_id": "account"}))
        self.assertEqual(claims["exp"], 123)
        self.assertEqual(claims["crm_id"], "account")

    def test_malformed_jwt_rejected(self):
        for candidate in ("", "notajwt", "a.e30.b", "a.bad!!.c"):
            with self.subTest(candidate=candidate), self.assertRaises(models.ResponseShapeError):
                models.jwt_claims(candidate)

    def test_calendar_sorts_and_merges(self):
        raw = [
            {"data": "2026-11-08", "svuotamenti": [{"codice_contarina": "S", "titolo": "Secco"}]},
            {"data": "2026-11-06", "svuotamenti": [
                {"codice_contarina": "C", "titolo": "Carta"},
                {"codice_contarina": "U", "titolo": "Umido"},
            ]},
            {"data": "2026-11-07", "svuotamenti": []},
        ]
        parsed = models.calendar_dates(raw)
        self.assertEqual(list(parsed), [date(2026, 11, 6), date(2026, 11, 8)])
        self.assertEqual(parsed[date(2026, 11, 6)], ("Carta", "Umido"))
        self.assertEqual(models.next_collection(parsed, date(2026, 11, 6))[0], date(2026, 11, 6))

    def test_http200_error_payload_not_misread_as_emptyings(self):
        with self.assertRaises(models.ResponseShapeError):
            models.required_list({"Code": 400, "Message": "missing from"})

    def test_emptyings_year_and_duplicate_id(self):
        events = [
            {"id_vuotamento": 1, "data": "2026-01-02T11:00:00Z"},
            {"id_vuotamento": 1, "data": "2026-01-02T11:00:00Z"},
            {"id_vuotamento": 2, "data": "2026-09-03T00:00:00Z"},
            {"id_vuotamento": 3, "data": "2025-12-30T23:59:00Z"},
        ]
        self.assertEqual(models.count_emptyings(events, 2026), 2)
        self.assertEqual(models.last_emptying(events), date(2026, 9, 3))

    def test_emptying_record_uses_rome_date(self):
        self.assertEqual(models.emptying_local_date("2025-12-31T23:30:00Z"), date(2026, 1, 1))
        self.assertEqual(models.count_emptyings([
            {"id_vuotamento": 1, "data": "2025-12-31T23:30:00Z"}
        ], 2026), 1)

    def test_container_end_date_beats_attivo(self):
        item = {"ATTIVO": True, "DATA_FINE": "2025-01-01T00:00:00Z"}
        self.assertFalse(models.is_active(item, date(2026, 11, 5)))
        self.assertTrue(models.is_active({"ATTIVO": False, "DATA_FINE": None}, date(2026, 11, 5)))

    def test_invoice_status_map(self):
        cases = [
            (3, 0, "paid"), (9, 1, "paid"), (8, 0, "unpaid"),
            (1, 19, "unpaid"), (7, 0, "partially_paid"),
            (0, 0, "due"), (4, 0, "compensated"),
            (4, 23, "refund_due"), (4, 27, "non_refundable"),
            (42, 99, "cancelled"), (123, 1, "unknown"),
        ]
        for state, loss, expected in cases:
            with self.subTest(state=state, loss=loss):
                self.assertEqual(models.invoice_status({"stato_fattura": state, "tipo_perdita": loss}), expected)

    def test_latest_invoice_sorting(self):
        invoices = [
            {"data_emissione": "2024-01-01T00:00:00Z", "tot_totalefatt": 1},
            {"data_emissione": "2026-03-02T09:00:00Z", "tot_totalefatt": 2},
        ]
        self.assertEqual(models.latest_invoice(invoices)["tot_totalefatt"], 2)

    def test_balance_text_html(self):
        self.assertTrue(models.parse_balance(" true "))
        self.assertFalse(models.parse_balance("false"))
        with self.assertRaises(models.ResponseShapeError):
            models.parse_balance({"unknown": 0})

    def test_iso_ranges_are_full_datetime(self):
        self.assertEqual(models.iso_start(date(2026, 1, 1)), "2025-12-31T23:00:00.000Z")
        self.assertEqual(models.iso_end(date(2026, 12, 31)), "2026-12-31T22:59:59.999Z")

    def test_date_display_is_text_and_none_is_preserved(self):
        self.assertEqual(models.display_date(date(2026, 11, 5)), "05-11-2026")
        self.assertIsNone(models.display_date(None))

    def test_invoice_classification_by_deadline(self):
        today = date(2026, 11, 5)
        due = {"stato_fattura": 0, "tipo_perdita": 0}
        self.assertEqual(models.invoice_bucket({**due, "scadenza": "2026-12-23"}, today), "upcoming")
        self.assertEqual(models.invoice_bucket({**due, "scadenza": "2026-11-04"}, today), "overdue")
        self.assertEqual(models.invoice_bucket({**due, "scadenza": "2026-11-05"}, today), "upcoming")
        self.assertEqual(models.invoice_bucket({**due, "scadenza": None}, today), "review")
        self.assertIsNone(models.invoice_bucket({"stato_fattura": 3, "tipo_perdita": 0}, today))
        self.assertEqual(models.invoice_bucket(
            {"stato_fattura": 7, "tipo_perdita": 0, "scadenza": "2026-12-23"},
            today,
        ), "review")

    def test_invoice_summary_excludes_adjustments(self):
        invoices = [
            {"stato_fattura": 0, "tipo_perdita": 0, "data_emissione": "2026-10-01",
             "scadenza": "2026-12-23", "tot_totalefatt": 127.12, "importo_pagato_totale": 0},
            {"stato_fattura": 3, "tipo_perdita": 0, "data_emissione": "2026-03-01",
             "scadenza": "2026-05-01", "tot_totalefatt": 72.88, "importo_pagato_totale": 72.88},
            {"stato_fattura": 3, "tipo_perdita": 0, "data_emissione": "2025-01-01",
             "scadenza": "2025-02-01", "tot_totalefatt": 40},
            {"stato_fattura": 42, "tipo_perdita": 99, "data_emissione": "2026-04-01",
             "tot_totalefatt": 55},
            {"stato_fattura": 4, "tipo_perdita": 0, "data_emissione": "2026-04-02",
             "tot_totalefatt": 23.45},
            {"stato_fattura": 999, "tipo_perdita": 0, "data_emissione": "2026-04-03",
             "tot_totalefatt": 17},
        ]
        summary = models.invoice_summary(invoices, 2026, date(2026, 11, 5))
        self.assertEqual(summary["count"], 6)
        self.assertEqual(summary["open"], 1)
        self.assertEqual(summary["upcoming"], 1)
        self.assertEqual(summary["overdue"], 0)
        self.assertEqual(summary["review"], 0)
        self.assertEqual(summary["year_total"], 200.0)
        self.assertEqual(summary["year_totals"], {"2025": 40.0, "2026": 200.0})
        self.assertEqual(summary["excluded_count"], 3)
        self.assertEqual(summary["history"][0]["emissione"], "2026-10-01")
        self.assertEqual(summary["history"][0]["importo_pagato_registrato"], 0)
        self.assertEqual(summary["history"][0]["importo"], 127.12)

    def test_invoice_summary_unpaid_overdue_not_balance_claim(self):
        summary = models.invoice_summary([
            {"stato_fattura": 8, "tipo_perdita": 0,
             "data_emissione": "2026-01-01", "scadenza": "2026-02-01",
             "tot_totalefatt": "10.50"},
            {"stato_fattura": 7, "tipo_perdita": 0,
             "data_emissione": "2026-03-01", "scadenza": "2026-12-01",
             "tot_totalefatt": "12.50"},
            {"stato_fattura": 0, "tipo_perdita": 0,
             "data_emissione": "2026-04-01", "tot_totalefatt": "3.00"},
        ], 2026, date(2026, 11, 5))
        self.assertEqual(summary["year_total"], 26.0)
        self.assertEqual(summary["overdue"], 1)
        self.assertEqual(summary["upcoming"], 0)
        self.assertEqual(summary["review"], 2)

    def test_invoice_summary_rejects_invalid_amounts(self):
        summary = models.invoice_summary([
            {"stato_fattura": 3, "tipo_perdita": 0,
             "data_emissione": "2026-01-01", "tot_totalefatt": "NaN"},
            {"stato_fattura": 3, "tipo_perdita": 0,
             "data_emissione": "2026-02-01", "tot_totalefatt": "Infinity"},
            {"stato_fattura": 3, "tipo_perdita": 0,
             "data_emissione": "2026-03-01", "tot_totalefatt": "5.50"},
        ], 2026, date(2026, 11, 5))
        self.assertEqual(summary["year_total"], 5.50)
        self.assertEqual(summary["excluded_count"], 2)

    def test_invoice_history_attribute_limit(self):
        invoices = [
            {"stato_fattura": 3, "tipo_perdita": 0,
             "data_emissione": "2026-01-01", "tot_totalefatt": 1}
            for _ in range(70)
        ]
        summary = models.invoice_summary(invoices, 2026, date(2026, 11, 5))
        self.assertEqual(summary["count"], 70)
        self.assertEqual(summary["year_total"], 70.0)
        self.assertEqual(len(summary["history"]), 60)
        self.assertTrue(summary["history_truncated"])

    def test_last_emptying_across_years(self):
        historical = [
            {"id_vuotamento": 1, "data": "2024-04-12T09:00:00Z"},
            {"id_vuotamento": 2, "data": "2025-06-12T09:00:00Z"},
        ]
        self.assertEqual(models.count_emptyings(historical, 2026), 0)
        self.assertEqual(models.last_emptying(historical), date(2025, 6, 12))
        self.assertEqual(models.display_date(models.last_emptying(historical)), "12-06-2025")

    def test_material_names_are_readable_and_not_inferred_from_codes(self):
        cases = [
            ("Carta", "Carta"),
            ("Secco non riciclabile", "Secco"),
            ("Vetro Plastica Lattine", "VPL"),
            ("Umido", "Umido"),
            ("Vegetale", "Vegetale"),
            (None, "Contenitore"),
            ("Metallo", "Metallo"),
        ]
        for source, expected in cases:
            with self.subTest(material=source):
                self.assertEqual(models.material_label(source), expected)

if __name__ == "__main__":
    unittest.main()
