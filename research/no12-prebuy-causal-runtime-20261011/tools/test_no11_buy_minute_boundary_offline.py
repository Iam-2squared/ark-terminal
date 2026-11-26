"""Isolated tests of exact source functions; no runtime import or broker transport."""
import ast
import datetime as dt
from decimal import Decimal, InvalidOperation
from pathlib import Path
import re
from types import SimpleNamespace
import unittest

HERE = Path(__file__).resolve().parent
SESSION = "2026-11-30"
JST = dt.timezone(dt.timedelta(hours=9))


def stamp(clock):
    return SESSION + "T" + clock + "+09:00"


def timestamp(value, session):
    value = dt.datetime.fromisoformat(value)
    if value.date().isoformat() != session or value.utcoffset() != dt.timedelta(hours=9):
        raise ValueError("session")
    return value


def instant(value, session):
    # Synthetic input uses whole seconds. The production instant() parser
    # remains unchanged and has its own precision regression suite.
    return int(timestamp(value, session).timestamp()) * 1_000_000_000


def extract(filename, names, env, class_method=None):
    tree = ast.parse((HERE / filename).read_text(encoding="utf-8-sig"))
    nodes = tree.body if class_method is None else next(
        n.body for n in tree.body if isinstance(n, ast.ClassDef)
        and any(isinstance(m, ast.FunctionDef) and m.name == class_method for m in n.body))
    functions = [n for n in nodes if isinstance(n, ast.FunctionDef) and n.name in names]
    if {n.name for n in functions} != set(names):
        raise AssertionError("source function missing")
    exec(compile(ast.Module(body=functions, type_ignores=[]), filename, "exec"), env)
    return env


def candidate(clock="09:35:59", key="candidate-a"):
    return {"candidateId": key, "decisionAtJst": stamp(clock),
            "symbol": "7203.T", "entry_timestamp": stamp("09:35:00"),
            "asofReferenceBarEndJst": stamp("09:35:00"),
            "referenceKnownAtJst": stamp("09:35:01")}


def minute(value):
    return value.hour * 60 + value.minute


def make_env():
    h = SimpleNamespace(timestamp=timestamp, minute=minute,
                        eligible_closed_minute=lambda m: 541 <= m <= 691 or 751 <= m <= 926,
                        SYMBOL=re.compile(r"[0-9A-Z]{4}\.T"), digest=lambda obj: repr(obj))
    env = {"h": h, "instant": instant, "Decimal": Decimal,
           "InvalidOperation": InvalidOperation, "ACCOUNTS": {"TEST"},
           "INTENT_SCHEMA": "TEST_INTENT", "digest": repr}
    extract("no11_broker_decision_bridge.py",
            ["need", "money", "quantity", "candidate_current_for_funding",
             "capital_strategy_time", "calculate_capital"], env)
    return env


