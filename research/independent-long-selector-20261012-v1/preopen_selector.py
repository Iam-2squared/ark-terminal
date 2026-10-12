"""Preopen-only research Selector; no broker, provider, fit or execution side effects.

Input snapshots contain only records already admitted by a separate PIT source
adapter. Outcome data is accepted ONLY by the evaluator. Historical source
admission and production readiness are not certified by these Python checks.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal, InvalidOperation
from fractions import Fraction
from typing import Any

JST = timezone(timedelta(hours=9))
CONTRACT = "ARK_PREOPEN_OPEN_HIGH_V1_20261012"
LABEL = "JPX_RAW_OPEN_TO_ALL_SESSION_HIGH_V1"
POS_BINS = ("0..<1", "1..<2", "2..<3", "3..<4", "4..<5", ">=5")
STATE_NAMES = ("RISE_STOP", "RISE", "SHARP_RISE", "PULLBACK", "RANGE",
               "REBOUND", "SHARP_DROP", "DROP", "DROP_STOP")


class PreopenError(ValueError):
    """A violated contract is not an empty or a successful trading result."""


def digest(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, ensure_ascii=False,
                     separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def stamp(value: str) -> datetime:
    try:
        out = datetime.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise PreopenError("INVALID_TIMESTAMP") from exc
    if out.tzinfo is None or out.utcoffset() != timedelta(hours=9):
        raise PreopenError("JST_TIMESTAMP_REQUIRED")
    return out


def day(value: str) -> date:
    try:
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            raise ValueError()
        return date.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise PreopenError("INVALID_SESSION") from exc


def rational(value: Any) -> Fraction:
    if isinstance(value, bool) or not isinstance(value, (str, int, float, Decimal)):
        raise PreopenError("NONNUMERIC_PRICE_OR_FEATURE")
    try:
        dec = Decimal(str(value))
        if not dec.is_finite():
            raise ValueError()
        return Fraction(dec)
    except (ValueError, InvalidOperation, ZeroDivisionError) as exc:
        raise PreopenError("NONFINITE_PRICE_OR_FEATURE") from exc


def number(value: Any, *, positive: bool = False) -> float:
    x = rational(value)
    if positive and x <= 0:
        raise PreopenError("NONPOSITIVE_PRICE")
    v = float(x)
    if not math.isfinite(v):
        raise PreopenError("NONFINITE_PRICE_OR_FEATURE")
    return v


def symbol(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9A-Z]{4}(0)?", value):
        raise PreopenError("UNVERIFIED_SYMBOL_MAPPING")
    return value[:4] + "0"


def row_key(row: dict) -> tuple[str, str]:
    day(row["session"])
    return row["session"], symbol(row["symbol"])


@dataclass(frozen=True)
class PreopenConfig:
    cutoff: str = "08:50:00"
    watchlist_cap: int = 15
    minimum_prior_price_jpy: float = 75.0

    def at(self, session: str) -> datetime:
        try:
            clock = time.fromisoformat(self.cutoff)
        except ValueError as exc:
            raise PreopenError("INVALID_CUTOFF") from exc
        if clock.tzinfo is not None or not time(0) <= clock < time(9):
            raise PreopenError("CUTOFF_MUST_PRECEDE_09_00")
        if type(self.watchlist_cap) is not int or not 1 <= self.watchlist_cap <= 50:
            raise PreopenError("WATCHLIST_OR_RSS_CAPACITY")
        if number(self.minimum_prior_price_jpy) < 0:
            raise PreopenError("INVALID_MINIMUM_PRICE")
        return datetime.combine(day(session), clock, JST)

    @property
    def sha(self) -> str:
        return digest({"contract": CONTRACT, **asdict(self)})


def _bar(bar: dict) -> dict:
    out = dict(bar)
    for field in ("open", "high", "low", "close"):
        out[field] = number(bar[field], positive=True)
    if not out["low"] <= min(out["open"], out["close"]) <= max(out["open"], out["close"]) <= out["high"]:
        raise PreopenError("INVALID_OHLC")
    for field in ("volume", "turnover"):
        # The older generic library defaults missing turnover to zero. Do NOT
        # allow that fallback at this adapter boundary.
        out[field] = number(bar[field])
        if out[field] < 0:
            raise PreopenError("NEGATIVE_VOLUME_OR_TURNOVER")
    return out


def _resample_complete_history(bars: list[dict], kind: str) -> list[dict]:
    """Aggregate history available through D-1, not future completed weeks/months.

    The final bucket is intentionally 'to previous session', and marked partial
    in metadata. Complete-session input order is validated before this function.
    """
    grouped = defaultdict(list)
    for b in bars:
        d = day(b["session"])
        group = (d.isocalendar().year, d.isocalendar().week) if kind == "week" else (d.year, d.month)
        grouped[group].append(b)
    result = []
    for group in sorted(grouped):
        bs = grouped[group]
        result.append({"open": bs[0]["open"], "high": max(b["high"] for b in bs),
                       "low": min(b["low"] for b in bs), "close": bs[-1]["close"],
                       "volume": sum(b["volume"] for b in bs),
                       "turnover": sum(b["turnover"] for b in bs)})
    return result


def build_preopen_features(snapshot: dict, config: PreopenConfig = PreopenConfig()) -> dict:
    """Use admitted D-1 history plus specifically timed preopen external facts.

    No current-day OHLCV, current-day State or five-minute intraday freshness
    requirement is inherited from the old daytime Selector.
    """
    forbidden = {"minuteBars", "tickRows", "state9", "decisionPrice", "currentOpen",
                 "currentHigh", "currentLow", "currentVolume", "labels", "outcomes"}
    if forbidden.intersection(snapshot) or any(k.lower().startswith(("future", "label", "outcome")) for k in snapshot):
        raise PreopenError("CURRENT_SESSION_OR_OUTCOME_IN_PREOPEN_INPUT")
    session = snapshot["session"]
    cutoff = config.at(session)
    code = symbol(snapshot["symbol"])
    if snapshot.get("assetType") != "JPX_CASH_EQUITY":
        raise PreopenError("CASH_EQUITY_REQUIRED")
    master = snapshot["master"]
    if master.get("pitVerified") is not True or stamp(master["knownAt"]) > cutoff:
        raise PreopenError("MASTER_ASOF_UNVERIFIED")
    if master.get("eligible") is not True or master.get("segment") not in ("PRIME", "STANDARD", "GROWTH"):
        raise PreopenError("INELIGIBLE_PIT_UNIVERSE")
    if master.get("commonStock") is not True or master.get("lotSize") != 100:
        raise PreopenError("COMMON_STOCK_100_SHARE_CONTRACT_REQUIRED")
    if snapshot.get("historyBasisVerifiedAsOf") is not True:
        raise PreopenError("CORPORATE_ACTION_PRICE_BASIS_UNVERIFIED")
    if stamp(snapshot["historyBasisKnownAt"]) > cutoff:
        raise PreopenError("FUTURE_PRICE_ADJUSTMENT")
    expected = snapshot["historySessions"]
    if not expected or expected != sorted(set(expected)) or any(day(d) >= cutoff.date() for d in expected):
        raise PreopenError("INVALID_HISTORY_CALENDAR")
    if expected[-1] != snapshot["previousSession"]:
        raise PreopenError("PREVIOUS_SESSION_CALENDAR_MISMATCH")
    raw = snapshot["dailyBars"]
    if [b["session"] for b in raw] != expected:
        raise PreopenError("MISSING_OR_DUPLICATE_DAILY_SESSION_NO_FILL")
    bars = []
    for b in raw:
        if day(b["session"]) >= cutoff.date() or stamp(b["availableAt"]) > cutoff:
            raise PreopenError("CURRENT_OR_FUTURE_DAILY_BAR")
        if stamp(b["availableAt"]).date() < day(b["session"]):
            raise PreopenError("DAILY_AVAILABLE_BEFORE_ITS_SESSION")
        bars.append(_bar(b))
    if bars[-1]["close"] <= config.minimum_prior_price_jpy:
        raise PreopenError("INELIGIBLE_PRIOR_PRICE_POLICY")
    if not snapshot.get("universeHash") or not snapshot.get("sourceManifestSha256"):
        raise PreopenError("SOURCE_AND_UNIVERSE_IDENTITY_REQUIRED")

    from technical_feature_library import build_ohlcv_features, DAILY_PERIODS, MINUTE_PERIODS
    from selector_core import EXTRA_FEATURES
    features = build_ohlcv_features(bars, prefix="preopen_daily", reference_price=bars[-1]["close"], periods=DAILY_PERIODS)
    for interval in ("week", "month"):
        coarse = _resample_complete_history(bars, interval)
        features.update(build_ohlcv_features(coarse, prefix=f"preopen_{interval}", reference_price=bars[-1]["close"], periods=DAILY_PERIODS))
    # Every optional source has explicit coverage. Absence is not a verified
    # zero-activity tape. The previous session prefix is never today's tape.
    minute_tail = []
    supplied = snapshot.get("previousMinuteBars")
    if supplied is not None:
        if snapshot.get("previousMinuteCoverageVerified") is not True:
            raise PreopenError("PRIOR_MINUTE_COVERAGE_UNVERIFIED")
        last = None
        for b in supplied:
            start, end, known = (stamp(b[k]) for k in ("start", "end", "availableAt"))
            if start.date().isoformat() != snapshot["previousSession"] or end-start != timedelta(minutes=1):
                raise PreopenError("CURRENT_OR_INVALID_PRIOR_MINUTE")
            if not start < end <= known <= cutoff or (last is not None and start <= last):
                raise PreopenError("PRIOR_MINUTE_TIME_ORDER")
            last = start
            minute_tail.append(_bar(b))
        # Short-window indicators do not bridge lunch or missing minutes.
        for i in range(len(minute_tail)-1, 0, -1):
            if stamp(minute_tail[i]["start"])-stamp(minute_tail[i-1]["start"]) != timedelta(minutes=1):
                minute_tail = minute_tail[i:]
                break
    features.update(build_ohlcv_features(minute_tail, prefix="preopen_previous_minute", reference_price=bars[-1]["close"], periods=MINUTE_PERIODS))
    facts = snapshot.get("asofFacts", {})
    if set(facts).difference(EXTRA_FEATURES):
        raise PreopenError("UNREGISTERED_EXTERNAL_FEATURE")
    missing = {}
    for name in EXTRA_FEATURES:
        record = facts.get(name)
        target = "preopen_external_" + name
        if record is None:
            features[target] = None
            missing[target] = "SOURCE_NOT_JOINED"
        elif (record.get("pitVerified") is not True or not record.get("sourceId")
              or record.get("liveRefreshContractVerified") is not True):
            features[target] = None
            missing[target] = "SOURCE_OR_REFRESH_CONTRACT_UNVERIFIED"
        elif stamp(record["knownAt"]) > cutoff or stamp(record["observedAt"]) > cutoff:
            features[target] = None
            missing[target] = "NOT_KNOWN_AT_CUTOFF"
        else:
            features[target] = number(record["value"])
    prior_state = snapshot.get("previousState")
    if prior_state is not None:
        if (prior_state.get("session") != snapshot["previousSession"] or
            prior_state.get("pitVerified") is not True or
            stamp(prior_state["knownAt"]) > cutoff or prior_state.get("primary") not in STATE_NAMES):
            raise PreopenError("PRIOR_STATE_NOT_VERIFIED")
    for name in STATE_NAMES:
        features["preopen_previous_state_"+name] = float(prior_state["primary"] == name) if prior_state else None
    values = [v for v in features.values() if v is not None]
    if any(not math.isfinite(v) for v in values):
        raise PreopenError("NONFINITE_PREOPEN_FEATURE")
    return {"schema": "ARK_PREOPEN_FEATURE_ROW_V1", "contract": CONTRACT,
            "configHash": config.sha, "session": session, "symbol": code,
            "cutoff": cutoff.isoformat(), "assetType": "JPX_CASH_EQUITY",
            "universeHash": snapshot["universeHash"], "sourceManifestSha256": snapshot["sourceManifestSha256"],
            "priorClose": bars[-1]["close"], "priorTurnover": bars[-1]["turnover"],
            "features": features, "featureHash": digest(features),
            "featureCount": len(features), "observedFeatureCount": len(values),
            "missingReasons": missing,
            "coarseBarSemantics": "CALENDAR_BUCKETS_THROUGH_D_MINUS_1_NO_FUTURE_COMPLETION",
            "sampleKind": snapshot.get("sampleKind", "HISTORICAL"),
            "productionReady": False}


def validate_feature_row(row: dict, config: PreopenConfig | None = None) -> None:
    if row.get("schema") != "ARK_PREOPEN_FEATURE_ROW_V1" or row.get("contract") != CONTRACT:
        raise PreopenError("WRONG_FEATURE_CONTRACT")
    if any(k.lower().startswith(("future", "label", "outcome")) for k in row):
        raise PreopenError("OUTCOME_IN_SCORING_ROW")
    expected = (config or PreopenConfig()).at(row["session"])
    if stamp(row["cutoff"]) != expected or row.get("configHash") != (config or PreopenConfig()).sha:
        raise PreopenError("PREOPEN_TIME_OR_CONFIG_DRIFT")
    if row.get("assetType") != "JPX_CASH_EQUITY" or not row.get("universeHash") or not row.get("sourceManifestSha256"):
        raise PreopenError("MISSING_SOURCE_OR_UNIVERSE")
    if not row.get("features") or any(not k.startswith("preopen_") for k in row["features"]):
        raise PreopenError("NON_PREOPEN_FEATURE_SCHEMA")
    if digest(row["features"]) != row.get("featureHash"):
        raise PreopenError("FEATURE_HASH_MISMATCH")
    for v in row["features"].values():
        if v is not None:
            number(v)
    row_key(row)


def make_watchlist(rows: list[dict], scores: dict[tuple[str, str], float],
                   config: PreopenConfig = PreopenConfig()) -> dict:
    if not rows:
        raise PreopenError("EMPTY_UNIVERSE_REQUIRES_SEPARATE_NO_CANDIDATE_RECEIPT")
    for r in rows:
        validate_feature_row(r, config)
    identities = {(r["session"], r["cutoff"], r["universeHash"], r["sourceManifestSha256"]) for r in rows}
    if len(identities) != 1:
        raise PreopenError("MIXED_COHORT")
    keys = [row_key(r) for r in rows]
    if len(keys) != len(set(keys)) or set(scores) != set(keys):
        raise PreopenError("DUPLICATE_SYMBOL_OR_SCORE_COVERAGE")
    for score in scores.values():
        number(score)
    selected = sorted(rows, key=lambda r: (-scores[row_key(r)], symbol(r["symbol"])))[:config.watchlist_cap]
    out = {"schema": "ARK_PREOPEN_WATCHLIST_V1", "contract": CONTRACT,
           "configHash": config.sha, "session": rows[0]["session"], "cutoff": rows[0]["cutoff"],
           "universeHash": rows[0]["universeHash"], "sourceManifestSha256": rows[0]["sourceManifestSha256"],
           "eligibleN": len(rows), "selectedN": len(selected), "cap": config.watchlist_cap,
           "selectionInformation": "PREOPEN_ONLY", "entryAllowed": False,
           "executionAllowed": False, "transmitted": False, "productionReady": False,
           "items": [{"session": r["session"], "symbol": symbol(r["symbol"]),
                      "rssSymbol": symbol(r["symbol"])[:4]+".T", "rank": i+1,
                      "rankScoreNotExpectedReturn": float(scores[row_key(r)]),
                      "featureHash": r["featureHash"]} for i, r in enumerate(selected)]}
    out["watchlistHash"] = digest(out)
    return out


def verify_watchlist(watchlist: dict) -> None:
    body = {k: v for k, v in watchlist.items() if k != "watchlistHash"}
    if digest(body) != watchlist.get("watchlistHash") or watchlist.get("contract") != CONTRACT:
        raise PreopenError("WATCHLIST_HASH_OR_CONTRACT_DRIFT")
    if watchlist.get("selectionInformation") != "PREOPEN_ONLY" or stamp(watchlist["cutoff"]).time() >= time(9):
        raise PreopenError("LATER_INFORMATION_NOT_PREOPEN_COMPARATOR")
    items = watchlist["items"]
    keys = [row_key(x) for x in items]
    if len(keys) != len(set(keys)) or len(items) != watchlist["selectedN"]:
        raise PreopenError("WATCHLIST_CARDINALITY")
    if any(x["session"] != watchlist["session"] for x in items):
        raise PreopenError("WATCHLIST_SESSION_DRIFT")


def positive_bucket(value: Fraction) -> str:
    if value < 0:
        raise PreopenError("NEGATIVE_OPEN_HIGH_IS_INVALID_OHLC_NOT_LOSS")
    return ">=5" if value >= 5 else f"{value.numerator//value.denominator}..<{value.numerator//value.denominator+1}"


def signed_bucket(value: Fraction) -> str:
    if value >= 5:
        return ">=5"
    n = value.numerator // value.denominator
    return f"{n}..<{n+1}"


def evaluate_open_high(watchlist: dict, labels: dict[tuple[str, str], dict]) -> list[dict]:
    """Use official all-session raw OHLC, including opening and closing auctions.

    NO_OPEN and unknown paths retain their original selections. A bad H<O is a
    contract error; it must never become a negative result or be clipped to zero.
    """
    verify_watchlist(watchlist)
    result = []
    for item in watchlist["items"]:
        key = row_key(item)
        out = {"session": key[0], "symbol": key[1], "rank": item["rank"],
               "labelId": LABEL, "status": "UNKNOWN", "openHighPct": None,
               "openLowPct": None, "openClosePct": None, "bucket": "UNKNOWN"}
        lab = labels.get(key)
        if lab is None:
            out["missingReason"] = "NO_OUTCOME_RECORD"
        elif row_key(lab) != key:
            raise PreopenError("LABEL_IDENTITY_MISMATCH")
        elif lab.get("labelId") != LABEL or lab.get("market") != "T" or lab.get("priceBasis") != "RAW_JPX_CASH":
            raise PreopenError("LABEL_SOURCE_OR_PRICE_BASIS_MISMATCH")
        elif lab.get("traded") is False:
            out["missingReason"] = "NO_OPEN_NO_TRADE"
        elif (lab.get("completeSession") is not True or lab.get("officialFirstTradeOpen") is not True
              or any(lab.get(k) is None for k in ("open", "high", "low", "close"))):
            out["missingReason"] = "OPEN_OR_COMPLETE_SESSION_NOT_VERIFIED"
        else:
            o, h, l, c = [rational(lab[k]) for k in ("open", "high", "low", "close")]
            if min(o,h,l,c) <= 0 or not l <= min(o,c) <= max(o,c) <= h:
                raise PreopenError("INVALID_OUTCOME_OHLC")
            if lab.get("openingAt") is not None:
                opened = stamp(lab["openingAt"])
                if opened.date().isoformat() != key[0] or opened.time() < time(9) or opened.time() > time(15,30):
                    raise PreopenError("INVALID_ACTUAL_OPENING_TIMESTAMP")
                out["openingAt"] = lab["openingAt"]
            up, low, close = [100*(p/o-1) for p in (h,l,c)]
            out.update({"status": "KNOWN", "openHighPct": float(up), "openLowPct": float(low),
                        "openClosePct": float(close), "bucket": positive_bucket(up),
                        "lowBucket": signed_bucket(low), "closeBucket": signed_bucket(close),
                        "exactZero": up == 0,
                        "upHits": {str(k): up >= k for k in (1,2,3,4,5)},
                        "lowHits": {str(k): low <= -k for k in (1,2,3,5)},
                        "closeNegative": close < 0,
                        "intrabarOrder": "NOT_INFERRED", "executableProfit": False})
        result.append(out)
    return result


def summarize_open_high(rows: list[dict]) -> dict:
    known = [r for r in rows if r["status"] == "KNOWN"]
    n, k = len(rows), len(known)
    bins = {b: sum(r["bucket"] == b for r in known) for b in POS_BINS}
    return {"labelId": LABEL, "selectedN": n, "knownN": k, "unknownN": n-k,
            "buckets": bins, "exactZeroN": sum(r["exactZero"] for r in known),
            "negativeOpenHighN": 0, "negativeCountInterpretation": "STRUCTURAL_NOT_PREDICTIVE",
            "knownBucketPct": {b: 100*v/k if k else None for b,v in bins.items()},
            "highHitN": {str(t): sum(r["upHits"][str(t)] for r in known) for t in (1,2,3,4,5)},
            "highHitLowerBoundPct": {str(t): 100*sum(r["upHits"][str(t)] for r in known)/n if n else None for t in (1,2,3,4,5)},
            "lowHitN": {str(t): sum(r["lowHits"][str(t)] for r in known) for t in (1,2,3,5)},
            "closeNegativeN": sum(r["closeNegative"] for r in known),
            "lowBuckets": dict(Counter(r["lowBucket"] for r in known)),
            "closeBuckets": dict(Counter(r["closeBucket"] for r in known)),
            "marketPerformanceCertified": False}


def compare_preopen_watchlists(a: dict, b: dict, labels: dict) -> dict:
    for w in (a,b):
        verify_watchlist(w)
    fields = ("session", "cutoff", "configHash", "universeHash", "sourceManifestSha256", "eligibleN", "selectedN")
    if any(a[k] != b[k] for k in fields):
        raise PreopenError("UNPAIRED_PREOPEN_INFORMATION_OR_UNIVERSE")
    ar, br = evaluate_open_high(a, labels), evaluate_open_high(b, labels)
    aa, bb = summarize_open_high(ar), summarize_open_high(br)
    return {"schema": "ARK_PREOPEN_PAIRED_SCORECARD_V1", "session": a["session"],
            "baseline": aa, "candidate": bb,
            "deltaBucketN": {k: bb["buckets"][k]-aa["buckets"][k] for k in POS_BINS},
            "infoSetMatched": True, "portfolioComparison": False}
