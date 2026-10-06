"""Inspect frozen P0 null guards; do not regenerate features or infer acquisition.

The gate definitions follow the immutable FIRST ENTRY v2 price_primitives.py,
price_features.py and common.py.  Inputs are supplied arrays, not provider
responses. A missing scheduled row therefore says nothing by itself about
whether the provider had no trade, the download failed, or the join omitted it.

Six-column rows [start, O, H, L, C, Volume] and the original seven-column rows
with Value are accepted. Value is never estimated from OHLCV. This module has
no network, filesystem, model, outcome, or capital dependency.
"""

from __future__ import annotations

from datetime import date
import math
import re
from typing import Any, Iterable, Sequence


VERSION = "FROZEN_P0_NULL_GUARD_AUDIT_V1"
HISTORY = "HISTORY_WINDOW_INSUFFICIENT"
BOUNDARY = "HALF_SESSION_BOUNDARY"
GAP = "SCHEDULED_BAR_GAP"
PREVIOUS = "PREVIOUS_INPUT_INSUFFICIENT"
DENOMINATOR = "INVALID_DENOMINATOR"
INAPPLICABLE = "NOT_APPLICABLE"
UNKNOWN = "UNKNOWN"
CLEAR = "NO_KNOWN_NULL_CONDITION"

_DESCRIBE = {
    "count", "coverage", "return", "high", "low", "range", "volatility",
    "body", "upper", "lower", "volume", "value", "vwapDistance",
    "closeLocation", "timeHigh", "timeLow", "trendEfficiency",
}
_WATCH_CONTEXT = {
    "activeMinutesSinceSelector", "priceVsFirstSelectorPct", "knownRefreshCount",
    "activeMinutesSinceLatestSelector", "clockMinute", "isPM",
}


def _finding(reason: str, detail: str, *, proves_null: bool | None = True,
             **evidence: Any) -> dict[str, Any]:
    return {"reason": reason, "detail": detail, "proves_null": proves_null,
            "evidence": evidence}


def _number(value: Any) -> float:
    if isinstance(value, bool):
        raise ValueError("boolean is not a market number")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("non-finite market number")
    return number


def _regular(start: int, day: str) -> bool:
    end = 900 if day < "2024-11-05" else 925
    return 540 <= start < 690 or 750 <= start < end


def _phase_start(cutoff: int) -> int:
    # Exact frozen rule, including cutoff=11:30 belonging to the AM session.
    return 540 if cutoff <= 690 else 750


def _prepare(rows: Iterable[Sequence[Any]] | None, day: str | None,
             cutoff: int | None) -> tuple[list[tuple[float, ...]], dict[str, Any]]:
    accepted: list[tuple[float, ...]] = []
    info: dict[str, Any] = {
        "accepted_rows": 0, "rejected_minutes": [], "excluded_unclosed_rows": 0,
        "excluded_nonregular_rows": 0, "shape_errors": 0,
        "ordering_or_duplicate_error": False, "value_column_absent_rows": 0,
        "input_absent": rows is None,
    }
    last_minute: int | None = None
    for source in (() if rows is None else rows):
        try:
            length = len(source)
            start = _number(source[0])
            if length not in (6, 7) or not start.is_integer():
                raise ValueError("unsupported row shape/start")
            minute = int(start)
        except (ValueError, TypeError, IndexError, OverflowError):
            info["shape_errors"] += 1
            continue
        # Never inspect H/L/C/Volume/Value of a bar not closed at the boundary.
        if cutoff is not None and minute >= cutoff:
            info["excluded_unclosed_rows"] += 1
            continue
        if last_minute is not None and minute <= last_minute:
            info["ordering_or_duplicate_error"] = True
        last_minute = minute
        if day is not None and not _regular(minute, day):
            info["excluded_nonregular_rows"] += 1
            continue
        try:
            values = tuple(_number(v) for v in source)
            _, opening, high, low, close, volume, *value = values
            valid = (low > 0 and low <= min(opening, close)
                     <= max(opening, close) <= high and volume >= 0
                     and (not value or value[0] >= 0))
            if not valid:
                raise ValueError("invalid OHLCV/value")
        except (ValueError, TypeError, OverflowError):
            info["rejected_minutes"].append(minute)
            continue
        accepted.append(values)
        info["value_column_absent_rows"] += int(length == 6)
    info["accepted_rows"] = len(accepted)
    return accepted, info


