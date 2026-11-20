"""Bounded causal Event study. Policy states and outcomes are separate records.

Default entry point is TRAIN only. No estimator fit, oracle entry or EXIT call.
"""
import argparse
import collections
import copy
import hashlib
import json
import math
import statistics
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

import numpy as np
from scripts import phase57_comprehensive_entry_v2 as v2

m, c, q = v2.m, v2.c, v2.q
ROOT = m.ROOT
BASE = ROOT / 'docs/evidence/phase57-comprehensive-entry-v3'
PROTOCOL_COMMIT = 'f66b4783f0507a2733d6ccdef90a209bb729fed0'
PROTOCOL_SHA = '642e43b301b5d46535f7399e509e0923e3393584fa4bbafbe99852c6ee0975f8'
EVENTS = ('E1_PULLBACK', 'E2_STABILIZATION', 'E3_RECLAIM', 'E4_MOMENTUM_TURN',
          'E5_FAILED_BREAKDOWN', 'E6_CONTINUATION', 'S1_P_S_R', 'S2_P_F_R', 'S3_P_S_M')
CLASSES = ('IMMEDIATE_WINNER', 'PULLBACK_THEN_WINNER', 'DEEP_PULLBACK_THEN_WINNER',
           'CHOP_THEN_WINNER', 'CONTINUED_FAILURE', 'OPPORTUNITY_EXPIRED', 'INCONCLUSIVE')
PB = ('PULLBACK_THEN_WINNER', 'DEEP_PULLBACK_THEN_WINNER')
SEQUENCES = {'S1_P_S_R': (0, 1, 2), 'S2_P_F_R': (0, 4, 2), 'S3_P_S_M': (0, 1, 3)}


def protocol():
    assert m.sha(BASE/'protocol.json') == PROTOCOL_SHA, 'PROTOCOL_MUTATED'
    p = m.read(BASE/'protocol.json')
    for name, digest in p['sourcePins'].items():
        assert m.sha(ROOT/name) == digest, name
    assert tuple(p['eventOrder']) == EVENTS
    assert all(x is False for x in p['safety'].values())
    return p


def sources(partition='TRAIN', contract=None):
    p = protocol()
    if partition != 'TRAIN':
        raise RuntimeError('SEALED_PARTITION_REQUIRES_SEPARATE_PRECOMMITTED_CANDIDATE_RUNNER')
    old, ops, paths, selectors, legacy = v2.sources()
    assert p['split'] == old['split']
    assert len(ops) == p['population']['expected']
    for name, dates in p['split'].items():
        assert sum(x['session'] in dates for x in ops) == p['population'][name]
    # Bundled source identity is verified, then sealed rows are inaccessible below.
    ops = [x for x in ops if x['session'] in p['split'][partition]]
    ids = {x['op']['anchorId'] for x in ops}
    return p, ops, {k: paths[k] for k in ids}, {k: selectors[k] for k in ids}, {k: legacy[k] for k in ids if k in legacy}


def normalized(bars, path, reference):
    return [{**{k: 100*(path['decisionPrice']*(1+b[k]/100)/reference-1) for k in ('o','h','l','c')},
             'start': b['start'], 'end': b['end']} for b in bars]


