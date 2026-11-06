"""Pure AD01 vacancy diagnostics; never imports or runs a portfolio engine.

``analyze_vacancy`` consumes one already saved arm.  Its third return value is
PRIVATE: it retains Entry IDs and decision/release timestamps.  The first two
return values contain aggregates only.  Rational strings (e.g. ``"3/2"``) are
exact; Decimal80 fields are explicitly display approximations.  Guard wait and
later-buy associations describe a realized account path, not causal slot or
cash-pool attribution.
"""
from collections import Counter, defaultdict
from decimal import Decimal, localcontext
from fractions import Fraction
from itertools import product
from statistics import median


SD_EXIT = "SHARP_DROP_FIRST_OBSERVED_EXIT_V0"
TIME_BANDS = ("BEFORE_1400", "1400_TO_1429", "FROM_1430")
RETURN_BANDS = (
    "L5_PLUS", "L4_5", "L3_4", "L2_3", "L1_2", "L0_1", "ZERO",
    "P0_1", "P1_2", "P2_3", "P3_4", "P4_5", "P5_PLUS", "R_UNKNOWN",
)
_ZERO = Fraction(0)
_MARKET_GRID = tuple(range(540, 690)) + tuple(range(750, 930))


def _fraction(value):
    if isinstance(value, bool):
        raise ValueError("Boolean is not an economic value")
    if isinstance(value, Fraction):
        return value
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ValueError("Nonfinite economic value")
        return Fraction(value)
    # In particular, never construct Fraction from a binary float directly.
    return Fraction(str(value))


def _exact(value):
    return None if value is None else str(_fraction(value))


def _decimal80(value):
    if value is None:
        return None
    value = _fraction(value)
    with localcontext() as context:
        context.prec = 80
        return str(Decimal(value.numerator) / Decimal(value.denominator))


def market_minutes(start, end):
    """Native market samples in [start,end), excluding lunch and close."""
    start, end = int(start), int(end)
    if end < start:
        raise ValueError("Release precedes entry")
    return sum(start <= minute < end for minute in _MARKET_GRID)


def time_band(minute):
    minute = int(minute)
    return TIME_BANDS[0] if minute < 840 else TIME_BANDS[1] if minute < 870 else TIME_BANDS[2]


def return_band(r):
    if r is None:
        return "R_UNKNOWN"
    r = _fraction(r)
    if r <= -5:
        return "L5_PLUS"
    for bound, label in ((-4, "L4_5"), (-3, "L3_4"), (-2, "L2_3"), (-1, "L1_2")):
        if r <= bound:
            return label
    if r < 0:
        return "L0_1"
    if r == 0:
        return "ZERO"
    for bound, label in ((1, "P0_1"), (2, "P1_2"), (3, "P2_3"), (4, "P3_4"), (5, "P4_5")):
        if r < bound:
            return label
    return "P5_PLUS"


def _funded_map(funded):
    values = list(funded.values()) if isinstance(funded, dict) else list(funded)
    result = {row["entry_id"]: row for row in values}
    if len(result) != len(values):
        raise ValueError("Duplicate funded Entry ID within account")
    return result


def _release_facts(trades, funded, decisions):
    """A native TRADES row is a completed full position pop and cash credit."""
    facts = defaultdict(list)
    seen = set()
    for trade in trades:
        key = trade["entry_id"]
        if key in seen:
            raise ValueError("Duplicate completed release")
        seen.add(key)
        own = funded.get(key)
        decision = decisions.get(key)
        if own is None or decision is None or decision.get("reason") != "FUNDED":
            raise ValueError("Completed release without own-arm funded decision")
        quantity = int(trade["quantity"])
        if quantity <= 0 or quantity != int(own["quantity"]) or quantity != int(decision["quantity"]):
            raise ValueError("Release is not the full funded quantity")
        if trade["session"] != own["session"] or trade["session"] != decision["session"]:
            raise ValueError("Release session mismatch")
        if _fraction(trade["credit"]) <= 0 or _fraction(trade["debit"]) <= 0:
            raise ValueError("Completed release has invalid debit/credit")
        minute = int(trade["release_minute"])
        if minute < int(trade["entry_minute"]):
            raise ValueError("Release precedes entry")
        facts[trade["session"]].append({
            "entry_id": key, "session": trade["session"], "minute": minute,
            "exit_kind": trade["exit_kind"], "is_sd": trade["exit_kind"] == SD_EXIT,
            "quantity": quantity, "credit": _exact(trade["credit"]),
        })
    for session in facts:
        facts[session].sort(key=lambda row: (row["minute"], row["entry_id"]))
    return facts


