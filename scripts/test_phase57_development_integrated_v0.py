"""Synthetic / contract tests only: no historical enrichment or performance."""
import copy
import gzip
import tempfile
import unittest
from pathlib import Path

from scripts import phase57_cash_capital_r34 as cash
from scripts import phase57_cash_portfolio_r37 as sized
from scripts import phase57_development_integrated_v0 as integrated


def intent(symbol="11110", minute=600, rank=1, score=.2, session="2025-07-03"):
    stamp=integrated.minute_stamp(session,minute)
    return {"entryId":f"{session}|{symbol}|{minute}","symbol":symbol,
            "timestamp":stamp,"entryKnownAt":stamp,"effectiveEntryPrice":1000,
            "newEligibleRank":rank,"savedV1Score":score,"rankKnownAt":stamp,
            "side":"LONG","account":"CASH"}


class IntegratedBenchmarkSyntheticTests(unittest.TestCase):
    def test_protocol_hash_and_safety9(self):
        a,b=integrated.load_contract()
        self.assertEqual(b["controllingEvaluationCohort"]["fillsByArm"][integrated.IM],1150)
        self.assertFalse(any(a["safety"].values()))
        self.assertEqual(a["exit"]["status"],"BENCHMARK_NOT_FINAL_EXIT")

    def test_allowlist_before_raw_value_json_decode(self):
        source='{"2025-07-03|11110":{"today":[[600,100,100,100,100,1,1]]},"OUTSIDE":{"secret":invalid}}'
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"raw.gz"
            path.write_bytes(gzip.compress(source.encode()))
            projected,skipped=integrated.allowlisted_raw_paths(path,{"2025-07-03|11110"})
        self.assertEqual(skipped,1)
        self.assertEqual(projected["2025-07-03|11110"][600][1],100)
        self.assertNotIn("OUTSIDE",projected)

    def test_allowlist_before_origin_payload_json_decode(self):
        allowed='{"WHO":{"ignored":"yes"},"id":"S","origin":{"decisionTimestamp":"2025-07-03T10:00:00+09:00","newEligibleRank":1,"savedV1Score":7}}'
        outsiders=[f'{{"id":"O{i:04d}","origin":invalid}}' for i in range(5374)]
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"origins.gz"
            path.write_bytes(gzip.compress(("["+",".join([allowed]+outsiders)+"]").encode()))
            projected=integrated.frozen_origin_projection(path,integrated.digest(path),{"S"})
        self.assertEqual(set(projected),{"S"})
        self.assertEqual(projected["S"]["newEligibleRank"],1)

    def test_exact_now_bar_mark_and_no_forward_search(self):
        raw={"2025-07-03|11110":{599:[599,100,200,40,101,100,1],
                                    600:[600,102,999,1,103,100,1],
                                    601:[601,104,200,1,105,100,1]}}
        self.assertEqual(integrated.fresh_mark(raw,"2025-07-03","11110",600,"x")["price"],101)
        self.assertEqual(integrated.fresh_mark(raw,"2025-07-03","11110",600,"x",newly_entered=True)["price"],102)
        self.assertIsNone(integrated.fresh_mark(raw,"2025-07-03","11110",603,"x"))
        self.assertIsNone(integrated.fresh_mark(raw,"2025-07-03","11110",750,"x"))
        self.assertIsNone(integrated.fresh_mark(raw,"2025-07-03","11110",930,"x"))

    def test_rank_and_future_denylist(self):
        self.assertEqual([x["symbol"] for x in sorted([
            intent("22220",rank=1,score=.1),intent("33330",rank=2,score=9),
            intent("11110",rank=1,score=.2)],key=integrated.event_priority)],
            ["11110","22220","33330"])
        p=sized.SizedCashPortfolio(3)
        future=dict(intent(),entryToPostEntryHighPct=10,exitPrice=900)
        with self.assertRaisesRegex(ValueError,"ALLOWLIST"):
            p.step(intent()["timestamp"],entry_intents=[future])
        bad=intent(); bad["rankKnownAt"]=integrated.minute_stamp("2025-07-03",601)
        with self.assertRaisesRegex(ValueError,"FUTURE_RANK"):
            p.step(bad["timestamp"],entry_intents=[bad])

    def test_confirmed_cash_release_then_same_time_entry(self):
        p=sized.SizedCashPortfolio(3)
        p.book=integrated.CensoredCashBook(3)
        s=integrated.minute_stamp("2025-07-03",600)
        e=intent()
        first=p.step(s,entry_intents=[e])
        self.assertEqual(first["sizing"][0]["status"],"SIZED")
        second_stamp=integrated.minute_stamp("2025-07-03",601)
        confirmed={"entryId":e["entryId"],"timestamp":second_stamp,
                   "knownAt":second_stamp,"price":1100,"confirmed":True}
        second=p.step(second_stamp,entry_intents=[intent("22220",minute=601)],
                      exits=[confirmed])
        self.assertEqual(second["postExitPreview"]["events"][0]["status"],"CLOSED")
        self.assertEqual(second["sizing"][0]["status"],"SIZED")
        self.assertGreaterEqual(float(second["ledger"]["cashJpy"]),0)

    def test_unconfirmed_exit_locks_cash_and_overnight(self):
        p=sized.SizedCashPortfolio(3)
        p.book=integrated.CensoredCashBook(3)
        e=intent()
        p.step(e["timestamp"],entry_intents=[e])
        stamp=integrated.minute_stamp("2025-07-03",930)
        unknown={"entryId":e["entryId"],"timestamp":stamp,"knownAt":stamp,
                 "price":None,"confirmed":False}
        event=p.step(stamp,exits=[unknown])
        self.assertEqual(event["postExitPreview"]["events"][0]["status"],
                         "UNRESOLVED_NO_CASH_RELEASE")
        locked=float(p.book.cash)
        day2=p.step(integrated.minute_stamp("2025-07-04",540),
                    entry_intents=[intent("22220",minute=540,session="2025-07-04")])
        self.assertEqual(day2["sizing"][0]["reason"],"MISSING_FRESH_MARK_UNRESOLVED_SIZING")
        self.assertEqual(float(p.book.cash),locked)
        self.assertIn(e["entryId"],p.book.positions)

    def test_lot_capacity_cash_and_no_short(self):
        for n in integrated.CAPACITIES:
            p=sized.SizedCashPortfolio(n)
            rows=[intent(str(11110+j*10),rank=j+1) for j in range(n+2)]
            batch=p.step(rows[0]["timestamp"],entry_intents=rows)
            accepted=[x for x in batch["sizing"] if x["status"]=="SIZED"]
            self.assertLessEqual(len(accepted),n)
            self.assertTrue(all(x["quantity"]%100==0 for x in accepted))
            self.assertGreaterEqual(float(p.book.cash),0)
        x=intent(); x["side"]="SHORT"
        with self.assertRaisesRegex(ValueError,"CASH_LONG_ONLY"):
            sized.SizedCashPortfolio(3).step(x["timestamp"],entry_intents=[x])

    def test_missing_mark_blocks_sizing_no_borrow(self):
        p=sized.SizedCashPortfolio(3)
        first=intent()
        p.step(first["timestamp"],entry_intents=[first])
        later=intent("22220",minute=601)
        batch=p.step(later["timestamp"],entry_intents=[later],marks={})
        self.assertEqual(batch["sizing"][0]["reason"],"MISSING_FRESH_MARK_UNRESOLVED_SIZING")
        self.assertIsNone(batch["freshSnapshot"]["equityJpy"])

    def test_evaluator_is_downstream_not_runtime_input(self):
        self.assertTrue(integrated.bucket({"postUpsidePct":5,"canonicalBucket":"<5%"},
                                          "POST_ENTRY_UPSIDE_GE5"))
        self.assertFalse(integrated.bucket({"postUpsidePct":4,"canonicalBucket":"<5%"},
                                           "POST_ENTRY_UPSIDE_GE5"))
        self.assertNotIn("evaluation",integrated.replay.__code__.co_varnames)
        self.assertNotIn("exitPrice",sized.INTENT_FIELDS)

    def test_no_final_exit_select_claim(self):
        with self.assertRaisesRegex(ValueError,"NO_SELECTION"):
            sized.require_select_freeze({"outcome":"NO_SELECTION_STOP"})
        self.assertEqual(integrated.load_contract()[0]["exit"]["status"],
                         "BENCHMARK_NOT_FINAL_EXIT")

    def test_synthetic_terminal_replay_cost_once_and_determinism(self):
        e=intent()
        cohort={"sessions":["2025-07-03","2025-07-04"]}
        terminal={e["entryId"]:{"session":"2025-07-03","exitMinute":930,
                                 "exitPrice":1100,"exitKind":"FORCED_TERMINAL"}}
        raw={"2025-07-03|11110":{600:[600,1000,1000,1000,1000,100,100000],
                                    930:[930,1100,1100,1100,1100,100,110000]}}
        a=integrated.replay(integrated.IM,3,cohort,[e],terminal,raw)
        b=integrated.replay(integrated.IM,3,cohort,[e],terminal,raw)
        self.assertEqual(integrated.canonical(a),integrated.canonical(b))
        self.assertEqual(len(a["closed"]),1)
        trade=a["closed"][0]
        self.assertAlmostEqual(float(trade["netReturnPct"]),9.95)
        self.assertEqual(a["snapshots"][-1]["equityJpy"],"1029850.00")
        self.assertEqual(a["endOpenEntryIds"],[])
        alternative=copy.deepcopy(raw)
        alternative["2025-07-03|11110"][930]=[930,900,900,900,900,100,90000]
        alternative_terminal=copy.deepcopy(terminal)
        alternative_terminal[e["entryId"]]["exitPrice"]=900
        later_changed=integrated.replay(integrated.IM,3,cohort,[e],alternative_terminal,alternative)
        self.assertEqual(a["events"][1]["sizing"],later_changed["events"][1]["sizing"])
        self.assertNotEqual(a["closed"][0]["netReturnPct"],
                            later_changed["closed"][0]["netReturnPct"])


if __name__=="__main__":
    unittest.main()
