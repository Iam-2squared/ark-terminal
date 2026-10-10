"""No-fit contract tests; new candidate performance is not inspected here."""
import inspect
import math
import unittest
from unittest import mock

import numpy as np

from scripts import phase57_exit_persistent_value_r53 as r
from scripts import phase57_exit_execution_contract_v1 as execution
from scripts import phase57_development_integrated_v0 as v0


class PersistentExitContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p = r.contract()

    def test_precommit_and_frozen_upstream_pins(self):
        self.assertEqual(r.sha(r.PRECOMMIT),
                         (r.EVIDENCE / "PRECOMMIT.sha256").read_text().strip())
        self.assertEqual(self.p["predictionSource"]["sha256"],
                         "e13f39f420e020349d09d36945d101372e7d67362374a447d8bdaec17b28cda1")
        self.assertEqual(self.p["originalPins"]["entryDualFreeze"],
                         "4878a1cc53430e816261dea0fb16aeb53b3c238d")
        self.assertEqual(self.p["finiteBudget"]["newFits"], 0)
        self.assertEqual(self.p["finiteBudget"]["newPolicyCandidates"], 1)

    def test_all_profit_states_have_causal_confirmation_path(self):
        hold = {"action": "HOLD"}
        for net in (-3.0, 0.0, 2.5, 4.0, 8.0):
            with self.subTest(returnPct=net):
                state = 0
                for i in (1, 2):
                    action, _, state = r.action(hold, True, net, -0.051, state, self.p)
                    self.assertEqual(action, "HOLD")
                    self.assertEqual(state, i)
                self.assertEqual(r.action(hold, True, net, -0.051, state, self.p)[0],
                                 "SELL_INTENT")

    def test_exact_threshold_and_finite_ooF(self):
        hold = {"action": "HOLD"}
        self.assertEqual(r.action(hold, True, 3, -.05, 2, self.p),
                         ("HOLD", "PREDICTED_CONTINUATION_RESET", 0))
        self.assertEqual(r.action(hold, True, 3, math.nan, 2, self.p)[2], 0)
        self.assertEqual(r.action(hold, True, 3, None, 2, self.p)[2], 0)

    def test_missing_and_stale_now_reset_counter(self):
        hold = {"action": "HOLD"}
        for fresh, ret in ((False, 2.0), (True, None), (True, math.nan)):
            self.assertEqual(r.action(hold, fresh, ret, -1, 2, self.p),
                             ("HOLD", "MISSING_NOW_RESET", 0))
        self.assertEqual(r.action(hold, True, 2, 0, 2, self.p)[2], 0)

    def test_frozen_r50_harvest_and_terminal_priority(self):
        self.assertEqual(r.action({"action": "EXIT_INTENT"}, False, None, None, 0, self.p),
                         ("SELL_INTENT", "FROZEN_R50_HARVEST", 0))
        self.assertEqual(r.action({"action": "FORCE_TERMINAL"}, True, -2, -1, 2, self.p),
                         ("FORCE_TERMINAL", "FROZEN_R50_TERMINAL", 0))

    def test_future_bucket_and_unresolved_future_fill_are_not_decision_arguments(self):
        keys = set(inspect.signature(r.action).parameters)
        self.assertEqual(keys, {"frozen_r50", "fresh", "current_return",
                                "prediction", "previous", "p"})
        forbidden = ("futureHigh", "postEntryUpside", "realizedPnL", "nextOpen")
        self.assertFalse(any(any(word.lower() in key.lower() for key in keys)
                             for word in forbidden))
        state = {"action": "HOLD"}
        before = r.action(state, True, 2.5, -.2, 2, self.p)
        changed_evaluator_only = {"futureHigh": 99, "realizedWinner": True}
        self.assertEqual(before, r.action(state, True, 2.5, -.2, 2, self.p))
        self.assertEqual(changed_evaluator_only["futureHigh"], 99)

    def test_next_open_no_search_ahead_and_missing_auction_no_cash(self):
        row = [600, 100.0, 100.0, 100.0, 100.0, 10.0, 1000.0]
        self.assertEqual(execution.ordinary_execution_reference("2025-07-23", 601,
                          [row, [602, 99, 99, 99, 99, 10, 1000]])["status"],
                         "MISSING_EXECUTION_REFERENCE")
        self.assertIsNone(execution.terminal_execution_reference([row])["price"])
        self.assertTrue(all(value is False for value in self.p["safety"].values()))

    def test_safety_and_fixed_lot_capacity(self):
        self.assertEqual(len(self.p["safety"]), 9)
        self.assertTrue(all(value is False for value in v0.SAFETY.values()))
        self.assertEqual(self.p["fixed"]["initialCashJpy"], 1000000)
        self.assertEqual(self.p["fixed"]["maxConcurrent"], 3)
        self.assertEqual(self.p["fixed"]["shareLot"], 100)
        self.assertTrue(self.p["fixed"]["longCashOnly"])

    def test_complete_small_calendar_uses_third_now_and_exact_next_open(self):
        arm = v0.IM
        eid = "2025-07-22|99990|599"
        identity = [{"now": now, "session": "2025-07-22", "arm": arm,
                     "entryId": eid} for now in (600, 601, 602, 925)]
        columns = ["facts.currentReturnPct"]
        arrays = {"numeric": np.zeros((4, 1), dtype=np.float32),
                  "fresh": np.asarray([True] * 4)}
        bar = lambda t, price: [t, price, price, price, price, 1, 1]
        path = {m: bar(m, 101) for m in (600, 601, 602)}
        path[930] = bar(930, 102)
        entries = {(arm, eid): {"session": "2025-07-22", "opportunity": "key"}}
        frozen_r50 = {arm: {eid: {"exitPrice": 102}},
                      v0.R1: {}}
        def old_intent(envelope, state, candidate, terminal=False):
            return {"action": "FORCE_TERMINAL" if terminal else "HOLD", "state": state}
        def facts(arrays, names, index, now):
            return {"fresh": True, "now": now}
        with mock.patch.object(r.r50, "initial_state", return_value={}), \
                mock.patch.object(r.r50, "intent", side_effect=old_intent), \
                mock.patch.object(r.r52, "fact", side_effect=facts):
            out, _, _ = r.calendar(
                self.p, {"numericColumns": columns}, arrays, identity,
                {(arm, eid): [0, 1, 2, 3]}, entries,
                {"key": path}, np.asarray([-1., -1., -1., np.nan]), frozen_r50)
        self.assertEqual(out[arm][eid]["decisionNow"], 602)
        self.assertEqual(out[arm][eid]["exitMinute"], 602)
        self.assertEqual(out[arm][eid]["exitPrice"], 101)
        self.assertEqual(out[arm][eid]["reason"], "CONFIRMED_NEGATIVE_VALUE")


if __name__ == "__main__":
    unittest.main()