def _arrivals(window_id, arm, data, funded):
    decisions = list(data["DECISIONS"])
    by_id = {row["entry_id"]: row for row in decisions}
    if len(by_id) != len(decisions):
        raise ValueError("Duplicate arrival Entry ID within account")
    trades = {row["entry_id"]: row for row in data["TRADES"]}
    if len(trades) != len(data["TRADES"]):
        raise ValueError("Duplicate trade Entry ID within account")
    facts = _release_facts(data["TRADES"], funded, by_id)
    purchase_sequence = Counter()
    arrivals = []
    for index, decision in enumerate(decisions):
        session, minute = decision["session"], int(decision["minute"])
        releases = [row for row in facts[session] if row["minute"] <= minute]
        sd_releases = [row for row in releases if row["is_sd"]]
        normal_seen = any(not row["is_sd"] for row in releases)
        sd_seen = bool(sd_releases)
        if "sd_full_release_seen_today" in decision:
            if decision["sd_full_release_seen_today"] is not sd_seen:
                raise ValueError("Saved H SD flag differs from completed own-arm release")
            if int(decision.get("sd_full_release_count_today", len(sd_releases))) != len(sd_releases):
                raise ValueError("Saved H SD release count differs from actual trades")
        guard = arm == "H1" or (arm == "H2" and sd_seen)
        native_action = decision.get("native_gate_action", decision.get("slot_gate_action", "NOT_EVALUATED"))
        native_eligible = bool(decision.get("native_eligibility", native_action in ("ADMIT", "REJECT")))
        native_permit = native_action == "ADMIT"
        quantity = int(decision.get("quantity", 0))
        is_funded = decision.get("reason") == "FUNDED"
        own = funded.get(decision["entry_id"])
        if is_funded != (own is not None):
            raise ValueError("Funded enrichment and decision disagree")
        trade = trades.get(decision["entry_id"])
        debit = pnl = cash_lock = _ZERO
        r = None
        supplied_cash_lock = None
        if is_funded:
            if quantity != int(own["quantity"]):
                raise ValueError("Funded quantity mismatch")
            purchase_sequence[session] += 1
            debit = _fraction(own["debit"])
            if debit <= 0:
                raise ValueError("Nonpositive funded debit")
            if trade is not None:
                pnl = _fraction(trade["pnl"])
                if pnl != _fraction(trade["credit"]) - _fraction(trade["debit"]):
                    raise ValueError("Trade PnL identity failed")
                if debit != _fraction(trade["debit"]):
                    raise ValueError("Enriched debit differs from trade")
                r = pnl / debit * 100
                cash_lock = debit * market_minutes(own["entry_minute"], trade["release_minute"])
            if own.get("R") is not None and _fraction(own["R"]) != r:
                raise ValueError("Enriched exact R differs from full trade")
            if own.get("pnl") is not None and trade is not None and _fraction(own["pnl"]) != pnl:
                raise ValueError("Enriched exact PnL differs from full trade")
            if own.get("cash_minutes") is not None:
                supplied_cash_lock = _fraction(own["cash_minutes"])
        occupancy = int(decision.get("pre_decision_occupancy", len(decision.get("held_before_batch", []))))
        if occupancy not in (0, 1, 2, 3):
            raise ValueError("Occupancy outside native MAX3 domain")
        direct_reject = decision.get("reason") == "ADMISSION_QUALITY_RESERVE"
        if direct_reject and (not native_permit or not guard or decision["rank"] in ("S", "A")):
            raise ValueError("Direct guard reject violates fixed policy")
        if is_funded and guard and decision["rank"] not in ("S", "A"):
            raise ValueError("Guard-active account funded a non-SA arrival")
        arrivals.append({
            "window_id": window_id, "arm": arm, "entry_id": decision["entry_id"],
            "session": session, "minute": minute, "decision_index": index,
            "rank": decision["rank"], "occupancy": occupancy,
            "occupancy_source": "SAVED_NATIVE_GATE_AUDIT" if "pre_decision_occupancy" in decision else "ACTUAL_HELD_GATE_NOT_VISITED",
            "sd_seen": sd_seen, "normal_seen": normal_seen, "time_band": time_band(minute),
            "guard_active": guard, "native_eligible": native_eligible,
            "native_evaluated": native_action in ("ADMIT", "REJECT"),
            "native_permit": native_permit, "native_gate_reason": decision.get("native_gate_reason", decision.get("slot_gate_reason")),
            "direct_reject": direct_reject,
            "overlay_permit": native_permit and not direct_reject,
            "reason": decision.get("reason"), "funded": is_funded, "quantity": quantity,
            "funded_slot": decision.get("funded_slot"),
            "purchase_sequence": purchase_sequence[session] if is_funded else 0,
            "post_release_context": "SD_RELEASE_ALREADY_SEEN" if sd_seen else "NORMAL_EXIT_RELEASE_ALREADY_SEEN" if normal_seen else "BEFORE_ANY_EXIT_RELEASE",
            "closed": trade is not None, "R": _exact(r), "R_band": return_band(r),
            "debit": _exact(debit), "pnl": _exact(pnl) if trade is not None else None,
            "cash_lock_market_jpy_minutes": _exact(cash_lock) if trade is not None else None,
            "supplied_cash_minutes": _exact(supplied_cash_lock),
            "supplied_cash_minutes_matches_market_grid": supplied_cash_lock == cash_lock if supplied_cash_lock is not None and trade is not None else None,
            "release_minute": int(trade["release_minute"]) if trade is not None else None,
            "exit_kind": trade["exit_kind"] if trade is not None else None,
        })
    return arrivals, [row for session in sorted(facts) for row in facts[session]]