def describe(bars):
    """Continuous descriptors only, computed entirely from the known prefix."""
    if not bars:
        return {k: None for k in protocol_descriptor_names()}
    b = bars[-1]; prev = bars[-2] if len(bars)>1 else None
    cs = [z['c'] for z in bars]; changes = [y-x for x,y in zip(cs,cs[1:])]
    ranges = [z['h']-z['l'] for z in bars[-6:]]; span = b['h']-b['l']
    pb_indices = [i for i,z in enumerate(bars) if z['c']<0]
    lower = 0
    for x in reversed(changes):
        if x>=0: break
        lower += 1
    low_extension = max(0, prev['l']-b['l']) if prev else None
    old_extension = max(0, bars[-3]['l']-prev['l']) if len(bars)>=3 else None
    loc = (b['c']-b['l'])/span if span else .5
    ploc = ((prev['c']-prev['l'])/(prev['h']-prev['l']) if prev['h']>prev['l'] else .5) if prev else None
    turn = len(changes)>=2 and changes[-2]<=0 and changes[-1]>0
    continuation = len(bars)>=3 and bars[-1]['c']>bars[-2]['c']>bars[-3]['c'] and bars[-1]['l']>bars[-2]['l']>bars[-3]['l'] and b['h']>prev['h']
    rhi = max(z['h'] for z in bars[-6:]); rlo = min(z['l'] for z in bars[-6:])
    return {'drawdownClose': min(0,b['c']), 'drawdownLow': min(0,min(z['l'] for z in bars)),
        'pullbackFromRunningHigh': b['c']-max(z['h'] for z in bars),
        'pullbackAge': 5*(len(bars)-1-pb_indices[0]) if pb_indices else None,
        'consecutiveLowerCloses': lower, 'lowExtension': low_extension,
        'adverseAcceleration': changes[-1]-changes[-2] if len(changes)>=2 else None,
        'volatilityNormalizedPullback': min(0,b['c'])/statistics.mean(ranges) if sum(ranges)>0 else None,
        'recentRangeLocation': (b['c']-rlo)/(rhi-rlo) if rhi>rlo else .5,
        'rangeContraction': span/(prev['h']-prev['l']) if prev and prev['h']>prev['l'] else None,
        'lowerWick': min(b['o'],b['c'])-b['l'], 'closeLocation':loc,
        'closeLocationChange': loc-ploc if ploc is not None else None,
        'closeDeteriorationStopped': b['c']>=prev['c'] if prev else None,
        'newLowStopped': b['l']>=prev['l'] if prev else None,
        'higherLow': b['l']>prev['l'] if prev else None, 'higherClose': b['c']>prev['c'] if prev else None,
        'priorHighReclaim': b['c']>prev['h'] if prev else None,
        'failedBreakdown': b['l']<prev['l'] and b['c']>prev['l'] if prev else None,
        'momentumTurn': turn, 'continuation': continuation,
        'closeVolatility': statistics.pstdev(changes) if changes else None,
        'lowExtensionChange': low_extension-old_extension if old_extension is not None else None}


def protocol_descriptor_names():
    # No runtime loading of outcomes or fit parameters.
    return ('drawdownClose','drawdownLow','pullbackFromRunningHigh','pullbackAge','consecutiveLowerCloses',
        'lowExtension','adverseAcceleration','volatilityNormalizedPullback','recentRangeLocation',
        'rangeContraction','lowerWick','closeLocation','closeLocationChange','closeDeteriorationStopped',
        'newLowStopped','higherLow','higherClose','priorHighReclaim','failedBreakdown','momentumTurn',
        'continuation','closeVolatility','lowExtensionChange')


def reconstruct(x, path, selector, legacy):
    """Immutable PIT state sequence; no evaluation, current execution bar or labels."""
    op=x['op']; start=c.minute(op['opportunityTimestamp']); bound=c.segment_end(start,path['sessionEndMinute'])
    reference=op.get('referencePrice'); terminal=None; states=[]
    if op['referenceStatus']!='REFERENCE_OPEN' or isinstance(reference,bool) or not isinstance(reference,(float,int)) or not math.isfinite(reference) or reference<=0:
        terminal='UNKNOWN_REFERENCE'
    for delay in range(0,31,5):
        t=start+delay
        if terminal is None and (bound is None or t>=bound): terminal='EXPIRED_BOUNDARY'
        f=None
        if terminal is None:
            f=v2.state(x,path,selector,legacy,t)
            if f is None: terminal='UNKNOWN_PREFIX'
        row={'timestamp':c.stamp(x['session'],t),'delay':delay,'status':terminal or 'AVAILABLE'}
        if terminal is None:
            bs=[b for b in path['future'] if c.minute(b['start'])>=start and c.minute(b['end'])<=t]
            assert len(bs)==delay//5
            bars=normalized(bs,path,reference)
            row.update(features=f,descriptors=describe(bars),bars=bars,
                newestCompletedEnd=bs[-1]['end'] if bs else None,
                intrabarOrder='UNKNOWN_INTRABAR_ORDER',
                dynamicVWAP='UNAVAILABLE',dynamicVolume='UNAVAILABLE',dynamicRelativeStrength='UNAVAILABLE')
        states.append(row)
    return states


