"""R1 independent implementation from the frozen V5 and R1 contracts.

No Primary adapter, policy, replay, allocation, execution, or metrics module is
imported here. The frozen V5 sources were inspected, then native gate, Decimal
funding, execution, token, and the event loop were separately implemented.

Decimal precision 28 / HALF_EVEN and the frozen V5 reduction order are the
canonical monetary operators. Sharing frozen raw inputs and frozen model bytes
is allowed. This module never calls any trainer or estimator fit method.

Calling ``run_profile`` is a counted reconstruction. It must only be called
once for D and once for DR after the parent has durably claimed and actual-GET
verified those executions. ``reconstruct_batch`` is outcome-blind and may be
used for the pre-main saved-Control proposal audit; it is not a market replay.
"""

from collections import defaultdict
from copy import deepcopy
from datetime import datetime
from decimal import Decimal, ROUND_FLOOR, ROUND_HALF_EVEN, localcontext
from fractions import Fraction
import math


D = Decimal
BUY = D("1.0005")
SELL = D("0.9995")
HEADS = ("pP", "MOVE_U2", "MOVE_U3", "MRET")
RANK_NAMES = dict(zip(HEADS, ("rP", "r2", "r3", "rM")))
CAP = {"S": D(".45"), "A": D(".35"), "B": D(".25")}
DEPLOY = {"S": D(".68"), "A": D(".56"), "B": D(".44")}
SHIELD_REASON = "V5_SLOT3_UNANIMOUS_LOW_SHIELD_REJECT"
ABSTAIN_REASON = "INTELLIGENCE_UNAVAILABLE_ABSTAIN_TO_V5"
RECOVERY_REASON = "V5_SLOT3_GUARDED_WINNER_RECOVERY_FUNDED"
D_PROFILE = "V5_SLOT3_UNANIMOUS_LOW_SHIELD_V1"
DR_PROFILE = "V5_SLOT3_UNANIMOUS_LOW_SHIELD_WITH_GUARDED_RECOVERY_V1"


def monetary_context():
    ctx = localcontext()
    return ctx


def capacity_band(score):
    if score is None or not math.isfinite(score) or score < 1:
        return None
    if score >= 2:
        return "S"
    if score >= 1.5:
        return "A"
    return "B"


def stable_order(row):
    return (-row["ML"], -row["m5"], -row["m3"], -row["m2"],
            row["entry_timestamp"], row["symbol"])


def native_gate(row, occupancy, minute, table):
    """Frozen V5 native slot policy, separately implemented."""
    assert occupancy in range(4)
    assert row["ML"] >= 1
    arrivals = table["minute_counts"][str(minute)]
    n = table["training_session_N"]
    probability = arrivals[0] / n
    expected = arrivals[2] / n
    audit = {
        "pre_decision_occupancy": occupancy,
        "training_B_median": table["B_median"],
        "training_B_p75": table["B_p75"],
        "remaining_Aplus_probability": probability,
        "remaining_Aplus_ge2_probability": arrivals[1] / n,
        "expected_remaining_Aplus": expected,
        "arrival_bucket": table["minute_bucket"][str(minute)],
        "training_block": row["block"],
    }
    if occupancy == 3:
        return False, "MAX_POSITION_CAP", audit
    if occupancy == 0:
        return True, "SLOT1_NO_RESERVE", audit
    if row["rank"] in ("S", "A"):
        return True, "SA_ALWAYS_ADMIT", audit
    assert row["rank"] == "B"
    if occupancy == 1:
        if minute >= 840:
            return True, "SLOT2_B_LATE_RELEASE", audit
        yes = row["ML"] >= table["B_median"] and probability < .50
        return yes, ("SLOT2_B_QUALITY_AND_ARRIVAL_PASS" if yes
                     else "SLOT2_RESERVE_FOR_FUTURE_QUALITY"), audit
    quality = row["ML"] >= table["B_p75"]
    yes = quality and (minute >= 870 or (probability < .35 and expected < .75))
    reason = ("SLOT3_B_LATE_RELEASE" if yes and minute >= 870 else
              "SLOT3_B_QUALITY_AND_ARRIVAL_PASS" if yes else
              "SLOT3_RESERVE_FOR_FUTURE_QUALITY")
    return yes, reason, audit


