"""Corruption rejection tests; synthetic rows only, no policy replay or fit."""
from __future__ import annotations

import copy
import gzip
import json
from pathlib import Path
import tempfile
import unittest

from scripts import phase57_exit_gen2_ledger_audit_r43 as audit


def fixture(*, terminal=False, missing=False, complete=True):
    day = "2025-07-03"
    entry = {"session": day, "entryId": day + "|SYN|540", "opportunity": day + "|SYN",
             "entryMinute": 540, "price": 100.0, "entryArm": "IMMEDIATE"}
    path = [[540, 100, 101, 99, 100, 1, 100], [541, 100, 200, 99, 102, 1, 100],
            [924, 102, 103, 101, 102, 1, 102]]
    if not missing:
        path.append([930, 102, 102, 102, 102, 1, 102])
    pos = {"observedRunningHigh": 101.0, "peakConfirmedAt": 541.0,
           "fullOwnedPrefix": float(complete)}
    minute = None if missing and terminal else 930 if terminal else 541
    price = None if minute is None else 102.0 if terminal else 100.0
    candidate = audit.runtime.load_protocol()["candidates"][0]
    metrics = audit.r36.evaluate_capture(entry_price=100.0, entry_minute=540,
        exit_price=price, exit_minute=minute, cost_pp=0.05, geometry=None, post_entry_high=None,
        owned_peak=None if price is None else 101.0,
        owned_peak_confirmed_at=None if price is None else 541, owned_path_complete=complete)
    row = {"candidateId": candidate["candidateId"], "entryArm": "IMMEDIATE", "fold": 1,
        "session": day, "opportunity": entry["opportunity"], "entryId": entry["entryId"],
        "entryMinute": 540, "entryPrice": 100.0, "decisionNow": 925 if terminal else 541,
        "exitStatus": "UNRESOLVED_TERMINAL_EXIT" if minute is None else "RESOLVED",
        "exitKind": None if minute is None else "FORCED_TERMINAL" if terminal else "MODEL_EXIT",
        "exitMinute": minute, "exitPrice": price, "missingOrdinaryReferences": 0,
        "activeMinutesHeld": None if minute is None else audit.r36.execution.active_minutes(day, 540, minute),
        "wallMinutesHeld": None if minute is None else minute - 540,
        "earlyExitOpportunityCostPp": None if minute is None else 0.0 if terminal else 100.0,
        "netReturnPctBySellCost": {f"{c:.2f}": None if price is None else 100 * (price / 100 - 1) - c
                                  for c in audit.r36.COSTS},
        "nonselectableDiagnostic": False, "metrics": metrics}
    context = {"candidate": candidate, "fresh": not terminal,
               "scores": [float("nan"), float("nan")] if terminal else [0.2, 0.8],
               "geometry": None, "post_high": None}
    return row, entry, path, pos, context


