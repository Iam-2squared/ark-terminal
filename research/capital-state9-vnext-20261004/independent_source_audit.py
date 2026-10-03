"""Independent archive/SQL/Fraction audit; no import of the primary auditor.

Reads the original attached nested ZIP bytes, rather than the extracted primary
inputs. It certifies source counts, source price arithmetic and null boundaries
only. It cannot certify portfolio, State9 joining, ranking or performance that
were not executed.
"""
from __future__ import annotations

import collections
import datetime as dt
from fractions import Fraction
import gzip
import hashlib
import io
import json
from pathlib import Path
import sqlite3
import zipfile
from zoneinfo import ZoneInfo

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "docs/evidence/phase57-capital-state9-vnext-20261004"
ARCHIVE = REPO.parent / "project_sources/19-Ark_Terminal_NEW_CHAT_HANDOFF_After_EXITV3_REENTRY_CapitalNext_20261003-5-.zip"


def main():
    primary = json.loads((OUT / "CURRENT_STRATEGY_ADAPTER_AUDIT.json").read_text())
    artifacts = {}
    archives = {}
    with zipfile.ZipFile(ARCHIVE) as outer:
        for n in outer.namelist():
            if n.endswith(".zip") and "/02_EVIDENCE/" in n and ("STRUCTURAL_EXIT_V2_" in n or "STRUCTURAL_EXIT_V3_" in n):
                label = "v2" if "EXIT_V2_" in n else "v3"
                payload = outer.read(n)
                archives[label] = hashlib.sha256(payload).hexdigest()
                with zipfile.ZipFile(io.BytesIO(payload)) as archive:
                    artifacts[label] = {i.filename: archive.read(i) for i in archive.infolist() if not i.is_dir()}

    checks = 0
    failures = []
    for name, files in artifacts.items():
        manifest = json.loads(files["MANIFEST.json"])
        for path, spec in manifest["components"].items():
            checks += 1
            if hashlib.sha256(files[path]).hexdigest() != spec["sha256"] or len(files[path]) != spec["bytes"]:
                failures.append(dict(check="original_archive_component_hash", package=name, path=path))

    raw_entries = [json.loads(s) for s in gzip.decompress(artifacts["v2"]["FROZEN_ENTRY/P1_Q70_FIRST_ENTRY_RECORDS.jsonl.gz"]).splitlines()]
    exits = [json.loads(s) for s in gzip.decompress(artifacts["v3"]["REPLAY_ROWS.jsonl.gz"]).splitlines()]
    raw_paths = json.loads(gzip.decompress(artifacts["v2"]["SAVED_INPUTS/raw_paths_selected.json.gz"]))
    db = sqlite3.connect(":memory:")
    db.executescript("""
        CREATE TABLE entry(id TEXT PRIMARY KEY, session TEXT, symbol TEXT, stamp TEXT, price TEXT, payload TEXT);
        CREATE TABLE sell(id TEXT PRIMARY KEY, session TEXT, symbol TEXT, stamp TEXT, price TEXT, status TEXT, payload TEXT);
    """)
    selected = [x for x in raw_entries if x["entry_status"] == "FIRST_ENTRY"]
    db.executemany("INSERT INTO entry VALUES(?,?,?,?,?,?)", [(x["watch_key"], x["session"], x["symbol"], x["fill_timestamp"], str(x["fill_price"]), json.dumps(x)) for x in selected])
    db.executemany("INSERT INTO sell VALUES(?,?,?,?,?,?,?)", [(x["watch_key"], x["session"], x["symbol"], x["entry_timestamp"], str(x["entry_fill_price"]), x["sell_status"], json.dumps(x)) for x in exits])
    identity_sql = db.execute("""
        SELECT COUNT(*) FROM entry e LEFT JOIN sell s USING(id)
        WHERE s.id IS NULL OR e.session != s.session OR e.symbol != s.symbol
           OR e.stamp != s.stamp OR e.price != s.price
    """).fetchone()[0]
    statuses = dict(db.execute("SELECT status,COUNT(*) FROM sell GROUP BY status"))
    sessions = db.execute("SELECT COUNT(DISTINCT session) FROM entry").fetchone()[0]
    sessions_unresolved = db.execute("SELECT COUNT(DISTINCT session) FROM sell WHERE status='UNRESOLVED'").fetchone()[0]
    state_count = 0
    display_count = 0
    late_count = 0
    price_failures = []
    source_checks = 0
    missing = 0
    incomplete_windows = 0
    old_field_counts = dict.fromkeys(("confidence", "probability", "selectionOpportunityScore", "selectionV2Score"), 0)
    for entry_text, sell_text in db.execute("SELECT e.payload,s.payload FROM entry e JOIN sell s USING(id)"):
        e, x = json.loads(entry_text), json.loads(sell_text)
        key = e["watch_key"]
        data = {int(a[0]): a for a in raw_paths[key]["today"]}
        for f in old_field_counts:
            old_field_counts[f] += int(e.get(f) is not None)
        s = x["entry_snapshot"]
        state_count += int(s.get("observed") is True and s.get("primary") is not None)
        display_count += int(s.get("primary") is None and s.get("display_primary") is not None)
        source_checks += 1
        expected_entry = Fraction(str(data[e["fill_minute"]][1])) * Fraction(2001,2000)
        if abs(Fraction(str(e["fill_price"])) - expected_entry) >= Fraction(1,100000000):
            price_failures.append(dict(entry_id=key, side="ENTRY"))
        if x["sell_status"] == "FILLED":
            source_checks += 1
            row = data[x["sell_minute"]]
            index = 4 if x["sell_source"] == "PLANNED_TERMINAL_AUCTION_CLOSE" else 1
            if Fraction(x["sell_price_decimal"]) != Fraction(str(row[index])) * Fraction(1999,2000):
                price_failures.append(dict(entry_id=key, side="EXIT"))
            late_count += int(dt.datetime.fromisoformat(x["sell_source_assumed_available_at"]) > dt.datetime.fromisoformat(x["sell_timestamp"]))
        elif not (x["sell_timestamp"] is None and x["sell_price"] is None):
            failures.append(dict(check="unresolved_null", entry_id=key))
        end_regular = 925 if e["session"] >= "2024-11-05" else 900
        window_end = min(x["sell_minute"] or end_regular, end_regular)
        absent = sum(e["fill_minute"] <= minute < window_end and minute not in data
                     for minute in (*range(540,690), *range(750,end_regular)))
        missing += absent
        incomplete_windows += int(absent > 0)

    expected = {
        "candidate_N": len(selected), "sessions_N": sessions,
        "source_component_hash_checks_N": checks,
        "identity_mismatch_N": identity_sql,
        "filled_exit_N": statuses.get("FILLED",0),
        "unresolved_exit_N": statuses.get("UNRESOLVED",0),
        "sessions_with_unresolved_exit_N": sessions_unresolved,
        "State9_snapshot_current_observed_primary_N": state_count,
        "State9_snapshot_display_only_N": display_count,
        "execution_source_assumed_available_later_than_reference_fill_N": late_count,
        "candidates_with_missing_regular_1m_marks_N": incomplete_windows,
        "missing_regular_1m_mark_N": missing,
    }
    for name, v in expected.items():
        if primary[name] != v:
            failures.append(dict(check="primary_comparison", field=name, independent=v, primary=primary[name]))
    if primary["old_feature_counts"] != old_field_counts:
        failures.append(dict(check="legacy_feature_counts"))
    db.close()
    report = dict(saved_at_jst=dt.datetime.now(ZoneInfo("Asia/Tokyo")).isoformat(),
                  status="PASS_SOURCE_ADAPTER_AUDIT_ONLY" if not failures and not price_failures and identity_sql == 0 else "FAIL",
                  independent_route="Original nested attachment ZIP -> SQLite identity join and status aggregation -> Fraction source price arithmetic; no primary auditor imported",
                  input_archive_sha256=hashlib.sha256(ARCHIVE.read_bytes()).hexdigest(),
                  nested_archive_sha256=archives, independent_source_counts=expected,
                  independent_confirmed_price_checks_N=source_checks,
                  source_hash_mismatch_N=len([x for x in failures if x["check"] == "original_archive_component_hash"]),
                  source_price_mismatch_N=len(price_failures), findings=failures+price_failures,
                  primary_comparison_mismatch_N=len(failures), old_feature_counts=old_field_counts,
                  supported_stop="CAPITAL_ADAPTER_MISMATCH",
                  integrity_pass_does_not_equal_adapter_admission=True,
                  C9_full_portfolio_audit_executed=False, portfolio_final_equity_audited=False,
                  portfolio_MaxDD_audited=False, current_State9_asof_join_certified=False,
                  future_isolation_current_Capital_canaries_executed=False,
                  future_isolation_legacy_original_test_evidence="18 recovered focused tests; one earlier-decision supplemental canary",
                  new_fits=0, new_portfolio_replays=0, provider_requests=0,
                  orders=0, main_merges=0)
    (OUT/"INDEPENDENT_AUDIT.json").write_text(json.dumps(report,indent=2,sort_keys=True,ensure_ascii=False)+"\n")
    print(json.dumps(report,indent=2))
    if report["status"] != "PASS_SOURCE_ADAPTER_AUDIT_ONLY":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