def _count(rows, predicate, unique=False):
    selected = [row for row in rows if predicate(row)]
    return len({row["entry_id"] for row in selected}) if unique else len(selected)


def _cohort_stats(rows, unique=False):
    funded = [row for row in rows if row["funded"]]
    closed = [row for row in funded if row["closed"]]
    count = lambda predicate: _count(rows, predicate, unique)
    out = {
        "arrival_N": count(lambda row: True),
        "native_eligible_N": count(lambda row: row["native_eligible"]),
        "native_gate_visited_N": count(lambda row: row["native_evaluated"]),
        "native_gate_permit_N": count(lambda row: row["native_permit"]),
        "native_gate_reject_N": count(lambda row: row["native_evaluated"] and not row["native_permit"]),
        "guard_active_arrival_N": count(lambda row: row["guard_active"]),
        "guard_active_native_permit_N": count(lambda row: row["guard_active"] and row["native_permit"]),
        "added_guard_reject_N": count(lambda row: row["direct_reject"]),
        "overlay_permit_N": count(lambda row: row["overlay_permit"]),
        "funded_N": count(lambda row: row["funded"]),
        "closed_N": count(lambda row: row["closed"]),
        "cash_or_lot_reject_N": count(lambda row: row["reason"] == "CASH_OR_LOT_CONSTRAINED"),
        "native_permit_quantity_zero_N": count(lambda row: row["native_permit"] and row["quantity"] == 0),
        "overlay_permit_sub100_N": count(lambda row: row["overlay_permit"] and row["quantity"] < 100),
        "first_entry_purchase_N": count(lambda row: row["funded"] and row["purchase_sequence"] == 1),
        "same_session_later_purchase_N": count(lambda row: row["funded"] and row["purchase_sequence"] > 1),
        "funded_SD_post_N": count(lambda row: row["funded"] and row["sd_seen"]),
        "funded_ordinary_exit_post_before_any_SD_N": count(lambda row: row["funded"] and row["normal_seen"] and not row["sd_seen"]),
        "funded_ordinary_exit_already_seen_including_SD_post_N": count(lambda row: row["funded"] and row["normal_seen"]),
        "ALL_MINUS_N": count(lambda row: row["closed"] and _fraction(row["R"]) < 0),
        "ALL_PLUS_N": count(lambda row: row["closed"] and _fraction(row["R"]) > 0),
        "ZERO_N": count(lambda row: row["closed"] and _fraction(row["R"]) == 0),
        "R_UNKNOWN_N": count(lambda row: row["funded"] and row["R"] is None),
    }
    for band in RETURN_BANDS:
        out[band + "_N"] = count(lambda row, band=band: row["funded"] and row["R_band"] == band)
    reasons = sorted({row["reason"] or "UNKNOWN" for row in rows})
    out["final_reason_counts"] = {
        reason: count(lambda row, reason=reason: (row["reason"] or "UNKNOWN") == reason)
        for reason in reasons
    }
    out["occupancy_source_counts"] = {
        source: count(lambda row, source=source: row["occupancy_source"] == source)
        for source in sorted({row["occupancy_source"] for row in rows})
    }
    numeric = {
        "quantity": sum(row["quantity"] for row in funded),
        "BUY_debit_jpy": _exact(sum((_fraction(row["debit"]) for row in funded), _ZERO)),
        "positive_PnL_jpy": _exact(sum((_fraction(row["pnl"]) for row in closed if _fraction(row["pnl"]) > 0), _ZERO)),
        "gross_loss_jpy": _exact(-sum((_fraction(row["pnl"]) for row in closed if _fraction(row["pnl"]) < 0), _ZERO)),
        "net_PnL_jpy": _exact(sum((_fraction(row["pnl"]) for row in closed), _ZERO)),
        "capital_lock_market_jpy_minutes": _exact(sum((_fraction(row["cash_lock_market_jpy_minutes"]) for row in closed), _ZERO)),
    }
    out.update({key: None for key in numeric} if unique else numeric)
    out["R_median_pct_exact"] = _exact(median([_fraction(row["R"]) for row in closed])) if closed and not unique else None
    for bound in range(1, 6):
        out[f"R_LE_MINUS{bound}_N"] = count(lambda row, bound=bound: row["closed"] and _fraction(row["R"]) <= -bound)
        out[f"R_GE_PLUS{bound}_N"] = count(lambda row, bound=bound: row["closed"] and _fraction(row["R"]) >= bound)
        out[f"R_LE_MINUS{bound}_gross_loss_jpy"] = None if unique else _exact(-sum((_fraction(row["pnl"]) for row in closed if _fraction(row["R"]) <= -bound), _ZERO))
        out[f"R_GE_PLUS{bound}_PnL_jpy"] = None if unique else _exact(sum((_fraction(row["pnl"]) for row in closed if _fraction(row["R"]) >= bound), _ZERO))
    if unique:
        out["unique_money_status"] = "UNDEFINED_ACCOUNT_QUANTITIES_DIFFER_NO_ACCOUNT_SELECTED"
    return out


