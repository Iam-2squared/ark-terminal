"""Pure FIRST_INTENT projection; no model, orders, or State9 recomputation.

The trace is already produced by frozen State9/Path.  Only closed endpoints at
or before first_intent.intent_minute are inspected.  Observation availability is
the inherited historical bar-end assumption, not an actual-arrival certificate.
Distances use the frozen normalized U coordinate.  Prior local-pivot features
describe a pattern; they are not a position's Local Guard or an EXIT rule.
"""
from fractions import Fraction
import hashlib
import json
import math


VERSION = "FIRST_INTENT_PREFIX_PROJECTION_DRAFT_V1"
UNKNOWN = "__UNKNOWN__"
STATES = frozenset(("RISE", "SHARP_RISE", "RISE_STOP", "PULLBACK", "RANGE",
                    "REBOUND", "DROP", "SHARP_DROP", "DROP_STOP"))
NUMERIC = (
    "entry/p1_score", "entry/p1_threshold", "entry/p1_margin",
    "entry/intent_clock", "selector/first_clock", "selector/to_intent_active_delay",
    "state/observed", "state/endpoint_age_minutes", "state/context_direction",
    "state/local_direction", "state/fast_applicable", "state/stop_count",
    "path/dwell_observed_bars", "path/dwell_scheduled_bars",
    "path/transitions_total", "path/segment_breaks_total",
    "path/observation_losses_total", "path/observed_prefix_rows",
    "path/last_transition_age_minutes",
    *(f"path/{kind}_{w}m" for w in (15, 30, 60)
      for kind in ("transitions", "observed_rows")),
    "structure/close_minus_protected_before_u",
    "structure/close_minus_protected_next_u",
    "structure/protected_update_age_bars", "structure/context_age_bars",
    "structure/protected_effective_in_bars",
    "local/prior_pivot_count", "local/prior_lhl_available",
    "local/prior_lhl_rise_u", "local/close_minus_prior_h_plus_half_u",
    "local/prior_l1_minus_protected_before_u",
    "local/close_minus_prior_l1_minus_half_u",
    "local/prior_l0_confirmation_age_bars", "local/prior_h_confirmation_age_bars",
    "local/prior_l1_confirmation_age_bars",
    "local/prior_lhl_close_confirmed_higher_low",
)
CATEGORICAL = (
    "state/current_primary", "state/activity", "state/basis",
    "state/direction_basis", "state/fast", "state/numeric_status",
    "path/last3_connected_primary",
)
STATE_FIELDS = (
    "as_of", "observed_at", "current_semantics_observed", "numeric_status",
    "primary", "activity", "basis", "direction_basis", "context", "leg_direction",
    "close_u", "protected_before", "protected_after_effective_next",
    "protected_updated_at", "protected_effective_from", "context_established_at",
    "local_pivot_confirmed", "bar_metadata", "events", "stop",
)
PATH_FIELDS = (
    "scheduled_t", "causal_segment_id", "Primary_or_null", "context_direction",
    "local_direction", "fast", "fast_applicable_to_primary", "dwell_observed_bars",
    "dwell_scheduled_bars", "quality",
)


def _mapping(value):
    return value if isinstance(value, dict) else {}


def _integer(value):
    return type(value) is int


def _exact(value):
    if value is None or type(value) is bool:
        return None
    try:
        return Fraction(str(value))
    except (ValueError, ZeroDivisionError, TypeError):
        return None


def fresh(row):
    """Validate formal observation, never use carried display_primary."""
    s, p = _mapping(row.get("state")), _mapping(row.get("path"))
    at = s.get("as_of")
    meta = _mapping(s.get("bar_metadata"))
    metadata_ok = bool(meta) and (
        _integer(meta.get("t")) and meta["t"] == at
        and _integer(meta.get("known_at")) and meta["known_at"] <= at
        and all(isinstance(meta.get(k), str) and meta[k] for k in ("source", "auction")))
    return (s.get("current_semantics_observed") is True
            and s.get("numeric_status") == "ACCEPTED"
            and _integer(at) and s.get("observed_at") == at
            and p.get("scheduled_t") == at
            and isinstance(p.get("causal_segment_id"), str)
            and bool(p["causal_segment_id"])
            and p.get("Primary_or_null") in STATES
            and s.get("primary") == p["Primary_or_null"]
            and s.get("activity") in ("LIVE", "STOPPED", "BALANCED")
            and s.get("basis") in ("OBSERVED_FRESH", "OBSERVED_NEW_SEGMENT_ONLY")
            and metadata_ok)


