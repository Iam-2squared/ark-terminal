"""Training-only R41 independent event labels, frozen before implementation.

This module deliberately reads future OHLC. It must never be imported by the
decision runtime or encoder. A complete head-specific scheduled window is
required for both 0 and 1; finding an early event never excuses missing later
observations. The two masks remain independent and no hit order is inferred.
"""
from __future__ import annotations

import math


HEADS = ("CONTINUATION", "FAILURE")
MAXIMUM_BARS = (60, 15)
REASONS = (
    "AVAILABLE", "NO_CONTINUOUS_REFERENCE", "EXACT_ANCHOR_MISSING",
    "EXACT_ANCHOR_INVALID_OPEN", "TARGET_WINDOW_MISSING_BAR",
    "TARGET_WINDOW_INVALID_OHLC",
)


def _require(value: bool, reason: str) -> None:
    if not value:
        raise ValueError(reason)


def _price(value) -> bool:
    return type(value) in (int, float) and math.isfinite(value) and value > 0


def valid_ohlc(row) -> bool:
    if len(row) != 7 or not all(_price(value) for value in row[1:5]):
        return False
    opening, high, low, close = row[1:5]
    return high >= max(opening, close) and low <= min(opening, close) and high >= low


def index_raw_rows(raw_rows) -> dict[int, list]:
    """Build an exact-minute index, never repairing or searching price data."""
    result = {}
    for row in raw_rows:
        _require(isinstance(row, (list, tuple)) and len(row) == 7, "INVALID_RAW_ROW_WIDTH")
        minute = row[0]
        _require(type(minute) in (int, float) and math.isfinite(minute)
                 and int(minute) == minute, "INVALID_RAW_MINUTE")
        minute = int(minute)
        _require(minute not in result, "DUPLICATE_EXACT_MINUTE")
        result[minute] = row
    return result


def event_labels(now: int, scheduled_starts, raw_rows=None, *, indexed_rows=None) -> dict:
    """Return C60/F15 labels and separate availability without feature access.

    `scheduled_starts` comes from R24, not observed row availability. The exact
    next OPEN anchors both heads, including the 11:30 -> 12:30 lunch jump.
    The auction is never a target bar. End-of-session horizons shrink according
    to the calendar, not according to the available data.
    """
    starts = tuple(scheduled_starts)
    _require(bool(starts) and starts == tuple(sorted(set(starts)))
             and all(type(s) is int and s < 925 for s in starts)
             and type(now) is int and now in {s + 1 for s in starts},
             "INVALID_SCHEDULE_OR_DECISION_EPOCH")
    _require((raw_rows is None) != (indexed_rows is None), "EXACTLY_ONE_RAW_INPUT_REQUIRED")
    rows = index_raw_rows(raw_rows) if indexed_rows is None else indexed_rows
    following = tuple(s for s in starts if s >= now)
    reference = following[0] if following else None
    anchor_row = rows.get(reference)
    base = None if anchor_row is None else anchor_row[1]
    targets, reasons, known, ends, horizons = {}, {}, {}, {}, {}
    for head, maximum in zip(HEADS, MAXIMUM_BARS):
        selected = following[:maximum]
        horizons[head] = len(selected)
        ends[head] = selected[-1] + 1 if selected else None
        reason = ("NO_CONTINUOUS_REFERENCE" if reference is None else
                  "EXACT_ANCHOR_MISSING" if anchor_row is None else
                  "EXACT_ANCHOR_INVALID_OPEN" if not _price(base) else None)
        if reason is None:
            for minute in selected:
                row = rows.get(minute)
                if row is None:
                    reason = "TARGET_WINDOW_MISSING_BAR"
                    break
                if not valid_ohlc(row):
                    reason = "TARGET_WINDOW_INVALID_OHLC"
                    break
        if reason is None:
            targets[head] = int(
                any(rows[m][2] >= base * 1.01 for m in selected)
                if head == "CONTINUATION" else
                any(rows[m][3] <= base * 0.9925 for m in selected))
            known[head] = ends[head]
        else:
            targets[head] = None
            known[head] = None
        reasons[head] = reason
    return {
        "labelSideOnly": True, "referenceMinute": reference,
        "targets": targets, "available": {h: targets[h] is not None for h in HEADS},
        "labelKnownAt": known, "windowEnd": ends, "horizonBars": horizons,
        "missingReasons": reasons, "labelImputation": False,
        "independentHeadMasks": True, "intrabarHitOrderInferred": False,
    }
