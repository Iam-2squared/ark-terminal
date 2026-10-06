"""Aggregate saved Development RAW coverage without outcomes or fitting.

The denominators are watch-decision rows, not frozen FIRST ENTRY rows.
This never opens canonical_opportunities, geometry_rows, substrate opportunities,
teachers, or commonHoldout/excluded market data. No price values are printed.
"""
import collections
import datetime
import gzip
import hashlib
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = HERE / "recovered-persistent"
ALL58_PATH = HERE / "meta/docs/evidence/capital-max3-upward-staircase-v4-20261004-v1/SESSION_SPLIT.json"
GRID_RECEIPT = Path("/workspace/ark-sign-work/research/persistent-watchlist-uptrend-first-entry-20261003-v2/PERSISTENT_GRID_RECEIPT.json")


def read(path):
    data = Path(path).read_bytes()
    return json.loads(gzip.decompress(data) if str(path).endswith(".gz") else data)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def starts(day):
    return list(range(540, 690)) + list(range(750, 900 if day < "2024-11-05" else 925))


def valid(row):
    return (len(row) == 7 and all(math.isfinite(float(x)) for x in row)
            and row[3] > 0 and row[3] <= min(row[1], row[4])
            <= max(row[1], row[4]) <= row[2] and row[5] >= 0 and row[6] >= 0)


def window_status(observed, t, n):
    phase = 540 if t <= 690 else 750
    if t - n < phase:
        return "HALF_SESSION_HISTORY_NOT_YET_LONG_ENOUGH"
    return "AVAILABLE" if all(m in observed for m in range(t - n, t)) else "MISSING_SCHEDULED_OBSERVATION"


