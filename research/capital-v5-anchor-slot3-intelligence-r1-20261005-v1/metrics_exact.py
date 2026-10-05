"""R1 evaluator. No replay, policy, model, or native metrics imports.

Money source cells are Decimal strings and all economic comparisons use Fraction.
This module is the primary evaluator; independent validators must reconstruct its
results without importing it. Protected IDs enter evaluation functions only.
"""
from __future__ import annotations

from collections import Counter
from decimal import Decimal, localcontext, ROUND_HALF_UP
from fractions import Fraction
from typing import Any
import gzip
import json
from pathlib import Path

ONE_M = Fraction(1_000_000)
EXPECTED_SESSION_N = 38
WINDOW_N = 20
EXPECTED_WINDOWS = 19
EXPECTED_PROTECTED_N = 100
GATE_IDS = [f"E{i}" for i in range(8)] + [f"Q{i}" for i in range(1, 12)]


class MetricsContractError(ValueError):
    pass


def exact(value: Any) -> Fraction:
    """Float money is refused. JSON loaders preserve numeric literal Decimals."""
    if isinstance(value, Fraction):
        return value
    if isinstance(value, bool) or isinstance(value, float) or value is None:
        raise MetricsContractError(f"Non-exact source cell: {type(value).__name__}")
    if isinstance(value, int):
        return Fraction(value)
    d = value if isinstance(value, Decimal) else Decimal(value)
    if not d.is_finite():
        raise MetricsContractError("Nonfinite source cell")
    return Fraction(d)


def json_read(path: str | Path) -> Any:
    with Path(path).open(encoding="utf-8") as f:
        return json.load(f, parse_float=Decimal)


def jsonl_read(path: str | Path) -> list[dict]:
    path = Path(path)
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as f:
        return [json.loads(line, parse_float=Decimal) for line in f if line.strip()]


def fraction_record(value: Fraction | None) -> dict | None:
    if value is None:
        return None
    with localcontext() as ctx:
        ctx.prec = 60
        display = format(Decimal(value.numerator) / Decimal(value.denominator), "f")
    return {"numerator": value.numerator, "denominator": value.denominator,
            "decimal_display": display, "decision_domain": "EXACT_RATIONAL"}


