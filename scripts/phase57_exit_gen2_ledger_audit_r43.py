"""R43 read-only structural/semantic audit of frozen R41 policy ledgers.

This verifies existing output. It never fits, replays a policy sequence, scores
candidates, ranks candidates, or reports performance aggregates. Evaluator
formulas are recomputed only to validate each already chosen execution record.
"""
from __future__ import annotations

import argparse
from collections import Counter
import gzip
import json
import math
from pathlib import Path

import numpy as np

from scripts import phase57_exit_finite_r36 as r36
from scripts import phase57_exit_gen2_runtime_r41 as runtime


FIELDS = frozenset((
    "activeMinutesHeld", "candidateId", "decisionNow", "earlyExitOpportunityCostPp", "entryArm",
    "entryId", "entryMinute", "entryPrice", "exitKind", "exitMinute", "exitPrice", "exitStatus",
    "fold", "metrics", "missingOrdinaryReferences", "netReturnPctBySellCost",
    "nonselectableDiagnostic", "opportunity", "session", "wallMinutesHeld",
))
NEUTRAL = "HOLD_TO_TERMINAL_DIAGNOSTIC"
require = r36.require


def equal(actual, expected, reason: str) -> None:
    """Typed recursive comparison; finite rounding tolerance only for floats."""
    if isinstance(expected, dict):
        require(isinstance(actual, dict) and set(actual) == set(expected), reason + ":KEYS")
        for key in expected:
            equal(actual[key], expected[key], reason + "/" + str(key))
    elif isinstance(expected, bool) or expected is None or isinstance(expected, str):
        require(type(actual) is type(expected) and actual == expected, reason)
    elif isinstance(expected, int):
        require(type(actual) is int and actual == expected, reason)
    elif isinstance(expected, float):
        require(type(actual) in (int, float) and math.isfinite(actual) and math.isfinite(expected)
                and math.isclose(actual, expected, abs_tol=1e-10, rel_tol=1e-12), reason)
    else:
        require(actual == expected, reason)


def read_rows(path: Path):
    def invalid_constant(value):
        raise ValueError("NONFINITE_JSON_CONSTANT:" + value)
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        for line in stream:
            yield json.loads(line, parse_constant=invalid_constant)


def verify_ledger_hashes(gen2_root: Path, filenames: set[str], final: dict, replay: dict) -> dict:
    require(set(final["ledgerHashes"]) == set(replay["ledgerHashes"]) == filenames, "LEDGER_RECEIPT_ALLOWLIST")
    require(final["ledgerHashes"] == replay["ledgerHashes"], "LEDGER_RECEIPT_HASH_DISAGREEMENT")
    hashes = {}
    for run_name in ("run-a", "run-b"):
        run_dir = gen2_root / run_name
        require({path.name for path in run_dir.iterdir()} == filenames | {"ledger-hashes.json"}, "RUN_FILE_ALLOWLIST")
        declared = r36.read_json(run_dir / "ledger-hashes.json")
        require(declared == final["ledgerHashes"], "RUN_HASH_MANIFEST_DISAGREEMENT")
        for name in sorted(filenames):
            digest = r36.sha(run_dir / name)
            require(digest == declared[name], "LEDGER_BYTES_CHANGED:" + run_name + "/" + name)
            hashes[run_name + "/" + name] = digest
    require(all(hashes["run-a/" + name] == hashes["run-b/" + name] for name in filenames), "AB_LEDGER_BYTES")
    return hashes


