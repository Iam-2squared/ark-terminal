"""Build the blind prefix-only REBOUND semantic review packet for the nine-State audit.

This is review infrastructure, not a performance experiment. It opens only the
frozen State-v3 checkpoint output plus the historical raw-price substrate needed
to reconstruct the causal prefix. It never opens Entry fills, Oracle Low/High,
outcomes, MFE/MAE, Capture, or future bars after the T0 as-of timestamp.

The public review packet hides Opportunity identity and the frozen classifier
label. A separate sealed mapping artifact is emitted for later joining *after*
review decisions are fixed.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import html
import json
import math
from pathlib import Path

TARGET_STATE = "REBOUND"
COMPARATOR_STATE = "RISE"
SEED = "phase57-rebound-prefix-review-v1"
TARGET_N = 24
COMPARATOR_N = 12
PATTERNS = (
    "RISE_STOP", "RISE", "SHARP_RISE", "PULLBACK", "RANGE",
    "REBOUND", "SHARP_DROP", "DROP", "DROP_STOP",
)
FORBIDDEN_REVIEW_KEYS = {
    "opportunity", "baselineState", "future", "outcome", "oracle", "entry",
    "fill", "capture", "mfe", "mae", "laterHigh", "orderedLow",
}


def read_json(path: Path):
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as fh:
        return json.load(fh)


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True,
                               indent=2, allow_nan=False) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def stable_rank(oid: str, salt: str = "") -> str:
    return hashlib.sha256(f"{SEED}|{salt}|{oid}".encode()).hexdigest()


def finite(value) -> bool:
    return isinstance(value, (int, float)) and math.isfinite(float(value))


def ratio(row):
    prior = row.get("priorReturn")
    recent = row.get("recentReturn")
    if not finite(prior) or not finite(recent) or abs(float(prior)) == 0:
        return None
    return abs(float(recent)) / abs(float(prior))


def t0_rows(checkpoints):
    rows = [row for row in checkpoints if row.get("delay") == 0]
    ids = [row["opportunity"] for row in rows]
    assert len(ids) == len(set(ids)) == 2155
    return rows


def add_unique(out, pool, count, key):
    existing = {row["opportunity"] for row in out}
    for row in sorted(pool, key=key):
        if row["opportunity"] in existing:
            continue
        out.append(row)
        existing.add(row["opportunity"])
        if len(out) >= count:
            break


def select_target(rows):
    target = [row for row in rows if row.get("state") == TARGET_STATE]
    assert len(target) == 192
    out = []
    # Contract-boundary cases: partial rebound closest to the full-reversal equality.
    boundary = [row for row in target if ratio(row) is not None and ratio(row) < 1]
    add_unique(out, boundary, 8, lambda r: (1 - ratio(r), stable_rank(r["opportunity"], "tb")))
    # Data-quality/confidence stress cases, outcome-blind.
    stress = [row for row in target
              if row.get("dataQuality") != "OK" or row.get("confidence") == "LOW"]
    add_unique(out, stress, 14, lambda r: stable_rank(r["opportunity"], "tq"))
    # Time-boundary stress from T0 as-of only.
    boundaries = (540, 690, 750, 930)
    add_unique(out, target, 18, lambda r: (
        min(abs(int(r["asOf"]) - b) for b in boundaries),
        stable_rank(r["opportunity"], "tt"),
    ))
    # Fixed-seed general coverage to the declared target sample size.
    add_unique(out, target, TARGET_N, lambda r: stable_rank(r["opportunity"], "tr"))
    assert len(out) == TARGET_N
    return out


def select_comparators(rows):
    # The closest semantic negative is a down-context + up-recent full recovery,
    # which the fixed contract calls RISE rather than REBOUND.
    pool = [row for row in rows
            if row.get("state") == COMPARATOR_STATE
            and row.get("priorDir") == -1 and row.get("recentDir") == 1
            and ratio(row) is not None and ratio(row) >= 1]
    assert pool, "NO_FULL_RECOVERY_RISE_COMPARATORS"
    out = []
    add_unique(out, pool, 6, lambda r: (ratio(r) - 1, stable_rank(r["opportunity"], "cb")))
    stress = [row for row in pool
              if row.get("dataQuality") != "OK" or row.get("confidence") == "LOW"]
    add_unique(out, stress, min(9, len(pool)), lambda r: stable_rank(r["opportunity"], "cq"))
    add_unique(out, pool, min(COMPARATOR_N, len(pool)),
               lambda r: stable_rank(r["opportunity"], "cr"))
    assert len(out) == min(COMPARATOR_N, len(pool))
    return out, len(pool)


def close_points(rows):
    out = []
    for row in rows:
        minute = int(row[0])
        close = row[4]
        if finite(close) and float(close) > 0:
            out.append((minute + 1, float(close)))
    return out


def review_series(raw, as_of):
    previous = close_points(raw.get("previous", []))
    today_rows = [row for row in raw.get("today", []) if int(row[0]) < as_of]
    today = []
    if today_rows and int(today_rows[0][0]) == 540 and finite(today_rows[0][1]):
        today.append((540, float(today_rows[0][1])))
    today.extend(close_points(today_rows))
    assert not today or max(t for t, _ in today) <= as_of
    return previous, today


def polyline(points, x0, y0, width, height):
    if not points:
        return "", None, None
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    xmin, xmax = min(xs), max(xs)
    ymin, ymax = min(ys), max(ys)
    if xmax == xmin:
        xmax += 1
    if ymax == ymin:
        pad = max(abs(ymin) * 0.001, 1e-6)
        ymin -= pad
        ymax += pad
    coords = []
    for x, y in points:
        px = x0 + (x - xmin) / (xmax - xmin) * width
        py = y0 + height - (y - ymin) / (ymax - ymin) * height
        coords.append(f"{px:.2f},{py:.2f}")
    return " ".join(coords), ymin, ymax


def render_svg(case_id, previous, today, as_of):
    width, height = 960, 540
    panel_h = 180
    prev_poly, prev_min, prev_max = polyline(previous, 70, 90, 820, panel_h)
    today_poly, today_min, today_max = polyline(today, 70, 330, 820, panel_h)
    def bounds_text(lo, hi):
        return "no usable points" if lo is None else f"min={lo:.4f} max={hi:.4f}"
    safe_id = html.escape(case_id)
    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        f'<text x="32" y="34" font-family="sans-serif" font-size="22">Blind prefix case {safe_id}</text>',
        f'<text x="32" y="58" font-family="sans-serif" font-size="14">Future suffix, Opportunity identity and frozen State label are withheld. Today is clipped at asOf={as_of}.</text>',
        '<rect x="60" y="80" width="840" height="200" fill="none" stroke="black"/>',
        '<text x="70" y="105" font-family="sans-serif" font-size="16">Previous session context (observed closes)</text>',
        f'<text x="650" y="105" font-family="sans-serif" font-size="12">{html.escape(bounds_text(prev_min, prev_max))}</text>',
        '<rect x="60" y="320" width="840" height="200" fill="none" stroke="black"/>',
        '<text x="70" y="345" font-family="sans-serif" font-size="16">Current session prefix only (official open if available + closed bars)</text>',
        f'<text x="650" y="345" font-family="sans-serif" font-size="12">{html.escape(bounds_text(today_min, today_max))}</text>',
    ]
    if prev_poly:
        svg.append(f'<polyline points="{prev_poly}" fill="none" stroke="black" stroke-width="2"/>')
    if today_poly:
        svg.append(f'<polyline points="{today_poly}" fill="none" stroke="black" stroke-width="2"/>')
    svg.append('</svg>')
    return "\n".join(svg) + "\n"


def strip_review_case(case_id, row, raw):
    previous, today = review_series(raw, int(row["asOf"]))
    witness = {
        "caseId": case_id,
        "asOfActiveMinute": int(row["asOf"]),
        "dataQuality": row.get("dataQuality"),
        "classifierConfidence": row.get("confidence"),
        "unitBpsLog": float(row["unit"]) * 10000 if finite(row.get("unit")) else None,
        "priorDirectionSign": row.get("priorDir"),
        "recentDirectionSign": row.get("recentDir"),
        "priorReturnBpsLog": float(row["priorReturn"]) * 10000 if finite(row.get("priorReturn")) else None,
        "recentReturnBpsLog": float(row["recentReturn"]) * 10000 if finite(row.get("recentReturn")) else None,
        "recentToPriorAbsRatio": ratio(row),
        "recentCoverage": row.get("recentCoverage"),
        "recentTransitions": row.get("recentTransitions"),
        "earlierTransitions": row.get("earlierTransitions"),
        "reasonCodesWithoutDecisionLabel": [
            x for x in row.get("reasonCodes", [])
            if x not in {
                "OPPOSING_DIRECTION_PARTIAL", "OPPOSING_DIRECTION_FULL",
                "ELIGIBLE_SHOCK", "ORDINARY_DIRECTION",
                "OBSERVED_PLATEAU_AT_PREFIX_HIGH", "OBSERVED_PLATEAU_AT_PREFIX_LOW",
                "OBSERVED_FLAT_NOT_ELIGIBLE_STOP", "NO_RECENT_PAIR_CARRY_PRIOR_OR_RANGE",
                "FLAT_BUT_SPARSE_OR_STALE_CARRY_PRIOR",
            }
        ],
        "previousPointCount": len(previous),
        "todayPrefixPointCount": len(today),
    }
    assert not (FORBIDDEN_REVIEW_KEYS & set(witness))
    return witness, previous, today


def packet_hashes(root: Path):
    return {
        str(path.relative_to(root)): sha256_file(path)
        for path in sorted(root.rglob("*")) if path.is_file()
    }


def run(args):
    checkpoints_path = Path(args.state_checkpoints)
    raw_paths_path = Path(args.raw_paths)
    output = Path(args.output)
    if output.exists():
        raise FileExistsError(output)
    packet = output / "packet"
    sealed = output / "sealed"
    charts = packet / "charts"
    charts.mkdir(parents=True)
    sealed.mkdir(parents=True)

    checkpoints = read_json(checkpoints_path)
    rows = t0_rows(checkpoints)
    raw_paths = read_json(raw_paths_path)
    by_oid = {row["opportunity"]: row for row in rows}
    assert set(by_oid).issubset(raw_paths)

    targets = select_target(rows)
    comparators, comparator_pool_n = select_comparators(rows)
    selected = targets + comparators
    # Mix target/comparator cases under neutral IDs without leaking source class.
    selected = sorted(selected, key=lambda r: stable_rank(r["opportunity"], "mix"))

    public_cases = []
    sealed_map = []
    for index, row in enumerate(selected, 1):
        case_id = f"RBV1-{index:03d}"
        witness, previous, today = strip_review_case(case_id, row, raw_paths[row["opportunity"]])
        public_cases.append(witness)
        (charts / f"{case_id}.svg").write_text(
            render_svg(case_id, previous, today, int(row["asOf"])), encoding="utf-8"
        )
        sealed_map.append({
            "caseId": case_id,
            "opportunity": row["opportunity"],
            "baselineState": row["state"],
            "isTargetRebound": row["state"] == TARGET_STATE,
            "session": row.get("session"),
            "asOf": row.get("asOf"),
            "ratio": ratio(row),
            "dataQuality": row.get("dataQuality"),
            "confidence": row.get("confidence"),
        })

    write_json(packet / "cases.json", public_cases)
    with (packet / "review-template.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["caseId", "chartInspected", "semanticState", "contractAmbiguous", "notes"])
        for row in public_cases:
            writer.writerow([row["caseId"], "", "", "", ""])

    readme = f"""# REBOUND prefix-only blind review packet v1

