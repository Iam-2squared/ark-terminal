"""R24 NEW EXIT decision/execution geometry; no policy, evaluator or routing.

All returned prices are historical references for a future Development replay.
Nothing in this module sends an order or authorizes live/paper execution.
"""
from __future__ import annotations

import datetime as dt
import math


TERMINAL_AUCTION_MINUTE = 930
SELL_COST_PP = 0.05
COST_STRESS_PP = (0.10, 0.20)
SAFETY = dict.fromkeys((
    "executionAllowed", "brokerWriteAllowed", "excelOrderWriteAllowed",
    "rssOrderFunctionAllowed", "liveTradingAllowed", "paperTradingAllowed",
    "automaticPromotionAllowed", "productionUpdateAllowed", "transmitted",
), False)


def require(ok: bool, reason: str) -> None:
    if not ok:
        raise ValueError(reason)


def finite_price(value) -> bool:
    return (isinstance(value, (int, float)) and not isinstance(value, bool)
            and math.isfinite(value) and value > 0)


def continuous_minutes(day: str) -> tuple[int, ...]:
    parsed = dt.date.fromisoformat(day)
    require(parsed >= dt.date(2024, 11, 5), "CONTRACT_ONLY_FOR_EXTENDED_2025_SESSION")
    return tuple(range(540, 690)) + tuple(range(750, 925))


def decision_endpoints(day: str, entry_minute: int) -> tuple[int, ...]:
    minutes = continuous_minutes(day)
    require(entry_minute in minutes, "ENTRY_OUTSIDE_CONTINUOUS_SESSION")
    return tuple(m + 1 for m in minutes if m >= entry_minute)


def next_execution_start(day: str, decision_now: int) -> int | None:
    """Exact next scheduled continuous OPEN; lunch is a wall-time jump."""
    endpoints = {m + 1 for m in continuous_minutes(day)}
    require(decision_now in endpoints, "NOT_A_DECISION_ENDPOINT")
    return next((m for m in continuous_minutes(day) if m >= decision_now), None)


def ordinary_execution_reference(day: str, decision_now: int, observed_rows) -> dict:
    """Resolve only the exact scheduled next OPEN; never search forward/stale-fill."""
    start = next_execution_start(day, decision_now)
    if start is None:
        return {
            "status": "NO_CONTINUOUS_REFERENCE_PROCEED_TO_TERMINAL",
            "decisionNow": decision_now,
            "referenceStart": None,
            "price": None,
            "queuedIntent": False,
        }
    exact = [row for row in observed_rows if int(row[0]) == row[0] == start]
    require(len(exact) <= 1, "DUPLICATE_EXECUTION_REFERENCE")
    if not exact:
        return {
            "status": "MISSING_EXECUTION_REFERENCE",
            "decisionNow": decision_now,
            "referenceStart": start,
            "price": None,
            "queuedIntent": False,
        }
    price = exact[0][1]
    require(finite_price(price), "INVALID_EXECUTION_OPEN")
    return {
        "status": "RESOLVED_NEXT_SCHEDULED_OPEN",
        "decisionNow": decision_now,
        "referenceStart": start,
        "price": float(price),
        "queuedIntent": False,
    }


def terminal_execution_reference(observed_rows) -> dict:
    """15:30 endpoint-stamped auction only; missing remains unresolved/censored."""
    exact = [row for row in observed_rows if int(row[0]) == row[0] == TERMINAL_AUCTION_MINUTE]
    require(len(exact) <= 1, "DUPLICATE_TERMINAL_REFERENCE")
    if not exact:
        return {
            "status": "UNRESOLVED_TERMINAL_MISSING_AUCTION_REFERENCE",
            "referenceMinute": TERMINAL_AUCTION_MINUTE,
            "price": None,
            "censored": True,
        }
    row = exact[0]
    require(len(row) == 7, "TERMINAL_ROW_WIDTH")
    require(all(finite_price(x) for x in row[1:5]), "INVALID_TERMINAL_OHLC")
    require(max(row[1:5]) == min(row[1:5]), "AUCTION_NOT_SINGLE_PRICE")
    return {
        "status": "RESOLVED_TERMINAL_AUCTION",
        "referenceMinute": TERMINAL_AUCTION_MINUTE,
        "price": float(row[1]),
        "censored": False,
    }


