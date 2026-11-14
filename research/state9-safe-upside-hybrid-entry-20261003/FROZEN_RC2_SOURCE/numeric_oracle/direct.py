"""Raw-prefix direct oracle: independent schema/parse/formulas and partial state tracking.
Not a complete third context classifier. No engine/helper imports.
"""
import re
from fractions import Fraction as F
from math import gcd
TOP=set('as_of case_id primary basis current_semantics_observed observed_at context leg_direction activity fast_flag fast_applicable_to_primary close_u progress_clock protected_before protected_after_effective_next protected_updated_at protected_effective_from protected_origin context_established_at stop balance local_pivot_confirmed events _structure_direction _structure_pivots _context_extreme _local_tip _blocked_anchor_time direction_basis bar_metadata range_analysis fast_analysis numeric_status rejection_reason schema_version'.split())
PIV=set('kind x extremum_t confirmed_at generation_reason'.split())
STOP=set('direction center low high start count recognized_at count_start progress_at evidence_window_start evidence_ids continuation_ids'.split())
BOX=set('low high close_low close_high established_at reason window_ids old_window_ids low_at high_at exit_low exit_high'.split())
RANGE=set('window_ids old_window_ids net tv span width eta turns old_low old_high guard conditions'.split())
FAST=set('window_ids net tv directional_net eta'.split())
STATES={'RISE_STOP','RISE','SHARP_RISE','PULLBACK','RANGE','REBOUND','SHARP_DROP','DROP','DROP_STOP'}
EVENTS={'LOCAL_PIVOT_CONFIRMED_NOW','SIGNIFICANT_PROGRESS_CLOCK_UPDATED','FIXED_BALANCE_BAND_CLOSE_BREAK','CONTEXT_ESTABLISHED_AT_STRUCTURE_SCALE','STRUCTURE_PIVOT_CONFIRMED_EFFECTIVE_NEXT_BAR','STRUCTURE_BREAK_FROM_PREVIOUS_LEVEL','PROTECTED_LEVEL_TIGHTENED_EFFECTIVE_NEXT_BAR','STOP_INVALIDATED_NO_AUTOMATIC_RANGE','STOP_CONFIRMED_FIXED_BAND','CONTEXT_RETIRED_BY_OBSERVED_BALANCE','SEGMENT_RESET_NO_GAP_RETURN','NO_ADMISSIBLE_CLOSED_BAR','NUMERIC_INPUT_REJECTED','INVALID_OHLC_OR_CLOCK'}
GRAM=re.compile(r'([+-]?)([0-9]*)(?:\.([0-9]*))?(?:[eE]([+-]?[0-9]+))?',re.ASCII)
def value(s,domain=False):
    if type(s) is not str:raise ValueError('STRING_REQUIRED')
    if not s.isascii() or (domain and len(s)>2048):raise ValueError('LEX')
    m=GRAM.fullmatch(s)
    if not m or not (m[2] or m[3]):raise ValueError('LEX')
    digits=m[2]+(m[3] or '');c=int(digits);e=int(m[4] or '0')-len(m[3] or '')
    if not c:return F(0)
    while c%10==0:c//=10;e+=1
    if domain and (len(str(c))>256 or abs(e)>512):raise ValueError('DOMAIN')
    if m[1]=='-':c=-c
    return F(c*10**e) if e>=0 else F(c,10**-e)
def canonical(f):
    if f==0:return '0'
    n,d=f.numerator,f.denominator;k=0
    # general finite decimal construction independent from engine factorization
    while d!=1:
        g=gcd(d,10)
        if g==1:raise ValueError('NONFINITE_DECIMAL')
        n*=10//g;d//=g;k+=1
    e=-k
    while n%10==0:n//=10;e+=1
    return str(n)+(('e'+str(e)) if e else '')
def qratio(n,tv):
    f=abs(n)/tv if tv else F(0);return {'num':str(f.numerator),'den':str(f.denominator)}
