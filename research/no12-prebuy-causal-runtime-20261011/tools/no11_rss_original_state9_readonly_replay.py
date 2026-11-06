#!/usr/bin/env python3
"""Read-only OFFLINE research: original Frozen RC2 candidate/independent engines
on prior verified RSS chart JSON, not a certified causal live connection.

Assumptions explicitly NOT certified: RSS time labels = interval START,
"known_at" = theoretical bar end (not actual receipt), RSS != J-Quants source,
and Excel floating Value2 -> JSON numbers != vendor's original decimal tokens.
No orders, Excel, broker calls, downloads, live permissions or strategy edits.
"""
import argparse
from collections import Counter
from datetime import datetime, timedelta
from decimal import Decimal
import hashlib
import importlib
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True

EXPECTED_SHA = "bbd03f2e88a6df3eaec6ffb17c95c286aab26916b5ae71cab9c2d3dc747518d8"
SOURCE = "RSS_CHART_VALUE2_RESEARCH_ONLY_NOT_JQUANTS_V2"
DAY = "2026-10-13"
PREV = "2026-10-09"
PROFILE_REL = Path("research/state9-structural-exit-v2-20261003/FROZEN_SOURCE/profile.json")
FROZEN_REL = PROFILE_REL.parent


def check(condition, code):
    if not condition:
        raise ValueError(code)


def as_decimal_token(raw):
    check(type(raw) is str and raw.isascii(), "RAW_TOKEN_FORMAT_MISMATCH")
    v = Decimal(raw)
    check(v.is_finite() and v > 0, "RAW_PRICE_NONPOSITIVE")
    return raw