def allocate(picked, equity, exposure, cash, existing_bands):
    """Independent frozen allocation with exact Decimal28 monetary fields."""
    with localcontext() as ctx:
        ctx.prec = 28
        ctx.rounding = ROUND_HALF_EVEN
        eq, exp, available = D(str(equity)), D(str(exposure)), D(str(cash))
        all_bands = list(existing_bands) + [capacity_band(c["capital_score"]) for c in picked]
        assert all_bands and all(b in CAP for b in all_bands)
        best = min(all_bands, key=("S", "A", "B").index)
        target = min(D(".92"), DEPLOY[best] + D(".055") * (len(all_bands) - 1))
        budget = min(available, max(D(0), eq * target - exp))
        total_weight = sum(D(str(c["capital_score"])) for c in picked)
        unspent, remaining = budget, available
        proposals = []
        for row in picked:
            band = capacity_band(row["capital_score"])
            lot_cost = D(row["raw_reference"]) * BUY * 100
            cap = eq * CAP[band]
            desired = budget * D(str(row["capital_score"])) / total_weight
            ceiling = min(desired, cap, remaining)
            lots = max(0, int((ceiling / lot_cost).to_integral_value(rounding=ROUND_FLOOR)))
            debit = lots * lot_cost
            remaining -= debit
            unspent -= debit
            proposals.append({
                "entry_id": row["entry_id"], "quantity": lots * 100,
                "first_pass_quantity": lots * 100, "water_fill_lots": 0,
                "debit": debit, "lot_debit": lot_cost, "equity_cap": cap,
                "liquidity_cap": None, "desired": desired, "band": band,
                "target_utilization": target, "batch_equity": eq, "batch_budget": budget,
            })
        rounds = 0
        while True:
            changed = False
            for proposal in proposals:
                if proposal["first_pass_quantity"] < 100:
                    continue
                lot = proposal["lot_debit"]
                if (lot > remaining or lot > unspent or
                        proposal["debit"] + lot > proposal["equity_cap"]):
                    continue
                proposal["quantity"] += 100
                proposal["water_fill_lots"] += 1
                proposal["debit"] += lot
                remaining -= lot
                unspent -= lot
                changed = True
            if not changed:
                break
            rounds += 1
        assert remaining >= 0 and unspent >= 0
        for proposal in proposals:
            assert proposal["quantity"] % 100 == 0
            assert proposal["debit"] <= proposal["equity_cap"]
            proposal["water_fill_rounds"] = rounds
            proposal["budget_unspent"] = unspent
        return proposals


def empirical_rank(current, reference):
    """SC02 exact integer domain. Missing/nonfinite abstains, never LOW."""
    if current is None or not math.isfinite(float(current)):
        return {"available": False, "low": None, "high": None,
                "numerator": None, "denominator": None, "rank": None}
    if not reference or any(not math.isfinite(float(x)) for x in reference):
        return {"available": False, "low": None, "high": None,
                "numerator": None, "denominator": None, "rank": None}
    numerator = 1 + sum(x < current for x in reference)
    denominator = len(reference) + 1
    low = 2 * numerator < denominator
    return {"available": True, "low": low, "high": not low,
            "numerator": numerator, "denominator": denominator,
            "rank": numerator / denominator}


