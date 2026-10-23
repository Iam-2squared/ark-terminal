"""Frozen Development generator and independent fresh replay. No provider access."""
from __future__ import annotations
import argparse,collections,csv,datetime as dt,gzip,hashlib,json,multiprocessing,os,pickle,platform,sys,time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from phase57_state_v2.common import r,ROOT,SAFETY,encoded,clean,digest,observation
from phase57_state_v2.historical import g,admit,split_task,prefix_at,verify_spec
from phase57_state_v2.now import now_state_reference_v2
from phase57_state_v2.future import future_resolution_v2
from phase57_state_v2.independent import verify_core

CHANGE_CODES=frozenset(('IDENTITY_PRESERVED','STATUS_SCHEMA_REPRESENTATION','EXPLICIT_NEGATIVE_STRUCTURE',
 'PIVOT_EVIDENCE_INSUFFICIENT','EXPLICIT_EMPTY_PHASE','INHERITED_INPUT_PREREQUISITE_FAILURE',
 'FUTURE_ASSISTED_TO_CAUSAL_PIVOT_CUTOFF','RETROSPECTIVE_EFFECTIVE_TIME_REPLAY','VALUES_PRESERVED'))

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def readgz(p):
    with gzip.open(p,'rt',encoding='utf-8') as f:
        for line in f:yield json.loads(line)
def writegz(p,records):
    h=hashlib.sha256()
    with Path(p).open('xb') as file,gzip.GzipFile(fileobj=file,mode='wb',mtime=0,filename='') as gz:
        for record in records:
            data=encoded(record);gz.write(data);h.update(data)
    return h.hexdigest()
def project_v1(old):
    a=old['reference'];st=a['state']
    return {'direction':a['descriptors']['direction'] if a['descriptors'] else None,
      'structure':(st.get('structure') or {}).get('kind'),'phase':st.get('phase',[]),
      'structureStatus':st['identificationStatus'],'lateConfirmedPivotN':a['futureConfirmation']['lateConfirmedPivotN']}
def reasons_for(old,now,effective_prefix=None):
    codes=['IDENTITY_PRESERVED','STATUS_SCHEMA_REPRESENTATION']
    ns=now['structure'];np=now['phase']
    if ns['status']=='NOT_EVALUATED':codes.append('INHERITED_INPUT_PREREQUISITE_FAILURE')
    elif ns['status']=='INSUFFICIENT':codes.append('PIVOT_EVIDENCE_INSUFFICIENT')
    elif ns['value']=='NONE':codes.append('EXPLICIT_NEGATIVE_STRUCTURE')
    if np['status']=='DEFINED' and np['value']==[]:codes.append('EXPLICIT_EMPTY_PHASE')
    changed=(old['structure']!=(None if ns['value'] in (None,'NONE') else ns['value']) or old['phase']!=(np['value'] or []))
    if changed:
        if effective_prefix is None:raise ValueError('MISSING_RETROSPECTIVE_COUNTERFACTUAL')
        causal=(None if ns['value'] in (None,'NONE') else ns['value'],np['value'] or [])
        target=(old['structure'],old['phase'])
        bridge=(effective_prefix['structure'],effective_prefix['phase'])
        if causal!=bridge:codes.append('RETROSPECTIVE_EFFECTIVE_TIME_REPLAY')
        if bridge!=target:
            if old['lateConfirmedPivotN']<=0:raise ValueError('UNEXPLAINED_HORIZON_CONFIRMATION_CHANGE')
            codes.append('FUTURE_ASSISTED_TO_CAUSAL_PIVOT_CUTOFF')
    else:codes.append('VALUES_PRESERVED')
    return codes

