"""Synthetic boundary and structural-projection tests; no private market data."""
from copy import deepcopy
import unittest

from prebuy_projection import project, NUMERIC, CATEGORICAL, UNKNOWN


def entry(intent=604):
    return {"first_intent": {"intent_minute": intent, "score": .8, "threshold": .7},
            "selector_minute": 600, "selector_to_intent_active_delay": intent - 600,
            "fill_minute": 610, "fill_price": "999.123", "raw_reference": "998.5",
            "intent_to_fill_active_delay": 6, "selector_to_entry_active_delay": 10}


def row(minute, ordinal=None, primary="RISE", segment="S1", source="CONTINUOUS",
        auction="NONE", pivot=None, observed=True, events=None):
    ordinal = minute if ordinal is None else ordinal
    return {"bar_end_minute": minute,
            "state": {"as_of": ordinal, "observed_at": ordinal,
                      "current_semantics_observed": observed, "numeric_status": "ACCEPTED",
                      "primary": primary, "activity": "LIVE", "basis": "OBSERVED_FRESH",
                      "direction_basis": "LOCAL_DC", "context": 1, "leg_direction": 1,
                      "close_u": "3.5", "protected_before": "1",
                      "protected_after_effective_next": "1.5",
                      "protected_updated_at": ordinal - 1, "protected_effective_from": ordinal,
                      "context_established_at": ordinal - 2, "local_pivot_confirmed": pivot,
                      "bar_metadata": {"t": ordinal, "known_at": ordinal,
                                       "source": source, "auction": auction},
                      "events": [], "stop": None},
            "path": {"scheduled_t": ordinal, "causal_segment_id": segment,
                     "Primary_or_null": primary, "context_direction": 1, "local_direction": 1,
                     "fast": False, "fast_applicable_to_primary": True,
                     "dwell_observed_bars": 1, "dwell_scheduled_bars": 1,
                     "quality": {"source": source, "auction": auction}},
            "path_events": events or []}


def pivot(kind, value, at):
    return {"kind": kind, "x": str(value), "extremum_t": at - 1, "confirmed_at": at}


