from copy import deepcopy
from dataclasses import is_dataclass
from fractions import Fraction
from .kernel import IndependentState9,Candle,Wave
from .exact import parse,price,ratio
NAMES=('as_of','case_id','primary','basis','current_semantics_observed','observed_at','context','leg_direction','activity','fast_flag','fast_applicable_to_primary','close_u','progress_clock','protected_before','protected_after_effective_next','protected_updated_at','protected_effective_from','protected_origin','context_established_at','stop','balance','local_pivot_confirmed','events','_structure_direction','_structure_pivots','_context_extreme','_local_tip','_blocked_anchor_time','direction_basis','bar_metadata','range_analysis','fast_analysis','numeric_status','rejection_reason','schema_version')
class EngineFault(RuntimeError):pass
def pack(x):
    if isinstance(x,Fraction):return price(x)
    if is_dataclass(x):return pack(vars(x))
    if type(x) is dict:return {k:pack(v) for k,v in x.items()}
    if isinstance(x,(tuple,list)):return [pack(v) for v in x]
    return x
class Engine(IndependentState9):
    def market(self):return deepcopy({k:v for k,v in vars(self).items() if k not in ('called','restart_required')})
    def unavailable(self,t,r,cid,status,why):
        self.called=t;self.restart_required=True
        data={k:None for k in NAMES};carry=status=='NOT_AVAILABLE'
        data.update(as_of=t,case_id=cid,primary=self.previous_primary if carry else None,basis=('CARRIED_GAP' if self.previous_primary else 'UNAVAILABLE') if carry else 'INVALID_INPUT',current_semantics_observed=False,observed_at=self.observed_minute if carry else None,fast_applicable_to_primary=False,events=[why],bar_metadata=None if r is None else {k:r.get(k) for k in ['t','known_at','source','auction']},numeric_status=status,rejection_reason=why,schema_version='RC2_EXACT_V1')
        return data
    def step(self,t,raw,case_id='',fault=None):
        if type(t)!=int or (self.called is not None and t<=self.called):raise ValueError('PROTOCOL_CLOCK')
        if raw is None:return self.unavailable(t,raw,case_id,'NOT_AVAILABLE','NO_ADMISSIBLE_CLOSED_BAR')
        try:
            candle=Candle(t=raw['t'],o=parse(raw['o']),h=parse(raw['h']),l=parse(raw['l']),c=parse(raw['c']),known_at=raw['known_at'],source=raw['source'],auction=raw['auction'])
        except (ValueError,TypeError,KeyError):return self.unavailable(t,raw,case_id,'REJECTED','NUMERIC_INPUT_REJECTED')
        except Exception as e:
            self.called=t;self.restart_required=True;raise EngineFault('NUMERIC_ENGINE_FAULT: admission '+str(e)) from e
        if not candle.admissible_shape() or candle.t!=t:return self.unavailable(t,raw,case_id,'REJECTED','INVALID_OHLC_OR_CLOCK')
        if candle.known_at>t:return self.unavailable(t,raw,case_id,'NOT_AVAILABLE','NO_ADMISSIBLE_CLOSED_BAR')
        try:
            next_state=deepcopy(self)
            data=next_state._step(t,candle)
            if fault=='engine_post_update':raise ArithmeticError('INJECTED_POST_UPDATE')
            data.update(case_id=case_id,protected_effective_from=next_state.level_time+1 if next_state.level_time is not None else None,protected_origin=next_state.level,_structure_direction=next_state.structure.sign,_structure_pivots=next_state.structure.turns,_context_extreme=next_state.context_extreme,_local_tip=next_state.leg.tip,_blocked_anchor_time=next_state.blocked_anchor_time,direction_basis=next_state.direction_basis,bar_metadata={k:raw[k] for k in ['t','known_at','source','auction']},numeric_status='ACCEPTED',rejection_reason=None,schema_version='RC2_EXACT_V1')
            data['range_analysis']=next_state.measure_range(data['events']);data['fast_analysis']=next_state.measure_fast()
            if fault=='engine_serializer':raise ArithmeticError('INJECTED_SERIALIZER')
            result=pack(data)
            if set(result)!=set(NAMES):raise AssertionError('SCHEMA')
        except Exception as e:
            self.called=t;self.restart_required=True;raise EngineFault('NUMERIC_ENGINE_FAULT: '+str(e)) from e
        self.__dict__=next_state.__dict__;return result
    def measure_range(self,events):
        if len(self.candles)<10:return None
        window=self.candles[-10:];previous=self.candles[-11:-1] if len(self.candles)>10 else [];values=[b.c for b in window];net=values[-1]-values[0];travel=sum((abs(values[i]-values[i-1]) for i in range(1,10)),Fraction(0));span=max(values)-min(values);width=max(b.h for b in window)-min(b.l for b in window)
        w=Wave(Fraction(1));reversals=0
        for b in window:
            sign=w.sign;w.observe(b.c,b.t)
            if sign and w.sign!=sign:reversals+=1
        low=min([b.l for b in previous]) if previous else None;high=max([b.h for b in previous]) if previous else None
        g=any(e in events for e in ['STRUCTURE_BREAK_FROM_PREVIOUS_LEVEL','FIXED_BALANCE_BAND_CLOSE_BREAK'])
        if previous:g=g or values[-1]-high>=Fraction(1,2) or low-values[-1]>=Fraction(1,2)
        conditions={'A':span<1,'B':span<=1 and abs(net)<=Fraction(1,2),'C':abs(net)<=Fraction(1,2) and width>=2 and reversals>=3 and 4*abs(net)<=travel,'D':self.stopped is not None and self.stopped['count']>=10}
        return {'window_ids':[b.t for b in window],'old_window_ids':[b.t for b in previous],'net':net,'tv':travel,'span':span,'width':width,'eta':ratio(net,travel),'turns':reversals,'old_low':low,'old_high':high,'guard':bool(g),'conditions':conditions}
    def measure_fast(self):
        if len(self.candles)<6:return None
        group=self.candles[-6:];values=[b.c for b in group];change=values[-1]-values[0];path=sum((abs(values[j]-values[j-1]) for j in range(1,6)),Fraction(0))
        return {'window_ids':[b.t for b in group],'net':change,'tv':path,'directional_net':self.leg.sign*change,'eta':ratio(change,path)}
