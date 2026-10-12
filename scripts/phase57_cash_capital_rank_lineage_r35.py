"""R35 causal Capital rank-lineage audit; no portfolio performance or outcome read.

Projects only Frozen Selector origin rank/score and frozen Entry identity.  The
purpose is to prove that the priority fields used by R34 are known no later than
the Entry they rank.  Future High/Low/MFE/MAE/EXIT/PnL fields are never read.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path

from scripts.phase57_chart_entry import minute

ROOT = Path(__file__).resolve().parents[1]
IMMEDIATE = ROOT / "docs/evidence/phase57-state-conditioned-signal-entry-v1/measurement/baseline-immediate-records.json.gz"
ORIGINS = ROOT / "docs/evidence/phase57-entry-pattern-v2/ci-result/substrate/opportunities.json.gz"

IMMEDIATE_SHA256 = "4522bea9ac94f597affc8518c4cb25354e27f9e64141152cde8b8a4b9e09df9c"
R1_SHA256 = "15ddb5cfc5169024878ee72d9dbecc6e1d9dec24e78afa2dcdf8dea891117fa6"
ORIGINS_SHA256 = "1138960e489c3403e49f502a7ff7ab1fa1e9ef205910d2d018f2bb938df813ea"

ARMS = ("IMMEDIATE", "ALL_MATERIAL_R1_TEMPORAL_NESTED_OOF")
SAFETY = dict.fromkeys((
    "executionAllowed", "brokerWriteAllowed", "excelOrderWriteAllowed",
    "rssOrderFunctionAllowed", "liveTradingAllowed", "paperTradingAllowed",
    "automaticPromotionAllowed", "productionUpdateAllowed", "transmitted"), False)


def require(ok: bool, reason: str) -> None:
    if not ok:
        raise ValueError(reason)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path: Path):
    data = path.read_bytes()
    return json.loads(gzip.decompress(data) if path.suffix == ".gz" else data)


def origin_projection() -> dict[str, dict]:
    require(sha(ORIGINS) == ORIGINS_SHA256, "ORIGIN_SOURCE_SHA")
    projected = {}
    for row in read(ORIGINS):
        oid = row["id"]
        origin = row["origin"]
        rank = origin["newEligibleRank"]
        score = origin["savedV1Score"]
        known = minute(origin["decisionTimestamp"])
        require(type(rank) is int and rank > 0, "INVALID_SELECTOR_RANK:" + oid)
        require(isinstance(score, (int, float)) and not isinstance(score, bool)
                and math.isfinite(score), "INVALID_SELECTOR_SCORE:" + oid)
        require(type(known) is int, "INVALID_SELECTOR_TIME:" + oid)
        require(oid not in projected, "DUPLICATE_SELECTOR_ORIGIN:" + oid)
        projected[oid] = {
            "newEligibleRank": rank,
            "savedV1Score": float(score),
            "rankKnownAtMinute": known,
        }
    return projected


def entry_projection(path: Path, arm: str, expected_sha: str) -> list[dict]:
    require(sha(path) == expected_sha, "ENTRY_SOURCE_SHA:" + arm)
    rows = read(path)
    require(len(rows) == 2155, "ENTRY_POPULATION:" + arm)
    out = []
    seen = set()
    for row in rows:
        oid = row["opportunity"]
        require(oid not in seen, "DUPLICATE_ENTRY_OPPORTUNITY:" + arm)
        seen.add(oid)
        require(row["session"] + "|" + row["symbol"] == oid, "ENTRY_IDENTITY:" + arm)
        entry_id = row["entryId"]
        entry_minute = row["entryMinute"]
        price = row["price"]
        if entry_id is None:
            require(entry_minute is None and price is None, "NO_ENTRY_WITH_FILL:" + arm)
        else:
            require(type(entry_minute) is int, "ENTRY_MINUTE:" + arm)
            require(entry_id == oid + "|" + str(entry_minute), "ENTRY_ID:" + arm)
            require(isinstance(price, (int, float)) and not isinstance(price, bool)
                    and math.isfinite(price) and price > 0, "ENTRY_PRICE:" + arm)
        out.append({
            "opportunity": oid,
            "session": row["session"],
            "symbol": row["symbol"],
            "entryId": entry_id,
            "entryMinute": entry_minute,
            "effectiveEntryPrice": price,
        })
    return out


def audit(r1_records: Path) -> dict:
    origins = origin_projection()
    immediate = entry_projection(IMMEDIATE, ARMS[0], IMMEDIATE_SHA256)
    r1 = entry_projection(r1_records, ARMS[1], R1_SHA256)
    allowed = {r["opportunity"] for r in immediate}
    require({r["opportunity"] for r in r1} == allowed, "ENTRY_ARM_COHORT_MISMATCH")
    require(set(origins) >= allowed, "MISSING_SELECTOR_ORIGINS")

    by_arm = {}
    projected = {}
    for arm, rows in zip(ARMS, (immediate, r1)):
        fills = equal = earlier = after = 0
        arm_rows = []
        for entry in rows:
            origin = origins[entry["opportunity"]]
            row = {**entry, **origin}
            if entry["entryId"] is not None:
                fills += 1
                if origin["rankKnownAtMinute"] == entry["entryMinute"]:
                    equal += 1
                elif origin["rankKnownAtMinute"] < entry["entryMinute"]:
                    earlier += 1
                else:
                    after += 1
            arm_rows.append(row)
        require(after == 0, "SELECTOR_RANK_AFTER_ENTRY:" + arm)
        require(fills == equal + earlier, "CAUSAL_RANK_ACCOUNTING:" + arm)
        by_arm[arm] = {
            "population": len(rows),
            "fills": fills,
            "rankScoreAvailableForAllPopulation": len(arm_rows),
            "rankScoreAvailableForAllFills": fills,
            "rankKnownAtEqualEntry": equal,
            "rankKnownBeforeEntry": earlier,
            "rankKnownAfterEntry": after,
        }
        projected[arm] = arm_rows

    return {
        "schemaVersion": "phase57-cash-capital-rank-lineage-r35",
        "status": "CAUSAL_RANK_LINEAGE_AUDIT_NOT_PORTFOLIO_PERFORMANCE",
        "priority": "newEligibleRank ASC -> savedV1Score DESC -> symbol ASC",
        "byArm": by_arm,
        "projection": projected,
        "sourceSHA256": {
            "immediate": IMMEDIATE_SHA256,
            "r1": R1_SHA256,
            "selectorOrigins": ORIGINS_SHA256,
        },
        "outcomeFieldsRead": 0,
        "portfolioReplays": 0,
        "providerRequests": 0,
        "protectedPartitionsOpened": 0,
        "safety": SAFETY,
    }


def canonical(value) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--r1-records", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.r1_records)
    require(not args.out.exists(), "APPEND_ONLY_OUTPUT_EXISTS")
    args.out.write_bytes(gzip.compress(canonical(result), mtime=0))
    print(json.dumps({k: v for k, v in result.items() if k != "projection"},
                     sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
