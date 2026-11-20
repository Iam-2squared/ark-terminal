"""Synthetic safety tests; not market-data validation or Capital replay."""
import unittest
from entry_state_gate import ResearchEntryStateGate, StateAtEntry


class GateTest(unittest.TestCase):
    def row(self, i, t):
        return {"entry_id": i, "entry_minute": t, "ML": 2.1}

    def state(self, i, p, t, usable=True, **kw):
        return StateAtEntry(i, p, usable, t, **kw)

    def test_first_slot_rejects_both(self):
        g = ResearchEntryStateGate()
        rows = [self.row("a", 600), self.row("b", 600), self.row("c", 600)]
        evidence = {"a": self.state("a", "PULLBACK", 599),
                    "b": self.state("b", "SHARP_DROP", 599),
                    "c": self.state("c", "RISE", 599)}
        kept, d = g.filter_batch(rows, evidence)
        self.assertEqual([r["entry_id"] for r in kept], ["c"])
        self.assertEqual([x.action for x in d], ["DROP", "DROP", "KEEP"])

    def test_recycled_slot_same_exclusion(self):
        g = ResearchEntryStateGate()
        # Simulated earlier first-slot entry; SELL fill would release a slot at 700.
        g.filter_batch([self.row("old", 610)], {"old": self.state("old", "RISE", 609)})
        batch = [self.row("pull", 700), self.row("sharp", 700), self.row("drop", 700)]
        e = {"pull": self.state("pull", "PULLBACK", 699),
             "sharp": self.state("sharp", "SHARP_DROP", 699),
             "drop": self.state("drop", "DROP", 699)}
        kept, decisions = g.filter_batch(batch, e)
        self.assertEqual([x["entry_id"] for x in kept], ["drop"])
        self.assertEqual([x.action for x in decisions], ["DROP", "DROP", "KEEP"])

    def test_no_reentry_after_later_recovery(self):
        g = ResearchEntryStateGate()
        g.filter_batch([self.row("x", 600)], {"x": self.state("x", "PULLBACK", 599)})
        rows, decisions = g.filter_batch([self.row("x", 740)], {"x": self.state("x", "RISE", 739)})
        self.assertEqual(rows, [])
        self.assertEqual(decisions[0].action, "SKIP_DUPLICATE")

    def test_unavailable_state_kept_but_not_relabelled(self):
        g = ResearchEntryStateGate()
        rows, d = g.filter_batch([self.row("u", 600)], {"u": self.state("u", "SHARP_DROP", None, False)})
        self.assertEqual(len(rows), 1)
        self.assertEqual(d[0].action, "KEEP_STATE_UNAVAILABLE")

    def test_future_clock_blocks(self):
        g = ResearchEntryStateGate()
        with self.assertRaisesRegex(ValueError, "RESEARCH_GATE_BLOCKED"):
            g.filter_batch([self.row("f", 600)], {"f": self.state("f", "PULLBACK", 601)})

    def test_identity_mismatch_blocks(self):
        g = ResearchEntryStateGate()
        with self.assertRaisesRegex(ValueError, "RESEARCH_GATE_BLOCKED"):
            g.filter_batch([self.row("bad", 600)], {"bad": self.state("other", "PULLBACK", 599)})

    def test_same_timestamp_order_blocks_when_unproven(self):
        g = ResearchEntryStateGate()
        with self.assertRaisesRegex(ValueError, "RESEARCH_GATE_BLOCKED"):
            g.filter_batch([self.row("t", 600)], {"t": self.state("t", "SHARP_DROP", 600, same_minute_phase_order_ok=False)})

    def test_no_forced_backfill_or_v5_policy_change(self):
        g = ResearchEntryStateGate()
        kept, _ = g.filter_batch([self.row("first", 700), self.row("second", 700)],
                                  {"first": self.state("first", "PULLBACK", 699),
                                   "second": self.state("second", "RANGE", 699)})
        self.assertEqual([r["entry_id"] for r in kept], ["second"])
        self.assertEqual(kept[0]["ML"], 2.1)
        # This module must never fund, reserve, resize or retroactively backfill.

if __name__ == "__main__":
    unittest.main()
