"""Metadata-only reference-history gate. It never releases existing seals."""
from __future__ import annotations

from preopen_selector import PreopenError, digest


def reference_dependencies(splits, exchange_sessions, blocked_dates, *, minimum_bars=76):
    if exchange_sessions != sorted(set(exchange_sessions)):
        raise PreopenError("REFERENCE_EXCHANGE_CALENDAR_NOT_UNIQUE_ORDERED")
    positions = {d:i for i,d in enumerate(exchange_sessions)}
    blocked = set(blocked_dates)
    rows = []
    for role, dates in splits.items():
        for target in dates:
            if target not in positions:
                raise PreopenError("REFERENCE_TARGET_NOT_EXCHANGE_SESSION")
            i = positions[target]
            window = exchange_sessions[max(0,i-minimum_bars):i]
            denied = sorted(set(window)&blocked)
            last = max((j+1 for j,d in enumerate(window) if d in blocked),default=0)
            rows.append({"role":role,"targetSession":target,"referenceDates":window,
                         "blockedReferenceDates":denied,"minimumBars":minimum_bars,
                         "comparableSuffixUpperBound":len(window)-last})
    return {"schema":"ARK_PREOPEN_REFERENCE_DEPENDENCIES_V1","rows":rows,
            "calendarHash":digest(exchange_sessions),"splitHash":digest(splits),
            "blockedDatesHash":digest(sorted(blocked)),
            "conflictDates":sorted({d for r in rows for d in r["blockedReferenceDates"]})}


def enforce_reference_admission(request, admission):
    if request.get("mode") != "AUTHORIZED_DEVELOPMENT" or not request.get("exchangeSessions"):
        return None
    audit = reference_dependencies(admission["exactSplits"],request["exchangeSessions"],
                                   request.get("protectedReferenceSessions",request.get("protectedSessions",[])))
    if audit["conflictDates"]:
        # Do not spend the finite candidate on a globally unobservable MA75,
        # join protected prices anyway, or silently change the reference rule.
        raise PreopenError("MA75_PROTECTED_REFERENCE_CONFLICT:"+",".join(audit["conflictDates"]))
    return audit
