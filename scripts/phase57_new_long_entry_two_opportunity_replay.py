#!/usr/bin/env python3
"""Deterministic Development replay for the frozen two-opportunity NEW LONG Entry kernel.

Historical Development / outcome-exposed only. Decisions are produced by the pure
kernel from causal prefix data. Evaluator outcomes are stored separately and never
fed back into the state machine. No model, provider, 1m, EXIT, Capital, Portfolio,
execution, broker, or trading imports.
"""
from __future__ import annotations

import argparse
import collections
import gzip
import hashlib
import json
import statistics
from pathlib import Path

from scripts import phase57_entry_location_study as loc
from scripts.phase57_new_long_entry_two_opportunity import (
    Anchor,
    CONTRACT_STATUS,
    emit_initial_opportunity,
    observe_first_completed_bar,
    state_record,
)

SOURCE_STUDY_HEAD = "a0a263ddc6abd83c9dca0b9f4bc2c86b9753b2bb"
CONTRACT_PATH = "docs/evidence/phase57-new-long-entry-two-opportunity-contract-2026-09-18.md"
STATUS = "NEW_LONG_ENTRY_TWO_OPPORTUNITY_KERNEL_PARITY_PASS"
SAFETY = {k: False for k in (
    "executionAllowed", "brokerWriteAllowed", "excelOrderWriteAllowed",
    "rssOrderFunctionAllowed", "liveTradingAllowed", "paperTradingAllowed",
    "automaticPromotionAllowed", "productionUpdateAllowed", "transmitted",
)}


def _json_bytes(obj):
    return (json.dumps(obj, ensure_ascii=False, sort_keys=True, allow_nan=False,
                       separators=(",", ":")) + "\n").encode()


def _write_json(path: Path, obj):
    path.write_bytes(_json_bytes(obj))


def _write_ndjson_gz(path: Path, rows):
    raw = b"".join(_json_bytes(row) for row in rows)
    path.write_bytes(gzip.compress(raw, mtime=0))


def _sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha_file(path: Path) -> str:
    return _sha_bytes(path.read_bytes())


def _first_anchors():
    events = loc.read(loc.EVENTS)
    first = {}
    for event in sorted(events, key=lambda r: (r["decisionTimestamp"], r["symbol"])):
        first.setdefault((event["sessionDate"], event["symbol"]), event)
    anchors = sorted(first.values(), key=lambda r: (r["decisionTimestamp"], r["symbol"]))
    ids = sorted(row["selectorEventId"] for row in anchors)
    identity = hashlib.sha256(("\n".join(ids) + "\n").encode()).hexdigest()
    assert len(events) == 3800
    assert len(anchors) == 2743
    assert identity == loc.ANCHOR_SHA
    return anchors, identity


def _complete_window(bars, start, minutes, buy, end):
    if buy is None:
        return None
    boundary = loc.segment_end(start, end)
    if boundary is None or start + minutes > boundary:
        return None
    result = loc.window(bars, start, start + minutes, buy)
    return result if result["status"] == "COMPLETE" else None


def _common60(bars, selection_minute, start, buy, end):
    if buy is None:
        return None
    boundary = loc.segment_end(selection_minute, end)
    if boundary is None or selection_minute + 60 > boundary or start >= selection_minute + 60:
        return None
    result = loc.window(bars, start, selection_minute + 60, buy)
    return result if result["status"] == "COMPLETE" else None


def _capture(rows, level):
    eligible = [row for row in rows
                if row["evaluator"].get("initialCommon60") is not None
                and row["evaluator"].get("secondaryCommon60") is not None]
    winners = [row for row in eligible
               if row["evaluator"]["initialCommon60"]["upside"] >= level]
    hits = sum(row["evaluator"]["secondaryCommon60"]["upside"] >= level for row in winners)
    return {
        "denominator": len(winners),
        "hits": hits,
        "ratio": hits / len(winners) if winners else None,
    }


def _distribution(values):
    return loc.distribution([value for value in values if value is not None])


