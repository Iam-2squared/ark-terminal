"""Build masked prefix-only review packets for the remaining five T0 States.

Targets: DROP, PULLBACK, RANGE, SHARP_DROP, DROP_STOP.  RISE_STOP has zero T0
observations and is handled by a checkpoint transition/code census instead of
fabricating target cases.  Sampling uses only frozen State-v3 prefix metadata,
quality/time stress and fixed hashes; no future or Entry evaluator is opened.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path

from scripts import phase57_nine_state_rebound_review_packet_v1 as common

TARGETS = {
    "DROP": {"prefix": "DV1", "n": 24, "comparators": ("PULLBACK",)},
    "PULLBACK": {"prefix": "PV1", "n": 24, "comparators": ("DROP",)},
    "RANGE": {"prefix": "RGV1", "n": 24, "comparators": ("DROP_STOP", "DROP", "RISE")},
    "SHARP_DROP": {"prefix": "SDV1", "n": 24, "comparators": ("DROP",)},
    "DROP_STOP": {"prefix": "DSV1", "n": 5, "comparators": ("RANGE", "DROP")},
}
SEED = "phase57-remaining-states-prefix-review-v1"
BOUNDARIES = (540, 690, 750, 930)


def stable(state, oid, salt=""):
    return hashlib.sha256(f"{SEED}|{state}|{salt}|{oid}".encode()).hexdigest()


def add_unique(out, pool, count, key):
    have = {row["opportunity"] for row in out}
    for row in sorted(pool, key=key):
        if row["opportunity"] in have:
            continue
        out.append(row)
        have.add(row["opportunity"])
        if len(out) >= count:
            break


def target_sample(rows, state, n):
    pool = [r for r in rows if r.get("state") == state]
    assert len(pool) >= n
    out = []
    stress = [r for r in pool if r.get("dataQuality") != "OK" or r.get("confidence") == "LOW"]
    add_unique(out, stress, min(8, n), lambda r: stable(state, r["opportunity"], "quality"))
    add_unique(out, pool, min(14, n), lambda r: (
        min(abs(int(r["asOf"]) - boundary) for boundary in BOUNDARIES),
        stable(state, r["opportunity"], "time"),
    ))
    add_unique(out, pool, n, lambda r: stable(state, r["opportunity"], "general"))
    assert len(out) == n
    return out


def comparator_sample(rows, state, allowed, n=12):
    pool = [r for r in rows if r.get("state") in allowed]
    # For RANGE/DROP_STOP, prioritize prefix-flat neighbors if available.
    flat = [r for r in pool if r.get("recentDir") == 0]
    out = []
    add_unique(out, flat, min(6, n), lambda r: stable(state, r["opportunity"], "flat"))
    stress = [r for r in pool if r.get("dataQuality") != "OK" or r.get("confidence") == "LOW"]
    add_unique(out, stress, min(9, n), lambda r: stable(state, r["opportunity"], "quality-comp"))
    add_unique(out, pool, min(n, len(pool)), lambda r: stable(state, r["opportunity"], "general-comp"))
    assert out
    return out


def build(root, state, config, rows, raw_paths):
    target = target_sample(rows, state, config["n"])
    comp = comparator_sample(rows, state, config["comparators"])
    selected = sorted(target + comp, key=lambda r: stable(state, r["opportunity"], "mix"))
    packet = root / "packet"; sealed = root / "sealed"; charts = packet / "charts"
    charts.mkdir(parents=True); sealed.mkdir(parents=True)
    public = []; mapping = []
    for index, row in enumerate(selected, 1):
        case_id = f"{config['prefix']}-{index:03d}"
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
        f"# {state} prefix-only blind review packet\n\n"
        f"Target={len(target)}, masked comparators={len(comp)} from {', '.join(config['comparators'])}. "
        "Selection is prefix-only/fixed-seed. Identity, baseline label, future suffix, Entry fill, Oracle, MFE/MAE and Capture are withheld. Review charts before sealed scoring.\n",
        encoding="utf-8",
    )
    common.write_json(sealed / "sealed-map.json", mapping)
    manifest = {
        "targetState": state,
        "targetPopulation": sum(r.get("state") == state for r in rows),
        "targetReviewCases": len(target),
        "comparatorStates": list(config["comparators"]),
        "comparatorReviewCases": len(comp),
        "totalReviewCases": len(selected),
        "futureOrOutcomeSourcesOpened": 0,
        "entryOrFillSourcesOpened": 0,
        "providerRequests": 0,
        "protectedDataOpened": 0,
        "packetHashes": common.packet_hashes(packet),
    }
    common.write_json(root / "manifest.json", manifest)
    return manifest


def run(args):
    checkpoints = common.read_json(Path(args.state_checkpoints))
    t0 = common.t0_rows(checkpoints)
    raw_paths = common.read_json(Path(args.raw_paths))
    assert {r["opportunity"] for r in t0}.issubset(raw_paths)
    output = Path(args.output)
    if output.exists(): raise FileExistsError(output)
    output.mkdir(parents=True)

    state_counts = {state: sum(r.get("state") == state for r in t0) for state in common.PATTERNS}
    assert state_counts == {
        "RISE_STOP": 0, "RISE": 111, "SHARP_RISE": 7, "PULLBACK": 354,
        "RANGE": 57, "REBOUND": 192, "SHARP_DROP": 26, "DROP": 1403,
        "DROP_STOP": 5,
    }
    manifests = {}
    for state, config in TARGETS.items():
        manifests[state] = build(output / state.lower().replace('_','-'), state, config, t0, raw_paths)

    # RISE_STOP: zero T0 cohort, so audit actual later checkpoint occurrence only.
    later = [r for r in checkpoints if r.get("delay", 0) > 0 and r.get("state") == "RISE_STOP"]
    rise_stop = {
        "t0Population": 0,
        "laterCheckpointRows": len(later),
        "uniqueOpportunities": len({r["opportunity"] for r in later}),
        "sessions": len({r.get("session") for r in later}),
        "prefixOnly": True,
        "outcomeOpened": 0,
    }
    common.write_json(output / "rise-stop-transition-census.json", rise_stop)
    common.write_json(output / "manifest.json", {
        "artifactKind": "phase57_remaining_states_prefix_blind_review_packets_v1",
        "states": {state: {
            "targetPopulation": m["targetPopulation"],
            "targetReviewCases": m["targetReviewCases"],
            "comparatorReviewCases": m["comparatorReviewCases"],
            "totalReviewCases": m["totalReviewCases"],
        } for state, m in manifests.items()},
        "riseStopTransitionCensus": rise_stop,
        "futureOrOutcomeSourcesOpened": 0,
        "entryOrFillSourcesOpened": 0,
        "providerRequests": 0,
        "protectedDataOpened": 0,
    })
    print(json.dumps({"states": {k:v["totalReviewCases"] for k,v in manifests.items()}, "RISE_STOP": rise_stop}, sort_keys=True))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--state-checkpoints", required=True)
    parser.add_argument("--raw-paths", required=True)
    parser.add_argument("--output", required=True)
    run(parser.parse_args())


if __name__ == "__main__": main()
