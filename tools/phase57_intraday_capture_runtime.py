from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from tools.phase57_intraday_capture import PHASE57_CAPTURE_SAFETY
from tools.phase57_intraday_capture_health import assess_capture_health
from tools.phase57_intraday_capture_ops import run_read_only_capture_cycle

PHASE57_P15_SAFETY = {
    **PHASE57_CAPTURE_SAFETY,
    "mode": "PHASE57_INTRADAY_CAPTURE_RUNTIME_READ_ONLY",
}


def run_read_only_runtime_tick(
    workbook: Any,
    *,
    root: str | Path = "data/intraday",
    sheet_name: str = "ArkIntraday",
    now: datetime | None = None,
    capture_thresholds: dict[str, float | int] | None = None,
    expected_interval_seconds: int = 5,
    stale_after_seconds: int = 30,
    max_gap_multiplier: float = 3.0,
) -> dict[str, Any]:
    """Run one READ-ONLY capture + health tick.

    This function is intentionally finite. An external scheduler may invoke it repeatedly.
    It never writes to Excel, never calls an RSS order function, and never transmits orders.
    """
    as_of = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    capture = run_read_only_capture_cycle(
        workbook,
        sheet_name=sheet_name,
        root=root,
        thresholds=capture_thresholds,
    )
    health = assess_capture_health(
        root,
        as_of=as_of,
        expected_interval_seconds=expected_interval_seconds,
        stale_after_seconds=stale_after_seconds,
        max_gap_multiplier=max_gap_multiplier,
    )
    healthy = health.get("status") == "INTRADAY_CAPTURE_HEALTHY"
    sufficient = capture.get("sufficiency", {}).get("status") == "INTRADAY_CAPTURE_SUFFICIENT_FOR_PREDECLARED_OOS"
    return {
        "phase": "57.p15",
        "status": "READ_ONLY_RUNTIME_TICK_HEALTHY" if healthy else "READ_ONLY_RUNTIME_TICK_BLOCKED",
        "capturedAt": as_of.isoformat(),
        "capture": capture,
        "health": health,
        "nextStep": "RUN_PREDECLARED_REAL_REPLAY_OOS" if healthy and sufficient else "CONTINUE_READ_ONLY_INTRADAY_CAPTURE",
        "edgeClaimAllowed": False,
        "executionAllowed": False,
        "brokerWriteAllowed": False,
        "excelOrderWriteAllowed": False,
        "rssOrderFunctionAllowed": False,
        "liveTradingAllowed": False,
        "paperTradingAllowed": False,
        "automaticPromotionAllowed": False,
        "productionUpdateAllowed": False,
        "safety": PHASE57_P15_SAFETY,
    }


def run_bounded_read_only_runtime(
    workbook: Any,
    *,
    iterations: int = 1,
    tick: Callable[..., dict[str, Any]] = run_read_only_runtime_tick,
    **kwargs: Any,
) -> dict[str, Any]:
    """Run a bounded number of local research ticks; never an infinite loop."""
    count = max(0, int(iterations))
    results = [tick(workbook, **kwargs) for _ in range(count)]
    blockers = [r for r in results if r.get("status") != "READ_ONLY_RUNTIME_TICK_HEALTHY"]
    return {
        "phase": "57.p15",
        "status": "BOUNDED_READ_ONLY_RUNTIME_COMPLETE",
        "iterationsRequested": count,
        "iterationsCompleted": len(results),
        "healthyTicks": len(results) - len(blockers),
        "blockedTicks": len(blockers),
        "results": results,
        "continuousLoopAllowed": False,
        "executionAllowed": False,
        "brokerWriteAllowed": False,
        "excelOrderWriteAllowed": False,
        "rssOrderFunctionAllowed": False,
        "liveTradingAllowed": False,
        "paperTradingAllowed": False,
        "automaticPromotionAllowed": False,
        "productionUpdateAllowed": False,
        "safety": PHASE57_P15_SAFETY,
    }
