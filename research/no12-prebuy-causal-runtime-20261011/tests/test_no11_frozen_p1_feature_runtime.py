"""Causal boundary and original streaming feature-history regression tests."""
from copy import deepcopy
import hashlib
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))
SPEC = importlib.util.spec_from_file_location(
    "no11_frozen_p1_feature_runtime", TOOLS / "no11_frozen_p1_feature_runtime.py")
FEATURE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(FEATURE)


def fixture():
    """Synthetic market numbers, used only to exercise calculation invariants."""
    day, previous_day = "2025-06-02", "2025-05-30"
    watch = {"watch_key": "synthetic-watch", "session": day,
             "selector_minute": 550, "selector_price": 100.0,
             "refresh_minutes": [550, 560, 580]}
    def bar(minute, i):
        close = round(100 + ((i % 18) if (i // 18) % 2 == 0 else 18 - i % 18) * .2, 3)
        return [minute, close, close + .1, close - .1, close, 10, close * 10]
    previous = [bar(t, i) for i, t in enumerate(range(540, 585))]
    today = [bar(t, i + 2) for i, t in enumerate(range(540, 600)) if t not in (567, 568)]
    def token(row, session):
        result = dict(zip(("O", "H", "L", "C", "Vo", "Va"), map(str, row[1:])))
        result.update(Date=session, Time="%02d:%02d" % divmod(row[0], 60),
                      Code="SYNTHETIC", _source={"fixture": True})
        return result
    raw = {"today": today, "previous": previous}
    source = {"previous": [token(r, previous_day) for r in previous],
              "previous_daily": {"AdjFactor": "1", "ExRT": None},
              "previous_session": previous_day,
              "current_prefix": [token(r, day) for r in today[:10]]}
    return watch, raw, source


class FeatureRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime = FEATURE.load_feature_runtime()
        cls.np = cls.runtime.np

    def setUp(self):
        self.watch, self.raw, self.source = fixture()

    def compute(self, **kwargs):
        return FEATURE.compute_watch_features(self.runtime, self.watch, self.raw, self.source, **kwargs)

    def test_only_original_calculation_nodes_are_loaded(self):
        ns = self.runtime.namespace
        self.assertFalse(set(("run", "fit", "teacher", "write", "write_lines")) & set(ns))
        self.assertEqual(len(self.runtime.numeric_names), 148)
        self.assertEqual(len(self.runtime.categorical_names), 15)
        self.assertEqual(self.runtime.numeric_names[110], "state/observed")

    def test_changed_public_body_is_rejected_before_execution(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "source.py"
            original = b"raise AssertionError('must not execute')\n"
            path.write_bytes(original + b"# changed\n")
            with self.assertRaisesRegex(ValueError, "P1_FEATURE_PUBLIC_SOURCE_PIN_MISMATCH"):
                FEATURE._public_bytes(path, hashlib.sha256(original).hexdigest())

    def test_future_append_and_future_daily_fields_do_not_affect_prefix(self):
        before = self.compute(as_of_minute=565)
        self.raw["today"] = [r for r in self.raw["today"] if r[0] < 565]
        # Future invalid/missing Va, extreme prices and a later afternoon opening
        # never reach the original state_task or its auction minima.
        self.raw["today"] += [[570], [750, 90000, 99999, 1, 90000, 1, None]]
        self.source["current_daily"] = {"C": "999999999"}
        self.source["max_candidate_intent"] = "DO_NOT_CONSUME"
        after = self.compute(as_of_minute=565)
        self.np.testing.assert_array_equal(before[1], after[1])
        self.assertEqual(before[2:4], after[2:4])
        self.assertTrue(all(m["intent_minute"] <= 565 for m in after[3]))

    def test_real_va_is_required_at_the_decision_boundary(self):
        self.raw["today"][0][-1] = None
        with self.assertRaisesRegex(ValueError, "P1_FEATURE_REAL_VA_REQUIRED"):
            self.compute(as_of_minute=565)

    def test_missing_watch_is_never_manufactured(self):
        del self.watch["selector_price"]
        with self.assertRaisesRegex(ValueError, "P1_FEATURE_CANONICAL_WATCH_REQUIRED"):
            self.compute()

    def test_rss_source_cannot_be_relabelled_by_the_batch_api(self):
        with self.assertRaisesRegex(ValueError, "P1_FEATURE_PROVIDER_SUBSTITUTION_NOT_ALLOWED"):
            self.compute(source_kind="RSS_CHART_VALUE2_RESEARCH_ONLY_NOT_JQUANTS_V2")

    def test_previous_source_must_be_past_and_date_consistent(self):
        self.source["previous_session"] = self.watch["session"]
        with self.assertRaisesRegex(ValueError, "P1_FEATURE_PREVIOUS_SOURCE_NOT_PAST"):
            self.compute()
        self.source["previous_session"] = "2025-05-29"
        with self.assertRaisesRegex(ValueError, "P1_FEATURE_PREVIOUS_LEXEME_DATE_MISMATCH"):
            self.compute()

    def test_previous_adjustment_or_missing_exrt_stays_source_unavailable(self):
        for daily in ({"AdjFactor": "2", "ExRT": None}, {"AdjFactor": "1"}):
            with self.subTest(daily=daily):
                self.source["previous_daily"] = daily
                result = self.compute(as_of_minute=565)
                self.assertTrue(self.np.isnan(result[1][:, 110:]).all())
                self.assertTrue(all(c[-1] == "SOURCE_UNAVAILABLE" for c in result[2]))
                self.assertEqual(result[4]["source_reason"], "PREVIOUS_PRICE_BASIS_NOT_CONTINUOUS")

    def test_compact_original_lexeme_mismatch_is_rejected(self):
        checked = FEATURE.verify_saved_compact_overlap(self.raw, self.source)
        self.assertGreater(checked["previousDecimalChecks"], 0)
        self.source["previous"][3]["C"] = "1"
        with self.assertRaisesRegex(ValueError, "P1_FEATURE_SAVED_LEXEME_VALUE_MISMATCH"):
            FEATURE.verify_saved_compact_overlap(self.raw, self.source)

    def test_incremental_state_path_history_matches_original_batch_after_gap(self):
        ns = self.runtime.namespace
        original_engine = ns["Engine"]
        states = []
        class CapturingEngine(original_engine):
            def step(self, *args, **kwargs):
                state = super().step(*args, **kwargs)
                states.append(deepcopy(state))
                return state
        with mock.patch.dict(ns, Engine=CapturingEngine):
            batch = self.compute()
        stream = FEATURE.StateFeatureStream(self.runtime, self.watch["session"], self.watch["watch_key"])
        snapshots = {}
        for state in states:
            end = state["as_of"] + 540
            snapshots[end] = stream.push(state, {
                "scheduled_t": state["as_of"], "bar_end": ns["stamp"](self.watch["session"], end),
                "row_status": "RAW_CLOSED_AT_ASSUMED_BAR_END" if state["numeric_status"] == "ACCEPTED" else "MISSING_RAW_SOURCE",
            })
        for i, meta in enumerate(batch[3]):
            snap = snapshots[meta["intent_minute"]]
            self.np.testing.assert_array_equal(batch[1][i, 110:], snap["numeric"])
            self.assertEqual(batch[2][i][:-1], snap["categorical"])
            self.assertFalse(snap["source_status_assigned"])
        self.assertTrue(any(s["numeric_status"] == "NOT_AVAILABLE" for s in states))
        self.assertGreater(len({s["endpoint"]["causal_segment_id"] for s in snapshots.values()}), 1)

    def test_history_uses_active_minutes_distinct_states_and_resets_on_loss(self):
        update = self.runtime.namespace["update_history"]
        endpoint = {"Primary_or_null": "RISE", "causal_segment_id": "s1", "entered_at": 145}
        state = ([], [], None, None, None)
        result = update("2025-06-02", endpoint, [], 685, *state)
        result = update("2025-06-02", endpoint, [], 756, *result[:5])
        self.assertEqual(result[5]["current_state_active_dwell"], 11)
        self.assertEqual(result[5]["transition_count_last10active"], 0)
        endpoint = dict(endpoint, Primary_or_null="DROP", entered_at=217)
        result = update("2025-06-02", endpoint, [{"event_type": "TRANSITION"}], 757, *result[:5])
        self.assertEqual(result[5]["previous_to_current_pair"], "RISE>DROP")
        self.assertEqual(result[5]["transition_count_last5active"], 1)
        endpoint = dict(endpoint, Primary_or_null=None)
        result = update("2025-06-02", endpoint, [{"event_type": "OBSERVATION_LOST"}], 758, *result[:5])
        self.assertEqual(result[5]["previous_to_current_pair"], "__UNKNOWN_HISTORY__")
        self.assertIsNone(result[5]["transition_count_last5active"])

    def test_category_encoding_is_lossless_and_does_not_expand_vocabulary(self):
        vocabulary = [["a", "b"] for _ in range(15)]
        coded = FEATURE.encode_categories(self.runtime, [["b"] * 15], vocabulary)
        self.assertEqual(coded.tolist(), [[1] * 15])
        with self.assertRaisesRegex(ValueError, "CATEGORY_OUTSIDE_ORIGINAL_GLOBAL_VOCABULARY"):
            FEATURE.encode_categories(self.runtime, [["rss-provider"] * 15], vocabulary)
        self.assertTrue(all(v == ["a", "b"] for v in vocabulary))

    def test_batch_receipt_does_not_claim_live_knownat_or_oof_dispatch(self):
        receipt = self.compute(as_of_minute=565)[4]
        self.assertEqual(receipt["actualKnownAt"], "UNKNOWN")
        self.assertEqual(receipt["assumedAvailableAt"], "bar_end")
        self.assertFalse(receipt["fullOofReplay"])
        self.assertFalse(receipt["orderTransmission"])
        self.assertEqual(receipt["modelFits"], 0)
        self.assertEqual(receipt["modelDispatch2026"], "UNDEFINED_IN_ORIGINAL_FROZEN_SPLIT")


if __name__ == "__main__":
    unittest.main()
