"""Prepare a pinned installer bundle for a *direct cmd.exe -> Python* launch.

No LIVE, Excel or order code is imported or called by this module. Unlike a
PowerShell bootstrap that remains in the installer ancestry, direct CMD launch
lets the ORIGINAL quiet-gate examine the real process tree unmodified.

Default is verification; creation needs --stage and explicit local inputs.
The stage folder lives outside the installed OneClick and evidence roots.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import uuid

SCHEMA = "ARK_NO11_ANYTIME_PINNED_CMD_STAGE_V1"
MODULE = "stage_no11_anytime_cmd.py"
INSTALL = "install_no11_anytime_preopen.py"
FILES = {
    INSTALL: "6488d3aeafd1bc7d2a28d3e67a43c6f8c3623393",
    "no11_anytime_preopen.py": "e5b1c2c5263e525092a1028d9c734c2a14f4efac",
    "no11_nightly_resume.py": "6c3668c47991e1407464c7049cd662ff9985ad35",
    "no11_oneclick_display_transform.py": "4c8ce6fb796320c00e80f0385437162925cb3921",
    "no11_oneclick_display_v2.py": "f285ae780e9e2605003c23c3729b5099adbbf3d3",
    "install_no11_oneclick_display_v2.py": "1b4923fb948a0e30fcfe8cb4a281f77a4e4fdef5",
    "install_no11_oneclick_display_overlay_compat.py": "e234c9fee85703329d9cd41444e64660468bee16",
}
ALL_MODULES = frozenset(FILES) | {MODULE}
MANIFEST = "verified-stage.json"
RUNNER = "Run-No11Anytime.cmd"
CODESAFE = re.compile(r"^[a-zA-Z0-9_ .:\\/=-]+$")
SENSITIVE = re.compile(r"[%!^&|<>()\r\n\x00-\x1f]")


def need(ok: bool, code: str):
    if not ok:
        raise ValueError("NO11_CMD_STAGE_" + code)


def git_blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") +
                        b"\0" + raw).hexdigest()


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def checked(path, *, file=False, folder=False):
    path = Path(path)
    need(path.is_absolute(), "ABSOLUTE_PATH_REQUIRED")
    for item in (path, *path.parents):
        if item.exists() or item.is_symlink():
            attrs = getattr(item.lstat(), "st_file_attributes", 0)
            need(not item.is_symlink() and not (attrs & 1024),
                 "REPARSE_PATH_UNSAFE")
    if file:
        need(path.is_file(), "FILE_MISSING")
    if folder:
        need(path.is_dir(), "DIRECTORY_MISSING")
    return path


def cmd_path(value):
    result = str(value)
    need(result.isascii() and not SENSITIVE.search(result)
         and '"' not in result and len(result) < 260
         and Path(result).is_absolute(), "UNSAFE_WINDOWS_CMD_PATH")
    return result


def raw_pins(src: Path):
    src = checked(src, folder=True)
    result = {}
    for name, blob_sha in FILES.items():
        p = checked(src / name, file=True)
        data = p.read_bytes()
        need(0 < len(data) < 2_000_000 and git_blob(data) == blob_sha,
             "MODULE_PIN_" + name.replace(".", "_").upper())
        result[name] = data
    this = checked(src / MODULE, file=True).read_bytes()
    need(0 < len(this) < 100_000, "STAGER_SOURCE_SIZE")
    result[MODULE] = this
    return result


def command(python_binary: Path, store: Path) -> bytes:
    """No inline PowerShell; verification Python exits BEFORE installer starts."""
    py = cmd_path(python_binary)
    root = cmd_path(store)
    cmd = f"""@echo off
setlocal DisableDelayedExpansion
if not "%~2"=="" goto INVALID
if /I "%~1"=="probe" goto CHECK
if /I "%~1"=="audit" goto CHECK
if /I "%~1"=="apply" goto CHECK
goto INVALID

:CHECK
"{py}" -B -X utf8 "%~dp0{MODULE}" --verify "%~dp0."
if errorlevel 1 exit /b 2
if /I "%~1"=="probe" goto PROBE
if /I "%~1"=="audit" goto AUDIT
if /I "%~1"=="apply" goto APPLY
goto INVALID

