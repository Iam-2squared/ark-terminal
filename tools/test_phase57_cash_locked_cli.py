import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest.mock import patch

from phase57_cash_locked_cli import main, validate_request

LINEAGE={"sourceActionSha256":"a"*64,"sourceCashExecutionIntentSha256":"b"*64,"sourceIntentSha256":"c"*64,"sourceIntentId":"MSII_INTENT|fixture","strategyId":"V1_V3__MAX_3"}

def request(path="account snapshot.json"):
    return {
        "schemaId": "ARK_CASH_LOCKED_REQUEST_V1", "snapshotPath": str(path),
        "intent": {"symbol": "7203.T", "direction": "LONG", "side": "BUY",
                   "positionEffect": "OPEN", "quantity": 100, "orderType": "MARKET",
                   "limitPrice": None, "timeInForce": "DAY"},
        "externalPositions": [{"symbol": "123A", "quantity": 40}],
        "estimatedNotional": 300000.25,
    }

class CashLockedCliTests(unittest.TestCase):
    def test_named_fields_keep_numeric_types_and_separate_symbols(self):
        value = validate_request(json.loads(json.dumps(request())))
        self.assertEqual(value["intent"]["symbol"], "7203.T"); self.assertIs(type(value["intent"]["quantity"]), int)
        self.assertEqual(value["externalPositions"][0]["symbol"], "123A"); self.assertEqual(value["estimatedNotional"], 300000.25); self.assertEqual(value["arkManagedPositions"], [])

    def test_valid_upstream_lineage_is_accepted_and_invalid_hash_blocks(self):
        value=request(); value["upstreamLineage"]=dict(LINEAGE)
        self.assertEqual(validate_request(value)["upstreamLineage"],LINEAGE)
        bad=request(); bad["upstreamLineage"]={**LINEAGE,"sourceActionSha256":"nope"}
        with self.assertRaisesRegex(ValueError,"SOURCEACTIONSHA256_INVALID"): validate_request(bad)

    def test_managed_positions_are_explicit_and_cannot_overlap_external_inventory(self):
        value = request(); value["intent"].update({"side": "SELL", "positionEffect": "CLOSE"}); value["arkManagedPositions"] = [{"symbol": "7203.T", "quantity": 100}]
        self.assertEqual(validate_request(value)["arkManagedPositions"][0]["symbol"], "7203.T")
        overlap = request(); overlap["arkManagedPositions"] = [{"symbol": "123A.T", "quantity": 100}]
        with self.assertRaisesRegex(ValueError, "POSITION_OWNERSHIP_OVERLAP"): validate_request(overlap)

    def test_invalid_managed_position_identity_or_quantity_blocks(self):
        for row in ({"symbol": "", "quantity": 100}, {"symbol": "7203", "quantity": 0}, {"symbol": "7203", "quantity": "100"}):
            value = request(); value["arkManagedPositions"] = [row]
            with self.subTest(row=row), self.assertRaises(ValueError): validate_request(value)

    def test_blank_symbol_rejected_not_shifted_or_defaulted(self):
        for symbol in (None, "", " "):
            value = request(); value["intent"]["symbol"] = symbol
            with self.subTest(symbol=symbol), self.assertRaisesRegex(ValueError, "ORDER_SYMBOL_REQUIRED"): validate_request(value)

    def test_quantity_is_never_parsed_from_another_field(self):
        for qty in ("123A", "100", True, 100.5, 0, -100):
            value = request(); value["intent"]["quantity"] = qty
            with self.subTest(qty=qty), self.assertRaisesRegex(ValueError, "ORDER_QUANTITY"): validate_request(value)

    def test_nonfinite_notional_rejected(self):
        for amount in (float("nan"), float("inf"), "300000,25", True, -1):
            value = request(); value["estimatedNotional"] = amount
            with self.subTest(amount=amount), self.assertRaises(ValueError): validate_request(value)

    def test_cash_direction_and_effect_validated(self):
        for changes in ({"direction": "SHORT"}, {"positionEffect": "OTHER"}, {"side": "SELL"}):
            value = request(); value["intent"].update(changes)
            with self.subTest(changes=changes), self.assertRaises(ValueError): validate_request(value)

    def test_bom_unicode_paths_no_timestamp_rewrite(self):
        with tempfile.TemporaryDirectory(prefix="ark spaces ") as root:
            root = Path(root); snapshot_path = root / "口座 snapshot.json"; source = {"capturedAt": "2026-09-15T10:00:00+09:00", "buyingPower": 17}
            snapshot_path.write_text(json.dumps(source), encoding="utf-8-sig"); request_path = root / "request.json"; request_path.write_text(json.dumps(request(snapshot_path)), encoding="utf-8-sig"); output = root / "result.json"; original_bytes = snapshot_path.read_bytes()
            with patch("phase57_cash_locked_cli._evaluate", return_value={"status": "BLOCKED", "stage": "G6"}) as evaluate: self.assertEqual(main(["--request", str(request_path), "--output", str(output)]), 0)
            self.assertEqual(evaluate.call_args.args[0], source); self.assertEqual(snapshot_path.read_bytes(), original_bytes); result = json.loads(output.read_text(encoding="utf-8")); self.assertEqual(result["status"], "BLOCKED"); self.assertTrue(result["inspectionOnly"])

    def test_invalid_request_exits_nonzero_without_ready_output(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root); path = root / "request.json"; output = root / "result.json"; value = request(); value["intent"]["quantity"] = "123A"; path.write_text(json.dumps(value), encoding="utf-8")
            with redirect_stderr(io.StringIO()), patch("phase57_cash_locked_cli._evaluate") as evaluate: self.assertEqual(main(["--request", str(path), "--output", str(output)]), 2)
            evaluate.assert_not_called(); self.assertFalse(output.exists())

    def test_invalid_pipeline_response_does_not_produce_ready(self):
        for bad in ({}, {"status": "LOCKED_READY"}, {"status": "OK", "stage": "X"}):
            with tempfile.TemporaryDirectory() as root:
                root = Path(root); account = root / "snapshot.json"; path = root / "request.json"; output = root / "result.json"; account.write_text("{}", encoding="utf-8"); path.write_text(json.dumps(request(account)), encoding="utf-8")
                with redirect_stderr(io.StringIO()), patch("phase57_cash_locked_cli._evaluate", return_value=bad): self.assertEqual(main(["--request", str(path), "--output", str(output)]), 2)
                self.assertFalse(output.exists())

    def test_source_file_cannot_be_used_as_output(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root); account = root / "snapshot.json"; path = root / "request.json"; account.write_text("{}", encoding="utf-8"); path.write_text(json.dumps(request(account)), encoding="utf-8")
            with redirect_stderr(io.StringIO()): self.assertEqual(main(["--request", str(path), "--output", str(account)]), 2)
            self.assertEqual(account.read_text(), "{}")

if __name__ == "__main__": unittest.main()
