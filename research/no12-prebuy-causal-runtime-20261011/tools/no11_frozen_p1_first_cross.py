"""Replay the frozen P1/Q70 first-intent machine, without models or future data.

The caller must verify all private artifact hashes before calling this module.
WATCH_RECORDS and PERSISTENT_GRID are the unchanged base-package artifacts;
FIRST_INTENTS_PRIVATE is the corrected overlay's comparison artifact. Only the
canonical watches in WATCH_RECORDS create replay state. Expected intents are
opened after every replay decision has been made and never supply replay input.

This is a full-row replay: row_indices must cover every canonical grid row.
Sample-only model checks must not call it or claim first-intent parity. The
function accepts numpy arrays, but imports only the Python standard library.
No individual watch, symbol, timestamp, price, or prediction is returned.

Source semantics: persistent-watchlist-uptrend-first-entry-20261003-v2/
first_entry.py:generate, canonical rows selected in model_oof.py, and
CORRECTED_LINEAGE_FAST_FREEZE_20261003/P1_Q70_ENTRY_CONTRACT.json. The comparison
tolerance applies to reported numerical parity only, never to score >= Q70.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime
import gzip
import json
import math


PARITY_ABS_TOLERANCE = 1e-12
_MISMATCH_FIELDS = (
    "missing_expected_watch", "unexpected_expected_watch",
    "duplicate_expected_watch", "watch_identity", "scoring_decisions",
    "first_intent_presence", "row_index", "fold", "intent_timestamp",
    "score", "threshold",
)


def _rows(path, label):
    """Stream JSONL and avoid including private row values in exceptions."""
    try:
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            for line in handle:
                row = json.loads(line)
                if not isinstance(row, dict):
                    raise ValueError(label + "_ROW_NOT_OBJECT")
                yield row
    except (OSError, EOFError, UnicodeError, json.JSONDecodeError):
        raise ValueError(label + "_INVALID_JSONL") from None


def _integer(value, code):
    try:
        if isinstance(value, (str, bytes, bool)):
            raise ValueError
        result = int(value)
        if result != value:
            raise ValueError
        return result
    except (ValueError, TypeError, OverflowError):
        raise ValueError(code) from None


def _number(value, code):
    try:
        if isinstance(value, (str, bytes, bool)):
            raise ValueError
        result = float(value)
        if not math.isfinite(result):
            raise ValueError
        return result
    except (ValueError, TypeError, OverflowError):
        raise ValueError(code) from None


def _string(row, key, code):
    value = row.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(code)
    return value


def _canonical(row, code):
    value = row.get("canonical")
    if not isinstance(value, bool):
        raise ValueError(code)
    return value


def _timestamp(value, code):
    try:
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError
        return parsed
    except (TypeError, ValueError):
        raise ValueError(code) from None


def _fold_contract(q70_by_fold, test_sessions_by_fold):
    thresholds = {}
    sessions = {}
    try:
        for key, value in q70_by_fold.items():
            fold = _integer(key, "INVALID_FOLD_CONTRACT")
            threshold = _number(value, "INVALID_Q70_THRESHOLD")
            if fold < 1 or fold in thresholds or not 0 <= threshold <= 1:
                raise ValueError("INVALID_FOLD_CONTRACT")
            thresholds[fold] = threshold
        claimed_sessions = set()
        for key, values in test_sessions_by_fold.items():
            fold = _integer(key, "INVALID_FOLD_CONTRACT")
            if isinstance(values, (str, bytes)):
                raise ValueError("INVALID_FOLD_SESSIONS")
            dates = set(values)
            if (fold in sessions or not dates
                    or any(not isinstance(day, str) or not day for day in dates)
                    or claimed_sessions.intersection(dates)):
                raise ValueError("INVALID_FOLD_SESSIONS")
            claimed_sessions.update(dates)
            sessions[fold] = dates
    except (AttributeError, TypeError):
        raise ValueError("INVALID_FOLD_CONTRACT") from None
    if not thresholds or set(thresholds) != set(sessions):
        raise ValueError("INVALID_FOLD_CONTRACT")
    return thresholds, sessions


def replay_and_compare(
    watch_path, grid_path, intent_path, row_indices, scores, folds,
    q70_by_fold, test_sessions_by_fold,
):
    """Return aggregate full-replay parity; raise ValueError on invalid inputs.

    Required inputs are hash-verified artifacts and newly recomputed P1 scores.
    row_indices are zero-based positions in the original complete grid, strictly
    increasing. Fold assignments must belong to the saved outer-test sessions;
    this function never chooses a model for a new session. Invalid coverage or
    causality fails before reading the expected-intent file. Valid inputs with
    different expected intents return status FAIL and aggregate mismatch counts.
    """
    thresholds, test_sessions = _fold_contract(
        q70_by_fold, test_sessions_by_fold)
    try:
        count = len(row_indices)
        if len(scores) != count or len(folds) != count:
            raise ValueError("ROW_ARRAY_LENGTH_MISMATCH")
    except TypeError:
        raise ValueError("ROW_ARRAYS_MUST_BE_SIZED") from None
    previous_index = -1
    for value in row_indices:
        index = _integer(value, "INVALID_ROW_INDEX")
        if index <= previous_index:
            raise ValueError("ROW_INDICES_NOT_STRICTLY_INCREASING")
        previous_index = index

    watches = {}
    for row in _rows(watch_path, "WATCH"):
        if not _canonical(row, "INVALID_WATCH_CANONICAL"):
            continue
        key = _string(row, "watch_key", "INVALID_WATCH_KEY")
        session = _string(row, "session", "INVALID_WATCH_SESSION")
        symbol = _string(row, "symbol", "INVALID_WATCH_SYMBOL")
        if key != session + "|" + symbol or key in watches:
            raise ValueError("DUPLICATE_OR_INVALID_WATCH_IDENTITY")
        watches[key] = {
            "session": session, "symbol": symbol,
            "last_timestamp": None, "first_intent": None,
            "scoring_decisions": 0,
        }
    if not watches:
        raise ValueError("NO_CANONICAL_WATCHES")

    cursor = 0
    grid_rows = 0
    rows_after_lock = 0
    for index, row in enumerate(_rows(grid_path, "GRID")):
        grid_rows += 1
        is_selected = cursor < count and int(row_indices[cursor]) == index
        canonical = _canonical(row, "INVALID_GRID_CANONICAL")
        key = _string(row, "watch_key", "INVALID_GRID_WATCH_KEY")
        if not canonical:
            if is_selected or key in watches:
                raise ValueError("NONCANONICAL_GRID_ROW_SELECTED")
            continue
        if key not in watches:
            raise ValueError("GRID_CANONICAL_WATCH_NOT_FOUND")
        if not is_selected:
            raise ValueError("CANONICAL_GRID_COVERAGE_INCOMPLETE")
        watch = watches[key]
        session = _string(row, "session", "INVALID_GRID_SESSION")
        fold = _integer(folds[cursor], "INVALID_ROW_FOLD")
        if (session != watch["session"] or fold not in thresholds
                or session not in test_sessions[fold]):
            raise ValueError("ROW_FOLD_TEST_SESSION_MISMATCH")
        score = _number(scores[cursor], "INVALID_ROW_SCORE")
        if not 0 <= score <= 1:
            raise ValueError("INVALID_ROW_SCORE")
        threshold = thresholds[fold]
        timestamp = _string(row, "intent_timestamp", "INVALID_INTENT_TIMESTAMP")
        intent_time = _timestamp(timestamp, "INVALID_INTENT_TIMESTAMP")
        feature_time = _timestamp(
            row.get("feature_max_timestamp"), "INVALID_FEATURE_TIMESTAMP")
        if feature_time > intent_time:
            raise ValueError("FEATURE_TIMESTAMP_AFTER_INTENT")
        if intent_time.date().isoformat() != session:
            raise ValueError("INTENT_TIMESTAMP_SESSION_MISMATCH")
        if (watch["last_timestamp"] is not None
                and intent_time <= watch["last_timestamp"]):
            raise ValueError("WATCH_GRID_NOT_STRICTLY_CHRONOLOGICAL")
        watch["last_timestamp"] = intent_time
        cursor += 1
        # Validating the entire supplied grid does not make another decision.
        # The first BUY_INTENT remains locked even when no fill is available.
        if watch["first_intent"] is not None:
            rows_after_lock += 1
            continue
        watch["scoring_decisions"] += 1
        if score >= threshold:
            watch["first_intent"] = {
                "row_index": index, "fold": fold,
                "intent_timestamp": timestamp,
                "score": score, "threshold": threshold,
            }
    if cursor != count:
        raise ValueError("ROW_INDEX_OUTSIDE_GRID")

    # All first-intent decisions are now complete. Expected rows cannot create
    # watches, affect the threshold loop, or provide feature/model input.
    mismatch = Counter({field: 0 for field in _MISMATCH_FIELDS})
    seen = set()
    expected_records = 0
    expected_intents = 0
    compared_watches = 0
    mismatch_watches = 0
    for row in _rows(intent_path, "EXPECTED_INTENT"):
        if row.get("family") != "P1" or row.get("policy") != "Q70":
            continue
        expected_records += 1
        key = _string(row, "watch_key", "INVALID_EXPECTED_WATCH_KEY")
        if key in seen:
            mismatch["duplicate_expected_watch"] += 1
            continue
        seen.add(key)
        if key not in watches:
            mismatch["unexpected_expected_watch"] += 1
            continue
        compared_watches += 1
        watch = watches[key]
        local_mismatches = 0
        if (row.get("session") != watch["session"]
                or row.get("symbol") != watch["symbol"]):
            mismatch["watch_identity"] += 1
            local_mismatches += 1
        decisions = _integer(row.get("scoring_decisions"),
                             "INVALID_EXPECTED_SCORING_DECISIONS")
        if decisions < 0:
            raise ValueError("INVALID_EXPECTED_SCORING_DECISIONS")
        if decisions != watch["scoring_decisions"]:
            mismatch["scoring_decisions"] += 1
            local_mismatches += 1
        if "first_intent" not in row:
            raise ValueError("EXPECTED_FIRST_INTENT_MISSING")
        expected = row["first_intent"]
        actual = watch["first_intent"]
        if expected is not None and not isinstance(expected, dict):
            raise ValueError("INVALID_EXPECTED_FIRST_INTENT")
        expected_intents += int(expected is not None)
        if (expected is None) != (actual is None):
            mismatch["first_intent_presence"] += 1
            local_mismatches += 1
        elif expected is not None:
            for field in ("row_index", "fold"):
                value = _integer(expected.get(field), "INVALID_EXPECTED_INTENT_FIELD")
                if value != actual[field]:
                    mismatch[field] += 1
                    local_mismatches += 1
            value = _string(expected, "intent_timestamp", "INVALID_EXPECTED_INTENT_FIELD")
            if value != actual["intent_timestamp"]:
                mismatch["intent_timestamp"] += 1
                local_mismatches += 1
            for field in ("score", "threshold"):
                value = _number(expected.get(field), "INVALID_EXPECTED_INTENT_FIELD")
                if not math.isclose(value, actual[field], rel_tol=0.0,
                                    abs_tol=PARITY_ABS_TOLERANCE):
                    mismatch[field] += 1
                    local_mismatches += 1
        mismatch_watches += int(local_mismatches > 0)
    mismatch["missing_expected_watch"] = len(set(watches).difference(seen))
    passed = not any(mismatch.values())
    intents = sum(watch["first_intent"] is not None for watch in watches.values())
    return {
        "status": "PASS" if passed else "FAIL",
        "parity_passed": passed,
        "family": "P1", "policy": "Q70", "full_replay": True,
        "canonical_watch_count": len(watches),
        "canonical_grid_row_count": cursor,
        "grid_row_count": grid_rows,
        "scoring_decisions": sum(w["scoring_decisions"] for w in watches.values()),
        "rows_after_first_intent_lock": rows_after_lock,
        "replayed_first_intent_count": intents,
        "replayed_no_intent_count": len(watches) - intents,
        "expected_p1_q70_record_count": expected_records,
        "expected_first_intent_count": expected_intents,
        "compared_watch_count": compared_watches,
        "mismatched_compared_watch_count": mismatch_watches,
        "mismatch_counts": dict(mismatch),
        "score_threshold_absolute_tolerance": PARITY_ABS_TOLERANCE,
        "threshold_trace_sha256_compared": False,
        "expected_intents_read_after_replay": True,
        "future_evaluator_read": False,
        "private_rows_returned": 0,
    }
