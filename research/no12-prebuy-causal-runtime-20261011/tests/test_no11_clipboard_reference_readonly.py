"""No.1.1: offline tests of 47x12 manual Excel clipboard RSS capture.

Synthetic cell values only. Does NOT certify exchange/RSS state or historical
market-time receipt. The importer never uses Excel COM, broker or model calls.
"""
import importlib.util
from pathlib import Path
import re
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "tools/no11_import_clipboard_reference_readonly.py"
SPEC = importlib.util.spec_from_file_location("no11_clipboard_test", SCRIPT)
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)
CODES = [f"{1000+i}.T" for i in range(47)]


def text_cells(*, code=None, rows=47, fields=12, missing=False):
    table=[]
    for i in range(rows):
        symbol = CODES[i] if code is None or i != 2 else code
        cells=[
            symbol,symbol[:4],"T","2026/10/27","2026/10/26",
            "" if missing and i==0 else "3,655","3655",
            "東証P", "100","2026/12/29","","2027/06/29",
        ]
        table.append("\t".join(cells[:fields]))
    return "\r\n".join(table) + "\r\n"


class StrictClipTests(unittest.TestCase):
    def test_47_exact_formulas_order_and_dates_with_crlf(self):
        cells = MOD.csv_rows(text_cells())
        self.assertEqual(len(cells), 47)
        self.assertEqual([len(r) for r in cells], [12] * 47)
        rows = MOD.convert_rows(cells, CODES)
        self.assertEqual(rows[0]["symbol"], "1000.T")
        self.assertEqual(rows[0]["marketCode"], "T")
        self.assertEqual(rows[0]["marketDate"], "2026-10-27")
        self.assertEqual(rows[0]["previousDate"], "2026-10-26")
        self.assertEqual(rows[0]["previousClose"], 3655)
        self.assertEqual(rows[0]["marketSection"], "東証P")
        self.assertEqual(rows[0]["exRightsDateRaw"], "2026/12/29")
        self.assertEqual(rows[0]["exDividendDateRaw"], "")
        self.assertEqual(rows[-1]["symbol"], CODES[-1])
        self.assertNotIn("corporateActionsCleared", rows[0])
        self.assertNotIn("priceBasisVerified", rows[0])

    def test_partial_or_extra_rows_columns_all_rejected(self):
        for value in [text_cells(rows=46), text_cells(fields=11),
                      text_cells(rows=47, fields=11), text_cells(rows=48)]:
            with self.assertRaisesRegex(ValueError, "EXACT_47_ROWS_12_FIELDS_REQUIRED"):
                MOD.csv_rows(value)

    def test_wrong_or_moved_ticker_rejected(self):
        with self.assertRaisesRegex(ValueError, "CLIPBOARD_SYMBOL_ORDER_MISMATCH"):
            MOD.convert_rows(MOD.csv_rows(text_cells(code="9999.T")), CODES)

    def test_missing_price_preserved_unknown_not_zero_or_reviewed(self):
        rows = MOD.convert_rows(MOD.csv_rows(text_cells(missing=True)), CODES)
        self.assertIsNone(rows[0]["previousClose"])
        self.assertEqual(rows[1]["previousClose"], 3655)

    def test_bad_clipboard_content_rejected(self):
        for text in ("hello world", "ARk\nMy bank password\tABC\n", "\x00"*200, ""):
            with self.assertRaisesRegex(ValueError, "CLIPBOARD_NOT_EXCEL_TABULAR_TEXT"):
                MOD.csv_rows(text)

    def test_unsupported_bad_date_is_unverified_not_fabricated(self):
        self.assertIsNone(MOD.date_cell("2026/99/99"))
        self.assertIsNone(MOD.date_cell(""))
        self.assertEqual(MOD.date_cell("2026/10/27"), "2026-10-27")
        self.assertEqual(MOD.date_cell("2026-10-26"), "2026-10-26")
        self.assertIsNone(MOD.number("not a price"))
        self.assertEqual(MOD.number("3,655"), 3655)

    def test_import_owns_no_excel_api_or_order_codes(self):
        source = SCRIPT.read_text(encoding="utf-8")
        for name in ("GetActiveObject(", "Excel.Application", "win32com",
                     "Workbooks.Open(", "RssStockOrder(", "RssCancelOrder(",
                     "EXTERNALLY_REVIEWED", "productionReady\": True",
                     "orderTransmission\": True"):
            self.assertNotIn(name, source)
        for name in ("original.scope(plan_file, mask_file)",
                     '"originalFormulaVerifiedByThisImporter": False',
                     '"priorFrozenDecisionsMayBeBackfilled": False',
                     '"knownAtJstNotBefore": source["completedAtJst"]',
                     '"corporateActionReviewPerformed": False'):
            self.assertIn(name, source)


if __name__ == "__main__":
    unittest.main()
