#!/usr/bin/env python3
"""Windows-first authenticated restore of the 24 pinned MODE B GitHub source blobs.

TRANSPORT ONLY: no research grant, numeric prices, labels, fit, orders, or Frozen changes.
Uses the Windows user's existing authenticated GitHub CLI; never prints or stores a token.
"""
from __future__ import annotations
import argparse
import base64
import binascii
import datetime
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REPO = "Iam-2squared/J-quants-E"
SCOPE = ROOT / "MODE_B_SOURCE_SCOPE_DRAFT.json"
SCOPE_GIT_BLOB = "ba62c576dafdb7861e08332f973c0165e7c3c781"
OBJECT_COUNT = 24
OBJECT_BYTES = 51429816
SAFE = ("executionAllowed", "brokerWriteAllowed", "excelOrderWriteAllowed",
        "rssOrderFunctionAllowed", "liveTradingAllowed", "paperTradingAllowed",
        "automaticPromotionAllowed", "productionUpdateAllowed", "transmitted",
        "productionReady", "entryAllowed")


class RestoreError(RuntimeError):
    pass


def require(ok: bool, message: str) -> None:
    if not ok:
        raise RestoreError(message)


def git_blob_hash(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def load_pinned_sources(path: Path = SCOPE) -> list[dict[str, Any]]:
    raw = path.read_bytes()
    if git_blob_hash(raw) != SCOPE_GIT_BLOB:
        # Git for Windows may check out text JSON as CRLF. Only accept exact
        # LF-normalization back to the originally committed Git blob bytes.
        raw = raw.replace(b"\r\n", b"\n")
    require(git_blob_hash(raw) == SCOPE_GIT_BLOB, "MODE_B_SCOPE_BLOB_DRIFT")
    document = json.loads(raw)
    require(document.get("schema") == "ARK_V2_MODE_B_SOURCE_SCOPE_DRAFT_V1", "MODE_B_SCOPE_SCHEMA")
    require(document.get("validation_final_teachers_included") is False, "MODE_B_EVALUATION_FORBIDDEN")
    entries = document.get("source_objects")
    require(isinstance(entries, list) and len(entries) == OBJECT_COUNT, "MODE_B_SCOPE_COUNT")
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in entries:
        source_id = row["source_id"]
        require(isinstance(source_id, str) and source_id.startswith(REPO + "/"), "UNKNOWN_SOURCE_REPOSITORY")
        relative = source_id[len(REPO) + 1:]
        relative_path = PurePosixPath(relative)
        require(bool(relative_path.parts) and not relative_path.is_absolute()
                and ".." not in relative_path.parts and "\\" not in relative
                and ":" not in relative and relative.endswith(".csv.gz")
                and relative_path.parts[0] == "equities", "UNSAFE_OR_UNEXPECTED_SOURCE_PATH")
        relative = "raw/" + relative
        require(relative not in seen, "DUPLICATE_PINNED_SOURCE")
        seen.add(relative)
        require(row.get("dataset") in ("DAILY", "MASTER"), "UNEXPECTED_SOURCE_FAMILY")
        purposes = row.get("requested_dates_by_purpose")
        require(isinstance(purposes, dict) and bool(purposes)
                and set(purposes) <= {"HISTORY", "FIT_FEATURE", "FIT_TEACHER",
                                     "CAL_FEATURE", "CAL_TEACHER"}
                and all(isinstance(days, list) and days for days in purposes.values()),
                "EVALUATION_OR_UNSCOPED_SOURCE")
        require(type(row.get("bytes")) is int and row["bytes"] > 0
                and re.fullmatch(r"[0-9a-f]{64}", str(row.get("source_sha256", ""))) is not None
                and re.fullmatch(r"[0-9a-f]{40}", str(row.get("original_git_blob", ""))) is not None,
                "MISSING_SOURCE_HASH_OR_SIZE")
        result.append({**row, "repo": REPO, "relative": relative})
    require(sum(r["bytes"] for r in result) == OBJECT_BYTES, "MODE_B_SCOPE_TOTAL_BYTES")
    return result


def safe_target(root: Path, relative: str) -> Path:
    root = root.resolve()
    require(root.is_absolute(), "DESTINATION_MUST_BE_ABSOLUTE")
    parts = PurePosixPath(relative).parts
    require(bool(parts) and parts[0] == "raw" and ".." not in parts
            and "\\" not in relative and ":" not in relative, "DESTINATION_ESCAPE")
    path = root.joinpath(*parts)
    require(path.resolve().is_relative_to(root), "DESTINATION_ESCAPE")
    for p in (root, *[root.joinpath(*parts[:i]) for i in range(1, len(parts) + 1)]):
        if p.is_symlink() or (hasattr(p, "is_junction") and p.is_junction()):
            raise RestoreError("DESTINATION_LINK_OR_JUNCTION")
    require(not root.is_relative_to(ROOT.resolve()), "NO_RAW_FILES_INSIDE_REPOSITORY")
    return path


def verify_source(path: Path, row: dict[str, Any]) -> None:
    payload = path.read_bytes()
    require(len(payload) == row["bytes"], "SOURCE_SIZE_MISMATCH")
    require(hashlib.sha256(payload).hexdigest() == row["source_sha256"], "SOURCE_SHA256_MISMATCH")
    require(git_blob_hash(payload) == row["original_git_blob"], "SOURCE_GIT_BLOB_MISMATCH")


def github_blob(repo: str, blob: str, *, program: str = "gh") -> bytes:
    require(repo == REPO and re.fullmatch(r"[0-9a-f]{40}", blob) is not None,
            "INVALID_GITHUB_SOURCE")
    require(shutil.which(program) is not None, "GITHUB_CLI_REQUIRED_INSTALL_GH")
    args = [program, "api", f"repos/{repo}/git/blobs/{blob}",
            "-H", "Accept: application/vnd.github+json"]
    try:
        response = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                  timeout=120, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RestoreError("GITHUB_AUTHENTICATED_BLOB_TRANSPORT_FAILED") from exc
    require(response.returncode == 0, "GITHUB_AUTH_REQUIRED_OR_PRIVATE_BLOB_UNAVAILABLE")
    try:
        result = json.loads(response.stdout.decode("utf-8"))
        require(result.get("encoding") == "base64", "GITHUB_BLOB_EXPECTED_BASE64")
        require(result.get("sha") == blob, "GITHUB_BLOB_IDENTITY_MISMATCH")
        content = result.get("content")
        require(isinstance(content, str) and bool(content.strip()), "GITHUB_BLOB_CONTENT_EMPTY")
        payload = base64.b64decode("".join(content.split()), validate=True)
        require(type(result.get("size")) is int and len(payload) == result["size"],
                "GITHUB_BLOB_SIZE")
        require(git_blob_hash(payload) == blob, "GITHUB_BLOB_SHA_MISMATCH")
    except (UnicodeDecodeError, ValueError, KeyError, TypeError, binascii.Error) as exc:
        raise RestoreError("GITHUB_BLOB_RESPONSE_INVALID") from exc
    return payload


def publish_verified(target: Path, payload: bytes, row: dict[str, Any]) -> None:
    require(len(payload) == row["bytes"], "DOWNLOAD_SIZE_MISMATCH")
    require(hashlib.sha256(payload).hexdigest() == row["source_sha256"], "DOWNLOAD_SHA256_MISMATCH")
    require(git_blob_hash(payload) == row["original_git_blob"], "DOWNLOAD_GIT_BLOB_MISMATCH")
    target.parent.mkdir(parents=True, exist_ok=True)
    require(not target.exists(), "NEVER_OVERWRITE_EXISTING_SOURCE")
    temp: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(dir=target.parent, prefix=".ark-restore-", delete=False) as output:
            temp = Path(output.name)
            output.write(payload)
            output.flush()
            os.fsync(output.fileno())
        verify_source(temp, row)
        os.link(temp, target)  # NTFS exclusive publish; never replace.
    finally:
        if temp is not None:
            temp.unlink(missing_ok=True)


def restore(dest: Path, sources: list[dict[str, Any]], *,
            retrieve=github_blob, dry_run: bool = False) -> dict[str, Any]:
    objects = []
    for index, row in enumerate(sources, 1):
        path = safe_target(dest, row["relative"])
        if path.is_file():
            verify_source(path, row)
            status = "VERIFIED_EXISTING"
        elif dry_run:
            status = "MISSING_NO_TRANSFER"
        else:
            require(not path.exists(), "SOURCE_NOT_REGULAR_FILE")
            payload = retrieve(row["repo"], row["original_git_blob"])
            publish_verified(path, payload, row)
            verify_source(path, row)
            status = "RESTORED_AND_VERIFIED"
        objects.append({"index": index, "source_sha256": row["source_sha256"],
                        "bytes": row["bytes"], "relative": row["relative"], "status": status})
    verified = sum(o["status"] != "MISSING_NO_TRANSFER" for o in objects)
    return {
        "schema": "ARK_V2_WINDOWS_SOURCE_TRANSPORT_V1",
        "status": "SOURCE_BYTES_VERIFIED" if verified == len(sources) else "SOURCE_BYTES_MISSING",
        "mode": "TRANSPORT_ONLY", "objects": objects,
        "objects_verified": verified, "objects_expected": len(sources),
        "source_bytes_total": sum(o["bytes"] for o in objects if o["status"] != "MISSING_NO_TRANSFER"),
        "market_numeric_price_reads": 0, "market_fits": 0, "market_calibrations": 0,
        "source_profile_adopted": False, "market_grant_created": False,
        "new_provider_acquisition": False, **{flag: False for flag in SAFE},
    }


def default_dest() -> Path:
    local = os.environ.get("LOCALAPPDATA")
    if not local:
        raise RestoreError("WINDOWS_LOCALAPPDATA_NOT_AVAILABLE")
    return Path(local) / "ArkTerminal" / "SelectorV2" / "Sources"


def write_private_receipt(dest: Path, receipt: dict[str, Any]) -> Path:
    # The verified source may live in admin-owned ProgramData. Keep transport
    # receipts in the existing user's profile, not next to protected originals.
    home = os.environ.get("LOCALAPPDATA")
    if not home:
        raise RestoreError("WINDOWS_LOCALAPPDATA_NOT_AVAILABLE")
    root = Path(home) / "ArkTerminal" / "SelectorV2" / "TransportReceipts"
    require(not root.resolve().is_relative_to(ROOT.resolve()), "PRIVATE_RECEIPT_IN_REPOSITORY")
    root.mkdir(parents=True, exist_ok=True)
    name = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    path = root / f"win-source-{name}.json"
    with path.open("x", encoding="utf-8") as output:
        json.dump(receipt, output, ensure_ascii=False, sort_keys=True, indent=2)
    return path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("plan", "restore", "verify"))
    parser.add_argument("--destination", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.operation != "plan":
            require(os.name == "nt", "WINDOWS_LOCAL_HOST_REQUIRED")
        sources = load_pinned_sources()
        destination = args.destination or default_dest()
        receipt = restore(destination, sources, dry_run=args.operation != "restore")
        if args.operation == "verify":
            require(receipt["objects_verified"] == OBJECT_COUNT, "SOURCE_OBJECTS_NOT_ALL_VERIFIED")
        if args.operation != "plan":
            receipt["private_receipt"] = str(write_private_receipt(destination, receipt))
        print(json.dumps({key: receipt[key] for key in (
            "schema", "status", "mode", "objects_verified", "objects_expected",
            "source_bytes_total", "market_numeric_price_reads", "market_fits")}))
        return 0
    except (RestoreError, OSError, ValueError, KeyError) as exc:
        print(json.dumps({"status": "BLOCKED", "reason": str(exc),
                          "objects_verified": "NOT_ESTABLISHED", "market_numeric_price_reads": 0,
                          "market_fits": 0, "market_grant_created": False}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    sys.exit(main())