def _reason_rows(window_id, arm, arrivals, unique=False):
    groups = defaultdict(list)
    for row in arrivals:
        groups[(row["rank"], row["occupancy"], row["sd_seen"], row["time_band"])].append(row)
    # Required native S/A/B x occupancy 0/1/2 x pre/post SD x time grid,
    # including zero-support cells. C and occupancy3 observed cells stay visible.
    dimensions = set(product(("S", "A", "B"), (0, 1, 2), (False, True), TIME_BANDS)) | set(groups)
    result = []
    for rank, occupancy, sd_seen, clock in sorted(dimensions):
        rows = groups[(rank, occupancy, sd_seen, clock)]
        result.append({
            "window_id": window_id, "arm": arm, "row_kind": "VACANCY_CONTEXT",
            "count_scope": "UNIQUE_ENTRY_WITHIN_CONTEXT_GROUP" if unique else "ACCOUNT_ARRIVAL_RECORDS",
            "native_rank": rank, "native_pre_decision_occupancy": occupancy,
            "own_confirmed_SD_release_seen_today": sd_seen, "time_band": clock,
            "context_support": "REQUIRED_NATIVE_VACANCY_GRID" if rank in ("S", "A", "B") and occupancy < 3 else "OTHER_OBSERVED_NATIVE_CONTEXT",
            **_cohort_stats(rows, unique),
        })
    return result