def main():
    grid_receipt = read(GRID_RECEIPT)
    export = read(SRC / "SOURCE_EXPORT_RECEIPT.json")
    for name in ("SOURCE_EXPORT_RECEIPT.json", "raw_paths_selected.json.gz",
                 "selector_events_full144.json.gz", "source_ledger.json", "split_original.json"):
        assert sha(SRC / name) == grid_receipt["source_inputs"][name]["sha256"]
    assert sha(ALL58_PATH) == "e83291b8706c48a4e496739219f1a645246b73be28f2195bebfaeb6614a12274"
    split, session_split = read(SRC / "split_original.json"), read(ALL58_PATH)
    allowed = set(split["intradayDevelopment"])
    protected = set(split["commonHoldout"]) | set(split["excluded"])
    all58 = set(session_split["all58"])
    raw = read(SRC / "raw_paths_selected.json.gz")
    assert all(k.split("|")[0] in allowed and k.split("|")[0] not in protected for k in raw)
    assert all(r["previousSession"] is None or r["previousSession"] in allowed for r in raw.values())
    events = read(SRC / "selector_events_full144.json.gz")
    assert all(e["sessionDate"] in allowed and e["sessionDate"] not in protected for e in events)
    first = {}
    for e in sorted(events, key=lambda e: (e["decisionTimestamp"], e["selectorEventId"])):
        key = e["sessionDate"] + "|" + e["symbol"]
        if key in raw:
            first.setdefault(key, e)
    assert set(first) == set(raw)
    selected = {k: v for k, v in raw.items() if k.split("|")[0] in all58}
    assert len(selected) == 2155 and len(all58) == 58
    counts = collections.Counter()
    windows = {str(n): collections.Counter() for n in (1, 2, 3, 4, 5, 6, 10, 11, 20, 21)}
    prior_windows = {str(n): collections.Counter() for n in (1, 3, 5, 10)}
    watch_support = collections.Counter()
    sources = collections.Counter()
    for key, r in selected.items():
        day = key.split("|")[0]
        regular = set(starts(day))
        e = first[key]
        selector_minute = int(e["decisionTimestamp"][11:13]) * 60 + int(e["decisionTimestamp"][14:16])
        today = r["today"]
        previous = r["previous"]
        assert all(len(x) == 7 for x in today + previous)
        assert all(type(x[0]) in (int, float) and x[0] == int(x[0]) for x in today + previous)
        for tag, rows in (("today", today), ("previous", previous)):
            minutes = [int(x[0]) for x in rows]
            assert len(minutes) == len(set(minutes))
            assert all(a < b for a, b in zip(minutes, minutes[1:]))
            counts[tag + "_raw_bars"] += len(rows)
            counts[tag + "_invalid_bars"] += sum(not valid(x) for x in rows)
            counts[tag + "_zero_volume_bars"] += sum(valid(x) and x[5] == 0 for x in rows)
            counts[tag + "_zero_value_bars"] += sum(valid(x) and x[6] == 0 for x in rows)
        obs = {int(x[0]) for x in today if valid(x) and int(x[0]) in regular}
        prior_regular = set(starts(r["previousSession"])) if r["previousSession"] is not None else set()
        prior = {int(x[0]) for x in previous if valid(x) and int(x[0]) in prior_regular}
        expected = sum(m + 1 >= selector_minute for m in regular)
        decisions = sorted(m + 1 for m in obs if m + 1 >= selector_minute)
        counts["expected_watch_decisions"] += expected
        counts["observed_watch_decisions"] += len(decisions)
        counts["missing_watch_decisions"] += expected - len(decisions)
        status = "EVALUABLE_FULL_GRID" if len(decisions) == expected else "PARTIALLY_EVALUABLE" if decisions else "SOURCE_UNAVAILABLE"
        watch_support[status] += 1
        counts["watches_with_empty_today"] += not bool(today)
        counts["watches_with_empty_previous"] += not bool(previous)
        counts["watches_without_previous_session"] += r["previousSession"] is None
        sources[r["contract"]] += 1
        for t in decisions:
            for n, c in windows.items():
                c[window_status(obs, t, int(n))] += 1
            for n, c in prior_windows.items():
                c[window_status(prior, t, int(n))] += 1
            expected_vwap = sum(m < t for m in regular)
            observed_vwap = sum(m < t for m in obs)
            counts["vwap_coverage_ge80pct_decisions"] += observed_vwap / expected_vwap >= .8
            counts["vwap_coverage_lt80pct_decisions"] += observed_vwap / expected_vwap < .8
    assert counts["expected_watch_decisions"] == grid_receipt["primary"]["expected_rows"] == 377450
    assert counts["observed_watch_decisions"] == grid_receipt["primary"]["observed_rows"] == 223940
    assert counts["missing_watch_decisions"] == grid_receipt["primary"]["missing_rows"] == 153510
    assert dict(watch_support) == grid_receipt["primary"]["status_counts"]
    utc = datetime.datetime.now(datetime.timezone.utc)
    report = {
        "status": "SAVED_RAW_RESTORED_HASH_MATCH_AND_CANONICAL_WATCH_GRID_COVERAGE_MATCH",
        "exact_utc": utc.isoformat(), "exact_jst": utc.astimezone(datetime.timezone(datetime.timedelta(hours=9))).isoformat(),
        "source_basis_head": export["basis_head"],
        "artifact_run": 37091120832,
        "artifact_sha256": "2db231298033006571bd8d5c709d3b19d81f0cc48644242fd763f6e891928cca",
        "restored_source_hashes": {p.name: sha(p) for p in SRC.iterdir() if p.is_file()},
        "all58_session_split_sha256": sha(ALL58_PATH),
        "RAW_schema": ["raw_start_minute_JST", "Open", "High", "Low", "Close", "Volume", "Value"],
        "RAW_price_basis": "Inherited frozen raw numeric input. Float conversion already done upstream; exact decimal source-token file is not in this artifact.",
        "RAW_original_token_missing": True,
        "available_at": "Historical actual receipt time UNKNOWN; raw-start+1 minute is inherited completed-bar assumption, not live-arrival certification.",
        "all_saved_watch_N": len(raw), "all_saved_session_N": len({k.split("|")[0] for k in raw}),
        "primary_watch_N": len(selected), "primary_sessions_N": len(all58),
        "primary_symbols_N": len({k.split("|")[1] for k in selected}),
        "primary_selector_events_N": sum(e["sessionDate"] in all58 for e in events),
        "bar_and_grid_counts": dict(counts), "watch_support_counts": dict(watch_support),
        "current_strict_window_status_counts": {n: dict(c) for n, c in windows.items()},
        "previous_day_strict_window_status_counts": {n: dict(c) for n, c in prior_windows.items()},
        "strict_window_denominator": "223940 actual observed CLOSED regular watch-decision rows across canonical 2155 watches and 58 sessions. This is NOT a frozen Entry1600 denominator.",
        "watch_grid_denominator": "377450 expected scheduled regular watch-decision rows after first Selector activation, not feature cells or Entry rows.",
        "protected_dates_N": len(split["commonHoldout"]), "excluded_dates_N": len(split["excluded"]),
        "protected_market_bodies_opened": 0, "excluded_market_bodies_opened": 0,
        "geometry_canonical_substrate_bodies_opened": 0, "teacher_rows_read": 0,
        "price_rows_displayed": 0, "new_provider_requests": 0, "fits": 0, "threshold_selection": 0, "capital_replay": 0,
        "frozen_entry_or_exit_replaced": False,
        "P0_connection": "Recovered RAW is byte-identical to the original frozen PERSISTENT_GRID source input. Suitable for descriptive strict-window audit and, once exact frozen Entry identity/intents and original snapshots are supplied, a separate sidecar P0 extractor/join audit. It is not a replacement Entry/EXIT/Sign snapshot.",
        "State9_connection": "Exact private source-token basis and existing frozen State/Path trace are not present; do not regenerate State9 from rounded numeric RAW or claim trace restored.",
        "missingness_causal_conclusion": "Not established. Strict-window unavailability is measured on watch-decision grid only; cannot attribute actual G_PRICE nulls on Entry1600 without original snapshots and Entry intents.",
        "next_action": "Use restored source for bounded descriptive audits. Recover exact frozen Entry1600 identities/intents, Sign original snapshots, and State/Path traces before feature repair or fitting.",
    }
    target = HERE / "RESTORED_RAW_COVERAGE_AUDIT.json"
    with target.open("x", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2, allow_nan=False)
        f.write("\n")
    print(json.dumps({k: report[k] for k in ("status", "primary_watch_N", "primary_sessions_N", "bar_and_grid_counts", "watch_support_counts", "current_strict_window_status_counts")}))


if __name__ == "__main__":
    main()
