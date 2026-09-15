"""JSON-file transport for the locked inspection pipeline; never accesses Excel.

Order values do not cross the Windows native argument parser. Only nonempty file
paths are command-line arguments. This is NOT a live order authorization API.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path

REQUEST_SCHEMA = "ARK_CASH_LOCKED_REQUEST_V1"


def _number(value, name, *, allow_zero=False):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError(f"{name}_MUST_BE_FINITE_NUMBER")
    if value < 0 or (value == 0 and not allow_zero):
        raise ValueError(f"{name}_OUT_OF_RANGE")
    return value


def validate_request(request):
    if not isinstance(request, dict) or request.get("schemaId") != REQUEST_SCHEMA:
        raise ValueError("LOCKED_REQUEST_SCHEMA_REQUIRED")
    path = request.get("snapshotPath")
    if not isinstance(path, str) or not path.strip():
        raise ValueError("SNAPSHOT_PATH_REQUIRED")
    intent = request.get("intent")
    if not isinstance(intent, dict):
        raise ValueError("ORDER_INTENT_REQUIRED")
    symbol = intent.get("symbol")
    if not isinstance(symbol, str) or not re.fullmatch(r"[0-9A-Z]{4}\.T", symbol):
        raise ValueError("ORDER_SYMBOL_REQUIRED")
    quantity = intent.get("quantity")
    if type(quantity) is not int or quantity <= 0 or quantity % 100:
        raise ValueError("ORDER_QUANTITY_MUST_BE_POSITIVE_100_SHARE_MULTIPLE")
    if intent.get("direction") != "LONG":
        raise ValueError("LONG_ONLY")
    if (intent.get("positionEffect"), intent.get("side")) not in {
        ("OPEN", "BUY"), ("CLOSE", "SELL")
    }:
        raise ValueError("CASH_POSITION_EFFECT_SIDE_MISMATCH")
    if intent.get("timeInForce") != "DAY":
        raise ValueError("DAY_ONLY")
    if intent.get("orderType") == "MARKET":
        if intent.get("limitPrice") is not None:
            raise ValueError("MARKET_LIMIT_PRICE_MUST_BE_NULL")
    elif intent.get("orderType") == "LIMIT":
        _number(intent.get("limitPrice"), "LIMIT_PRICE")
    else:
        raise ValueError("ORDER_TYPE_REQUIRED")
    _number(request.get("estimatedNotional"), "ESTIMATED_NOTIONAL")
    positions = request.get("externalPositions")
    if not isinstance(positions, list):
        raise ValueError("EXTERNAL_POSITIONS_ARRAY_REQUIRED")
    for row in positions:
        if not isinstance(row, dict) or not isinstance(row.get("symbol"), str):
            raise ValueError("EXTERNAL_POSITION_IDENTITY_REQUIRED")
        if not re.fullmatch(r"[0-9A-Z]{4}(?:\.T)?", row["symbol"]):
            raise ValueError("EXTERNAL_POSITION_IDENTITY_REQUIRED")
        _number(row.get("quantity"), "EXTERNAL_POSITION_QUANTITY")
    return request


def _evaluate(snapshot, request):
    # Imported only after input validation; this module itself has no COM access.
    from phase57_cash_locked_pipeline import run_locked_pipeline
    return run_locked_pipeline(
        snapshot,
        external_positions=request["externalPositions"],
        intent=request["intent"],
        estimated_notional=request["estimatedNotional"],
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        request = validate_request(json.loads(args.request.read_text(encoding="utf-8-sig")))
        snapshot_path = Path(request["snapshotPath"])
        if args.output.resolve() in {args.request.resolve(), snapshot_path.resolve()}:
            raise ValueError("OUTPUT_MUST_NOT_OVERWRITE_INPUT")
        if args.output.exists():
            raise ValueError("OUTPUT_ALREADY_EXISTS")
        snapshot = json.loads(snapshot_path.read_text(encoding="utf-8-sig"))
        if not isinstance(snapshot, dict):
            raise ValueError("SNAPSHOT_OBJECT_REQUIRED")
        result = _evaluate(snapshot, request)
        if not isinstance(result, dict) or result.get("status") not in {"BLOCKED", "LOCKED_READY"}:
            raise ValueError("PIPELINE_RESULT_INVALID")
        if not isinstance(result.get("stage"), str) or not result["stage"]:
            raise ValueError("PIPELINE_STAGE_REQUIRED")
        result["inspectionOnly"] = True
        # A unique output path is allocated by the bridge. No stdout JSON, no
        # caller-supplied freshness rewrite, no Excel or order function call.
        with args.output.open("x", encoding="utf-8") as stream:
            json.dump(result, stream, ensure_ascii=True, allow_nan=False)
        return 0
    except (OSError, ValueError, TypeError, KeyError, OverflowError) as exc:
        print(f"LOCKED_PIPELINE_ERROR:{type(exc).__name__}:{exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
