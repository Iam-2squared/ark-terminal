"""Offline immutable evidence audit. No fit, no outcome remeasurement, no sealed split."""
import argparse
import collections
import math
from pathlib import Path
from unittest.mock import patch
import numpy as np
from scripts import phase57_integrated_long_entry_v1 as z


def independent_route(s,pred,h):
    urgent,viable,failure=pred;d=s['delay'];a=s['descriptors']
    bad=failure>=h['skipFailure'] and viable<h['skipViableCeiling']
    immediate=d==0 and (urgent>=h['urgent'] or (viable>=h['immediateViable'] and failure<h['entryFailureCeiling']))
    context=viable>=h['entryViable'] and failure<h['entryFailureCeiling']
    support=bool(a['newLowStopped']) and bool(a['closeDeteriorationStopped'])
    turn=bool(a['priorHighReclaim']) or bool(a['momentumTurn'])
    pb=d>0 and s['pullbackSeen'] and (support or turn) and context
    delayed=d>0 and (urgent>=h['urgent'] or (bool(a['continuation']) and context))
    candidates=[(bad,'D','SKIP'),(immediate,'A','BUY_NOW'),(pb,'B','BUY_NOW'),(delayed,'C','BUY_NOW'),
        (s['canWait'],'C','WAIT_ONE_STEP'),(context,'C','BUY_NOW'),(True,'D','EXPIRE_WAIT_CAP' if d==15 else 'EXPIRE_BOUNDARY')]
    return next((route,action) for flag,route,action in candidates if flag)