class LedgerAuditTests(unittest.TestCase):
    def test_valid_ordinary_terminal_censored_and_incomplete_rows(self):
        for options in ({}, {"terminal": True}, {"terminal": True, "missing": True}, {"complete": False}):
            row, entry, path, pos, context = fixture(**options)
            audit.validate_semantics(row, entry, path, pos, **context)
            expected = {"IMMEDIATE::" + entry["entryId"]: entry}
            self.assertEqual(len(audit.validate_population([row], row["candidateId"], expected,
                                                          {entry["session"]: 1})), 1)

    def test_changed_frozen_entry_price_or_fold_fails(self):
        row, entry, _, _, _ = fixture()
        expected = {"IMMEDIATE::" + entry["entryId"]: entry}
        for field, value, reason in (("entryPrice", 100.1, "FROZEN_ENTRY"), ("fold", 2, "FOLD_LINEAGE")):
            corrupt = copy.deepcopy(row); corrupt[field] = value
            with self.assertRaisesRegex(ValueError, reason):
                audit.validate_population([corrupt], row["candidateId"], expected, {entry["session"]: 1})

    def test_duplicate_or_missing_entry_is_rejected(self):
        row, entry, _, _, _ = fixture()
        second = {**entry, "entryId": entry["entryId"] + "X"}
        expected = {"IMMEDIATE::" + r["entryId"]: r for r in (entry, second)}
        with self.assertRaisesRegex(ValueError, "DUPLICATE_ENTRY_ID"):
            audit.validate_population([row, row], row["candidateId"], expected, {entry["session"]: 1})
        with self.assertRaisesRegex(ValueError, "LEDGER_ROW_COUNT"):
            audit.validate_population([row], row["candidateId"], expected, {entry["session"]: 1})

    def test_wrong_execution_open_or_time_is_rejected(self):
        row, entry, path, pos, context = fixture()
        for field, value in (("exitPrice", 101.0), ("exitMinute", 542)):
            corrupt = copy.deepcopy(row); corrupt[field] = value
            with self.assertRaisesRegex(ValueError, "EXACT_ORDINARY"):
                audit.validate_semantics(corrupt, entry, path, pos, **context)
        with self.assertRaisesRegex(ValueError, "REFERENCE_MISSING"):
            audit.validate_semantics(row, entry, [r for r in path if r[0] != 541], pos, **context)

    def test_model_exit_requires_fresh_current_registered_scores(self):
        row, entry, path, pos, context = fixture()
        with self.assertRaisesRegex(ValueError, "FRESHNESS"):
            audit.validate_semantics(row, entry, path, pos, **{**context, "fresh": False})
        with self.assertRaisesRegex(ValueError, "CURRENT_SCORES"):
            audit.validate_semantics(row, entry, path, pos, **{**context, "scores": [0.9, 0.1]})

    def test_cost_corruption_and_owned_null_corruption_are_rejected(self):
        row, entry, path, pos, context = fixture(complete=False)
        cost = copy.deepcopy(row); cost["netReturnPctBySellCost"]["0.05"] += 0.01
        with self.assertRaisesRegex(ValueError, "FIXED_COST"):
            audit.validate_semantics(cost, entry, path, pos, **context)
        owned = copy.deepcopy(row); owned["metrics"]["ownedPeakGivebackPp"] = 1.0
        with self.assertRaisesRegex(ValueError, "OWNERSHIP_NULL"):
            audit.validate_semantics(owned, entry, path, pos, **context)

    def test_terminal_cannot_substitute_925_close_or_invent_missing_fill(self):
        row, entry, path, pos, context = fixture(terminal=True)
        row["exitMinute"] = 925
        with self.assertRaisesRegex(ValueError, "TERMINAL_MINUTE"):
            audit.validate_semantics(row, entry, path, pos, **context)
        row, entry, path, pos, context = fixture(terminal=True, missing=True)
        row["exitPrice"] = 102.0
        with self.assertRaisesRegex(ValueError, "CENSORED_EXIT_PRICE"):
            audit.validate_semantics(row, entry, path, pos, **context)

    def test_neutral_cannot_be_a_model_exit_or_have_missing_intents(self):
        row, entry, path, pos, context = fixture()
        with self.assertRaisesRegex(ValueError, "MODEL_EXIT_FRESHNESS"):
            audit.validate_semantics(row, entry, path, pos, **{**context, "candidate": None})
        row, entry, path, pos, context = fixture(terminal=True)
        row["missingOrdinaryReferences"] = 1
        with self.assertRaisesRegex(ValueError, "NEUTRAL_NOT_TERMINAL_ONLY"):
            audit.validate_semantics(row, entry, path, pos, **{**context, "candidate": None})

    def test_byte_corruption_and_unregistered_extra_file_are_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); filenames = {"SYN.jsonl.gz"}
            for name in ("run-a", "run-b"):
                (root / name).mkdir()
                (root / name / "SYN.jsonl.gz").write_bytes(b"frozen bytes")
            digest = audit.r36.sha(root / "run-a/SYN.jsonl.gz")
            final = {"ledgerHashes": {"SYN.jsonl.gz": digest}}
            for name in ("run-a", "run-b"):
                (root / name / "ledger-hashes.json").write_text(json.dumps(final["ledgerHashes"]))
            self.assertEqual(len(audit.verify_ledger_hashes(root, filenames, final, final)), 2)
            (root / "run-b/SYN.jsonl.gz").write_bytes(b"corrupt bytes")
            with self.assertRaisesRegex(ValueError, "LEDGER_BYTES_CHANGED"):
                audit.verify_ledger_hashes(root, filenames, final, final)
            (root / "run-b/SYN.jsonl.gz").write_bytes(b"frozen bytes")
            (root / "run-b/EXTRA.jsonl.gz").write_bytes(b"unregistered")
            with self.assertRaisesRegex(ValueError, "RUN_FILE_ALLOWLIST"):
                audit.verify_ledger_hashes(root, filenames, final, final)

    def test_json_nonfinite_and_typed_counter_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "bad.gz"
            with gzip.open(path, "wt") as stream:
                stream.write('{"value":NaN}\n')
            with self.assertRaisesRegex(ValueError, "NONFINITE_JSON"):
                list(audit.read_rows(path))
        row, entry, _, _, _ = fixture(); row["missingOrdinaryReferences"] = True
        with self.assertRaisesRegex(ValueError, "MISSING_REFERENCE_COUNT_TYPE"):
            audit.validate_population([row], row["candidateId"], {"IMMEDIATE::" + entry["entryId"]: entry},
                                      {entry["session"]: 1})


if __name__ == "__main__":
    unittest.main()