def validate_population(rows: list[dict], candidate_id: str, expected: dict,
                        fold_by_day: dict[str, int]) -> set[tuple]:
    require(len(rows) == len(expected), "LEDGER_ROW_COUNT")
    seen, triggers = set(), set()
    ordered_keys = []
    for row in rows:
        require(set(row) == FIELDS, "LEDGER_FIELDS")
        equal(row["candidateId"], candidate_id, "CANDIDATE_ID")
        equal(row["nonselectableDiagnostic"], candidate_id == NEUTRAL, "DIAGNOSTIC_FLAG")
        key = row["entryArm"] + "::" + row["entryId"]
        require(key not in seen, "DUPLICATE_ENTRY_ID")
        require(key in expected, "UNEXPECTED_ENTRY_ID")
        seen.add(key); ordered_keys.append(key)
        entry = expected[key]
        for field, source in (("entryArm", "entryArm"), ("entryId", "entryId"),
                              ("session", "session"), ("opportunity", "opportunity"),
                              ("entryMinute", "entryMinute"), ("entryPrice", "price")):
            # Frozen Entry fields are byte-preserved numeric values, not rounded replacements.
            require(type(row[field]) is type(entry[source]) and row[field] == entry[source],
                    "FROZEN_ENTRY_FIELD:" + field)
        equal(row["fold"], fold_by_day[entry["session"]], "FOLD_LINEAGE")
        require(type(row["decisionNow"]) is int and row["decisionNow"] in
                r36.execution.decision_endpoints(entry["session"], entry["entryMinute"]),
                "INVALID_DECISION_ENDPOINT")
        require(type(row["missingOrdinaryReferences"]) is int and
                row["missingOrdinaryReferences"] >= 0, "MISSING_REFERENCE_COUNT_TYPE")
        triggers.add((row["entryArm"], row["entryId"], row["decisionNow"]))
    require(seen == set(expected), "MISSING_FROZEN_ENTRY_ID")
    require(ordered_keys == sorted(expected), "LEDGER_ENTRY_ORDER")
    return triggers


def validate_semantics(row: dict, entry: dict, path: list, position: dict,
                       *, candidate: dict | None, fresh: bool, scores: list,
                       geometry, post_high) -> None:
    now = row["decisionNow"]
    if row["exitKind"] == "MODEL_EXIT":
        require(candidate is not None and now < 925 and fresh is True, "MODEL_EXIT_FRESHNESS_OR_TIME")
        # Current intent compatibility only. No sequential persistence/replay reconstruction.
        action = runtime.intent(scores, fresh, candidate["persistenceFreshCheckpoints"] - 1,
                                candidate, now)
        require(action["action"] == "EXIT_INTENT", "CURRENT_SCORES_DO_NOT_AUTHORIZE_EXIT")
        reference = r36.execution.ordinary_execution_reference(entry["session"], now, path)
        require(reference["status"] == "RESOLVED_NEXT_SCHEDULED_OPEN", "MODEL_EXIT_REFERENCE_MISSING")
        equal(row["exitStatus"], "RESOLVED", "MODEL_EXIT_STATUS")
        equal(row["exitMinute"], int(reference["referenceStart"]), "EXACT_ORDINARY_TIME")
        equal(row["exitPrice"], float(reference["price"]), "EXACT_ORDINARY_PRICE")
    else:
        require(now == 925, "TERMINAL_DECISION_NOT_925")
        reference = r36.execution.terminal_execution_reference(path)
        if reference["status"] == "RESOLVED_TERMINAL_AUCTION":
            equal(row["exitKind"], "FORCED_TERMINAL", "TERMINAL_KIND")
            equal(row["exitStatus"], "RESOLVED", "TERMINAL_STATUS")
            equal(row["exitMinute"], 930, "TERMINAL_MINUTE")
            equal(row["exitPrice"], float(reference["price"]), "TERMINAL_PRICE")
        else:
            equal(row["exitKind"], None, "UNRESOLVED_KIND")
            equal(row["exitStatus"], "UNRESOLVED_TERMINAL_EXIT", "UNRESOLVED_STATUS")
            equal(row["exitMinute"], None, "CENSORED_EXIT_TIME")
            equal(row["exitPrice"], None, "CENSORED_EXIT_PRICE")
        require(all(math.isnan(float(value)) for value in scores), "TERMINAL_SCORES_NOT_BYPASSED")
    if candidate is None:
        require(now == 925 and row["missingOrdinaryReferences"] == 0, "NEUTRAL_NOT_TERMINAL_ONLY")
    exit_price, exit_minute = row["exitPrice"], row["exitMinute"]
    equal(row["netReturnPctBySellCost"], {
        f"{cost:.2f}": None if exit_price is None else 100 * (exit_price / entry["price"] - 1) - cost
        for cost in r36.COSTS}, "FIXED_COST_FORMULA")
    equal(row["activeMinutesHeld"], None if exit_minute is None else
          r36.execution.active_minutes(entry["session"], entry["entryMinute"], exit_minute), "ACTIVE_HOLD")
    equal(row["wallMinutesHeld"], None if exit_minute is None else exit_minute - entry["entryMinute"], "WALL_HOLD")
    peak, peak_at = position.get("observedRunningHigh"), position.get("peakConfirmedAt")
    if exit_price is None or not r36.finite(peak) or not r36.finite(peak_at):
        peak = peak_at = None
    metrics = r36.evaluate_capture(
        entry_price=float(entry["price"]), entry_minute=int(entry["entryMinute"]),
        exit_price=exit_price, exit_minute=exit_minute, cost_pp=0.05,
        geometry=geometry, post_entry_high=post_high, owned_peak=peak,
        owned_peak_confirmed_at=int(peak_at) if peak_at is not None else None,
        owned_path_complete=bool(position.get("fullOwnedPrefix") == 1),
    )
    equal(row["metrics"], metrics, "EVALUATOR_FORMULA_OR_OWNERSHIP_NULL")
    later_highs = [] if exit_minute is None else [float(r[2]) for r in path if len(r) == 7
        and r36.finite(r[2]) and ((int(r[0]) if int(r[0]) == 930 else int(r[0]) + 1) > exit_minute)]
    early = (None if exit_minute is None else
             100 * max(0.0, (max(later_highs, default=exit_price) - exit_price) / entry["price"]))
    equal(row["earlyExitOpportunityCostPp"], early, "POST_EXIT_HIGH_KNOWN_AT_FORMULA")


