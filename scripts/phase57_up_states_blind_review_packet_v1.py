"""Build outcome-blind prefix review packets for RISE and SHARP_RISE.

This is review infrastructure only.  It reuses the already frozen State-v3 T0
checkpoints and the approved raw-price substrate.  No Entry fill, Oracle,
outcome, Capture, MFE/MAE or future suffix is opened.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

from scripts import phase57_nine_state_rebound_review_packet_v1 as common

RISE_SEED = "phase57-rise-prefix-review-v1"
SHARP_SEED = "phase57-sharp-rise-prefix-review-v1"
PATTERNS = common.PATTERNS


def stable(seed, oid, salt=""):
    return hashlib.sha256(f"{seed}|{salt}|{oid}".encode()).hexdigest()


def finite(value):
    return isinstance(value, (int, float)) and math.isfinite(float(value))


def abs_units(row):
    unit = row.get("unit")
    ret = row.get("recentReturn")
    if not finite(unit) or not finite(ret) or float(unit) <= 0:
        return None
    return abs(float(ret)) / float(unit)


def ratio(row):
    return common.ratio(row)


def add_unique(out, pool, target_n, key):
    have = {row["opportunity"] for row in out}
    for row in sorted(pool, key=key):
        if row["opportunity"] in have:
            continue
        out.append(row)
        have.add(row["opportunity"])
        if len(out) >= target_n:
            break


def rise_selection(rows):
    target = [r for r in rows if r.get("state") == "RISE"]
    assert len(target) == 111
    out = []
    full_recovery = [
        r for r in target
        if r.get("priorDir") == -1 and r.get("recentDir") == 1
        and ratio(r) is not None and ratio(r) >= 1
    ]
    add_unique(out, full_recovery, min(8, len(full_recovery)),
               lambda r: (ratio(r) - 1, stable(RISE_SEED, r["opportunity"], "full")))
    ordinary = [
        r for r in target
        if r.get("recentDir") == 1 and "ORDINARY_DIRECTION" in r.get("reasonCodes", [])
    ]
    add_unique(out, ordinary, 14,
               lambda r: (-(abs_units(r) or -1), stable(RISE_SEED, r["opportunity"], "ordinary")))
    sparse = [
        r for r in target
        if "FLAT_BUT_SPARSE_OR_STALE_CARRY_PRIOR" in r.get("reasonCodes", [])
        or "NO_RECENT_PAIR_CARRY_PRIOR_OR_RANGE" in r.get("reasonCodes", [])
    ]
    add_unique(out, sparse, 18, lambda r: stable(RISE_SEED, r["opportunity"], "sparse"))
    stress = [r for r in target if r.get("dataQuality") != "OK" or r.get("confidence") == "LOW"]
    add_unique(out, stress, 21, lambda r: stable(RISE_SEED, r["opportunity"], "quality"))
    add_unique(out, target, 24, lambda r: stable(RISE_SEED, r["opportunity"], "general"))
    assert len(out) == 24

    rebound = [r for r in rows if r.get("state") == "REBOUND" and ratio(r) is not None]
    rebound = sorted(rebound, key=lambda r: (abs(1 - ratio(r)), stable(RISE_SEED, r["opportunity"], "rb")))[:6]
    sharp = [r for r in rows if r.get("state") == "SHARP_RISE"]
    sharp = sorted(sharp, key=lambda r: stable(RISE_SEED, r["opportunity"], "sr"))[:6]
    comparators = rebound + sharp
    assert len(comparators) >= 10
    return out, comparators


def sharp_rise_selection(rows):
    target = [r for r in rows if r.get("state") == "SHARP_RISE"]
    assert len(target) == 7
    target = sorted(target, key=lambda r: stable(SHARP_SEED, r["opportunity"], "all"))
    rise = [r for r in rows if r.get("state") == "RISE" and r.get("recentDir") == 1]
    shock_like = [
        r for r in rise
        if (r.get("recentTransitions") or 0) >= 3
        and abs_units(r) is not None and abs_units(r) >= 3
        and r.get("priorDir") in (0, 1)
    ]
    chosen = []
    add_unique(chosen, shock_like, min(8, len(shock_like)),
               lambda r: (abs((abs_units(r) or 0) - 3), stable(SHARP_SEED, r["opportunity"], "shocklike")))
    add_unique(chosen, rise, 12,
               lambda r: (-(abs_units(r) or -1), stable(SHARP_SEED, r["opportunity"], "rise")))
    assert len(chosen) == 12
    return target, chosen


def build_packet(root: Path, prefix: str, seed: str, target_state: str,
                 targets, comparators, raw_paths):
    packet = root / "packet"
    sealed = root / "sealed"
    charts = packet / "charts"
    charts.mkdir(parents=True)
    sealed.mkdir(parents=True)
    selected = list(targets) + list(comparators)
    selected = sorted(selected, key=lambda r: stable(seed, r["opportunity"], "mix"))
    public, mapping = [], []
    for i, row in enumerate(selected, 1):
        case_id = f"{prefix}-{i:03d}"
        witness, prev, today = common.strip_review_case(case_id, row, raw_paths[row["opportunity"]])
        public.append(witness)
        (charts / f"{case_id}.svg").write_text(
            common.render_svg(case_id, prev, today, int(row["asOf"])), encoding="utf-8"
        )
        mapping.append({
            "caseId": case_id,
            "opportunity": row["opportunity"],
            "baselineState": row["state"],
            "session": row.get("session"),
            "asOf": row.get("asOf"),
        })
    common.write_json(packet / "cases.json", public)
    with (packet / "review-template.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["caseId", "chartInspected", "semanticState", "contractAmbiguous", "notes"])
        for row in public:
            writer.writerow([row["caseId"], "", "", "", ""])
    (packet / "README.md").write_text(
        f"# {target_state} prefix-only semantic review\n\n"
        f"Target cases: {len(targets)}; masked comparison cases: {len(comparators)}. "
        "Identity, frozen label, future suffix, Entry fills, Oracle, MFE/MAE and Capture are withheld. "
        "Review every chart before opening the sealed map. This is a deterministic Development semantic audit, not a population-accuracy estimate.\n",
        encoding="utf-8",
    )
    common.write_json(sealed / "sealed-map.json", mapping)
    manifest = {
        "artifactKind": f"phase57_{target_state.lower()}_prefix_blind_review_packet_v1",
        "seed": seed,
        "targetState": target_state,
        "targetPopulation": sum(1 for r in t0 if r.get("state") == target_state),
        "targetReviewCases": len(targets),
        "comparatorReviewCases": len(comparators),
        "totalReviewCases": len(selected),
        "futureOrOutcomeSourcesOpened": 0,
        "entryOrFillSourcesOpened": 0,
        "providerRequests": 0,
        "protectedDataOpened": 0,
        "publicContainsIdentity": False,
        "publicContainsBaselineState": False,
        "packetHashes": common.packet_hashes(packet),
    }
    common.write_json(root / "manifest.json", manifest)
    return manifest


def run(args):
    global t0
    checkpoints = common.read_json(Path(args.state_checkpoints))
    t0 = common.t0_rows(checkpoints)
    raw_paths = common.read_json(Path(args.raw_paths))
    assert {r["opportunity"] for r in t0}.issubset(raw_paths)
    output = Path(args.output)
    if output.exists():
        raise FileExistsError(output)
    output.mkdir(parents=True)

    rise_targets, rise_comp = rise_selection(t0)
    sharp_targets, sharp_comp = sharp_rise_selection(t0)
    manifests = {
        "RISE": build_packet(output / "rise", "RV1", RISE_SEED, "RISE", rise_targets, rise_comp, raw_paths),
        "SHARP_RISE": build_packet(output / "sharp-rise", "SRV1", SHARP_SEED, "SHARP_RISE", sharp_targets, sharp_comp, raw_paths),
    }
    common.write_json(output / "manifest.json", {
        "artifactKind": "phase57_up_states_prefix_blind_review_packets_v1",
        "states": {k: {
            "targetPopulation": v["targetPopulation"],
            "targetReviewCases": v["targetReviewCases"],
            "comparatorReviewCases": v["comparatorReviewCases"],
            "totalReviewCases": v["totalReviewCases"],
        } for k, v in manifests.items()},
        "futureOrOutcomeSourcesOpened": 0,
        "entryOrFillSourcesOpened": 0,
        "providerRequests": 0,
        "protectedDataOpened": 0,
    })
    print(json.dumps({k: v["totalReviewCases"] for k, v in manifests.items()}, sort_keys=True))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--state-checkpoints", required=True)
    parser.add_argument("--raw-paths", required=True)
    parser.add_argument("--output", required=True)
    run(parser.parse_args())


if __name__ == "__main__":
    main()