This packet contains {len(public_cases)} cases: {TARGET_N} frozen-T0 REBOUND cases and {len(comparators)} masked full-recovery RISE comparison cases. Their identities and labels are in a separate sealed artifact and MUST NOT be opened before the review CSV is completed and fixed.

Review each SVG using only the visible previous-session context and current-session prefix through T0, plus the prefix-only numeric witness in `cases.json`. Future suffix, outcome, fill, Entry quality, Oracle Low/High, MFE/MAE and Capture are absent.

For every case set `chartInspected=YES` only after actually viewing the SVG. Set `semanticState` to exactly one of: {', '.join(PATTERNS)}. If the fixed contract itself is genuinely insufficient to decide from the packet, set `contractAmbiguous=YES` and explain why; do not invent a new threshold.

Sampling is an outcome-blind semantic audit, not a population accuracy estimator: 24 REBOUND cases combine fixed boundary/quality/time stress coverage with fixed-seed general coverage; comparators are fixed-contract full-recovery RISE cases nearest the REBOUND/RISE equality plus quality/random coverage. No future result was used to select a case.
"""
    (packet / "README.md").write_text(readme, encoding="utf-8")
    write_json(sealed / "sealed-map.json", sealed_map)

    manifest = {
        "artifactKind": "phase57_rebound_prefix_blind_review_packet_v1",
        "seed": SEED,
        "targetState": TARGET_STATE,
        "targetPopulation": sum(r.get("state") == TARGET_STATE for r in rows),
        "targetReviewCases": len(targets),
        "comparatorDefinition": "T0 RISE with priorDir=-1 recentDir=+1 and abs(recentReturn)>=abs(priorReturn)",
        "comparatorPool": comparator_pool_n,
        "comparatorReviewCases": len(comparators),
        "totalReviewCases": len(public_cases),
        "stateCheckpointSHA256": sha256_file(checkpoints_path),
        "rawPathsSHA256": sha256_file(raw_paths_path),
        "futureOrOutcomeSourcesOpened": 0,
        "entryOrFillSourcesOpened": 0,
        "providerRequests": 0,
        "protectedDataOpened": 0,
        "reviewPacketContainsOpportunityIdentity": False,
        "reviewPacketContainsBaselineState": False,
        "sealedMapSeparate": True,
        "packetMemberSHA256": packet_hashes(packet),
        "patterns": list(PATTERNS),
        "status": "PACKET_READY_BLIND_REVIEW_NOT_YET_COMPLETED",
    }
    write_json(output / "manifest.json", manifest)
    return manifest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--state-checkpoints", required=True)
    parser.add_argument("--raw-paths", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    manifest = run(args)
    print(json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