def _window(rows: list[tuple[float, ...]], cutoff: int, n: int, role: str
            ) -> tuple[list[tuple[float, ...]] | None, list[dict[str, Any]]]:
    begin = cutoff - n
    phase = _phase_start(cutoff)
    evidence = {"role": role, "window_start": begin, "window_end_exclusive": cutoff,
                "required_rows": n, "half_session_start": phase}
    if begin < phase:
        return None, [_finding(BOUNDARY, "Frozen strict window crosses its half-session start.",
                               **evidence)]
    selected = [r for r in rows if begin <= r[0] < cutoff]
    starts = [int(r[0]) for r in selected]
    required = list(range(begin, cutoff))
    if starts == required:
        return selected, []
    absent = sorted(set(required) - set(starts))
    detail = "Supplied input does not cover the full required time window."
    earliest = int(rows[0][0]) if rows else None
    underlying = HISTORY if earliest is None or earliest > begin else GAP
    if underlying == GAP:
        detail = "Scheduled minute(s) are absent from the supplied accepted prefix."
    reason = PREVIOUS if role == "previous_day" else underlying
    return None, [_finding(reason, detail, **evidence,
                           observed_window_rows=len(selected), missing_minutes=absent,
                           earliest_supplied_minute=earliest,
                           underlying_window_reason=underlying,
                           underlying_source_cause=UNKNOWN,
                           acquisition_manifest_checked=False)]


def _column_guard(rows: list[tuple[float, ...]] | None, col: int, role: str,
                  *, denominator: bool = False) -> list[dict[str, Any]]:
    if rows is None:
        return []
    if col == 6 and any(len(r) < 7 for r in rows):
        return [_finding(UNKNOWN, "Value is not supplied; OHLCV is not a Value substitute.",
                         proves_null=None, role=role, required_column="Value")]
    if denominator:
        total = math.fsum(r[col] for r in rows)
        if total <= 0:
            return [_finding(DENOMINATOR, "Frozen ratio/pct denominator is not positive.",
                             role=role, column="Volume" if col == 5 else "Value",
                             denominator_positive=False)]
    return []


def _vwap_guards(rows: list[tuple[float, ...]], day: str, cutoff: int, role: str,
                 *, positive_value_required: bool = True
                 ) -> list[dict[str, Any]]:
    prefix = [r for r in rows if r[0] < cutoff]
    end = 900 if day < "2024-11-05" else 925
    expected = sum(m < cutoff for m in (*range(540, 690), *range(750, end)))
    # Exact frozen len/expected definition, not a new continuous-window VWAP.
    coverage = len(prefix) / expected if expected else 0.0
    if coverage < 0.8:
        return [_finding(HISTORY, "Frozen observed VWAP coverage is below 80%.",
                         role=role, observed_rows=len(prefix), scheduled_rows=expected,
                         coverage=coverage, minimum_coverage=0.8,
                         underlying_source_cause=UNKNOWN,
                         acquisition_manifest_checked=False)]
    findings = _column_guard(prefix, 5, role, denominator=True)
    findings += _column_guard(prefix, 6, role, denominator=positive_value_required)
    return findings