class TestBoundary(unittest.TestCase):
    def setUp(self):
        self.e = make_env()
        self.current = self.e["candidate_current_for_funding"]
        self.strategy = self.e["capital_strategy_time"]

    def test_two_seconds_across_minute(self):
        row = candidate()
        self.assertTrue(self.current(row, stamp("09:36:01"), SESSION))
        self.assertEqual(self.strategy({"results": [row]}, stamp("09:36:01"), SESSION),
                         stamp("09:35:59"))

    def test_same_minute_still_allowed(self):
        self.assertTrue(self.current(candidate("09:35:10"), stamp("09:35:11"), SESSION))

    def test_stale_future_and_cutoff(self):
        self.assertFalse(self.current(candidate(), stamp("09:37:30"), SESSION))
        self.assertFalse(self.current(candidate(), stamp("09:35:58"), SESSION))
        self.assertFalse(self.current(candidate("15:19:59"), stamp("15:20:00"), SESSION))
        self.assertFalse(self.current(candidate("11:29:59"), stamp("11:30:00"), SESSION))
        self.assertFalse(self.current(candidate("11:59:59"), stamp("12:00:00"), SESSION))
        self.assertTrue(self.current(candidate("12:35:59"), stamp("12:36:01"), SESSION))
        with self.assertRaises(ValueError):
            self.current(candidate(), "2026-12-01T09:36:01+09:00", SESSION)

    def test_existing_90_second_bound_inclusive(self):
        self.assertTrue(self.current(candidate(), stamp("09:37:29"), SESSION))
        self.assertFalse(self.current(candidate(), stamp("09:37:30"), SESSION))

    def test_frozen_minute_and_actual_intent_clock_distinct(self):
        row = candidate()
        at = stamp("09:36:01")
        account = {"schemaId": "ARK_NO11_BROKER_CAPITAL_INPUT_V1",
                   "sessionDate": SESSION, "decisionAtJst": at, "account": "TEST",
                   "entryBlocked": False, "pendingOrders": False, "positions": [],
                   "externalSymbols": [], "availableCashJpy": "200000",
                   "exposureJpy": "0", "equityJpy": "200000"}
        observed = {}
        def build_request(batch, validation, arrival):
            observed["strategy"] = validation["decisionAtJst"]
            self.assertEqual(validation["arkCapitalInputs"]["cash"], "0")
            strategy_min = minute(timestamp(validation["decisionAtJst"], SESSION))
            for item in batch["results"]:
                if minute(timestamp(item["decisionAtJst"], SESSION)) != strategy_min:
                    raise ValueError("mixed minute")
            return {"minute": strategy_min, "preorderedCandidates": [{
                "entry_id": row["candidateId"], "brokerSymbol": row["symbol"],
                "block": "8", "raw_reference": "1000"}]}
        def gate(item, slots, logical_min, table):
            observed["slot_minute"] = logical_min
            return True, "", None
        def allocate(rows, equity, exposure, cash, bands):
            return [{"entry_id": row["candidateId"], "quantity": 100,
                     "debit": Decimal("100050"), "equity_cap": Decimal("200000"),
                     "band": "A", "batch_budget": Decimal("200000"),
                     "first_pass_quantity": 100, "water_fill_lots": 0}]
        self.e.update(hcap=SimpleNamespace(SCENARIO="TEST", FROZEN="TEST",
                                           build_request=build_request),
                      original_functions=lambda: (SimpleNamespace(allocation=allocate),
                                                  SimpleNamespace(gate=gate)))
        calculate = self.e["calculate_capital"]
        result = calculate({"results": [row]}, account, {"8": {}})
        self.assertEqual(observed["strategy"], stamp("09:35:59"))
        self.assertEqual(observed["slot_minute"], 575)
        self.assertEqual(result["intents"][0]["createdAtJst"], at)
        self.assertEqual(result["intents"][0]["quantity"], 100)
        self.assertFalse(result["orderTransmission"])
        # The existing validator must still refuse mixed source-minute batches.
        other = candidate("09:36:00", "candidate-b")
        other["symbol"] = "6758.T"
        with self.assertRaises(ValueError):
            calculate({"results": [row, other]}, account, {"8": {}})

    def test_service_funds_once_and_never_replays(self):
        env = {"h": self.e["h"], "need": self.e["need"]}
        calls, dispatch = [], []
        def calculate(batch, account, arrival):
            calls.append(batch)
            return {"intents": [{"side": "BUY", "synthetic": True}]}
        env["decisions"] = SimpleNamespace(candidate_current_for_funding=self.current,
                                            calculate_capital=calculate)
        extract("no11_broker_execution_service.py", ["fund"], env, class_method="fund")
        state = {}
        book = SimpleNamespace(source_checkpoint=lambda k: state.get(k),
                               checkpoint_source=lambda k, v, at: state.update({k: v}))
        service = SimpleNamespace(session=SESSION, book=book, arrival={},
                                  _capital_input=lambda quotes, at: {"decisionAtJst": at},
                                  clock=lambda: stamp("09:36:01"),
                                  submit_intents=lambda intents, at: dispatch.append((intents, at)))
        batch = {"results": [candidate()]}
        env["fund"](service, batch, {}, stamp("09:36:01"))
        self.assertEqual(len(calls), 1)
        self.assertEqual(len(dispatch), 1)
        self.assertEqual(dispatch[0][1], stamp("09:36:01"))
        self.assertIsNone(env["fund"](service, batch, {}, stamp("09:36:02")))
        self.assertEqual(len(dispatch), 1)
        with self.assertRaises(ValueError):
            env["fund"](service, {"results": [candidate("09:36:00")]}, {}, stamp("09:36:02"))


if __name__ == "__main__":
    unittest.main()