:PROBE
"{py}" -B -X utf8 "%~dp0{INSTALL}" --store "{root}" --probe-gate
exit /b %ERRORLEVEL%

:AUDIT
"{py}" -B -X utf8 "%~dp0{INSTALL}" --store "{root}"
exit /b %ERRORLEVEL%

:APPLY
echo Confirm ALL: ARK, OneClick and nightly are STOPPED.
echo Confirm broker orders, fills and holdings independently checked.
echo Only use OUTSIDE 08:00-15:40 JST. Never remove claims or receipts.
choice /C YN /N /M "Confirm broker orders/fills/positions reviewed and ARK stopped? Y/N: "
if errorlevel 2 exit /b 2
if not errorlevel 1 exit /b 2
"{py}" -B -X utf8 "%~dp0{INSTALL}" --store "{root}" --apply
exit /b %ERRORLEVEL%

:INVALID
echo NO11_CMD_STAGE=BLOCKED_INVALID_ACTION
echo VALID_ACTIONS=probe,audit,apply
exit /b 2
"""
    # Literal CRLF needed for cmd.exe even when repository checkout uses LF.
    return cmd.replace("\n", "\r\n").encode("ascii")


def plan(source_dir, store, python_binary, stage_parent, *, commit):
    source_dir = checked(source_dir, folder=True)
    store = checked(store, folder=True)
    py = checked(python_binary, file=True)
    parent = checked(stage_parent.parent, folder=True)
    need(stage_parent.parent == parent, "PARENT_SCOPE_CHANGED")
    need(type(commit) is str and re.fullmatch(r"[a-f0-9]{40}", commit),
         "SOURCE_COMMIT_INVALID")
    cmd_path(store)
    cmd_path(py)
    cmd_path(stage_parent)
    need(py.name.lower() == "python.exe" if os.name == "nt" else True,
         "PYTHON_EXECUTABLE_UNVERIFIED")
    settings = checked(store / "settings.json", file=True)
    binding = checked(store / "automatic-inputs.json", file=True)
    config = json.loads(binding.read_text(encoding="utf-8-sig"))
    need(config.get("schemaId") == "ARK_NO11_AUTOMATIC_LAUNCHER_BINDING_V1"
         and config.get("orderTransmission") is False
         and str(config.get("python")) == str(py), "BOUND_PYTHON_UNVERIFIED")
    cfg = json.loads(settings.read_text(encoding="utf-8-sig"))
    need(cfg.get("sameDayApprovalRequired") is True
         and cfg.get("automaticOrderAuthorization") is False
         and cfg.get("orderTransmission") is False, "SAFETY_SETTINGS_CHANGED")
    copied = raw_pins(source_dir)
    need(not stage_parent.is_symlink(), "STAGE_ROOT_REPARSE")
    stage_parent.mkdir(exist_ok=True)
    checked(stage_parent, folder=True)
    path = stage_parent / ("verified-" + uuid.uuid4().hex)
    path.mkdir(exist_ok=False)
    copied_sha = {}
    for name, data in copied.items():
        dest = path / name
        with dest.open("xb") as out:
            out.write(data)
            out.flush()
            os.fsync(out.fileno())
        copied_sha[name] = sha(data)
    runner = command(py, store)
    with (path / RUNNER).open("xb") as out:
        out.write(runner)
        out.flush()
        os.fsync(out.fileno())
    rec = {
        "schemaId": SCHEMA,
        "releaseCommit": commit,
        "store": str(store),
        "python": str(py),
        "sourceSha256": copied_sha,
        "sourceGitBlobs": dict(FILES),
        "runnerSha256": sha(runner),
        "settingsSha256": sha(settings.read_bytes()),
        "bindingSha256": sha(binding.read_bytes()),
        "orderTransmission": False,
        "tradeStarted": False,
        "afterHoursApplyOnly": True,
    }
    with (path / MANIFEST).open("xb") as out:
        out.write((json.dumps(rec, sort_keys=True, separators=(",", ":")) +
                   "\n").encode("ascii"))
        out.flush()
        os.fsync(out.fileno())
    verify(path)
    return path / RUNNER


def verify(stage):
    path = checked(stage, folder=True)
    manifest = checked(path / MANIFEST, file=True)
    raw = manifest.read_bytes()
    need(0 < len(raw) < 100_000, "MANIFEST_SIZE")
    rec = json.loads(raw.decode("ascii"))
    need(type(rec) is dict and rec.get("schemaId") == SCHEMA
         and rec.get("sourceGitBlobs") == FILES
         and rec.get("orderTransmission") is False
         and rec.get("tradeStarted") is False
         and rec.get("afterHoursApplyOnly") is True
         and re.fullmatch(r"[a-f0-9]{40}", str(rec.get("releaseCommit", ""))),
         "MANIFEST_CONTRACT")
    need(type(rec.get("sourceSha256")) is dict and
         set(rec["sourceSha256"]) == ALL_MODULES, "MANIFEST_SOURCE_SET")
    for name in ALL_MODULES:
        data = checked(path / name, file=True).read_bytes()
        need(0 < len(data) < 2_000_000 and
             sha(data) == rec["sourceSha256"][name], "BUNDLE_SOURCE_CHANGED")
        if name in FILES:
            need(git_blob(data) == FILES[name], "BUNDLE_GIT_PIN_CHANGED")
    runner = checked(path / RUNNER, file=True).read_bytes()
    python_binary = checked(rec.get("python", ""), file=True)
    store = checked(rec.get("store", ""), folder=True)
    need(runner == command(python_binary, store) and
         sha(runner) == rec.get("runnerSha256"), "BUNDLE_RUNNER_CHANGED")
    for name, key in (("settings.json", "settingsSha256"),
                      ("automatic-inputs.json", "bindingSha256")):
        need(sha(checked(store / name, file=True).read_bytes()) == rec[key],
             "LOCAL_INSTALL_CHANGED_RESTAGE")
    print("NO11_CMD_STAGE_BUNDLE=VERIFIED")
    print("ORIGINAL_NATIVE_PROCESS_GATE=UNCHANGED")
    print("ORDER_TRANSMISSION=False")
    return True


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--stage", action="store_true")
    group.add_argument("--verify", type=Path)
    ap.add_argument("--source-dir", type=Path)
    ap.add_argument("--store", type=Path)
    ap.add_argument("--python", type=Path)
    ap.add_argument("--stage-root", type=Path)
    ap.add_argument("--source-commit")
    args = ap.parse_args(argv)
    try:
        if args.verify is not None:
            need(not any((args.source_dir, args.store, args.python,
                          args.stage_root, args.source_commit)),
                 "VERIFY_ARGUMENTS_UNSAFE")
            verify(args.verify)
        else:
            need(all((args.source_dir, args.store, args.python,
                      args.stage_root, args.source_commit)), "STAGE_ARGUMENTS_MISSING")
            run = plan(args.source_dir, args.store, args.python,
                       args.stage_root, commit=args.source_commit)
            print("NO11_CMD_STAGE=PREPARED_NO_INSTALL")
            print("NO11_CMD_STAGE_RUNNER=" + str(run))
            print("NO11_CMD_STAGE_ACTIONS=probe,audit,apply")
        return 0
    except (OSError, ValueError, UnicodeError, TypeError, KeyError) as exc:
        code = str(exc)
        if re.fullmatch(r"NO11_CMD_STAGE_[A-Z0-9_]+", code) is None:
            code = "NO11_CMD_STAGE_UNVERIFIED_IO_OR_SOURCE"
        print("NO11_CMD_STAGE=BLOCKED|" + code)
        print("INSTALLED_ONECLICK_CHANGED=False")
        return 2
    finally:
        print("TRADE_STARTED=False")
        print("EXCEL_TOUCHED=False")
        print("ORDER_TRANSMISSION=False")


if __name__ == "__main__":
    sys.exit(main())
