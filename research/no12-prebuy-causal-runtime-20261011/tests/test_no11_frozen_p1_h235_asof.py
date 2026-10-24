"""Frozen H235 as-of project/rank on SYNTHETIC inputs; no private model data.

Exercises the genuine byte-pinned native project / sklearn-like logistic
preprocessing / PAVA / ML R0 and all 24-member integrity gates. No broker.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))
import no11_h235_asof_forward_shadow as h

SESSION = "2026-10-26"


def stamp(m, sec=0):
    return SESSION + f"T{m // 60:02d}:{m % 60:02d}:{sec:02d}+09:00"


def fake_trace():
    rows = []
    for m in (569, 570, 571):
        t = m - 540
        state = {
            "as_of": t, "numeric_status": "ACCEPTED",
            "current_semantics_observed": True, "observed_at": t,
            "activity": "LIVE", "basis": "OBSERVED_FRESH",
            "direction_basis": "PRICE", "stop": {"count": 2},
        }
        path = {
            "bar_end": stamp(m), "scheduled_t": t,
            "Primary_or_null": "RISE",
            "context_direction": 1, "local_direction": 1,
            "fast_applicable_to_primary": True, "fast": False,
            "dwell_observed_bars": m - 568,
            "dwell_scheduled_bars": m - 568,
            "causal_segment_id": "S1",
        }
        rows.append({
            "bar_end_minute": m, "knownAtJst": stamp(m, 8),
            "state": state, "path": path, "path_events": [],
        })
    return rows


def valid_input():
    return {
        "schemaId": h.INPUT_SCHEMA, "sessionDate": SESSION,
        "symbol": "7203.T", "candidateId": "a" * 64,
        "selectorFirstAtJst": stamp(570),
        "firstIntentAtJst": stamp(571),
        "decisionAtJst": stamp(571, 12),
        "p1Score": .75, "p1Threshold": .583,
        "selectorFirstPrice": 99.0,
        "referencePrice": 101.25,
        "referenceBarEndJst": stamp(571),
        "referenceKnownAtJst": stamp(571, 8),
        "stateTrace": fake_trace(), "sourceKind": "RSS_CUMULATIVE_PROXY",
        "shadowOnly": True, "productionReady": False,
        "orderTransmission": False,
    }


def synthetic_models(root, original):
    models = []
    for horizon in h.HEADS:
        for block in range(1, 9):
            nn = ["entry/p1_score", "selector/raw_entry_vs_first_price_pct"]
            cc = ["state/current_primary"]
            model = {
                "base_rate": {2: .6, 3: .5, 5: .4}[horizon],
                "preprocessing": {
                    "numeric_fields": nn,
                    "categorical_fields": cc,
                    "numeric_mean": [0.0] * (2 * len(nn)),
                    "numeric_scale": [1.0] * (2 * len(nn)),
                    "categorical_train_vocab": {"state/current_primary": ["RISE", "__UNKNOWN__"]},
                },
                "coef": [0.0] * (2 * len(nn) + 2),
                "intercept": 0.0,
                "testSyntheticNotOriginal": True,
            }
            b = h.stable_bytes(model)
            filename = f"H{horizon}_BLOCK_{block:02d}.json"
            path = root / "inputs" / "frozen_models" / filename
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b)
            models.append({
                "local_member": "inputs/frozen_models/" + filename,
                "bytes": len(b),
                "sha256": hashlib.sha256(b).hexdigest(),
                "git_blob": h.git_blob(b),
            })
    manifest = {
        "status": "EXACT_MEMBER_HASH_PASS", "original_model_member_N": 24,
        "new_fit": 0, "models": models,
    }
    return manifest


class PolicyAndFeatureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.core, cls.prep, cls.stair, cls.source = h.original_dependencies()
        cls.project = h.asof_projector(cls.core, cls.source)

    def test_shadow_policy_explicit_future_block_without_original_oof_claim(self):
        p = h.policy(SESSION)
        self.assertEqual(p["selectedBlock"], 8)
        self.assertEqual(p["originalLatestSavedTrainThrough"], "2025-08-20")
        self.assertTrue(p["originalOofDateDispatchUnchanged"])
        self.assertFalse(p["originalHistoricalRankParityClaim"])
        self.assertFalse(p["productionReady"])
        self.assertFalse(p["orderTransmission"])

    def test_dates_outside_2026_forward_shadow_rejected(self):
        for day in ("2025-08-25", "2026-10-25", "2027-01-04"):
            with self.assertRaisesRegex(ValueError, "SHADOW_SESSION_OUTSIDE_SCOPE"):
                h.policy(day)

    def test_original_project_ast_is_unchanged_except_two_asof_assignments(self):
        r = valid_input()
        _, trace, *_ = h.validate_input(r)
        reference = self.core.project({
            "fill_minute": 571, "fill_price": r["referencePrice"] * 1.0005,
            "first_intent": {"score": .75, "threshold": .583, "intent_minute": 571},
            "selector_price": 99.0, "selector_minute": 570,
            "intent_to_fill_active_delay": 0,
            "selector_to_intent_active_delay": 1,
            "selector_to_entry_active_delay": 1,
        }, trace)
        asof = self.project({
            "asof_minute": 571, "asof_reference_price": 101.25,
            "first_intent": {"score": .75, "threshold": .583, "intent_minute": 571},
            "selector_price": 99.0, "selector_minute": 570,
            "intent_to_fill_active_delay": 0,
            "selector_to_intent_active_delay": 1,
            "selector_to_entry_active_delay": 1,
        }, trace)
        for key in self.core.NUMERIC:
            if key == "selector/raw_entry_vs_first_price_pct":
                self.assertAlmostEqual(reference["numeric"][key],
                                       asof["numeric"][key], places=10)
            else:
                self.assertEqual(reference["numeric"][key], asof["numeric"][key])
        self.assertEqual(reference["categorical"], asof["categorical"])
        self.assertEqual(reference["provenance"], asof["provenance"])

    def test_changed_native_project_structure_fails_closed(self):
        source = self.source.replace(b"t=entry['fill_minute']", b"t=entry['asof_minute']")
        with self.assertRaisesRegex(ValueError, "FILL_ACCESS_CHANGED"):
            h.asof_projector(self.core, source)

    def test_future_price_and_future_state_cannot_enter_r0(self):
        r = valid_input()
        r["referenceKnownAtJst"] = stamp(572, 1)
        with self.assertRaisesRegex(ValueError, "INPUT_CLOCK_ORDER"):
            h.validate_input(r)
        r = valid_input()
        r["stateTrace"][0]["knownAtJst"] = stamp(575, 1)
        with self.assertRaisesRegex(ValueError, "STATE_TRACE_CAUSAL_CLOCK"):
            h.validate_input(r)

    def test_excluded_state_and_missing_observation_block(self):
        for primary, observed in (("PULLBACK", True), ("SHARP_DROP", True),
                                  (None, True), ("RISE", False)):
            r = valid_input()
            r["stateTrace"][-1]["path"]["Primary_or_null"] = primary
            r["stateTrace"][-1]["state"]["current_semantics_observed"] = observed
            with self.assertRaisesRegex(ValueError, "FROZEN_ENTRY_STATE_EXCLUDED"):
                h.validate_input(r)

    def test_reference_cannot_be_futuristic_or_stale(self):
        r = valid_input()
        r["decisionAtJst"] = stamp(574)
        with self.assertRaisesRegex(ValueError, "REFERENCE_BAR_STALE"):
            h.validate_input(r)
        r = valid_input()
        r["referenceBarEndJst"] = stamp(572)
        with self.assertRaisesRegex(ValueError, "INPUT_CLOCK_ORDER"):
            h.validate_input(r)

    def test_wrong_p1_threshold_and_fabricated_fill_key_refused(self):
        r = valid_input()
        r["p1Score"] = .2
        with self.assertRaisesRegex(ValueError, "P1_FIRST_CROSS_NOT_CONFIRMED"):
            h.validate_input(r)
        r = valid_input()
        r["fill_price"] = 102.0
        with self.assertRaisesRegex(ValueError, "INPUT_FIELDS_INVALID"):
            h.validate_input(r)

    def test_active_minutes_do_not_count_lunch_break(self):
        self.assertEqual(h.active_elapsed(690, 751), 0)
        self.assertEqual(h.active_elapsed(570, 571), 1)

    def test_receipt_clock_gates_actual_local_observation(self):
        r = valid_input()
        r["stateTrace"][1]["knownAtJst"] = stamp(570, 15)
        r["stateTrace"][2]["knownAtJst"] = stamp(571, 8)
        h.validate_input(r)  # nondecreasing first-seen still okay
        r["stateTrace"][2]["knownAtJst"] = stamp(570, 59)
        with self.assertRaisesRegex(ValueError, "STATE_TRACE_CAUSAL_CLOCK"):
            h.validate_input(r)

    def test_first_entry_candidate_must_be_genuine_shadow_p1_event(self):
        p1 = {
            "status": "FIRST_ENTRY_CANDIDATE",
            "candidateId": "a" * 64, "barEndJst": stamp(571),
            "evaluatedAtJst": stamp(571, 12),
            "score": {"score": .75}, "threshold": .583,
            "orderTransmission": False, "orderAuthorized": False, "shadowOnly": True,
        }
        watch = {"selector_minute": 570, "selector_price": 99.0}
        source = {"Code": "7203.T", "C": 101.25,
                  "knownAtJst": stamp(571, 8)}
        r = h.make_received_candidate(p1_decision=p1, watch=watch,
                                      reference_row=source, trace=fake_trace(),
                                      session=SESSION)
        h.validate_input(r)
        p1["status"] = "WAIT"
        with self.assertRaisesRegex(ValueError, "P1_FIRST_INTENT_REQUIRED"):
            h.make_received_candidate(p1_decision=p1, watch=watch,
                                      reference_row=source, trace=fake_trace(),
                                      session=SESSION)

    def test_staircase_origin_is_used_not_p1_score_as_rank(self):
        self.assertEqual(self.stair.materialize({
            "p2": .5, "p3": .5, "p5": .5,
            "base2": .6, "base3": .5, "base5": .4,
        })["ML"], 1.0)


class ModelTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.manifest = synthetic_models(self.root, None)

    def tearDown(self):
        self.temp.cleanup()

    def test_24_synthetic_bytes_verify_before_original_inference(self):
        self.assertEqual(len(h.verify_models(self.root, self.manifest)), 24)
        scorer = h.FrozenH235AsOf(self.root, SESSION, manifest=self.manifest)
        output = scorer.score(valid_input())
        self.assertEqual(output["originalFrozenModelFilesVerified"], 24)
        self.assertEqual(output["originalModelsExecuted"], 3)
        self.assertEqual(output["ML"], 1.0)
        self.assertEqual(output["rank"], "B")
        self.assertTrue(output["admission"])
        self.assertEqual(output["selectedBlock"], 8)
        self.assertFalse(output["orderAuthorized"])
        self.assertFalse(output["capitalExecutionAuthorized"])
        self.assertTrue(output["changedFeatureSemantics"])

    def test_model_replaced_after_manifest_is_blocked(self):
        target = self.root / self.manifest["models"][0]["local_member"]
        target.write_text('{"modified":true}')
        with self.assertRaisesRegex(ValueError, "MODEL_BYTE_HASH_MISMATCH"):
            h.verify_models(self.root, self.manifest)

    def test_missing_model_is_blocked(self):
        target = self.root / self.manifest["models"][-1]["local_member"]
        target.unlink()
        with self.assertRaisesRegex(ValueError, "MODEL_MEMBER_UNSAFE"):
            h.verify_models(self.root, self.manifest)

    def test_manifest_duplicate_or_wrong_count_is_blocked(self):
        m = deepcopy(self.manifest)
        m["models"][-1] = m["models"][0]
        with self.assertRaisesRegex(ValueError, "MODEL_MEMBER_DUPLICATE"):
            h.verify_models(self.root, m)
        m = deepcopy(self.manifest)
        m["models"].pop()
        with self.assertRaisesRegex(ValueError, "ORIGINAL_MANIFEST_INVALID"):
            h.verify_models(self.root, m)

    def test_no_original_model_features_from_future(self):
        scorer = h.FrozenH235AsOf(self.root, SESSION, manifest=self.manifest)
        val = valid_input()
        val["stateTrace"].append({
            **deepcopy(val["stateTrace"][-1]),
            "bar_end_minute": 572,
            "knownAtJst": stamp(572, 8),
        })
        with self.assertRaisesRegex(ValueError, "STATE_TRACE_CAUSAL_CLOCK"):
            scorer.score(val)

    def test_missing_private_root_does_not_fallback_to_synthetic_model(self):
        with self.assertRaisesRegex(ValueError, "PRIVATE_ROOT_INVALID"):
            h.verify_models(self.root / "missing", self.manifest)


if __name__ == "__main__":
    unittest.main()
