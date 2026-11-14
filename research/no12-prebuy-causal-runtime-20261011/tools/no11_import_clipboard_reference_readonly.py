#!/usr/bin/env python3
"""Import an A1:L47 human-copied RssMarket table into a *UNREVIEWED* RSS reference.

NO Excel COM, new RSS request, broker, model, orders, fitting, or live trading.
It checks the original byte-pinned G1/Chart50 selected scope and immutable
clipboard receipt. Clipboard-read time is the local PC possession time, NOT the
RSS-vendor field update clock or a retrospective decision time. It MUST NOT
authorize a prior frozen Selector/BUY, corporate action or price-basis approval.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime
from decimal import Decimal, InvalidOperation
import hashlib
from io import StringIO
import json
from pathlib import Path
import re
import sys

sys.dont_write_bytecode = True
DAY = "2026-10-27"
PRIOR = "2026-10-26"
CLIP_SCHEMA = "ARK_NO11_LOCAL_RSS_CLIPBOARD_CAPTURE_V1"
SOURCE_SCHEMA = "ARK_NO11_RSS_SESSION_REFERENCE_CAPTURE_V1"
COLS = 12
STAMP = re.compile(r"2026-10-27T\d\d:\d\d:\d\d(?:\.\d{3})?\+09:00")
SYM = re.compile(r"[0-9A-Z]{4}\.T")
RECEIPT = re.compile(r"clipboard-source-([a-f0-9]{64})\.json")
DIGEST = re.compile(r"[a-f0-9]{64}")


def need(ok, code):
    if not ok:
        raise ValueError("NO11_CLIPBOARD_" + code)


def private(p, *, directory=False):
    p = Path(p)
    need(p.is_absolute(), "PRIVATE_PATH_ABSOLUTE_REQUIRED")
    p = p.absolute()
    need(not p.is_symlink() and all(not q.is_symlink() for q in p.parents)
         and (p.is_dir() if directory else p.is_file()),
         "PRIVATE_PATH_OR_TYPE_INVALID")
    return p


def json_file(p, limit=4_000_000):
    p = private(p)
    need(0 < p.stat().st_size <= limit, "SOURCE_BYTES_LIMIT")
    b = p.read_bytes()
    return json.loads(b.decode("utf-8-sig")), b


def clock(s):
    need(type(s) is str and STAMP.fullmatch(s), "OBSERVED_CLOCK_INVALID")
    try:
        t = datetime.fromisoformat(s)
    except ValueError:
        raise ValueError("NO11_CLIPBOARD_OBSERVED_CLOCK_INVALID") from None
    need(t.isoformat().startswith(DAY) and t.utcoffset().total_seconds() == 9 * 3600,
         "OBSERVED_CLOCK_INVALID")
    return t


def date_cell(s):
    s = s.strip()
    if not s:
        return None
    # Exactly the printed Excel values, not a guessed previous date.
    for fmt in ("%Y/%m/%d", "%Y/%-m/%-d", "%Y-%m-%d"):
        if "%-" in fmt:
            continue  # platform-specific %-m; use fromisoformat-normalized below
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    m = re.fullmatch(r"(20\d\d)[/-](\d\d?)[/-](\d\d?)", s)
    if m:
        try:
            return datetime(int(m[1]), int(m[2]), int(m[3])).strftime("%Y-%m-%d")
        except ValueError:
            return None
    if re.fullmatch(r"\d{5}(?:\.0+)?", s):
        try:
            from datetime import timedelta
            return (datetime(1899, 12, 30) + timedelta(days=float(s))).strftime("%Y-%m-%d")
        except ValueError:
            return None
    return None


def number(s):
    s = s.strip().replace(",", "")
    if not s or not re.fullmatch(r"(?:0|[1-9]\d*)(?:\.\d+)?", s):
        return None
    try:
        v = Decimal(s)
    except InvalidOperation:
        return None
    if not v.is_finite() or v < 0 or v > Decimal("1000000000"):
        return None
    return float(v) if "." in s else int(v)


def csv_rows(text):
    need(type(text) is str and 10 < len(text) < 200_000 and
         "\t" in text and "\x00" not in text,
         "CLIPBOARD_NOT_EXCEL_TABULAR_TEXT")
    rows = list(csv.reader(StringIO(text, newline=""), delimiter="\t",
                           quotechar='"', strict=True))
    while rows and rows[-1] == []:
        rows.pop()
    need(len(rows) == 47 and all(len(row) == COLS for row in rows),
         "EXACT_47_ROWS_12_FIELDS_REQUIRED")
    need(all(all(len(cell) <= 300 and "\x00" not in cell for cell in row)
             for row in rows), "CLIPBOARD_CELL_LIMIT")
    return rows


def convert_rows(rows, selected):
    need(len(selected) == 47 and len(set(selected)) == 47
         and all(SYM.fullmatch(s) for s in selected), "ORIGINAL_SCOPE_NOT_47")
    records = []
    for idx, row in enumerate(rows):
        symbol = selected[idx]
        need(row[0].strip() == symbol, "CLIPBOARD_SYMBOL_ORDER_MISMATCH")
        need(row[1].strip() == symbol[:4], "RSS_VENDOR_SYMBOL_MISMATCH")
        market_code = row[2].strip()
        need(market_code in ("T", ""), "MARKET_CODE_INVALID")
        records.append({
            "symbol": symbol, "marketCode": market_code,
            "marketDate": date_cell(row[3]),
            "previousDate": date_cell(row[4]),
            "previousClose": number(row[5]),
            "dayBasePrice": number(row[6]),
            "marketSection": row[7].strip(),
            "lotShares": number(row[8]),
            "exRightsDateRaw": row[9].strip(),
            "exDividendDateRaw": row[10].strip(),
            "interimExDividendDateRaw": row[11].strip()
        })
    return records


def build(clip, filename, plan_file, mask_file, engine_root):
    match = RECEIPT.fullmatch(filename.name)
    need(match is not None, "CLIPBOARD_FILENAME_INVALID")
    source, binary = json_file(filename, 250_000)
    need(hashlib.sha256(binary).hexdigest() == match.group(1),
         "CLIPBOARD_IMMUTABLE_BYTES_CHANGED")
    need(source.get("schemaId") == CLIP_SCHEMA and
         source.get("sessionDate") == DAY and
         source.get("copiedFromExcelByUser") is True and
         source.get("readOnly") is True and
         source.get("productionReady") is False and
         source.get("orderTransmission") is False and
         source.get("actualRssSourceTimeCertified") is False and
         source.get("independentCorporateActionReviewPerformed") is False,
         "CLIPBOARD_DECLARATION_INVALID")
    start, end = clock(source.get("capturedAtJst")), clock(source.get("completedAtJst"))
    need(0 <= (end - start).total_seconds() <= 30,
         "CLIPBOARD_LOCAL_READ_CLOCK_INVALID")

    engine = private(engine_root, directory=True)
    root = engine.parents[1]
    need(engine.name == "no12-prebuy-causal-runtime-20261011" and
         engine.parent.name == "research", "ENGINE_IDENTITY_INVALID")
    need(root not in private(plan_file).parents and
         root not in private(mask_file).parents and
         root not in filename.parents, "SOURCE_MUST_BE_PRIVATE")
    sys.path.insert(0, str(engine / "tools"))
    import no11_previous_archive_context as original
    scope = original.scope(plan_file, mask_file)
    need(scope["sessionDate"] == DAY and scope["previousSession"] == PRIOR,
         "ORIGINAL_SCOPE_DATE_INVALID")
    selected = scope["selectedSymbols"]
    rows = convert_rows(csv_rows(source.get("clipboardTabularText")), selected)
    need(len(rows) == len(selected) == 47, "SOURCE_SCOPE_INVALID")
    record = {
        "schemaId": SOURCE_SCHEMA,
        "sessionDate": DAY,
        "source": "RssMarket_SELECTED_REFERENCE_READONLY",
        "capturedAtJst": source["capturedAtJst"],
        "completedAtJst": source["completedAtJst"],
        "chartPlanSha256": scope["chartPlanSha256"],
        "selectedSymbols": selected,
        "rows": rows,
        "corporateActionReviewPerformed": False,
        "readOnly": True, "productionReady": False,
        "orderTransmission": False,
        "acquisitionTransport": "MANUAL_EXCEL_CLIPBOARD_READ_NOT_COM",
        "actualRssSourceTimeCertified": False,
        "originWorkbookAtCopyIndependentlyVerified": False,
        "originalFormulaVerifiedByThisImporter": False,
        "priorFrozenDecisionsMayBeBackfilled": False,
        "knownAtJstNotBefore": source["completedAtJst"],
    }
    return record


def immutable(root, label, value):
    root = private(root, directory=True)
    b = (json.dumps(value, ensure_ascii=False, separators=(",", ":"),
                    allow_nan=False) + "\n").encode("utf-8")
    digest = hashlib.sha256(b).hexdigest()
    p = root / (label + "-" + digest + ".json")
    need(not p.is_symlink(), "OUTPUT_SYMLINK")
    if p.exists():
        need(p.read_bytes() == b, "EXISTING_IMMUTABLE_SOURCE_CHANGED")
    else:
        with p.open("xb") as stream:
            stream.write(b)
            stream.flush()
    return p


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--clipboard-file", required=True, type=Path)
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--mask", required=True, type=Path)
    parser.add_argument("--engine-root", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        record = build(None, args.clipboard_file, args.plan,
                       args.mask, args.engine_root)
        from no11_review_queue_from_actual_rss import build_queue, immutable as review_immutable
        chart, _ = json_file(args.plan)
        mask, _ = json_file(args.mask)
        # Preserve immutable evidence but never assert EXTERNALLY_REVIEWED.
        p = immutable(args.output_root, "session-reference", record)
        reference, binary = json_file(p)
        queue = build_queue(reference, binary, p, chart, mask)
        q = review_immutable(args.output_root, queue)
        need(queue["independentlyClearedCount"] == 0 and
             queue["datedMasterCreated"] is False and
             queue["fullIntegratedShadowAuthorized"] is False,
             "EXTERNAL_REVIEW_UNEXPECTEDLY_PASSED")
        print("NO11_CLIPBOARD_REFERENCE_ROWS=47")
        print("NO11_CLIPBOARD_RSS_FIELDS_PRESENT=" +
              str(queue["rssReferenceFieldsPresent"]))
        print("NO11_CLIPBOARD_RSS_FIELDS_MISSING=" +
              str(queue["rssReferenceFieldsMissing"]))
        print("NO11_CLIPBOARD_ORIGINAL_DECISIONS_BACKFILLED=False")
        print("NO11_CLIPBOARD_REFERENCE_FILE=" + str(p))
        print("NO11_CLIPBOARD_UNREVIEWED_QUEUE=" + str(q))
        print("NO11_CLIPBOARD_DATED_MASTER=NOT_CREATED")
        print("NO11_CLIPBOARD_INTEGRATED_SHADOW=NOT_AUTHORIZED")
        print("ORDER_TRANSMISSION=False")
        return 0
    except (OSError, ValueError, TypeError, KeyError, csv.Error) as exc:
        reason = str(exc)
        if not re.fullmatch(r"NO11_(?:CLIPBOARD|REAL_RSS_REVIEW|PREVIOUS_ARCHIVE)_[A-Z0-9_]+", reason):
            reason = "NO11_CLIPBOARD_PRIVATE_OR_PARSE_INPUT_INVALID"
        print("NO11_CLIPBOARD_REFERENCE=BLOCKED|" + reason)
        print("ORDER_TRANSMISSION=False")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
