#!/usr/bin/env python3
"""Surgically expose V3 physical-transport BLOCKED reasons in installed ARK.

Only one Python log-filter line and its bound SHA256 are changed.
No Excel COM, trade, order trigger, launcher, white OneClick UI, or broker ledger.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import uuid

OLD = b"if line.startswith(('AUTOMATIC_TRANSPORT_', 'ORDER_TRIGGER_', 'ORDER_SENT=')):"
NEW = b"if line.startswith(('AUTOMATIC_TRANSPORT_', 'AUTOMATIC_TRANSPORT=BLOCKED|', 'ORDER_TRIGGER_', 'ORDER_SENT=')):"
SCHEMA = "ARK_NO11_AUTOMATIC_LAUNCHER_BINDING_V1"
BRIDGE_FILE = "launcher_automatic_bridge_v4.py"


def need(ok: bool, code: str) -> None:
    if not ok:
        raise ValueError("NO11_TRANSPORT_LOG_FIX_" + code)


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def parse_object(raw: bytes) -> dict:
    def unique(pairs):
        obj = {}
        for key, value in pairs:
            need(key not in obj, "DUPLICATE_JSON_KEY")
            obj[key] = value
        return obj
    obj = json.loads(raw.decode("utf-8-sig"), object_pairs_hook=unique)
    need(type(obj) is dict, "JSON_OBJECT")
    return obj


def safe(path: Path, name: str | None = None) -> Path:
    need(path.is_absolute() and path.is_file(), "SOURCE_PATH")
    if name:
        need(path.name == name, "WRONG_SOURCE_FILE")
    for part in (path, *path.parents):
        if part.exists():
            need(not part.is_symlink() and not (getattr(part.lstat(), "st_file_attributes", 0) & 1024),
                 "REPARSE_PATH")
    return path


def check_quiet() -> None:
    """Fail closed and explain which ARK process prevents an atomic patch."""
    if os.name != "nt":
        return
    command = (
        "$ErrorActionPreference='Stop';"
        "try {"
        "$p=@(Get-CimInstance Win32_Process -ErrorAction Stop | Where-Object {"
        "$_.ProcessId -ne $PID -and "
        "$_.Name -match '^(powershell|pwsh|python|pythonw)([.]exe)?$' -and "
        "$_.CommandLine -match '(Start-No11OneClick[.]ps1|Start-No11UnifiedLauncher[.]ps1|"
        "Start-No11PreopenStandby[.]ps1|Run-No11ReceivedSessionOperatorLive[.]ps1|"
        "no11_received_session_controller[.]py)'"
        "});"
        "foreach($item in $p){"
        "$role='ARK_PROCESS';"
        "if($item.CommandLine -match 'Start-No11OneClick[.]ps1'){$role='ONECLICK_UI'}"
        "elseif($item.CommandLine -match 'Start-No11PreopenStandby[.]ps1'){$role='PREOPEN_WORKER'}"
        "elseif($item.CommandLine -match 'Start-No11UnifiedLauncher[.]ps1'){$role='NATIVE_LAUNCHER'}"
        "elseif($item.CommandLine -match 'Run-No11ReceivedSessionOperatorLive[.]ps1|"
        "no11_received_session_controller[.]py'){$role='LIVE_ENGINE'};"
        "Write-Output ('NO11_BLOCKING_PROCESS='+$item.ProcessId+'|'+$role)"
        "};"
        "if($p.Count){exit 3};Write-Output 'NO11_BLOCKING_PROCESS_COUNT=0';"
        "} catch {Write-Output 'NO11_PROCESS_QUERY=FAILED';exit 4}"
    )
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=35, check=False,
    )
    for line in result.stdout.splitlines():
        if re.fullmatch(r"NO11_BLOCKING_PROCESS=[0-9]+\|(ONECLICK_UI|PREOPEN_WORKER|NATIVE_LAUNCHER|LIVE_ENGINE|ARK_PROCESS)", line):
            print(line, flush=True)
        elif line in ("NO11_BLOCKING_PROCESS_COUNT=0", "NO11_PROCESS_QUERY=FAILED"):
            print(line, flush=True)
    if result.returncode == 3:
        need(False, "ACTIVE_ARK_PROCESS")
    need(result.returncode == 0, "PROCESS_QUERY_FAILED")


def write_atomic(path: Path, content: bytes, previous: bytes) -> None:
    need(path.read_bytes() == previous, "CONCURRENT_EDIT")
    candidate = None
    try:
        with tempfile.NamedTemporaryFile(mode="wb", prefix=path.name + ".logfix-", dir=path.parent,
                                         delete=False) as out:
            candidate = Path(out.name)
            out.write(content)
            out.flush()
            os.fsync(out.fileno())
        need(path.read_bytes() == previous, "CONCURRENT_EDIT")
        os.replace(candidate, path)
        candidate = None
    finally:
        if candidate is not None:
            candidate.unlink(missing_ok=True)


def inspect(binding_file: Path) -> tuple[Path, bytes, bytes, bytes, bytes]:
    binding_file = safe(binding_file, "automatic-inputs.json")
    raw = binding_file.read_bytes()
    binding = parse_object(raw)
    need(binding.get("schemaId") == SCHEMA and binding.get("orderTransmission") is False,
         "BINDING_CONTRACT")
    bridge = safe(Path(binding["bridge"]), BRIDGE_FILE)
    before = bridge.read_bytes()
    old_sha = sha(before)
    need(binding.get("bridgeSha256") == old_sha, "BOUND_BRIDGE_SHA_CHANGED")
    probe = safe(Path(binding["transportProbe"]))
    need(sha(probe.read_bytes()) == binding.get("transportProbeSha256"),
         "PHYSICAL_TRANSPORT_PROBE_CHANGED")
    settings = parse_object(safe(Path(binding["settings"]), "settings.json").read_bytes())
    need(settings.get("schemaId") == "ARK_NO11_UNIFIED_LAUNCHER_SETTINGS_V1"
         and settings.get("orderTransmission") is False
         and settings.get("automaticOrderAuthorization") is False
         and settings.get("sameDayApprovalRequired") is True, "SAFETY_SETTINGS")

    if OLD not in before:
        need(before.count(NEW) == 1, "UNEXPECTED_BRIDGE_CONTENT")
        return bridge, before, before, raw, raw
    need(before.count(OLD) == 1 and before.count(NEW) == 0, "UNEXPECTED_BRIDGE_CONTENT")
    after = before.replace(OLD, NEW, 1)
    compile(after.decode("utf-8-sig"), str(bridge), "exec")

    matches = list(re.finditer(rb'("bridgeSha256"\s*:\s*")([0-9a-f]{64})(")', raw))
    need(len(matches) == 1, "BINDING_SHA_FIELD")
    match = matches[0]
    need(match.group(2).decode("ascii") == old_sha, "BINDING_SHA_FIELD_MISMATCH")
    new_raw = raw[:match.start(2)] + sha(after).encode("ascii") + raw[match.end(2):]
    updated = parse_object(new_raw)
    need(updated.get("bridgeSha256") == sha(after)
         and all(updated.get(k) == v for k, v in binding.items() if k != "bridgeSha256"),
         "BINDING_FIELDS_CHANGED")
    return bridge, before, after, raw, new_raw


def apply(binding_file: Path, *, live: bool = True, _test_mode: bool = False) -> str:
    bridge, original_bridge, updated_bridge, original_binding, updated_binding = inspect(binding_file)
    if original_bridge == updated_bridge:
        return "ALREADY_APPLIED"
    if not live:
        return "READY"
    need(os.name == "nt" or _test_mode, "WINDOWS_ONLY")
    if not _test_mode:
        check_quiet()
    store = binding_file.parent
    backup = store / ("transport-log-fix-backup-" + uuid.uuid4().hex)
    backup.mkdir(mode=0o700)
    (backup / "bridge.before.py").write_bytes(original_bridge)
    (backup / "automatic-inputs.before.json").write_bytes(original_binding)
    need((backup / "bridge.before.py").read_bytes() == original_bridge and
         (backup / "automatic-inputs.before.json").read_bytes() == original_binding,
         "BACKUP_FAILED")
    bridge_changed = False
    binding_changed = False
    try:
        write_atomic(bridge, updated_bridge, original_bridge)
        bridge_changed = True
        write_atomic(binding_file, updated_binding, original_binding)
        binding_changed = True
        need(bridge.read_bytes() == updated_bridge and binding_file.read_bytes() == updated_binding,
             "READBACK_FAILED")
        need(inspect(binding_file)[1] == inspect(binding_file)[2], "POSTINSTALL_PIN_FAILED")
    except BaseException:
        if binding_changed and binding_file.read_bytes() == updated_binding:
            write_atomic(binding_file, original_binding, updated_binding)
        if bridge_changed and bridge.read_bytes() == updated_bridge:
            write_atomic(bridge, original_bridge, updated_bridge)
        raise
    return "PASS"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binding", type=Path, required=True)
    parser.add_argument("--apply", action="store_true", help="Install only, never start trading")
    args = parser.parse_args()
    try:
        state = apply(args.binding, live=args.apply)
        print("NO11_TRANSPORT_ERROR_LOG_FIX=" + state)
        print("WHITE_ONECLICK_UI_CHANGED=False")
        print("EXCEL_TOUCHED=False")
        print("TRADE_LAUNCHED=False")
        print("ORDER_TRANSMISSION=False")
    except Exception as err:
        reason = str(err)
        if not re.fullmatch(r"NO11_TRANSPORT_LOG_FIX_[A-Z0-9_]+", reason):
            reason = "NO11_TRANSPORT_LOG_FIX_LOCAL_ERROR"
        print("NO11_TRANSPORT_ERROR_LOG_FIX=BLOCKED|" + reason)
        print("TRADE_LAUNCHED=False")
        print("ORDER_TRANSMISSION=False")
        raise SystemExit(2)


if __name__ == "__main__":
    main()
