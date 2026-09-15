from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable


@dataclass(frozen=True)
class BarState:
    date: str
    time: str
    open: float
    high: float
    low: float
    close: float
    volume: float

    @property
    def key(self) -> tuple[str, str]:
        return self.date, self.time

    @property
    def ohlcv(self) -> tuple[float, float, float, float, float]:
        return self.open, self.high, self.low, self.close, self.volume


class FinalizationError(RuntimeError):
    pass


class NextBarFinalizationObserver:
    """Finalize a 5m bar only after the next 5m bar is actually observed.

    A clock boundary alone is never evidence of finalization. Any mutation of a
    bar after it has been finalized fails closed.
    """

    def __init__(self) -> None:
        self._last_seen: BarState | None = None
        self._finalized: dict[tuple[str, str], tuple[float, float, float, float, float]] = {}

    def observe(self, bars: Iterable[BarState], observed_at: datetime) -> dict:
        ordered = list(bars)
        if not ordered:
            return {"observedAt": observed_at.isoformat(), "finalized": [], "latest": None}

        for bar in ordered:
            prior = self._finalized.get(bar.key)
            if prior is not None and prior != bar.ohlcv:
                raise FinalizationError(f"FINALIZED_BAR_REVISED:{bar.date}T{bar.time}")

        newly_finalized: list[dict] = []
        if len(ordered) >= 2:
            previous = ordered[-2]
            latest = ordered[-1]
            if previous.key >= latest.key:
                raise FinalizationError("NONMONOTONIC_NEXT_BAR")

            prior = self._finalized.get(previous.key)
            if prior is None:
                self._finalized[previous.key] = previous.ohlcv
                newly_finalized.append({
                    "date": previous.date,
                    "time": previous.time,
                    "ohlcv": previous.ohlcv,
                    "finalizedByNextBar": latest.time,
                    "observedAt": observed_at.isoformat(),
                })
            elif prior != previous.ohlcv:
                raise FinalizationError(f"FINALIZED_BAR_REVISED:{previous.date}T{previous.time}")

        self._last_seen = ordered[-1]
        return {
            "observedAt": observed_at.isoformat(),
            "finalized": newly_finalized,
            "latest": {
                "date": self._last_seen.date,
                "time": self._last_seen.time,
                "ohlcv": self._last_seen.ohlcv,
            },
        }
