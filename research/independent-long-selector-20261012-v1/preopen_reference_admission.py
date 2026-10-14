"""Metadata-only reference-history gate. It never releases existing seals."""
from __future__ import annotations

import json
from preopen_selector import PreopenError, digest

HISTORY_EXCEPTION_DATES = ("2024-09-10", "2024-09-11", "2024-09-12", "2024-09-13")


def admitted_history_exception(request, admission):
    """Read a separately hashed approval; preserve every original seal/ledger.

    This exception admits four DAILY_RAW reference dates, never teacher days,
    financial disclosures, intraday prices, outcomes or an expanded candidate.
    """
    entry = request.get("historyReferenceException")
    if entry is None:
        return frozenset()
    from preopen_io import verify_entry, require_safe_flags
    approval = json.loads(verify_entry(entry, request["privateRoot"]).read_text())
    require_safe_flags(approval)
    teachers = {d for dates in admission["exactSplits"].values() for d in dates}
    if (approval.get("schema") != "ARK_APPROVED_DAILY_HISTORY_EXCEPTION_V1"
            or approval.get("approved") is not True
            or approval.get("sourceKind") != "DIRECT_USER_MESSAGE"
            or not approval.get("ownerStatement") or not approval.get("authorizedAt")
            or approval.get("workId") != request.get("reuseWorkId")
            or approval.get("dataset") != "DAILY_RAW"
            or approval.get("allowedUse") != "CAUSAL_PRICE_HISTORY_ONLY"
            or approval.get("dates") != list(HISTORY_EXCEPTION_DATES)
            or approval.get("splitHash") != digest(admission["exactSplits"])
            or approval.get("originalLedgerSha256") != admission.get("ledgerSha256")
            or approval.get("originalLedgerRewrite") is not False
            or approval.get("freshCredit") is not False
            or approval.get("teacherDatesAdded") != 0
            or approval.get("outcomeEvaluationAllowed") is not False
            or teachers.intersection(HISTORY_EXCEPTION_DATES)):
        raise PreopenError("INVALID_DAILY_HISTORY_EXCEPTION_SCOPE_OR_BINDING")
    return frozenset(HISTORY_EXCEPTION_DATES)


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
    original_blocked = request.get("protectedReferenceSessions",request.get("protectedSessions",[]))
    exception = admitted_history_exception(request, admission)
    audit = reference_dependencies(admission["exactSplits"],request["exchangeSessions"],
                                   set(original_blocked)-exception)
    audit["originalProtectedDatesHash"] = digest(sorted(set(original_blocked)))
    audit["approvedHistoryOnlyDates"] = sorted(exception)
    audit["approvalSha256"] = request.get("historyReferenceException",{}).get("sha256")
    audit["originalLedgerRewritten"] = False
    if audit["conflictDates"]:
        # Do not spend the finite candidate on a globally unobservable MA75,
        # join protected prices anyway, or silently change the reference rule.
        raise PreopenError("MA75_PROTECTED_REFERENCE_CONFLICT:"+",".join(audit["conflictDates"]))
    return audit