def audit_ledgers(gen2_root: Path, core_root: Path, protocol: dict) -> dict:
    require(protocol == runtime.load_protocol(), "FROZEN_PROTOCOL_CONTENT")
    require(r36.sha(gen2_root / "protocol.json") == runtime.PROTOCOL_SHA256, "ARTIFACT_PROTOCOL_HASH")
    final = r36.read_json(gen2_root / "receipt.json")
    replay = r36.read_json(gen2_root / "replay-receipt.json")
    data_receipt = r36.read_json(gen2_root / "data/data-receipt.json")
    candidates = {candidate["candidateId"]: candidate for candidate in protocol["candidates"]}
    require(len(candidates) == 16, "EXACTLY_16_CANDIDATES")
    filenames = {name + ".jsonl.gz" for name in candidates} | {NEUTRAL + ".jsonl.gz"}
    hashes = verify_ledger_hashes(gen2_root, filenames, final, replay)
    core_a, _ = r36._verify_r35(core_root)
    require(core_a["projectionSha256"] == protocol["features"]["r35ProjectionSha256"], "R35_PINNED_PROJECTION")
    for name in ("columns.json", "entry-envelopes.json.gz"):
        require(r36.sha(core_root / "core-a" / name) == core_a["outputHashes"][name], "R35_SOURCE_BYTES:" + name)
    columns = r36.read_json(core_root / "core-a/columns.json")
    require(data_receipt["numericColumns"] == columns["numeric"] + protocol["features"]["calendarFields"], "NUMERIC_COLUMN_LINEAGE")
    envelopes = r36.read_json(core_root / "core-a/entry-envelopes.json.gz")
    require(set(envelopes) == set(protocol["entryArms"]), "ENVELOPE_ARMS")
    fold_by_day = {day: fold["fold"] for fold in protocol["split"]["folds"] for day in fold["score"]}
    require(len(fold_by_day) == sum(len(f["score"]) for f in protocol["split"]["folds"]) == 34, "OOF_SESSION_COUNT")
    expected, all_oids, score_oids = {}, set(), set()
    for arm in protocol["entryArms"]:
        require(len(envelopes[arm]) == 2155, "FULL_ARM_POPULATION")
        arm_all = {row["opportunity"] for row in envelopes[arm]}
        arm_score = {row["opportunity"] for row in envelopes[arm] if row["session"] in fold_by_day}
        require(len(arm_all) == 2155 and len(arm_score) == 1267, "OPPORTUNITY_POPULATION")
        require(not all_oids or all_oids == arm_all, "ARM_POPULATION_MISMATCH")
        require(not score_oids or score_oids == arm_score, "ARM_SCORE_POPULATION_MISMATCH")
        all_oids, score_oids = arm_all, arm_score
        for row in envelopes[arm]:
            if row["session"] in fold_by_day and row["entryId"] is not None:
                key = arm + "::" + row["entryId"]
                require(key not in expected, "DUPLICATE_FROZEN_ENTRY_ID")
                expected[key] = {**row, "entryArm": arm}
    expected_counts = {"IMMEDIATE": 1150, "ALL_MATERIAL_R1_TEMPORAL_NESTED_OOF": 1107}
    require(dict(Counter(row["entryArm"] for row in expected.values())) == expected_counts, "OOF_FILLED_POPULATION")
    ledgers, triggers = {}, set()
    for name in sorted(filenames):
        rows = list(read_rows(gen2_root / "run-a" / name))
        triggers.update(validate_population(rows, name.removesuffix(".jsonl.gz"), expected, fold_by_day))
        ledgers[name] = rows
    identity_path = gen2_root / "data/source-row-identity.jsonl.gz"
    require(r36.sha(identity_path) == data_receipt["outputHashes"][identity_path.name], "ROW_IDENTITY_BYTES")
    positions = {i: name.removeprefix("position.") for i, name in enumerate(columns["numeric"])
                 if name.startswith("position.")}
    checkpoint_info, total_rows = {}, 0
    identity_rows = iter(read_rows(identity_path))
    arm_counts = Counter()
    for session in r36.r25.development_sessions():
        relative = "checkpoints/" + session + ".jsonl.gz"
        source_path = core_root / "core-a" / relative
        require(r36.sha(source_path) == core_a["outputHashes"][relative], "R35_CHECKPOINT_BYTES:" + session)
        core_rows = sorted(read_rows(source_path), key=lambda row: (
            protocol["entryArms"].index(row["identity"][0]), row["identity"][1], row["identity"][2]))
        for row in core_rows:
            arm, eid, now = row["identity"]
            identity = next(identity_rows, None)
            require(identity == {"index": total_rows, "session": session, "arm": arm,
                                 "entryId": eid, "now": now}, "SOURCE_ROW_IDENTITY_LINEAGE")
            require(row["session"] == session, "CORE_SESSION_LINEAGE")
            arm_counts[arm] += 1
            key = (arm, eid, now)
            if key in triggers:
                require(key not in checkpoint_info, "DUPLICATE_TRIGGER_CHECKPOINT")
                pos = {name: None if row["numeric"][i] is None else float(np.float32(row["numeric"][i]))
                       for i, name in positions.items()}
                checkpoint_info[key] = (total_rows, row["fresh"], pos)
            total_rows += 1
    require(next(identity_rows, None) is None and total_rows == 656247, "SOURCE_ROW_IDENTITY_COUNT")
    require(dict(arm_counts) == data_receipt["rowsByArm"], "ROW_IDENTITY_ARM_COUNTS")
    require(set(checkpoint_info) == triggers, "TRIGGER_CHECKPOINT_NOT_FOUND")
    for path, expected_sha in ((r36.RAW_PATHS, r36.RAW_PATHS_SHA256),
                               (r36.OPPORTUNITY_RECORDS, r36.OPPORTUNITY_RECORDS_SHA256)):
        require(r36.sha(path) == expected_sha, "EVALUATOR_SOURCE_HASH:" + path.name)
    raw = {key: value for key, value in r36.read_json(r36.RAW_PATHS).items() if key in all_oids}
    records = {row["opportunity"]: row for row in r36.read_json(r36.OPPORTUNITY_RECORDS)}
    require(set(raw) == set(records) == all_oids, "EVALUATOR_DEVELOPMENT_POPULATION")
    geometries = {key: r36._ordered_geometry(records[key]) for key in all_oids}
    highs = {key: r36._post_entry_high(entry, raw[entry["opportunity"]]["today"]) for key, entry in expected.items()}
    prediction_path = gen2_root / "oof-predictions.npz"
    require(r36.sha(prediction_path) == final["predictionSha256"], "OOF_PREDICTION_BYTES")
    checked_rows = 0
    with np.load(prediction_path, allow_pickle=False) as stored:
        predictions = {key: stored[key] for key in stored.files}
    for name, rows in ledgers.items():
        candidate = candidates.get(name.removesuffix(".jsonl.gz"))
        for row in rows:
            key = row["entryArm"] + "::" + row["entryId"]
            index, fresh, pos = checkpoint_info[(row["entryArm"], row["entryId"], row["decisionNow"])]
            scores = predictions[candidate["predictionSpec"]][index].tolist() if candidate else [float("nan")] * 2
            validate_semantics(row, expected[key], raw[row["opportunity"]]["today"], pos,
                               candidate=candidate, fresh=fresh, scores=scores,
                               geometry=geometries[row["opportunity"]], post_high=highs[key])
            checked_rows += 1
    return {"schemaVersion": "phase57-exit-gen2-ledger-audit-r43-v1", "status": "PASS",
            "inputLedgerHashes": hashes, "ledgerFiles": 34, "byteIdenticalPairs": 17,
            "candidateCount": 16, "neutralDiagnosticCount": 1, "rowsPerLedger": len(expected),
            "filledRowsByArm": expected_counts, "scoreSessions": len(fold_by_day),
            "scoreOpportunityPopulationPerArm": len(score_oids), "developmentOpportunities": len(all_oids),
            "sourceRowIdentitiesVerified": total_rows, "uniqueTriggerCheckpoints": len(checkpoint_info),
            "uniqueRowsSemanticallyVerified": checked_rows, "rowsCoveredIncludingIdenticalB": checked_rows * 2,
            "checks": {key: True for key in ("exactCandidateAndDiagnosticAllowlist", "allActualABFileHashes",
                "frozenEntryIdentityPriceMinute", "foldLineage", "fullSourceRowIdentityLineage",
                "chosenCurrentScoreCompatibility", "exactOrdinaryOrAuctionReference", "censoredWithoutFabrication",
                "fixedCosts", "ownedFloat32ScalarTransport", "ownershipNullSemantics", "evaluatorFormulas")},
            "fullPolicySequenceReplayed": False, "persistenceSequenceReaudited": False,
            "missingIntentCountReconstructed": False, "newModelFits": 0, "newPolicyReplays": 0,
            "performanceAggregatesProduced": 0, "selection": None,
            "providerRequests": 0, "protectedPartitionsOpened": 0, "safety": dict(r36.SAFETY)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--gen2-root", type=Path, required=True)
    parser.add_argument("--core-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    require(not args.out.exists(), "APPEND_ONLY_AUDIT_OUTPUT_EXISTS")
    result = audit_ledgers(args.gen2_root, args.core_root, runtime.load_protocol())
    args.out.mkdir(parents=True, exist_ok=False)
    r36.write_json(args.out / "receipt.json", result)
    print(json.dumps({"status": result["status"], "ledgerFiles": result["ledgerFiles"],
                      "rowsPerLedger": result["rowsPerLedger"], "performanceAggregatesProduced": 0}, sort_keys=True))


if __name__ == "__main__":
    main()
