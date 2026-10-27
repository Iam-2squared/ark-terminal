#!/usr/bin/env python3
"""Build UNREVIEWED local security/corporate-action queue from ACTUAL RssMarket.

Input: immutable 2026-10-27 selected-session reference + original Chart50
prescreen + original prior-day G1 PASS mask. No Excel/broker/network.
The queue is NOT an evidence receipt, not a datedMaster and never passes
EXTERNALLY_REVIEWED. Raw RSS ex-date cells are observations, NOT clearance.
Only explicitly independently sourced and reviewed documents can later
provide the existing NO11 input-prerequisite contract's real evidence.

Private local output only, SHA256 immutable, no actual quote/symbols printed.
"""
from __future__ import annotations

import argparse
from datetime import datetime
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
import re
import sys
from typing import Any

DAY = "2026-10-27"
PRIOR = "2026-10-26"
STAMP = re.compile(r"^2026-10-27T\d\d:\d\d:\d\d(?:\.\d{3})?\+09:00$")
SYMBOL = re.compile(r"^[0-9A-Z]{4}\.T$")
SHA256 = re.compile(r"^[a-f0-9]{64}$")
REFERENCE_FILENAME = re.compile(r"^session-reference-([a-f0-9]{64})\.json$")
SECTIONS = {"東証P": "PRIME", "東証S": "STANDARD", "東証G": "GROWTH"}
QUEUE_SCHEMA = "ARK_NO11_20261027_EXTERNAL_SECURITY_REVIEW_QUEUE_UNREVIEWED_V1"


def need(condition: bool, code: str) -> None:
    if not condition:
        raise ValueError("NO11_REAL_RSS_REVIEW_" + code)


def private(path: Path, *, folder: bool = False) -> Path:
    need(path.is_absolute(), "ABSOLUTE_PRIVATE_PATH_REQUIRED")
    path = path.absolute()
    need(path.exists() and (path.is_dir() if folder else path.is_file())
         and not path.is_symlink()
         and all(not p.is_symlink() for p in path.parents),
         "PRIVATE_PATH_REQUIRED")
    return path


def load(path: Path, limit: int = 4_000_000) -> tuple[dict, bytes]:
    p = private(path)
    need(0 < p.stat().st_size <= limit, "PRIVATE_JSON_SIZE")
    data = p.read_bytes()
    result = json.loads(data.decode("utf-8-sig"))
    need(type(result) is dict, "JSON_OBJECT_REQUIRED")
    return result, data


def timestamp(value: Any) -> datetime:
    need(type(value) is str and STAMP.fullmatch(value),
         "SESSION_RECEIPT_TIMESTAMP")
    return datetime.fromisoformat(value)


def price(value: Any) -> bool:
    if type(value) not in (int, float):
        return False
    try:
        n = Decimal(str(value))
    except (ValueError, InvalidOperation):
        return False
    return n.is_finite() and 0 < n <= Decimal("1000000000")


def check_reference(data: dict, payload: bytes, filename: Path,
                    chart: dict, mask: dict) -> tuple[list[dict], str]:
    match = REFERENCE_FILENAME.fullmatch(filename.name)
    need(match is not None
         and hashlib.sha256(payload).hexdigest() == match.group(1),
         "IMMUTABLE_REFERENCE_SHA256_MISMATCH")
    plan = chart.get("chartPlan")
    need(chart.get("schemaId") == "ARK_NO11_CHART50_PRIVATE_EXPORT_RECEIPT_V1"
         and chart.get("orderTransmission") is False
         and chart.get("productionReady") is False
         and type(plan) is dict
         and plan.get("sessionDate") == DAY
         and plan.get("asOfSession") == PRIOR
         and plan.get("orderTransmission") is False
         and plan.get("productionReady") is False,
         "PRIVATE_CHART_PLAN_REQUIRED")
    selected = plan.get("selectorInputSymbols")
    need(type(selected) is list and 1 <= len(selected) <= 50
         and all(type(s) is str and SYMBOL.fullmatch(s) for s in selected)
         and len(set(selected)) == len(selected),
         "SELECTED_SYMBOLS_INVALID")
    need(mask.get("asOfSession") == PRIOR
         and mask.get("productionReady") is False
         and mask.get("orderTransmission") is False
         and mask.get("observedPassCount") == len(mask.get("observedPassSymbols", []))
         and all(s in mask["observedPassSymbols"] for s in selected),
         "G1_DAY_OR_MEMBERSHIP_INVALID")
    need(data.get("schemaId") == "ARK_NO11_RSS_SESSION_REFERENCE_CAPTURE_V1"
         and data.get("source") == "RssMarket_SELECTED_REFERENCE_READONLY"
         and data.get("sessionDate") == DAY
         and data.get("readOnly") is True
         and data.get("corporateActionReviewPerformed") is False
         and data.get("productionReady") is False
         and data.get("orderTransmission") is False
         and data.get("chartPlanSha256") == plan.get("planSha256")
         and data.get("selectedSymbols") == selected,
         "REFERENCE_SCOPE_MODE_OR_DATE_INVALID")
    started, finished = timestamp(data.get("capturedAtJst")), timestamp(data.get("completedAtJst"))
    need(started <= finished and (finished - started).total_seconds() < 30,
         "REFERENCE_RECEIPT_CLOCK_INVALID")
    rows = data.get("rows")
    need(type(rows) is list and len(rows) == len(selected),
         "REFERENCE_ROW_COUNT_INVALID")
    need([row.get("symbol") for row in rows if type(row) is dict] == selected,
         "REFERENCE_ROW_MEMBERSHIP_OR_ORDER_INVALID")
    return rows, match.group(1)


