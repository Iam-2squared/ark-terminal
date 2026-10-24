"""Windows NTFS owner channel security; no Linux account or UID dependency.

The controller is a fixed administrator-installed path. PowerShell's built-in
Get-Acl inspects NTFS owner and DACL before any JSON grant is read. Broad write
permissions, worker write to controller, elevation, junctions and symlinks fail
closed. Pure verify_acl_report is testable without a Windows runtime.
"""
from __future__ import annotations

import base64
import json
import os
from pathlib import Path
import re
import subprocess
from typing import Any

from .exact_math import V2Error

CONTROL_ROOT = Path("C:/ProgramData/ArkTerminal/SelectorV2")
HOST_CONFIG = CONTROL_ROOT / "owner-channel.json"
ADMIN_SID = "S-1-5-32-544"
SYSTEM_SID = "S-1-5-18"
CONTROLLERS = frozenset((ADMIN_SID, SYSTEM_SID))
# WriteData, AppendData, WriteEA, DeleteChild, WriteAttributes, Delete,
# WriteDac, WriteOwner, GenericWrite and GenericAll.
MUTATE_MASK = 0x00000156 | 0x00010000 | 0x00040000 | 0x00080000 | 0x10000000 | 0x40000000
READ_MASK = 0x00000001 | 0x00000080 | 0x00020000


def verify_acl_report(report: dict[str, Any], *, purpose: str) -> str:
    """Verify allowed ACL principals and owner; return current user SID."""
    if purpose not in {"control", "journal"}:
        raise V2Error("WIN_ACL_UNKNOWN_PURPOSE")
    owner, user = report.get("owner_sid"), report.get("user_sid")
    if not (isinstance(owner, str) and isinstance(user, str)
            and re.fullmatch(r"S-\d(?:-\d+)+", owner)
            and re.fullmatch(r"S-\d(?:-\d+)+", user)):
        raise V2Error("WIN_ACL_OWNER_OR_WORKER_SID")
    if report.get("elevated") is not False or user in CONTROLLERS:
        raise V2Error("WIN_WORKER_MUST_BE_UNELEVATED")
    if owner not in (CONTROLLERS if purpose == "control" else CONTROLLERS | {user}):
        raise V2Error("WIN_UNTRUSTED_ACL_OWNER")
    rules = report.get("access")
    if not isinstance(rules, list) or not rules:
        raise V2Error("WIN_MISSING_DACL")
    has_user_read = False
    has_user_write = False
    for ace in rules:
        sid = ace.get("sid") if isinstance(ace, dict) else None
        mask = ace.get("mask") if isinstance(ace, dict) else None
        kind = ace.get("kind") if isinstance(ace, dict) else None
        if (not isinstance(sid, str) or re.fullmatch(r"S-\d(?:-\d+)+", sid) is None
                or type(mask) is not int or kind not in ("Allow", "Deny")):
            raise V2Error("WIN_UNRECOGNIZED_ACL_ENTRY")
        mask &= 0xffffffff
        if kind != "Allow":
            continue
        if sid == user:
            has_user_read |= bool(mask & READ_MASK)
            has_user_write |= bool(mask & MUTATE_MASK)
        if (mask & MUTATE_MASK) and sid not in CONTROLLERS and not (
                purpose == "journal" and sid == user):
            raise V2Error("WIN_UNTRUSTED_ACL_WRITE")
    if not has_user_read or (purpose == "journal" and not has_user_write):
        raise V2Error("WIN_WORKER_ACCESS_MISSING")
    if purpose == "control" and has_user_write:
        raise V2Error("WIN_WORKER_CAN_CHANGE_OWNER_CONTROL")
    return user


def no_reparse(path: Path) -> None:
    """Reject all symlink/junction/reparse ancestors, including NTFS junctions."""
    if not path.is_absolute():
        raise V2Error("WIN_CHANNEL_PATH_NOT_ABSOLUTE")
    for candidate in (path, *path.parents):
        if candidate.is_symlink() or (hasattr(candidate, "is_junction") and candidate.is_junction()):
            raise V2Error("WIN_CHANNEL_LINK_OR_JUNCTION")
        try:
            attrs = getattr(candidate.stat(), "st_file_attributes", 0)
        except FileNotFoundError:
            continue
        except AttributeError:
            continue
        if attrs & 0x400:  # FILE_ATTRIBUTE_REPARSE_POINT
            raise V2Error("WIN_CHANNEL_REPARSE_POINT")


def read_acl(path: Path) -> dict[str, Any]:
    if os.name != "nt":
        raise V2Error("WIN_ACL_REQUIRES_WINDOWS")
    no_reparse(path)
    # Embed UTF-16LE base64 of the literal path to prevent PowerShell injection.
    path_b64 = base64.b64encode(str(path).encode("utf-16-le")).decode("ascii")
    script = (
        "$ErrorActionPreference='Stop';"
        "$p=[Text.Encoding]::Unicode.GetString([Convert]::FromBase64String('"
        + path_b64
        + "'));"
        "$a=Get-Acl -LiteralPath $p;"
        "$id=[Security.Principal.WindowsIdentity]::GetCurrent();"
        "$principal=New-Object Security.Principal.WindowsPrincipal($id);"
        "$owner=([Security.Principal.NTAccount]$a.Owner).Translate("
        "[Security.Principal.SecurityIdentifier]).Value;"
        "$entries=@(foreach($r in $a.Access){ "
        "$sid=$r.IdentityReference.Translate([Security.Principal.SecurityIdentifier]).Value;"
        "@{sid=$sid;mask=[long]$r.FileSystemRights;"
        "kind=$r.AccessControlType.ToString()} });"
        "@{owner_sid=$owner;user_sid=$id.User.Value;"
        "elevated=$principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator);"
        "access=$entries}|ConvertTo-Json -Compress -Depth 5"
    )
    encoded = base64.b64encode(script.encode("utf-16-le")).decode("ascii")
    try:
        process = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            timeout=20, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise V2Error("WIN_ACL_PROBE_NOT_AVAILABLE") from exc
    if process.returncode:
        if os.environ.get("GITHUB_ACTIONS") == "true":
            # Diagnostics in an ephemeral test runner only, never in live logs.
            detail = process.stderr.decode("utf-8", errors="replace")[-1000:]
            raise V2Error("WIN_ACL_PROBE_FAILED_TEST_ONLY:" + detail)
        raise V2Error("WIN_ACL_PROBE_FAILED")
    try:
        value = json.loads(process.stdout.decode("utf-8-sig"))
    except (ValueError, UnicodeDecodeError) as exc:
        raise V2Error("WIN_ACL_RESULT_INVALID") from exc
    if not isinstance(value, dict):
        raise V2Error("WIN_ACL_RESULT_INVALID")
    if isinstance(value.get("access"), dict):
        value["access"] = [value["access"]]
    return value


def verify_path(path: Path, *, purpose: str, directory: bool = False) -> str:
    no_reparse(path)
    if directory != path.is_dir() or not path.exists():
        raise V2Error("WIN_CHANNEL_OBJECT_TYPE")
    return verify_acl_report(read_acl(path), purpose=purpose)


def validate_control_config(config: Path = HOST_CONFIG) -> str:
    if os.name != "nt":
        raise V2Error("WIN_CHANNEL_REQUIRES_WINDOWS")
    if config != HOST_CONFIG:
        raise V2Error("WIN_HOST_CONFIG_NOT_FIXED")
    verify_path(CONTROL_ROOT, purpose="control", directory=True)
    return verify_path(config, purpose="control")
