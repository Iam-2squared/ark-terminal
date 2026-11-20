"""RC2 candidate; RC1 audit repair migration basis, now exact coefficient/exponent arithmetic and RC2 frozen semantics. Same author exposure is disclosed."""
from __future__ import annotations
from copy import deepcopy
from dataclasses import dataclass, asdict, field
from .exact import N, parse
from math import gcd
from typing import Optional


D = N
PATTERNS = (
    'RISE_STOP', 'RISE', 'SHARP_RISE', 'PULLBACK', 'RANGE',
    'REBOUND', 'SHARP_DROP', 'DROP', 'DROP_STOP',
)

@dataclass(frozen=True)
class Profile:
    local_reversal: D = field(default_factory=lambda: D('1'))
    structure_reversal: D = field(default_factory=lambda: D('4'))
    break_buffer: D = field(default_factory=lambda: D('0.5'))
    progress_increment: D = field(default_factory=lambda: D('0.5'))
    stop_half_band: D = field(default_factory=lambda: D('0.5'))
    stop_min_age: int = 3
    stop_min_bars: int = 3
    stop_max_qualified_bars: int = 10
    balance_bars: int = 10
    balance_net_max: D = field(default_factory=lambda: D('0.5'))
    balance_min_turns: int = 3
    balance_min_swing_width: D = field(default_factory=lambda: D('2'))
    balance_eff_max: D = field(default_factory=lambda: D('0.25'))
    fast_intervals: int = 5
    fast_displacement: D = field(default_factory=lambda: D('5'))
    fast_eff_min: D = field(default_factory=lambda: D('0.8'))

    def __post_init__(self):
        positive = (self.local_reversal, self.structure_reversal,
                    self.break_buffer, self.progress_increment,
                    self.stop_half_band, self.fast_displacement)
        if any(not x.is_finite() or x <= 0 for x in positive):
            raise ValueError('Thresholds must be positive and finite.')
        if self.structure_reversal <= self.local_reversal:
            raise ValueError('Structure scale must exceed local scale.')
        if self.progress_increment != self.stop_half_band:
            raise ValueError('RC1 locks progress increment to stop half-band.')
        if self.stop_half_band >= self.local_reversal:
            raise ValueError('Stop band must be narrower than local reversal.')
        if not (0 <= self.balance_eff_max < self.fast_eff_min <= 1):
            raise ValueError('Invalid efficiency thresholds.')
        if self.balance_bars < self.stop_min_bars or self.fast_intervals < 1:
            raise ValueError('Invalid history lengths.')
        if self.stop_max_qualified_bars < self.balance_bars:
            raise ValueError('Stop retirement must include a full observed balance window.')

@dataclass(frozen=True)
class Bar:
    """t is a strictly increasing scheduled-bar-end ordinal; known_at is separate."""
    t: int
    o: D
    h: D
    l: D
    c: D
    known_at: int
    auction: str = 'A'
    source: str = 'synthetic'

    def valid(self) -> bool:
        vals = (self.o, self.h, self.l, self.c)
        return (type(self.t) is int and type(self.known_at) is int
                and all(isinstance(v, D) and v.is_finite() for v in vals)
                and self.l <= min(self.o, self.c)
                and self.h >= max(self.o, self.c)
                and isinstance(self.auction, str) and bool(self.auction)
                and isinstance(self.source, str) and bool(self.source))

@dataclass(frozen=True)
class Pivot:
    kind: str
    x: D
    extremum_t: int
    confirmed_at: int
    generation_reason: str = "DC_CONFIRMED"

