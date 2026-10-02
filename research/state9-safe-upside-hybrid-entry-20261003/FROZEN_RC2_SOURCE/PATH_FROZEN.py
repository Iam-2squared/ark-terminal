"""Streaming candidate Path builder. Imports no State9, M0 or reference helpers."""
from copy import deepcopy
from datetime import datetime

STATES=('RISE','SHARP_RISE','RISE_STOP','PULLBACK','RANGE','REBOUND','DROP','SHARP_DROP','DROP_STOP')
REQUIRED=('as_of','primary','current_semantics_observed','activity','basis','observed_at','context','leg_direction','direction_basis','fast_flag','fast_applicable_to_primary','stop','balance','events','numeric_status','rejection_reason','bar_metadata')

class PathInputError(ValueError): pass

def validate(row,slot,previous):
    if not isinstance(row,dict) or not isinstance(slot,dict) or any(k not in row for k in REQUIRED):
        raise PathInputError('SCHEMA')
    t=slot.get('scheduled_t')
    if type(t) is not int or type(row['as_of']) is not int or row['as_of']!=t: raise PathInputError('PROTOCOL_CLOCK')
    try:
        clock=datetime.fromisoformat(slot['bar_end'])
    except (ValueError,KeyError,TypeError): raise PathInputError('BAR_END_FORMAT')
    if clock.utcoffset() is None:raise PathInputError('BAR_END_TIMEZONE')
    if previous is not None and (t<=previous['scheduled_t'] or clock<=datetime.fromisoformat(previous['bar_end'])):raise PathInputError('PROTOCOL_ORDER')
    if type(row['current_semantics_observed']) is not bool or type(row['fast_applicable_to_primary']) is not bool:raise PathInputError('OBSERVATION_TYPE')
    if row['primary'] not in STATES+(None,):raise PathInputError('PRIMARY_ENUM')
    if row['numeric_status'] not in ('ACCEPTED','REJECTED','NOT_AVAILABLE'):raise PathInputError('STATUS_ENUM')
    if row['fast_flag'] is not None and type(row['fast_flag']) is not bool:raise PathInputError('FAST_TYPE')
    if any(v is not None and (type(v) is not int or v not in (-1,0,1)) for v in (row['context'],row['leg_direction'])):raise PathInputError('DIRECTION_TYPE')
    at=row['observed_at']
    if at is not None and (type(at) is not int or at>t):raise PathInputError('OBSERVED_AT')
    if not isinstance(row['events'],list) or any(type(v) is not str for v in row['events']):raise PathInputError('EVENT_SCHEMA')
    if not isinstance(slot.get('row_status'),str):raise PathInputError('SLOT_STATUS')
    if row['numeric_status']=='ACCEPTED':
        m=row['bar_metadata']
        if not isinstance(m,dict) or type(m.get('t')) is not int or m['t']!=t or type(m.get('known_at')) is not int or m['known_at']>t or type(m.get('source')) is not str or type(m.get('auction')) is not str:raise PathInputError('BAR_METADATA')
    if row['current_semantics_observed']:
        if row['primary'] is None or row['numeric_status']!='ACCEPTED' or row['activity'] not in ('LIVE','STOPPED','BALANCED') or row['basis'] not in ('OBSERVED_FRESH','OBSERVED_NEW_SEGMENT_ONLY') or at!=t:raise PathInputError('OBSERVED_CONTRACT')
    elif row['numeric_status']=='ACCEPTED' and row['activity']!='INITIALIZING':raise PathInputError('UNOBSERVED_ACCEPTED_CONTRACT')
    if row['stop'] is not None and not isinstance(row['stop'],dict):raise PathInputError('STOP_SCHEMA')
    if row['balance'] is not None and not isinstance(row['balance'],dict):raise PathInputError('RANGE_SCHEMA')