def active_minutes(day: str, start: int, end: int) -> int:
    require(end >= start, "REVERSED_TIME")
    return sum(start <= minute < end for minute in continuous_minutes(day))


def contract() -> dict:
    return {
        "schemaVersion": "phase57-exit-decision-execution-terminal-r24",
        "decisionCadence": "EVERY_COMPLETED_CONTINUOUS_1M_ENDPOINT_AFTER_FROZEN_ENTRY",
        "decisionNow": "BAR_START_PLUS_1_AND_INPUT_KNOWN_AT_NOT_AFTER_NOW",
        "execution": {
            "ordinary": "EXACT_NEXT_SCHEDULED_CONTINUOUS_BAR_OPEN",
            "delay": "ONE_DECISION_BOUNDARY;_11_30_DECISION_TO_12_30_OPEN_ACROSS_LUNCH",
            "missing": "NO_FILL_NO_FORWARD_SEARCH_NO_STALE_REFERENCE_REEVALUATE_NEXT_CHECKPOINT",
            "intentPersistence": "NOT_QUEUED",
        },
        "session": {
            "continuous": "09:00-11:29_AND_12:30-15:24_BAR_STARTS",
            "lastDecisionNow": 925,
            "overnightAllowed": False,
            "terminal": "FORCED_15:30_ENDPOINT_STAMPED_AUCTION_AT_MINUTE_930",
            "missingTerminal": "UNRESOLVED_EXIT_AND_CENSORED_NO_15:25_CLOSE_SUBSTITUTE",
        },
        "time": {
            "active": "COUNT_SCHEDULED_CONTINUOUS_MINUTES_LUNCH_EXCLUDED",
            "wall": "NOW_MINUS_ENTRY_MINUTE_LUNCH_INCLUDED",
            "bothReported": True,
        },
        "ownership": {
            "entryBarOwned": True,
            "exitOpenBarHighLowOwned": False,
            "runningHighLow": "COMPLETED_OWNED_BARS_STRICTLY_BEFORE_EXIT_REFERENCE",
            "equalPeakTie": "LATEST_CONFIRMATION",
            "intrabarOrder": "UNKNOWN_NEVER_INFERRED",
            "futureHigh": "EVALUATOR_MISSED_OPPORTUNITY_NOT_OWNED_GIVEBACK",
            "incompleteOwnedPath": "OBSERVED_EXTREMA_ONLY_CERTIFIED_GIVEBACK_NULL",
        },
        "priceAndCost": {
            "entry": "UNCHANGED_FROZEN_EFFECTIVE_ENTRY_ALREADY_CONTAINS_BUY_5BPS",
            "exitGross": "RAW_EXACT_EXECUTION_REFERENCE",
            "primarySellCostPp": SELL_COST_PP,
            "stressSellCostPp": list(COST_STRESS_PP),
            "noDoubleEntryCost": True,
        },
        "missingTaxonomy": [
            "NO_ENTRY", "NO_EXIT_INTENT", "MISSING_EXECUTION_REFERENCE",
            "STALE_OBSERVATION_NOT_EXECUTION_REFERENCE", "NO_TRADE_NOT_PROVEN",
            "INCOMPLETE_OWNED_PATH", "UNRESOLVED_TERMINAL_EXIT",
        ],
        "availabilityCaveat": "HISTORICAL_BAR_END_PROXY_NOT_PROVIDER_PUBLICATION_TIME",
        "legacyInherited": {"entry30MinuteDeadline": False, "Fixed12": False,
                            "CandidateAPlus3Plus1": False},
        "safety": SAFETY,
    }


if __name__ == "__main__":
    import json
    print(json.dumps(contract(), sort_keys=True, separators=(",", ":")))
