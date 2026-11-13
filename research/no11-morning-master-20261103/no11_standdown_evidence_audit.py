"""Read-only NO-TRADE session evidence audit.

The operator can elect not to trade. This utility DOES NOT disable a running
engine, cancel broker orders, insert a no-trade marker, or certify that the
broker has no orders. It inspects immutable local evidence, never changes it.
No Excel COM, broker API, process launch, or network requests.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys

JST = timezone(timedelta(hours=9))
DAY = re.compile(r"20\d\d-\d\d-\d\d\Z")
HASH = re.compile(r"[a-f0-9]{64}\Z")
SYMBOL = re.compile(r"[0-9A-Z]{4}\.T\Z")
PIN = "ARK_NO11_NIGHTLY_LAUNCHER_HANDOFF_V1"
HANDOFF = "ARK_NO11_MORNING_MASTER_HANDOFF_V1"
RESULT_SCHEMA = "ARK_NO11_OPERATOR_STANDDOWN_READONLY_V1"


def fail(code: str):
    raise ValueError("NO11_STANDDOWN_" + code)


def insist(ok, code: str):
    if not ok:
        fail(code)


def secure(path, *, root=None, directory=False):
    p = Path(path)
    insist(p.is_absolute(), "ABSOLUTE_PATH")
    for ancestor in (p, *p.parents):
        if ancestor.exists() or ancestor.is_symlink():
            attrs = getattr(ancestor.lstat(), "st_file_attributes", 0)
            insist(not ancestor.is_symlink() and not (attrs & 1024), "REPARSE_SOURCE")
    insist(p.is_dir() if directory else p.is_file(), "SOURCE_NOT_FOUND")
    if root is not None:
        p.resolve().relative_to(Path(root).resolve())
    return p


def data(path, *, root=None, limit=2_000_000):
    p = secure(path, root=root)
    raw = p.read_bytes()
    insist(0 < len(raw) <= limit, "SOURCE_SIZE")
    def no_duplicates(pairs):
        out = {}
        for key, value in pairs:
            insist(key not in out, "DUPLICATE_KEY")
            out[key] = value
        return out
    obj = json.loads(raw.decode("utf-8-sig"), object_pairs_hook=no_duplicates,
                     parse_constant=lambda _: fail("NONFINITE_NUMBER"))
    insist(type(obj) is dict, "JSON_OBJECT")
    return obj, hashlib.sha256(raw).hexdigest()


def previous_weekday(day):
    d = datetime.strptime(day, "%Y-%m-%d").date() - timedelta(days=1)
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return d.isoformat()


def indicator(path):
    """Presence is evidence of a possible action, never proof of order/fill."""
    p = Path(path)
    if p.is_symlink() or (p.exists() and
        getattr(p.lstat(), "st_file_attributes", 0) & 1024):
        return "UNVERIFIED_REPARSE"
    return "PRESENT_REVIEW_REQUIRED" if p.exists() else "ABSENT"


def today_handoff(binding, day):
    root = binding.get("dailyCycleRoot")
    if type(root) is not str or not Path(root).is_absolute():
        return {"state": "UNVERIFIED", "reason": "DAILY_ROOT_UNAVAILABLE"}
    try:
        root = secure(root, directory=True)
        pointer_path = root / "prepared-days" / (day + ".json")
        if not pointer_path.exists():
            return {"state": "MISSING", "reason": "DATED_POINTER_MISSING"}
        ptr, _ = data(pointer_path, root=root)
        insist(ptr.get("schemaId") == PIN and ptr.get("sessionDate") == day and
               ptr.get("orderTransmission") is False and
               ptr.get("productionReady") is False and
               ptr.get("humanReviewClaimed") is False,
               "POINTER_CONTRACT")
        handoff_sha = ptr.get("handoffSha256")
        insist(type(handoff_sha) is str and HASH.fullmatch(handoff_sha),
               "HANDOFF_SHA")
        handoff_file = Path(ptr.get("handoff", ""))
        insist(handoff_file.name == "morning-handoff-" + handoff_sha + ".json",
               "HANDOFF_NAME")
        hand, actual_sha = data(handoff_file, root=root)
        symbols = hand.get("selectedSymbols")
        insist(actual_sha == handoff_sha and
               hand.get("schemaId") == HANDOFF and
               hand.get("sessionDate") == day and
               hand.get("previousSession") == ptr.get("previousSession") and
               hand.get("orderTransmission") is False and
               hand.get("productionReady") is False and
               hand.get("reviewStatus") == "NOT_REVIEWED" and
               hand.get("datedMasterCreated") is False and
               type(symbols) is list and
               0 < len(symbols) <= 47 and
               symbols == ptr.get("selectedSymbols") and
               len(symbols) == ptr.get("selectedCount") and
               len(set(symbols)) == len(symbols) and
               all(type(code) is str and SYMBOL.fullmatch(code) for code in symbols),
               "HANDOFF_CONTRACT")
        prev = ptr.get("previousSession")
        insist(type(prev) is str and DAY.fullmatch(prev) and
               datetime.fromisoformat(prev).date() <
               datetime.fromisoformat(day).date(), "SOURCE_DAY")
        return {"state": "VERIFIED_DATED_HANDOFF", "selectedCount": len(symbols),
                "sourceSession": prev}
    except (OSError, UnicodeError, ValueError, KeyError, TypeError, RuntimeError):
        return {"state": "UNVERIFIED", "reason": "HANDOFF_INTEGRITY_UNKNOWN"}


def bridge_status(binding):
    """Only source pin correctness, NEVER execute or activate the bridge."""
    path, expected = binding.get("bridge"), binding.get("bridgeSha256")
    if (type(path) is not str or type(expected) is not str or
            not HASH.fullmatch(expected)):
        return "NOT_PINNED"
    try:
        actual = hashlib.sha256(secure(path).read_bytes()).hexdigest()
        return "SOURCE_PIN_VERIFIED" if actual == expected else "SOURCE_PIN_MISMATCH"
    except (OSError, ValueError, TypeError):
        return "UNVERIFIED"


def previous_collector(private, previous):
    if private is None:
        return "UNKNOWN_PRIVATE_ROOT"
    try:
        root = secure(private, directory=True)
        ptr_path = root / ("received-session-" + previous + ".active.json")
        if not ptr_path.exists():
            return "NO_PRIOR_RUN_POINTER_AT_THIS_ROOT"
        ptr, _ = data(ptr_path, root=root)
        run = Path(ptr.get("runRoot", ""))
        insist(run.parent == root and
               re.fullmatch(r"session-" + re.escape(previous) + r"-[a-f0-9]{32}", run.name)
               and ptr.get("sessionDate") == previous,
               "PRIOR_RUN_SCOPE")
        secure(run, root=root, directory=True)
        attempts = sorted(run.glob("attempt-*"))
        if len(attempts) == 0:
            return "NO_PRIOR_ATTEMPTS"
        insist(len(attempts) <= 32, "TOO_MANY_PRIOR_ATTEMPTS")
        # A file's existence is not a cryptographic proof of a normal shutdown.
        latest = secure(attempts[-1], root=run, directory=True)
        attempt, _ = data(latest / "attempt.json", root=run)
        status = attempt.get("status")
        closed = indicator(latest / "collector-ready.json.closed.json")
        if status == "CLOSED" and closed == "PRESENT_REVIEW_REQUIRED":
            return "CLOSED_RECORD_PRESENT_NOT_CERTIFIED"
        if status in ("REQUESTING", "RUNNING", "CONNECTED"):
            return ("UNCLOSED_ATTEMPT_" + status if closed == "ABSENT"
                    else "CONFLICTING_ATTEMPT_AND_CLOSURE")
        return "PRIOR_ATTEMPT_UNVERIFIED"
    except (OSError, ValueError, TypeError, KeyError, RuntimeError):
        return "PRIOR_ATTEMPT_UNVERIFIED"


def inspect(store, *, day=None):
    day = day or datetime.now(JST).date().isoformat()
    insist(type(day) is str and DAY.fullmatch(day), "INVALID_SESSION_DATE")
    store = secure(store, directory=True)
    settings, _ = data(store / "settings.json")
    binding, _ = data(store / "automatic-inputs.json")
    insist(settings.get("schemaId") == "ARK_NO11_UNIFIED_LAUNCHER_SETTINGS_V1"
           and settings.get("sameDayApprovalRequired") is True
           and settings.get("automaticOrderAuthorization") is False
           and settings.get("orderTransmission") is False
           and settings.get("normalMaxPositions") == 3
           and binding.get("schemaId") == "ARK_NO11_AUTOMATIC_LAUNCHER_BINDING_V1"
           and binding.get("orderTransmission") is False,
           "LOCAL_CONFIG_UNSAFE")
    marker = {
        "preopenRequest": indicator(store / ("PREOPEN-" + day + ".request.json")),
        "preopenExecutionClaim": indicator(store / ("PREOPEN-" + day + ".execution-claimed")),
        "tradeLaunchRequest": indicator(store / ("TRADE-" + day + ".launch.json")),
    }
    try:
        cfgpath = settings.get("bootstrapConfigFile")
        cfg, _ = data(cfgpath)
        bootdate = cfg.get("sessionDate")
        private = cfg.get("privateRoot")
        private = private if type(private) is str and Path(private).is_absolute() else None
    except (OSError, ValueError, TypeError, KeyError, RuntimeError):
        bootdate = None
        private = None
    handoff = today_handoff(binding, day)
    local = {
        **marker,
        "activeRun": indicator(Path(private) / ("received-session-" + day + ".active.json"))
                     if private else "UNVERIFIED",
        "recoveryRequired": indicator(Path(private) / "bootstrap-recovery-required.json")
                            if private else "UNVERIFIED",
    }
    uncertain = any(value != "ABSENT" for value in local.values())
    return {
        "schemaId": RESULT_SCHEMA,
        "sessionDate": day,
        "readOnly": True,
        "operatorNoTradeIntent": "DECLARED_IN_CHAT_NOT_LOCAL_ENFORCEMENT",
        "brokerOrdersChecked": False,
        "brokerExecutionsChecked": False,
        "brokerPositionsChecked": False,
        "canAuthorizeTrade": False,
        "ordersCancelledByAudit": False,
        "tradeLaunchedByAudit": False,
        "orderTransmission": False,
        "markers": local,
        "localLaunchEvidence": ("REVIEW_OR_UNKNOWN" if uncertain
                                else "NO_LOCAL_LAUNCH_MARKERS_AT_SCANNED_ROOT"),
        "preparedData": handoff,
        "bridge": bridge_status(binding),
        "legacyBootstrapDate": bootdate if isinstance(bootdate, str) and DAY.fullmatch(bootdate) else "UNVERIFIED",
        "legacyBootstrapDateIsToday": bootdate == day,
        "autoBridgeMayRebindOnlyOnTrade": True,
        "previousSession": previous_weekday(day),
        "previousCollector": previous_collector(private, previous_weekday(day)),
        "requiresIndependentBrokerReview": True,
        "requiresExplicitVerifiedShutdownIfLive": True,
        "untouchedHistoricalClaims": True,
    }


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--store", type=Path, required=True)
    p.add_argument("--day", type=str)
    a = p.parse_args(argv)
    try:
        print(json.dumps(inspect(a.store, day=a.day), ensure_ascii=True,
                         separators=(",", ":"), sort_keys=True, allow_nan=False))
        return 0
    except (OSError, ValueError, TypeError, KeyError):
        print(json.dumps({
            "schemaId": RESULT_SCHEMA, "readOnly": True,
            "operatorNoTradeIntent": "DECLARED_IN_CHAT_NOT_LOCAL_ENFORCEMENT",
            "canAuthorizeTrade": False, "orderTransmission": False,
            "state": "AUDIT_BLOCKED_SOURCE_UNVERIFIED",
            "requiresIndependentBrokerReview": True,
        }, separators=(",", ":")))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