def _wait_records(arrivals, session_ends, completed_sessions):
    by_session = defaultdict(list)
    for row in arrivals:
        by_session[row["session"]].append(row)
    records = []
    for row in arrivals:
        if not row["direct_reject"]:
            continue
        # A later original decision in the same batch is a natural later arrival.
        later = [candidate for candidate in by_session[row["session"]]
                 if (candidate["minute"], candidate["decision_index"]) > (row["minute"], row["decision_index"])]
        later.sort(key=lambda candidate: (candidate["minute"], candidate["decision_index"]))
        eligible_sa = next((candidate for candidate in later if candidate["rank"] in ("S", "A") and candidate["native_eligible"] and candidate["native_permit"]), None)
        later_buy = next((candidate for candidate in later if candidate["funded"]), None)
        end = session_ends.get(row["session"], 930)
        complete = row["session"] in completed_sessions
        records.append({
            "window_id": row["window_id"], "arm": row["arm"], "entry_id": row["entry_id"],
            "session": row["session"], "reject_minute": row["minute"], "decision_index": row["decision_index"],
            "rank": row["rank"], "occupancy": row["occupancy"], "sd_seen": row["sd_seen"], "time_band": row["time_band"],
            "first_later_native_permitted_SA_entry_id": eligible_sa["entry_id"] if eligible_sa else None,
            "first_later_native_permitted_SA_minute": eligible_sa["minute"] if eligible_sa else None,
            "wait_to_first_native_permitted_SA_market_minutes": market_minutes(row["minute"], eligible_sa["minute"]) if eligible_sa else None,
            "no_later_native_permitted_SA_until_observed_session_end": eligible_sa is None,
            "first_later_bought_entry_id": later_buy["entry_id"] if later_buy else None,
            "first_later_buy_minute": later_buy["minute"] if later_buy else None,
            "wait_to_later_buy_market_minutes": market_minutes(row["minute"], later_buy["minute"]) if later_buy else None,
            "no_later_buy_until_observed_session_end": later_buy is None,
            "session_end_complete": complete,
            "no_later_buy_until_complete_session_end": complete and later_buy is None,
            "no_later_native_permitted_SA_until_complete_session_end": complete and eligible_sa is None,
            "remaining_observed_market_minutes": market_minutes(row["minute"], max(row["minute"], end)),
            "description_status": "REALIZED_SEQUENCE_ASSOCIATION_NOT_CAUSAL_SLOT_ATTRIBUTION",
        })
    return records


def _waiting_stats(records, unique=False):
    count = lambda predicate: _count(records, predicate, unique)
    out = {
        "direct_reject_wait_observation_N": count(lambda row: True),
        "reject_followed_by_native_permitted_SA_N": count(lambda row: row["first_later_native_permitted_SA_entry_id"] is not None),
        "reject_no_later_native_permitted_SA_N": count(lambda row: row["first_later_native_permitted_SA_entry_id"] is None),
        "reject_followed_by_later_buy_N": count(lambda row: row["first_later_bought_entry_id"] is not None),
        "reject_no_later_buy_until_observed_session_end_N": count(lambda row: row["first_later_bought_entry_id"] is None),
        "reject_no_later_buy_until_complete_session_end_N": count(lambda row: row["no_later_buy_until_complete_session_end"]),
        "reject_no_later_native_permitted_SA_until_complete_session_end_N": count(lambda row: row["no_later_native_permitted_SA_until_complete_session_end"]),
        "wait_observation_session_end_censored_N": count(lambda row: not row["session_end_complete"]),
        "wait_association_status": "DESCRIPTIVE_SAME_SESSION_SUBSEQUENT_DECISIONS_NOT_CAUSAL",
    }
    for metric in ("wait_to_first_native_permitted_SA_market_minutes", "wait_to_later_buy_market_minutes"):
        values = [row[metric] for row in records if row[metric] is not None]
        out[metric + "_sum"] = sum(values) if not unique else None
        out[metric + "_median_exact"] = _exact(median(values)) if values and not unique else None
        out[metric + "_max"] = max(values) if values and not unique else None
    out["no_later_buy_remaining_market_minutes_sum"] = sum(row["remaining_observed_market_minutes"] for row in records if row["first_later_bought_entry_id"] is None) if not unique else None
    if unique:
        out["unique_wait_status"] = "COUNTS_ANY_MATCHING_ACCOUNT_CONTEXT_WAIT_DURATION_UNDEFINED"
    return out