def detect(states):
    """First causal Event per family; each sequence advances at most one stage/bar."""
    found={}; stage={k:[] for k in SEQUENCES}; first_pullback=None
    for s in states:
        if s['status']!='AVAILABLE': break
        bars=s['bars']
        if not bars: continue
        b=bars[-1]; prev=bars[-2] if len(bars)>1 else None; d=s['descriptors']
        earlier_pb=first_pullback is not None and first_pullback<s['delay']
        predicates=(b['c']<0,
            bool(earlier_pb and prev and b['l']>=prev['l'] and b['c']>=prev['c'] and b['h']-b['l']<=prev['h']-prev['l']),
            bool(earlier_pb and d['priorHighReclaim']), bool(earlier_pb and d['momentumTurn']),
            bool(earlier_pb and d['failedBreakdown']), bool(d['continuation']))
        for i,hit in enumerate(predicates):
            if hit and EVENTS[i] not in found:
                found[EVENTS[i]]={'delay':s['delay'],'timestamp':s['timestamp'],'recognitionClosePct':b['c'],'sequenceDelays':[s['delay']]}
        for name, seq in SEQUENCES.items():
            completed=stage[name]
            if len(completed)<len(seq) and predicates[seq[len(completed)]]:
                assert not completed or completed[-1]<s['delay']
                completed.append(s['delay'])
                if len(completed)==len(seq):
                    found[name]={'delay':s['delay'],'timestamp':s['timestamp'],'recognitionClosePct':b['c'],'sequenceDelays':list(completed)}
        if predicates[0] and first_pullback is None: first_pullback=s['delay']
    return found


def decision(x,path,states,event):
    if event is not None:
        price=v2.open_reference(path,c.minute(event['timestamp']))
        return {'status':'COUNTERFACTUAL_ENTER' if price is not None else 'UNKNOWN_EXECUTION',
            'delay':event['delay'] if price is not None else None,
            'transitions':[{'timestamp':s['timestamp'],'delay':s['delay'],
                'action':'BUY_NOW' if s['delay']==event['delay'] else 'WAIT_ONE_STEP'} for s in states if s['delay']<=event['delay']],
            'executionPrice':price,'event':event}
    bad=next((s for s in states if s['status']!='AVAILABLE'),None)
    return {'status':bad['status'] if bad else 'NO_EVENT','delay':None,
        'transitions':[{'timestamp':s['timestamp'],'delay':s['delay'],'action':'WAIT_ONE_STEP' if s['delay']<30 else 'NO_EVENT'} for s in states if s['status']=='AVAILABLE'],
        'executionPrice':None,'event':None}


def outcome_row(x,path,d):
    """Evaluator only: called after policy Event/decision is fixed."""
    b=v2.evaluate(x,path,0); e=v2.evaluate(x,path,d['delay']) if d['delay'] is not None else None
    cls=m.path_class(x,path)
    return {'id':x['id'],'session':x['session'],'symbol':x['symbol'],'source':x['op']['eventType'],
        'timestamp':x['op']['opportunityTimestamp'],'breadth':x['breadth'],'pathClass':cls,
        'decision':d,'baseline':b,'entry':e,
        'immediateEntryRequiredDiagnosticOnly': d['status'] in ('NO_EVENT','EXPIRED_BOUNDARY') and cls=='IMMEDIATE_WINNER',
        'winnerBeforeEvent':{str(k): bool(b and b['commonComplete'] and d.get('event') and
            b['common']['hitMinutes'][str(k)] is not None and b['common']['hitMinutes'][str(k)]<=d['event']['delay']) for k in (1,2,3,5)}}


def complete(rows): return [r for r in rows if r['baseline'] and r['baseline']['commonComplete']]
def entered(rows): return [r for r in rows if r['entry'] and r['entry']['commonComplete']]
def fraction(n,d): return n/d if d else None
def improvement(b,a,key): return a[key]-b[key] if a[key] is not None and b[key] is not None else None
def ge(x,y): return x is not None and math.isfinite(x) and x>=y


def occurrence(rows):
    n=len(rows); k=sum(r['decision'].get('event') is not None for r in rows)
    if not n:return {'n':0,'eventN':0,'rate':None,'wilson95':None}
    z=1.959963984540054; p=k/n; den=1+z*z/n
    mid=(p+z*z/(2*n))/den; width=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return {'n':n,'eventN':k,'rate':p,'wilson95':[mid-width,mid+width]}


