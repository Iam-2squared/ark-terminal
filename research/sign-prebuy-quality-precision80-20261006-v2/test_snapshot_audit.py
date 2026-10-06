import copy
import unittest
from snapshot_audit import audit_snapshot_views, timestamp


class AuditTest(unittest.TestCase):
    def inputs(self):
        snapshots = [{"entry_id": "2025-01-06|TEST_A", "numeric": {"entry/intent_clock": 600, "p0/a": None, "p0/b": 1.0}}]
        meta = [{"entry_id": snapshots[0]["entry_id"], "session": "2025-01-06", "execution_eligible": True}]
        prov = [{"entry_id": snapshots[0]["entry_id"], "G_PRICE": {"source_available_at": "2025-01-06T10:01:00+09:00", "feature_as_of": "2025-01-06T10:00:00+09:00", "valid_from": "2025-01-06T10:00:00+09:00"}}]
        registry = {"groups": {"G_PRICE": ["p0/a", "p0/b"]}}
        return snapshots, meta, prov, registry

    def test_cell_and_entry_denominators_are_distinct(self):
        out = audit_snapshot_views(*self.inputs())["groups"]["G_PRICE"]
        self.assertEqual((out["cell_denominator"], out["missing_cells"]), (2, 1))
        self.assertEqual(out["missing_cell_rate"], .5)
        self.assertEqual(out["entry_any_missing_rate"], 1)

    def test_after_intent_diagnostic_does_not_certify(self):
        out = audit_snapshot_views(*self.inputs())
        self.assertEqual(out["groups"]["G_PRICE"]["intent_boundary_receipt_counts"]["source_available_at_after_intent"], 1)
        self.assertFalse(out["actual_arrival_verified"])
        self.assertEqual(out["model_fits"], 0)

    def test_identity_and_duplicate_fail(self):
        a = self.inputs()
        a[1][0]["entry_id"] = "different"
        with self.assertRaises(ValueError):
            audit_snapshot_views(*a)
        a = self.inputs()
        a[0].append(copy.deepcopy(a[0][0]))
        with self.assertRaises(ValueError):
            audit_snapshot_views(*a)

    def test_no_outcome_field_is_read(self):
        a = self.inputs()
        out = audit_snapshot_views(*a)
        a[0][0]["future_EXIT_profit"] = {"poison": object()}
        self.assertEqual(out, audit_snapshot_views(*a))

    def test_timezone_required_and_offsets_respected(self):
        with self.assertRaises(ValueError):
            timestamp("2025-01-06T10:00:00")
        self.assertEqual(timestamp("2025-01-06T01:00:00Z"), timestamp("2025-01-06T10:00:00+09:00"))

    def test_ineligible_rows_not_in_missingness_denominator(self):
        a = self.inputs()
        a[1][0]["execution_eligible"] = False
        out = audit_snapshot_views(*a)
        self.assertEqual(out["groups"]["G_PRICE"]["cell_denominator"], 0)
        self.assertIsNone(out["groups"]["G_PRICE"]["missing_cell_rate"])

    def test_unknown_eligibility_not_coerced_to_false(self):
        a = self.inputs()
        a[1][0]["execution_eligible"] = None
        with self.assertRaises(ValueError):
            audit_snapshot_views(*a)

    def test_missing_column_null_and_invalid_are_separated(self):
        a = self.inputs()
        del a[0][0]["numeric"]["p0/a"]
        a[0][0]["numeric"]["p0/b"] = float("nan")
        out = audit_snapshot_views(*a)["groups"]["G_PRICE"]
        self.assertEqual((out["absent_numeric_key_cells"], out["explicit_null_cells"], out["invalid_numeric_cells"]), (1, 0, 1))


if __name__ == "__main__":
    unittest.main()
