import unittest

from scripts.phase57_new_long_entry_two_opportunity import (
    Anchor,
    emit_initial_opportunity,
    observe_first_completed_bar,
    state_record,
)


class TwoOpportunityEntryKernelTest(unittest.TestCase):
    def anchor(self):
        return Anchor(
            anchor_id="A1",
            symbol="7203",
            session="2025-01-01",
            decision_timestamp="2025-01-01T09:30:00+09:00",
            decision_price=100.0,
        )

    def test_initial_is_future_independent_and_has_no_quantity(self):
        s1, e1 = emit_initial_opportunity(self.anchor())
        s2, e2 = emit_initial_opportunity(self.anchor())
        self.assertEqual(e1, e2)
        self.assertEqual(e1["eventType"], "INITIAL_ENTRY_OPPORTUNITY")
        self.assertFalse(e1["quantityOwnedByEntry"])
        self.assertNotIn("quantity", e1)
        self.assertNotIn("notional", e1)
        self.assertFalse(s1.secondary_terminal)
        self.assertEqual(s1, s2)

    def test_first_closed_dip_emits_one_reprice_opportunity(self):
        state, _ = emit_initial_opportunity(self.anchor())
        final, event = observe_first_completed_bar(
            state,
            {"missing": False, "open": 101.0, "high": 999.0, "low": 1.0,
             "close": 98.0, "end": "2025-01-01T09:35:00+09:00",
             "futureHigh": 1000000.0, "futureLow": 0.0001},
        )
        self.assertEqual(final.state, "DIP_REPRICE_EMITTED")
        self.assertTrue(final.secondary_terminal)
        self.assertEqual(event["eventType"], "DIP_REPRICE_OPPORTUNITY")
        self.assertEqual(event["sourceState"], "FIRST_CLOSED_DIP")
        self.assertEqual(event["observedFirstClose"], 98.0)
        self.assertFalse(event["quantityOwnedByEntry"])
        self.assertNotIn("futureHigh", event)
        self.assertNotIn("futureLow", event)

    def test_future_fields_cannot_change_dip_decision(self):
        state, _ = emit_initial_opportunity(self.anchor())
        bar1 = {"missing": False, "c": 99.0, "end": "2025-01-01T09:35:00+09:00",
                "h": 100.0, "l": 98.0, "nextClose": 1.0}
        bar2 = {"missing": False, "c": 99.0, "end": "2025-01-01T09:35:00+09:00",
                "h": 99999.0, "l": 0.001, "nextClose": 99999.0}
        f1, e1 = observe_first_completed_bar(state, bar1)
        f2, e2 = observe_first_completed_bar(state, bar2)
        self.assertEqual(f1, f2)
        self.assertEqual(e1, e2)

    def test_continuation_emits_no_secondary(self):
        state, _ = emit_initial_opportunity(self.anchor())
        final, event = observe_first_completed_bar(
            state,
            {"missing": False, "close": 100.0, "end": "2025-01-01T09:35:00+09:00"},
        )
        self.assertEqual(final.state, "FIRST_BAR_CONTINUATION")
        self.assertTrue(final.secondary_terminal)
        self.assertIsNone(event)

    def test_missing_is_unknown_without_imputation(self):
        state, _ = emit_initial_opportunity(self.anchor())
        final, event = observe_first_completed_bar(state, {"missing": True})
        self.assertEqual(final.state, "SECONDARY_UNKNOWN")
        self.assertIsNone(event)

    def test_boundary_expiry(self):
        state, _ = emit_initial_opportunity(self.anchor())
        final, event = observe_first_completed_bar(state, None, boundary_expired=True)
        self.assertEqual(final.state, "SECONDARY_EXPIRED_BOUNDARY")
        self.assertIsNone(event)

    def test_no_recursive_secondary_transition(self):
        state, _ = emit_initial_opportunity(self.anchor())
        final, _ = observe_first_completed_bar(
            state,
            {"missing": False, "close": 99.0, "end": "2025-01-01T09:35:00+09:00"},
        )
        with self.assertRaisesRegex(ValueError, "SECONDARY_STATE_ALREADY_TERMINAL"):
            observe_first_completed_bar(
                final,
                {"missing": False, "close": 98.0, "end": "2025-01-01T09:40:00+09:00"},
            )

    def test_state_record_has_no_outcome_or_sizing_fields(self):
        state, _ = emit_initial_opportunity(self.anchor())
        record = state_record(state)
        raw = repr(record).lower()
        for forbidden in ("futurehigh", "futurelow", "d30", "profit", "quantity", "notional"):
            self.assertNotIn(forbidden, raw)


if __name__ == "__main__":
    unittest.main()