def _audit_feature(name: str, day: str, cutoff: int,
                   today: list[tuple[float, ...]], previous: list[tuple[float, ...]]
                   ) -> list[dict[str, Any]]:
    match = re.fullmatch(r"w(5|10|20)/([A-Za-z]+)", name)
    if match and match[2] in _DESCRIBE:
        n, field = int(match[1]), match[2]
        if field in {"count", "coverage"}:
            return [_finding(INAPPLICABLE, "Frozen count/coverage reports counts even when its strict window fails.",
                             proves_null=False)]
        window, findings = _window(today, cutoff, n, "current")
        if field in {"value", "vwapDistance"}:
            findings += _column_guard(window, 6, "current")
        if field == "vwapDistance":
            findings += _column_guard(window, 5, "current", denominator=True)
            # pct(close, Value/Volume) is null also for zero Value.
            findings += _column_guard(window, 6, "current", denominator=True)
        return findings
    match = re.fullmatch(r"return(1|3|5|10|20)", name)
    if match:
        return _window(today, cutoff, int(match[1]) + 1, "current")[1]
    match = re.fullmatch(r"pullback(5|10|20)Pct", name)
    if match:
        return _window(today, cutoff, int(match[1]), "current")[1]
    if name in {"vwapDistancePct", "vwapSlope3Pct"}:
        findings = _vwap_guards(today, day, cutoff, "current_vwap",
                                positive_value_required=name == "vwapDistancePct")
        if name == "vwapSlope3Pct":
            findings += _vwap_guards(today, day, cutoff - 3, "lag3_vwap")
        return findings
    if name == "vwapObservedCoverage":
        return [_finding(INAPPLICABLE, "Coverage itself does not become null below its threshold.",
                         proves_null=False)]
    match = re.fullmatch(r"activity/(1|3|5|10)/(currentRows|precedingRows|previousDayRows|volume|value|volumeAcceleration|valueAcceleration|volumeRelativePreviousDay|valueRelativePreviousDay)", name)
    if match:
        n, field = int(match[1]), match[2]
        if field.endswith("Rows"):
            return [_finding(INAPPLICABLE, "Frozen activity counts retain observed counts for incomplete windows.",
                             proves_null=False)]
        col = 5 if field.startswith("volume") else 6
        current, findings = _window(today, cutoff, n, "current")
        findings += _column_guard(current, col, "current")
        if field.endswith("Acceleration"):
            preceding, guards = _window(today, cutoff - n, n, "preceding")
            findings += guards + _column_guard(preceding, col, "preceding", denominator=True)
        elif field.endswith("RelativePreviousDay"):
            historical, guards = _window(previous, cutoff, n, "previous_day")
            findings += guards + _column_guard(historical, col, "previous_day", denominator=True)
        return findings
    match = re.fullmatch(r"activity/(compression|expansion|wick)/(volume|value)(Contraction|Expansion|Confirmation)", name)
    if match:
        kind, measure, suffix = match.groups()
        if suffix != {"compression": "Contraction", "expansion": "Expansion", "wick": "Confirmation"}[kind]:
            return [_finding(UNKNOWN, "Feature name is outside the frozen P0 registry.", proves_null=None)]
        col = 5 if measure == "volume" else 6
        n = 2 if kind == "wick" else 11
        window, findings = _window(today, cutoff, n, "current")
        findings += _column_guard(window, col, "current")
        if window is not None:
            denominator = window[:1] if kind == "wick" else window[:5] if kind == "compression" else window[5:10]
            findings += _column_guard(denominator, col, kind + "_denominator", denominator=True)
        return findings
    if name in _WATCH_CONTEXT:
        return [_finding(UNKNOWN, "Watch/Selector context is not provided by OHLCV arrays.",
                         proves_null=None, required_input="frozen watch metadata")]
    return [_finding(UNKNOWN, "Feature name is outside the frozen P0 registry.", proves_null=None)]


