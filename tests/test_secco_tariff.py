"""Unit tests for the conservative Contarina Secco tariff threshold."""
from __future__ import annotations
import importlib.util
from pathlib import Path
import unittest

path = Path(__file__).resolve().parents[1] / "custom_components" / "contarina" / "models.py"
spec = importlib.util.spec_from_file_location("contarina_models_tariff", path)
models = importlib.util.module_from_spec(spec)
spec.loader.exec_module(models)


class SeccoMinimumTests(unittest.TestCase):
    def calculate(self, members, liters, actual, domestic=True, count=1):
        return models.secco_minimum_120l(
            members, liters, actual, is_domestic=domestic, secco_container_count=count
        )

    def test_domestic_three_people_and_120_liters(self):
        value = self.calculate("3", "120", 1)
        self.assertEqual(value["minimo_annuo_stimato"], 4)
        self.assertEqual(value["svuotamenti_prima_eccedenza"], 3)
        self.assertEqual(value["svuotamenti_oltre_minimo"], 0)
        self.assertTrue(value["verifica_componenti_31_12_precedente"])

    def test_exact_threshold_and_excess(self):
        self.assertEqual(self.calculate(3, 120, 4)["svuotamenti_prima_eccedenza"], 0)
        self.assertEqual(self.calculate(3, 120, 5)["svuotamenti_oltre_minimo"], 1)

    def test_non_domestic_not_inferred(self):
        self.assertEqual(self.calculate(3, 120, 1, domestic=False), {})

    def test_other_capacities_not_inferred(self):
        for liters in (40, 80, 240, None):
            with self.subTest(liters=liters):
                self.assertEqual(self.calculate(3, liters, 1), {})

    def test_multiple_secco_bins_not_inferred(self):
        self.assertEqual(self.calculate(3, 120, 1, count=2), {})

    def test_missing_or_invalid_components(self):
        for members in (None, 0, -1, "abc", 3.5, True):
            with self.subTest(members=members):
                self.assertEqual(self.calculate(members, 120, 1), {})

    def test_invalid_emptyings(self):
        for actual in (None, -1, 2.5, False):
            with self.subTest(actual=actual):
                self.assertEqual(self.calculate(3, 120, actual), {})


if __name__ == "__main__":
    unittest.main()
