from __future__ import annotations

import unittest

import phase58_validate_msii_multisymbol_registry as preflight


class RegistryPreflightTest(unittest.TestCase):
    def test_preflight_normalizes_symbols_and_freezes_registry_hash(self):
        payload = {
            "schemaVersion": 1,
            "workbook": "ArkMarketSpeed.xlsx",
            "symbols": [
                {"symbol": "7203", "marketSheet": "Market7203", "tickSheet": "Ticks7203"},
                {"symbol": "8306.T", "marketSheet": "Market8306", "tickSheet": "Ticks8306"},
            ],
        }
        first = preflight.build_registry_preflight(payload, source_path="registry.json")
        second = preflight.build_registry_preflight(payload, source_path="elsewhere.json")
        self.assertEqual(first["status"], "PHASE58_MSII_REGISTRY_PREFLIGHT_READY")
        self.assertEqual(first["symbolCount"], 2)
        self.assertEqual(first["symbols"], ["7203.T", "8306.T"])
        self.assertEqual(first["registrySha256"], second["registrySha256"])
        self.assertFalse(first["methodology"]["futureDynamicSelectionCoverageGuaranteed"])
        self.assertTrue(first["methodology"]["coverageMustBeMeasuredProspectively"])
        self.assertFalse(first["safety"]["rssOrderFunctionAllowed"])
        self.assertFalse(first["safety"]["liveTradingAllowed"])

    def test_preflight_reuses_capture_registry_fail_closed_validation(self):
        with self.assertRaisesRegex(ValueError, "sheet reused"):
            preflight.build_registry_preflight({
                "schemaVersion": 1,
                "symbols": [
                    {"symbol": "7203", "marketSheet": "Shared", "tickSheet": "Ticks7203"},
                    {"symbol": "8306", "marketSheet": "Shared", "tickSheet": "Ticks8306"},
                ],
            })


if __name__ == "__main__":
    unittest.main()