def intelligence_state(entry_id, intelligence):
    values = intelligence.get(entry_id, {})
    result = {"intelligence_available": True}
    for head in HEADS:
        row = values.get(head, {})
        ref = row.get("training_scores", row.get("reference_scores", []))
        state = empirical_rank(row.get("score"), ref)
        name = RANK_NAMES[head]
        result[name] = state["rank"]
        result[name + "_numerator"] = state["numerator"]
        result[name + "_denominator"] = state["denominator"]
        result["LOW_" + name[1:]] = state["low"]
        result["HIGH_" + name[1:]] = state["high"]
        result[head + "_score"] = row.get("score")
        result["intelligence_available"] &= state["available"]
    return result


def shield(native_action, native_index, actual_slot, native_quantity, state):
    return bool(native_action == "ADMIT" and native_index == 3 and
                actual_slot == 3 and native_quantity >= 100 and
                state["intelligence_available"] and
                all(state["LOW_" + name[1:]] for name in RANK_NAMES.values()))


def serial_monetary(record):
    return {k: str(v) if isinstance(v, D) else v for k, v in record.items()}


def reconstruct_batch(snapshot, tables, intelligence):
    """All candidate native proposals from a causal pre-batch snapshot.

    ``snapshot`` has positions/cash/candidates/session/minute only, never books,
    protected-membership, teachers, realized data, or future source availability.
    Allocation is calculated once before shield and never changes after veto.
    """
    with localcontext() as ctx:
        ctx.prec = 28
        ctx.rounding = ROUND_HALF_EVEN
        minute, day = snapshot["minute"], snapshot["session"]
        positions = snapshot["positions"]
        cash = D(str(snapshot["cash"]))
        rows = sorted(snapshot["candidates"], key=stable_order)
        decisions, picked = [], []
        for row in rows:
            decision = {"entry_id": row["entry_id"], "session": day, "minute": minute,
                        "quantity": 0, "reason": None}
            decisions.append(decision)
            if minute >= 920:
                decision["reason"] = "CAPITAL_EOD_ENTRY_CUTOFF"
                continue
            if not row["admission"]:
                decision["reason"] = "UPWARD_BELOW_BASELINE"
                continue
            if capacity_band(row["capital_score"]) is None:
                decision["reason"] = "SCORE_INPUT_UNKNOWN"
                continue
            if any(p["symbol"] == row["symbol"] for p in positions.values()):
                decision["reason"] = "SYMBOL_ALREADY_OPEN"
                continue
            yes, why, audit = native_gate(row, len(positions) + len(picked), minute,
                                          tables[str(row["block"])])
            decision.update(audit, slot_gate_reason=why,
                            slot_gate_action="ADMIT" if yes else "REJECT")
            if not yes:
                decision["reason"] = ("SLOT_RESERVE_REJECT" if
                                      why.startswith(("SLOT2_RESERVE", "SLOT3_RESERVE")) else why)
                continue
            decision["slot_admission_index"] = len(positions) + len(picked) + 1
            picked.append((row, decision))
        assigned = []
        if picked:
            exposure = sum(p["quantity"] * D(str(p["mark"])) for p in positions.values())
            assigned = allocate([r for r, _ in picked], cash + exposure, exposure, cash,
                                [p["band"] for p in positions.values()])
        prior = 0
        native_cash = cash
        for (row, decision), allocation in zip(picked, assigned):
            decision.update(serial_monetary(allocation))
            q, debit = allocation["quantity"], allocation["debit"]
            actual_slot = len(positions) + prior + 1
            decision.update(existing_open_N=len(positions),
                            prior_native_successful_BUY_proposal_N=prior,
                            actual_planned_slot=actual_slot,
                            native_quantity=q, native_debit=str(debit),
                            native_would_fund_quantity=q, native_would_fund_debit=str(debit))
            state = intelligence_state(row["entry_id"], intelligence)
            decision.update(state)
            decision["D_veto"] = shield(decision["slot_gate_action"],
                                        decision["slot_admission_index"], actual_slot, q, state)
            success = q >= 100 and debit <= native_cash
            decision["native_successful_BUY_proposal"] = success
            decision["reason"] = "FUNDED" if success else "CASH_OR_LOT_CONSTRAINED"
            if success:
                prior += 1
                native_cash -= debit
        return {"decisions": decisions, "picked_ids": [r["entry_id"] for r, _ in picked],
                "assigned": [serial_monetary(a) for a in assigned]}