def work_day(payload):
    day,tasks,out_s,v1_s,reverse,replay_s=payload
    out=Path(out_s);es=g.ends_for(day)
    olds={(z['opportunity'],z['asOfJST']):z for z in readgz(Path(v1_s)/'raw'/(day+'.jsonl.gz'))}
    if len(olds)!=sum(1 for _ in readgz(Path(v1_s)/'raw'/(day+'.jsonl.gz'))):raise ValueError('V1_DUPLICATE')
    previous_now={}
    previous_future={}
    if replay_s:
        previous_now={(z['opportunityId'],z['checkpointAsOf']):z for z in readgz(Path(replay_s)/'now_state_reference_v2'/(day+'.jsonl.gz'))}
        previous_future={(z['opportunityId'],z['checkpointAsOf']):z for z in readgz(Path(replay_s)/'future_resolution_v2'/(day+'.jsonl.gz'))}
    allnow=[];allfuture=[];changes=[];stats=collections.Counter();seen=set();coverage=[]
    for task in sorted(tasks,key=lambda x:x['id'],reverse=reverse):
        identity,context=split_task(task);bs=task['today'];grid=r.grid(task['selectorMinute'],es)['checkpoints']
        seq=list(enumerate(grid))
        if reverse:seq.reverse()
        for k,t in seq:
            ii={**identity,'elapsedActiveMinutesFromSelector':k*5}
            prefix=prefix_at(bs,t)
            if replay_s:
                # Change every suffix price and activity without inspecting outcomes.
                suffix=tuple(r.Bar(b.end,b.o+1000,b.h+1000,b.l+1000,b.c+1000,b.volume,b.value,b.available_at) for b in bs if b.end>t)
                mutated=prefix+suffix
                if prefix_at(mutated,t)!=prefix or prefix_at(prefix,t)!=prefix:raise ValueError('SUFFIX_ROUTING_LEAK')
                prefix=prefix_at(mutated,t)
                stats['suffixMutationChecks']+=1;stats['suffixRemovalChecks']+=1
            n=now_state_reference_v2(prefix=prefix,ends=es,asof=t,identity=ii,context=context)
            cutoff=([e for e in es if e>t][:10] or [t])[-1]
            f=future_resolution_v2(bounded_bars=prefix_at(bs,cutoff),ends=es,asof=t,identity=ii,context=context)
            key=(identity['opportunityId'],n['checkpointAsOf'])
            if key in seen or key not in olds:raise ValueError('KEY_DUPLICATE_OR_MISMATCH')
            old=olds[key]
            if (old['session'],old['symbol'],old['selectorAt'],old['elapsedActiveMinutes'])!=(day,ii['securityId'],ii['selectorAt'],k*5):raise ValueError('KEY_FIELD_MISMATCH')
            seen.add(key)
            v1=project_v1(old);fs=f['adjudicatedStructureAtT']['value'];fp=f['adjudicatedPhaseAtT']['value'] or []
            if (None if fs in (None,'NONE') else fs)!=v1['structure'] or fp!=v1['phase']:raise ValueError('FROZEN_FUTURE_VALUES_CHANGED')
            if n['direction']['value']!=v1['direction']:raise ValueError('DIRECTION_VALUES_CHANGED')
            # No production semantic helper is used by the independent projector.
            witness=r.snapshot(prefix,es,t,context['scale'].get('scale'))
            verify_core(n,witness,context['scale']['status'])
            stats['independentCoreProjectionMatches']+=1
            if replay_s:
                if encoded(n)!=encoded(previous_now[key]):raise ValueError('NOW_FRESH_REPLAY_MISMATCH')
                if encoded(f)!=encoded(previous_future[key]):raise ValueError('FUTURE_REPLAY_MISMATCH')
                stats['freshNowReplayMatches']+=1;stats['futureReplayMatches']+=1
            # Separate a historical effective-time replay effect from genuinely
            # new confirmations after t. They are not equivalent.
            bridge=None
            ns=n['structure']['value'];np=n['phase']['value'] or []
            if (None if ns in (None,'NONE') else ns,np)!=(v1['structure'],v1['phase']):
                s=context['scale'].get('scale')
                ps=r.pivots(prefix,s) if s is not None else []
                counterfactual=r._snapshot(list(prefix),list(es),t,s,ps,True)['state']
                bridge={'structure':(counterfactual.get('structure') or {}).get('kind'),'phase':counterfactual.get('phase',[]),'allPivotConfirmationsAtOrBeforeT':all(p['confirmedAt']<=t for p in ps)}
            codes=reasons_for(v1,n,bridge)
            if not set(codes)<=CHANGE_CODES:raise ValueError('CHANGE_REASON_ENUM')
            changes.append({'opportunityId':key[0],'checkpointAsOf':key[1],'v1ArtifactMode':'ORACLE_REFERENCE',
                'v1':v1,'retrospectivePrefixBridge':bridge,'v2Now':{axis:n[axis] for axis in ('direction','structure','phase')},
                'v2Future':{'structure':f['adjudicatedStructureAtT'],'phase':f['adjudicatedPhaseAtT']},'changeReasonCodes':codes})
            # Independently check the reason predicate using serialized values.
            if (bool(set(codes)&{'FUTURE_ASSISTED_TO_CAUSAL_PIVOT_CUTOFF','RETROSPECTIVE_EFFECTIVE_TIME_REPLAY'})) != (v1['structure']!=(None if n['structure']['value'] in ('NONE',None) else n['structure']['value']) or v1['phase']!=(n['phase']['value'] or [])):raise ValueError('EXPLANATION_RESIDUAL')
            price=task['selectorPrice'];priceband='<500' if price<500 else '500-999' if price<1000 else '1000-2999' if price<3000 else '3000-9999' if price<10000 else '>=10000'
            band='OPEN_0900_1000' if t<600 else 'AM_1000_1130' if t<=690 else 'PM_EARLY_1230_1400' if t<840 else 'PM_LATE_1400_CLOSE'
            row={'opportunityId':key[0],'checkpointAsOf':key[1],'session':day,'symbol':ii['securityId'],'timeBand':band,'priceBand':priceband,'scaleStatus':context['scale']['status'],'observation':n['observationQuality']['window']['status'],'directionStatus':n['direction']['status'],'direction':n['direction']['value'],'structureStatus':n['structure']['status'],'structure':n['structure']['value'],'phaseStatus':n['phase']['status'],'phase':n['phase']['value'],'futureStructureStatus':f['adjudicatedStructureAtT']['status'],'futureStructure':fs,'futureResolutionStatus':f['resolutionStatus'],'futureCensorFlags':f['censorFlags'],'unknownMissingCause':bool(n['observationQuality']['missingCauseCodes']),'oldStructureStatus':v1['structureStatus'],'oldStructure':v1['structure'],'changeCodes':codes}
            coverage.append(row);allnow.append(n);allfuture.append(f);stats['rows']+=1
    if seen!=set(olds):raise ValueError('ROW_LOSS_OR_GRID_CHANGE')
    order=lambda z:(z['opportunityId'],z['checkpointAsOf'])
    hs={}
    for dirname,records in [('now_state_reference_v2',allnow),('future_resolution_v2',allfuture),('transitions',changes),('coverage_rows',coverage)]:
        records.sort(key=order)
        hs[dirname]=writegz(out/dirname/(day+'.jsonl.gz'),records)
    return {'session':day,'opportunityN':len(tasks),'stats':dict(stats),'canonicalHashes':hs}

