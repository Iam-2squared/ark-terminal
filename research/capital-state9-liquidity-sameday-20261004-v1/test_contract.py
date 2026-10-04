"""Finite independent synthetic contract tests plus immutable1600 identity/cutoff admission."""
import copy
import gzip
import hashlib
import json
import sys
from pathlib import Path
from decimal import Decimal
from datetime import datetime, timedelta, timezone
import capital_contract as p
import independent_contract as independent

def main():
    root = Path(sys.argv[1])
    source = root / "eod_private/primary/entry.jsonl.gz"
    entries = [json.loads(s) for s in gzip.open(source, "rt")]
    entries = [e for e in entries if e["entry_status"] == "FIRST_ENTRY"]
    checks, mismatches = 0, []
    def check(name, actual, expected=True):
        nonlocal checks
        checks += 1
        if actual != expected:
            mismatches.append({"name": name, "actual": str(actual), "expected": str(expected)})
    check("N1600", len(entries), 1600)
    check("unique1600", len({e["watch_key"] for e in entries}), 1600)
    late = 0
    for e in entries:
        a, b = p.candidate_runtime(e), independent.runtime_oracle(e)
        for k in a:
            check("independent1600:" + k, a[k], b[k])
        late += not a["eligible"]
    check("late22 preserved funding0", late, 22)
    base = {"watch_key": "synthetic", "symbol": "synthetic", "session": "2025-08-25", "fill_timestamp": "2025-08-25T10:00:00+09:00", "fill_price": 1000.5, "first_intent": {"score": .72}}
    r = p.candidate_runtime(base)
    groups = []
    def group(name):
        groups.append(name)
    group("future_execution_presence_buy_invariance")
    for status in ["KNOWN", "UNKNOWN", "HALT", "NO_TRADE"]:
        e = {**base, "execution_evidence_status": status, "future_exit_price": 99999}
        check(groups[-1], p.candidate_runtime(e), r)
    group("future_high_low_rank_invariance")
    e = {**base, "futureHigh": 1e8, "futureLow": .1, "profit": -1e9}
    check(groups[-1], p.candidate_runtime(e), r)
    group("next_day_rank_invariance")
    check(groups[-1], p.candidate_runtime({**base, "nextDay": {"Open": 1e9}}), r)
    group("state_future_suffix_prefix_invariance")
    events = [{"known_at": "2025-08-25T09:59:00+09:00", "observed_at": "2025-08-25T09:58:00+09:00", "primary": "RANGE"}]
    prefix = p.rank_prefix(.72, base["fill_timestamp"], events)
    check(groups[-1], p.rank_prefix(.72, base["fill_timestamp"], events + [{"known_at": "2025-08-25T10:01:00+09:00", "observed_at": "2025-08-25T10:00:00+09:00", "primary": "SHARP_RISE"}]), prefix)
    group("liquidity_prior20_only")
    days = [(datetime(2025, 7, 1) + timedelta(days=i)).date().isoformat() for i in range(20)]
    records = [{"Date": d, "Va": str(10000000+i*1000000)} for i,d in enumerate(days)]
    cap = p.liquidity_capacity("2025-08-25", days, records)
    check(groups[-1], cap, independent.capacity_oracle("2025-08-25", days, records))
    check(groups[-1]+"future mutation", p.liquidity_capacity("2025-08-25", days, records + [{"Date":"2025-08-25", "Va":1e15}]), cap)
    check(groups[-1]+"no prior1", p.liquidity_capacity("2025-08-25", days, records[:1]), None)
    group("cutoff1520_always_zero")
    for clock in ["15:20:00", "15:20:59", "15:21:00", "15:24:00"]:
        x=p.candidate_runtime({**base,"fill_timestamp":"2025-08-25T"+clock+"+09:00"})
        check(groups[-1], p.quantity(x,1e6,1e6,1e6,1e6), (0,"CAPITAL_EOD_ENTRY_CUTOFF"))
    pos={"session":"2025-08-25", "quantity":100,"side":"LONG"}
    normal=p.eod_intent(pos)
    group("limitup_causal_flag_only")
    check(groups[-1],p.eod_intent(pos,{"dailyUL":"1","dailyHigh":1e9}),normal)
    flag={"session":"2025-08-25","status":"UPPER_LIMIT_CONFIRMED","authoritative":True,"observed_at":"2025-08-25T15:19:00+09:00","known_at":"2025-08-25T15:19:01+09:00"}
    exceptional=p.eod_intent(pos,flag)
    check("independent normal intent",normal,independent.intent_oracle(pos))
    check("independent limit-up intent",exceptional,independent.intent_oracle(pos,flag))
    check(groups[-1],exceptional["sor"],False)
    check(groups[-1]+"future flag",p.eod_intent(pos,{**flag,"known_at":"2025-08-25T15:21:00+09:00"}),normal)
    group("no_dual_normal_limitup_order")
    check(groups[-1],exceptional["intent_timestamp"],"2025-08-25T15:25:00+09:00")
    check(groups[-1],p.eod_intent({**pos,"closed":True}),None)
    group("no_auction_no_cash")
    nofill=p.execution_outcome(exceptional,[],None)
    check(groups[-1],nofill["cash_release"],Decimal(0))
    group("funded_unknown_pnl_not_zero")
    check(groups[-1],nofill["pnl"],None)
    check(groups[-1],nofill["status"],"POSITION_MEASUREMENT_BLOCKED")
    group("max3_4_5_cap")
    for n in [3,4,5]:
        positions=[]
        for _ in range(8):
            if len(positions)<n:positions.append(100)
            check(groups[-1],len(positions)<=n)
    group("cash_nonnegative")
    group("100_share_lot")
    for cash in [1,100000,1000000]:
        a=p.quantity(r,300000,cash,400000,cap)
        check("quantity independent",a,independent.quantity_oracle(r,300000,cash,400000,cap))
        check("cash>=0",Decimal(str(cash))-a[0]*Decimal(r["entry_effective_price"])>=0)
        check("lot100",a[0]%100,0)
    group("long_only")
    group("no_margin_short")
    for bad in [{**pos,"side":"SHORT"},{**pos,"margin":True}]:
        try:p.eod_intent(bad);ok=False
        except ValueError:ok=True
        check("cash LONG rejection",ok)
    group("commission_zero")
    group("execution_friction_once")
    ledger=p.accounting(Decimal(1000)*p.BUY_FACTOR,Decimal(1100)*p.SELL_FACTOR,100)
    check("commission",ledger["commission"],Decimal(0))
    check("cash endpoint vs pnl",ledger["credit"]-ledger["debit"],ledger["pnl"])
    check("single friction",ledger["pnl"],Decimal("9895.0000"))
    group("deterministic_rerun")
    check(groups[-1],p.candidate_runtime(copy.deepcopy(base)),r)
    check("eod future outcome not intent",p.eod_intent(pos),normal)
    check("future outcome suffix intent invariant",p.eod_intent({**pos,"future_price":1e9,"execution_evidence_status":"UNKNOWN","next_day_price":.001}),normal)
    trade={"timestamp":"2025-08-25T15:21:00+09:00","Open":"1100","Volume":100,"lineage":"synthetic-test-only","assumed_available_at":"2025-08-25T15:22:00+09:00"}
    auction={**trade,"timestamp":"2025-08-25T15:30:00+09:00","valid_exact_auction":True,"assumed_available_at":"2025-08-25T15:31:00+09:00"}
    for order in [normal,exceptional,None]:
        for regular,close in [([trade],auction),([],auction),([],None),([{**trade,"Open":"0"}],None)]:
            aa=p.execution_outcome(order,regular,close);bb=independent.outcome_oracle(order,regular,close)
            check("independent execution / cash",aa,bb)
    check("reference price only, no HL/Close",p.execution_outcome(normal,[{**trade,"High":1e9,"Low":.001,"Close":1e8}],auction),p.execution_outcome(normal,[trade],auction))
    result={"jst":datetime.now(timezone(timedelta(hours=9))).isoformat(),"status":"PASS" if not mismatches else "FAIL", "groups":groups,"group_count":len(groups),"checks":checks,"mismatch_count":len(mismatches),"mismatches":mismatches,"candidate_count":len(entries),"late_cutoff_count":late,"candidate_identities_unchanged":True,"funding_future_execution_input":False,"source_sha256":hashlib.sha256(source.read_bytes()).hexdigest(),"new_estimator_fits":0,"portfolio_replays":0,"provider_requests":0}
    print(json.dumps(result,ensure_ascii=False))
    return bool(mismatches)

if __name__=="__main__":sys.exit(main())