class DC:
    """Close-only directional change. Pivot time is never confirmation time."""
    def __init__(self, theta: D):
        self.theta = theta
        self.direction = 0
        self.high: Optional[tuple[D, int]] = None
        self.low: Optional[tuple[D, int]] = None
        self.extreme: Optional[tuple[D, int]] = None
        self.pivots: list[Pivot] = []

    def seed(self, x: D, t: int):
        self.direction = 0
        self.high = self.low = self.extreme = (x, t)
        self.pivots = []

    def rebase(self, origin: tuple[D, int], x: D, t: int, direction: int, reason="DC_CONFIRMED"):
        """New context origin is an observed extreme, not the crossed level."""
        self.direction = direction
        self.high = (max(origin[0], x), origin[1] if origin[0] >= x else t)
        self.low = (min(origin[0], x), origin[1] if origin[0] <= x else t)
        self.extreme = (x, t)
        self.pivots = [Pivot('L' if direction == 1 else 'H', origin[0], origin[1], t, reason)]

    def step(self, x: D, t: int) -> Optional[Pivot]:
        if self.extreme is None:
            self.seed(x, t)
            return None
        event = None
        if self.direction == 0:
            assert self.high is not None and self.low is not None
            up = x - self.low[0] >= self.theta
            down = self.high[0] - x >= self.theta
            if up and down:
                raise AssertionError('Unresolved initialization tie: input history is inconsistent.')
            if up:
                event = Pivot('L', self.low[0], self.low[1], t)
                self.direction, self.extreme = 1, (x, t)
            elif down:
                event = Pivot('H', self.high[0], self.high[1], t)
                self.direction, self.extreme = -1, (x, t)
            else:
                # Exact ties retain the earliest extremum, not a refreshed clock.
                if x > self.high[0]: self.high = (x, t)
                if x < self.low[0]: self.low = (x, t)
        elif self.direction == 1:
            if x > self.extreme[0]:
                self.extreme = (x, t)
            elif self.extreme[0] - x >= self.theta:
                event = Pivot('H', self.extreme[0], self.extreme[1], t)
                self.direction, self.extreme = -1, (x, t)
        else:
            if x < self.extreme[0]:
                self.extreme = (x, t)
            elif x - self.extreme[0] >= self.theta:
                event = Pivot('L', self.extreme[0], self.extreme[1], t)
                self.direction, self.extreme = 1, (x, t)
        if event:
            self.pivots.append(event)
        return event

@dataclass
class Context:
    direction: int = 0
    protected: Optional[Pivot] = None
    extreme: Optional[tuple[D, int]] = None
    established_at: Optional[int] = None
    level_updated_at: Optional[int] = None

@dataclass
class Stop:
    direction: int
    center: D
    low: D
    high: D
    start: int
    count: int = 1
    recognized_at: int = 0
    count_start: int = 0
    progress_at: int = 0
    evidence_window_start: int = 0
    evidence_ids: list = None
    continuation_ids: list = None

@dataclass
class Balance:
    low: D
    high: D
    close_low: tuple[D, int]
    close_high: tuple[D, int]
    established_at: int
    reason: str
    window_ids: list = None
    old_window_ids: list = None
    low_at: int = 0
    high_at: int = 0
    exit_low: D = field(default_factory=lambda: D(0))
    exit_high: D = field(default_factory=lambda: D(0))


def projection(ctx: int, leg: int, fast: bool) -> str:
    if leg == 1:
        return 'REBOUND' if ctx == -1 else ('SHARP_RISE' if fast else 'RISE')
    if leg == -1:
        return 'PULLBACK' if ctx == 1 else ('SHARP_DROP' if fast else 'DROP')
    raise ValueError('LIVE projection requires an observed direction.')


def wire(obj):
    if isinstance(obj, D): return str(obj)
    if isinstance(obj, dict): return {k: wire(v) for k, v in obj.items()}
    if isinstance(obj, (tuple, list)): return [wire(v) for v in obj]
    return obj