def invalidate_token(token, day, minute, positions, session_end=False):
    if token is None or not token.get("active"):
        return None
    ids = sorted(positions)
    if session_end or token["session"] != day:
        return "SESSION_END"
    if minute >= 920:
        return "CUTOFF_REACHED"
    if len(ids) < 2:
        return "OPEN_POSITION_BELOW_TWO"
    if len(ids) > 2:
        return "THIRD_BUY_SUCCESS"
    if ids != token["held_pair_ids"]:
        return "HELD_PAIR_CHANGED"
    return None


def recovery_choices(token, day, minute, positions, native_picked_ids, rows, decisions, intelligence):
    """Pure recovery filtering/order. Current source constraints only."""
    if (token is None or not token.get("active") or token["session"] != day or
            minute <= token["created_minute"] or minute >= 920 or len(positions) != 2 or
            sorted(positions) != token["held_pair_ids"] or native_picked_ids):
        return []
    lookup = {d["entry_id"]: d for d in decisions}
    eligible = []
    for order, row in enumerate(sorted(rows, key=stable_order)):
        decision = lookup[row["entry_id"]]
        if (row["entry_id"] == token["origin_entry_id"] or
                not row["admission"] or row["rank"] != "B" or
                decision.get("slot_gate_reason") != "SLOT3_RESERVE_FOR_FUTURE_QUALITY" or
                any(p["symbol"] == row["symbol"] for p in positions.values())):
            continue
        state = intelligence_state(row["entry_id"], intelligence)
        if (not state["intelligence_available"] or
                not all(state["HIGH_" + n[1:]] for n in RANK_NAMES.values())):
            continue
        eligible.append((row, decision, state, order))
    def exact_rank(state, name):
        return Fraction(state[name + "_numerator"], state[name + "_denominator"])
    eligible.sort(key=lambda x: tuple(-exact_rank(x[2], name)
                                     for name in ("rP", "r3", "rM", "r2")) + (x[3],))
    return eligible


def minute_clock(timestamp):
    value = datetime.fromisoformat(timestamp)
    return 60 * value.hour + value.minute


def valid_market(row, auction=False):
    try:
        if not row.get("lineage"):
            return False
        o, h, l, c, volume, value = [D(str(row[k])) for k in ("O", "H", "L", "C", "Vo", "Va")]
        if not all(v.is_finite() and v > 0 for v in (o, h, l, c, volume, value)):
            return False
        if not l <= min(o, c) <= max(o, c) <= h:
            return False
        return not auction or o == h == l == c
    except (KeyError, ValueError, TypeError):
        return False


def frozen_sell(book):
    exit_record = book["frozen_exit"]
    if exit_record["sell_status"] != "FILLED":
        return None
    release = minute_clock(exit_record["sell_source_assumed_available_at"])
    if release > 920:
        return None
    source = next((r for r in book["market"] if r["minute"] == exit_record["sell_minute"]), None)
    if source is None or not valid_market(source):
        return {"blocked": "FROZEN_EXIT_SOURCE_LINEAGE_BLOCKED", "release_minute": release}
    raw = source["O"] if exit_record["sell_source"] == "NEXT_ELIGIBLE_REGULAR_RAW_OPEN" else source["C"]
    price = D(str(raw)) * SELL
    assert price == D(exit_record["sell_price_decimal"])
    return {"kind": "FROZEN_EXIT_V3", "source_minute": exit_record["sell_minute"],
            "release_minute": release, "price": str(price), "lineage": source["lineage"]}


