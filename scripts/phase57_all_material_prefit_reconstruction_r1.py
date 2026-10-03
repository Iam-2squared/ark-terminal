"""One-shot prefit reconstruction. Frozen policies; no learned fits/labels."""
from __future__ import annotations
import collections,gzip,hashlib,json,os,time
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
import numpy as np
from scripts import phase57_entry_pattern_v2 as pattern
from scripts import phase57_entry_timing_signals as signals
from scripts import phase57_state_v3_9pattern_entry_v1 as state
from scripts import phase57_drop_pull_1m_state_recheck_v1 as one
from scripts import phase57_state_conditioned_signal_entry_v1 as metrics
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'docs/evidence/phase57-entry-pattern-v2/ci-result/substrate'
OUT=ROOT/'artifacts/all-material-r1-prefit'
POLICY=metrics.read_json(ROOT/'docs/evidence/phase57-state-v3-9pattern-entry-v1/POLICY_LOCK.json')

def canonical_hash(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()

def generate(item):
    oid,day,start,selector,path=item
    a=np.asarray(path['today'],float).reshape(-1,7)
    prev=np.asarray(path['previous'],float).reshape(-1,7)
    grid=signals.comparison_grid(day,start)
    obs=[]; checks=[]
    for t in signals.census_grid(day,start):
        delay=pattern.elapsed(day,start,t)
        if delay>30:continue
        prefix=pattern.closed(a,t)
        z=signals.detect(day,t,selector,prefix,prev,path.get('previousSession'))
        z.update(opportunity=oid,session=day,delay=delay,comparisonEligible=t in grid)
        obs.append(z)
        if delay%5==0:
            st=state.classify_state_v3(day,t,prefix.tolist(),path['previous'],path.get('previousSession'))
            st.update(opportunity=oid,session=day,delay=delay,inputTodayPrefixRows=len(prefix),inputPreviousRows=len(prev))
            checks.append(st)
    assert obs and obs[0]['delay']==0
    assert checks and checks[0]['delay']==0
    use,violations=one._classify_target_every_minute(oid,day,obs,path) if checks[0]['state'] in one.TARGET_INITIAL_STATES else (checks,0)
    assert violations==0
    intent=state.frozen_intent(oid,obs,use,POLICY)
    return oid,obs,checks,intent

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    p=metrics.read_json(ROOT/'docs/evidence/phase57-entry-pattern-v2/protocol.json')
    meta=metrics.read_json(SOURCE/'opportunities.json.gz')
    paths=metrics.read_json(SOURCE/'raw-paths-evaluator-only.json.gz')
    allowed=set(p['fit']+p['selection']+p['evaluation'])
    safe=[(o['id'],o['session'],pattern.old.minute(o['origin']['decisionTimestamp']),o['origin']['decisionPrice'],paths[o['id']]) for o in meta if o['session'] in allowed]
    del paths,meta
    current={o for o,d,_,_,_ in safe if d in p['evaluation']}
    assert len(current)==2155 and len(safe)==5021
    saved_obs={}
    src=ROOT/'docs/evidence/phase57-entry-timing-signal-census-v1/measurement/minute-census'
    for f in sorted(src.glob('*.json.gz')):
        for r in metrics.read_json(f):
            if r['delay']<=30:saved_obs[(r['opportunity'],r['minute'])]=r
    saved_checks=metrics.read_json(ROOT/'docs/evidence/phase57-state-v3-9pattern-entry-v1/measurement/state-checkpoints.json.gz')
    saved_checks={(r['opportunity'],r['asOf']):r for r in saved_checks}
    intents={};nobs=nstate=0;results={};start_clock=time.monotonic()
    with ProcessPoolExecutor(max_workers=2) as pool:
        for count,(oid,obs,checks,intent) in enumerate(pool.map(generate,safe,chunksize=5),1):
            if oid in current:
                for r in obs:
                    assert r==saved_obs[(oid,r['minute'])],('SIGNAL_PARITY',oid,r['minute'])
                    nobs+=1
                for r in checks:
                    assert r==saved_checks[(oid,r['asOf'])],('STATE_PARITY',oid,r['asOf'])
                    nstate+=1
            intents[oid]=intent
            results[oid]={'minuteRows':obs,'stateRows':checks,'intent':intent}
            if count%250==0:print(json.dumps({'done':count,'total':len(safe),'seconds':round(time.monotonic()-start_clock,1),'signalParity':nobs,'stateParity':nstate}),flush=True)
    assert nobs==len(saved_obs) and nstate==len(saved_checks)
    metrics.write_gzip_json(OUT/'causal-sources.json.gz',results)
    receipt={'status':'CAUSAL_RECONSTRUCTION_PARITY_PASS','population':len(safe),'currentPopulation':len(current),
        'currentSignalRowsExact':nobs,'currentStateRowsExact':nstate,
        'currentIntentsSHA256':canonical_hash({k:intents[k] for k in sorted(current)}),
        'allIntentsSHA256':canonical_hash(intents),'sourceSHA256':metrics.sha256(SOURCE/'raw-paths-evaluator-only.json.gz'),
        'causalSourcesSHA256':metrics.sha256(OUT/'causal-sources.json.gz'),
        'modelFits':0,'newTrainingLabelsRead':0,'providerRequests':0,'protectedDataOpened':0}
    metrics.write_json(OUT/'causal-reconstruction-receipt.json',receipt)
    print(json.dumps(receipt,sort_keys=True),flush=True)

if __name__=='__main__':main()
