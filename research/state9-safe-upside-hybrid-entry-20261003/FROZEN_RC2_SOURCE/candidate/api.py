from copy import deepcopy
from dataclasses import asdict,is_dataclass
from .kernel import State9,Bar,DC,Profile
from .exact import N,parse
FIELDS='as_of case_id primary basis current_semantics_observed observed_at context leg_direction activity fast_flag fast_applicable_to_primary close_u progress_clock protected_before protected_after_effective_next protected_updated_at protected_effective_from protected_origin context_established_at stop balance local_pivot_confirmed events _structure_direction _structure_pivots _context_extreme _local_tip _blocked_anchor_time direction_basis bar_metadata range_analysis fast_analysis numeric_status rejection_reason schema_version'.split()
class EngineFault(RuntimeError):pass
def encode(x):
    if isinstance(x,N):return str(x)
    if is_dataclass(x):return encode(asdict(x))
    if isinstance(x,dict):return {k:encode(v) for k,v in x.items()}
    if isinstance(x,(list,tuple)):return [encode(v) for v in x]
    return x
class Engine(State9):
    def __init__(self,profile):
        ik={'stop_min_age','stop_min_bars','stop_max_qualified_bars','balance_bars','balance_min_turns','fast_intervals'}
        super().__init__(Profile(**{k:int(v) if k in ik else parse(v) for k,v in profile.items()}))
    def market(self):return deepcopy({k:v for k,v in self.__dict__.items() if k not in ('last_call','force_restart')})
    def negative(self,t,raw,cid,status,reason):
        self.last_call=t;self.force_restart=True
        o=dict.fromkeys(FIELDS);o.update(as_of=t,case_id=cid,primary=self.last_primary if status=='NOT_AVAILABLE' else None,basis=('CARRIED_GAP' if self.last_primary else 'UNAVAILABLE') if status=='NOT_AVAILABLE' else 'INVALID_INPUT',current_semantics_observed=False,observed_at=self.last_observed_at if status=='NOT_AVAILABLE' else None,fast_applicable_to_primary=False,events=[reason],bar_metadata=None if raw is None else {k:raw.get(k) for k in ('t','known_at','source','auction')},numeric_status=status,rejection_reason=reason,schema_version='RC2_EXACT_V1')
        return o
    def step(self,t,raw,case_id='',fault=None):
        if type(t) is not int or (self.last_call is not None and t<=self.last_call):raise ValueError('PROTOCOL_CLOCK')
        if raw is None:return self.negative(t,raw,case_id,'NOT_AVAILABLE','NO_ADMISSIBLE_CLOSED_BAR')
        try:bar=Bar(**{k:parse(raw[k]) if k in 'ohlc' and len(k)==1 else raw[k] for k in ('t','o','h','l','c','known_at','source','auction')})
        except (ValueError,KeyError,TypeError):return self.negative(t,raw,case_id,'REJECTED','NUMERIC_INPUT_REJECTED')
        except Exception as e:
            self.last_call=t;self.force_restart=True;raise EngineFault('NUMERIC_ENGINE_FAULT: admission '+str(e)) from e
        if not bar.valid() or bar.t!=t:return self.negative(t,raw,case_id,'REJECTED','INVALID_OHLC_OR_CLOCK')
        if bar.known_at>t:return self.negative(t,raw,case_id,'NOT_AVAILABLE','NO_ADMISSIBLE_CLOSED_BAR')
        try:
            work=deepcopy(self)
            o=work._step(t,bar)
            if fault=='engine_post_update':raise ArithmeticError('INJECTED_POST_UPDATE')
            o.update(case_id=case_id,protected_effective_from=work.ctx.level_updated_at+1 if work.ctx.level_updated_at is not None else None,protected_origin=work.ctx.protected,_structure_direction=work.struct.direction,_structure_pivots=work.struct.pivots,_context_extreme=work.ctx.extreme,_local_tip=work.local.extreme,_blocked_anchor_time=work.stop_blocked_clock,direction_basis=work.direction_basis,bar_metadata={k:raw[k] for k in ('t','known_at','source','auction')},numeric_status='ACCEPTED',rejection_reason=None,schema_version='RC2_EXACT_V1')
            o['range_analysis']=work.range_metrics(t,o['events']);o['fast_analysis']=work.fast_metrics()
            if fault=='engine_serializer':raise ArithmeticError('INJECTED_SERIALIZER')
            o=encode(o)
            if set(o)!=set(FIELDS):raise AssertionError('SCHEMA')
        except Exception as e:
            self.last_call=t;self.force_restart=True;raise EngineFault('NUMERIC_ENGINE_FAULT: '+str(e)) from e
        self.__dict__=work.__dict__;return o
    def range_metrics(self,t,events):
        if len(self.history)<10:return None
        w=self.history[-10:];old=self.history[-11:-1] if len(self.history)>=11 else [];xs=[v.c for v in w];net=xs[-1]-xs[0];tv=sum((abs(y-x) for x,y in zip(xs,xs[1:])),N(0));span=max(xs)-min(xs);width=max(v.h for v in w)-min(v.l for v in w)
        probe=DC(N(1));turns=0
        for v in w:
            d=probe.direction;probe.step(v.c,v.t);turns+=int(d!=0 and d!=probe.direction)
        lo=min((v.l for v in old),default=None);hi=max((v.h for v in old),default=None)
        guard=('STRUCTURE_BREAK_FROM_PREVIOUS_LEVEL' in events or 'FIXED_BALANCE_BAND_CLOSE_BREAK' in events or (bool(old) and (xs[-1]>=hi+N('.5') or xs[-1]<=lo-N('.5'))))
        return dict(window_ids=[v.t for v in w],old_window_ids=[v.t for v in old],net=net,tv=tv,span=span,width=width,eta=abs(net).ratio(tv),turns=turns,old_low=lo,old_high=hi,guard=bool(guard),conditions=dict(A=span<N(1),B=span<=N(1) and abs(net)<=N('.5'),C=abs(net)<=N('.5') and width>=N(2) and turns>=3 and 4*abs(net)<=tv,D=self.stop is not None and self.stop.count>=10))
    def fast_metrics(self):
        if len(self.history)<6:return None
        w=self.history[-6:];xs=[v.c for v in w];net=xs[-1]-xs[0];tv=sum((abs(y-x) for x,y in zip(xs,xs[1:])),N(0))
        return dict(window_ids=[v.t for v in w],net=net,tv=tv,directional_net=self.local.direction*net,eta=abs(net).ratio(tv))