def closing_sell(book, session):
    regular = sorted((r for r in book["market"] if r.get("session") == session and
                      920 <= r["minute"] < 925 and valid_market(r)), key=lambda r: r["minute"])
    auction = [r for r in book["market"] if r.get("session") == session and
               r["minute"] == 930 and valid_market(r, True)]
    source = regular[0] if regular else auction[0] if auction else None
    if source is None:
        return None
    kind = "EOD_REGULAR" if regular else "EOD_EXACT_1530_AUCTION"
    price = D(str(source["O"] if regular else source["C"])) * SELL
    return {"kind": kind, "source_minute": source["minute"],
            "release_minute": source["minute"] + 1, "price": str(price), "lineage": source["lineage"]}


def limit_up_known(record, day, minute):
    return bool(record and record.get("status") == "LIMIT_UP_CONFIRMED" and
                record.get("authoritative_price_limit_source") and record.get("causal_exchange_status") and
                record.get("session") == day and record.get("known_minute", 9999) <= minute and
                record.get("observed_minute", 9999) <= minute)


def run_profile(arm, stream, books, tables, intelligence):
    """One separately implemented D or DR market reconstruction; no evaluator."""
    assert arm in ("D", "DR", D_PROFILE, DR_PROFILE)
    recover = arm in ("DR", DR_PROFILE)
    profile = DR_PROFILE if recover else D_PROFILE
    result = {name: [] for name in ("daily", "decisions", "trades", "curves", "intents", "token_events", "native_proposals")}
    with localcontext() as ctx:
        ctx.prec = 28
        ctx.rounding = ROUND_HALF_EVEN
        capital, chain = D(1000000), True
        for day in sorted({r["session"] for r in stream}):
            opening = capital if chain else D(1000000)
            cash, original_pool, recycled_pool, recycled_used = opening, opening, D(0), D(0)
            positions, scheduled, events = {}, defaultdict(list), defaultdict(list)
            blockers, token, peak, cash_min = [], None, 0, opening
            for row in stream:
                if row["session"] == day:
                    events[row["entry_minute"]].append(row)

            def record_token(event, minute, detail=None):
                result["token_events"].append({"session": day, "minute": minute, "event": event,
                                               "token": deepcopy(token), "detail": detail})

            def check_token(minute, session_end=False):
                nonlocal token
                reason = invalidate_token(token, day, minute, positions, session_end)
                if reason:
                    token["active"] = False
                    record_token("INVALIDATED", minute, reason)
                    token = None

            def fund(row, decision, assignment, minute, recovery=False):
                nonlocal cash, original_pool, recycled_pool, recycled_used, cash_min, peak
                q = assignment["quantity"]
                decision.update({k: str(v) if isinstance(v, D) else v for k, v in assignment.items()
                                 if k != "entry_id"})
                decision["cash_before"] = str(cash)
                if q < 100:
                    decision["reason"] = "CASH_OR_LOT_CONSTRAINED"
                    return False
                buy = D(row["raw_reference"]) * BUY
                debit = q * buy
                assert debit == assignment["debit"] and debit <= cash
                cash -= debit
                cash_min = min(cash_min, cash)
                original = min(original_pool, debit)
                original_pool -= original
                recycled = debit - original
                recycled_pool -= recycled
                recycled_used += recycled
                assert recycled_pool >= 0 and cash >= 0
                decision.update(quantity=q, reason="FUNDED", debit=str(debit),
                                recycled_cash_used=str(recycled), funded_slot=len(positions) + 1)
                if recovery:
                    decision["policy_reason"] = RECOVERY_REASON
                    decision["recovery_funded"] = True
                raw = D(row["raw_reference"])
                key = row["entry_id"]
                positions[key] = {"symbol": row["symbol"], "entry_minute": minute,
                                  "raw_reference": str(raw), "buy": buy, "quantity": q,
                                  "mark": raw, "mark_known_minute": minute,
                                  "band": row["capacity_band"], "side": "LONG", "margin": False,
                                  "intent_issued": False}
                peak = max(peak, len(positions))
                assert len(positions) <= 3 and q % 100 == 0
                assert len({p["symbol"] for p in positions.values()}) == len(positions)
                # Outcome/execution suffix consulted only after causal funding.
                book = books[key]
                positions[key]["mark_updates"] = sorted((r["minute"] + 1, D(r["C"]))
                    for r in book["market"] if r.get("session") == day and
                    r["minute"] >= minute and valid_market(r))
                positions[key]["mark_index"] = 0
                if not book["capture_complete"] or not book.get("entry_actual_source"):
                    blockers.append({"entry_id": key, "minute": minute,
                                     "reason": "MTM_SOURCE_LINEAGE_BLOCKED"})
                sell = frozen_sell(book)
                if sell:
                    assert sell["release_minute"] > minute
                    scheduled[sell["release_minute"]].append((key, sell))
                return True

            for minute in range(540, 932):
                for key, p in positions.items():
                    assert books[key]["session"] == day
                    while (p["mark_index"] < len(p["mark_updates"]) and
                           p["mark_updates"][p["mark_index"]][0] <= minute):
                        known, price = p["mark_updates"][p["mark_index"]]
                        p["mark"], p["mark_known_minute"] = price, known
                        p["mark_index"] += 1
                for key, fill in sorted(scheduled.pop(minute, []), key=lambda item: item[0]):
                    assert key in positions
                    if fill.get("blocked"):
                        blockers.append({"entry_id": key, "minute": minute, "reason": fill["blocked"]})
                        continue
                    p = positions.pop(key)
                    credit = D(fill["price"]) * p["quantity"]
                    cash += credit
                    recycled_pool += credit
                    debit = p["buy"] * p["quantity"]
                    result["trades"].append({
                        "entry_id": key, "session": day, "quantity": p["quantity"],
                        "entry_minute": p["entry_minute"], "release_minute": minute,
                        "source_minute": fill["source_minute"], "exit_kind": fill["kind"],
                        "buy_effective": str(p["buy"]), "sell_effective": fill["price"],
                        "debit": str(debit), "credit": str(credit), "pnl": str(credit - debit),
                        "net_return": float(credit / debit - 1), "lineage": fill["lineage"], "commission": 0,
                    })
                if recover:
                    check_token(minute)
                batch = sorted(events.get(minute, []), key=stable_order)
                if batch:
                    snapshot = {"session": day, "minute": minute, "cash": str(cash),
                                "positions": {k: {"symbol": p["symbol"], "quantity": p["quantity"],
                                                  "mark": str(p["mark"]), "band": p["band"]}
                                              for k, p in positions.items()}, "candidates": batch}
                    proposed = reconstruct_batch(snapshot, tables, intelligence)
                    result["native_proposals"].append({"snapshot": snapshot, **deepcopy(proposed)})
                    decision_lookup = {d["entry_id"]: d for d in proposed["decisions"]}
                    row_lookup = {r["entry_id"]: r for r in batch}
                    ds = proposed["decisions"]
                    for row in batch:
                        decision = decision_lookup[row["entry_id"]]
                        decision.update(capital_score=row["capital_score"], capacity_band=row["capacity_band"],
                                        rank=row["rank"], admission=row["admission"], ML=row["ML"],
                                        m2=row["m2"], m3=row["m3"], m5=row["m5"],
                                        held_before_batch=sorted(positions), profile=profile, primary_chain=chain)
                        if "intelligence_available" not in decision:
                            decision.update(intelligence_state(row["entry_id"], intelligence))
                        if not decision["intelligence_available"]:
                            decision["intelligence_reason"] = ABSTAIN_REASON
                    result["decisions"].extend(ds)
                    veto_ids = []
                    for key, serialized in zip(proposed["picked_ids"], proposed["assigned"]):
                        row, decision = row_lookup[key], decision_lookup[key]
                        assignment = {k: D(v) if k in ("debit", "lot_debit", "equity_cap", "desired",
                            "target_utilization", "batch_equity", "batch_budget", "budget_unspent") else v
                            for k, v in serialized.items()}
                        if decision["D_veto"]:
                            decision.update(quantity=0, reason=SHIELD_REASON, actual_debit="0",
                                            policy_reason=SHIELD_REASON)
                            decision["cash_before"] = str(cash)
                            veto_ids.append(key)
                            continue
                        fund(row, decision, assignment, minute)
                    if recover:
                        check_token(minute)
                        if veto_ids and len(positions) == 2 and minute < 920:
                            origin = veto_ids[0]
                            if token is None:
                                token = {"session": day, "created_minute": minute, "origin_entry_id": origin,
                                         "held_pair_ids": sorted(positions), "active": True}
                                record_token("CREATED", minute)
                        choices = recovery_choices(token, day, minute, positions,
                                                   proposed["picked_ids"], batch, ds, intelligence)
                        if choices:
                            row, decision, state, _ = choices[0]
                            decision.update(state, recovery_attempted=True,
                                            recovery_token_origin=token["origin_entry_id"],
                                            policy_reason="V5_SLOT3_GUARDED_WINNER_RECOVERY_ATTEMPT")
                            exposure = sum(p["quantity"] * p["mark"] for p in positions.values())
                            one = allocate([row], cash + exposure, exposure, cash,
                                           [p["band"] for p in positions.values()])[0]
                            record_token("RECOVERY_ATTEMPT", minute, row["entry_id"])
                            fund(row, decision, one, minute, True)
                            check_token(minute)
                if minute == 920:
                    for key, p in sorted(positions.items()):
                        assert not p["intent_issued"] and p["quantity"] > 0
                        p["intent_issued"] = True
                        confirmed = limit_up_known(books[key]["limit_up_authority"], day, minute)
                        result["intents"].append({"minute": 920, "side": "SELL", "quantity": p["quantity"],
                            "sor": True, "order_type": "MARKET", "condition": "DAY", "transmitted": False,
                            "entry_id": key, "session": day,
                            "limit_up_status": "LIMIT_UP_CONFIRMED" if confirmed else "LIMIT_UP_UNKNOWN"})
                        close = closing_sell(books[key], day)
                        if close:
                            scheduled[close["release_minute"]].append((key, close))
                        else:
                            blockers.append({"entry_id": key, "minute": 931,
                                "reason": "LIMIT_UP_EOD_UNEXECUTED_FAIL_CLOSED" if confirmed
                                else "EOD_UNEXECUTED_FAIL_CLOSED"})
                eq = cash + sum(p["quantity"] * p["mark"] for p in positions.values())
                assert cash >= 0 and eq > 0
                result["curves"].append({"session": day, "minute": minute, "equity": str(eq),
                    "cash": str(cash), "exposure": str(eq - cash), "utilization": float((eq - cash) / eq),
                    "concurrent": len(positions), "primary_chain": chain,
                    "known_marks": {k: p["mark_known_minute"] for k, p in positions.items()}})
            if recover:
                check_token(931, session_end=True)
            known_blocked = {b["entry_id"] for b in blockers}
            for key in positions:
                if key not in known_blocked:
                    blockers.append({"entry_id": key, "minute": 931, "reason": "EOD_UNEXECUTED_FAIL_CLOSED"})
            complete = not blockers and not positions
            daily = {"session": day,
                "status": "COMPLETE" if complete else "PORTFOLIO_MEASUREMENT_BLOCKED_EXECUTION",
                "starting_cash": str(opening), "ending_cash": str(cash) if complete else None,
                "daily_return": float(cash / opening - 1) if complete and chain else None,
                "diagnostic_daily_return": float(cash / opening - 1) if complete else None,
                "primary_chain": chain, "blockers": blockers, "open_obligations": list(positions),
                "cash_min": str(cash_min), "max_concurrent": peak, "recycled_cash_used": str(recycled_used)}
            result["daily"].append(daily)
            if chain and complete:
                capital = cash
            elif chain:
                chain = False
    return result
