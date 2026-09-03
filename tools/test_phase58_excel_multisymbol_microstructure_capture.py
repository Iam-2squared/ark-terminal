from __future__ import annotations

import unittest

import phase58_excel_multisymbol_microstructure_capture as multi


class _Range:
    def __init__(self, *, value=None, formula=None):
        self.Value = value
        self.Formula = formula if formula is not None else value


class _Sheet:
    def __init__(self, values, formulas=None):
        self.UsedRange = _Range(value=values, formula=formulas if formulas is not None else values)


class _Worksheets:
    def __init__(self, mapping):
        self.mapping = mapping

    def __call__(self, name):
        return self.mapping[name]


class _Workbook:
    def __init__(self, mapping):
        self.Worksheets = _Worksheets(mapping)


class MultiSymbolCaptureTest(unittest.TestCase):
    def test_registry_normalizes_and_rejects_sheet_reuse(self):
        registry = multi.validate_registry({
            "schemaVersion": 1,
            "symbols": [
                {"symbol": "7203", "marketSheet": "Market7203", "tickSheet": "Ticks7203"},
                {"symbol": "8306.T", "marketSheet": "Market8306", "tickSheet": "Ticks8306"},
            ],
        })
        self.assertEqual([row["symbol"] for row in registry["symbols"]], ["7203.T", "8306.T"])
        with self.assertRaisesRegex(ValueError, "sheet reused"):
            multi.validate_registry({
                "schemaVersion": 1,
                "symbols": [
                    {"symbol": "7203", "marketSheet": "Shared", "tickSheet": "Ticks7203"},
                    {"symbol": "8306", "marketSheet": "Shared", "tickSheet": "Ticks8306"},
                ],
            })

    def test_forbidden_order_formula_fails_closed(self):
        safe = _Sheet((("symbol",), ("7203",)), formulas=(("=RssMarket(A1)",), ("7203",)))
        multi.assert_read_only_formula_surface(safe, "safe")
        unsafe = _Sheet((("x",),), formulas=(("=RssStockOrder(A1,B1)",),))
        with self.assertRaisesRegex(RuntimeError, "forbidden RSS"):
            multi.assert_read_only_formula_surface(unsafe, "unsafe")

    def test_named_market_sheet_requires_exact_symbol(self):
        headers = ("symbol", "bestAsk", "bestBid", "bestAskSize", "bestBidSize", "bestAskTime", "bestBidTime")
        values = (headers, ("7203", 100.2, 100.0, 1000, 1000, "09:35:00", "09:35:00"))
        workbook = _Workbook({"Market7203": _Sheet(values)})
        row = multi.read_market_sheet_named(workbook, "Market7203", "7203.T")
        self.assertEqual(row["symbol"], "7203")
        with self.assertRaisesRegex(RuntimeError, "symbol mismatch"):
            multi.read_market_sheet_named(workbook, "Market7203", "8306.T")

    def test_named_tick_sheet_parses_spilled_header(self):
        values = (
            ("formula", None, None),
            ("RssTickList", None, None),
            ("時刻", "出来高", "約定値"),
            ("09:35:00.100", 200, 100.1),
        )
        workbook = _Workbook({"Ticks7203": _Sheet(values)})
        ticks = multi.read_tick_sheet_named(workbook, "Ticks7203")
        self.assertEqual(ticks, [{"time": "09:35:00.100", "volume": 200, "price": 100.1}])


if __name__ == "__main__":
    unittest.main()
