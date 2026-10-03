"""Read-only, pre-replay Frozen Entry / EXIT source admission audit.

No allocator, fitting, portfolio replay, liquidation or provider access. This
program preserves every Frozen Entry, including UNRESOLVED exits. Its output
is a source-admission decision, never a State9-value or performance decision.
"""
from __future__ import annotations

import collections
import datetime as dt
from decimal import Decimal
import gzip
import hashlib
import json
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
SCRATCH = ROOT.parent
INPUTS = SCRATCH / "work_inputs"
OUT = ROOT / "docs/evidence/phase57-capital-state9-vnext-20261004"
PRIVATE = SCRATCH / "capital_vnext_private"
FROZEN_ENTRY_SHA = "e7a6140b6b11d8d078a271fad76b75e68a5b2fda9e45c7db43d98ee2f282abeb"


def rows(path):
    with gzip.open(path, "rt", encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(name, value):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(value, indent=2, sort_keys=True,
                                      ensure_ascii=False, allow_nan=False) + "\n")


def now():
    return dt.datetime.now(ZoneInfo("Asia/Tokyo")).isoformat()


def main():
    hashes = []
    for label in ("exit_v2", "exit_v3"):
        base = INPUTS / label
        manifest = json.loads((base / "MANIFEST.json").read_text())
        for name, meta in manifest["components"].items():
            path = base / name
            actual = digest(path) if path.is_file() else None
            hashes.append(dict(package=label, path=name, expected=meta["sha256"],
                               actual=actual, match=actual == meta["sha256"],
                               bytes_match=path.is_file() and path.stat().st_size == meta["bytes"]))
    entry_path = INPUTS / "exit_v2/FROZEN_ENTRY/P1_Q70_FIRST_ENTRY_RECORDS.jsonl.gz"
    assert digest(entry_path) == FROZEN_ENTRY_SHA
    watches = rows(entry_path)
    entries = [e for e in watches if e["entry_status"] == "FIRST_ENTRY"]
    replays = rows(INPUTS / "exit_v3/REPLAY_ROWS.jsonl.gz")
    economics = rows(INPUTS / "exit_v3/ECONOMICS_ROWS.jsonl.gz")
    by_exit = {x["watch_key"]: x for x in replays}
    by_econ = {x["watch_key"]: x for x in economics}
    with gzip.open(INPUTS / "exit_v2/SAVED_INPUTS/raw_paths_selected.json.gz", "rt") as f:
        raw_paths = json.load(f)
    assert len(watches) == 2155 and len(entries) == 1600
    assert len({e["watch_key"] for e in entries}) == len(by_exit) == len(by_econ) == 1600
    assert {e["watch_key"] for e in entries} == set(by_exit) == set(by_econ) == set(raw_paths)

    identities, execution, missing = [], [], []
    legacy_fields = ("confidence", "probability", "selectionOpportunityScore", "selectionV2Score")
    feature_counts = {name: 0 for name in legacy_fields}
    post_entry_mark_missing = []
    asof_execution_late = 0
    known_state = 0
    known_display_only = 0
    per_session = collections.defaultdict(lambda: collections.Counter())
    for entry in entries:
        key = entry["watch_key"]
        exit_ = by_exit[key]
        day = entry["session"]
        raw = raw_paths[key]["today"]
        lookup = {int(r[0]): r for r in raw}
        consistent = (
            exit_["session"] == day and exit_["symbol"] == entry["symbol"]
            and exit_["entry_timestamp"] == entry["fill_timestamp"]
            and Decimal(str(exit_["entry_fill_price"])) == Decimal(str(entry["fill_price"]))
        )
        identities.append(consistent)
        for name in legacy_fields:
            feature_counts[name] += int(name in entry and entry[name] is not None)
        snapshot = exit_["entry_snapshot"]
        known_state += int(snapshot.get("observed") is True and snapshot.get("primary") is not None)
        known_display_only += int(snapshot.get("primary") is None and snapshot.get("display_primary") is not None)

        fill_raw = lookup.get(entry["fill_minute"])
        entry_source_ok = fill_raw is not None and (
            abs(Decimal(str(entry["fill_price"])) - Decimal(str(fill_raw[1])) * Decimal("1.0005")) < Decimal("0.00000001")
        )
        record = dict(entry_id=key, session=day, symbol=entry["symbol"],
                      entry_timestamp=entry["fill_timestamp"],
                      entry_identity_match=consistent, entry_source_match=entry_source_ok,
                      entry_effective_price=entry["fill_price"],
                      sell_status=exit_["sell_status"], sell_timestamp=exit_["sell_timestamp"],
                      sell_price=exit_["sell_price"],
                      sell_source_assumed_available_at=exit_.get("sell_source_assumed_available_at"),
                      reference_execution_not_live_certification=True)
        per_session[day]["candidate_N"] += 1
        if exit_["sell_status"] == "FILLED":
            minute = exit_["sell_minute"]
            r = lookup.get(minute)
            index = 4 if exit_["sell_source"] == "PLANNED_TERMINAL_AUCTION_CLOSE" else 1
            exit_source_ok = r is not None and Decimal(str(exit_["sell_price_decimal"])) == Decimal(str(r[index])) * Decimal("0.9995")
            if dt.datetime.fromisoformat(exit_["sell_source_assumed_available_at"]) > dt.datetime.fromisoformat(exit_["sell_timestamp"]):
                asof_execution_late += 1
            record.update(exit_source_match=exit_source_ok,
                          positive_exit_delay=minute > entry["fill_minute"])
            execution.append(entry_source_ok and exit_source_ok and record["positive_exit_delay"])
            per_session[day]["FILLED"] += 1
        else:
            assert exit_["sell_status"] == "UNRESOLVED"
            assert exit_["sell_timestamp"] is None and exit_["sell_price"] is None
            record.update(unresolved_reason=exit_["unresolved_reason"],
                          cash_release_authorized=False, exit_source_match=None)
            missing.append(record)
            per_session[day]["UNRESOLVED"] += 1

        # Missing regular 1m closes inside the position window remain unknown.
        # This is an input completeness count, not a position replay or a claim
        # that every hypothetical allocation would fund this candidate.
        regular_end = 925 if day >= "2024-11-05" else 900
        end = min(exit_["sell_minute"] or regular_end, regular_end)
        regular = set(range(540, 690)) | set(range(750, regular_end))
        expected = sorted(m for m in regular if entry["fill_minute"] <= m < end)
        absent = [m for m in expected if m not in lookup]
        post_entry_mark_missing.append(dict(entry_id=key, missing_1m_close_N=len(absent),
                                            expected_1m_close_N=len(expected)))

    PRIVATE.mkdir(exist_ok=True)
    # No row-level data enters the public repository. Receipts pin private bytes.
    for name, values in (("ADAPTER_ROWS.jsonl.gz", [dict(entry_id=e["watch_key"],
                            session=e["session"], symbol=e["symbol"],
                            entry_timestamp=e["fill_timestamp"],
                            sell_status=by_exit[e["watch_key"]]["sell_status"]) for e in entries]),
                         ("UNRESOLVED_EXIT_ROWS.jsonl.gz", missing),
                         ("INPUT_HASH_CHECKS.jsonl.gz", hashes),
                         ("MARK_COMPLETENESS_ROWS.jsonl.gz", post_entry_mark_missing)):
        with (PRIVATE/name).open("wb") as raw_file:
            with gzip.GzipFile(filename="", mode="wb", fileobj=raw_file, mtime=0) as f:
                for value in values:
                    f.write((json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode())

    report = dict(
        saved_at_jst=now(), stage="C2_CURRENT_FROZEN_STRATEGY_ADAPTER_AUDIT",
        status="CAPITAL_ADAPTER_MISMATCH", identity_integrity_status="PASS",
        frozen_entry_source_sha256=digest(entry_path), watches_N=len(watches), candidate_N=len(entries),
        sessions_N=len(per_session), identity_mismatch_N=sum(not x for x in identities),
        source_component_hash_checks_N=len(hashes),
        source_component_hash_mismatch_N=sum(not x["match"] or not x["bytes_match"] for x in hashes),
        filled_exit_N=len(execution), filled_exit_source_or_price_mismatch_N=sum(not x for x in execution),
        unresolved_exit_N=len(missing), unresolved_exit_rate_pct=100*len(missing)/len(entries),
        sessions_with_unresolved_exit_N=sum(v["UNRESOLVED"] > 0 for v in per_session.values()),
        full_1600_resolved_trade_adapter_available=False,
        missing_rows_removed_N=0, invented_prices_N=0, invented_cash_releases_N=0,
        old_feature_counts=feature_counts, legacy_quality_status="LEGACY_FEATURE_UNAVAILABLE",
        P1_score_is_legacy_probability=False, P1_score_already_includes_State9=True,
        State9_snapshot_current_observed_primary_N=known_state,
        State9_snapshot_display_only_N=known_display_only,
        State9_snapshot_is_not_formal_asof_join_audit=True,
        candidates_with_missing_regular_1m_marks_N=sum(x["missing_1m_close_N"] > 0 for x in post_entry_mark_missing),
        missing_regular_1m_mark_N=sum(x["missing_1m_close_N"] for x in post_entry_mark_missing),
        historical_actual_known_at="UNKNOWN",
        execution_source_assumed_available_later_than_reference_fill_N=asof_execution_late,
        timing_boundary="Reference execution timestamp is not certified historical price-arrival/settlement timestamp. Moving fills or backdating arrival is not silently authorized.",
        inherited_cost=dict(BUY="raw Open *1.0005", SELL="raw Open or exact auction Close *0.9995", commission=0,
                            extra_old_005pct_roundtrip_fee_allowed=False,
                            extra_R34_005pct_sell_fee_allowed=False),
        technical_adapter_findings=[
            "Entry/EXIT identities and confirmed reference prices join exactly; schema mapping itself is feasible.",
            "Legacy Lane-C requires every normalized trade to have a finite EXIT timestamp/price and matching close marks; it cannot directly preserve the39 UNRESOLVED identities.",
            "Newer LONG-only ledgers can retain locked/unpriced positions and null equity. They do not resolve missing fills, establish overnight mark continuity, or make full-period allocation evidence complete.",
            "Old effective-fill==raw-close assumptions and fees require explicit semantic adaptation; no extra fees or synthetic effective close marks were adopted.",
        ],
        stop_basis="No all1600 complete source adapter under unchanged Frozen Entry/EXIT and required exact cash/MTM boundaries. Deleting UNRESOLVED rows is future-outcome filtering; substituting a close or crediting cash invents a Frozen EXIT. Null-aware exploratory accounting would remain incomplete, and is not silently promoted to the required comparative Freeze evidence.",
        new_portfolio_replays=0, new_fits=0, State9_incremental_value_tested=False,
        current_Capital_performance_conclusion=None,
        session_counts={k:dict(v) for k,v in sorted(per_session.items())},
    )
    assert report["identity_mismatch_N"] == report["source_component_hash_mismatch_N"] == report["filled_exit_source_or_price_mismatch_N"] == 0
    save("CURRENT_STRATEGY_ADAPTER_AUDIT.json", report)
    save("PRIVATE_ADAPTER_EVIDENCE_RECEIPT.json", {p.name:dict(bytes=p.stat().st_size, sha256=digest(p), visibility="PRIVATE") for p in sorted(PRIVATE.iterdir()) if p.is_file()})
    print(json.dumps({k:v for k,v in report.items() if k not in ("session_counts", "technical_adapter_findings", "stop_basis")}, indent=2))


if __name__ == "__main__":
    main()
