"""CAL-only threshold optimization with exact count-ratio tie breaking."""
import math
from fractions import Fraction

ALL_REJECT = math.nextafter(1.0, math.inf)

def select_threshold(cal, q):
    known = [r for r in cal if r["y_plus"] is not None and r["p_plus"] is not None]
    positive = sum(r["y_plus"] == 1 for r in known)
    negative = sum(r["y_plus"] == 0 for r in known)
    support = {"known_N": len(known), "sessions": len({r["session"] for r in known}),
               "PLUS": positive, "MINUS": negative}
    base = {"q": float(q), "tau": 0.0, "support": support, "all_reject_sentinel": ALL_REJECT,
            "weights": "unit counts; no sample/class weights"}
    if len(known) < 50 or support["sessions"] < 3 or positive < 10 or negative < 10:
        return {**base, "status": "FILTER_OFF_SUPPORT", "cal_BA": None, "cal_plus_retention": None, "cal_minus_removal": None}
    candidates = sorted({0.0, ALL_REJECT} | {r["p_plus"] for r in known})
    best = None
    for tau in candidates:
        tp = sum(r["y_plus"] == 1 and r["p_plus"] >= tau for r in known)
        tn = sum(r["y_plus"] == 0 and r["p_plus"] < tau for r in known)
        keep = Fraction(tp, positive); remove = Fraction(tn, negative)
        if keep < Fraction(str(q)):
            continue
        ba = (keep + remove) / 2
        key = (ba, remove, -tau)
        if best is None or key > best[0]:
            best = (key, tau, keep, remove)
    assert best is not None
    if best[0][0] <= Fraction(1, 2):
        return {**base, "status": "NULL_ALL_PASS", "cal_BA": 0.5,
                "cal_plus_retention": 1.0, "cal_minus_removal": 0.0, "candidate_N": len(candidates)}
    return {**base, "tau": best[1], "status": "ACTIVE", "cal_BA": float(best[0][0]),
            "cal_plus_retention": float(best[2]), "cal_minus_removal": float(best[3]), "candidate_N": len(candidates)}

def filter_action(p_plus, threshold):
    # ABSTAIN is operationally a pass, and remains a separate raw sign status.
    if p_plus is None or threshold["status"] != "ACTIVE":
        return "PASS_CANDIDATE"
    return "PASS_CANDIDATE" if p_plus >= threshold["tau"] else "REJECT_CANDIDATE"

