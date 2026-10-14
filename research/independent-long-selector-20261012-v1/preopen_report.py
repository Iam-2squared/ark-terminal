"""Outcome-only diagnostics and a separate Decimal recount, never model selection."""
from __future__ import annotations

import random
from collections import Counter, defaultdict
from decimal import Decimal
from fractions import Fraction
from math import ceil

from preopen_selector import PreopenError, summarize_open_high, stamp

UPS = (1, 2, 3, 4, 5)
DOWNS = (1, 2, 3, 5)


def independent_recount(watchlists, raw_labels, evaluated_rows):
    """Separate arithmetic path: does not call the production label evaluator.

    This is a same-author independent calculation, not a blind external audit.
    """
    emitted = {(r["session"], r["symbol"]): r for r in evaluated_rows}
    counts = Counter()
    known = unknown = exact_zero = 0
    seen = set()
    for watch in watchlists:
        for item in watch["items"]:
            key = item["session"], item["symbol"]
            if key in seen:
                raise PreopenError("RECOUNT_DUPLICATE_SELECTED_IDENTITY")
            seen.add(key)
            label = raw_labels.get(key)
            expected = emitted.get(key)
            if expected is None:
                raise PreopenError("RECOUNT_SELECTED_ROW_MISSING")
            ready = (label is not None and label.get("traded") is not False
                     and label.get("completeSession") is True
                     and label.get("officialFirstTradeOpen") is True
                     and all(label.get(k) is not None for k in ("open", "high", "low", "close")))
            if not ready:
                unknown += 1
                if expected["status"] != "UNKNOWN":
                    raise PreopenError("RECOUNT_UNKNOWN_DISAGREEMENT")
                continue
            vals = []
            for name in ("open", "high", "low", "close"):
                if isinstance(label[name], bool):
                    raise PreopenError("RECOUNT_BOOLEAN_PRICE")
                dec = Decimal(str(label[name]))
                if not dec.is_finite() or dec <= 0:
                    raise PreopenError("RECOUNT_INVALID_PRICE")
                vals.append(dec.as_integer_ratio())
            # Cross multiplication is exact even beyond Decimal context precision.
            prices = [Fraction(n, d) for n, d in vals]
            o, h, l, c = prices
            if not l <= min(o, c) <= max(o, c) <= h:
                raise PreopenError("RECOUNT_INVALID_OHLC")
            up, low, close = (100 * (v - o) / o for v in (h, l, c))
            bucket = ">=5" if up >= 5 else str(up // 1) + "..<" + str(up // 1 + 1)
            if (expected["status"] != "KNOWN" or expected["bucket"] != bucket
                    or expected["exactZero"] != (h == o)
                    or expected["closeNegative"] != (c < o)
                    or any(expected["upHits"][str(t)] != (h*100 >= o*(100+t)) for t in UPS)
                    or any(expected["lowHits"][str(t)] != (l*100 <= o*(100-t)) for t in DOWNS)):
                raise PreopenError("INDEPENDENT_RECOUNT_DISAGREEMENT")
            for field, value in (("lowBucket", low), ("closeBucket", close)):
                signed = "EXACT_ZERO" if value == 0 else str(value // 1) + "..<" + str(value // 1+1)
                if expected[field] != signed:
                    raise PreopenError("INDEPENDENT_SIGNED_BUCKET_DISAGREEMENT")
            known += 1
            exact_zero += h == o
            counts[bucket] += 1
    if set(emitted) != seen:
        raise PreopenError("RECOUNT_EXTRA_EVALUATED_IDENTITY")
    if sum(counts.values()) != known or known + unknown != len(seen):
        raise PreopenError("RECOUNT_CARDINALITY")
    return {"schema": "ARK_PREOPEN_INDEPENDENT_RECOUNT_V1", "status": "PASS",
            "selectedN": len(seen), "knownN": known, "unknownN": unknown,
            "exclusiveBuckets": dict(counts), "exactZeroN": exact_zero,
            "arithmetic": "DECIMAL_INTEGER_RATIOS_AND_CROSS_MULTIPLICATION",
            "independentCodePath": True, "blindIndependentAuthorAudit": False}


def extended_diagnostics(rows):
    daily = defaultdict(list)
    for r in rows:
        daily[r["session"]].append(r)
    day_summaries = {d: summarize_open_high(rs) for d, rs in sorted(daily.items())}
    cross = {f"up>={u}_low<=-{d}": sum(
        r["status"] == "KNOWN" and r["upHits"][str(u)] and r["lowHits"][str(d)]
        for r in rows) for u in UPS for d in DOWNS}
    stability = {}
    for t in UPS:
        rates = [s["highHitLowerBoundPct"][str(t)] for s in day_summaries.values()
                 if s["selectedN"]]
        hits = [s["highHitN"][str(t)] for s in day_summaries.values()]
        stability[str(t)] = {
            "sessions": len(hits), "zeroHitDays": sum(h == 0 for h in hits),
            "zeroHitDayPct": 100*sum(h == 0 for h in hits)/len(hits) if hits else None,
            "meanHitsPerSession": sum(hits)/len(hits) if hits else None,
            "allSelectedRatePctDistribution": sorted(rates)}
    strata={}
    for field in ("marketSegment","sector","sizeCategory","priorLiquidityGroup","priorRegime"):
        groups=defaultdict(list)
        for r in rows:groups[str(r.get(field,"UNKNOWN"))].append(r)
        strata[field]={k:{**summarize_open_high(v),
                          "distinctSessions":len({r["session"] for r in v}),
                          "generalizationCertified":False}
                       for k,v in groups.items()}
    return {"schema": "ARK_PREOPEN_DIAGNOSTICS_V1", "dayResults": day_summaries,
            "predeclaredRankDiagnostics": {
                str(k): summarize_open_high([r for r in rows if r["rank"] <= k])
                for k in (1, 3, 5, 15)},
            "upsideDownsideCrossTabN": cross, "dailyHitStability": stability,
            "highLowOrder": "NOT_INFERRED_FROM_DAILY_OHLC",
            "marketSizeLiquidityRegime": strata,
            "rankKRetuned": False}


def _metric(summary, metric):
    kind, key = metric.split(":", 1)
    if kind == "bucket":
        return summary["buckets"].get(key, 0)
    if kind == "lowbucket":
        return summary["lowBuckets"].get(key, 0)
    if kind == "closebucket":
        return summary["closeBuckets"].get(key, 0)
    if kind == "up":
        return summary["highHitN"][key]
    if kind == "down":
        return summary["lowHitN"][key]
    if kind == "close_down":
        return summary["closeHitN"][key]
    return summary[key]


def paired_day_uncertainty(daily, draws=2000, seed=20261012, block_length=5):
    if len(daily) < 2:
        return {"status": "INSUFFICIENT_DISTINCT_SESSIONS", "sessionN": len(daily)}
    if draws < 40 or type(draws) is not int:
        raise PreopenError("BOOTSTRAP_DRAWS_TOO_SMALL")
    metrics = {f"up:{x}" for x in UPS} | {f"down:{x}" for x in DOWNS}
    metrics |= {f"close_down:{x}" for x in DOWNS}
    metrics |= {"count:closeNegativeN", "count:unknownN", "count:exactZeroN"}
    for d in daily:
        for arm in ("baseline", "candidate"):
            for name, kind in (("buckets", "bucket"), ("lowBuckets", "lowbucket"),
                               ("closeBuckets", "closebucket")):
                metrics |= {kind + ":" + x for x in d[arm][name]}

    def compute(block):
        rng = random.Random(seed)
        samples = {k: [] for k in sorted(metrics)}
        for _ in range(draws):
            if block == 1:
                batch = rng.choices(daily, k=len(daily))
            else:
                batch = []
                for _ in range(ceil(len(daily)/block)):
                    start = rng.randrange(len(daily))
                    batch.extend(daily[(start+j) % len(daily)] for j in range(block))
                batch = batch[:len(daily)]
            a = sum(d["baseline"]["selectedN"] for d in batch)
            b = sum(d["candidate"]["selectedN"] for d in batch)
            if not a or not b:
                raise PreopenError("EMPTY_BOOTSTRAP_DENOMINATOR")
            for metric in samples:
                av = sum(_metric(d["baseline"], metric) for d in batch)
                bv = sum(_metric(d["candidate"], metric) for d in batch)
                samples[metric].append(100*(bv/b - av/a))
        for key, values in samples.items():
            values.sort()
            samples[key] = [values[int(.025*(draws-1))], values[int(.975*(draws-1))]]
        return samples

    return {"status": "DESCRIPTIVE_PAIRED_SESSION_BOOTSTRAP_NOT_OOS_CERTIFICATE",
            "sessionN": len(daily), "seed": seed, "draws": draws,
            "denominator": "ALL_SELECTED_INCLUDING_UNKNOWN",
            "delta95PctPoints": compute(1),
            "fixedCircularBlockSensitivity": {
                "blockLength": block_length,
                "status": "INSUFFICIENT_SESSIONS" if len(daily) < 2*block_length else "DESCRIPTIVE",
                "delta95PctPoints": None if len(daily) < 2*block_length else compute(block_length)}}


def remaining_opportunity(bars, *, reference_at, complete_session_verified,
                          max_reference_age_seconds=300):
    """Report-only reference-to-later-high diagnostic; never a preopen feature."""
    ref = stamp(reference_at)
    before = [b for b in bars if stamp(b["end"]) <= ref and stamp(b["availableAt"]) <= ref]
    after = [b for b in bars if stamp(b["start"]) >= ref]
    if (not complete_session_verified or not before or not after
            or any(stamp(b["start"]).date() != ref.date() for b in bars)):
        return {"status": "UNKNOWN", "reason": "INCOMPLETE_PATH_OR_REFERENCE"}
    latest = max(before, key=lambda b: stamp(b["end"]))
    age = (ref-stamp(latest["end"])).total_seconds()
    if age > max_reference_age_seconds:
        return {"status": "UNKNOWN", "reason": "STALE_REFERENCE", "referenceAgeSeconds": age}
    p = Fraction(Decimal(str(latest["close"])))
    high = max(Fraction(Decimal(str(b["high"]))) for b in after)
    if p <= 0 or high <= 0:
        raise PreopenError("INVALID_REMAINING_OPPORTUNITY_PRICE")
    return {"status": "KNOWN", "referenceAt": reference_at,
            "referenceAvailableAt": latest["availableAt"], "referenceAgeSeconds": age,
            "futureHighPct": float(100*(high/p-1)),
            "remainingMinutes": (max(stamp(b["end"]) for b in after)-ref).total_seconds()/60,
            "intrabarOrder": "AMBIGUOUS", "entryExitOrRotationPerformance": False}
