#!/usr/bin/env python3
"""No11 after-hours, no-trade, read-only fault census for the operator's Windows PC.

Never writes ANY file, starts or stops a process, launches Excel, imports
order/RSS modules, reads securities/position values, or grants Trade access.
File names/paths, account data and source payloads are never printed.
A PASS means local metadata is internally consistent, NOT live readiness.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any

JST = timezone(timedelta(hours=9))
CURRENT_DAY = lambda: datetime.now(JST).date().isoformat()
NO11_DIR = Path(__file__).resolve().parent
MAX_JSON_BYTES = 4_000_000


class AuditStop(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def checked_file(path: Path) -> Path:
    if not path.is_absolute():
        raise AuditStop("SOURCE_NOT_ABSOLUTE")
    for ancestor in (path, *path.parents):
        if ancestor.is_symlink() or (hasattr(ancestor, "is_junction") and ancestor.is_junction()):
            raise AuditStop("REPARSE_POINT_NOT_TRUSTED")
        try:
            if getattr(ancestor.stat(), "st_file_attributes", 0) & 0x400:
                raise AuditStop("REPARSE_POINT_NOT_TRUSTED")
        except FileNotFoundError:
            continue
        except OSError:
            raise AuditStop("SOURCE_NOT_READABLE") from None
    try:
        if not path.is_file():
            raise AuditStop("SOURCE_MISSING")
        if path.stat().st_size > MAX_JSON_BYTES:
            raise AuditStop("SOURCE_TOO_LARGE")
    except OSError:
        raise AuditStop("SOURCE_NOT_READABLE") from None
    return path


def read_json(path: Path) -> dict[str, Any]:
    checked_file(path)
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, ValueError):
        raise AuditStop("INVALID_JSON") from None
    if not isinstance(data, dict):
        raise AuditStop("JSON_NOT_OBJECT")
    return data


def is_sha256(value: Any) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def sha256(path: Path) -> str:
    checked_file(path)
    h = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            for part in iter(lambda: stream.read(256 * 1024), b""):
                h.update(part)
    except OSError:
        raise AuditStop("SOURCE_NOT_READABLE") from None
    return h.hexdigest()


def source_date(record: Any) -> str | None:
    if not isinstance(record, dict):
        return None
    for field in ("sessionDate", "tradeDate", "targetSession"):
        if field in record:
            value = record[field]
            return str(value) if value is not None else "NULL_DATE"
    return None


def no_trading_flags(record: Any) -> bool:
    if not isinstance(record, dict):
        return False
    return all(record.get(key) is False for key in ("orderTransmission", "productionReady"))


def readonly_audit(root: Path, day: str, *, preflight: Path | None = None) -> dict[str, Any]:
    """Return safe, bounded, categorically non-authorizing status fields."""
    result: dict[str, Any] = {
        "schema": "ARK_NO11_AFTERHOURS_READONLY_CENSUS_V1",
        "target_session": day,
        "today_jst": CURRENT_DAY(),
        "declared_trade_policy": "NO_TRADING_ON_2026_11_13",
        "read_only": True,
        "source_values_or_paths_emitted": False,
        "broker_orders_fills_positions_verified": False,
        "excel_rss_checked": False,
        "live_runtime_running_verified": False,
        "live_start_verified": False,
        "trade_authorized": False,
        "order_transmission": False,
        "recommendation": "DO_NOT_START_TRADE_OR_REPLAY",
        "checks": {},
    }
    checks: dict[str, str] = result["checks"]
    try:
        datetime.strptime(day, "%Y-%m-%d")
        if datetime.strptime(day, "%Y-%m-%d").date().isoformat() != day:
            raise ValueError("noncanonical")
    except ValueError:
        checks["DATE_FORMAT"] = "BLOCKED_NONCANONICAL_DATE"
        return result
    checks["DATE_SCOPE"] = ("TODAY_READONLY" if day == result["today_jst"]
                            else "OTHER_SESSION_READONLY_NO_DATE_REWRITE")
    preflight = preflight or (NO11_DIR / "Check-No11StartPrerequisitesReadOnly20261111.ps1")
    checks["PREFLIGHT_IN_GIT_CHECKOUT"] = (
        "PRESENT" if preflight.is_file() else "NOT_PRESENT_IN_THIS_CHECKOUT"
    )
    settings_path = root / "settings.json"
    binding_path = root / "automatic-inputs.json"
    try:
        settings, binding = read_json(settings_path), read_json(binding_path)
        checks["SETTINGS_AND_BINDING"] = "READABLE"
    except AuditStop as exc:
        checks["SETTINGS_AND_BINDING"] = "BLOCKED_" + exc.code
        checks["PREPARED_DAY"] = "NOT_INSPECTED"
        checks["BOOTSTRAP_SESSION"] = "NOT_INSPECTED"
        checks["LOCAL_RUN_EVIDENCE"] = "NOT_INSPECTED"
        return result
    if (settings.get("schemaId") != "ARK_NO11_UNIFIED_LAUNCHER_SETTINGS_V1"
            or binding.get("schemaId") != "ARK_NO11_AUTOMATIC_LAUNCHER_BINDING_V1"
            or not no_trading_flags(settings)
            or binding.get("orderTransmission") is not False
            or settings.get("automaticOrderAuthorization") is not False):
        checks["SETTINGS_AND_BINDING"] = "BLOCKED_CONFIG_CONTRACT"
    for key, obj in (("SETTINGS_SESSION", settings), ("BINDING_SESSION", binding)):
        date = source_date(obj)
        checks[key] = ("DATE_NOT_DECLARED" if date is None else
                       ("MATCHES_TARGET" if date == day else "WRONG_SESSION_DATE"))
    def bound_path(value: Any) -> Path:
        if not isinstance(value, str) or not value or "\x00" in value:
            raise AuditStop("BOUND_PATH_UNDEFINED")
        path = Path(value)
        if not path.is_absolute():
            raise AuditStop("BOUND_PATH_NOT_ABSOLUTE")
        return path
    try:
        boot = read_json(bound_path(settings.get("bootstrapConfigFile")))
        date = source_date(boot)
        checks["BOOTSTRAP_SESSION"] = ("DATE_NOT_DECLARED" if date is None else
                                        ("MATCHES_TARGET" if date == day else "WRONG_SESSION_DATE"))
    except AuditStop as exc:
        boot = {}
        checks["BOOTSTRAP_SESSION"] = "BLOCKED_" + exc.code
    try:
        prepared_root = bound_path(binding.get("dailyCycleRoot"))
        pointer = read_json(prepared_root / "prepared-days" / (day + ".json"))
        if (pointer.get("sessionDate") != day
                or pointer.get("schemaId") != "ARK_NO11_NIGHTLY_LAUNCHER_HANDOFF_V1"
                or not no_trading_flags(pointer)
                or pointer.get("humanReviewClaimed") is not False):
            checks["PREPARED_DAY"] = "BLOCKED_WRONG_OR_UNSAFE_HANDOFF"
        else:
            hand_path = bound_path(pointer.get("handoff"))
            pin = pointer.get("handoffSha256")
            if not is_sha256(pin) or sha256(hand_path) != pin:
                checks["PREPARED_DAY"] = "BLOCKED_HANDOFF_SHA256"
            else:
                hand = read_json(hand_path)
                if (hand.get("sessionDate") != day
                        or hand.get("schemaId") != "ARK_NO11_MORNING_MASTER_HANDOFF_V1"
                        or not no_trading_flags(hand)
                        or hand.get("reviewStatus") != "NOT_REVIEWED"
                        or hand.get("datedMasterCreated") is not False):
                    checks["PREPARED_DAY"] = "BLOCKED_HANDOFF_SCOPE"
                else:
                    checks["PREPARED_DAY"] = "DATE_AND_HASH_MATCH_READONLY"
    except AuditStop as exc:
        checks["PREPARED_DAY"] = "BLOCKED_" + exc.code
    # Existence of a local marker is NOT proof of zero broker orders.
    # Missing marker is NOT proof a prior order never occurred.
    marker = root / ("TRADE-" + day + ".launch.json")
    try:
        private_root = bound_path(boot.get("privateRoot"))
        marker_present = (
            marker.exists()
            or (private_root / ("received-session-" + day + ".active.json")).exists()
            or (private_root / "bootstrap-recovery-required.json").exists()
        )
        checks["LOCAL_RUN_EVIDENCE"] = (
            "EXISTING_CLAIM_REQUIRES_MANUAL_REVIEW" if marker_present
            else "NO_LOCAL_MARKER_FOUND_NOT_BROKER_CLEARANCE"
        )
    except AuditStop as exc:
        checks["LOCAL_RUN_EVIDENCE"] = "BLOCKED_" + exc.code
    # Controller/source provenance requires separate exact native review.
    checks["LEGACY_RETRY_CONTROLLER"] = "NOT_CLEARED_BY_THIS_AUDIT"
    checks["CHART50_ATTEMPT_CLOSURE"] = "RECONCILIATION_REQUIRED"
    checks["NODE_FAILURE_CAUSE"] = "NOT_RECOVERABLE_FROM_MISSING_2026_11_12_STDERR"
    checks["PR612_613_614_PC_DEPLOYMENT"] = "NOT_VERIFIED_BY_THIS_AUDIT"
    checks["BROKER_STATE"] = "NOT_OBSERVED_NO_ZERO_ASSUMPTION"
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session-date", help="YYYY-MM-DD, for read-only diagnostics ONLY")
    parser.add_argument("--settings-root", help="LocalAppData/unified-launcher; no write")
    args = parser.parse_args()
    day = args.session_date or CURRENT_DAY()
    if args.settings_root:
        root = Path(args.settings_root)
    else:
        local = os.environ.get("LOCALAPPDATA", "")
        root = Path(local) / "ArkTerminal" / "No12" / "unified-launcher" if local else Path("/missing-localappdata")
    result = readonly_audit(root, day)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    # This program is never a green light for live trading.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
