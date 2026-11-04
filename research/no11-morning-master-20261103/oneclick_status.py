#!/usr/bin/env python3
"""Fail-closed, read-only ARK No.1.1 OneClick status.

Does not import the trading engine, touch Excel, submit orders, reset the
session, or infer trade authorization from a UI process being open.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
import sys

JST = timezone(timedelta(hours=9))
HASH = re.compile(r"^[a-f0-9]{64}$")
DAY = re.compile(r"^20\d{2}-\d{2}-\d{2}$")
PIN = "ARK_NO11_NIGHTLY_LAUNCHER_HANDOFF_V1"


def fail(code):
    raise ValueError("NO11_ONECLICK_" + code)


def safe(path, *, root=None):
    p = Path(path)
    if not p.is_absolute() or p.is_symlink() or not p.is_file():
        fail("FILE_MISSING_OR_UNSAFE")
    if root is not None:
        try:
            p.relative_to(Path(root))
        except ValueError:
            fail("PATH_OUTSIDE_PRIVATE_ROOT")
    return p


def read_json(path, *, root=None, size=2_000_000):
    p = safe(path, root=root)
    raw = p.read_bytes()
    if not 0 < len(raw) <= size:
        fail("JSON_SIZE")
    try:
        obj = json.loads(raw.decode("utf-8-sig"))
    except (ValueError, UnicodeError):
        fail("JSON_INVALID")
    if not isinstance(obj, dict):
        fail("JSON_OBJECT_REQUIRED")
    return obj, hashlib.sha256(raw).hexdigest()


def validated_handoff(binding, day):
    root = binding.get("dailyCycleRoot")
    if not isinstance(root, str) or not Path(root).is_absolute():
        return False, "NIGHTLY_NOT_INSTALLED"
    path = Path(root) / "prepared-days" / (day + ".json")
    if not path.is_file():
        return False, "TODAY_HANDOFF_MISSING"
    ptr, _ = read_json(path, root=root)
    if ptr.get("schemaId") != PIN or ptr.get("sessionDate") != day:
        return False, "HANDOFF_DATE_OR_SCHEMA"
    if ptr.get("orderTransmission") is not False or ptr.get("productionReady") is not False:
        return False, "HANDOFF_UNSAFE"
    source, sha = read_json(ptr.get("handoff"), root=root)
    if sha != ptr.get("handoffSha256") or not HASH.fullmatch(sha):
        return False, "HANDOFF_HASH_CHANGED"
    symbols = source.get("selectedSymbols")
    if (source.get("sessionDate") != day or source.get("orderTransmission") is not False
            or not isinstance(symbols, list) or not 0 < len(symbols) <= 47
            or symbols != ptr.get("selectedSymbols") or len(symbols) != ptr.get("selectedCount")
            or len(set(symbols)) != len(symbols)
            or not all(isinstance(s, str) and re.fullmatch(r"[0-9A-Z]{4}\.T", s) for s in symbols)):
        return False, "HANDOFF_CONTENT_INVALID"
    return True, "TODAY_HANDOFF_PINNED"


def inspect(settings_file, binding_file, *, at=None):
    now = at or datetime.now(JST)
    if now.utcoffset() != timedelta(hours=9):
        fail("JST_REQUIRED")
    day = now.date().isoformat()
    settings, _ = read_json(settings_file)
    binding, _ = read_json(binding_file)
    store = Path(settings_file).parent
    result = {
        "schemaId": "ARK_NO11_ONECLICK_STATUS_V1",
        "sessionDate": day,
        "mode": "BLOCKED",
        "reason": "UNVERIFIED",
        "canRequestTrade": False,
        "canRunNightly": False,
        "requiresSameDayApproval": True,
        "readOnly": True,
        "brokerOrderTransmission": False,
    }
    if (settings.get("normalMaxPositions") != 3 or
            settings.get("sameDayApprovalRequired") is not True or
            settings.get("automaticOrderAuthorization") is not False or
            settings.get("orderTransmission") is not False or
            binding.get("schemaId") != "ARK_NO11_AUTOMATIC_LAUNCHER_BINDING_V1" or
            binding.get("orderTransmission") is not False):
        result["reason"] = "CONFIG_UNSAFE"
        return result
    if now.weekday() >= 5:
        result["reason"] = "NON_TRADING_DAY"
        return result
    if now.hour >= 18:
        result["mode"] = "AFTER_CLOSE"
        result["reason"] = "NIGHTLY_NOT_INSTALLED"
        if (isinstance(binding.get("dailyCycleTool"), str) and
                isinstance(binding.get("dailyCycleRoot"), str) and
                Path(binding["dailyCycleTool"]).is_file() and
                Path(binding["dailyCycleRoot"]).is_dir()):
            result.update(canRunNightly=True, reason="NIGHTLY_OPERATOR_BUTTON_AVAILABLE")
        return result
    marker = store / ("TRADE-" + day + ".launch.json")
    if marker.exists():
        receipt, _ = read_json(marker)
        result["reason"] = ("ALREADY_STARTED_TODAY" if
                            receipt.get("kind") == "TRADE" and receipt.get("asOfDate") == day
                            else "UNKNOWN_TRADE_MARKER")
        return result
    bootstrap_file = settings.get("bootstrapConfigFile")
    if not isinstance(bootstrap_file, str) or not bootstrap_file:
        result["reason"] = "BOOTSTRAP_MISSING"
        return result
    bootstrap, _ = read_json(bootstrap_file)
    if bootstrap.get("sessionDate") != day or bootstrap.get("orderTransmission") is not False:
        result["reason"] = "BOOTSTRAP_NOT_TODAY"
        # A fresh nightly pointer can be activated through existing bridge.
        pinned, why = validated_handoff(binding, day)
        if not pinned:
            result["reason"] = why
            return result
    private = bootstrap.get("privateRoot")
    if isinstance(private, str) and Path(private).is_absolute():
        root = Path(private)
        pointer = root / ("received-session-" + day + ".active.json")
        if pointer.exists() or (root / "bootstrap-recovery-required.json").exists():
            result["reason"] = "EXISTING_RUN_REQUIRES_REVIEW"
            return result
    pinned, why = validated_handoff(binding, day)
    if not pinned:
        # If nightly is installed, a missing/altered dated pointer is a hard
        # block. Do not fall back to an older seed handoff.
        if why != "NIGHTLY_NOT_INSTALLED":
            result["reason"] = why
            return result
        # Legacy same-day direct handoff: never silently redate old inputs.
        hand = binding.get("handoff")
        if not isinstance(hand, str):
            result["reason"] = why
            return result
        handoff, _ = read_json(hand)
        if handoff.get("sessionDate") != day or handoff.get("orderTransmission") is not False:
            result["reason"] = why
            return result
    if (now.hour < 9 or now.hour > 15 or
            (now.hour == 15 and now.minute >= 20)):
        result.update(mode="OUTSIDE_ENTRY_WINDOW", reason="NEW_ENTRY_WINDOW_CLOSED")
        return result
    result.update(mode="OPERATOR_CHECK", reason="PRELIMINARY_INPUTS_READY",
                  canRequestTrade=True)
    return result


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--settings", type=Path, required=True)
    p.add_argument("--binding", type=Path, required=True)
    a = p.parse_args(argv)
    try:
        print(json.dumps(inspect(a.settings, a.binding),
                         ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    except (OSError, ValueError, TypeError, KeyError):
        print(json.dumps({"schemaId": "ARK_NO11_ONECLICK_STATUS_V1",
                          "mode": "BLOCKED", "reason": "SOURCE_OR_RUNTIME_UNVERIFIED",
                          "canRequestTrade": False, "canRunNightly": False,
                          "readOnly": True, "brokerOrderTransmission": False}))
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
