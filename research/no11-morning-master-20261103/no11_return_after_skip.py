#!/usr/bin/env python3
"""Read-only source continuity across days when the operator did not trade/update.

Reuse exact previously verified nightly artifacts as *historical* evidence only.
No prices are generated, no handoff is re-dated, and no order is authorized.
The real next-session D100/G1/previous-1M must still be acquired by native RSS.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re

JST = timezone(timedelta(hours=9))
DAY = re.compile(r"20\d\d-\d\d-\d\d\Z")
SHA = re.compile(r"[a-f0-9]{64}\Z")
SYMBOL = re.compile(r"[0-9A-Z]{4}\.T\Z")


def need(ok: bool, code: str):
    if not ok:
        raise ValueError("NO11_RETURN_" + code)


def safe_file(path: Path, root: Path | None = None) -> Path:
    p = Path(path)
    need(p.is_absolute(), "PATH_ABSOLUTE_REQUIRED")
    for part in (p, *p.parents):
        if part.exists() or part.is_symlink():
            need(not part.is_symlink() and not (getattr(part.lstat(), "st_file_attributes", 0) & 1024),
                 "REPARSE_POINT")
    need(p.is_file(), "FILE_MISSING")
    if root is not None:
        need(p.resolve().is_relative_to(root.resolve()), "FILE_OUTSIDE_PRIVATE_ROOT")
    return p


def safe_dir(path: Path) -> Path:
    p = Path(path)
    need(p.is_absolute() and p.is_dir() and not p.is_symlink(), "ROOT_UNSAFE")
    return p.resolve()


def load(p: Path, root: Path | None = None) -> tuple[dict, str]:
    raw = safe_file(p, root).read_bytes()
    need(0 < len(raw) <= 2_000_000, "SOURCE_SIZE")
    def pairs(items):
        d = {}
        for key, value in items:
            need(key not in d, "DUPLICATE_JSON_KEY")
            d[key] = value
        return d
    body = json.loads(raw.decode("utf-8-sig"), object_pairs_hook=pairs,
                      parse_constant=lambda _: need(False, "NONFINITE_JSON"))
    need(type(body) is dict, "OBJECT_REQUIRED")
    return body, hashlib.sha256(raw).hexdigest()


def verify_pointer(private_root: Path, path: Path, expected_date: str) -> dict:
    need(DAY.fullmatch(expected_date) is not None, "DATE_INVALID")
    root = safe_dir(private_root)
    folder = root / "prepared-days"
    need(path.parent.resolve() == folder.resolve() and
         path.name == expected_date + ".json", "POINTER_PATH_INVALID")
    p, _ = load(path, root)
    need(p.get("schemaId") == "ARK_NO11_NIGHTLY_LAUNCHER_HANDOFF_V1" and
         p.get("sessionDate") == expected_date and
         p.get("productionReady") is False and
         p.get("orderTransmission") is False and
         p.get("humanReviewClaimed") is False, "POINTER_CONTRACT")
    previous = p.get("previousSession")
    need(type(previous) is str and DAY.fullmatch(previous) is not None and
         date.fromisoformat(previous) < date.fromisoformat(expected_date),
         "ASOF_CONTRACT")
    source_sha = p.get("handoffSha256")
    need(type(source_sha) is str and SHA.fullmatch(source_sha) is not None,
         "HANDOFF_HASH")
    src = safe_file(Path(p.get("handoff", "")), root)
    need(src.name == "morning-handoff-" + source_sha + ".json",
         "HANDOFF_FILENAME")
    hand, sha = load(src, root)
    need(sha == source_sha, "HANDOFF_CHANGED")
    symbols = hand.get("selectedSymbols")
    need(hand.get("schemaId") == "ARK_NO11_MORNING_MASTER_HANDOFF_V1" and
         hand.get("sessionDate") == expected_date and
         hand.get("previousSession") == previous and
         hand.get("orderTransmission") is False and
         hand.get("productionReady") is False and
         hand.get("reviewStatus") == "NOT_REVIEWED" and
         hand.get("datedMasterCreated") is False and
         type(symbols) is list and 0 < len(symbols) <= 47 and
         symbols == p.get("selectedSymbols") and
         len(symbols) == p.get("selectedCount") and
         len(set(symbols)) == len(symbols) and
         all(type(x) is str and SYMBOL.fullmatch(x) for x in symbols),
         "HANDOFF_CONTRACT")
    return {"sessionDate": expected_date, "sourceAsOf": previous,
            "selectedCount": len(symbols),
            "handoffSha256": sha}


def inspect(binding_file: Path, today: str | None = None) -> dict:
    today = today or datetime.now(JST).date().isoformat()
    need(type(today) is str and DAY.fullmatch(today) is not None, "TODAY")
    today_date = date.fromisoformat(today)
    binding, _ = load(Path(binding_file))
    need(binding.get("schemaId") == "ARK_NO11_AUTOMATIC_LAUNCHER_BINDING_V1"
         and binding.get("orderTransmission") is False, "BINDING")
    root = safe_dir(Path(binding.get("dailyCycleRoot", "")))
    folder = root / "prepared-days"
    base = {"schemaId": "ARK_NO11_RETURN_DAY_READINESS_V1",
            "today": today, "canTrade": False,
            "tradeAuthorizationGranted": False,
            "sourceDatesRelabeled": False,
            "brokerOrdersTouched": False,
            "originalArtifactsModified": False,
            "freshActualRssRequired": True,
            "orderTransmission": False}
    if not folder.is_dir():
        return {**base, "state": "NO_PREPARED_DAY", "reason": "NO_NIGHTLY_HISTORY"}
    need(not folder.is_symlink(), "POINTER_FOLDER_UNSAFE")
    latest: tuple[str, Path] | None = None
    count = 0
    for p in folder.iterdir():
        count += 1
        need(count <= 2000, "TOO_MANY_POINTER_FILES")
        need(not p.is_symlink(), "POINTER_REPARSE")
        if not p.is_file() or p.suffix != ".json":
            continue
        day = p.stem
        need(DAY.fullmatch(day) is not None, "POINTER_NAME_INVALID")
        # A future-dated pointer is never used to justify today's session.
        if day > today:
            continue
        if latest is None or day > latest[0]:
            latest = (day, p)
    if latest is None:
        return {**base, "state": "NO_PREPARED_DAY", "reason": "NO_VALID_DAY_POINTER"}
    last, path = latest
    try:
        proof = verify_pointer(root, path, last)
    except (OSError, ValueError, KeyError, TypeError):
        return {**base, "state": "BLOCKED_SOURCE_INTEGRITY",
                "reason": "LATEST_POINTER_UNVERIFIED",
                "latestPointerDate": last}
    if last == today:
        return {**base, **proof, "state": "CURRENT_DAY_HANDOFF_VERIFIED",
                "freshActualRssRequired": False,
                "reason": "STILL_REQUIRES_NORMAL_SAME_DAY_BROKER_GATES"}
    # This only reuses source history; the last day's missing market data
    # cannot be replaced with data received on a previous day.
    return {**base, **proof, "state": "CATCHUP_REQUIRED",
            "reason": "REUSE_LAST_VERIFIED_BASE_FETCH_ACTUAL_LATEST_RSS",
            "daysSinceLastHandoff": (today_date - date.fromisoformat(last)).days,
            "marketDataForTodayAlreadyCollected": False,
            "staleHandoffMayBeTraded": False,
            "requiresNewDailyD100": True,
            "requiresNewChart50AndG1": True,
            "requiresRecentPrevious1M": True,
            "weeklyPoolMayNeedRebuild": True}


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--binding", type=Path, required=True)
    p.add_argument("--today", default=None)
    args = p.parse_args(argv)
    try:
        print(json.dumps(inspect(args.binding, args.today), ensure_ascii=False, sort_keys=True,
                         separators=(",", ":")))
    except (OSError, ValueError, KeyError, TypeError):
        print(json.dumps({"schemaId": "ARK_NO11_RETURN_DAY_READINESS_V1",
                          "state": "BLOCKED_SOURCE_INTEGRITY", "canTrade": False,
                          "freshActualRssRequired": True, "orderTransmission": False}))
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
