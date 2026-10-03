from __future__ import annotations

import gzip
import json
import tempfile
import unittest
from pathlib import Path

from scripts import phase57_nine_state_rebound_review_packet_v1 as mod


def make_row(i, state, prior=-1, recent=1, ratio=0.5, quality="OK", confidence="HIGH"):
    prior_return = -0.01 if prior < 0 else 0.01 if prior > 0 else 0.0
    recent_return = abs(prior_return) * ratio * (1 if recent > 0 else -1 if recent < 0 else 0)
    return {
        "opportunity": f"opp-{i:04d}",
        "session": "2025-01-01",
        "delay": 0,
        "state": state,
        "asOf": 600 + (i % 80),
        "unit": 0.001,
        "priorDir": prior,
        "recentDir": recent,
        "priorReturn": prior_return,
        "recentReturn": recent_return,
        "recentCoverage": 1.0,
        "recentTransitions": 4,
        "earlierTransitions": 6,
        "dataQuality": quality,
        "confidence": confidence,
        "reasonCodes": ["PRIOR_DIRECTION_FROM_PREVIOUS_SESSION", "OPPOSING_DIRECTION_PARTIAL"],
    }


def write_gz(path, value):
    with gzip.open(path, "wt", encoding="utf-8") as fh:
        json.dump(value, fh)


class ReboundPacketTest(unittest.TestCase):
    def test_selection_is_deterministic_and_bounded(self):
        rows = []
        for i in range(192):
            rows.append(make_row(i, "REBOUND", ratio=0.2 + (i % 70) / 100,
                                 quality="DEGRADED" if i % 7 == 0 else "OK",
                                 confidence="LOW" if i % 11 == 0 else "HIGH"))
        for i in range(192, 232):
            rows.append(make_row(i, "RISE", ratio=1.0 + (i % 20) / 100))
        self.assertEqual(
            [r["opportunity"] for r in mod.select_target(rows)],
            [r["opportunity"] for r in mod.select_target(rows)],
        )
        self.assertEqual(len(mod.select_target(rows)), 24)
        comparators, pool_n = mod.select_comparators(rows)
        self.assertEqual(len(comparators), 12)
        self.assertEqual(pool_n, 40)
        self.assertTrue(all(r["state"] == "RISE" for r in comparators))

    def test_prefix_series_never_uses_bar_start_at_or_after_asof(self):
        raw = {
            "previous": [[540, 100, 101, 99, 100], [541, 100, 101, 99, 99]],
            "today": [
                [540, 100, 100, 99, 99],
                [541, 99, 100, 98, 98.5],
                [542, 98.5, 100, 98, 99.5],
                [543, 99.5, 101, 99, 100.5],
            ],
        }
        previous, today = mod.review_series(raw, 543)
        self.assertEqual(len(previous), 2)
        self.assertTrue(today)
        self.assertLessEqual(max(t for t, _ in today), 543)
        # raw 543 bar is future/unclosed at asOf 543 and must not appear.
        self.assertNotIn(100.5, [p for _, p in today])

    def test_full_run_packet_hides_identity_state_and_future_sources(self):
        rows = []
        raw_paths = {}
        for i in range(2155):
            if i < 192:
                row = make_row(i, "REBOUND", ratio=0.3 + (i % 60) / 100)
            elif i < 222:
                row = make_row(i, "RISE", ratio=1.0 + (i % 15) / 100)
            else:
                row = make_row(i, "DROP", prior=-1, recent=-1, ratio=0.5)
            rows.append(row)
            raw_paths[row["opportunity"]] = {
                "previousSession": "2024-12-31",
                "previous": [[540, 100, 101, 99, 100], [541, 100, 101, 98, 99]],
                "today": [[540, 99, 100, 98, 98.5], [541, 98.5, 100, 98, 99]],
            }
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            checkpoints = td / "checkpoints.json.gz"
            raw = td / "raw.json.gz"
            write_gz(checkpoints, rows)
            write_gz(raw, raw_paths)
            args = type("Args", (), {
                "state_checkpoints": str(checkpoints),
                "raw_paths": str(raw),
                "output": str(td / "out"),
            })()
            manifest = mod.run(args)
            self.assertEqual(manifest["futureOrOutcomeSourcesOpened"], 0)
            self.assertEqual(manifest["entryOrFillSourcesOpened"], 0)
            cases = json.loads((td / "out/packet/cases.json").read_text())
            self.assertEqual(len(cases), 36)
            serialized = json.dumps(cases)
            self.assertNotIn("opportunity", serialized)
            self.assertNotIn("baselineState", serialized)
            self.assertNotIn("laterHigh", serialized)
            sealed = json.loads((td / "out/sealed/sealed-map.json").read_text())
            self.assertEqual(len(sealed), 36)
            self.assertIn("opportunity", sealed[0])
            self.assertIn("baselineState", sealed[0])


if __name__ == "__main__":
    unittest.main()