def cohort_metrics(rows):
    rs=complete(rows); pairs=entered(rs); s=v2.summarize(rows)
    ratios={str(k):fraction(sum(r['baseline']['common']['mfe']>=k and r['entry']['common']['mfe']>=k for r in pairs),
        sum(r['baseline']['common']['mfe']>=k for r in pairs)) for k in (1,2,3,5)}
    bm=s['baselinePairedMFE']['mean']; am=s['entryPairedMFE']['mean']
    return {'summary':s,'occurrence':occurrence(rs), 'occurrenceAll':occurrence(rows),
        'enteredPairPreservation':ratios,'remainingMFEMeanRatio':am/bm if bm is not None and bm>0 and am is not None else None,
        'strict30MedianImprovementPP':improvement(s['baselineStrict30MAE'],s['entryStrict30MAE'],'median'),
        'strict30P05ImprovementPP':improvement(s['baselineStrict30MAE'],s['entryStrict30MAE'],'p05'),
        'eventDelay':m.dist([r['decision']['event']['delay'] for r in rs if r['decision'].get('event')]),
        'entryPrice':m.dist([r['entry']['price'] for r in pairs]),'baselineEntryPricePaired':m.dist([r['baseline']['price'] for r in pairs]),
        'winnerBeforeEvent':{str(k):sum(r['winnerBeforeEvent'][str(k)] for r in rs) for k in (1,2,3,5)},
        'noEventWinners':{str(k):sum(r['decision'].get('event') is None and r['baseline']['common']['mfe']>=k for r in rs) for k in (1,2,3,5)},
        'immediateEntryRequiredDiagnosticOnly':sum(r['immediateEntryRequiredDiagnosticOnly'] for r in rows),
        'delayBins':{str(d):sum(r['decision']['delay']==d for r in rows) for d in range(0,31,5)},
        'outcomes':dict(collections.Counter(r['decision']['status'] for r in rows)),
        'riskDecomposition':{str(k):{'baselineAll':s['tails'][str(k)]['baselineAll'],
            'RISK_REDUCTION_BY_BETTER_ENTRY':s['tails'][str(k)]['baselineEnteredPair']-s['tails'][str(k)]['entryPair'],
            'RISK_NOT_ENTERED_NOT_AN_ADOPTED_SKIP_POLICY':s['tails'][str(k)]['baselineAll']-s['tails'][str(k)]['baselineEnteredPair'],
            'entryTail':s['tails'][str(k)]['entryPair']} for k in (3,5,10)}}


def basic_mechanic(rows,g,samples=True):
    allrs=complete(rows); pb=[r for r in allrs if r['pathClass'] in PB]; fail=[r for r in allrs if r['pathClass']=='CONTINUED_FAILURE']
    z=cohort_metrics(pb); s=z['summary']; a=occurrence(pb); b=occurrence(fail)
    gap=a['rate']-b['rate'] if a['rate'] is not None and b['rate'] is not None else None
    gates={'pbCapture':ge(fraction(s['enteredCommon'],len(pb)),g['pullbackEventCoverage']),
        'failureSeparation':ge(gap,g['occurrenceGapVsContinuedFailure']),
        'priceMean':ge(s['priceImprovement']['mean'],g['pullbackPriceImprovementMeanPP']),
        'priceMedian':ge(s['priceImprovement']['median'],g['pullbackPriceImprovementMedianPP']),
        'strict30Median':ge(z['strict30MedianImprovementPP'],g['pullbackStrict30MAEMedianImprovementPP']),
        'strict30P05':ge(z['strict30P05ImprovementPP'],g['pullbackStrict30MAEP05ImprovementPP']),
        'remainingMFE':ge(z['remainingMFEMeanRatio'],g['pullbackRemainingMFEMeanRatioEnteredPairs']),
        'preserve3EnteredPairs':ge(z['enteredPairPreservation']['3'],g['pullbackPlus3PreservationEnteredPairs']),
        'preserve5EnteredPairs':ge(z['enteredPairPreservation']['5'],g['pullbackPlus5PreservationEnteredPairs'])}
    if samples:gates.update(completeN=len(allrs)>=g['completeBaselineN'],pbBaselineN=len(pb)>=g['pullbackBaselineN'],pbEventN=s['enteredCommon']>=g['pullbackEventN'])
    return {'gates':gates,'pullback':z,'failure':cohort_metrics(fail),'occurrenceGap':gap}


