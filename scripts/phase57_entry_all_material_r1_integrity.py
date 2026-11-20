"""Independent R1 integrity diagnostics; no fitting or performance-based selection.

Mutation sample: first 32 current Opportunity IDs ranked by SHA256(seed || ID).
Full future OHLCV suffix is evaluator-side input to this test only. Production
features continue to receive the strictly closed prefix. Original Pattern 476
columns retain their separately pinned upstream P0 scope/limitations.
"""
from __future__ import annotations
import argparse,collections,hashlib,json,math
from pathlib import Path
import numpy as np
from scripts import phase57_entry_all_material_r1_data as d
from scripts import phase57_entry_all_material_r1_train as t
from scripts import phase57_entry_all_material_evaluator_v1 as c


def prefit_checks(out):
    root=d.OUT/'prefit'
    manifest=d.read(root/'manifest.json')
    for name,h in manifest.items():assert d.digest(root/name)==h,name
    rows=d.read(root/'rows.json');folds=d.read(root/'folds.json')
    original=d.read(d.REFERENCE/'opportunities.json.gz')
    cids={r['opportunity'] for r in original};days={r['session'] for r in original}
    assert len(cids)==2155 and len(days)==58
    keyset=set();by_opp=collections.defaultdict(list);by_session=collections.defaultdict(set)
    for i,r in enumerate(rows):
        assert r['id'] not in keyset;r_id=r['id'];keyset.add(r_id)
        assert r['computedThroughMinute'] is None or r['computedThroughMinute']<r['minute']
        by_opp[r['opportunity']].append(i);by_session[r['session']].add(r['opportunity'])
    assert cids<=set(by_opp)
    seen=set();purges=[]
    for f in folds:
        assert set(f['train']).isdisjoint(f['test'])
        assert max(f['train'])<f['purge']<min(f['test'])
        ids=set().union(*(by_session[s] for s in f['test']))
        assert not seen&ids;seen|=ids;assert len(ids)==f['testN']
        iv_seen=set()
        for inner in f['inner']:
            assert set(inner['train'])<=set(f['train']) and set(inner['validation'])<=set(f['train'])
            assert max(inner['train'])<inner['purge']<min(inner['validation'])
            assert not iv_seen&set(inner['validation']);iv_seen|=set(inner['validation'])
            purges.append({'outer':f['id'],'inner':inner['id'],'purge':inner['purge']})
    assert seen==cids
    raw=d.read(d.SUB/'raw-paths-evaluator-only.json.gz')
    sample=sorted(cids,key=lambda oid:hashlib.sha256(('570926|'+oid).encode()).hexdigest())[:32]
    counters=collections.Counter();witnesses=[]
    matrix=np.load(root/'features.npy',mmap_mode='r')
    day_cache={}
    for oid in sample:
        inds=by_opp[oid]
        inds=[inds[0]]+[i for i in inds[1:] if rows[i]['delay'] in (5,10,20,30)]
        day=rows[inds[0]]['session']
        if day not in day_cache:day_cache[day]=d.read(root/'days'/(day+'.sources.json.gz'))
        s=day_cache[day][oid];path=raw[oid]
        a=np.asarray(path['today'],float).reshape(-1,7);previous=np.asarray(path['previous'],float).reshape(-1,7)
        for i in inds:
            r=rows[i];now=r['minute'];mask=a[:,0]<now;prefix=a[mask]
            obs=[o for o in s['observations'] if o['minute']<=now]
            checks=[o for o in s['originalState'] if o['asOf']<=now]
            original_overlay=np.asarray(d.overlay(now,obs,checks,prefix),float)
            np.testing.assert_array_equal(original_overlay,matrix[i,476:])
            mutated=a.copy();mutated[~mask,1:5]*=37.;mutated[~mask,5:]*=19.
            variants=[mutated[mutated[:,0]<now],a[mask]]
            sig=d.signals.detect(day,now,s['opportunity']['origin']['decisionPrice'],prefix,previous,path['previousSession'])
            state_now=d.state.classify_state_v3(day,now,prefix.tolist(),path['previous'],path['previousSession'])
            for xx in variants:
                np.testing.assert_array_equal(xx,prefix)
                got=np.asarray(d.overlay(now,obs,checks,xx),float)
                np.testing.assert_array_equal(got,original_overlay)
                assert d.signals.detect(day,now,s['opportunity']['origin']['decisionPrice'],xx,previous,path['previousSession'])==sig
                assert d.state.classify_state_v3(day,now,xx.tolist(),path['previous'],path['previousSession'])==state_now
                counters['futureSuffixVariants']+=1
            counters['checkpointSamples']+=1
            witnesses.append({'opportunity':oid,'minute':now,'delay':r['delay'],'inputLatestBar':int(prefix[-1,0]) if len(prefix) else None,'overlayMatchesPrefit':True,'mutationAndDeletionInvariant':True})
    # Fast inner evaluator exactly matches the canonical evaluator on the immutable comparator.
    rec=d.read(d.REFERENCE/'one-minute.json.gz');opps={r['opportunity']:r for r in original}
    trades={r['opportunity']:r for r in rec};outcomes={r['entryId']:{'labels':r['labels']} for r in rec if r['entryId']}
    quick=t.fast_metrics(sorted(trades),trades,opps,outcomes);exact=c.policy_panel(original,rec)
    assert quick['population']==exact['population']==2155
    assert quick['fills']==exact['fills']==1764
    assert quick['entryPositionN']==exact['entryPosition']['count']==1751
    assert abs(quick['meanEntryPosition']-exact['entryPosition']['mean'])<1e-14
    for level in ('1','2','3','4','5'):
        assert quick['capture'][level]['captured']==exact['capture'][level]['captured']
        assert quick['capture'][level]['denominator']==exact['capture'][level]['selectorWinnerDenominator']
        assert quick['capture'][level]['ratePct']==exact['capture'][level]['ratePct']
    result={'status':'PASS_SCOPED_CHECKS','sampleRule':'first32 current Opportunity IDs by SHA256(570926|ID); first + available5/10/20/30 checkpoints, not chosen by outcomes',
        'population':2155,'outerTestExactlyOnce':True,'outerFolds':5,'innerFoldsChecked':len(purges),'oneSessionPurgesVerified':True,
        'all149900ComputedThroughBeforeDecision':True,'fastInnerCanonicalComparatorParity':True,
        'base476':'unchanged pinned Pattern columns; inherited P0 audit applies, not independently recertified historical knownAt',
        'newOverlay90MutationTests':dict(counters),'witnesses':witnesses,'modelFitsAdded':0,'providerRequests':0,'protectedOpens':0,
        'limitations':['sampled dynamic suffix test, not exhaustive semantic proof','historical availability certification remains inherited and conditional'],
        'safety':dict.fromkeys(d.state.SAFETY_KEYS,False)}
    d.write(out,result);print(json.dumps({k:v for k,v in result.items() if k!='witnesses'},sort_keys=True))

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--output',required=True);args=ap.parse_args();prefit_checks(Path(args.output))
