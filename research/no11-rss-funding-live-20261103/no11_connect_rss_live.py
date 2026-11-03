#!/usr/bin/env python3
"""Bind a *generated*, same-day RSS LIVE bootstrap to the existing launcher.

This tool does not start the launcher, touch Excel, invoke broker transport,
initialize a ledger, or grant operator approval. The human-approved physical
transport input must already exist. Never redate an older Chart50/master.
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
import uuid

SETTINGS_SCHEMA = "ARK_NO11_UNIFIED_LAUNCHER_SETTINGS_V1"
BOOT_SCHEMA = "ARK_NO11_READONLY_BOOTSTRAP_CONFIG_V1"
BROKER_SCHEMA = "ARK_NO11_BROKER_EXECUTION_CONFIG_V1"
KEYS = ("schemaId", "accountWorkbookPath", "marketWorkbookPath",
        "orderIdWorkbookPath", "bootstrapConfigFile", "fullSymbolsFile",
        "normalMaxPositions", "sameDayApprovalRequired",
        "automaticOrderAuthorization", "orderTransmission")
JST = timezone(timedelta(hours=9))


def need(ok: bool, reason: str):
    if not ok:
        raise ValueError("NO11_RSS_CONNECT_" + reason)


def safe(path: Path, *, directory=False, may_create=False):
    need(path.is_absolute(), "ABSOLUTE_PATH_REQUIRED")
    for parent in (path, *path.parents):
        if parent.is_symlink():
            raise ValueError("NO11_RSS_CONNECT_REPARSE_POINT")
    if directory:
        need(path.is_dir(), "DIRECTORY_MISSING")
    elif not may_create:
        need(path.is_file() and 0 < path.stat().st_size <= 200_000,
             "SOURCE_MISSING_OR_TOO_LARGE")
    else:
        need(path.parent.is_dir(), "PARENT_MISSING")
    return path


def read_json(path: Path):
    raw = safe(path).read_bytes()
    pairs = []
    def unique(kvs):
        keys = [k for k, _ in kvs]
        need(len(keys) == len(set(keys)), "DUPLICATE_JSON_KEY")
        return dict(kvs)
    value = json.loads(raw.decode("utf-8-sig"), object_pairs_hook=unique)
    need(type(value) is dict, "JSON_OBJECT_REQUIRED")
    return value, raw


def same_path(a: str, b: str):
    return (isinstance(a, str) and isinstance(b, str)
            and bool(a) and bool(b)
            and os.path.normcase(os.path.abspath(a))
            == os.path.normcase(os.path.abspath(b)))


def validate_settings(settings: dict):
    need(type(settings) is dict and tuple(settings) == KEYS,
         "SETTINGS_FIELD_ORDER")
    need(settings["schemaId"] == SETTINGS_SCHEMA
         and type(settings["normalMaxPositions"]) is int
         and settings["normalMaxPositions"] == 3
         and settings["sameDayApprovalRequired"] is True
         and settings["automaticOrderAuthorization"] is False
         and settings["orderTransmission"] is False,
         "SETTINGS_UNSAFE")


def validate_inputs(settings: dict, prepared: dict, physical: dict,
                    arrival: Path, today: str):
    validate_settings(settings)
    need(settings["bootstrapConfigFile"] in ("", None),
         "EXISTING_BOOTSTRAP_MUST_BE_REVIEWED_FIRST")
    need(type(prepared) is dict and prepared.get("schemaId") == BOOT_SCHEMA
         and prepared.get("sessionDate") == today
         and prepared.get("productionReady") is False
         and prepared.get("orderTransmission") is False,
         "CURRENT_DAY_PREPARED_INPUT_REQUIRED")
    need("brokerExecutionConfig" not in prepared
         and "shadowAccountConfig" not in prepared,
         "OLD_BROKER_OR_SHADOW_NOT_ALLOWED")
    need("previousContext" in prepared != ("previousCaptureFiles" in prepared),
         "EXACTLY_ONE_PREVIOUS_SOURCE")
    need("datedMaster" in prepared and "runtimeRoot" in prepared
         and "h235ModelRoot" in prepared and "dailyRun" in prepared
         and "privateRoot" in prepared,
         "FULL_ORIGINAL_INPUTS_REQUIRED")
    need(same_path(prepared.get("orderIdWorkbookPath"),
                   settings["orderIdWorkbookPath"]),
         "ORDER_ID_WORKBOOK_MISMATCH")
    for name in ("accountWorkbookPath", "marketWorkbookPath",
                 "orderIdWorkbookPath"):
        safe(Path(settings[name]))
    safe(arrival)
    need(type(physical) is dict
         and physical.get("schemaId") == "ARK_NO11_MSII_TRANSPORT_CONFIG_V1"
         and physical.get("sessionDate") == today
         and physical.get("mode") == "LIVE"
         and physical.get("orderTransmission") is True
         and physical.get("operatorEnabled") is True
         and physical.get("approvedForSession") is True,
         "ACTUAL_APPROVED_PHYSICAL_TRANSPORT_REQUIRED")
    need(same_path(physical.get("workbookPath"),
                   settings["orderIdWorkbookPath"]),
         "PHYSICAL_BOOK_MISMATCH")
    for key in ("rssSessionKey", "expiresAtJst", "dispatchDirectory",
                "worksheetName", "formulaCell", "triggerCell", "guardCell",
                "sessionCell", "guardValue", "expectedExcelPid",
                "expectedExcelHwnd", "expectedExcelStartedAt",
                "expectedAddInPaths", "expectedOpenWorkbooks",
                "permitMaximumAgeMs", "responseTimeoutMs"):
        need(key in physical, "PHYSICAL_PIN_MISSING")
    need(physical["guardValue"] == "ARK_NO11_SEND_ONCE",
         "GUARD_VALUE_MISMATCH")


def atomic(path: Path, data: bytes):
    temp = path.with_name(path.name + ".register-" + uuid.uuid4().hex)
    try:
        with temp.open("xb") as out:
            out.write(data)
            out.flush()
            os.fsync(out.fileno())
        os.replace(temp, path)
    finally:
        if temp.exists():
            temp.unlink()


def register(settings_file: Path, bootstrap_file: Path,
             broker_file: Path, backup_root: Path, now: str):
    settings, before = read_json(settings_file)
    validate_settings(settings)
    bootstrap, _ = read_json(bootstrap_file)
    broker, _ = read_json(broker_file)
    need(bootstrap.get("schemaId") == BOOT_SCHEMA
         and bootstrap.get("sessionDate") == now[:10]
         and bootstrap.get("orderTransmission") is False
         and bootstrap.get("productionReady") is False
         and same_path(bootstrap.get("brokerExecutionConfig"), str(broker_file))
         and same_path(bootstrap.get("orderIdWorkbookPath"),
                       settings["orderIdWorkbookPath"]),
         "GENERATED_BOOTSTRAP_MISMATCH")
    need(broker.get("schemaId") == BROKER_SCHEMA
         and broker.get("sessionDate") == now[:10]
         and broker.get("fundingPolicy") == "RSS_BUYING_POWER"
         and broker.get("orderTransmission") is True
         and broker.get("productionReady") is False
         and broker.get("transport", {}).get("mode") == "LIVE"
         and broker.get("transport", {}).get("approvedForSession") is True
         and broker.get("ledger", {}).get("maxSymbols") == 3
         and broker.get("ledger", {}).get("lotSize") == 100
         and broker.get("ledger", {}).get("account") == "一般",
         "GENERATED_BROKER_CONFIG_UNSAFE")
    need(same_path(broker["transport"].get("workbookPath"),
                   settings["orderIdWorkbookPath"]),
         "GENERATED_PHYSICAL_BOOK_MISMATCH")
    need(settings["bootstrapConfigFile"] in ("", None),
         "LAUNCHER_BOOTSTRAP_ALREADY_SET")
    safe(backup_root, directory=True)
    backup = backup_root / ("launcher-settings-before-rss-" +
                            uuid.uuid4().hex + ".json")
    with backup.open("xb") as out:
        out.write(before)
        out.flush()
        os.fsync(out.fileno())
    need(backup.read_bytes() == before, "BACKUP_VERIFY_FAILED")
    updated = dict(settings)
    updated["bootstrapConfigFile"] = str(bootstrap_file)
    validate_settings(updated)
    after = (json.dumps(updated, ensure_ascii=False, separators=(",", ":"))
             + "\n").encode("utf-8")
    # Do not silently replace a concurrent operator edit.
    need(settings_file.read_bytes() == before, "SETTINGS_CHANGED_DURING_PREPARE")
    atomic(settings_file, after)
    try:
        check, check_bytes = read_json(settings_file)
        need(check == updated and check_bytes == after,
             "POST_REGISTER_VERIFY_FAILED")
    except BaseException:
        if settings_file.read_bytes() == after:
            atomic(settings_file, before)
        raise
    return backup


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--prepared-bootstrap", required=True, type=Path)
    p.add_argument("--physical-transport", required=True, type=Path)
    p.add_argument("--original-arrival", required=True, type=Path)
    p.add_argument("--settings", required=True, type=Path)
    p.add_argument("--output-root", required=True, type=Path)
    p.add_argument("--backup-root", required=True, type=Path)
    p.add_argument("--register", action="store_true",
                   help="Generate two configs and register their path; NEVER start Trade")
    a = p.parse_args()
    now = datetime.now(JST).isoformat(timespec="milliseconds")
    settings, _ = read_json(a.settings)
    prepared, _ = read_json(a.prepared_bootstrap)
    physical, _ = read_json(a.physical_transport)
    validate_inputs(settings, prepared, physical, a.original_arrival, now[:10])
    safe(a.output_root, directory=True)
    safe(a.backup_root, directory=True)
    if not a.register:
        print("RSS_LIVE_CONNECTOR=INPUT_CONTRACT_CHECKED_ONLY")
        print("CONFIG_GENERATED=False")
    else:
        # Import the already-installed, exact original native config generator.
        tools = Path(__file__).resolve().parent
        sys.path.insert(0, str(tools))
        import no11_make_rss_live_config as maker
        boot, broker = maker.build({
            "bootstrapInputs": prepared, "transport": physical,
            "originalArrivalTable": str(a.original_arrival)
        }, a.output_root, now)
        backup = register(a.settings, boot, broker, a.backup_root, now)
        print("RSS_LIVE_CONNECTOR=REGISTERED")
        print("GENERATED_BOOTSTRAP=" + str(boot))
        print("GENERATED_BROKER=" + str(broker))
        print("LAUNCHER_SETTINGS_BACKUP=" + str(backup))
    print("LAUNCHER_STARTED=False")
    print("TRADE_LAUNCHED=False")
    print("OPERATOR_APPROVAL_CREATED=False")
    print("ORDER_SENT=False")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, TypeError, KeyError, RuntimeError,
            ImportError, json.JSONDecodeError) as err:
        message = str(err)
        code = message if re.fullmatch(r"NO11_RSS_CONNECT_[A-Z0-9_]+", message) else (
            "NO11_RSS_CONNECT_MISSING_OR_UNVERIFIED_PRIVATE_SOURCE")
        print("RSS_LIVE_CONNECTOR=BLOCKED|" + code, file=sys.stderr)
        print("ORDER_SENT=False", file=sys.stderr)
        raise SystemExit(2)
