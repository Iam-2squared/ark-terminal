"""RC2 separate Wave state interpreter; old independent implementation migration basis. Fraction arithmetic, own parser/serializer, no reference/candidate/helper calls. Same author and prior code exposure are disclosed."""
from dataclasses import dataclass, replace
from fractions import Fraction
from .exact import parse, price, ratio
from copy import deepcopy
from typing import Optional


D = Fraction
STATES = ('RISE_STOP','RISE','SHARP_RISE','PULLBACK','RANGE','REBOUND',
          'SHARP_DROP','DROP','DROP_STOP')

@dataclass(frozen=True)
class Candle:
    t: int
    o: D
    h: D
    l: D
    c: D
    known_at: int
    auction: str = 'A'
    source: str = 'synthetic'

    def admissible_shape(self):
        return (type(self.t) is int and type(self.known_at) is int and
                all(isinstance(x,D) for x in (self.o,self.h,self.l,self.c)) and
                self.l <= self.o <= self.h and self.l <= self.c <= self.h and
                isinstance(self.source,str) and bool(self.source) and
                isinstance(self.auction,str) and bool(self.auction))

@dataclass(frozen=True)
class Turn:
    kind: str
    x: D
    extremum_t: int
    confirmed_at: int
    generation_reason: str = "DC_CONFIRMED"

class Wave:
    """Signed generic DC update, sharing no functions with the reference DC."""
    def __init__(self, threshold):
        self.threshold = threshold
        self.sign = 0
        self.bounds = None
        self.tip = None
        self.turns = []

    def observe(self, value, minute):
        here = (value, minute)
        if self.tip is None:
            self.bounds = (here, here)
            self.tip = here
            return None
        if not self.sign:
            low, high = self.bounds
            if value-low[0] >= self.threshold:
                s, origin = 1, low
            elif high[0]-value >= self.threshold:
                s, origin = -1, high
            else:
                self.bounds = (here if value<low[0] else low,
                               here if value>high[0] else high)
                return None
            self.sign, self.tip = s, here
            turn = Turn('L' if s==1 else 'H', *origin, minute)
        else:
            delta = self.sign*(value-self.tip[0])
            if delta > 0:
                self.tip = here
                return None
            if delta > -self.threshold:
                return None
            turn = Turn('H' if self.sign==1 else 'L', *self.tip, minute)
            self.sign, self.tip = -self.sign, here
        self.turns.append(turn)
        return turn

    @classmethod
    def from_origin(cls, threshold, origin, current, minute, sign, reason="DC_CONFIRMED"):
        w = cls(threshold)
        w.sign = sign
        w.tip = (current,minute)
        w.bounds = (min(origin,(current,minute)), max(origin,(current,minute)))
        w.turns = [Turn('L' if sign==1 else 'H',*origin,minute,reason)]
        return w

def serial(value):
    if isinstance(value,D): return str(value)
    if isinstance(value,Turn): return serial(vars(value))
    if isinstance(value,dict): return {k:serial(v) for k,v in value.items()}
    if isinstance(value,(tuple,list)): return [serial(v) for v in value]
    return value