class PathBuilder:
    def __init__(self,case_id):
        if not isinstance(case_id,str) or not case_id:raise PathInputError('CASE_ID')
        self.case_id=case_id;self.segment=0;self.accepted=None;self.pending=set()
        self.endpoints=[];self.events=[];self.runs=[];self.active=None

    def _event(self,e,kind,a,b,reason=None,details=None):
        self.events.append({'event_id':f'{self.case_id}:E{len(self.events)+1:06d}','scheduled_t':e['scheduled_t'],'bar_end':e['bar_end'],'causal_segment_id':e['causal_segment_id'],'event_type':kind,'from_primary_or_null':a,'to_primary_or_null':b,'reason':reason,'details':deepcopy(details)})

    def push(self,row,slot):
        validate(row,slot,self.endpoints[-1] if self.endpoints else None)
        staged=deepcopy(self)
        result=staged._push(row,slot)
        self.__dict__=staged.__dict__
        return deepcopy(result)

    def _push(self,row,slot):
        t=slot['scheduled_t'];p=self.endpoints[-1] if self.endpoints else None
        meta=row['bar_metadata'] or {};reset=[]
        if row['numeric_status']=='ACCEPTED':
            if 'NOT_AVAILABLE' in self.pending:reset.append('AFTER_UNAVAILABLE')
            if 'REJECTED' in self.pending:reset.append('AFTER_REJECTED')
            if self.accepted is not None:
                if t!=self.accepted['t']+1:reset.append('ORDINAL_GAP')
                if meta['source']!=self.accepted['source']:reset.append('SOURCE_CHANGE')
                if meta['auction']!=self.accepted['auction']:reset.append('AUCTION_CHANGE')
            if 'SEGMENT_RESET_NO_GAP_RETURN' in row['events']:reset.append('FROZEN_RESET_EVENT')
            if self.accepted is None:
                self.segment=1;reset=['INITIAL_SEGMENT']+reset
            elif reset:self.segment+=1
            self.accepted=deepcopy(meta);self.pending.clear()
        else:self.pending.add(row['numeric_status'])
        observed=row['current_semantics_observed'];primary=row['primary'] if observed else None
        e={'case_id':self.case_id,'scheduled_t':t,'bar_end':slot['bar_end'],'causal_segment_id':f'{self.case_id}:S{self.segment:04d}','Primary_or_null':primary,'display_primary':row['primary'],'current_semantics_observed':observed,'activity':row['activity'],'basis':row['basis'],'observed_at':row['observed_at'],'local_direction':row['leg_direction'],'context_direction':row['context'],'direction_basis':row['direction_basis'],'fast':row['fast_flag'],'fast_applicable_to_primary':row['fast_applicable_to_primary'],'stop':deepcopy(row['stop']),'range':deepcopy(row['balance']),'source_events':deepcopy(row['events']),'quality':{'numeric_status':row['numeric_status'],'reason':row['rejection_reason'],'reset_reasons':reset,'row_status':slot['row_status'],'source':meta.get('source'),'auction':meta.get('auction')},'run_id':None,'dwell_scheduled_bars':None,'dwell_observed_bars':None,'entered_at':None,'entered_bar_end':None,'last_observed_at':None,'last_observed_bar_end':None}
        gap=p is not None and t!=p['scheduled_t']+1
        segchange=p is not None and p['causal_segment_id']!=e['causal_segment_id'] and not p['causal_segment_id'].endswith(':S0000')
        brk=gap or segchange
        connection=p is not None and not brk and p['current_semantics_observed'] and observed and p['causal_segment_id']==e['causal_segment_id']
        a=p['Primary_or_null'] if p else None
        if brk:
            reasons=list(reset)
            if gap:reasons.append('ENDPOINT_ORDINAL_GAP')
            self._event(e,'SEGMENT_BREAK',a,primary,'|'.join(reasons),{'old_segment_id':p['causal_segment_id'],'new_segment_id':e['causal_segment_id']})
        if p is not None and p['current_semantics_observed'] and not observed:self._event(e,'OBSERVATION_LOST',a,None,row['basis'])
        if e['activity']=='INITIALIZING' and (p is None or p['activity']!='INITIALIZING' or brk):self._event(e,'INITIALIZING',a,None,'ACCEPTED_NOT_OBSERVED')
        hold=connection and a==primary
        transition=connection and a!=primary
        if self.active is not None and not hold:
            old=self.runs[self.active]
            why='SEGMENT_BREAK' if brk else 'OBSERVATION_LOST' if not observed else 'PRIMARY_CHANGE'
            old.update(closed_at=t,closed_bar_end=e['bar_end'],closed_reason=why)
            self._event(e,'EXIT',old['Primary'],None if not transition else primary,why,{'run_id':old['run_id'],'last_observed_at':old['last_observed_at'],'dwell_scheduled_bars':old['dwell_scheduled_bars'],'dwell_observed_bars':old['dwell_observed_bars']})
            self.active=None
        if observed:
            if not connection:
                why='FIRST_OBSERVATION' if p is None else 'AFTER_SEGMENT_BREAK' if brk else 'AFTER_NULL'
                self._event(e,'OBSERVATION_RESUMED',None,primary,why)
            if transition:self._event(e,'TRANSITION',a,primary,'ADJACENT_OBSERVED_SAME_SEGMENT')
            if not hold:
                rid=f'{self.case_id}:R{len(self.runs)+1:05d}'
                self.runs.append({'run_id':rid,'Primary':primary,'causal_segment_id':e['causal_segment_id'],'entered_at':t,'entered_bar_end':e['bar_end'],'last_observed_at':t,'last_observed_bar_end':e['bar_end'],'dwell_scheduled_bars':1,'dwell_observed_bars':1,'closed_at':None,'closed_bar_end':None,'closed_reason':None})
                self.active=len(self.runs)-1
                self._event(e,'ENTER',a if transition else None,primary,'PRIMARY_CHANGE' if transition else 'NEW_OBSERVED_RUN',{'run_id':rid})
            else:
                run=self.runs[self.active];run['last_observed_at']=t;run['last_observed_bar_end']=e['bar_end'];run['dwell_observed_bars']+=1;run['dwell_scheduled_bars']=t-run['entered_at']+1
                self._event(e,'HOLD',a,primary,'CONTIGUOUS_OBSERVED_SAME_PRIMARY',{'run_id':run['run_id']})
            run=self.runs[self.active]
            for k in ['run_id','dwell_scheduled_bars','dwell_observed_bars','entered_at','entered_bar_end','last_observed_at','last_observed_bar_end']:e[k]=run[k]
        if connection:self._facets(p,e)
        self.endpoints.append(e)
        return e

    def _facets(self,p,e):
        a=p['Primary_or_null'];b=e['Primary_or_null']
        def event(kind,key,reason):self._event(e,kind,a,b,reason,{'from':deepcopy(p[key]),'to':deepcopy(e[key])})
        if p['activity']=='BALANCED' and e['activity']!='BALANCED':event('RANGE_EXIT','range','FROZEN_ACTIVITY_CHANGE')
        if p['activity']!='BALANCED' and e['activity']=='BALANCED':event('RANGE_ENTER','range','FROZEN_ACTIVITY_CHANGE')
        def sid(q):
            s=q['stop']
            return (s.get('direction'),s.get('center'),s.get('recognized_at')) if q['activity']=='STOPPED' and s else None
        before=sid(p);after=sid(e)
        if before is not None and before!=after:event('STOP_EXIT','stop','FROZEN_STOP_IDENTITY_CHANGE')
        if after is not None and before!=after:event('STOP_ENTER','stop','FROZEN_STOP_IDENTITY_CHANGE')
        if before is not None and before==after and p['stop']!=e['stop']:event('STOP_UPDATE','stop','FROZEN_STOP_METADATA_CHANGE')
        if p['fast'] is not None and e['fast'] is None:event('FAST_UNAVAILABLE','fast','FROZEN_FAST_AVAILABILITY')
        if p['fast'] is None and e['fast'] is not None:event('FAST_AVAILABLE','fast','FROZEN_FAST_AVAILABILITY')
        if p['fast'] is True and e['fast'] is not True:event('FAST_EXIT','fast','FROZEN_FAST_FLAG_CHANGE')
        if p['fast'] is not True and e['fast'] is True:event('FAST_ENTER','fast','FROZEN_FAST_FLAG_CHANGE')
        for key,kind in [('context_direction','CONTEXT_CHANGE'),('local_direction','LOCAL_DIRECTION_CHANGE'),('direction_basis','DIRECTION_BASIS_CHANGE')]:
            if p[key]!=e[key]:event(kind,key,'FROZEN_METADATA_CHANGE')

    def snapshot(self):return deepcopy({'endpoints':self.endpoints,'events':self.events,'runs':self.runs})

def build(rows,slots,case_id):
    if len(rows)!=len(slots):raise PathInputError('ROW_SLOT_N')
    b=PathBuilder(case_id)
    for row,slot in zip(rows,slots):b.push(row,slot)
    return b.snapshot()