def _capital_rows(window_id, arm, arrivals, curves, releases, waits, result, unique=False):
    samples = [row for row in curves if int(row["minute"]) in _MARKET_GRID]
    out = {
        "window_id": window_id, "arm": arm, "row_kind": "CAPITAL_WINDOW",
        "capital_context": "ALL", "count_scope": "UNIQUE_ENTRY" if unique else "ACCOUNT_PATHS",
        "market_time_grid": "540<=minute<690 OR 750<=minute<930;330 samples/session",
        **_cohort_stats(arrivals, unique), **_waiting_stats(waits, unique),
    }
    if unique:
        out.update(market_samples_N=None, occupancy_market_minutes=None,
                   cash_ratio_equity_weighted_mean_exact=None, utilization_equity_weighted_mean_exact=None,
                   cash_ratio_arithmetic_mean_decimal80=None, utilization_arithmetic_mean_decimal80=None,
                   cash_ratio_median_exact=None, cumulative_SELL_credit_jpy=None,
                   round_trip_turnover_jpy=None, market_time_status="UNDEFINED_OVERLAPPING_ACCOUNT_STATES")
        out["cumulative_BUY_debit_jpy"] = None
        out["SHARP_DROP_full_release_N"] = len({(row["entry_id"], row["session"], row["minute"]) for row in releases if row["is_sd"]})
        out["ordinary_full_release_N"] = len({(row["entry_id"], row["session"], row["minute"]) for row in releases if not row["is_sd"]})
    else:
        ratios = [_fraction(row["cash"]) / _fraction(row["equity"]) for row in samples]
        equity_sum = sum((_fraction(row["equity"]) for row in samples), _ZERO)
        cash_sum = sum((_fraction(row["cash"]) for row in samples), _ZERO)
        cash_weighted = cash_sum / equity_sum if equity_sum else None
        with localcontext() as context:
            context.prec = 80
            arithmetic = (sum((Decimal(value.numerator) / Decimal(value.denominator) for value in ratios), Decimal(0)) / Decimal(len(ratios))) if ratios else None
            utilization = Decimal(1) - arithmetic if arithmetic is not None else None
        occupancy = Counter(int(row["concurrent"]) for row in samples)
        credit = sum((_fraction(row["credit"]) for row in releases), _ZERO)
        debit = sum((_fraction(row["debit"]) for row in arrivals if row["funded"]), _ZERO)
        sessions = {row["session"] for row in samples}
        expected_sessions = len(result.get("planned_sessions", result.get("daily_series", sessions)))
        out.update({
            "market_samples_N": len(samples), "expected_market_samples_N": 330 * expected_sessions,
            "market_time_status": "COMPLETE_NATIVE_GRID" if len(samples) == 330 * expected_sessions else "PARTIAL_NATIVE_GRID",
            "occupancy_market_minutes": {str(occupancy_n): occupancy[occupancy_n] for occupancy_n in range(4)},
            "cash_ratio_equity_weighted_mean_exact": _exact(cash_weighted),
            "utilization_equity_weighted_mean_exact": _exact(1 - cash_weighted) if cash_weighted is not None else None,
            "cash_ratio_arithmetic_mean_decimal80": str(arithmetic) if arithmetic is not None else None,
            "utilization_arithmetic_mean_decimal80": str(utilization) if utilization is not None else None,
            "arithmetic_ratio_status": "DECIMAL80_DISPLAY_ONLY_NOT_USED_FOR_GATES",
            "cash_ratio_median_exact": _exact(median(ratios)) if ratios else None,
            "market_cash_sum_jpy_minutes": _exact(cash_sum), "market_equity_sum_jpy_minutes": _exact(equity_sum),
            "SHARP_DROP_full_release_N": sum(row["is_sd"] for row in releases),
            "ordinary_full_release_N": sum(not row["is_sd"] for row in releases),
            "cumulative_SELL_credit_jpy": _exact(credit), "round_trip_turnover_jpy": _exact(debit + credit),
            "cumulative_BUY_debit_jpy": _exact(debit),
            "supplied_cash_minutes_market_grid_mismatch_N": sum(row["supplied_cash_minutes_matches_market_grid"] is False for row in arrivals),
        })
    rows = [out]
    contexts = (
        ("FIRST_ENTRY_PURCHASE", lambda row: row["funded"] and row["purchase_sequence"] == 1),
        ("SAME_SESSION_LATER_PURCHASE", lambda row: row["funded"] and row["purchase_sequence"] > 1),
        ("SD_RELEASE_ALREADY_SEEN", lambda row: row["sd_seen"]),
        ("NORMAL_EXIT_RELEASE_ALREADY_SEEN_BEFORE_ANY_SD", lambda row: row["normal_seen"] and not row["sd_seen"]),
        ("BEFORE_ANY_EXIT_RELEASE", lambda row: not row["normal_seen"] and not row["sd_seen"]),
    )
    for name, predicate in contexts:
        cohort = [row for row in arrivals if predicate(row)]
        rows.append({"window_id": window_id, "arm": arm, "row_kind": "CAPITAL_ENTRY_CONTEXT",
                     "capital_context": name, "count_scope": out["count_scope"], **_cohort_stats(cohort, unique)})
    return rows


