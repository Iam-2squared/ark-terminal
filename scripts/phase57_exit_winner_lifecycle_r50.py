"""Frozen R50 causal winner-lifecycle decision boundary."""
from __future__ import annotations
from copy import deepcopy
from functools import lru_cache
import hashlib, json, math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = ROOT / "docs/evidence/phase57-comprehensive-exit-v1/R50_PRECOMMIT.json"
PROTOCOL_SHA256 = "011b4959bf7cd343694f44e2986d13d87c07b6fa238dc326f5273e86885afe18"
FACTS = ("certifiedMfePct", "certifiedGivebackPp", "timeSincePeak", "barsHeld",
         "currentReturnPct", "momentum5Pct", "weakRun", "stateRecovery", "failedRecovery",
         "signalTrueN", "signalFalseN", "signalLossN", "signalRecoveryN", "newPeak")
CANDIDATES = ("R50_A_LIFECYCLE", "R50_B_FAILED_RECOVERY")

def require(ok, reason):
    if not ok:
        raise ValueError(reason)

def finite(v):
    return type(v) in (int, float) and math.isfinite(v)

@lru_cache(maxsize=1)
def protocol():
    raw = PROTOCOL_PATH.read_bytes()
    require(hashlib.sha256(raw).hexdigest() == PROTOCOL_SHA256, "R50_PROTOCOL_HASH")
    p = json.loads(raw)
    require(p["status"] == "FROZEN_BEFORE_PERFORMANCE", "R50_PROTOCOL_STATUS")
    require(p["candidateCount"] == 2, "R50_CANDIDATE_COUNT")
    require(tuple(x["candidateId"] for x in p["candidates"]) == CANDIDATES, "R50_CANDIDATES")
    require(not p["performanceBeforeFreezeAllowed"] and not p["candidateAfterPerformanceAllowed"], "R50_FREEZE")
    require(all(v is False for v in p["safety"].values()), "R50_SAFETY")
    return p

def load_protocol():
    return deepcopy(protocol())

def initial_state():
    return {"lifecycle": "UNARMED", "lastNow": None, "deteriorationCount": 0,
            "recoveryCount": 0, "armedEver": False}

def _ge(v, k, x): return finite(v.get(k)) and v[k] >= x
def _le(v, k, x): return finite(v.get(k)) and v[k] <= x

def validate_envelope(envelope):
    require(type(envelope) is dict and set(envelope) == {"now", "maxKnownAt", "maxBarEnd", "fresh", "values"}, "R50_ENVELOPE")
    now = envelope["now"]
    require(type(now) is int and type(envelope["fresh"]) is bool, "R50_ENVELOPE_TYPES")
    require(type(envelope["maxKnownAt"]) is int and type(envelope["maxBarEnd"]) is int, "R50_KNOWN_TYPES")
    require(envelope["maxKnownAt"] <= now and envelope["maxBarEnd"] <= now, "R50_FUTURE_FACT")
    require(type(envelope["values"]) is dict and set(envelope["values"]) == set(FACTS), "R50_FACT_ALLOWLIST")
    require(all(x is None or finite(x) for x in envelope["values"].values()), "R50_NONFINITE")
    return envelope["values"]

def intent(envelope, previous_state, candidate, *, terminal=False):
    p = protocol(); v = validate_envelope(envelope); now = envelope["now"]
    require(candidate in CANDIDATES, "R50_UNKNOWN_CANDIDATE")
    require(type(previous_state) is dict and set(previous_state) == set(initial_state()), "R50_STATE")
    s = deepcopy(previous_state)
    require(s["lastNow"] is None or s["lastNow"] < now, "R50_NONMONOTONE")
    s["lastNow"] = now
    if terminal:
        s["lifecycle"] = "TERMINAL"
        return {"action": "FORCE_TERMINAL", "authority": "FORCE_TERMINAL", "state": s}
    if not envelope["fresh"]:
        s.update(lifecycle="MISSING_HOLD", deteriorationCount=0, recoveryCount=0)
        return {"action": "HOLD", "authority": "MISSING_HOLD", "state": s}
    # Incomplete owned path is represented by null certified MFE/giveback and cannot arm or exit.
    if not finite(v["certifiedMfePct"]) or not finite(v["certifiedGivebackPp"]):
        s.update(lifecycle="UNARMED" if not s["armedEver"] else "MISSING_HOLD", deteriorationCount=0, recoveryCount=0)
        return {"action": "HOLD", "authority": "UNCERTIFIED_HOLD", "state": s}
    cfg = p["lifecycle"]
    if v["certifiedMfePct"] >= cfg["winnerArmed"]["certifiedMfePctMin"]:
        s["armedEver"] = True
    if not s["armedEver"]:
        s.update(lifecycle="UNARMED", deteriorationCount=0, recoveryCount=0)
        return {"action": "HOLD", "authority": "UNARMED_HOLD", "state": s}
    if v["newPeak"] == 1:
        s.update(lifecycle="CONTINUATION", deteriorationCount=0, recoveryCount=0)
        return {"action": "HOLD", "authority": "NEW_PEAK_CONTINUATION", "state": s}
    recovery = v["stateRecovery"] == 1 or _ge(v, "signalRecoveryN", 1)
    recovery_confirm = recovery and _ge(v, "momentum5Pct", 0) and _ge(v, "signalTrueN", 1)
    s["recoveryCount"] = s["recoveryCount"] + 1 if recovery_confirm else 0
    if s["recoveryCount"] >= cfg["recoveryConfirmed"]["confirm"]:
        s.update(lifecycle="RECOVERY_CONFIRMED", deteriorationCount=0)
        return {"action": "HOLD", "authority": "RECOVERY_CONFIRMED", "state": s}
    continuation = _ge(v, "momentum5Pct", 0) and _ge(v, "signalTrueN", 1)
    if continuation:
        s.update(lifecycle="CONTINUATION", deteriorationCount=0)
        return {"action": "HOLD", "authority": "CONTINUATION", "state": s}
    if recovery:
        s.update(lifecycle="RECOVERY_ATTEMPT", deteriorationCount=0)
        return {"action": "HOLD", "authority": "RECOVERY_ATTEMPT", "state": s}
    m = cfg["matureDeterioration"]
    giveback = max(3.0, 0.50 * v["certifiedMfePct"])
    mature = (_ge(v, "certifiedGivebackPp", giveback) and _ge(v, "timeSincePeak", m["timeSincePeakMin"])
              and _ge(v, "barsHeld", m["barsHeldMin"]) and _le(v, "momentum5Pct", m["momentum5PctMax"])
              and _ge(v, "signalFalseN", m["signalFalseNMin"]))
    failed = v["failedRecovery"] == 1 and _ge(v, "weakRun", 4)
    eligible = mature and (candidate == "R50_A_LIFECYCLE" or failed)
    s["deteriorationCount"] = s["deteriorationCount"] + 1 if eligible else 0
    if s["deteriorationCount"] >= m["confirm"]:
        s["lifecycle"] = "HARVEST_INTENT"
        return {"action": "EXIT_INTENT", "authority": "WINNER_HARVEST", "state": s}
    s["lifecycle"] = "FAILED_RECOVERY" if failed else ("MATURE_DETERIORATION" if mature else "ORDINARY_PULLBACK")
    return {"action": "HOLD", "authority": s["lifecycle"], "state": s}