def _replay_event(event):
    bars = loc.absolute_path(event)
    minute = event["entryMinute"]
    session_end = event["sessionEndMinute"]
    boundary = loc.segment_end(minute, session_end)

    anchor = Anchor(
        anchor_id=event["selectorEventId"],
        symbol=event["symbol"],
        session=event["sessionDate"],
        decision_timestamp=event["decisionTimestamp"],
        decision_price=event["decisionPrice"],
    )
    state, initial_event = emit_initial_opportunity(anchor)

    initial_reference = loc.entry_reference("IMMEDIATE", event, bars)
    initial_price = initial_reference["price"]
    if initial_reference["status"] == "REFERENCE_OPEN":
        initial_event = {
            **initial_event,
            "referenceStatus": "REFERENCE_OPEN",
            "referencePrice": initial_price,
            "referenceTimestamp": bars[minute]["start"] if loc.valid(bars.get(minute)) else None,
        }
    else:
        initial_event = {
            **initial_event,
            "referenceStatus": initial_reference["status"],
            "referencePrice": None,
            "referenceTimestamp": None,
        }

    first_bar = bars.get(minute)
    secondary_boundary_expired = boundary is None or minute + 5 >= boundary
    reference_bar = bars.get(minute + 5) if not secondary_boundary_expired else None
    final_state, secondary_event = observe_first_completed_bar(
        state,
        first_bar,
        boundary_expired=boundary is None,
        reference_bar=reference_bar,
        reference_boundary_expired=secondary_boundary_expired,
    )

    primary = (
        boundary is not None
        and minute + 60 <= boundary
        and loc.window(bars, minute, minute + 60, event["decisionPrice"])["status"] == "COMPLETE"
    )

    first_close_cohort = "UNKNOWN"
    if boundary is not None and loc.valid(first_bar):
        first_close_cohort = (
            "FIRST_CLOSED_DIP" if first_bar["c"] < event["decisionPrice"]
            else "NO_FIRST_CLOSED_DIP"
        )

    evaluator = {
        "primary60": primary,
        "firstCloseCohort": first_close_cohort,
    }
    if primary and initial_price is not None:
        evaluator["initialD30"] = _complete_window(bars, minute, 30, initial_price, session_end)
        evaluator["initialCommon60"] = _common60(
            bars, minute, minute, initial_price, session_end)
        secondary_price = secondary_event.get("referencePrice") if secondary_event else None
        if secondary_price is not None:
            evaluator["secondaryD30"] = _complete_window(
                bars, minute + 5, 30, secondary_price, session_end)
            evaluator["secondaryCommon60"] = _common60(
                bars, minute, minute + 5, secondary_price, session_end)
            evaluator["buyImprovementPct"] = 100 * (1 - secondary_price / initial_price)
        else:
            evaluator["secondaryD30"] = None
            evaluator["secondaryCommon60"] = None
            evaluator["buyImprovementPct"] = None

    return {
        "anchorId": event["selectorEventId"],
        "symbol": event["symbol"],
        "sessionDate": event["sessionDate"],
        "decision": {
            "initialEvent": initial_event,
            "secondaryState": state_record(final_state),
            "secondaryEvent": secondary_event,
        },
        "evaluator": evaluator,
    }