class IndependentState9:
    def __init__(self, profile):
        integer_keys = {'stop_min_age','stop_min_bars','stop_max_qualified_bars',
                        'balance_bars','balance_min_turns','fast_intervals'}
        self.p = {k:(int(v) if k in integer_keys else D(v)) for k,v in profile.items()}
        self.called = self.accepted = self.previous_primary = self.observed_minute = None
        self.restart_required = False
        self.reacquired = False
        self.direction_basis = "NOT_ESTABLISHED"
        self.reset()

    def reset(self):
        self.leg = Wave(self.p['local_reversal'])
        self.structure = Wave(self.p['structure_reversal'])
        self.context = 0
        self.level = self.context_extreme = None
        self.context_time = self.level_time = None
        self.candles = []
        self.anchor = None
        self.stopped = self.box = None
        self.blocked_anchor_time = None
        self.direction_basis = "NOT_ESTABLISHED"

    def _establish(self, minute, close):
        if self.structure.sign:
            self.context = self.structure.sign
            self.level = self.structure.turns[0]
            self.context_time = self.level_time = minute
            self.context_extreme = (close,minute)

    def _context_transaction(self, candle, old_turns, events):
        x,t,p = candle.c,candle.t,self.p
        if not self.context:
            before = self.structure.sign
            self._establish(t,x)
            if before: events.append('CONTEXT_ESTABLISHED_AT_STRUCTURE_SCALE')
            return False
        old_sign = self.context
        # Signed displacement avoids adding a small buffer to a large coordinate.
        if old_sign*(x-self.level.x) <= -p['break_buffer']:
            origin = self.context_extreme
            self.context = -old_sign
            self.level = Turn('L' if self.context==1 else 'H',*origin,t,"STRUCTURE_BREAK")
            self.context_time = self.level_time = t
            self.context_extreme = (x,t)
            self.structure = Wave.from_origin(p['structure_reversal'],origin,x,t,self.context,"STRUCTURE_BREAK")
            events.append('STRUCTURE_BREAK_FROM_PREVIOUS_LEVEL')
            return True
        if len(old_turns)>=3:
            first,middle,last = old_turns[-3:]
            pattern = ['L','H','L'] if old_sign==1 else ['H','L','H']
            if ([v.kind for v in (first,middle,last)]==pattern and
                all(v.confirmed_at<t for v in (first,middle,last)) and
                old_sign*(last.x-first.x)>=p['break_buffer'] and
                old_sign*(last.x-self.level.x)>0 and
                old_sign*(x-middle.x)>=p['break_buffer']):
                self.level,self.level_time = last,t
                events.append('PROTECTED_LEVEL_TIGHTENED_EFFECTIVE_NEXT_BAR')
        if old_sign*(x-self.context_extreme[0])>0:
            self.context_extreme = (x,t)
        return False

    def _range_candidate(self, prior_ten, suppressed):
        p = self.p
        if suppressed or len(self.candles)<p['balance_bars']: return None
        current = self.candles[-p['balance_bars']:]
        xs = [b.c for b in current]
        if len(prior_ten)==p['balance_bars']:
            if (xs[-1]-max(b.h for b in prior_ten)>=p['break_buffer'] or
                min(b.l for b in prior_ten)-xs[-1]>=p['break_buffer']):
                return None
        span,net = max(xs)-min(xs),abs(xs[-1]-xs[0])
        if span<p['local_reversal']: return 'OBSERVED_SUBTHRESHOLD_CLOSE_BAND'
        if net>p['balance_net_max']: return None
        if span<=p['local_reversal']: return 'OBSERVED_CLOSE_BALANCE_WINDOW'
        probe = Wave(p['local_reversal'])
        reversals = 0
        for b in current:
            previous = probe.sign
            probe.observe(b.c,b.t)
            reversals += int(previous!=0 and probe.sign!=previous)
        if (max(b.h for b in current)-min(b.l for b in current)>=p['balance_min_swing_width']
            and reversals>=p['balance_min_turns'] and 4*abs(xs[-1]-xs[0])<=sum((abs(y-x) for x,y in zip(xs,xs[1:])),D(0))):
            return 'OBSERVED_CANCELLED_OSCILLATION'
        if self.stopped is not None and self.stopped['count']>=p['stop_max_qualified_bars']:
            return 'OBSERVED_STOP_BAND_PERSISTENCE'
        return None

    def _fix_box(self, minute, reason, events):
        w = self.candles[-self.p['balance_bars']:]
        self.box = {'low':min(b.l for b in w),'high':max(b.h for b in w),
                    'close_low':min(((b.c,b.t) for b in w),key=lambda x:(x[0],x[1])),
                    'close_high':max(((b.c,b.t) for b in w),key=lambda x:(x[0],-x[1])),
                    'established_at':minute,'reason':reason, 'window_ids':[v.t for v in w],
                    'old_window_ids':[v.t for v in self.candles[-11:-1]] if len(self.candles)>=11 else [],
                    'low_at':min(w,key=lambda v:v.l).t,'high_at':max(w,key=lambda v:v.h).t,
                    'exit_low':min(v.l for v in w)-D('0.5'),'exit_high':max(v.h for v in w)+D('0.5')}
        self.stopped = None
        self.context = 0
        self.level = self.context_extreme = self.context_time = self.level_time = None
        self.structure = Wave(self.p['structure_reversal'])
        self.structure.observe(w[-1].c,minute)
        events.append('CONTEXT_RETIRED_BY_OBSERVED_BALANCE')

    def _fast(self):
        n = self.p['fast_intervals']+1
        if not self.leg.sign or len(self.candles)<n: return None
        xs = [b.c for b in self.candles[-n:]]
        return (self.leg.sign*(xs[-1]-xs[0])>=self.p['fast_displacement']
                and (tv:=sum((abs(y-x) for x,y in zip(xs,xs[1:])),D(0)))>0 and 5*abs(xs[-1]-xs[0])>=4*tv)

    def _step(self, minute, candle):
        if type(minute) is not int: raise ValueError('Expected integer scheduled minute')
        if self.called is not None and minute<=self.called: raise ValueError('Non-increasing calls')
        self.called = minute
        shape_ok = candle is not None and candle.admissible_shape()
        if candle is None or (shape_ok and (candle.known_at>minute or candle.t>minute)):
            self.restart_required = True
            return {'as_of':minute,'primary':self.previous_primary,
                    'basis':'CARRIED_GAP' if self.previous_primary else 'UNAVAILABLE',
                    'observed_at':self.observed_minute,'fast_flag':None,
                    'events':['NO_ADMISSIBLE_CLOSED_BAR'],'current_semantics_observed':False}
        if not shape_ok or candle.t!=minute:
            self.restart_required = True
            return {'as_of':minute,'primary':None,'basis':'INVALID_INPUT','observed_at':None,
                    'fast_flag':None,'events':['INVALID_OHLC_OR_CLOCK'],'current_semantics_observed':False}
        events = []
        if self.restart_required or (self.accepted and
            (minute!=self.accepted.t+1 or candle.source!=self.accepted.source or
             candle.auction!=self.accepted.auction)):
            self.reset()
            self.reacquired = True
            events.append('SEGMENT_RESET_NO_GAP_RETURN')
        self.restart_required = False
        self.accepted = candle
        prior_ten = self.candles[-self.p['balance_bars']:]
        old_turns = tuple(self.structure.turns)
        before_level = self.level.x if self.level else None
        self.candles.append(candle)
        before_leg = self.leg.sign
        local_turn = self.leg.observe(candle.c,minute)
        if local_turn: events.append('LOCAL_PIVOT_CONFIRMED_NOW')
        reversal = self.leg.sign!=before_leg
        if reversal:self.direction_basis="LOCAL_DC_CONFIRMED"
        advancing = False
        if self.leg.sign:
            if reversal or self.anchor is None:
                self.anchor = (candle.c,minute)
                advancing = True
            elif self.leg.sign*(candle.c-self.anchor[0])>=self.p['progress_increment']:
                self.anchor = (candle.c,minute)
                advancing = True
                events.append('SIGNIFICANT_PROGRESS_CLOCK_UPDATED')
        if advancing:
            self.blocked_anchor_time = None
        if reversal or advancing:
            self.stopped = None
        break_now = exit_now = False
        if self.box:
            s = (1 if candle.c-self.box['high']>=self.p['break_buffer'] else
                 -1 if self.box['low']-candle.c>=self.p['break_buffer'] else 0)
            if s:
                origin = self.box['close_low' if s==1 else 'close_high']
                self.box = self.stopped = None
                self.context = 0
                self.level = self.context_extreme = self.context_time = self.level_time = None
                self.structure = Wave(self.p['structure_reversal'])
                self.structure.observe(*origin)
                self.structure.observe(candle.c,minute)
                self.leg = Wave.from_origin(self.p['local_reversal'],origin,candle.c,minute,s,"RANGE_EXIT")
                local_turn=self.leg.turns[-1]
                if 'LOCAL_PIVOT_CONFIRMED_NOW' not in events:events.append('LOCAL_PIVOT_CONFIRMED_NOW')
                self.anchor = (candle.c,minute)
                self.blocked_anchor_time = None
                exit_now = True
                self.direction_basis="RANGE_EXIT_CONFIRMED"
                events.append('FIXED_BALANCE_BAND_CLOSE_BREAK')
                self._context_transaction(candle,(),events)
        else:
            turn = self.structure.observe(candle.c,minute)
            if turn: events.append('STRUCTURE_PIVOT_CONFIRMED_EFFECTIVE_NEXT_BAR')
            break_now = self._context_transaction(candle,old_turns,events)
        if self.stopped:
            st = self.stopped
            if candle.l>=st['low'] and candle.h<=st['high'] and st['direction']==self.leg.sign:
                st['count'] += 1
                st['continuation_ids'].append(minute)
            else:
                self.stopped = None
                self.blocked_anchor_time = self.anchor[1] if self.anchor else None
                events.append('STOP_INVALIDATED_NO_AUTOMATIC_RANGE')
        if not self.box:
            evidence = self._range_candidate(prior_ten,break_now or exit_now)
            if evidence: self._fix_box(minute,evidence,events)
        if not self.box:
            if (not self.box and not self.stopped and self.leg.sign and self.anchor and
                self.blocked_anchor_time!=self.anchor[1] and
                minute-self.anchor[1]>=self.p['stop_min_age'] and
                len(self.candles)>=self.p['stop_min_bars']):
                center = self.anchor[0]
                lo,hi = center-self.p['stop_half_band'],center+self.p['stop_half_band']
                if all(b.l>=lo and b.h<=hi for b in self.candles[-self.p['stop_min_bars']:]):
                    self.stopped = {'direction':self.leg.sign,'center':center,'low':lo,'high':hi,
                                    'start':minute,'count':1,'recognized_at':minute,'count_start':minute,
                                    'progress_at':self.anchor[1],'evidence_window_start':self.candles[-3].t,
                                    'evidence_ids':[v.t for v in self.candles[-3:]],'continuation_ids':[minute]}
                    events.append('STOP_CONFIRMED_FIXED_BAND')
        if self.box:
            primary,activity = 'RANGE','BALANCED'
        elif self.stopped:
            primary,activity = ('RISE_STOP' if self.stopped['direction']==1 else 'DROP_STOP'),'STOPPED'
        elif self.leg.sign:
            activity = 'LIVE'
            if self.leg.sign==1 and self.context==-1: primary = 'REBOUND'
            elif self.leg.sign==-1 and self.context==1: primary = 'PULLBACK'
            elif self.leg.sign==1: primary = 'SHARP_RISE' if self._fast() is True else 'RISE'
            else: primary = 'SHARP_DROP' if self._fast() is True else 'DROP'
        else:
            primary,activity = self.previous_primary or 'RANGE','INITIALIZING'
        observed = activity!='INITIALIZING'
        if observed: self.observed_minute = minute
        self.previous_primary = primary
        basis = ('WARMUP_CARRY_OR_ANCHOR' if not observed else
                 'OBSERVED_NEW_SEGMENT_ONLY' if self.reacquired else 'OBSERVED_FRESH')
        return {'as_of':minute,'primary':primary,'basis':basis,
            'current_semantics_observed':observed,'observed_at':self.observed_minute,
            'context':self.context,'leg_direction':self.leg.sign,'activity':activity,
            'fast_flag':self._fast(),'fast_applicable_to_primary':activity=='LIVE',
            'close_u':candle.c,'progress_clock':self.anchor,'protected_before':before_level,
            'protected_after_effective_next':self.level.x if self.level else None,
            'protected_updated_at':self.level_time,'context_established_at':self.context_time,
            'stop':self.stopped,'balance':self.box,'local_pivot_confirmed':local_turn,'events':events}