def build_queue(reference: dict, reference_bytes: bytes, reference_file: Path,
                chart: dict, mask: dict) -> dict:
    rows, fingerprint = check_reference(reference, reference_bytes, reference_file,
                                        chart, mask)
    work = []
    for row in rows:
        symbol = row["symbol"]
        is_t = (row.get("marketCode") == "T")
        valid_dates = (row.get("marketDate") == DAY
                       and row.get("previousDate") == PRIOR)
        section = SECTIONS.get(row.get("marketSection"))
        lot = type(row.get("lotShares")) in (int, float) and row["lotShares"] == 100
        close = price(row.get("previousClose"))
        base = price(row.get("dayBasePrice"))
        observed_ok = bool(is_t and valid_dates and section and lot and close and base)
        work.append({
            "symbol": symbol,
            "rssReferenceStatus": "FIELDS_PRESENT_NOT_EXTERNAL_REVIEWED"
                if observed_ok else "FIELDS_MISSING_OR_UNEXPECTED",
            "actualRssObservation": {
                "marketCode": row.get("marketCode"),
                "marketDate": row.get("marketDate"),
                "previousDate": row.get("previousDate"),
                "previousClose": row.get("previousClose"),
                "dayBasePrice": row.get("dayBasePrice"),
                "marketSection": row.get("marketSection"),
                "lotShares": row.get("lotShares"),
                "exRightsDateRaw": row.get("exRightsDateRaw"),
                "exDividendDateRaw": row.get("exDividendDateRaw"),
                "interimExDividendDateRaw": row.get("interimExDividendDateRaw")
            },
            # Deliberately NOT the actual safety-evidence schema. Every review
            # field remains null; the packet cannot pass the real master gate.
            "independentlyReviewedSegment": None,
            "independentlyReviewedSector": None,
            "commonEquity": None,
            "corporateActionsCleared": None,
            "priceBasisVerified": None,
            "reviewedPreviousClose": None,
            "sourceDocumentSha256": [],
            "reviewedBy": None,
            "reviewedAtJst": None,
            "reviewStatus": "NOT_REVIEWED",
            "approvedForDatedMaster": False
        })
    return {
        "schemaId": QUEUE_SCHEMA,
        "sessionDate": DAY,
        "previousSession": PRIOR,
        "status": "REQUIRES_INDEPENDENT_EXTERNAL_DOCUMENT_REVIEW",
        "source": "OBSERVED_RSS_SESSION_REFERENCE_UNVERIFIED_CORPORATE_ACTIONS",
        "referenceSourceSha256": fingerprint,
        "chartPlanSha256": chart["chartPlan"]["planSha256"],
        "selectedCount": len(work),
        "rssReferenceFieldsPresent": sum(r["rssReferenceStatus"] == "FIELDS_PRESENT_NOT_EXTERNAL_REVIEWED"
                                         for r in work),
        "rssReferenceFieldsMissing": sum(r["rssReferenceStatus"] != "FIELDS_PRESENT_NOT_EXTERNAL_REVIEWED"
                                         for r in work),
        "independentlyClearedCount": 0,
        "corporateActionReviewPerformed": False,
        "sourcePriceBasisCertified": False,
        "datedMasterCreated": False,
        "fullIntegratedShadowAuthorized": False,
        "productionReady": False,
        "orderTransmission": False,
        "rows": work
    }


def immutable(root: Path, obj: dict) -> Path:
    dest_root = private(root, folder=True)
    raw = (json.dumps(obj, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
           + "\n").encode("utf-8")
    fingerprint = hashlib.sha256(raw).hexdigest()
    target = dest_root / ("rss-review-queue-unreviewed-" + fingerprint + ".json")
    need(not target.is_symlink(), "OUTPUT_SYMLINK")
    if target.exists():
        need(target.read_bytes() == raw, "EXISTING_REVIEW_QUEUE_CHANGED")
    else:
        with target.open("xb") as handle:
            handle.write(raw)
            handle.flush()
    return target


def main(argv=None) -> int:
    args = argparse.ArgumentParser(description=__doc__)
    args.add_argument("--reference", required=True, type=Path)
    args.add_argument("--plan", required=True, type=Path)
    args.add_argument("--mask", required=True, type=Path)
    args.add_argument("--output-root", required=True, type=Path)
    a = args.parse_args(argv)
    try:
        reference, raw = load(a.reference)
        chart, _ = load(a.plan)
        mask, _ = load(a.mask)
        queue = build_queue(reference, raw, a.reference, chart, mask)
        file = immutable(a.output_root, queue)
        print("NO11_RSS_REFERENCE_SELECTED=" + str(queue["selectedCount"]))
        print("NO11_RSS_REFERENCE_FIELDS_PRESENT=" + str(queue["rssReferenceFieldsPresent"]))
        print("NO11_RSS_REFERENCE_FIELDS_MISSING=" + str(queue["rssReferenceFieldsMissing"]))
        print("NO11_RSS_EXTERNAL_CORPORATE_REVIEW=NOT_DONE")
        print("NO11_RSS_DATED_MASTER=NOT_CREATED")
        print("NO11_RSS_REVIEW_QUEUE=" + str(file))
        print("NO11_RSS_INTEGRATED_SHADOW_PREFLIGHT=NOT_PASSED")
        print("ORDER_TRANSMISSION=False")
        return 0
    except (OSError, ValueError, RuntimeError, TypeError, KeyError) as e:
        code = str(e)
        if not re.fullmatch(r"NO11_REAL_RSS_REVIEW_[A-Z0-9_]+", code):
            code = "NO11_REAL_RSS_REVIEW_PRIVATE_OR_SOURCE_UNAVAILABLE"
        print("NO11_RSS_REVIEW_QUEUE=BLOCKED|" + code)
        print("ORDER_TRANSMISSION=False")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