class PrebuyProjectionTests(unittest.TestCase):
    def pattern(self):
        return [row(600), row(601, pivot=pivot("L", 1, 601)),
                row(602, primary="PULLBACK", pivot=pivot("H", 3, 602),
                    events=[{"event_type": "TRANSITION"}]),
                row(603, pivot=pivot("L", 2, 603),
                    events=[{"event_type": "TRANSITION"}]), row(604)]

    def test_fill_and_future_suffix_are_irrelevant_and_inputs_unchanged(self):
        original = self.pattern()
        before = deepcopy(original)
        result = project(entry(), original)
        changed_entry = entry()
        for key in list(changed_entry):
            if key not in ("first_intent", "selector_minute", "selector_to_intent_active_delay"):
                changed_entry[key] = object()
        self.assertEqual(result, project(changed_entry, original + [
            {"bar_end_minute": 605, "state": object(), "path": object(), "path_events": object()},
            {"bar_end_minute": 1000, "state": {"future_return": "POISON"}},
        ]))
        self.assertEqual(before, original)
        self.assertEqual(set(result["numeric"]), set(NUMERIC))
        self.assertEqual(set(result["categorical"]), set(CATEGORICAL))
        self.assertFalse(any("fill" in k or "raw_entry" in k for k in result["numeric"]))

    def test_exact_known_structure_and_prior_lhl(self):
        result = project(entry(), self.pattern())
        n = result["numeric"]
        self.assertEqual(n["structure/close_minus_protected_before_u"], 2.5)
        self.assertEqual(n["structure/close_minus_protected_next_u"], 2)
        self.assertEqual(n["local/prior_lhl_available"], 1)
        self.assertEqual(n["local/prior_lhl_rise_u"], 1)
        self.assertEqual(n["local/close_minus_prior_h_plus_half_u"], 0)
        self.assertEqual(n["local/prior_l1_confirmation_age_bars"], 1)
        self.assertEqual(n["local/prior_lhl_close_confirmed_higher_low"], 1)
        self.assertEqual(result["categorical"]["path/last3_connected_primary"], "RISE>PULLBACK>RISE")

    def test_current_pivot_cannot_complete_prior_lhl(self):
        rows = self.pattern()
        rows[3]["state"]["local_pivot_confirmed"] = None
        rows[4]["state"]["local_pivot_confirmed"] = pivot("L", 2, 604)
        result = project(entry(), rows)
        self.assertEqual(result["numeric"]["local/prior_pivot_count"], 2)
        self.assertEqual(result["numeric"]["local/prior_lhl_available"], 0)
        self.assertIsNone(result["numeric"]["local/prior_lhl_rise_u"])

    def test_future_confirmation_in_prior_row_is_not_used(self):
        rows = self.pattern()
        rows[3]["state"]["local_pivot_confirmed"] = pivot("L", 2, 606)
        result = project(entry(), rows)
        self.assertIsNone(result["numeric"]["local/prior_lhl_available"])
        self.assertIn("INVALID_LOCAL_PIVOT_SCHEMA_OR_TIME", result["quality"]["issues"])

    def test_gap_lunch_source_auction_and_segment_reset_connection(self):
        variants = [row(604, segment="S2"), row(604, source="OTHER"),
                    row(604, auction="MIXED"), row(604, ordinal=700)]
        lunch = row(751, ordinal=604)
        for final in variants + [lunch]:
            with self.subTest(final=final["bar_end_minute"], path=final["path"]):
                result = project(entry(final["bar_end_minute"]), self.pattern()[:-1] + [final])
                self.assertEqual(result["quality"]["connected_prefix_rows"], 1)
                self.assertEqual(result["numeric"]["local/prior_pivot_count"], 0)
                self.assertEqual(result["categorical"]["path/last3_connected_primary"], "RISE")

    def test_invalid_observation_and_stale_prefix_clear_current_features(self):
        rows = self.pattern()
        rows[-1]["state"]["current_semantics_observed"] = False
        for trace in (rows, self.pattern()[:-1], []):
            result = project(entry(), trace)
            self.assertEqual(result["numeric"]["state/observed"], 0)
            self.assertEqual(result["categorical"]["state/current_primary"], UNKNOWN)
            self.assertIsNone(result["numeric"]["structure/close_minus_protected_before_u"])
            self.assertIsNone(result["numeric"]["local/prior_lhl_available"])
            self.assertIn("local/prior_lhl_available", result["quality"]["feature_reasons"])

    def test_invalid_then_resume_does_not_compress_a_null_b(self):
        rows = self.pattern()
        rows[3]["state"]["current_semantics_observed"] = False
        rows[-1]["path"]["Primary_or_null"] = "DROP"
        rows[-1]["state"]["primary"] = "DROP"
        rows[-1]["path_events"] = [{"event_type": "TRANSITION"}]
        result = project(entry(), rows)
        self.assertEqual(result["categorical"]["path/last3_connected_primary"], "DROP")
        self.assertEqual(result["numeric"]["path/transitions_total"], 1)
        self.assertIn("UNCONNECTED_TRANSITION_IGNORED", result["quality"]["issues"])

    def test_unknown_fields_and_source_do_not_create_information(self):
        rows = self.pattern()
        del rows[-1]["state"]["protected_after_effective_next"]
        del rows[2]["state"]["local_pivot_confirmed"]
        result = project(entry(), rows)
        self.assertIsNone(result["numeric"]["structure/close_minus_protected_next_u"])
        self.assertIsNone(result["numeric"]["local/prior_lhl_available"])
        rows = self.pattern()
        rows[-1]["state"]["bar_metadata"] = {}
        rows[-1]["path"]["quality"] = {}
        result = project(entry(), rows)
        self.assertEqual(result["quality"]["connected_prefix_rows"], 0)
        self.assertIsNone(result["numeric"]["local/prior_lhl_available"])
        self.assertIn("STATE_BAR_METADATA_UNAVAILABLE", result["quality"]["issues"])

    def test_cached_pivot_cannot_bridge_reset(self):
        rows = self.pattern()
        rows[-1]["path"]["causal_segment_id"] = "S2"
        rows[-1]["state"]["local_pivot_confirmed"] = pivot("L", 2, 603)
        result = project(entry(), rows)
        self.assertIsNone(result["numeric"]["local/prior_lhl_available"])
        self.assertIn("LOCAL_PIVOT_CONFIRMATION_BEFORE_CONNECTED_EPISODE", result["quality"]["issues"])

    def test_unavailable_event_schema_is_not_zero_history(self):
        rows = self.pattern()
        del rows[-1]["path_events"]
        result = project(entry(), rows)
        self.assertIsNone(result["numeric"]["path/transitions_total"])
        self.assertIsNone(result["numeric"]["path/transitions_15m"])
        self.assertEqual(result["quality"]["feature_reasons"]["path/transitions_total"],
                         "PATH_EVENT_SCHEMA_UNAVAILABLE")

    def test_future_selector_timestamp_and_negative_delay_are_null(self):
        e = entry()
        e["selector_minute"] = 605
        e["selector_to_intent_active_delay"] = -1
        result = project(e, self.pattern())
        self.assertIsNone(result["numeric"]["selector/first_clock"])
        self.assertIsNone(result["numeric"]["selector/to_intent_active_delay"])

    def test_future_metadata_or_effect_time_is_not_accepted(self):
        rows = self.pattern()
        rows[-1]["state"]["bar_metadata"]["known_at"] = 605
        self.assertEqual(project(entry(), rows)["numeric"]["state/observed"], 0)
        rows = self.pattern()
        rows[-1]["state"]["protected_effective_from"] = 608
        self.assertIsNone(project(entry(), rows)["numeric"]["structure/close_minus_protected_next_u"])

    def test_duplicate_or_reversed_prefix_and_invalid_cutoff_fail(self):
        with self.assertRaisesRegex(ValueError, "PREFIX_ORDER_NOT_STRICT"):
            project(entry(), [row(604), row(603)])
        with self.assertRaisesRegex(ValueError, "PREFIX_ORDER_NOT_STRICT"):
            project(entry(), [row(604), row(604)])
        with self.assertRaisesRegex(ValueError, "FIRST_INTENT_MINUTE_REQUIRED"):
            project({"first_intent": {}}, [])

    def test_nan_bool_and_nonfinite_features_remain_null(self):
        e = entry()
        e["first_intent"]["score"] = float("nan")
        e["first_intent"]["threshold"] = True
        rows = self.pattern()
        rows[-1]["state"]["close_u"] = "1e9999"
        result = project(e, rows)
        self.assertIsNone(result["numeric"]["entry/p1_score"])
        self.assertIsNone(result["numeric"]["entry/p1_threshold"])
        self.assertIsNone(result["numeric"]["entry/p1_margin"])
        self.assertIsNone(result["numeric"]["structure/close_minus_protected_before_u"])


if __name__ == "__main__":
    unittest.main()