def panel(rows,p,top3,dates):
    g=p['mechanicKeepGate']; base=basic_mechanic(rows,g); gates=dict(base['gates'])
    bysource={k:basic_mechanic([r for r in rows if r['source']==k],g) for k in (q.INITIAL,q.DIP)}
    def cohort_pass(z):
        pb=z['pullback'];return pb['summary']['enteredCommon']>=5 and ge(pb['summary']['priceImprovement']['mean'],0) and ge(pb['strict30MedianImprovementPP'],0) and ge(pb['remainingMFEMeanRatio'],.85)
    gates['INITIAL_DIP']=all(cohort_pass(z) for z in bysource.values())
    blocks={str(i+1):basic_mechanic([r for r in rows if r['session'] in ds],g) for i,ds in enumerate(np.array_split(dates,4))}
    def block_pass(z):
        pb=z['pullback'];return pb['summary']['commonComplete']>=10 and z['failure']['summary']['commonComplete']>=10 and pb['summary']['enteredCommon']>=3 and ge(z['occurrenceGap'],0) and ge(pb['summary']['priceImprovement']['mean'],0) and ge(pb['strict30MedianImprovementPP'],0)
    flags={k:block_pass(z) for k,z in blocks.items()};gates['chronological']=sum(flags.values())>=3
    pbpairs=entered([r for r in complete(rows) if r['pathClass'] in PB]);sc=collections.Counter(r['symbol'] for r in pbpairs);dc=collections.Counter(r['session'] for r in pbpairs)
    gates['concentration']=bool(pbpairs) and max(sc.values())/len(pbpairs)<=.25 and max(dc.values())/len(pbpairs)<=.25
    ex=basic_mechanic([r for r in rows if r['symbol'] not in top3],g,False);gates['top3Exclusion']=all(ex['gates'].values())
    freq=collections.Counter(r['symbol'] for r in rows)
    return {**base,'gates':gates,'verdict':'KEEP_MECHANIC' if all(gates.values()) else 'KILL',
        'failedGates':[k for k,val in gates.items() if not val], 'overall':cohort_metrics(rows),
        'classes':{k:cohort_metrics([r for r in rows if r['pathClass']==k]) for k in CLASSES},
        'cohorts':bysource,'chronological':blocks,'chronologicalPass':flags,'top3Excluded':ex,
        'concentration':{'top3Train':top3,'uniqueSymbols':len(freq),'symbolHHI':sum((n/len(rows))**2 for n in freq.values()),
            'top10':sorted(freq.items(),key=lambda kv:(-kv[1],kv[0]))[:10],
            'pullbackEnteredUniqueSymbols':len(sc),'pullbackEnteredSymbolHHI':sum((n/len(pbpairs))**2 for n in sc.values()) if pbpairs else None,
            'maxPullbackSymbolShare':max(sc.values())/len(pbpairs) if sc else None,'maxPullbackSessionShare':max(dc.values())/len(pbpairs) if dc else None},
        'breadth':{str(k):cohort_metrics([r for r in rows if r['breadth']==k]) for k in range(1,6)},
        'sessionPart':{part:cohort_metrics([r for r in rows if (c.minute(r['timestamp'])<690)==morning]) for part,morning in [('morning',True),('afternoon',False)]}}


