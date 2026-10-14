#!/usr/bin/env python3
"""Offline aggregate-only paired selector comparison. No provider or order calls.

Usage:
 python run_paired_comparison.py --authorization LOCAL_GATE.json \
   --baseline OLD_TOP5.jsonl --candidate NEW_TOP5.jsonl \
   --outcomes FUTURE_CONTINUOUS_5M.jsonl --output PRIVATE_SUMMARY.json

All three input paths MUST reference the same pre-authorized evaluation universe.
"""
from __future__ import annotations

import argparse
import json
import random
from collections import Counter, defaultdict
from pathlib import Path

from selector_core import ContractError, compare_policies
from selector_model import authorize_research

SEED = 20261012
SESSION_BOOTSTRAP_DRAWS = 2000


def load_rows(path: str) -> list[dict]:
    rows = []
    with Path(path).open("r", encoding="utf-8") as f:
        for n, line in enumerate(f, 1):
            if line.strip():
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    raise ContractError(f"INVALID_JSONL:{path}:{n}") from exc
    return rows


def load_future(path: str) -> dict:
    result = {}
    for row in load_rows(path):
        key = (row["session"], row["decisionTime"], row["symbol"])
        if key in result:
            raise ContractError("DUPLICATE_FUTURE_ID")
        result[key] = row["bars"]
    return result


def session_counts(events: list[dict]) -> dict[str, dict]:
    sessions = defaultdict(lambda: {
        "known": 0, "unknown": 0, "bins": Counter(), "downsides": Counter(),
    })
    for row in events:
        a = sessions[row["session"]]
        if row["signedHighPct"] is None:
            a["unknown"] += 1
            continue
        a["known"] += 1
        a["bins"][row["bucket"]] += 1
        for t in (1, 2, 3, 5):
            if row["maePct"] <= -t:
                a["downsides"][str(t)] += 1
    return dict(sessions)


def _pct(count: int, n: int) -> float | None:
    return 100 * count / n if n else None


def _ci(values: list[float]) -> tuple[float | None, float | None]:
    if not values:
        return None, None
    s = sorted(values)
    return s[int(0.025 * (len(s) - 1))], s[int(0.975 * (len(s) - 1))]


def paired_session_ci(old: list[dict], new: list[dict],
                      labels: list[str]) -> dict:
    a = session_counts(old)
    b = session_counts(new)
    if set(a) != set(b):
        raise ContractError("SESSION_MISMATCH")
    days = sorted(a)
    if not days:
        return {label: [None, None] for label in labels}
    rng = random.Random(SEED)
    estimates = {label: [] for label in labels}
    for _ in range(SESSION_BOOTSTRAP_DRAWS):
        batch = rng.choices(days, k=len(days))
        an = sum(a[d]["known"] for d in batch)
        bn = sum(b[d]["known"] for d in batch)
        if not an or not bn:
            continue
        for label in labels:
            ahits = sum(a[d]["bins"][label] for d in batch)
            bhits = sum(b[d]["bins"][label] for d in batch)
            estimates[label].append(100 * (bhits / bn - ahits / an))
    return {label: list(_ci(estimates[label])) for label in labels}


def _bucket_order(label: str) -> float:
    if label == ">=5":
        return float("inf")
    return int(label.split("..")[0])


def build_public_summary(paired: dict) -> dict:
    a, b = paired["events"]["baseline"], paired["events"]["candidate"]
    sa, sb = paired["baseline"], paired["candidate"]
    labels = sorted((set(sa["exclusiveBucketCounts"])
                    | set(sb["exclusiveBucketCounts"])) - {"UNKNOWN"},
                    key=_bucket_order)
    labels = [name for name in labels if name != "UNKNOWN"]
    ci = paired_session_ci(a, b, labels)
    bands = []
    for label in labels:
        ac = sa["exclusiveBucketCounts"].get(label, 0)
        bc = sb["exclusiveBucketCounts"].get(label, 0)
        ap = _pct(ac, sa["knownN"])
        bp = _pct(bc, sb["knownN"])
        bands.append({
            "bucket": label, "baselineCount": ac, "candidateCount": bc,
            "baselineKnownPct": ap, "candidateKnownPct": bp,
            "deltaPctPoints": bp - ap if ap is not None and bp is not None else None,
            "pairedSessionBootstrap95PctPoints": ci[label],
        })
    return {
        "status": "HISTORICAL_ONLY_NOT_LIVE_ECONOMIC_OR_OOS",
        "pairing": "same session, decision time, eligibleUniverseHash, priceBasis",
        "strictHighDefinition": "future-only continuous 5m high; raw signed return",
        "bootstrap": {"unit": "session", "draws": SESSION_BOOTSTRAP_DRAWS,
                      "seed": SEED, "method": "paired session resampling"},
        "decisionN": paired["pairedDecisionN"],
        "baselineN": sa["selectedN"], "candidateN": sb["selectedN"],
        "baselineKnownN": sa["knownN"], "candidateKnownN": sb["knownN"],
        "baselineUnknownN": sa["unknownN"], "candidateUnknownN": sb["unknownN"],
        "bands": bands,
        "cumulativeHigh": {
            t: {"baseline": sa["cumulativeHighCounts"][t],
                "candidate": sb["cumulativeHighCounts"][t]}
            for t in ("1", "2", "3", "4", "5")
        },
        "futureLowDownside": {
            t: {"baseline": sa["downsideCounts"][t],
                "candidate": sb["downsideCounts"][t]}
            for t in ("1", "2", "3", "5")
        },
        "note": "High opportunities cannot be treated as realizable trade PnL; "
                "coverage and missingness remain visible. In-sample is not OOS.",
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--authorization", required=True)
    p.add_argument("--baseline", required=True)
    p.add_argument("--candidate", required=True)
    p.add_argument("--outcomes", required=True)
    p.add_argument("--output", required=True)
    args = p.parse_args()
    authorization = json.loads(Path(args.authorization).read_text(encoding="utf-8"))
    authorize_research(authorization)
    old = load_rows(args.baseline)
    new = load_rows(args.candidate)
    future = load_future(args.outcomes)
    compared = compare_policies(old, new, future)
    output = build_public_summary(compared)
    out = Path(args.output)
    if out.exists():
        raise ContractError("REFUSE_OVERWRITE_RESULT")
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("x", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print("SELECTOR_PAIRED_AGGREGATE_WRITTEN")
    print(f"DECISIONS={output['decisionN']}")
    print(f"BASELINE_KNOWN={output['baselineKnownN']}/{output['baselineN']}")
    print(f"CANDIDATE_KNOWN={output['candidateKnownN']}/{output['candidateN']}")
    print("NO_ORDERS_NO_PROVIDER_NO_GITHUB_UPLOAD")


if __name__ == "__main__":
    main()
