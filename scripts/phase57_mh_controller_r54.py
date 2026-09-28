"""Experimental R54 EXIT controller. It never reads a future market reference.

Two finite policies share the same fixed D forecasts and differ only in one
non-renewable active-minute grace allowance. No live/paper order is permitted.
"""
from __future__ import annotations

import dataclasses
import math
from functools import lru_cache

from scripts import phase57_exit_execution_contract_v1 as execution

POLICIES = {"MH_WAIT15": 15, "MH_WAIT5": 5}
SHORT = (1, 5)
LONG = (15, 30, 60, "EOD")
SAFETY = execution.SAFETY


@lru_cache(maxsize=128)
def endpoints_for(day: str) -> tuple[int, ...]:
    return execution.decision_endpoints(day, execution.continuous_minutes(day)[0])


def deadline_after(day: str, now: int, budget: int) -> int:
    endpoints = endpoints_for(day)
    if now not in endpoints:
        raise ValueError("NOT_A_DECISION_ENDPOINT")
    pos = endpoints.index(now)
    return endpoints[min(len(endpoints) - 1, pos + budget)]


def previous_decision(day: str, now: int) -> int | None:
    ends = endpoints_for(day)
    idx = ends.index(now)
    return ends[idx - 1] if idx else None


def good_prediction(values, horizon):
    v = values.get(horizon)
    if not isinstance(v, dict):
        return False
    return all(isinstance(v.get(k), (int, float)) and math.isfinite(v[k])
               for k in ("mean", "q10", "q90"))


@dataclasses.dataclass
class State:
    last_now: int | None = None
    last_short_set: tuple = ()
    neg_count: int = 0
    grace_used: bool = False
    grace_active: bool = False
    grace_deadline: int | None = None
    grace_origin: int | None = None
    grace_anchor_target: int | None = None
    pending_intent: bool = False


class Controller:
    def __init__(self, policy: str, day: str):
        if policy not in POLICIES:
            raise ValueError("UNKNOWN_FROZEN_POLICY")
        self.policy = policy
        self.day = day
        self.state = State()

    def intent_result(self, confirmed: bool) -> None:
        s = self.state
        if not s.pending_intent:
            raise ValueError("INTENT_NOT_PENDING")
        s.pending_intent = False
        if not confirmed:
            s.neg_count = 0
            s.grace_active = False
        # On a confirmed fill the caller removes this controller/position.

    def decide(self, now: int, forecasts: dict, targets: dict,
               *, fresh: bool, current_return: float | None) -> dict:
        s = self.state
        if s.pending_intent:
            raise ValueError("PENDING_FILL_MUST_RESOLVE_FIRST")
        if s.last_now is not None and now <= s.last_now:
            raise ValueError("DUPLICATE_OR_REVERSED_CHECKPOINT")
        # Existing scheduled terminal decision outranks any model and any grace.
        if now == 925:
            s.last_now = now
            return {"action": "FORCE_TERMINAL", "reason": "FROZEN_TERMINAL", "state": dataclasses.asdict(s)}
        calendar_short = tuple(h for h in SHORT if targets.get(h) is not None)
        if s.last_now is not None and (previous_decision(self.day, now) != s.last_now
                                       or calendar_short != s.last_short_set):
            s.neg_count = 0
            s.grace_active = False
        s.last_now = now
        s.last_short_set = calendar_short

        def result(action, reason, **extra):
            return {"action": action, "reason": reason, **extra, "state": dataclasses.asdict(s)}

        if (not fresh or current_return is None
                or not isinstance(current_return, (int, float))
                or not math.isfinite(current_return) or not calendar_short
                or any(not good_prediction(forecasts, h) for h in calendar_short)):
            s.neg_count = 0
            s.grace_active = False
            return result("HOLD", "DATA_UNAVAILABLE")
        if not all(forecasts[h]["mean"] < 0 for h in calendar_short):
            s.neg_count = 0
            if s.grace_deadline is not None and now >= s.grace_deadline:
                s.grace_active = False
            return result("HOLD", "SHORT_NOT_NEGATIVE")
        s.neg_count += 1
        if s.neg_count < 2:
            return result("HOLD", "NEGATIVE_CONFIRMATION_WAIT")

        # The long horizon's selected target is fixed at grant and can only shrink.
        eligible = [h for h in LONG if targets.get(h) is not None
                    and good_prediction(forecasts, h)
                    and forecasts[h]["mean"] > 0 and forecasts[h]["q10"] >= 0]
        anchor = (sorted(eligible, key=lambda h: (-forecasts[h]["mean"],
                                                  targets[h], str(h)))[0] if eligible else None)
        if s.grace_active and s.grace_deadline is not None and now < s.grace_deadline and anchor is not None:
            return result("HOLD", "BOUNDED_LONG_RECOVERY_WAIT", anchor=anchor)
        if not s.grace_used and anchor is not None:
            deadline = min(deadline_after(self.day, now, POLICIES[self.policy]),
                           targets[anchor], 925)
            if deadline > now:
                s.grace_used = True
                s.grace_active = True
                s.grace_deadline = deadline
                s.grace_origin = now
                s.grace_anchor_target = targets[anchor]
                return result("HOLD", "BOUNDED_LONG_RECOVERY_WAIT", anchor=anchor)
        s.grace_active = False
        s.pending_intent = True
        return result("SELL_INTENT", "PERSISTENT_SHORT_DISADVANTAGE")