def replay():
    protocol = loc.read(loc.BASE / "protocol.json")
    for path, expected in protocol["sourcePins"].items():
        assert loc.sha(path) == expected, path

    anchors, anchor_identity = _first_anchors()
    paths = loc.read(loc.PATHS)
    path_map = {row["selectorEventId"]: row for row in paths["events"]}
    assert set(path_map) == {row["selectorEventId"] for row in loc.read(loc.EVENTS)}

    ledger = [_replay_event(path_map[row["selectorEventId"]]) for row in anchors]
    primary = [row for row in ledger if row["evaluator"]["primary60"]]
    dips = [row for row in primary if row["evaluator"]["firstCloseCohort"] == "FIRST_CLOSED_DIP"]
    no_dips = [row for row in primary if row["evaluator"]["firstCloseCohort"] == "NO_FIRST_CLOSED_DIP"]
    secondary = [row for row in dips if row["decision"]["secondaryEvent"] is not None]
    paired = [row for row in secondary
              if row["evaluator"].get("initialD30") is not None
              and row["evaluator"].get("secondaryD30") is not None
              and row["evaluator"].get("initialCommon60") is not None
              and row["evaluator"].get("secondaryCommon60") is not None]

    state_counts = collections.Counter(
        row["decision"]["secondaryState"]["state"] for row in ledger)
    primary_state_counts = collections.Counter(
        row["decision"]["secondaryState"]["state"] for row in primary)
    first_close_counts = collections.Counter(
        row["evaluator"]["firstCloseCohort"] for row in ledger)

    summary = {
        "status": STATUS,
        "contractStatus": CONTRACT_STATUS,
        "sourceStudyHead": SOURCE_STUDY_HEAD,
        "contractPath": CONTRACT_PATH,
        "dataKind": "HISTORICAL_DEVELOPMENT_OUTCOME_EXPOSED",
        "newValidation": False,
        "architecturePerformanceConclusionAllowed": False,
        "fullAnchors": len(ledger),
        "anchorIdentitySHA256": anchor_identity,
        "primary60": len(primary),
        "primarySymbols": len({row["symbol"] for row in primary}),
        "primarySessions": len({row["sessionDate"] for row in primary}),
        "primaryFirstClosedDip": len(dips),
        "primaryNoFirstClosedDip": len(no_dips),
        "primarySecondaryResolved": len(secondary),
        "primaryPaired": len(paired),
        "fullStateCounts": dict(sorted(state_counts.items())),
        "primaryStateCounts": dict(sorted(primary_state_counts.items())),
        "fullFirstCloseCohortCounts": dict(sorted(first_close_counts.items())),
        "initialReferenceStates": dict(sorted(collections.Counter(
            row["decision"]["initialEvent"]["referenceStatus"] for row in ledger).items())),
        "dipRepriceParity": {
            "buyImprovementPct": _distribution(
                row["evaluator"].get("buyImprovementPct") for row in paired),
            "initialD30Downside": _distribution(
                row["evaluator"]["initialD30"]["downside"] for row in paired),
            "secondaryD30Downside": _distribution(
                row["evaluator"]["secondaryD30"]["downside"] for row in paired),
            "initialCommon60Upside": _distribution(
                row["evaluator"]["initialCommon60"]["upside"] for row in paired),
            "secondaryCommon60Upside": _distribution(
                row["evaluator"]["secondaryCommon60"]["upside"] for row in paired),
            "capture3": _capture(paired, 3),
            "capture5": _capture(paired, 5),
        },
        "decisionInputs": {
            "t0": ["selector identity", "decision timestamp", "decision price"],
            "secondary": ["first completed 5m close", "next regular 5m open reference", "boundary/missing status"],
            "futureHighLowUsed": False,
            "outcomeUsed": False,
            "quantityOwnedByEntry": False,
        },
        "modelFits": 0,
        "modelPredictions": 0,
        "freshAccess": 0,
        "oosAccess": 0,
        "providerRequests": 0,
        "minuteResearchRuns": 0,
        "exitEvaluations": 0,
        "capitalEvaluations": 0,
        "portfolioEvaluations": 0,
        "mainMerge": False,
        "safety": SAFETY,
    }
    return ledger, summary


def write_artifacts(output_dir: Path):
    output_dir.mkdir(parents=True, exist_ok=True)
    ledger, summary = replay()
    ledger_path = output_dir / "ledger.ndjson.gz"
    summary_path = output_dir / "summary.json"
    _write_ndjson_gz(ledger_path, ledger)
    _write_json(summary_path, summary)
    manifest = {
        "status": STATUS,
        "files": {
            "ledger.ndjson.gz": _sha_file(ledger_path),
            "summary.json": _sha_file(summary_path),
        },
        "fullAnchors": summary["fullAnchors"],
        "anchorIdentitySHA256": summary["anchorIdentitySHA256"],
    }
    _write_json(output_dir / "manifest.json", manifest)
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    if args.output_dir:
        result = write_artifacts(args.output_dir)
    else:
        _, result = replay()
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