class State9:
    def __init__(self, profile: Profile = Profile()):
        self.p = profile
        self.last_call: Optional[int] = None
        self.last_accepted: Optional[Bar] = None
        self.last_primary: Optional[str] = None
        self.last_observed_at: Optional[int] = None
        self.force_restart = False
        self.segment_reason = 'INITIAL'
        self.direction_basis = "NOT_ESTABLISHED"
        self._reset_segment()

    def _reset_segment(self):
        self.local = DC(self.p.local_reversal)
        self.struct = DC(self.p.structure_reversal)
        self.ctx = Context()
        self.stop: Optional[Stop] = None
        self.balance: Optional[Balance] = None
        self.history: list[Bar] = []
        self.clock: Optional[tuple[D, int]] = None
        self.stop_blocked_clock: Optional[int] = None
        self.direction_basis = "NOT_ESTABLISHED"

    def _make_balance(self, t: int, reason: str, events: list[str]):
        w = self.history[-self.p.balance_bars:]
        assert len(w) == self.p.balance_bars
        lo = min(w, key=lambda z: (z.c, z.t))
        hi = max(w, key=lambda z: (z.c, -z.t))
        self.balance = Balance(min(b.l for b in w), max(b.h for b in w),
                               (lo.c, lo.t), (hi.c, hi.t), t, reason, [b.t for b in w], [b.t for b in self.history[-11:-1]] if len(self.history)>=11 else [],
                               min(w,key=lambda b:b.l).t, max(w,key=lambda b:b.h).t,
                               min(b.l for b in w)-D(".5"),max(b.h for b in w)+D(".5"))
        self.stop = None
        # Confirmed independent balance retires, rather than rewrites, old context.
        events.append('CONTEXT_RETIRED_BY_OBSERVED_BALANCE')
        self.ctx = Context()
        self.struct = DC(self.p.structure_reversal)
        self.struct.seed(self.history[-1].c, t)

    def _balance_evidence(self, suppress: bool) -> Optional[str]:
        p = self.p
        if suppress or len(self.history) < p.balance_bars:
            return None
        w = self.history[-p.balance_bars:]
        xs = [b.c for b in w]
        close_span = max(xs)-min(xs)
        # With ten real bars but no 1U direction at all, a bounded close band is observed.
        subthreshold = close_span < p.local_reversal
        if not subthreshold and abs(xs[-1] - xs[0]) > p.balance_net_max:
            return None
        # An exit beyond the old observed band cannot be swallowed by re-establishment.
        prior = self.history[-(p.balance_bars+1):-1]
        if len(prior) == p.balance_bars:
            if xs[-1] - max(b.h for b in prior) >= p.break_buffer:
                return None
            if min(b.l for b in prior) - xs[-1] >= p.break_buffer:
                return None
        width = max(b.h for b in w) - min(b.l for b in w)
        if subthreshold:
            return 'OBSERVED_SUBTHRESHOLD_CLOSE_BAND'
        if close_span <= 2*p.stop_half_band:
            return 'OBSERVED_CLOSE_BALANCE_WINDOW'
        probe = DC(p.local_reversal)
        turns = 0
        for b in w:
            old = probe.direction
            probe.step(b.c, b.t)
            if old != 0 and probe.direction != old:
                turns += 1
        if (width >= p.balance_min_swing_width and turns >= p.balance_min_turns
                and 4*abs(xs[-1]-xs[0]) <= sum((abs(b-a) for a,b in zip(xs,xs[1:])),D(0))):
            return 'OBSERVED_CANCELLED_OSCILLATION'
        if self.stop is not None and self.stop.count>=p.stop_max_qualified_bars:
            return 'OBSERVED_STOP_BAND_PERSISTENCE'
        return None

    def _context_update(self, old: Context, old_pivots: list[Pivot],
                        b: Bar, events: list[str]) -> bool:
        """Tests only protected levels / structural pivots known before this bar."""
        p, x, t = self.p, b.c, b.t
        if old.direction and old.protected:
            assert old.level_updated_at is not None and old.level_updated_at < t
            broken = (x <= old.protected.x-p.break_buffer if old.direction == 1
                      else x >= old.protected.x+p.break_buffer)
            if broken:
                assert old.extreme is not None
                direction = -old.direction
                origin = old.extreme
                newpivot = Pivot('L' if direction == 1 else 'H', origin[0], origin[1], t,"STRUCTURE_BREAK")
                self.ctx = Context(direction, newpivot, (x, t), t, t)
                self.struct.rebase(origin, x, t, direction,"STRUCTURE_BREAK")
                events.append('STRUCTURE_BREAK_FROM_PREVIOUS_LEVEL')
                return True
            # Tighten only on a same-scale new extreme; newly confirmed pivots cannot enter here.
            if len(old_pivots) >= 3:
                a, mid, z = old_pivots[-3:]
                if all(v.confirmed_at < t for v in (a, mid, z)):
                    up_ok = (old.direction == 1 and [a.kind, mid.kind, z.kind] == ['L','H','L']
                             and z.x >= a.x+p.break_buffer and z.x > old.protected.x
                             and x >= mid.x+p.break_buffer)
                    dn_ok = (old.direction == -1 and [a.kind, mid.kind, z.kind] == ['H','L','H']
                             and z.x <= a.x-p.break_buffer and z.x < old.protected.x
                             and x <= mid.x-p.break_buffer)
                    if up_ok or dn_ok:
                        self.ctx.protected = z
                        self.ctx.level_updated_at = t
                        events.append('PROTECTED_LEVEL_TIGHTENED_EFFECTIVE_NEXT_BAR')
        elif self.struct.direction != 0:
            pivot = self.struct.pivots[0]
            self.ctx = Context(self.struct.direction, pivot, (x,t), t,t)
            events.append('CONTEXT_ESTABLISHED_AT_STRUCTURE_SCALE')
        if self.ctx.direction:
            ex = self.ctx.extreme
            if ex is None or self.ctx.direction*(x-ex[0]) > 0:
                self.ctx.extreme = (x,t)
        return False

    def _fast(self, direction: int) -> Optional[bool]:
        n = self.p.fast_intervals
        if direction == 0 or len(self.history) < n+1:
            return None
        xs = [b.c for b in self.history[-(n+1):]]
        return (direction*(xs[-1]-xs[0]) >= self.p.fast_displacement
                and (tv:=sum((abs(b-a) for a,b in zip(xs,xs[1:])),D(0)))>0 and 5*abs(xs[-1]-xs[0]) >= 4*tv)

    def _step(self, t: int, bar: Optional[Bar]):
        if type(t) is not int:
            raise ValueError('t must be an integer ordinal, not bool.')
        if self.last_call is not None and t <= self.last_call:
            raise ValueError('Calls must follow strictly increasing scheduled ordinals.')
        self.last_call = t
        if bar is None or (bar.valid() and (bar.known_at > t or bar.t > t)):
            self.force_restart = True
            return {'as_of':t, 'primary':self.last_primary,
                    'basis':'CARRIED_GAP' if self.last_primary else 'UNAVAILABLE',
                    'observed_at':self.last_observed_at, 'fast_flag':None,
                    'events':['NO_ADMISSIBLE_CLOSED_BAR'], 'current_semantics_observed':False}
        if not bar.valid() or bar.t != t:
            self.force_restart = True
            return {'as_of':t, 'primary':None, 'basis':'INVALID_INPUT',
                    'observed_at':None, 'fast_flag':None,
                    'events':['INVALID_OHLC_OR_CLOCK'], 'current_semantics_observed':False}
        events: list[str] = []
        restart = self.force_restart or (self.last_accepted is not None and
                   (t != self.last_accepted.t+1 or bar.auction != self.last_accepted.auction
                    or bar.source != self.last_accepted.source))
        if restart:
            self._reset_segment()
            self.segment_reason = 'REACQUIRED_AFTER_GAP_AUCTION_OR_SOURCE'
            events.append('SEGMENT_RESET_NO_GAP_RETURN')
        self.force_restart = False
        self.last_accepted = bar
        self.history.append(bar)
        oldctx = deepcopy(self.ctx)
        oldpivots = list(self.struct.pivots)
        before_level = oldctx.protected.x if oldctx.protected else None
        olddir = self.local.direction
        local_pivot = self.local.step(bar.c,t)
        if local_pivot:
            events.append('LOCAL_PIVOT_CONFIRMED_NOW')
        changed = self.local.direction != olddir
        if changed:self.direction_basis="LOCAL_DC_CONFIRMED"
        progress = False
        if self.local.direction:
            if changed or self.clock is None:
                self.clock = (bar.c,t)
                progress = True
                self.stop_blocked_clock = None
            elif self.local.direction*(bar.c-self.clock[0]) >= self.p.progress_increment:
                self.clock = (bar.c,t)
                progress = True
                self.stop_blocked_clock = None
                events.append('SIGNIFICANT_PROGRESS_CLOCK_UPDATED')
        if changed or progress:
            self.stop = None
        box_exit = False
        ctx_break = False
        if self.balance is not None:
            box = self.balance
            direction = (1 if bar.c >= box.high+self.p.break_buffer else
                         -1 if bar.c <= box.low-self.p.break_buffer else 0)
            if direction:
                origin = box.close_low if direction == 1 else box.close_high
                self.balance = None
                self.stop = None
                self.ctx = Context()
                self.struct = DC(self.p.structure_reversal)
                self.struct.seed(origin[0],origin[1])
                self.struct.step(bar.c,t)
                self.local.rebase(origin,bar.c,t,direction,"RANGE_EXIT")
                local_pivot=self.local.pivots[-1]
                if 'LOCAL_PIVOT_CONFIRMED_NOW' not in events:events.append('LOCAL_PIVOT_CONFIRMED_NOW')
                self.clock = (bar.c,t)
                self.stop_blocked_clock = None
                changed = progress = box_exit = True
                self.direction_basis="RANGE_EXIT_CONFIRMED"
                events.append('FIXED_BALANCE_BAND_CLOSE_BREAK')
                ctx_break = self._context_update(Context(), [], bar, events)
        else:
            pivot = self.struct.step(bar.c,t)
            if pivot:
                events.append('STRUCTURE_PIVOT_CONFIRMED_EFFECTIVE_NEXT_BAR')
            ctx_break = self._context_update(oldctx, oldpivots, bar, events)
        if self.stop is not None:
            stop = self.stop
            contained = bar.l >= stop.low and bar.h <= stop.high
            if contained and stop.direction == self.local.direction:
                stop.count += 1
                stop.continuation_ids.append(t)
            else:
                self.stop = None
                self.stop_blocked_clock = self.clock[1] if self.clock else None
                events.append('STOP_INVALIDATED_NO_AUTOMATIC_RANGE')
        if self.balance is None:
            evidence = self._balance_evidence(ctx_break or box_exit)
            if evidence:
                self._make_balance(t,evidence,events)
        if self.balance is not None:
            primary, activity = 'RANGE','BALANCED'
        else:
            d = self.local.direction
            if self.balance is not None:
                primary, activity = 'RANGE','BALANCED'
            else:
                if (self.stop is None and d != 0 and self.clock is not None
                        and self.stop_blocked_clock != self.clock[1]
                        and t-self.clock[1] >= self.p.stop_min_age
                        and len(self.history) >= self.p.stop_min_bars):
                    c = self.clock[0]
                    lo, hi = c-self.p.stop_half_band, c+self.p.stop_half_band
                    w = self.history[-self.p.stop_min_bars:]
                    if all(z.l >= lo and z.h <= hi for z in w):
                        self.stop = Stop(d,c,lo,hi,t,1,t,t,self.clock[1],w[0].t,[z.t for z in w],[t])
                        events.append('STOP_CONFIRMED_FIXED_BAND')
                if self.stop is not None:
                    primary = 'RISE_STOP' if self.stop.direction == 1 else 'DROP_STOP'
                    activity = 'STOPPED'
                elif d != 0:
                    flag = self._fast(d)
                    primary, activity = projection(self.ctx.direction,d,flag is True),'LIVE'
                else:
                    # Technical bootstrap, not an assertion of an observed range.
                    primary, activity = (self.last_primary or 'RANGE'),'INITIALIZING'
        flag = self._fast(self.local.direction)
        basis = ('WARMUP_CARRY_OR_ANCHOR' if activity == 'INITIALIZING'
                 else ('OBSERVED_FRESH' if self.segment_reason == 'INITIAL'
                       else 'OBSERVED_NEW_SEGMENT_ONLY'))
        observed = activity != 'INITIALIZING'
        if observed:
            self.last_observed_at = t
        self.last_primary = primary
        result = {
            'as_of':t, 'primary':primary, 'basis':basis,
            'current_semantics_observed':observed, 'observed_at':self.last_observed_at,
            'context':self.ctx.direction, 'leg_direction':self.local.direction,
            'activity':activity, 'fast_flag':flag,
            'fast_applicable_to_primary':activity == 'LIVE',
            'close_u':bar.c, 'progress_clock':self.clock,
            'protected_before':before_level,
            'protected_after_effective_next':self.ctx.protected.x if self.ctx.protected else None,
            'protected_updated_at':self.ctx.level_updated_at,
            'context_established_at':self.ctx.established_at,
            'stop':asdict(self.stop) if self.stop else None,
            'balance':asdict(self.balance) if self.balance else None,
            'local_pivot_confirmed':asdict(local_pivot) if local_pivot else None,
            'events':events,
        }
        assert primary in PATTERNS
        assert (activity == 'STOPPED') == (primary in ('RISE_STOP','DROP_STOP')) or not observed
        return result