def public(value: Any) -> Any:
    if isinstance(value, Fraction):
        return fraction_record(value)
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {str(k): public(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [public(v) for v in value]
    if isinstance(value, set):
        return sorted(value)
    if isinstance(value, float):
        raise MetricsContractError("Float encountered in exact evaluator output")
    return value


def rounded_yen(value: Fraction) -> str:
    with localcontext() as ctx:
        ctx.prec = max(80, len(str(abs(value.numerator))) + len(str(value.denominator)) + 5)
        return f"{int((Decimal(value.numerator)/Decimal(value.denominator)).quantize(Decimal(1), rounding=ROUND_HALF_UP)):,}"


def mean_exact(values: list[Fraction]) -> Fraction:
    if not values:
        raise MetricsContractError("Empty mean")
    return sum(values, Fraction(0)) / len(values)


def median_exact(values: list[Fraction]) -> Fraction:
    if not values:
        raise MetricsContractError("Empty median")
    s = sorted(values)
    n = len(s)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def maxdd_exact(initial_equity: Fraction, points: list[dict]) -> dict:
    if initial_equity <= 0 or not points:
        raise MetricsContractError("Missing/nonpositive MTM initial equity or points")
    peak = initial_equity
    peak_identity = {"source": "pre_window_EOD_equity"}
    maxdd = Fraction(0)
    peak_at_maxdd = initial_equity
    trough_at_maxdd = initial_equity
    peak_id_at_maxdd = peak_identity
    trough_id_at_maxdd = None
    for p in points:
        equity = exact(p["equity"])
        if equity <= 0:
            raise MetricsContractError("Nonpositive minute MTM equity")
        if equity > peak:
            peak, peak_identity = equity, {"session": p["session"], "minute": p["minute"]}
        dd = (peak - equity) / peak
        if dd > maxdd:
            maxdd = dd
            peak_at_maxdd, trough_at_maxdd = peak, equity
            peak_id_at_maxdd = peak_identity
            trough_id_at_maxdd = {"session": p["session"], "minute": p["minute"]}
    return {"maxdd": maxdd, "initial_peak": initial_equity, "valid_minute_point_N": len(points),
            "peak_equity": peak_at_maxdd, "trough_equity": trough_at_maxdd,
            "peak_identity": peak_id_at_maxdd, "trough_identity": trough_id_at_maxdd,
            "point_selection": "ALL_VALID_NATIVE_MINUTE_MTM_POINTS_NO_LUNCH_FILTER"}


def capital_metrics(daily: list[dict], curves: list[dict], expected_sessions: list[str] | None = None) -> dict:
    """No resetting: each window is cut from one continuous 38-session path."""
    facts = {"observed_session_N": len(daily), "expected_session_N": EXPECTED_SESSION_N,
             "window_sessions_N": WINDOW_N, "expected_window_N": EXPECTED_WINDOWS,
             "window_reset_replay_N": 0}
    reasons = []
    sessions = [d["session"] for d in daily]
    if len(daily) != EXPECTED_SESSION_N:
        reasons.append("FULL_38_SESSIONS_NOT_COMPLETE")
    if len(set(sessions)) != len(sessions) or sessions != sorted(sessions):
        reasons.append("SESSION_IDENTITIES_NOT_UNIQUE_AND_ORDERED")
    if expected_sessions is not None and sessions != expected_sessions:
        reasons.append("SESSION_IDENTITIES_MISMATCH_V5")
    for d in daily:
        if d.get("status") != "COMPLETE" or d.get("primary_chain") is not True or d.get("ending_cash") is None:
            reasons.append("DAILY_EXECUTION_OR_PRIMARY_CHAIN_INCOMPLETE")
        if d.get("open_obligations") or d.get("blockers"):
            reasons.append("UNRESOLVED_EXECUTION_OR_BLOCKER")
    if reasons:
        return {"status": "NOT_EVALUATED", "reasons": sorted(set(reasons)), "facts": facts,
                "windows": None, "statistics": None, "full_maxdd": None, "daily": None}
    by_session: dict[str, list[dict]] = {s: [] for s in sessions}
    for p in curves:
        if p["session"] not in by_session or p.get("primary_chain") is not True:
            raise MetricsContractError("Unexpected MTM session/primary chain")
        by_session[p["session"]].append(p)
    if [(p["session"],p["minute"]) for p in curves] != [(s,t) for s in sessions for t in range(540,932)]:
        raise MetricsContractError("Full MTM curve order/coverage mismatch")
    for i, d in enumerate(daily):
        start, end = exact(d["starting_cash"]), exact(d["ending_cash"])
        if start <= 0 or end <= 0:
            raise MetricsContractError("Nonpositive daily EOD equity")
        if i == 0 and start != ONE_M:
            raise MetricsContractError("Continuous chain must begin at 1000000")
        if i and start != exact(daily[i-1]["ending_cash"]):
            raise MetricsContractError("Session cash reset/continuous chain mismatch")
        points = by_session[d["session"]]
        identities = [(p["session"], p["minute"]) for p in points]
        if not points or len(set(identities)) != len(points) or identities != sorted(identities):
            raise MetricsContractError("Missing/duplicate/unsorted minute MTM")
        if [p["minute"] for p in points] != list(range(540, 932)):
            raise MetricsContractError("Frozen native MTM 540..931 coverage incomplete")
        if exact(points[-1]["equity"]) != end:
            raise MetricsContractError("EOD equity/minute MTM mismatch")
    windows = []
    for start_index in range(EXPECTED_WINDOWS):
        part = daily[start_index:start_index+WINDOW_N]
        pre = exact(part[0]["starting_cash"])
        end = exact(part[-1]["ending_cash"])
        window_points = [p for d in part for p in by_session[d["session"]]]
        growth = end / pre
        windows.append({"window_index": start_index, "start_session": part[0]["session"],
                        "end_session": part[-1]["session"], "pre_window_EOD_equity_cell": part[0]["starting_cash"],
                        "window_end_EOD_equity_cell": part[-1]["ending_cash"], "growth": growth,
                        "amount_from_1m": ONE_M * growth, "hit_2x": growth >= 2,
                        "below_1m": growth < 1, "maxdd": maxdd_exact(pre, window_points)})
    growths = [w["growth"] for w in windows]
    statistics = {"minimum": min(growths), "mean": mean_exact(growths), "median": median_exact(growths),
                  "maximum": max(growths), "hit_2x_N": sum(w["hit_2x"] for w in windows),
                  "below_1m_window_N": sum(w["below_1m"] for w in windows), "window_N": len(windows)}
    days = [{"session": d["session"], "starting_equity_cell": d["starting_cash"],
             "ending_equity_cell": d["ending_cash"],
             "exact_return": exact(d["ending_cash"]) / exact(d["starting_cash"]) - 1} for d in daily]
    return {"status": "EVALUATED", "facts": facts, "session_ids": sessions, "windows": windows,
            "statistics": statistics, "full_maxdd": maxdd_exact(ONE_M, curves), "daily": days,
            "negative_session_N": sum(d["exact_return"] < 0 for d in days),
            "worst_daily_return": min(d["exact_return"] for d in days),
            "final38_equity_secondary_only": exact(daily[-1]["ending_cash"])}


def trade_index(trades: list[dict]) -> dict[str, dict]:
    result = {}
    for t in trades:
        key = t["entry_id"]
        if key in result:
            raise MetricsContractError("Duplicate funded identity trade")
        debit, credit, pnl = exact(t["debit"]), exact(t["credit"]), exact(t["pnl"])
        if credit - debit != pnl:
            raise MetricsContractError("Trade debit/credit/PnL conservation mismatch")
        if t["quantity"] < 100 or t["quantity"] % 100:
            raise MetricsContractError("Funded BUY lot contract violated")
        result[key] = t
    return result


def protected_audit(v5_decisions: list[dict], v5_trades: list[dict], candidate_decisions: list[dict],
                    candidate_trades: list[dict], expected_n: int = EXPECTED_PROTECTED_N) -> dict:
    """Evaluation-only: membership is NEVER supplied to a replay/policy function."""
    base_t, cand_t = trade_index(v5_trades), trade_index(candidate_trades)
    cand_dec = {d["entry_id"]: d for d in candidate_decisions if d.get("quantity", 0) >= 100}
    protected = [d for d in v5_decisions if d.get("quantity", 0) >= 100 and d.get("funded_slot") in (1, 2)]
    ids = [d["entry_id"] for d in protected]
    if len(ids) != expected_n or len(set(ids)) != expected_n:
        raise MetricsContractError("V5 protected100 authority mismatch")
    groups = []
    detail = []
    for slot, expected_group_n in ((1, 41), (2, 59)):
        group = [d["entry_id"] for d in protected if d["funded_slot"] == slot]
        base_pnl = sum((exact(base_t[k]["pnl"]) for k in group), Fraction(0))
        present = [k for k in group if k in cand_dec and k in cand_t]
        cand_pnl = sum((exact(cand_t[k]["pnl"]) for k in present), Fraction(0))
        groups.append({"original_v5_slot": slot, "identity_N": len(group), "expected_identity_N": expected_group_n,
                       "funded_N": len(present), "v5_pnl": base_pnl, "candidate_pnl": cand_pnl,
                       "pnl_delta": cand_pnl-base_pnl, "all_identities_funded": len(present) == len(group),
                       "aggregate_pnl_noninferior": cand_pnl >= base_pnl})
        for key in group:
            bt, ct, cd = base_t[key], cand_t.get(key), cand_dec.get(key)
            detail.append({"entry_id": key, "original_v5_slot": slot, "candidate_funded": key in present,
                           "candidate_funded_slot": cd.get("funded_slot") if cd else None,
                           "v5_quantity": bt["quantity"], "candidate_quantity": ct["quantity"] if ct else None,
                           "v5_pnl_cell": bt["pnl"], "candidate_pnl_cell": ct["pnl"] if ct else None})
    passed = all(g["identity_N"] == g["expected_identity_N"] and g["all_identities_funded"] and
                 g["aggregate_pnl_noninferior"] for g in groups)
    return {"status": "PASS" if passed else "FAIL", "protected_identity_N": len(ids),
            "evaluation_only": True, "group_level_pnl_gate_only": True,
            "individual_identity_pnl_noninferiority_required": False, "groups": groups, "details": detail}


def quality_metrics(decisions: list[dict], trades: list[dict], outcomes: dict[str, dict],
                    capital: dict, protected: dict | None = None) -> dict:
    if capital["status"] != "EVALUATED":
        return {"status": "NOT_EVALUATED", "denominator": None, "counts": None,
                "reason": "FULL_38_EXECUTION_INCOMPLETE"}
    funded = [d for d in decisions if d.get("quantity", 0) >= 100]
    ids = [d["entry_id"] for d in funded]
    ts = trade_index(trades)
    if len(ids) != len(set(ids)) or set(ids) != set(ts):
        raise MetricsContractError("Funded BUY/trade exact identity mismatch")
    counts = Counter({"U5": 0, "U10": 0, "Medium": 0, "Weak": 0, "below3": 0,
                      "loser_le_zero": 0, "positive": 0, "strict_negative": 0, "exact_zero": 0})
    details = []
    loss = profit = Fraction(0)
    for key in ids:
        potential = exact(outcomes[key]["potential_pct"])
        pnl = exact(ts[key]["pnl"])
        flags = {"U5": potential >= 5, "U10": potential >= 10, "Medium": 3 <= potential < 5,
                 "Weak": potential < 2, "below3": potential < 3, "loser_le_zero": pnl <= 0,
                 "positive": pnl > 0, "strict_negative": pnl < 0, "exact_zero": pnl == 0}
        counts.update({k: int(v) for k, v in flags.items()})
        if pnl < 0:
            loss -= pnl
        elif pnl > 0:
            profit += pnl
        details.append({"entry_id": key, "session": ts[key]["session"],
                        "potential_pct_cell": outcomes[key]["potential_pct"], "pnl_cell": ts[key]["pnl"],
                        "flags": flags, "quantity": ts[key]["quantity"]})
    denom = len(ids)
    return {"status": "EVALUATED", "denominator": denom, "denominator_contract": "FUNDED_BUY_UNIQUE_IDENTITY_N",
            "counts": dict(counts), "rates": {k: Fraction(v, denom) if denom else None for k,v in counts.items()},
            "gross_realized_loss_jpy": loss, "gross_realized_profit_jpy": profit,
            "net_realized_pnl_jpy": profit-loss, "profit_factor": profit/loss if loss else None,
            "negative_session_N": capital["negative_session_N"],
            "worst_daily_return": capital["worst_daily_return"], "protected_slot12": protected,
            "funded_identity_details": details}


def gate(passed: bool | None, facts: dict, reason: str | None = None) -> dict:
    return {"status": "NOT_EVALUATED" if passed is None else "PASS" if passed else "FAIL",
            "facts": facts, **({"reason": reason} if reason else {})}


def compare_arm(v5_capital: dict, candidate_capital: dict, v5_quality: dict, candidate_quality: dict,
                independent_mismatch_n: int | None, all_causal_canaries_pass: bool | None) -> dict:
    gates = {}
    if v5_capital["status"] != "EVALUATED" or candidate_capital["status"] != "EVALUATED":
        return {"status": "NOT_EVALUATED", "eligible": False, "paired19": None,
                "gates": {gid: gate(None, {}, "FULL_38_EXECUTION_OR_AUTHORITY_INCOMPLETE") for gid in GATE_IDS}}
    bw, cw = v5_capital["windows"], candidate_capital["windows"]
    same_ids = [(w["start_session"],w["end_session"]) for w in bw] == [(w["start_session"],w["end_session"]) for w in cw]
    gates["E0"] = gate(len(cw) == 19 and same_ids,
                       {"session_N": 38, "unresolved_execution_N": 0, "paired_window_identity_exact": same_ids})
    if not same_ids:
        for gid in GATE_IDS[1:]:
            gates[gid] = gate(None, {}, "PAIRED_WINDOW_IDENTITIES_MISMATCH")
        return {"status": "FAIL", "eligible": False, "paired19": None, "gates": gates}
    pair = [{"start_session": b["start_session"], "end_session": b["end_session"],
             "v5_growth": b["growth"], "candidate_growth": c["growth"],
             "growth_delta": c["growth"]-b["growth"], "yen_delta": ONE_M*(c["growth"]-b["growth"]),
             "noninferior": c["growth"] >= b["growth"],
             "v5_maxdd": b["maxdd"]["maxdd"], "candidate_maxdd": c["maxdd"]["maxdd"],
             "maxdd_noninferior": c["maxdd"]["maxdd"] <= b["maxdd"]["maxdd"]} for b,c in zip(bw,cw)]
    gates["E1"] = gate(all(p["noninferior"] for p in pair),
                       {"better_N": sum(p["growth_delta"] > 0 for p in pair),
                        "equal_N": sum(p["growth_delta"] == 0 for p in pair),
                        "worse_N": sum(p["growth_delta"] < 0 for p in pair),
                        "worst_growth_delta": min(p["growth_delta"] for p in pair)})
    bs,cs = v5_capital["statistics"],candidate_capital["statistics"]
    for gid,k,strict in (("E2","median",True),("E3","mean",True),("E4","minimum",False),("E5","maximum",False)):
        gates[gid] = gate(cs[k] > bs[k] if strict else cs[k] >= bs[k],
                          {"v5":bs[k], "candidate":cs[k], "strict":strict})
    gates["E6"] = gate(cs["hit_2x_N"] >= bs["hit_2x_N"] and cs["below_1m_window_N"] == 0,
                       {"v5_hit_2x_N":bs["hit_2x_N"], "candidate_hit_2x_N":cs["hit_2x_N"],
                        "candidate_below_1m_window_N":cs["below_1m_window_N"]})
    bdd,cdd = v5_capital["full_maxdd"]["maxdd"],candidate_capital["full_maxdd"]["maxdd"]
    gates["E7"] = gate(all(p["maxdd_noninferior"] for p in pair) and cdd <= bdd,
                       {"all_paired19_window_maxdd_noninferior": all(p["maxdd_noninferior"] for p in pair),
                        "v5_full_maxdd":bdd, "candidate_full_maxdd":cdd})
    if v5_quality["status"] != "EVALUATED" or candidate_quality["status"] != "EVALUATED":
        for i in range(1,12):
            gates[f"Q{i}"] = gate(None, {}, "QUALITY_OUTCOME_JOIN_INCOMPLETE")
    else:
        qc = candidate_quality["counts"]
        n = candidate_quality["denominator"]
        for gid,k,target in (("Q1","U5",50),("Q2","U10",26),("Q3","Medium",27),("Q7","positive",68)):
            gates[gid] = gate(qc[k] >= target, {"candidate_N":qc[k], "minimum_N":target})
        for gid,k,max_n,strict in (("Q4","Weak",58,False),("Q5","below3",73,False),("Q6","loser_le_zero",82,True)):
            count_ok = qc[k] < max_n if strict else qc[k] <= max_n
            rate_ok = qc[k]*150 < max_n*n if strict else qc[k]*150 <= max_n*n
            gates[gid] = gate(n > 0 and count_ok and rate_ok,
                              {"candidate_N":qc[k],"candidate_denominator":n,"v5_N":max_n,
                               "v5_denominator":150,"integer_cross_product_candidate":qc[k]*150,
                               "integer_cross_product_v5":max_n*n,"strict":strict})
        gates["Q8"] = gate(candidate_quality["gross_realized_loss_jpy"] <= v5_quality["gross_realized_loss_jpy"],
                           {"v5":v5_quality["gross_realized_loss_jpy"],"candidate":candidate_quality["gross_realized_loss_jpy"]})
        gates["Q9"] = gate(candidate_quality["negative_session_N"] <= v5_quality["negative_session_N"] and
                           candidate_quality["worst_daily_return"] >= v5_quality["worst_daily_return"],
                           {"v5_negative_session_N":v5_quality["negative_session_N"],
                            "candidate_negative_session_N":candidate_quality["negative_session_N"],
                            "v5_worst_daily_return":v5_quality["worst_daily_return"],
                            "candidate_worst_daily_return":candidate_quality["worst_daily_return"]})
        protection = candidate_quality.get("protected_slot12")
        gates["Q10"] = gate(None if protection is None else protection["status"] == "PASS", protection or {},
                            "PROTECTED100_NOT_EVALUATED" if protection is None else None)
        known = independent_mismatch_n is not None and all_causal_canaries_pass is not None
        gates["Q11"] = gate(independent_mismatch_n == 0 and all_causal_canaries_pass is True if known else None,
                            {"independent_mismatch_N":independent_mismatch_n,
                             "all_causal_canaries_pass":all_causal_canaries_pass})
    eligible = all(gates[gid]["status"] == "PASS" for gid in GATE_IDS)
    return {"status": "PASS" if eligible else "NOT_EVALUATED" if any(g["status"] == "NOT_EVALUATED" for g in gates.values()) else "FAIL",
            "eligible":eligible, "paired19":pair, "gates":gates}


def select_research_candidate(arms: dict[str, dict]) -> str | None:
    eligible = [name for name in ("D", "DR") if name in arms and arms[name]["comparison"]["eligible"]]
    def sortkey(name: str):
        arm=arms[name]; s=arm["capital"]["statistics"]; q=arm["quality"]["counts"]
        return (-s["hit_2x_N"],-s["median"],-s["mean"],-s["minimum"],q["loser_le_zero"],
                -q["U10"],-q["U5"],-q["Medium"],arm["capital"]["full_maxdd"]["maxdd"],0 if name=="D" else 1)
    return sorted(eligible,key=sortkey)[0] if eligible else None


def delta_ledger(v5_trades: list[dict], candidate_trades: list[dict], outcomes: dict[str,dict],
                 all_sessions: list[str] | None = None) -> dict:
    b,c=trade_index(v5_trades),trade_index(candidate_trades)
    rows=[]
    for key in sorted(set(b)|set(c)):
        relation="COMMON" if key in b and key in c else "V5_ONLY" if key in b else "CANDIDATE_ONLY"
        bp,cp=exact(b[key]["pnl"]) if key in b else Fraction(0),exact(c[key]["pnl"]) if key in c else Fraction(0)
        rows.append({"entry_id":key,"relation":relation,"session":(c.get(key) or b[key])["session"],
                     "potential_pct_cell":outcomes[key]["potential_pct"],
                     "v5_quantity":b[key]["quantity"] if key in b else None,
                     "candidate_quantity":c[key]["quantity"] if key in c else None,
                     "v5_pnl":bp,"candidate_pnl":cp,"pnl_delta":cp-bp})
    sessions=all_sessions if all_sessions is not None else sorted({r["session"] for r in rows})
    total_delta=sum((r["pnl_delta"] for r in rows),Fraction(0))
    loo=[{"excluded_session":s,"trade_pnl_delta_excluding_session":total_delta-sum((r["pnl_delta"] for r in rows if r["session"]==s),Fraction(0))} for s in sessions]
    gained_lost={}
    for relation in ("V5_ONLY","CANDIDATE_ONLY"):
        group=[r for r in rows if r["relation"]==relation]
        pnl_key="v5_pnl" if relation=="V5_ONLY" else "candidate_pnl"
        gained_lost[relation]={"identity_N":len(group),
            "U5":sum(exact(r["potential_pct_cell"])>=5 for r in group),
            "U10":sum(exact(r["potential_pct_cell"])>=10 for r in group),
            "Medium":sum(3<=exact(r["potential_pct_cell"])<5 for r in group),
            "Weak":sum(exact(r["potential_pct_cell"])<2 for r in group),
            "positive":sum(r[pnl_key]>0 for r in group),
            "loser":sum(r[pnl_key]<=0 for r in group)}
    return {"rows":rows,"relation_counts":dict(Counter(r["relation"] for r in rows)),"gained_lost":gained_lost,
            "total_trade_pnl_delta":total_delta,"leave_one_session_out":loo,
            "LOO_contract":"SAVED_TRADE_DELTA_CONCENTRATION_ONLY_NO_NEW_REPLAY_OR_ROLLING20"}


def reason_conservation(decisions: list[dict], outcomes: dict[str,dict], rank_pass_ids: set[str]) -> dict:
    """Every frozen rank-pass U5/U10 ID has exactly one terminal decision reason."""
    by_id={}
    for d in decisions:
        if d["entry_id"] in by_id:
            raise MetricsContractError("Duplicate terminal decision identity")
        by_id[d["entry_id"]]=d
    records={}
    for label,threshold,expected in (("U5",5,113),("U10",10,47)):
        ids={key for key in rank_pass_ids if exact(outcomes[key]["potential_pct"]) >= threshold}
        if len(ids)!=expected:
            raise MetricsContractError("Frozen rank-pass winner denominator mismatch")
        reasons=Counter()
        detail=[]
        for key in sorted(ids):
            if key not in by_id:
                raise MetricsContractError("Missing rank-pass terminal reason")
            d=by_id[key]
            reason="FUNDED" if d.get("quantity",0)>=100 else d["reason"]
            reasons[reason]+=1
            detail.append({"entry_id":key,"reason":reason,"slot_gate_reason":d.get("slot_gate_reason"),"quantity":d.get("quantity",0)})
        records[label]={"denominator":expected,"reason_counts":dict(reasons),"conserved":sum(reasons.values())==expected,"identities":detail}
    return records


def slot3_and_token_diagnostics(decisions: list[dict],trades: list[dict],tokens: list[dict],
                                outcomes: dict[str,dict],completed_arm: bool) -> dict:
    """Observed ledgers; veto teacher joins are never counted as actual arm PnL."""
    ts=trade_index(trades)
    veto=[d for d in decisions if d.get("reason")=="V5_SLOT3_UNANIMOUS_LOW_SHIELD_REJECT"]
    rescued=[d for d in decisions if d.get("recovery_funded") is True and d.get("quantity",0)>=100]
    native_planned=[d for d in decisions if d.get("actual_planned_slot")==3 and d.get("native_would_fund_quantity",0)>=100]
    cohorts={}
    for name,group in (("veto",veto),("rescued",rescued)):
        rows=[]
        counts=Counter({"U5":0,"U10":0,"Medium":0,"Weak":0,"frozen_realized_le_zero":0,
                        "frozen_realized_positive":0,"frozen_realized_unknown":0})
        for d in group:
            out=outcomes[d["entry_id"]];pot=exact(out["potential_pct"])
            for k,v in (("U5",pot>=5),("U10",pot>=10),("Medium",3<=pot<5),("Weak",pot<2)):
                counts[k]+=int(v)
            r=out.get("frozen_realized_net_return_cell")
            if r is None or out.get("frozen_execution_status")!="COMPLETE":counts["frozen_realized_unknown"]+=1
            else:
                counts["frozen_realized_le_zero"]+=int(exact(r)<=0)
                counts["frozen_realized_positive"]+=int(exact(r)>0)
            t=ts.get(d["entry_id"])
            rows.append({"entry_id":d["entry_id"],"session":d["session"],"minute":d["minute"],
                         "native_would_fund_quantity":d.get("native_would_fund_quantity"),
                         "native_would_fund_debit_cell":d.get("native_would_fund_debit"),
                         "actual_planned_slot":d.get("actual_planned_slot"),"four_ranks":d.get("intelligence"),
                         "potential_pct_cell":out["potential_pct"],
                         "frozen_realized_net_return_post_join_cell":r,"frozen_execution_status":out.get("frozen_execution_status"),
                         "actual_arm_pnl_cell":t["pnl"] if t else None,
                         "post_join_evaluation_only":True})
        cohorts[name]={"observed_identity_N":len(group),"counts":dict(counts),"rows":rows}
    token_summary={"action_counts":dict(Counter(t["action"] for t in tokens)),
                   "terminal_reason_counts":dict(Counter(t.get("reason") for t in tokens if t["action"] in ("CONSUME","INVALIDATE"))),
                   "events":tokens}
    slot3ids={d["entry_id"] for d in decisions if d.get("quantity",0)>=100 and d.get("funded_slot")==3}
    return {"scope":"COMPLETE_ARM" if completed_arm else "OBSERVED_PARTIAL_LEDGER_ONLY_NO_OFFICIAL_ECONOMIC_GATE",
            "native_planned_slot3_observed_N":len(native_planned),"cohorts":cohorts,"tokens":token_summary,
            "funded_slot3_identity_N":len(slot3ids),
            "closed_slot3_pnl_jpy":sum((exact(ts[k]["pnl"]) for k in slot3ids if k in ts),Fraction(0)),
            "slot3_unclosed_identity_N":len(slot3ids-set(ts)),
            "veto_teacher_return_not_actual_arm_pnl":True}


def induced_miss_diagnostics(v5_decisions: list[dict],candidate_decisions: list[dict],outcomes: dict[str,dict]) -> dict:
    b={d["entry_id"]:d for d in v5_decisions}
    c={d["entry_id"]:d for d in candidate_decisions}
    rows=[]
    def category(d):
        if d.get("quantity",0)>=100:return "FUNDED"
        reason=d.get("reason","");slot=d.get("slot_gate_reason","")
        if "MAX3" in reason:return "MAX3"
        if "RESERVE" in reason or "RESERVE" in slot:return "RESERVE"
        if "CASH" in reason or "LOT" in reason:return "CASH_OR_LOT"
        if reason=="V5_SLOT3_UNANIMOUS_LOW_SHIELD_REJECT":return "D_VETO"
        return reason
    for key in sorted(set(b)&set(c)):
        bc,cc=category(b[key]),category(c[key])
        if bc==cc:continue
        rows.append({"entry_id":key,"v5_category":bc,"candidate_category":cc,
                     "potential_pct_cell":outcomes[key]["potential_pct"],
                     "new_MAX3_miss":cc=="MAX3" and bc!="MAX3",
                     "new_cash_miss":cc=="CASH_OR_LOT" and bc!="CASH_OR_LOT",
                     "new_reserve_miss":cc=="RESERVE" and bc!="RESERVE",
                     "reserve_recovery":bc=="RESERVE" and cc=="FUNDED"})
    return {"rows":rows,"counts":{k:sum(r[k] for r in rows) for k in ("new_MAX3_miss","new_cash_miss","new_reserve_miss","reserve_recovery")},
            "scope":"OBSERVED_REASON_LEDGER_JOIN_NO_CAUSAL_OVERLAP_OR_ORACLE_CLAIM"}