def turns(xs):
    direction=0;low=high=tip=xs[0];count=0
    for x in xs[1:]:
        if direction==0:
            if x-low>=1:direction=1;tip=x
            elif high-x>=1:direction=-1;tip=x
            else:low=min(low,x);high=max(high,x)
        elif direction==1:
            if x>tip:tip=x
            elif tip-x>=1:direction=-1;tip=x;count+=1
        else:
            if x<tip:tip=x
            elif x-tip>=1:direction=1;tip=x;count+=1
    return count
class Direct:
    def __init__(self,cid):
        self.cid=cid;self.raw={};self.history=[];self.prev=None;self.restart=False;self.newseg=False
        self.direction=0;self.low=self.high=self.tip=self.clock=None;self.blocked=None;self.box=None;self.stop=None;self.last_observed=None;self.last_primary=None;self.direction_basis='NOT_ESTABLISHED';self.context_extreme=None
    def check(self,t,r,o):
        errors=[]
        def ck(ok,name):
            if not ok:errors.append(name)
        def eq(a,b,name):ck(a==b,name)
        def pv(x,expected,name):
            try:eq(value(x),expected,name);eq(x,canonical(expected),name+'.canonical')
            except Exception:eq(False,True,name+'.encoding')
        def point(pt,name):
            if pt is None:return
            ck(type(pt) is list and len(pt)==2,name+'.shape')
            if type(pt) is list and len(pt)==2:
                when=pt[1];ck(type(when) is int and when in self.raw,name+'.real_time')
                if when in self.raw:pv(pt[0],self.raw[when]['c'],name+'.raw_close')
        def pivot(p,name):
            if p is None:return
            eq(set(p),PIV,name+'.schema');point([p.get('x'),p.get('extremum_t')],name)
            ck(p.get('kind') in ('H','L'),name+'.kind');ck(type(p.get('confirmed_at')) is int and p['extremum_t']<=p['confirmed_at']<=t,name+'.causal')
            ck(p.get('generation_reason') in ('DC_CONFIRMED','STRUCTURE_BREAK','RANGE_EXIT'),name+'.reason')
        eq(set(o),TOP,'schema.top');eq(o.get('as_of'),t,'as_of');eq(o.get('case_id'),self.cid,'case_id');eq(o.get('schema_version'),'RC2_EXACT_V1','version')
        eq(o.get('bar_metadata'),None if r is None else {k:r.get(k) for k in ('t','known_at','source','auction')},'metadata')
        valid=False;why='NO_ADMISSIBLE_CLOSED_BAR';status='NOT_AVAILABLE'
        if r is not None:
            try:
                b={k:value(r[k],True) for k in ('o','h','l','c')};b.update({k:r[k] for k in ('t','known_at','source','auction')})
                if not (type(b['t']) is int and type(b['known_at']) is int and b['t']==t and b['l']<=b['o']<=b['h'] and b['l']<=b['c']<=b['h'] and type(b['source']) is str and b['source'] and type(b['auction']) is str and b['auction']):status='REJECTED';why='INVALID_OHLC_OR_CLOCK'
                elif b['known_at']>t:pass
                else:valid=True;status='ACCEPTED';why=None
            except Exception:status='REJECTED';why='NUMERIC_INPUT_REJECTED'
        eq(o.get('numeric_status'),status,'admission');eq(o.get('rejection_reason'),why,'rejection_reason')
        if not valid:
            self.restart=True
            expected=dict.fromkeys(TOP);expected.update(as_of=t,case_id=self.cid,primary=self.last_primary if status=='NOT_AVAILABLE' else None,basis=('CARRIED_GAP' if self.last_primary else 'UNAVAILABLE') if status=='NOT_AVAILABLE' else 'INVALID_INPUT',current_semantics_observed=False,observed_at=self.last_observed if status=='NOT_AVAILABLE' else None,fast_applicable_to_primary=False,events=[why],bar_metadata=o.get('bar_metadata'),numeric_status=status,rejection_reason=why,schema_version='RC2_EXACT_V1')
            eq(o,expected,'negative.full_schema');return errors
        reset=bool(self.restart or (self.history and (t!=self.history[-1]['t']+1 or b['source']!=self.history[-1]['source'] or b['auction']!=self.history[-1]['auction'])))
        if reset:
            self.history=[];self.direction=0;self.low=self.high=self.tip=self.clock=None;self.blocked=None;self.box=self.stop=None;self.direction_basis='NOT_ESTABLISHED';self.newseg=True;self.context_extreme=None
        self.restart=False;self.raw[t]=b;self.history.append(b);x=b['c'];here=(x,t);old_direction=self.direction;progress=False
        if self.tip is None:self.low=self.high=self.tip=here
        elif not self.direction:
            if x-self.low[0]>=1:self.direction=1;self.tip=here
            elif self.high[0]-x>=1:self.direction=-1;self.tip=here
            else:
                if x<self.low[0]:self.low=here
                if x>self.high[0]:self.high=here
        elif self.direction==1:
            if x>self.tip[0]:self.tip=here
            elif self.tip[0]-x>=1:self.direction=-1;self.tip=here
        else:
            if x<self.tip[0]:self.tip=here
            elif x-self.tip[0]>=1:self.direction=1;self.tip=here
        if self.direction!=old_direction:self.direction_basis='LOCAL_DC_CONFIRMED'
        if self.direction:
            if self.direction!=old_direction or self.clock is None or self.direction*(x-self.clock[0])>=F(1,2):self.clock=here;progress=True;self.blocked=None
        if progress or self.direction!=old_direction:self.stop=None
        exited=False;exit_origin=None
        if self.box:
            s=1 if x>=self.box['high']+F(1,2) else -1 if x<=self.box['low']-F(1,2) else 0
            if s:
                exit_origin=self.box['close_low' if s==1 else 'close_high']
                self.direction=s;self.tip=self.clock=here;self.blocked=None;self.box=self.stop=None;self.direction_basis='RANGE_EXIT_CONFIRMED';exited=True
        if self.stop:
            if b['l']>=self.stop['low'] and b['h']<=self.stop['high'] and self.stop['direction']==self.direction:
                self.stop['count']+=1;self.stop['continuation_ids'].append(t)
            else:self.stop=None;self.blocked=self.clock[1] if self.clock else None
        eq(o.get('leg_direction'),self.direction,'local.direction');eq(o.get('direction_basis'),self.direction_basis,'direction_basis');eq(o.get('progress_clock'),None if self.clock is None else [canonical(self.clock[0]),self.clock[1]],'clock');eq(o.get('_local_tip'),[canonical(self.tip[0]),self.tip[1]],'local.tip');eq(o.get('_blocked_anchor_time'),self.blocked,'blocked_clock');pv(o.get('close_u'),x,'close.raw')
        rm=None
        if len(self.history)>=10:
            w=self.history[-10:];old=self.history[-11:-1] if len(self.history)>10 else [];xs=[z['c'] for z in w];net=xs[-1]-xs[0];tv=sum(abs(y-x) for x,y in zip(xs,xs[1:]));span=max(xs)-min(xs);width=max(z['h'] for z in w)-min(z['l'] for z in w);nturn=turns(xs)
            guard=exited or ('STRUCTURE_BREAK_FROM_PREVIOUS_LEVEL' in o.get('events',[])) or (bool(old) and (x>=max(z['h'] for z in old)+F(1,2) or x<=min(z['l'] for z in old)-F(1,2)))
            cond={'A':span<1,'B':span<=1 and abs(net)<=F(1,2),'C':abs(net)<=F(1,2) and width>=2 and nturn>=3 and 4*abs(net)<=tv,'D':self.stop is not None and self.stop['count']>=10}
            reason=next((text for key,text in zip('ABCD',['OBSERVED_SUBTHRESHOLD_CLOSE_BAND','OBSERVED_CLOSE_BALANCE_WINDOW','OBSERVED_CANCELLED_OSCILLATION','OBSERVED_STOP_BAND_PERSISTENCE']) if cond[key]),None)
            if not self.box and not guard and reason:
                low=min(w,key=lambda z:(z['c'],z['t']));high=max(w,key=lambda z:(z['c'],-z['t']));lo=min(z['l'] for z in w);hi=max(z['h'] for z in w)
                self.box={'low':lo,'high':hi,'close_low':[canonical(low['c']),low['t']],'close_high':[canonical(high['c']),high['t']],'established_at':t,'reason':reason,'window_ids':[z['t'] for z in w],'old_window_ids':[z['t'] for z in old],'low_at':min(w,key=lambda z:z['l'])['t'],'high_at':max(w,key=lambda z:z['h'])['t'],'exit_low':lo-F(1,2),'exit_high':hi+F(1,2)};self.stop=None;cond['D']=False
            rm={'window_ids':[z['t'] for z in w],'old_window_ids':[z['t'] for z in old],'net':canonical(net),'tv':canonical(tv),'span':canonical(span),'width':canonical(width),'eta':qratio(net,tv),'turns':nturn,'old_low':canonical(min(z['l'] for z in old)) if old else None,'old_high':canonical(max(z['h'] for z in old)) if old else None,'guard':bool(guard),'conditions':cond}
        eq(o.get('range_analysis'),rm,'range_analysis.raw_full')
        if not self.box and not self.stop and self.direction and self.clock and self.blocked!=self.clock[1] and t-self.clock[1]>=3 and len(self.history)>=3:
            center=self.clock[0];lo=center-F(1,2);hi=center+F(1,2);w=self.history[-3:]
            if all(z['l']>=lo and z['h']<=hi for z in w):self.stop={'direction':self.direction,'center':canonical(center),'low':lo,'high':hi,'start':t,'count':1,'recognized_at':t,'count_start':t,'progress_at':self.clock[1],'evidence_window_start':w[0]['t'],'evidence_ids':[z['t'] for z in w],'continuation_ids':[t]}
        def formal(d):return None if d is None else {k:canonical(v) if type(v) is F else v for k,v in d.items()}
        eq(o.get('stop'),formal(self.stop),'stop.raw_full');eq(o.get('balance'),formal(self.box),'balance.raw_full')
        if o.get('stop') is not None:eq(set(o['stop']),STOP,'stop.schema')
        if o.get('balance') is not None:eq(set(o['balance']),BOX,'balance.schema')
        if rm is not None:eq(set(o.get('range_analysis') or {}),RANGE,'range.schema')
        fm=None;flag=None
        if len(self.history)>=6:
            w=self.history[-6:];xs=[z['c'] for z in w];net=xs[-1]-xs[0];tv=sum(abs(y-x) for x,y in zip(xs,xs[1:]));fm=dict(window_ids=[z['t'] for z in w],net=canonical(net),tv=canonical(tv),directional_net=canonical(self.direction*net),eta=qratio(net,tv))
            if self.direction:flag=self.direction*net>=5 and tv>0 and 5*abs(net)>=4*tv
        eq(o.get('fast_analysis'),fm,'fast_analysis.raw_full');eq(o.get('fast_flag'),flag,'fast_flag');
        if fm is not None:eq(set(o.get('fast_analysis') or {}),FAST,'fast.schema')
        activity='BALANCED' if self.box else 'STOPPED' if self.stop else 'LIVE' if self.direction else 'INITIALIZING';eq(o.get('activity'),activity,'activity');observed=activity!='INITIALIZING';eq(o.get('current_semantics_observed'),observed,'observed');eq(o.get('fast_applicable_to_primary'),activity=='LIVE','fast_application')
        primary='RANGE' if self.box else ('RISE_STOP' if self.direction==1 else 'DROP_STOP') if self.stop else ('REBOUND' if o.get('context')==-1 else 'SHARP_RISE' if flag else 'RISE') if self.direction==1 else ('PULLBACK' if o.get('context')==1 else 'SHARP_DROP' if flag else 'DROP') if self.direction==-1 else self.last_primary or 'RANGE'
        eq(o.get('primary'),primary,'primary.mapping');ck(o.get('primary') in STATES,'primary.enum')
        if observed:self.last_observed=t
        eq(o.get('observed_at'),self.last_observed,'observed_at');eq(o.get('basis'),'WARMUP_CARRY_OR_ANCHOR' if not observed else 'OBSERVED_NEW_SEGMENT_ONLY' if self.newseg else 'OBSERVED_FRESH','basis')
        ck(type(o.get('events')) is list and all(e in EVENTS for e in o['events']),'events.schema');eq('FIXED_BALANCE_BAND_CLOSE_BREAK' in o['events'],exited,'exit_event');eq('SEGMENT_RESET_NO_GAP_RETURN' in o['events'],bool(reset),'reset_event')
        for key in ['progress_clock','_context_extreme','_local_tip']:point(o.get(key),key)
        pivot(o.get('protected_origin'),'protected_origin');pivot(o.get('local_pivot_confirmed'),'local_pivot_confirmed')
        if exited:
            expected_pivot={'kind':'L' if self.direction==1 else 'H','x':exit_origin[0],'extremum_t':exit_origin[1],'confirmed_at':t,'generation_reason':'RANGE_EXIT'}
            eq(o.get('local_pivot_confirmed'),expected_pivot,'exit.origin_real_close_earliest')
        ps=o.get('_structure_pivots');ck(type(ps) is list,'structure.list')
        for p in ps or []:pivot(p,'structure.pivot')
        ck(o.get('_structure_direction') in (-1,0,1),'structure.direction');ck(o.get('context') in (-1,0,1),'context.enum')
        for key in ['context_established_at','protected_updated_at']:
            v=o.get(key);ck(v is None or (type(v) is int and v in self.raw and v<=t),key+'.real_causal')
        ut=o.get('protected_updated_at');eq(o.get('protected_effective_from'),ut+1 if ut is not None else None,'protected.effective_from')
        origin=o.get('protected_origin');eq(o.get('protected_after_effective_next'),origin['x'] if origin else None,'protected.after_origin')
        prev=self.prev if not reset else None;eq(o.get('protected_before'),prev.get('protected_after_effective_next') if prev else None,'protected.before_snapshot')
        if ut==t and 'PROTECTED_LEVEL_TIGHTENED_EFFECTIVE_NEXT_BAR' in o['events']:
            candidates=prev.get('_structure_pivots',[])[-3:] if prev else []
            ck(len(candidates)==3,'tighten.last3');
            if len(candidates)==3:
                a,m,z=candidates;s=o['context'];ck([p['kind'] for p in candidates]==(['L','H','L'] if s==1 else ['H','L','H']),'tighten.pattern');ck(all(p['confirmed_at']<t for p in candidates),'tighten.preknown');ck(s*(value(z['x'])-value(a['x']))>=F(1,2) and s*(value(z['x'])-value(o['protected_before']))>0 and s*(x-value(m['x']))>=F(1,2),'tighten.exact');eq(origin,z,'tighten.origin')
        if self.box:eq(o['context'],0,'range.retires_context')
        broken=bool(prev and prev['context'] and prev['protected_after_effective_next'] is not None and prev['context']*(x-value(prev['protected_after_effective_next']))<=-F(1,2))
        eq('STRUCTURE_BREAK_FROM_PREVIOUS_LEVEL' in o['events'],broken,'structure.break_raw_old_level')
        if broken:
            eq(o['context'],-prev['context'],'structure.break_direction');prior_extreme=prev['_context_extreme'];eq(origin,{'kind':'L' if o['context']==1 else 'H','x':prior_extreme[0],'extremum_t':prior_extreme[1],'confirmed_at':t,'generation_reason':'STRUCTURE_BREAK'},'structure.break_real_origin')
        # Context direction establishment/break judgment is checked by two separate
        # state engines + fixed semantic fixtures; here track real extreme source.
        if not o['context']:self.context_extreme=None
        elif not prev or prev['context']!=o['context'] or prev['context_established_at']!=o['context_established_at']:self.context_extreme=here
        elif self.context_extreme is None or o['context']*(x-self.context_extreme[0])>0:self.context_extreme=here
        eq(o.get('_context_extreme'),None if self.context_extreme is None else [canonical(self.context_extreme[0]),self.context_extreme[1]],'context.extreme_raw')
        self.prev=o;self.last_primary=o['primary'];return errors