def _source(row):
    s, p = _mapping(row.get("state")), _mapping(row.get("path"))
    meta, quality = _mapping(s.get("bar_metadata")), _mapping(p.get("quality"))
    source = meta.get("source", quality.get("source"))
    auction = meta.get("auction", quality.get("auction"))
    return (source, auction) if all(isinstance(x, str) and x for x in (source, auction)) else None


def connected(previous, current):
    """Evidence of adjacent observations in the same frozen causal segment."""
    if previous is None or not fresh(previous) or not fresh(current):
        return False
    a, b = previous["path"], current["path"]
    if (b["causal_segment_id"] != a["causal_segment_id"]
            or b["scheduled_t"] != a["scheduled_t"] + 1
            or current["bar_end_minute"] != previous["bar_end_minute"] + 1
            or _source(previous) is None or _source(previous) != _source(current)):
        return False
    events = current.get("path_events")
    if not isinstance(events, list):
        return False
    if any(_mapping(e).get("event_type") in ("SEGMENT_BREAK", "OBSERVATION_LOST",
                                             "OBSERVATION_RESUMED") for e in events):
        return False
    return "SEGMENT_RESET_NO_GAP_RETURN" not in current["state"].get("events", [])


def project(entry, trace):
    """Return numeric/category inputs plus explicit quality/provenance.

    Invalid or absent source attributes are null with a reason.  This function
    does not join private P0/P1 matrices or certify learned-score dependencies.
    Caller must perform those audits before enabling model fitting.
    """
    intent = _mapping(entry.get("first_intent"))
    cutoff = intent.get("intent_minute")
    if not _integer(cutoff):
        raise ValueError("FIRST_INTENT_MINUTE_REQUIRED")
    prefix = []
    for row in trace:
        if not isinstance(row, dict) or not _integer(row.get("bar_end_minute")):
            raise ValueError("TRACE_BAR_END_MINUTE_REQUIRED")
        # Exclude first, before reading any nested State/Path/suffix data.
        if row["bar_end_minute"] <= cutoff:
            prefix.append(row)
    if any(a["bar_end_minute"] >= b["bar_end_minute"] for a, b in zip(prefix, prefix[1:])):
        raise ValueError("PREFIX_ORDER_NOT_STRICT")
    latest = prefix[-1] if prefix else None
    current = bool(latest and latest["bar_end_minute"] == cutoff and fresh(latest))
    s = _mapping(latest.get("state")) if latest else {}
    p = _mapping(latest.get("path")) if latest else {}
    numeric = dict.fromkeys(NUMERIC)
    categorical = {k: UNKNOWN for k in CATEGORICAL}
    reasons = {}
    issues = []

    def put(name, value, missing="SOURCE_FIELD_UNAVAILABLE"):
        exact = _exact(value)
        if exact is not None:
            try:
                number = float(exact)
            except (OverflowError, ValueError):
                number = float("nan")
            if math.isfinite(number):
                numeric[name] = number
                return
        reasons[name] = missing if value is None else "INVALID_OR_NONFINITE_NUMERIC"

    put("entry/p1_score", intent.get("score"))
    put("entry/p1_threshold", intent.get("threshold"))
    score, threshold = _exact(intent.get("score")), _exact(intent.get("threshold"))
    put("entry/p1_margin", score - threshold if score is not None and threshold is not None else None)
    put("entry/intent_clock", cutoff)
    selector_at = entry.get("selector_minute")
    put("selector/first_clock", selector_at
        if _integer(selector_at) and selector_at <= cutoff else None,
        "SELECTOR_CLOCK_MISSING_OR_AFTER_INTENT")
    delay = _exact(entry.get("selector_to_intent_active_delay"))
    put("selector/to_intent_active_delay", delay if delay is not None and delay >= 0 else None,
        "SELECTOR_DELAY_MISSING_OR_NEGATIVE")
    put("state/observed", int(current))
    put("state/endpoint_age_minutes", cutoff - latest["bar_end_minute"] if latest else None,
        "NO_PREFIX_ENDPOINT")
    invalid_reason = ("NO_PREFIX_ENDPOINT" if not latest else
                      "STALE_PREFIX_ENDPOINT" if latest["bar_end_minute"] != cutoff else
                      "CURRENT_FORMAL_OBSERVATION_UNAVAILABLE")
    if latest and not _mapping(s.get("bar_metadata")):
        issues.append("STATE_BAR_METADATA_UNAVAILABLE")
    episode = []
    if current:
        episode.append(latest)
        for row in reversed(prefix[:-1]):
            if not connected(row, episode[-1]):
                break
            episode.append(row)
        episode.reverse()
        for feature, field in (("state/context_direction", "context_direction"),
                               ("state/local_direction", "local_direction"),
                               ("path/dwell_observed_bars", "dwell_observed_bars"),
                               ("path/dwell_scheduled_bars", "dwell_scheduled_bars")):
            put(feature, p.get(field))
        applicable = p.get("fast_applicable_to_primary")
        put("state/fast_applicable", int(applicable) if type(applicable) is bool else None)
        put("state/stop_count", _mapping(s.get("stop")).get("count"),
            "NOT_APPLICABLE_OR_STOP_FIELD_UNAVAILABLE")
        categorical.update({
            "state/current_primary": p["Primary_or_null"],
            "state/activity": s["activity"], "state/basis": s["basis"],
            "state/direction_basis": s.get("direction_basis") or UNKNOWN,
            "state/fast": str(p["fast"]) if type(p.get("fast")) is bool else UNKNOWN,
            "state/numeric_status": s["numeric_status"],
        })
        sequence = []
        for row in episode:
            primary = row["path"]["Primary_or_null"]
            if not sequence or primary != sequence[-1]:
                sequence.append(primary)
        categorical["path/last3_connected_primary"] = ">".join(sequence[-3:])
    else:
        for name in NUMERIC:
            if name.startswith(("structure/", "local/")) or name in (
                    "state/context_direction", "state/local_direction", "state/fast_applicable",
                    "state/stop_count", "path/dwell_observed_bars", "path/dwell_scheduled_bars"):
                reasons[name] = invalid_reason
        issues.append(invalid_reason)

    # These are past wall-clock descriptions, not active-minute durations or
    # transitions manufactured across a gap.  Counts use stored Path events.
    event_schema = bool(prefix) and all(isinstance(r.get("path_events"), list)
                                       and all(isinstance(e, dict) for e in r["path_events"])
                                       for r in prefix)
    transitions, events = [], []
    if event_schema:
        for i, row in enumerate(prefix):
            events.extend(row["path_events"])
            for event in row["path_events"]:
                if event.get("event_type") == "TRANSITION":
                    if i and connected(prefix[i - 1], row):
                        transitions.append(row["bar_end_minute"])
                    else:
                        issues.append("UNCONNECTED_TRANSITION_IGNORED")
        put("path/transitions_total", len(transitions))
        put("path/segment_breaks_total", sum(e.get("event_type") == "SEGMENT_BREAK" for e in events))
        put("path/observation_losses_total", sum(e.get("event_type") == "OBSERVATION_LOST" for e in events))
        put("path/last_transition_age_minutes", cutoff - transitions[-1] if transitions else None,
            "NO_VALID_PRIOR_TRANSITION")
    for window in (15, 30, 60):
        put(f"path/transitions_{window}m",
            sum(cutoff - window < t <= cutoff for t in transitions) if event_schema else None,
            "PATH_EVENT_SCHEMA_UNAVAILABLE")
        put(f"path/observed_rows_{window}m",
            sum(cutoff - window < r["bar_end_minute"] <= cutoff and fresh(r) for r in prefix)
            if prefix else None, "NO_PREFIX_ENDPOINT")
    put("path/observed_prefix_rows", sum(fresh(r) for r in prefix) if prefix else None,
        "NO_PREFIX_ENDPOINT")
    if not event_schema:
        for name in ("path/transitions_total", "path/segment_breaks_total",
                     "path/observation_losses_total", "path/last_transition_age_minutes"):
            reasons[name] = "PATH_EVENT_SCHEMA_UNAVAILABLE"

    if current:
        at = s["as_of"]
        close, before = _exact(s.get("close_u")), _exact(s.get("protected_before"))
        after = _exact(s.get("protected_after_effective_next"))
        put("structure/close_minus_protected_before_u", close - before
            if close is not None and before is not None else None)
        effective = s.get("protected_effective_from")
        next_available = _integer(effective) and effective <= at + 1
        put("structure/close_minus_protected_next_u", close - after
            if close is not None and after is not None and next_available else None,
            "PROTECTED_NEXT_EFFECT_SCHEMA_UNAVAILABLE")
        put("structure/protected_effective_in_bars", effective - at if next_available else None,
            "PROTECTED_NEXT_EFFECT_SCHEMA_UNAVAILABLE")
        for name, field in (("structure/protected_update_age_bars", "protected_updated_at"),
                            ("structure/context_age_bars", "context_established_at")):
            start = s.get(field)
            put(name, at - start if _integer(start) and start <= at else None,
                "TIMESTAMP_MISSING_OR_AFTER_CURRENT")
        pivots, pivot_schema = [], True
        episode_start = episode[0]["state"]["as_of"]
        for row in episode:
            state = row["state"]
            if "local_pivot_confirmed" not in state:
                pivot_schema = False
                continue
            pivot = state["local_pivot_confirmed"]
            if pivot is None:
                continue
            q = _mapping(pivot)
            confirmed, extremum, x = q.get("confirmed_at"), q.get("extremum_t"), _exact(q.get("x"))
            if (q.get("kind") not in ("L", "H") or x is None
                    or not _integer(confirmed) or not _integer(extremum)
                    or extremum > confirmed or confirmed > state["as_of"]):
                pivot_schema = False
                issues.append("INVALID_LOCAL_PIVOT_SCHEMA_OR_TIME")
                continue
            if confirmed >= at:
                continue  # current confirmation cannot update the prior pattern
            if confirmed < episode_start:
                # No cached confirmation is allowed to bridge the last reset.
                pivot_schema = False
                issues.append("LOCAL_PIVOT_CONFIRMATION_BEFORE_CONNECTED_EPISODE")
                continue
            item = (q["kind"], x, extremum, confirmed)
            if item in pivots:
                continue
            if pivots and confirmed <= pivots[-1][3]:
                pivot_schema = False
                issues.append("LOCAL_PIVOT_CONFIRMATION_ORDER_CONFLICT")
                continue
            pivots.append(item)
        prior = pivots[-3:]
        lhl = pivot_schema and len(prior) == 3 and [x[0] for x in prior] == ["L", "H", "L"]
        put("local/prior_pivot_count", len(prior) if pivot_schema else None,
            "LOCAL_PIVOT_SCHEMA_UNAVAILABLE")
        put("local/prior_lhl_available", int(lhl) if pivot_schema else None,
            "LOCAL_PIVOT_SCHEMA_UNAVAILABLE")
        for name in NUMERIC:
            if name.startswith("local/") and name not in (
                    "local/prior_pivot_count", "local/prior_lhl_available"):
                reasons[name] = "NO_PRIOR_LHL" if pivot_schema else "LOCAL_PIVOT_SCHEMA_UNAVAILABLE"
        if lhl:
            a, h, b = prior
            rise = b[1] - a[1]
            put("local/prior_lhl_rise_u", rise)
            put("local/close_minus_prior_h_plus_half_u", close - h[1] - Fraction(1, 2)
                if close is not None else None)
            put("local/prior_l1_minus_protected_before_u", b[1] - before if before is not None else None)
            put("local/close_minus_prior_l1_minus_half_u", close - b[1] + Fraction(1, 2)
                if close is not None else None)
            for label, pivot in (("l0", a), ("h", h), ("l1", b)):
                put(f"local/prior_{label}_confirmation_age_bars", at - pivot[3])
            put("local/prior_lhl_close_confirmed_higher_low",
                int(rise >= Fraction(1, 2) and close >= h[1] + Fraction(1, 2))
                if close is not None else None)

    # Remove stale reasons for features that received a valid value later.
    reasons = {name: reason for name, reason in reasons.items() if numeric[name] is None}
    hashed_rows = [{"bar_end_minute": r["bar_end_minute"],
                    "state": {k: _mapping(r.get("state")).get(k) for k in STATE_FIELDS},
                    "path": {k: _mapping(r.get("path")).get(k) for k in PATH_FIELDS},
                    "path_events": r.get("path_events")} for r in prefix]
    digest = hashlib.sha256(json.dumps(hashed_rows, sort_keys=True, separators=(",", ":"),
                                       default=str).encode()).hexdigest()
    return {"numeric": numeric, "categorical": categorical,
            "quality": {"current_observed": current, "feature_reasons": reasons,
                        "issues": sorted(set(issues)), "connected_prefix_rows": len(episode)},
            "provenance": {"cutoff_basis": "FROZEN_FIRST_INTENT", "cutoff_minute": cutoff,
                           "max_known_minute": latest["bar_end_minute"] if latest else None,
                           "prefix_rows": len(prefix), "prefix_sha256": digest,
                           "prefix_hash_scope": "ALLOWLISTED_FIELDS_OF_INTENT_PREFIX",
                           "historical_actual_arrival": "UNKNOWN", "version": VERSION,
                           "learned_score_lineage_audited": False}}