def explain_missingness(day: str, cutoff_minute: int,
                        today_rows: Iterable[Sequence[Any]] | None,
                        previous_rows: Iterable[Sequence[Any]] | None,
                        feature_name: str, *, previous_day: str | None = None,
                        observed_is_missing: bool | None = None) -> dict[str, Any]:
    """Return guard evidence, separately from any link to a stored null cell.

    ``expected_null`` reports a proven frozen null guard under supplied inputs.
    ``False`` means no inspected guard would produce null, not that a stored
    feature was independently recomputed. ``None`` means insufficient evidence.
    No result certifies original acquisition completeness, basis, join identity,
    or true knownAt. Callers must keep those separate from this inspection.
    """
    evidence: dict[str, Any] = {
        "day": day, "cutoff_minute": cutoff_minute, "feature_name": feature_name,
        "new_feature_values_computed": False, "acquisition_manifest_checked": False,
        "underlying_acquisition_cause": UNKNOWN,
        "source_basis_and_identity_verified": False,
        "original_feature_cell_verified": False,
    }
    findings: list[dict[str, Any]]
    try:
        date.fromisoformat(day)
        if previous_day is not None:
            date.fromisoformat(previous_day)
            if previous_day >= day:
                raise ValueError("previous_day must precede day")
        if isinstance(cutoff_minute, bool) or int(cutoff_minute) != cutoff_minute:
            raise ValueError("cutoff must be an integer minute")
        cutoff = int(cutoff_minute)
        if observed_is_missing is not None and not isinstance(observed_is_missing, bool):
            raise ValueError("observed_is_missing must be bool or None")
        name = feature_name[3:] if feature_name.startswith("p0/") else feature_name
        if feature_name.startswith(("state/", "path/", "entry/", "selector/", "score/")):
            findings = [_finding(INAPPLICABLE, "This is not a frozen P0 price feature.", proves_null=None)]
        elif not (540 <= cutoff <= 690 or 750 <= cutoff <= (900 if day < "2024-11-05" else 925)):
            findings = [_finding(INAPPLICABLE, "No regular-session frozen P0 decision is defined at this cutoff.", proves_null=None)]
        else:
            today, today_info = _prepare(today_rows, day, cutoff)
            previous, previous_info = _prepare(previous_rows, previous_day, None)
            evidence.update(today_input=today_info, previous_input=previous_info)
            uses_previous = (name.endswith("RelativePreviousDay")
                             or name.endswith("/previousDayRows"))
            relevant_info = (today_info, previous_info) if uses_previous else (today_info,)
            if any(info["shape_errors"] or info["ordering_or_duplicate_error"]
                   for info in relevant_info):
                findings = [_finding(UNKNOWN, "Input shape/order/uniqueness is incompatible with the frozen array contract.", proves_null=None)]
            else:
                findings = _audit_feature(name, day, cutoff, today, previous)
                if uses_previous and previous_day is None and cutoff > 900:
                    findings.append(_finding(UNKNOWN, "Previous date is required to verify the dated 15:00/15:25 session boundary.",
                                             proves_null=None, required_input="previous_day"))
    except (ValueError, TypeError, AttributeError, OverflowError) as error:
        findings = [_finding(UNKNOWN, "Invalid audit input; no cause inferred.",
                             proves_null=None, input_error=str(error))]
    known_null = [f for f in findings if f["proves_null"] is True]
    uncertain = [f for f in findings if f["proves_null"] is None]
    expected_null = True if known_null else None if uncertain else False
    if known_null:
        reason = known_null[0]["reason"]
    elif uncertain:
        reason = uncertain[0]["reason"]
    elif findings:
        reason = findings[0]["reason"]
    else:
        reason = CLEAR
    if observed_is_missing is None:
        linkage = "STORED_CELL_NOT_CHECKED"
    elif expected_null is None:
        linkage = "INSUFFICIENT_EVIDENCE"
    elif observed_is_missing and expected_null:
        linkage = "COMPATIBLE_NULL_GUARD_ONLY"
    elif observed_is_missing:
        linkage = "STORED_NULL_UNEXPLAINED"
    elif expected_null:
        linkage = "GUARD_PRESENT_BUT_STORED_CELL_NON_NULL"
    else:
        linkage = "NO_NULL_GUARD_AND_STORED_CELL_NON_NULL"
    return {"version": VERSION, "reason": reason, "expected_null": expected_null,
            "findings": findings, "evidence": evidence,
            "observed_is_missing": observed_is_missing, "stored_null_linkage": linkage,
            "causal_effect_of_repair_established": False}