def run(outdir):
    out=Path(outdir)
    if out.exists():raise FileExistsError(out)
    p,ops,paths,selectors,legacy=sources();out.mkdir(parents=True)
    state_rows=[]; ledgers={name:[] for name in EVENTS}; baseline=[]; descriptors=[]
    freq=collections.Counter(x['symbol'] for x in ops);top3=[k for k,n in sorted(freq.items(),key=lambda kv:(-kv[1],kv[0]))[:3]]
    for x in ops:
        aid=x['op']['anchorId'];path=paths[aid]
        states=reconstruct(x,path,selectors[aid],legacy.get(aid,{}));found=detect(states)
        state_rows.append({'id':x['id'],'session':x['session'],'source':x['op']['eventType'],'states':states,'events':found})
        for s in states:
            if s['status']=='AVAILABLE': descriptors.append(s['descriptors'])
        for name in EVENTS:ledgers[name].append(outcome_row(x,path,decision(x,path,states,found.get(name))))
        d=v2.decide(x,path,selectors[aid],legacy.get(aid,{}),baseline='B0_IMMEDIATE');d['event']={'delay':0,'timestamp':x['op']['opportunityTimestamp']}
        baseline.append(outcome_row(x,path,d))
    m.write(out/'train-pit-states.json.gz',state_rows)
    m.write(out/'b0-immediate-train.json.gz',baseline)
    results={}
    for name,rows in ledgers.items():
        m.write(out/(name.lower()+'-train.json.gz'),rows);results[name]=panel(rows,p,top3,p['split']['TRAIN'])
    keep=[name for name in p['mechanicPriority'] if results[name]['verdict']=='KEEP_MECHANIC']
    status='TRAIN_MECHANIC_KEEP_REQUIRES_ARCHITECTURE_PRECOMMIT' if keep else 'COMPREHENSIVE_LONG_ENTRY_V3_DEVELOPMENT_LIMIT_REACHED'
    summary={'status':status,'protocolCommit':PROTOCOL_COMMIT,'protocolSHA256':PROTOCOL_SHA,'population':p['population'],
        'partitionEvaluated':'TRAIN','trainSessions':38,'trainEmitted':len(ops),'trainCompleteCommon60':len(complete(baseline)),
        'sourceCounts':dict(collections.Counter(r['source'] for r in baseline)),
        'classCountsAll':dict(collections.Counter(r['pathClass'] for r in baseline)),
        'classCountsComplete':dict(collections.Counter(r['pathClass'] for r in complete(baseline))),
        'events':results,'keepMechanics':keep,'selectedMechanic':keep[0] if keep else None,
        'baseline':cohort_metrics(baseline),'stateDescriptors':{k:m.dist([d[k] for d in descriptors]) for k in protocol_descriptor_names()},
        'stateAvailability':dict(collections.Counter(s['status'] for r in state_rows for s in r['states'])),
        'contextAvailability':{'legacyAnchorOnly':{k:sum(legacy.get(x['op']['anchorId'],{}).get('features',{}).get(k,{}).get('status')=='AVAILABLE' for x in ops) for k in m.LEGACY},
            'dynamicVolume':'UNAVAILABLE','dynamicVWAP':'UNAVAILABLE','dynamicRelativeStrength':'UNAVAILABLE','marketIndexPath':'UNAVAILABLE'},
        'supervisedFits':0,'validationEvaluations':0,'developmentTestEvaluations':0,'freshOOSOpened':False,
        'economic':'NOT_RUN_NO_ENTRY_GATE_SURVIVOR','candidateFreeze':False,'safety':p['safety'],
        'limits':['TRAIN is already generally outcome-exposed Development, not Fresh.',
            'Only complete same-segment common60 outcomes are performance denominators; all missing paths remain emitted.',
            'Independent INITIAL/DIP alternatives can share symbol-session. State count is not independent sample size.',
            'Event occurrence gap is descriptive; Wilson intervals do not make correlated episodes independent.',
            'No-event is a diagnostic outcome, not an adopted SKIP policy. Immediate-required tag is evaluator-only.',
            'Saved 5m bars may have fewer than five underlying observations. No new minute data used.']}
    m.write(out/'summary.json',summary)
    m.write(out/'manifest.json',{'protocolCommit':PROTOCOL_COMMIT,'protocolSHA256':PROTOCOL_SHA,'sourcePins':p['sourcePins'],
        'codeSHA256':m.sha(__file__),'outputs':{f.name:m.sha(f) for f in sorted(out.iterdir())},'safety':p['safety']})
    print(json.dumps({'status':status,'complete':summary['trainCompleteCommon60'],'keep':keep,'events':{k:{'verdict':z['verdict'],'failedGates':z['failedGates']} for k,z in results.items()}},indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',required=True);args=parser.parse_args()
    with ExitStack() as stack:
        for obj,name in ((m.Model,'fit'),(v2,'fit_heads'),(v2,'fit_guard'),(v2,'economic')):
            stack.enter_context(patch.object(obj,name,side_effect=AssertionError('EVENT_STUDY_NO_FIT_NO_ECONOMIC')))
        run(args.out)
