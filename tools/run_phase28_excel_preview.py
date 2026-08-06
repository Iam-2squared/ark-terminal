from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from typing import Any, Callable

from tools.rss_order_preparation import (
    ORDER_SHEET_NAME,
    build_order_preparation,
    write_preparation_to_worksheet,
)


def build_validation_payload(symbol: str, quantity: int, limit_price: float) -> dict[str, Any]:
    return {
        "approval": {
            "status": "DRY_RUN_READY",
            "candidateHash": "phase28.5-local-validation",
        },
        "risk": {"status": "DRY_RUN_ALLOWED"},
        "killSwitch": {"status": "ARMED"},
        "candidate": {
            "symbol": symbol,
            "side": "BUY",
            "quantity": quantity,
            "orderType": "LIMIT",
            "limitPrice": limit_price,
            "accountType": "CASH",
            "executionCondition": "DAY",
        },
    }


def _bridge_accessors() -> tuple[Callable[[], tuple[Any, Any]], Callable[[], None]]:
    # Delayed import prevents rss_bridge <-> preview runner circular imports.
    from tools.rss_bridge import read_workbook_snapshot, release_com

    return read_workbook_snapshot, release_com


def run_excel_preview(
    symbol: str,
    quantity: int,
    limit_price: float,
    *,
    workbook_reader: Callable[[], tuple[Any, Any]] | None = None,
    com_releaser: Callable[[], None] | None = None,
) -> dict[str, Any]:
    payload = build_validation_payload(symbol, quantity, limit_price)
    preparation = build_order_preparation(payload)
    if preparation.status != "PREPARED_FOR_LOCAL_REVIEW":
        return {
            "status": preparation.status,
            "blockers": list(preparation.blockers),
            "worksheet": preparation.worksheet,
            "auditHash": preparation.audit_hash,
            "safety": dict(preparation.safety),
        }

    if workbook_reader is None or com_releaser is None:
        default_reader, default_releaser = _bridge_accessors()
        workbook_reader = workbook_reader or default_reader
        com_releaser = com_releaser or default_releaser

    _, workbook = workbook_reader()
    try:
        try:
            worksheet = workbook.Worksheets(ORDER_SHEET_NAME)
        except Exception as exc:
            raise RuntimeError(
                f"Excelに{ORDER_SHEET_NAME}シートが見つかりません。"
            ) from exc

        write_result = write_preparation_to_worksheet(worksheet, preparation)
        return {
            **write_result,
            "auditHash": preparation.audit_hash,
            "prepared": asdict(preparation),
            "safety": {
                **dict(preparation.safety),
                "orderTrigger": False,
                "brokerWrites": 0,
                "liveOrders": 0,
            },
        }
    finally:
        com_releaser()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Phase28.5 Excel preview runner. Never transmits an order."
    )
    parser.add_argument("--symbol", default="7203.T")
    parser.add_argument("--quantity", type=int, default=100)
    parser.add_argument("--limit-price", type=float, default=1.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = run_excel_preview(args.symbol, args.quantity, args.limit_price)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "PREVIEW_WRITTEN" else 1


if __name__ == "__main__":
    raise SystemExit(main())
