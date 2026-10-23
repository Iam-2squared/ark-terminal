"""Accounting-only synthetic checks, run before Development performance."""
import copy
import json
import unittest
from decimal import Decimal

from scripts import phase57_cash_capital_r34 as cash
from scripts import phase57_development_integrated_v0 as v0
from scripts import phase57_development_integrated_v1 as v1

DAY = "2025-07-03"
NEXT = "2025-07-04"
EID = DAY + "|59050|578"
STAMP = v0.minute_stamp


def bar(minute, value, close=None):
    return [minute, value, value, value, close if close is not None else value, 100, 100 * value]


def synthetic(*, terminal_price=None, next_day_raw=None):
    raw = {DAY+"|59050": {578: bar(578, 100), 579: bar(579, 101),
                             920: bar(920, 105)}}
    if terminal_price is not None:
        raw[DAY+"|59050"][930] = bar(930, terminal_price)
    if next_day_raw is not None:
        raw[NEXT+"|59050"] = {540: bar(540, next_day_raw)}
    intent = {"entryId": EID, "symbol": "59050", "timestamp": STAMP(DAY, 578),
              "entryKnownAt": STAMP(DAY, 578), "effectiveEntryPrice": 100.05,
              "newEligibleRank": 1, "savedV1Score": 1,
              "rankKnownAt": STAMP(DAY, 578), "side": "LONG", "account": "CASH"}
    cohort = {"sessions": [DAY, NEXT]}
    terminal = {EID: {"session": DAY, "exitMinute": 930 if terminal_price else None,
                      "exitPrice": terminal_price, "exitKind": "FORCED_TERMINAL"}}
    return cohort, [intent], terminal, raw


