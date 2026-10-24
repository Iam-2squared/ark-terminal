#!/usr/bin/env python3
"""Ark Terminal: independent read-only RSS saved-JSON -> Frozen M0 technical audit.

This does NOT certify provider decimal-token lineage, actual receipt timestamps,
J-Quants source identity, State9 connection, or live order authorization.
No Excel/broker access; no output files; only prints non-account evidence.
"""
import argparse
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import sys

EXPECTED_SHA256 = "bbd03f2e88a6df3eaec6ffb17c95c286aab26916b5ae71cab9c2d3dc747518d8"
PREVIOUS_DAY = "2026-10-09"
CURRENT_DAY = "2026-10-13"
SYMBOL = "7203.T"


def stop(reason):
    raise ValueError(reason)


def schedule(period, terminal=True):
    if period == "1M":
        minutes = list(range(540, 690)) + [690] + list(range(750, 925))
    elif period == "5M":
        minutes = list(range(540, 690, 5)) + [690] + list(range(750, 925, 5))
    else:
        stop("UNKNOWN_PERIOD")
    if terminal:
        minutes.append(930)
    return [f"{m // 60:02d}:{m % 60:02d}" for m in minutes]


def frozen_module(folder, name):
    src = folder / (name + ".py")
    if not src.is_file():
        stop("FROZEN_M0_MODULE_MISSING:" + name)
    spec = importlib.util.spec_from_file_location("frozen_" + name, src)
    if spec is None or spec.loader is None:
        stop("FROZEN_MODULE_IMPORT_BLOCKED:" + name)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def decimal_number(s):
    if type(s) is not str:
        stop("DECIMAL_TOKEN_NOT_STRING")
    try:
        v = Decimal(s)
    except InvalidOperation:
        stop("DECIMAL_TOKEN_BAD")
    if not v.is_finite() or v <= 0:
        stop("DECIMAL_TOKEN_NONPOSITIVE")
    return v


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", required=True, type=Path)
    parser.add_argument("--repo", required=True, type=Path)
    args = parser.parse_args()
    if not args.evidence.is_file() or not args.repo.is_dir():
        stop("INPUT_PATH_MISSING")
    raw = args.evidence.read_bytes()
    file_sha = sha256(raw).hexdigest()
    if file_sha != EXPECTED_SHA256:
        stop("EVIDENCE_SHA256_MISMATCH")
    data = json.loads(raw.decode("utf-8-sig"), parse_int=str, parse_float=str,
                      parse_constant=lambda _: stop("NONFINITE_NUMBER"))
    if data.get("schemaId") != "ARK_NO11_RSS_CHART_DUAL_EVIDENCE_V1" or data.get("symbol") != SYMBOL:
        stop("EVIDENCE_SCHEMA_OR_SYMBOL_CHANGED")
    for key in ("privateAccountDataIncluded", "excelOrderEnabled", "labelSemanticsCertified",
                "brokerArrivalCertified", "originalNativeState9Certified", "productionReady", "orderTransmission"):
        if data.get(key) is not False:
            stop("UNEXPECTED_EVIDENCE_SAFETY_FLAG:" + key)
    if data.get("sourceFunction") != "RssChart" or data.get("evidenceMode") != "OBSERVED_READ_ONLY":
        stop("EVIDENCE_SOURCE_CHANGED")
    if set(data.get("periods", {})) != {"1M", "5M"}:
        stop("PERIOD_SCHEMA_CHANGED")
    by_period = {}
    for period in ("1M", "5M"):
        group = data["periods"][period]
        rows = group["rows"]
        if int(group["validRows"]) != len(rows) or len(rows) > int(group["requestedBars"]):
            stop("ROW_COUNT_INVALID:" + period)
        seen = set()
        by_day = {}
        for row in rows:
            label = row["label"]
            if label in seen:
                stop("DUPLICATE_BAR:" + label)
            seen.add(label)
            dt = datetime.fromisoformat(label)
            if dt.utcoffset() != timedelta(hours=9):
                stop("BAR_TIMEZONE_INVALID")
            if len(label) != 25 or label[19:] != "+09:00":
                stop("BAR_LABEL_INVALID")
            prices = {key: decimal_number(row[key]) for key in ("open", "high", "low", "close")}
            if prices["low"] > min(prices["open"], prices["close"]) or prices["high"] < max(prices["open"], prices["close"]):
                stop("INVALID_OHLC:" + label)
            vol = int(row["volume"])
            if vol < 0 or str(vol) != row["volume"]:
                stop("VOLUME_INVALID:" + label)
            by_day.setdefault(label[:10], []).append(row)
        by_period[period] = by_day
    for period in ("1M", "5M"):
        for day, terminal in ((PREVIOUS_DAY, True), (CURRENT_DAY, False)):
            got = sorted(r["label"][11:16] for r in by_period[period].get(day, []))
            expected = schedule(period, terminal=terminal)
            if got != expected:
                stop(f"EXPECTED_SESSION_BARS_INCOMPLETE:{period}:{day}:{len(got)}/{len(expected)}")
    one_by_label = {r["label"]: r for r in data["periods"]["1M"]["rows"]}
    matched = unmatched = 0
    for bar in data["periods"]["5M"]["rows"]:
        start = datetime.fromisoformat(bar["label"])
        group = [one_by_label.get((start + timedelta(minutes=i)).isoformat(timespec="seconds")) for i in range(5)]
        if any(r is None for r in group):
            unmatched += 1
            continue
        actual = {
            "open": decimal_number(group[0]["open"]),
            "high": max(decimal_number(r["high"]) for r in group),
            "low": min(decimal_number(r["low"]) for r in group),
            "close": decimal_number(group[-1]["close"]),
            "volume": sum(int(r["volume"]) for r in group),
        }
        if any(actual[k] != (int(bar[k]) if k == "volume" else decimal_number(bar[k])) for k in actual):
            stop("ONE_MIN_FIVE_MIN_OHLCV_MISMATCH:" + bar["label"])
        matched += 1
    if matched != 147 or unmatched != 51:
        stop("PARITY_DENOMINATOR_CHANGED")

    frozen = (args.repo / "research" / "state9-structural-exit-v2-20261003" / "FROZEN_SOURCE")
    m80 = frozen_module(frozen, "normalize80")
    m120 = frozen_module(frozen, "normalize120")

    def convert(day):
        out = []
        for r in sorted(by_period["1M"][day], key=lambda z: z["label"]):
            out.append({
                "Date": day, "Time": r["label"][11:16],
                "O": r["open"], "H": r["high"], "L": r["low"], "C": r["close"],
                "_source": {"evidenceSha256": file_sha, "source": "RSS_VALUE2_SERIALIZED_JSON",
                            "period": "1M", "label": r["label"]}
            })
        return out

    previous, current = convert(PREVIOUS_DAY), convert(CURRENT_DAY)
    r80 = m80.generate(previous, current)
    r120 = m120.regenerate(previous, current)
    comparable = ("U", "P_ref", "previous_return_pairs_N", "previous_pair_ids",
                  "previous_last_source", "previous_last_source_time", "coordinates")
    if any(r80[k] != r120[k] for k in comparable):
        stop("FROZEN_NATIVE_80_120_INCONSISTENT")
    if r80["previous_return_pairs_N"] != 321 or r80["P_ref"] != "2910.5":
        stop("PREVIOUS_REFERENCE_MISMATCH")
    if r80["U"] != "0.000999500333083533166809":
        stop("FROZEN_U_EXPECTED_MISMATCH")
    if len(r80["coordinates"]) != 326 or any(set(r) != {"O", "H", "L", "C"} for r in r80["coordinates"]):
        stop("NORMALIZATION_COORDINATE_COUNT_MISMATCH")
    print("NO11_EVIDENCE_SHA256=" + file_sha)
    print("NO11_PREVIOUS_FULL_1M=" + str(len(previous)))
    print("NO11_PREVIOUS_FULL_5M=" + str(len(by_period["5M"][PREVIOUS_DAY])))
    print("NO11_CURRENT_OBSERVED_1M=" + str(len(current)))
    print("NO11_PARITY_1M_5M=" + str(matched) + "/" + str(matched))
    print("NO11_PARITY_UNMATCHED_5M=" + str(unmatched))
    print("NO11_M0_PREVIOUS_RETURN_PAIRS=" + str(r80["previous_return_pairs_N"]))
    print("NO11_M0_P_REF=" + r80["P_ref"])
    print("NO11_M0_U=" + r80["U"])
    print("NO11_M0_NATIVE_COORDINATES_EQUAL=" + str(len(current) * 4))
    print("NO11_M0_NATIVE_80_120=TECHNICAL_PARITY_PASS")
    print("NO11_VENDOR_DECIMAL_PROVENANCE_CERTIFIED=False")
    print("NO11_VENDOR_LABEL_AND_AVAILABILITY_CERTIFIED=False")
    print("NO11_FROZEN_STATE9_CONNECTED=False")
    print("NO11_PRODUCTION_READY=False")
    print("ORDER_TRANSMISSION=False")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print("NO11_M0_NATIVE_AUDIT=BLOCKED:" + str(exc), file=sys.stderr)
        print("NO11_PRODUCTION_READY=False", file=sys.stderr)
        print("ORDER_TRANSMISSION=False", file=sys.stderr)
        sys.exit(2)
