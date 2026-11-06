"""Synthetic/contract tests only; never run the 2,155 Development fit."""
from __future__ import annotations

import unittest
import numpy as np

from scripts import phase57_exit_research_protocol_v1 as r25
from scripts.phase57_exit_finite_r36 import (
    ARMS, Data, _post_entry_high, candidate_spec, prediction_specs,
    rank_selection, replay_candidate, spec_id, weights_for,
)


class FiniteR36Tests(unittest.TestCase):
    def test_exact_grid_maps_to_six_shared_prediction_specs(self):
        specs = prediction_specs()
        self.assertEqual(len(specs), 6)
        counts = {}
        for candidate in r25.candidate_grid():
            sid = candidate_spec(candidate)
            counts[sid] = counts.get(sid, 0) + 1
        self.assertEqual(set(counts), {spec_id(x) for x in specs})
        self.assertEqual(set(counts.values()), {4})
        self.assertEqual(sum(counts.values()), 24)

    def test_hierarchical_weights_equalize_entries_and_sessions(self):
        data = Data(
            ["s1", "s2"], [], [], [],
            sessions=np.array([0, 0, 0, 1, 1], dtype=np.int16),
            arms=np.zeros(5, dtype=np.int8),
            entries=np.array([0, 0, 1, 2, 2], dtype=np.int32),
            now=np.arange(5), fresh=np.ones(5, dtype=bool),
            categorical=np.empty((5, 0)), numeric=np.empty((5, 0)),
            pattern=np.empty((5, 0)), targets=np.empty((5, 3)),
            entry_ids=["a", "b", "c"], entry_rows={}, raw={}, opportunity_records={})
        w = weights_for(data, np.arange(5))
        # Within each session the total is equal; within s1 both entries are equal.
        self.assertAlmostEqual(w[:3].sum(), w[3:].sum())
        self.assertAlmostEqual(w[:2].sum(), w[2])
        self.assertAlmostEqual(w.mean(), 1.0)

    def test_post_entry_high_excludes_entry_candle_and_knows_auction_at_930(self):
        entry = {"entryMinute": 540}
        rows = [[540, 100, 999, 99, 100, 1, 1],
                [541, 100, 105, 98, 104, 1, 1],
                [930, 110, 110, 110, 110, 1, 1]]
        high = _post_entry_high(entry, rows)
        self.assertEqual(high.high, 110)
        self.assertEqual(high.high_available_at(), 930)

    def test_missing_exact_open_is_not_queued_and_later_fresh_checkpoint_retries(self):
        session = "2025-07-03"
        eid = f"{session}|11110|540"
        key = f"{ARMS[0]}::{eid}"
        names = ["position.fullOwnedPrefix", "position.observedRunningHigh",
                 "position.peakConfirmedAt"]
        data = Data(
            [session], [], names, [],
            sessions=np.zeros(3, dtype=np.int16), arms=np.zeros(3, dtype=np.int8),
            entries=np.zeros(3, dtype=np.int32), now=np.array([541, 542, 543], dtype=np.int16),
            fresh=np.array([True, False, True]), categorical=np.empty((3, 0)),
            numeric=np.array([[1, 101, 541], [0, 101, 541], [1, 103, 543]], dtype=np.float32),
            pattern=np.empty((3, 0)), targets=np.empty((3, 3)), entry_ids=[key],
            entry_rows={key: {"entryId": eid, "entryArm": ARMS[0], "entryMinute": 540,
                "opportunity": f"{session}|11110", "price": 100.0,
                "session": session, "symbol": "11110"}},
            raw={f"{session}|11110": {"today": [
                [540, 100, 101, 99, 100, 1, 1],
                # exact start 541 deliberately absent
                [542, 101, 103, 100, 102, 1, 1],
                [543, 102, 104, 101, 103, 1, 1],
                [930, 103, 103, 103, 103, 1, 1],
            ]}},
            opportunity_records={f"{session}|11110": {
                "session": session, "opportunity": f"{session}|11110",
                "orderedOracle": {"fullSessionEvaluable": True,
                    "status": "OBSERVED_ORDERED_ORACLE", "low": 99.0,
                    "high": 104.0, "lowMinute": 540, "highMinute": 543,
                    "rangePct": 100 * (104 / 99 - 1)}}})
        prediction = np.full((3, 3), -1.0, dtype=np.float32)
        candidate = {"candidateId": "SYNTH", "exitThresholdPp": 0.0,
                     "persistenceFreshCheckpoints": 1}
        row = replay_candidate(data, prediction, candidate)[0]
        self.assertEqual(row["missingOrdinaryReferences"], 1)
        self.assertEqual(row["exitKind"], "MODEL_EXIT")
        self.assertEqual(row["exitMinute"], 543)
        self.assertEqual(row["exitPrice"], 102.0)

    def test_no_pass_and_exact_tie_both_stop(self):
        self.assertEqual(rank_selection([])["outcome"], "NO_SELECTION_STOP")
        base = {"gate": {"pass": True, "capabilityMargins": {
            "winner": 1.0, "retention": 1.0, "loss": 1.0}}}
        tied = [dict(base, candidateId="A"), dict(base, candidateId="B")]
        result = rank_selection(tied)
        self.assertEqual(result["outcome"], "NO_SELECTION_STOP")
        self.assertEqual(result["reason"], "EXACT_SUBSTANTIVE_CAPABILITY_TIE")


if __name__ == "__main__":
    unittest.main()