def clock_labels(current):
    return ([f"{x // 60:02d}:{x % 60:02d}" for x in range(540, 691)]
            + [f"{x // 60:02d}:{x % 60:02d}" for x in range(750, 925)]
            if current else
            [f"{x // 60:02d}:{x % 60:02d}" for x in range(540, 691)]
            + [f"{x // 60:02d}:{x % 60:02d}" for x in range(750, 925)]
            + ["15:30"])


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo", type=Path, required=True)
    p.add_argument("--evidence", type=Path, required=True)
    args = p.parse_args()
    check(args.evidence.is_file() and args.repo.is_dir(), "INPUT_PATH_MISSING")
    blob = args.evidence.read_bytes()
    digest = hashlib.sha256(blob).hexdigest()
    check(digest == EXPECTED_SHA, "EVIDENCE_SHA256_MISMATCH")
    data = json.loads(blob.decode("utf-8-sig"), parse_float=str, parse_int=str,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError("NONFINITE_JSON")))
    check(data.get("schemaId") == "ARK_NO11_RSS_CHART_DUAL_EVIDENCE_V1" and
          data.get("symbol") == "7203.T" and data.get("sourceFunction") == "RssChart" and
          data.get("evidenceMode") == "OBSERVED_READ_ONLY", "EVIDENCE_SOURCE_OR_SCHEMA_INVALID")
    for flag in ("excelOrderEnabled", "privateAccountDataIncluded", "labelSemanticsCertified",
                 "brokerArrivalCertified", "originalNativeState9Certified", "productionReady",
                 "orderTransmission"):
        check(data.get(flag) is False, "EVIDENCE_SAFETY_FLAG_NOT_FALSE:" + flag)
    check(set(data.get("periods", {})) == {"1M", "5M"}, "EVIDENCE_PERIODS_INVALID")
    old = sorted([r for r in data["periods"]["1M"]["rows"] if r["label"].startswith(PREV)], key=lambda r:r["label"])
    today = sorted([r for r in data["periods"]["1M"]["rows"] if r["label"].startswith(DAY)], key=lambda r:r["label"])
    check([r["label"][11:16] for r in old] == clock_labels(False) and
          [r["label"][11:16] for r in today] == clock_labels(True),
          "PREVIOUS_OR_CURRENT_COMPLETE_CLOCK_INVALID")
    check(len(old) == 327 and len(today) == 326, "INCOMPLETE_BARS")
    check(datetime.fromisoformat(data["periods"]["1M"]["observedAt"]).utcoffset() == timedelta(hours=9),
          "OBSERVATION_TIMEZONE_INVALID")
    for r in old + today:
        check(r["label"].endswith("+09:00"), "BAR_TIMEZONE_INVALID")
        o,h,l,c = (Decimal(as_decimal_token(r[k])) for k in ("open","high","low","close"))
        check(l <= min(o,c) and h >= max(o,c), "OHLC_INVALID")
        check(type(r["volume"]) is str and int(r["volume"]) >= 0, "VOLUME_INVALID")

    frozen = args.repo / FROZEN_REL
    check((frozen/"normalize80.py").is_file() and
          (frozen/"normalize120.py").is_file() and
          (frozen/"candidate/api.py").is_file() and
          (frozen/"independent/api.py").is_file() and
          (frozen/"profile.json").is_file(), "ORIGINAL_FROZEN_SOURCE_MISSING")
    sys.path.insert(0, str(frozen))
    normalize80 = importlib.import_module("normalize80")
    normalize120 = importlib.import_module("normalize120")
    candidate_api = importlib.import_module("candidate.api")
    independent_api = importlib.import_module("independent.api")
    profile = json.loads((frozen/"profile.json").read_text(encoding="utf-8"))

    def adapt(rows):
        out = []
        for r in rows:
            out.append({
                "Date": r["label"][:10], "Time": r["label"][11:16],
                "O": r["open"], "H": r["high"], "L": r["low"], "C": r["close"],
                "_source": {"label":r["label"],"evidenceSha256":digest,
                            "source":"RSS_EXCEL_VALUE2_JSON_TOKEN_NOT_VENDOR_NATIVE"}
            })
        return out

    old_price = adapt(old)
    today_price = adapt(today)
    r80 = normalize80.generate(old_price, today_price)
    r120 = normalize120.regenerate(old_price, today_price)
    compare_fields = ("U","P_ref","previous_return_pairs_N","previous_pair_ids",
                      "previous_last_source","previous_last_source_time","coordinates")
    check(all(r80[k] == r120[k] for k in compare_fields), "FROZEN_NATIVE_M0_80_120_MISMATCH")
    check(r80["U"] == "0.000999500333083533166809" and
          r80["P_ref"] == "2910.5" and r80["previous_return_pairs_N"] == 321 and
          len(r80["coordinates"]) == len(today), "M0_BASELINE_MISMATCH")

    a = candidate_api.Engine(profile)
    b = independent_api.Engine(profile)
    observed = Counter()
    all_primary = Counter()
    resets = 0
    mismatch = None
    keys = ("as_of","primary","basis","current_semantics_observed","observed_at",
            "context","leg_direction","activity","fast_flag","fast_applicable_to_primary",
            "numeric_status","rejection_reason","direction_basis")
    prev_t = None
    for candle, coord in zip(today, r80["coordinates"]):
        start = datetime.fromisoformat(candle["label"])
        end = start + timedelta(minutes=1)
        t = end.hour*60 + end.minute - 540
        check(t > 0 and (prev_t is None or t > prev_t), "SCHEDULED_ORDINAL_NOT_INCREASING")
        prev_t = t
        stamp = start.strftime("%H:%M")
        bucket = ("TERMINAL_AUCTION_MINUTE" if stamp=="11:30" else
                  "OPENING_MIXED_MINUTE" if stamp in ("09:00","12:30") else "CONTINUOUS")
        raw = {k.lower():coord[k] for k in ("O","H","L","C")}
        raw.update({"t":t, "known_at":t, "source":SOURCE, "auction":bucket})
        try:
            output_a = a.step(t, raw, case_id="RSS_7203_TECHNICAL_REPLAY")
            output_b = b.step(t, raw, case_id="RSS_7203_TECHNICAL_REPLAY")
        except Exception as e:
            raise ValueError("FROZEN_NATIVE_ENGINE_EXCEPTION_AT_"+stamp+":"+type(e).__name__) from e
        differences = [key for key in keys if output_a.get(key) != output_b.get(key)]
        check(not differences, "FROZEN_TWO_ENGINE_SEMANTIC_MISMATCH_AT_"+stamp+":"+','.join(differences))
        check(output_a["numeric_status"] == "ACCEPTED", "FROZEN_NATIVE_REJECTED_AT_"+stamp)
        check(output_a["as_of"] == t, "FROZEN_ASOF_INCONSISTENT")
        if output_a["current_semantics_observed"]:
            check(output_a["basis"] in ("OBSERVED_FRESH","OBSERVED_NEW_SEGMENT_ONLY"),
                  "STATE9_OBSERVED_BASIS_INVALID")
            check(output_a["observed_at"] == t, "STATE9_OBSERVED_AT_INVALID")
            observed[output_a["primary"]] += 1
        else:
            check(output_a["primary"] is None or output_a["basis"] in ("INITIALIZING","WARMUP_CARRY_OR_ANCHOR","OBSERVED_NEW_SEGMENT_ONLY"),
                  "STATE9_UNOBSERVED_PRIMARY_NEEDS_REVIEW")
        all_primary[str(output_a["primary"])] += 1
        if "SEGMENT_RESET_NO_GAP_RETURN" in output_a.get("events",[]):
            resets += 1

    check(sum(observed.values()) > 0, "NO_OBSERVED_STATE9_OUTPUT")
    print("NO11_EVIDENCE_SHA256="+digest)
    print("NO11_FROZEN_M0_80_120=PASS")
    print("NO11_FROZEN_STATE9_REPLAY_SCHEDULED_BARS="+str(len(today)))
    print("NO11_FROZEN_STATE9_REPLAY_LAST_SCHEDULED_T="+str(prev_t))
    print("NO11_FROZEN_STATE9_REPLAY_RC2_ACCEPTED="+str(sum(all_primary.values())))
    print("NO11_FROZEN_STATE9_REPLAY_OBSERVED="+str(sum(observed.values())))
    print("NO11_FROZEN_STATE9_REPLAY_INITIALIZING="+str(len(today)-sum(observed.values())))
    print("NO11_FROZEN_STATE9_REPLAY_RESETS="+str(resets))
    print("NO11_FROZEN_STATE9_REPLAY_STATE_COUNTS="+json.dumps(dict(sorted(observed.items())),sort_keys=True,separators=(",",":")))
    print("NO11_FROZEN_STATE9_TWO_ORIGINAL_ENGINES_SEMANTIC_PARITY=PASS")
    print("NO11_STATE9_TECHNICAL_REPLAY=OFFLINE_ASSUMED_KNOWN_AT_NOT_LIVE")
    print("NO11_VENDOR_LABEL_AND_ACTUAL_KNOWN_AT_CERTIFIED=False")
    print("NO11_ORIGINAL_VENDOR_DECIMAL_TOKENS_CERTIFIED=False")
    print("NO11_JQUANTS_SOURCE_IDENTITY_PARITY_CERTIFIED=False")
    print("NO11_NATIVE_STATE9_LIVE_CONNECTED=False")
    print("NO11_PRODUCTION_READY=False")
    print("ORDER_TRANSMISSION=False")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("NO11_STATE9_NATIVE_REPLAY=BLOCKED:"+str(e),file=sys.stderr)
        print("NO11_PRODUCTION_READY=False",file=sys.stderr)
        print("ORDER_TRANSMISSION=False",file=sys.stderr)
        sys.exit(2)
