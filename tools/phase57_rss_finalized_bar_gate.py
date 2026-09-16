"""Fail-closed bridge from RSS 5m observations to realtime-shadow eligible bars.

This module does not run strategy logic and cannot transmit orders. A bar is
released only when a strictly later 5m bar from the same session is observed.
"""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from typing import Iterable

from phase57_rss_finalization import BarState, FinalizationError, NextBarFinalizationObserver

SAFETY = {
    "executionAllowed": False,
    "brokerWriteAllowed": False,
    "excelOrderWriteAllowed": False,
    "rssOrderFunctionAllowed": False,
    "liveTradingAllowed": False,
    "paperTradingAllowed": False,
    "automaticPromotionAllowed": False,
    "productionUpdateAllowed": False,
    "transmitted": False,
}


def _minutes(clock: str) -> int:
    try:
        hour, minute = map(int, clock.split(":")[:2])
    except Exception as error:
        raise FinalizationError("INVALID_BAR_TIME") from error
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise FinalizationError("INVALID_BAR_TIME")
    return hour * 60 + minute


class FinalizedBarShadowGate:
    """Release each completed bar at most once, only on observed next-bar evidence."""

    def __init__(self) -> None:
        self._observer = NextBarFinalizationObserver()
        self._released: set[tuple[str, str]] = set()

    def observe(self, bars: Iterable[BarState], observed_at: datetime) -> dict:
        ordered = list(bars)
        for left, right in zip(ordered, ordered[1:]):
            if left.date == right.date and _minutes(right.time) - _minutes(left.time) != 5:
                raise FinalizationError(f"NON_5M_NEXT_BAR:{left.time}->{right.time}")
        result = self._observer.observe(ordered, observed_at)
        released = []
        by_key = {bar.key: bar for bar in ordered}
        for item in result["finalized"]:
            key = (item["date"], item["time"])
            if key in self._released:
                continue
            bar = by_key.get(key)
            if bar is None:
                raise FinalizationError("FINALIZED_BAR_NOT_IN_SOURCE_WINDOW")
            released.append({
                "type": "RSS_5M_FINALIZED_BAR_READY_FOR_SHADOW",
                "bar": asdict(bar),
                "finalizedByNextBar": item["finalizedByNextBar"],
                "observedAt": item["observedAt"],
                "safety": dict(SAFETY),
            })
            self._released.add(key)
        return {
            "released": released,
            "latest": result["latest"],
            "safety": dict(SAFETY),
        }
