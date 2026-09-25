"""R21 evaluator-only price geometry. Never import this from an EXIT decision.

Input extrema must come from a separately frozen evaluator horizon/definition.
No price path, future peak or oracle timestamp is exposed by the observer module.
This is a metric kernel, not an EXIT policy, target-selection rule or backtest.
"""
from __future__ import annotations
from dataclasses import dataclass
import math

BUCKETS = ('<1%', '1-2%', '2-3%', '3-4%', '4-5%', '>=5%')


def number(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def check(ok, reason):
    if not ok:
        raise ValueError(reason)


def price(x):
    check(number(x) and x > 0, 'INVALID_PRICE')


def minute(x):
    check(isinstance(x, int) and not isinstance(x, bool) and 0 <= x <= 1440, 'INVALID_MINUTE')


def opportunity_bucket(range_pct):
    """Half-open non-overlapping buckets, plus explicit unavailable/degenerate."""
    if range_pct is None:
        return 'UNAVAILABLE'
    check(number(range_pct), 'INVALID_RANGE')
    if range_pct <= 0:
        return 'NON_POSITIVE_RANGE'
    for upper, name in zip((1, 2, 3, 4, 5), BUCKETS):
        if range_pct < upper:
            return name
    return BUCKETS[-1]


@dataclass(frozen=True)
class OrderedGeometry:
    low: float
    high: float
    low_bar_start: int
    high_bar_start: int
    horizon_end: int
    definition_id: str
    coverage_status: str

    def validate(self):
        price(self.low); price(self.high)
        for x in (self.low_bar_start, self.high_bar_start, self.horizon_end):
            minute(x)
        check(self.low_bar_start < self.high_bar_start, 'LOW_HIGH_NOT_STRICTLY_ORDERED')
        check(self.high_bar_start + 1 <= self.horizon_end, 'HIGH_OUTSIDE_HORIZON')
        check(isinstance(self.definition_id, str) and bool(self.definition_id.strip()), 'GEOMETRY_DEFINITION_REQUIRED')
        check(self.coverage_status in ('COMPLETE', 'PARTIAL', 'MISSING'), 'COVERAGE_STATUS_REQUIRED')


@dataclass(frozen=True)
class PostEntryHigh:
    high: float
    high_bar_start: int
    horizon_end: int
    definition_id: str
    coverage_status: str

    def validate(self):
        price(self.high); minute(self.high_bar_start); minute(self.horizon_end)
        check(self.high_bar_start + 1 <= self.horizon_end, 'HIGH_OUTSIDE_HORIZON')
        check(isinstance(self.definition_id, str) and bool(self.definition_id.strip()), 'GEOMETRY_DEFINITION_REQUIRED')
        check(self.coverage_status in ('COMPLETE', 'PARTIAL', 'MISSING'), 'COVERAGE_STATUS_REQUIRED')


def evaluate_capture(*, entry_price, entry_minute, exit_price, exit_minute,
                     cost_pp, geometry: OrderedGeometry | None, post_entry_high: PostEntryHigh | None = None,
                     owned_peak=None, owned_peak_confirmed_at=None,
                     owned_path_complete=False):
    """Report both whole-opportunity and same-ordered-high realization.

    Entry prices are preserved effective frozen prices; no second Entry slippage.
    cost_pp is REQUIRED and supplied by the future NEW EXIT execution contract:
    no inherited 0.05pp/default cost, Fixed12 horizon or Candidate A dependency.

    Full-opportunity extrema can occur AFTER EXIT. Their gap is not owned-profit
    giveback. Owned giveback requires a separately verified owned-path peak.
    """
    check(number(cost_pp) and cost_pp >= 0, 'EXPLICIT_NONNEGATIVE_COST_REQUIRED')
    check(type(owned_path_complete) is bool, 'OWNED_COVERAGE_BOOLEAN_REQUIRED')
    if geometry is not None:
        geometry.validate()
    if post_entry_high is not None:
        post_entry_high.validate()
        check(geometry is None or post_entry_high.horizon_end == geometry.horizon_end, 'DIFFERENT_EVALUATION_HORIZONS')
    r = {'evaluatorOnly': True, 'geometryDefinition': geometry.definition_id if geometry else None,
         'geometryCoverage': geometry.coverage_status if geometry else 'MISSING',
         'bucket': 'UNAVAILABLE', 'observedBucket': 'UNAVAILABLE',
         'opportunityRangePct': None, 'observedOpportunityRangePct': None,
         'entryPositionPct': None, 'entryToSameOrderedHighPct': None,
         'entryToExitGrossPct': None, 'entryToExitNetPct': None,
         'wholeOpportunityCapturePct': None, 'sameHighUpsideCapturePct': None,
         'sameHighEvaluatorGapPp': None, 'ownedPeakGivebackPp': None,
         'sameHighAfterExit': None, 'entryBeforeOrderedLow': None,
         'postEntryHighDefinition': post_entry_high.definition_id if post_entry_high else None,
         'entryToPostEntryHighPct': None, 'postEntryUpsideCapturePct': None,
         'postEntryHighEvaluatorGapPp': None, 'postEntryCaptureStatus': 'HIGH_UNAVAILABLE',
         'captureStatus': 'GEOMETRY_UNAVAILABLE', 'entryStatus': 'NO_ENTRY',
         'exitStatus': 'NO_ENTRY', 'explicitCostPp': cost_pp}
    if geometry:
        g = geometry
        rng = 100 * (g.high - g.low) / g.low
        r['observedOpportunityRangePct'] = rng
        r['observedBucket'] = opportunity_bucket(rng)
        if g.coverage_status == 'COMPLETE':
            r['opportunityRangePct'] = rng
            r['bucket'] = r['observedBucket']
    if entry_price is None or entry_minute is None:
        check(entry_price is None and entry_minute is None and exit_price is None and exit_minute is None,
              'NO_ENTRY_WITH_PRICE_TIME_OR_EXIT')
        check(owned_peak is None and owned_peak_confirmed_at is None, 'NO_ENTRY_WITH_OWNED_PEAK')
        r['captureStatus'] = 'NO_ENTRY'
        r['postEntryCaptureStatus'] = 'NO_ENTRY'
        return r
    price(entry_price); minute(entry_minute)
    r['entryStatus'] = 'FILLED_REFERENCE'
    r['exitStatus'] = 'UNRESOLVED'
    resolved = exit_price is not None and exit_minute is not None
    check(resolved or (exit_price is None and exit_minute is None), 'PARTIAL_EXIT_REFERENCE')
    if resolved:
        price(exit_price); minute(exit_minute)
        check(exit_minute > entry_minute, 'EXIT_NOT_AFTER_ENTRY')
        r['exitStatus'] = 'EXIT_REFERENCE'
        r['entryToExitGrossPct'] = 100 * (exit_price - entry_price) / entry_price
        r['entryToExitNetPct'] = r['entryToExitGrossPct'] - cost_pp
    if post_entry_high is not None:
        h = post_entry_high
        if h.coverage_status != 'COMPLETE':
            r['postEntryCaptureStatus'] = 'INCOMPLETE_HIGH_GEOMETRY'
        elif h.high_bar_start <= entry_minute:
            r['postEntryCaptureStatus'] = 'HIGH_NOT_STRICTLY_AFTER_ENTRY'
        elif resolved and exit_minute > h.horizon_end:
            r['postEntryCaptureStatus'] = 'OUTSIDE_COMMON_EVALUATION_HORIZON'
        else:
            r['entryToPostEntryHighPct'] = 100 * (h.high - entry_price) / entry_price
            if resolved:
                r['postEntryHighEvaluatorGapPp'] = 100 * (h.high - exit_price) / entry_price
                if h.high > entry_price:
                    r['postEntryUpsideCapturePct'] = 100 * (exit_price - entry_price) / (h.high - entry_price)
                    r['postEntryCaptureStatus'] = 'EVALUABLE'
                else:
                    r['postEntryCaptureStatus'] = 'NON_POSITIVE_AVAILABLE_UPSIDE'
            else:
                r['postEntryCaptureStatus'] = 'UNRESOLVED_EXIT'
    if owned_peak is not None or owned_peak_confirmed_at is not None:
        check(owned_peak is not None and owned_peak_confirmed_at is not None, 'PARTIAL_OWNED_PEAK')
        price(owned_peak); minute(owned_peak_confirmed_at)
        check(resolved, 'OWNED_EXIT_METRIC_WITHOUT_EXIT')
        check(entry_minute < owned_peak_confirmed_at <= exit_minute, 'PEAK_NOT_KNOWN_DURING_OWNERSHIP')
        if owned_path_complete:
            # Include actual Entry/EXIT references in the owned mark path.
            peak = max(entry_price, exit_price, owned_peak)
            r['ownedPeakGivebackPp'] = 100 * (peak - exit_price) / entry_price
    if geometry is None:
        return r
    g = geometry
    r['entryBeforeOrderedLow'] = entry_minute < g.low_bar_start
    if g.coverage_status != 'COMPLETE':
        r['captureStatus'] = 'INCOMPLETE_GEOMETRY'
        return r
    if g.high <= g.low:
        r['captureStatus'] = 'NON_POSITIVE_RANGE'
        return r
    if entry_minute >= g.horizon_end or (resolved and exit_minute > g.horizon_end):
        r['captureStatus'] = 'OUTSIDE_COMMON_EVALUATION_HORIZON'
        return r
    r['entryPositionPct'] = 100 * (entry_price - g.low) / (g.high - g.low)
    if resolved:
        r['wholeOpportunityCapturePct'] = 100 * (exit_price - entry_price) / (g.high - g.low)
        r['sameHighAfterExit'] = g.high_bar_start + 1 > exit_minute
    if g.high_bar_start <= entry_minute:
        r['captureStatus'] = 'ORDERED_HIGH_NOT_STRICTLY_AFTER_ENTRY'
        return r
    r['entryToSameOrderedHighPct'] = 100 * (g.high - entry_price) / entry_price
    if not resolved:
        r['captureStatus'] = 'UNRESOLVED_EXIT'
        return r
    r['sameHighEvaluatorGapPp'] = 100 * (g.high - exit_price) / entry_price
    if g.high <= entry_price:
        r['captureStatus'] = 'NON_POSITIVE_AVAILABLE_UPSIDE'
        return r
    r['sameHighUpsideCapturePct'] = 100 * (exit_price - entry_price) / (g.high - entry_price)
    r['captureStatus'] = 'EVALUABLE'
    return r