def analyze_vacancy(window_id, arm, data, funded):
    """Return (public reason rows, public capital rows, PRIVATE examples).

    data: result plus DECISIONS/TRADES/CURVE/INTENTS saved rows.  funded is a
    mapping or iterable of enriched funded rows; R is percent, never a ratio.
    E0's state is derived only from TRADES.  H state is independently verified
    against exactly those own-arm completed releases.  INTENTS are not read.
    """
    if arm not in ("E0", "H1", "H2"):
        raise ValueError("Unknown fixed AD01 arm")
    funded = _funded_map(funded)
    result = data["result"]
    arrivals, releases = _arrivals(window_id, arm, data, funded)
    curves = list(data["CURVE"])
    session_ends = {}
    for curve in curves:
        session_ends[curve["session"]] = max(session_ends.get(curve["session"], 0), min(int(curve["minute"]) + 1, 930))
    completed_sessions = {row["session"] for row in result.get("daily_series", [])
                          if row.get("status") == "COMPLETE" and not row.get("open_obligations")}
    if result.get("status") == "COMPLETE" and not result.get("daily_series"):
        completed_sessions.update(result.get("planned_sessions", []))
    waits = _wait_records(arrivals, session_ends, completed_sessions)
    reasons = _reason_rows(window_id, arm, arrivals)
    capitals = _capital_rows(window_id, arm, arrivals, curves, releases, waits, result)
    return reasons, capitals, {
        "privacy": "PRIVATE_ENTRY_IDS_SESSION_TIMESTAMPS_ACCOUNT_PATHS",
        "window_id": window_id, "arm": arm,
        "arrival_records": arrivals, "confirmed_release_records": releases,
        "direct_rejection_wait_records": waits,
        "waiting_definition": "First later original native-permitted S/A arrival and first later funded Entry in same session; same-batch later order has zero market-minute wait. No causal cash/slot assignment.",
        "uncompleted_session_wait_status": "Observed-end censoring; session-end waiting is not established unless original result session is COMPLETE.",
        # Aggregate helper reuses saved curves without choosing a representative
        # account for overlapping Entry IDs. This whole object stays private.
        "market_curve_records": [row for row in curves if int(row["minute"]) in _MARKET_GRID],
        "planned_session_N": len(result.get("planned_sessions", result.get("daily_series", []))),
    }


def aggregate_vacancy(analyses, scope="PRIMARY9_ACCOUNT_SUM", unique=False):
    """Combine analyze_vacancy triples from ONE arm without rerunning data.

    ``unique=True`` counts exact Entry IDs within each context. The same Entry
    may belong to several account contexts, so context rows are not additive.
    Money, quantities, market time and wait durations remain undefined there.
    """
    private = [analysis[2] for analysis in analyses]
    arms = {value["arm"] for value in private}
    if len(arms) != 1:
        raise ValueError("Aggregate must contain exactly one arm")
    if len({value["window_id"] for value in private}) != len(private):
        raise ValueError("Duplicate account window in aggregate")
    arm = next(iter(arms))
    arrivals = [row for value in private for row in value["arrival_records"]]
    releases = [row for value in private for row in value["confirmed_release_records"]]
    waits = [row for value in private for row in value["direct_rejection_wait_records"]]
    curves = [row for value in private for row in value["market_curve_records"]]
    # One immutable Entry must preserve its price/EXIT/cost return across sizes.
    r_by_id = defaultdict(set)
    for row in arrivals:
        if row["closed"]:
            r_by_id[row["entry_id"]].add(row["R"])
    if any(len(values) != 1 for values in r_by_id.values()):
        raise ValueError("Same Entry R changed across overlapping accounts")
    expected = sum(value["planned_session_N"] for value in private)
    reasons = _reason_rows(scope, arm, arrivals, unique)
    capitals = _capital_rows(scope, arm, arrivals, curves, releases, waits,
                             {"planned_sessions": [None] * expected}, unique)
    return reasons, capitals, {
        "privacy": "PRIVATE_AGGREGATE_CARRIER", "window_id": scope, "arm": arm,
        "account_window_N": len(private), "unique_entry_N": len({row["entry_id"] for row in arrivals}),
        "unique_funded_entry_N": len({row["entry_id"] for row in arrivals if row["funded"]}),
        "context_scope_note": "Unique context groups can overlap; monetary/account-time aggregation uses account sum only.",
    }