class IntegratedV1Synthetic(unittest.TestCase):
    def test_frozen_protocol_and_single_option(self):
        p = v1.contract()
        self.assertEqual(len(p["valuationOptions"]), 1)
        self.assertEqual(p["scope"]["capacities"], [3,4,5])
        self.assertFalse(any(p["safety"].values()))

    def test_future_suffix_isolation_and_closed_bar(self):
        raw = {DAY+"|59050": {578: bar(578, 100), 579: bar(579, 101, 104)}}
        at_579 = v1.observed_mark(raw, DAY, "59050", 579, 578, DAY)
        self.assertEqual(at_579["sourceMinute"], 578)
        self.assertEqual(at_579["price"], 100)
        at_580 = v1.observed_mark(raw, DAY, "59050", 580, 578, DAY)
        self.assertEqual(at_580["sourceMinute"], 579)
        self.assertEqual(at_580["price"], 104)
        raw[DAY+"|59050"][600] = bar(600, 999)
        self.assertEqual(v1.observed_mark(raw, DAY, "59050", 580, 578, DAY), at_580)

    def test_mark_is_raw_price_not_cost_inclusive_fill(self):
        cohort, intents, terminal, raw = synthetic()
        mark = v1.observed_mark(raw, DAY, "59050", 578, 578, DAY)
        self.assertEqual(mark["price"], 100)
        self.assertNotEqual(mark["price"], intents[0]["effectiveEntryPrice"])
        self.assertEqual(mark["source"], "RAW_ENTRY_OPEN_ASOF")

    def test_missing_auction_is_not_filled_or_cash_released(self):
        cohort, intents, terminal, raw = synthetic()
        result = v1.replay(v0.IM, 3, cohort, intents, terminal, raw)
        self.assertEqual(len(result["closed"]), 0)
        self.assertEqual(result["endOpenEntryIds"], [EID])
        self.assertEqual(result["unresolvedEntryIds"], [EID])
        self.assertEqual(result["finalCashJpy"], "669835.00")
        eod = next(x for x in result["snapshots"] if x["session"] == DAY and x["minute"] == 930)
        self.assertTrue(eod["equityValid"])
        position = eod["positions"][0]
        self.assertEqual(position["markSource"], "RAW_LAST_COMPLETED_CLOSE_SAME_SEGMENT")
        self.assertEqual(position["staleMinutes"], 9)
        self.assertTrue(position["unresolvedExit"])
        self.assertEqual(position["markPrice"], 105)
        next_open = next(x for x in result["snapshots"] if x["session"] == NEXT)
        self.assertIsNone(next_open["equityJpy"])
        self.assertEqual(next_open["cashJpy"], result["finalCashJpy"])
        self.assertEqual(next_open["positions"][0]["missingReason"],
                         "UNCERTIFIED_OVERNIGHT_CORPORATE_ACTION_AND_NO_CROSS_SESSION_MARK")

    def test_after_missing_auction_even_available_next_day_price_is_not_assumed(self):
        cohort, intents, terminal, raw = synthetic(next_day_raw=99)
        result = v1.replay(v0.IM, 3, cohort, intents, terminal, raw)
        self.assertIsNone(result["snapshots"][-1]["equityJpy"])
        self.assertEqual(result["missingReferences"][-1]["rawKeyAllowlisted"], True)

    def test_confirmed_auction_exits_with_cost_once(self):
        cohort, intents, terminal, raw = synthetic(terminal_price=110)
        result = v1.replay(v0.IM, 3, cohort, intents, terminal, raw)
        self.assertEqual(len(result["closed"]), 1)
        self.assertEqual(result["endOpenEntryIds"], [])
        closed = result["closed"][0]
        self.assertEqual(Decimal(closed["sellCostJpy"]), Decimal("165.082500"))
        self.assertEqual(Decimal(closed["realizedPnlJpy"]), Decimal("32669.917500"))
        self.assertEqual(Decimal(result["finalCashJpy"]), Decimal("1032669.917500"))
        self.assertEqual(result["snapshots"][-1]["equityJpy"], result["finalCashJpy"])

    def test_auction_must_be_observed_single_price(self):
        raw = {DAY+"|59050": {578: bar(578, 100), 930: [930,100,101,99,100,100,10000]}}
        with self.assertRaisesRegex(ValueError, "NOT_SINGLE_PRICE_AUCTION"):
            v1.observed_mark(raw, DAY, "59050", 930, 578, DAY)

    def test_no_cross_lunch(self):
        raw = {DAY+"|59050": {578: bar(578,100)}}
        self.assertIsNone(v1.observed_mark(raw, DAY, "59050", 750, 578, DAY))

    def test_post_lunch_new_completed_bar_reprices_morning_owned_position(self):
        raw = {DAY+"|59050": {578: bar(578,100), 750: bar(750,110,109)}}
        self.assertIsNone(v1.observed_mark(raw, DAY, "59050", 750, 578, DAY))
        mark = v1.observed_mark(raw, DAY, "59050", 751, 578, DAY)
        self.assertEqual(mark["price"],109)
        self.assertEqual(mark["knownAt"],STAMP(DAY,751))

    def test_no_cross_session_mark(self):
        cohort, intents, _, raw = synthetic()
        self.assertIsNone(v1.observed_mark(raw, NEXT, "59050", 540, 578, DAY))
        book = v1.AsOfCensoredCashBook(3)
        book.step(STAMP(DAY, 578), entries=[{**intents[0], "quantity": 100}])
        book.step(STAMP(DAY, 930), exits=[{"entryId":EID,"timestamp":STAMP(DAY,930),
                                           "knownAt":STAMP(DAY,930),
                                           "price":None,"confirmed":False}])
        book.step(STAMP(NEXT, 540))
        with self.assertRaisesRegex(ValueError, "CROSS_SEGMENT_OR_SESSION_STALE_MARK"):
            book.snapshot(STAMP(NEXT, 540), {EID: {"timestamp": STAMP(DAY,920),
                             "knownAt": STAMP(DAY,920), "price": 100}})
        with self.assertRaisesRegex(ValueError, "UNCERTIFIED_CROSS_SESSION_MARK"):
            book.snapshot(STAMP(NEXT, 540), {EID: {"timestamp": STAMP(NEXT,540),
                             "knownAt": STAMP(NEXT,540), "price": 100}})

    def test_future_and_pre_entry_marks_blocked(self):
        cohort, intents, _, raw = synthetic()
        book = v1.AsOfCensoredCashBook(3)
        book.step(STAMP(DAY,578),entries=[{**intents[0],"quantity":100}])
        for m, phrase in [(579,"FUTURE_OR_PRE_ENTRY_MARK"),(577,"FUTURE_OR_PRE_ENTRY_MARK")]:
            with self.subTest(minute=m), self.assertRaisesRegex(ValueError,phrase):
                book.snapshot(STAMP(DAY,578),{EID: {"timestamp":STAMP(DAY,m),
                     "knownAt":STAMP(DAY,m),"price":100}})

    def test_missing_mark_is_null_not_zero_pnl(self):
        cohort, intents, _, raw = synthetic()
        book = v1.AsOfCensoredCashBook(3)
        book.step(STAMP(DAY,578),entries=[{**intents[0],"quantity":100}])
        snap=book.snapshot(STAMP(DAY,578))
        self.assertEqual(snap["cashJpy"], "989995.00")
        self.assertIsNone(snap["equityJpy"])
        self.assertIsNone(snap["grossExposureJpy"])
        self.assertIsNone(snap["unrealizedPnlJpy"])

    def test_missing_valuation_rejects_new_sizing_without_cash_reuse(self):
        cohort, intents, terminal, raw = synthetic()
        other = {**intents[0], "entryId": NEXT+"|12345|550", "symbol": "12345",
                 "timestamp":STAMP(NEXT,550),"entryKnownAt":STAMP(NEXT,550),
                 "rankKnownAt":STAMP(NEXT,550)}
        raw[NEXT+"|12345"] = {550:bar(550,100)}
        result=v1.replay(v0.IM,3,cohort,[intents[0],other],terminal,raw)
        rows=[e for e in result["events"] if e["session"]==NEXT and e["minute"]==550]
        self.assertEqual(rows[0]["sizing"][0]["reason"],"MISSING_FRESH_MARK_UNRESOLVED_SIZING")
        self.assertEqual(len(result["funded"]),1)
        self.assertEqual(result["finalCashJpy"],"669835.00")

    def test_exact_priority_no_outcome_input_and_determinism(self):
        cohort,intents,terminal,raw=synthetic()
        a=v1.replay(v0.IM,3,cohort,intents,terminal,raw)
        b=v1.replay(v0.IM,3,cohort,copy.deepcopy(intents),terminal,raw)
        self.assertEqual(v0.canonical(a),v0.canonical(b))
        with self.assertRaisesRegex(ValueError,"SIZING_INTENT_ALLOWLIST"):
            v1.replay(v0.IM,3,cohort,[{**intents[0],"futureHigh":1000}],terminal,raw)

    def test_max3_4_5_only_and_safety(self):
        cohort,intents,terminal,raw=synthetic()
        with self.assertRaisesRegex(ValueError,"VARIANT_ALLOWLIST"):
            v1.replay(v0.IM,6,cohort,intents,terminal,raw)
        self.assertEqual(set(v1.SAFETY),set(cash.SAFETY))
        self.assertFalse(any(v1.SAFETY.values()))

    def test_curve_null_gap_does_not_invent_drawdown(self):
        cohort,intents,terminal,raw=synthetic()
        c=v1.curve(v1.replay(v0.IM,3,cohort,intents,terminal,raw))
        self.assertIsNone(c[-1]["equityJpy"])
        self.assertIsNone(c[-1]["drawdownPct"])
        self.assertFalse(c[-1]["equityValid"])


if __name__ == "__main__":
    unittest.main()
