"""Additive evaluator-only ordered-Low/later-High panels; no Entry decisions."""
from __future__ import annotations
import argparse
import collections
import math
from pathlib import Path
from scripts import phase57_entry_all_material_evaluator_v1 as canonical

STATES=('REBOUND','RISE','SHARP_RISE','DROP','PULLBACK','RANGE','SHARP_DROP','DROP_STOP','RISE_STOP')
BUCKETS=(('lt1',0,1),('1to2',1,2),('2to3',2,3),('3to4',3,4),('4to5',4,5),('ge5',5,float('inf')))


def valid_range(opportunity):
    oracle=opportunity.get('orderedOracle',{})
    if not oracle.get('fullSessionEvaluable'):
        return None,'FULL_SESSION_OBSERVATION_INSUFFICIENT'
    if oracle.get('status')!='OBSERVED_ORDERED_ORACLE':
        return None,str(oracle.get('status','MISSING_ORACLE'))
    low,high=oracle.get('low'),oracle.get('high')
    if low is None or high is None or low<=0 or high<=low:
        return None,'NONPOSITIVE_ORDERED_RANGE'
    if oracle.get('highMinute',-1)<=oracle.get('lowMinute',-1):
        return None,'NON_STRICT_ORACLE_ORDER'
    value=oracle.get('rangePct')
    if value is None or not math.isfinite(value):
        return None,'MISSING_RANGE_PCT'
    assert abs(value-100*(high/low-1))<1e-8, 'RANGE_DEFINITION_MISMATCH'
    return float(value),None


def build(opportunities,records,policy_name,t0_state_records=None,baseline_records=None,baseline_name=None):
    out=canonical.evaluate(opportunities,records,policy_name,baseline_records,baseline_name)
    values={}; reasons=collections.Counter()
    for o in opportunities:
        val,reason=valid_range(o)
        if reason: reasons[reason]+=1
        else: values[o['opportunity']]=val
    def panel(ids):
        opp,rec=canonical._subset(opportunities,records,ids)
        result=canonical.policy_panel(opp,rec)
        result['unfilledReasons']=dict(collections.Counter(
            r.get('unfilledReason') or r.get('reason') or r.get('noEntryReason') or 'UNSPECIFIED'
            for r in rec if not r['entryId']))
        result['entryPositionInvalidFilledN']=result['fills']-result['entryPosition']['count']
        return result
    buckets={}; assigned=set()
    for name,lo,hi in BUCKETS:
        ids={k for k,v in values.items() if lo<=v<hi}
        assert not assigned & ids
        assigned|=ids
        buckets[name]={'denominator':len(ids),'futureEvaluatorOnly':True,
            'definition':f'{lo} <= orderedOracle.rangePct < {hi}', 'metrics':panel(ids)}
    assert assigned==set(values)
    missing={o['opportunity'] for o in opportunities}-assigned
    buckets['notEvaluable']={'denominator':len(missing),'reasons':dict(sorted(reasons.items())),
        'futureEvaluatorOnly':True,'metrics':panel(missing)}
    out['orderedLowHighRangeBuckets']=buckets
    out['orderedLowHighRangeThresholds']={str(k):{'denominator':sum(v>=k for v in values.values()),
        'definition':f'orderedOracle.rangePct >= {k}; valid fully observed ordered range',
        'futureEvaluatorOnly':True,'metrics':panel({i for i,v in values.items() if v>=k})} for k in range(1,6)}
    out['rangeDefinitionClarification']={
        'entryPosition':'(entryPrice-orderedOracle.low)/(orderedOracle.high-orderedOracle.low), unchanged and unclipped',
        'legacyBuckets':'futureSelectorMfeBuckets use selectorOutcome.mfeEnd, NOT Low-to-High range',
        'newBuckets':'orderedLowHighRangeBuckets use 100*(orderedOracle.high/orderedOracle.low-1)',
        'oracle':'Existing maximum observed ordered rise with strictly later high; not unordered daily min/max',
        'nonEvaluableReasonCounts':dict(sorted(reasons.items())),
        'retrospectiveOnly':True,'changesInputEntryDecisions':False}
    if t0_state_records is not None:
        state_map={r['opportunity']:r['initialState'] for r in t0_state_records}
        assert set(state_map)=={o['opportunity'] for o in opportunities}
        assert set(state_map.values())<=set(STATES)
        out['fixedOriginalT0StatePanels']={s:panel({i for i,v in state_map.items() if v==s}) for s in STATES}
        out['fixedOriginalT0StateSource']='Original State-v3 T0 labels; reporting only; legacy records unchanged'
    return out


def self_test():
    def opp(low,high,range_pct,full=True,lm=1,hm=2):
        return {'orderedOracle':{'low':low,'high':high,'rangePct':range_pct,
            'fullSessionEvaluable':full,'lowMinute':lm,'highMinute':hm,'status':'OBSERVED_ORDERED_ORACLE'}}
    assert valid_range(opp(100,102,2))[0]==2
    assert valid_range(opp(100,105,5))[0]==5
    assert valid_range(opp(100,100,0))[1]=='NONPOSITIVE_ORDERED_RANGE'
    assert valid_range(opp(100,102,2,False))[0] is None
    assert valid_range(opp(100,102,2,hm=1))[1]=='NON_STRICT_ORACLE_ORDER'
    assert next(k for k,l,h in BUCKETS if l<=2<h)=='2to3'
    assert next(k for k,l,h in BUCKETS if l<=5<h)=='ge5'
    try:
        valid_range(opp(100,105,2))
        raise RuntimeError('wrong denominator accepted')
    except AssertionError as error:
        assert str(error)=='RANGE_DEFINITION_MISMATCH'
    print('PASS: 8 ordered-range definition/edge checks')


def main():
    p=argparse.ArgumentParser();p.add_argument('--self-test',action='store_true')
    for n in ('opportunities','records','policy-name','output','state-records','baseline-records','baseline-name'):
        p.add_argument('--'+n)
    a=p.parse_args()
    if a.self_test:self_test();return
    read=canonical.base.read_json
    out=build(read(Path(a.opportunities)),read(Path(a.records)),a.policy_name,
        read(Path(a.state_records)) if a.state_records else None,
        read(Path(a.baseline_records)) if a.baseline_records else None,a.baseline_name)
    canonical.base.write_json(Path(a.output),out)
    print({'population':out['population'],'rangeBuckets':{k:v['denominator'] for k,v in out['orderedLowHighRangeBuckets'].items()}})

if __name__=='__main__':main()