def main():
    pa=argparse.ArgumentParser();pa.add_argument('--sources',required=True);pa.add_argument('--v1',required=True);pa.add_argument('--output',required=True);pa.add_argument('--workers',type=int,default=2);pa.add_argument('--reverse',action='store_true');pa.add_argument('--replay');pa.add_argument('--admitted-cache');args=pa.parse_args()
    out=Path(args.output);out.mkdir(parents=True,exist_ok=False);st=time.monotonic()
    for d in ('now_state_reference_v2','future_resolution_v2','transitions','coverage_rows','verified_spec'): (out/d).mkdir()
    pins=verify_spec(out/'verified_spec');(out/'pin-recovery.json').write_bytes(encoded(pins))
    if args.admitted_cache:
        cache=Path(args.admitted_cache);report=g.read(cache/'admission.json')
        for name,path in g.source_paths(ROOT,args.sources).items():
            if sha(path)!=report['sourcePins'][name]:raise ValueError('CACHED_ADMISSION_INPUT_CHANGED')
        # Cache is local generated material, never an untrusted downloaded pickle.
        with (cache/'tasks.pkl').open('rb') as file:tasks=pickle.load(file)
        (out/'admission.json').write_bytes((cache/'admission.json').read_bytes())
    else:tasks,report=admit(args.sources,out)
    byday=collections.defaultdict(list)
    for task in tasks:byday[task['session']].append(task)
    codehashes={str(p.relative_to(ROOT)):sha(p) for p in sorted((ROOT/'scripts/phase57_state_v2').glob('*.py'))}
    codehashes['scripts/run_phase57_state_v2.py']=sha(Path(__file__))
    launch={'recordedAtJST':dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).isoformat(),'workingCodeSHA256':codehashes,'workingCodeSetHash':digest(codehashes),'codeBaseCommit':'44b1e55a0ad8721df8bec4013e60e735ac698b74','runtime':sys.version,'platform':platform.platform(),'workerN':args.workers,'reverseOrder':args.reverse,'sourcePins':report['sourcePins'],'specSHA256':pins[0]['effectiveSHA256'],'safety':SAFETY,'protectedDataOpened':0,'providerRequests':0,'status':'GENERATION_STARTED_NOT_ACCEPTED'}
    (out/'launch.json').write_bytes(encoded(launch))
    payloads=[(day,byday[day],str(out),args.v1,args.reverse,args.replay) for day in sorted(byday,reverse=args.reverse)]
    results=[]
    with ProcessPoolExecutor(max_workers=args.workers,mp_context=multiprocessing.get_context('fork')) as pool:
        for result in pool.map(work_day,payloads,chunksize=1):
            results.append(result);print(result['session'],result['stats']['rows'],'seconds',round(time.monotonic()-st,2),flush=True)
    results.sort(key=lambda x:x['session']);total=collections.Counter()
    for x in results:total.update(x['stats'])
    if total['rows']!=77214 or sum(x['opportunityN'] for x in results)!=2155:raise ValueError('ROW_COUNTS')
    canonical={}
    for dirname in ('now_state_reference_v2','future_resolution_v2','transitions','coverage_rows'):
        h=hashlib.sha256()
        for day in sorted(byday):
            with gzip.open(out/dirname/(day+'.jsonl.gz'),'rb') as f:
                for block in iter(lambda:f.read(1048576),b''):h.update(block)
        canonical[dirname]=h.hexdigest()
    summary={'status':'GENERATED_CANDIDATE_NOT_ACCEPTED','opportunityN':2155,'checkpointN':77214,'stats':dict(total),'dayN':len(results),'canonicalHashes':canonical,'wallSeconds':time.monotonic()-st,'safety':SAFETY,'protectedDataOpened':0,'providerRequests':0,'knownLimitations':g.QUALITY,'days':results}
    if args.replay:
        first=g.read(Path(args.replay)/'summary.json')
        if canonical!=first['canonicalHashes']:raise ValueError('CANONICAL_OUTPUT_REPLAY_HASH')
        summary['doubleReplayHashesMatch']=True
    (out/'summary.json').write_bytes(encoded(summary))
    paths=sorted(p for p in out.rglob('*') if p.is_file());manifest={str(p.relative_to(out)):sha(p) for p in paths}
    (out/'manifest.json').write_bytes(encoded(manifest))
    print(json.dumps({k:v for k,v in summary.items() if k!='days'},indent=2),flush=True)
if __name__=='__main__':main()