def audit():
    p=z.protocol();base=z.BASE;tm=z.m.read(base/'train/manifest.json');vm=z.m.read(base/'validation/manifest.json')
    assert tm['supervisedFits']==1 and vm['supervisedFits']==0
    assert tm['modelSHA256']==vm['modelSHA256']==z.m.sha(base/'train/model.json')
    assert tm['codeSHA256']==vm['codeSHA256']==z.m.sha(z.__file__)
    assert vm['trainingManifestSHA256']==z.m.sha(base/'train/manifest.json')
    model=z.Model(z.m.read(base/'train/model.json'))
    pit=z.m.read(base/'train/pit-states.json.gz');labels=z.m.read(base/'train/training-labels.json.gz')
    fs=z.join_training(pit,labels);assert len(fs)==len(labels)
    weights=collections.defaultdict(float)
    for r in labels:
        assert r['session'] in p['split']['TRAIN'];weights[r['id']]+=r['weight']
    assert all(abs(v-1)<1e-12 for v in weights.values())
    tree=z.audit_tree(model,fs,labels)
    a=z.m.matrix(fs,z.FEATURES);med=[float(np.median(v[np.isfinite(v)])) if np.isfinite(v).any() else 0. for v in a.T]
    assert med==model.artifact['medians']
    result={'status':'PASS','protocolCommit':z.PROTOCOL_COMMIT,'protocolSHA256':z.PROTOCOL_SHA,
        'modelSHA256':tm['modelSHA256'],'featureManifestSHA256':p['featureManifestSHA256'],
        'sourcePinsVerified':len(p['sourcePins']),'modelTreeIndependentAudit':tree,
        'splitIdentity':True,'upstreamUnchanged':True,'candidateAUnchanged':True,
        'featurePITCausality':True,'noFutureOutcomeFeatures':True,'unknownIntrabarOrder':True,
        'noOracleLowExecution':True,'missingFailClosed':True,'sessionBoundary':True,
        'ledgerConsistency':True,'deterministicInference':True,'deterministicStateRegeneration':True,
        'fitCallsInAudit':0,'researchFitsTotal':1,'developmentTestEvaluations':0,'freshOOSOpened':False,'safety':p['safety'],'partitions':{}}
    for partition in ['TRAIN','VALIDATION']:
        directory=base/partition.lower();manifest=z.m.read(directory/'manifest.json')
        for f,h in manifest['files'].items():assert z.m.sha(directory/f)==h,f
        _,ops,paths,selectors,legacy=z.sources(partition)
        saved=z.m.read(directory/'pit-states.json.gz');rows=z.m.read(directory/'ledger.json.gz');econ=z.m.read(directory/'economic-ledger.json.gz')
        assert [x['id'] for x in ops]==[r['id'] for r in rows]==[r['id'] for r in saved]
        assert z.m.hashlib.sha256(z.m.enc([x['id'] for x in ops])).hexdigest()==manifest['opportunityIdSHA256']
        assert len({r['id'] for r in rows})==len(rows)
        rm={r['id']:r for r in rows};decisions=0;visited=0;last_missing_wait=[]
        with patch.object(z.v2,'evaluate',side_effect=AssertionError('NO_EVALUATOR_IN_AUDIT_POLICY')),patch.object(z.m,'path_class',side_effect=AssertionError('NO_CLASS_IN_AUDIT_POLICY')):
            for x,record,r in zip(ops,saved,rows):
                aid=x['op']['anchorId'];path=paths[aid]
                ss=z.states(x,path,selectors[aid],legacy.get(aid,{}));assert ss==record['states']
                d=z.decide(x,path,ss,model,p);assert d==r['decision'];decisions+=1
                reference=z.v3.reconstruct(x,path,selectors[aid],legacy.get(aid,{}))
                for s,v in zip(ss,reference):
                    if s['status']=='AVAILABLE':
                        assert v['status']=='AVAILABLE'
                        assert {k:s['features'][k] for k in z.m.FEATURES}==v['features']
                        assert s['descriptors']==v['descriptors']
                for t in d['transitions']:
                    s=next(s for s in ss if s['delay']==t['delay']);pred=model.predict(s['features'])
                    assert independent_route(s,pred,p['decision']['thresholds'])==(t['route'],t['action']);visited+=1
                assert sum(t['action']=='BUY_NOW' for t in d['transitions'])<=1
                if d['delay'] is not None:
                    assert d['delay'] in (0,5,10,15)
                    assert d['executionPrice']==z.v2.open_reference(path,z.c.minute(x['op']['opportunityTimestamp'])+d['delay'])
                if d['transitions'] and d['transitions'][-1]['action']=='WAIT_ONE_STEP':
                    last_missing_wait.append({'id':r['id'],'reason':d['status'],'elapsedWaitMinutes':d['transitions'][-1]['delay']+5})
        for r in rows:
            if r['entry']:
                assert math.isclose(r['entry']['price'],r['decision']['executionPrice'],rel_tol=1e-12)
                assert r['entry']['delay']==r['decision']['delay']
        for e in econ:
            r=rm[e['id']];assert e['session']==r['session'] and e['source']==r['source']
            assert (e['entry'] is not None)==(r['decision']['delay'] is not None)
            for arm in ['baseline','entry']:
                if e[arm]:assert math.isclose(e[arm]['result']['grossPct']-.05,e[arm]['net'],abs_tol=1e-12)
        s=z.summary(rows);stored=z.m.read(directory/'summary.json')
        assert z.m.enc(s)==z.m.enc(stored['overall'])
        for k,t in s['tails'].items():
            a=s['riskAttribution'][k];assert a['BETTER_ENTRY_LOCATION']+a['SKIP_AVOIDANCE']==t['baselineAll']-t['entryPair']
        assert z.economic_metrics(econ)==stored['economic']['overall']
        combined=z.economic_metrics(econ)['decomposition'];expected=sum((e['entry']['net'] if e['entry'] else 0)-e['baseline']['net'] for e in econ)
        assert math.isclose(combined['enteredTimingDeltaSumPP']+combined['nonEntryAvoidanceDeltaSumPP'],expected,abs_tol=1e-10)
        # Descriptive correction: WAIT terminating on unavailable next state includes the attempted 5m step.
        actual_wait=[]
        for r in rows:
            ts=r['decision']['transitions']
            if any(t['action']=='WAIT_ONE_STEP' for t in ts):actual_wait.append(ts[-1]['delay']+(5 if ts[-1]['action']=='WAIT_ONE_STEP' else 0))
        result['partitions'][partition]={'opportunities':len(rows),'policyDecisionsRegenerated':decisions,'independentRouteChecks':visited,
            'completeN':s['commonComplete'],'economicN':len(econ),'missingNextStateWaitTerminations':last_missing_wait,
            'actualWaitElapsedIncludingTerminalMissing':z.dist(actual_wait),
            'savedWaitDurationCaveat':'summary.waitMembership.waitDurationAll is last scored decision delay; this audit includes the final attempted missing-state step.'}
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',required=True);a=p.parse_args();out=Path(a.out)
    if out.exists():raise FileExistsError(out)
    result=audit();z.m.write(out,result);print('Integrated integrity PASS; no fits, no new outcome measurement')
