"""Pairability repair: immutable memberships, separated endpoint/path observability."""
from __future__ import annotations
import argparse,collections,csv,datetime as dt,hashlib,json,math,statistics
from pathlib import Path
import numpy as np
from scripts import phase57_selector_path_anatomy as a

ROOT=a.ROOT
BASE=ROOT/'docs/evidence/phase57-selector-pairability-repair-v2'
V1=a.BASE/'measurement'
P=BASE/'protocol-final.json'
H=(*a.H,'SESSION_END')
read,write,sha=a.read,a.write,a.sha

def groups():
    membership=read(a.MEMBERSHIP)
    arms={};events={}
    for arm,label in zip(a.ARMS,['selector','random','momentum']):
        rows=read(V1/f'{label}-path-ledger.json.gz')['events']
        assert [r['selectorEventId'] for r in rows]==membership['arms'][arm]
        arms[arm]=membership['arms'][arm]
        for r in rows:events[r['selectorEventId']]=r
    return arms,events

def boundary(stamp,h):
    t=a.old.timestamp(stamp);m=t.hour*60+t.minute;close=900 if str(t.date())<'2024-11-05' else 930
    if h=='SESSION_END':return 'ELIGIBLE' if (540<=m<690 or 750<=m<close) else 'NO_REGULAR_ENTRY_SESSION'
    if m+h>close:return 'SESSION_END'
    if 690<=m<750 or m<690<m+h:return 'LUNCH_BREAK'
    if m<540:return 'BEFORE_SESSION'
    return 'ELIGIBLE'

def phase_a(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=False);a.audit(V1)
    arms,events=groups();economic={r['selectorEventId']:r for r in read(a.old.BASE/'measurement/event-ledger.json.gz')}
    selector_paths={r['selectorEventId']:r for r in read(a.old.FROZEN_PATHS)['events']}
    masks={};grouped={};csvrows=[];summary={};reasons={};features={}
    for arm,ids in arms.items():
        grouped[arm]=collections.defaultdict(list)
        for i in ids:grouped[arm][events[i]['decisionTimestamp']].append(i)
        assert len(grouped[arm])==760 and all(len(v)==5 for v in grouped[arm].values())
    stamps=sorted(grouped[a.ARMS[0]])
    assert all(sorted(v)==stamps for v in grouped.values())
    for h in H:
        key=str(h);masks[key]={};reasons[key]={};summary[key]={};features[key]={}
        for arm,ids in arms.items():
            masks[key][arm]={};counts=collections.Counter();feature={}
            for field in ['volatilityStratum','priceBand','liquidityBucket','segment','sessionHalf']:
                feature[field]=collections.defaultdict(lambda:collections.Counter())
            for stamp in stamps:
                selected=grouped[arm][stamp];obs=[i for i in selected if events[i]['outcomes'][key]['status']=='AVAILABLE']
                known_endpoint=[];unknown_endpoint=[];detail=[]
                for i in selected:
                    e=events[i];reason=e['outcomes'][key]['status'];counts[reason]+=1
                    ep='NOT_PERSISTED_AT_THIS_HORIZON'
                    if isinstance(h,int) and h<=60:
                        old=economic[i]['delays']['0'];ep=boundary(stamp,h)
                        if ep=='ELIGIBLE':ep=old['selectorTerminal'][key]['status'] if old['status']=='AVAILABLE' else old['status']
                        if ep=='AVAILABLE':known_endpoint.append(i)
                    else:unknown_endpoint.append(i)
                    regular=boundary(stamp,h)
                    record={'symbol':e['symbol'],'id':i,'pathStatus':reason,'endpointStatus':ep,'calendar':regular}
                    if i in selector_paths:
                        path=selector_paths[i];decision=a.old.timestamp(stamp)
                        end=decision.replace(hour=15,minute=0 if e['sessionDate']<'2024-11-05' else 30) if h=='SESSION_END' else decision+dt.timedelta(minutes=h)
                        expected=a.regular_slots(decision,end) if regular=='ELIGIBLE' else []
                        bystart={a.old.timestamp(b['start']):b for b in path['future']}
                        record.update(expectedSlots=len(expected),missingSlots=[t.isoformat() for t in expected if t not in bystart or bystart[t]['missing']],
                            barAvailabilitySource='PINNED_SELECTOR_PROJECTION')
                    else:record.update(expectedSlots=None,missingSlots=None,barAvailabilitySource='V1_PATH_STATUS_ONLY_EXACT_SLOT_LIST_NOT_PERSISTED')
                    detail.append(record)
                    for field in feature:
                        f=str(e['context'][field]);feature[field][f]['selected']+=1
                        if regular=='ELIGIBLE':
                            feature[field][f]['calendarEligible']+=1
                            feature[field][f]['pathObserved']+=int(reason=='AVAILABLE')
                            if ep!='NOT_PERSISTED_AT_THIS_HORIZON':feature[field][f]['endpointObserved']+=int(ep=='AVAILABLE')
                masks[key][arm][stamp]={'path':len(obs),'endpoint':None if unknown_endpoint else len(known_endpoint)}
                overlap={other:len(set(selected)&set(grouped[other][stamp])) for other in a.ARMS if other!=arm}
                csvrows.append({'session':stamp[:10],'timestamp':stamp,'arm':arm,'horizon':key,'originalCount':5,'observedPathCount':len(obs),'missingPathCount':5-len(obs),
                    'endpointObservedCount':None if unknown_endpoint else len(known_endpoint),'boundary':boundary(stamp,h),'originalTop5AndMissingReasons':json.dumps(detail,sort_keys=True),
                    'groupOverlap':json.dumps(overlap,sort_keys=True)})
            reasons[key][arm]=dict(counts);features[key][arm]={f:{k:dict(v) for k,v in cats.items()} for f,cats in feature.items()}
            summary[key][arm]={'pathRows':sum(v['path'] for v in masks[key][arm].values()),'pathCountHistogram':dict(collections.Counter(v['path'] for v in masks[key][arm].values())),
                'endpointRows':None if h in [90,120,'SESSION_END'] else sum(v['endpoint'] for v in masks[key][arm].values()),
                'endpointCountHistogram':None if h in [90,120,'SESSION_END'] else dict(collections.Counter(v['endpoint'] for v in masks[key][arm].values()))}
        summary[key]['pairs']={}
        for baseline in a.ARMS[1:]:
            x,y=masks[key][a.ARMS[0]],masks[key][baseline]
            joint=collections.Counter((x[t]['path'],y[t]['path']) for t in stamps)
            summary[key]['pairs'][baseline]={'pathJointCounts':{f'{i}|{j}':v for (i,j),v in sorted(joint.items())},'pathFull5':joint.get((5,5),0),
                'endpointFull5':None if h in [90,120,'SESSION_END'] else sum(x[t]['endpoint']==y[t]['endpoint']==5 for t in stamps),
                'endpointBothRepresented':None if h in [90,120,'SESSION_END'] else sum(x[t]['endpoint']>0 and y[t]['endpoint']>0 for t in stamps)}
    write(out/'02_missingness_summary.json',{'role':'AVAILABILITY_ONLY_NO_NEW_RETURN_AGGREGATION','sessions':76,'timestamps':760,'originalRowsPerArm':3800,
        'rootCauses':['Calendar excludes lunch and late decisions identically in all arms.','Full-path observability intersects every required 5m slot.','Requiring all five original members in both arms compounds row-level missingness into a ten-row conjunction.','The sets of complete Top5 timestamps do not overlap at 60/90/120/session end for Selector and Random.'],
        'unresolvedPhysicalCause':'Absent normalized slot alone cannot distinguish no trades, halt, provider omission or archive omission; never label it confirmed provider outage.',
        'futureAvailabilityMembershipUsed':False,'membershipParity':'Exact identity with prior deterministic causal eligible-universe reconstruction, verified by v1 CI and pinned ledgers.',
        'outcomeDependentMissingness':'Cannot establish MAR. PIT strata show selection/observability differences; missing outcomes are not identified.',
        'asymmetricReconstruction':'No algorithmic asymmetry: all arms same pinned 5m projector and hash-verified source; exact whole-union path parity was enforced in v1.',
        'barSlotEvidenceLimitation':'Exact slots currently available for saved Selector paths; baseline per-slot masks will be regenerated in v2 CI from the same pinned cache, without changing membership.'})
    write(out/'03_pairability_by_horizon.json',summary)
    with (out/'04_pairability_by_timestamp.csv').open('x',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(csvrows[0]));w.writeheader();w.writerows(csvrows)
    write(out/'05_missing_reason_breakdown.json',reasons);write(out/'06_group_observability_comparison.json',features)
    print(json.dumps({h:v['pairs']['RANDOM_TOP5'] for h,v in summary.items()}))

def load_protocol():
    p=read(P);lock=read(BASE/'08_protocol_v2_final_hash.json')
    assert sha(P)==lock['protocolSHA256']
    assert p['id']=='PHASE57_FROZEN_SELECTOR_PAIRABILITY_REPAIR_V2'
    assert p['primary']['fullTop5Required'] is True
    assert p['primary']['minimumClusters']==38 and p['primary']['minimumPairedTimestamps']==76
    assert p['random']['repetitions']==1 and p['random']['seed']==20260919
    assert all(v is False for v in p['safety'].values())
    assert p['sealed']['newProviderRequests']==0 and not any(v for k,v in p['sealed'].items() if k!='newProviderRequests')
    for f,h in p['sourcePins'].items():assert sha(ROOT/f)==h,f
    return p

def end_target(stamp,h):
    t=a.old.timestamp(stamp)
    return t.replace(hour=15,minute=0 if str(t.date())<'2024-11-05' else 30) if h=='SESSION_END' else t+dt.timedelta(minutes=h)

def terminal(path,h):
    decision=a.old.timestamp(path['decisionTimestamp']);target=end_target(path['decisionTimestamp'],h)
    calendar=boundary(path['decisionTimestamp'],h) if h!='SESSION_END' else ('ELIGIBLE' if target>decision else 'SESSION_END')
    if calendar!='ELIGIBLE':return {'status':calendar,'calendarEligible':False}
    bars=a.old.materialize_path(path);entry=a.old.entry_at_or_after(bars,decision)
    expected=a.regular_slots(decision,target)
    if not expected:return {'status':'NO_REGULAR_BAR','calendarEligible':True}
    # Never skip an absent expected initial slot, even if a malformed projector omits its placeholder.
    if not bars or bars[0]['start']!=expected[0]:return {'status':'FIRST_EXPECTED_BAR_ABSENT','calendarEligible':True}
    if entry['status']!='AVAILABLE':return {'status':entry['status'],'calendarEligible':True}
    if a.old.timestamp(entry['timestamp'])>=target:return {'status':'NONPOSITIVE_HOLDING_WINDOW','calendarEligible':True}
    last=a.old.exact_exit(bars,target)
    if last['status']!='AVAILABLE':return {'status':last['status'],'calendarEligible':True}
    gross=a.old.trade_return(entry,last)
    return {'status':'AVAILABLE','calendarEligible':True,'gross':gross,'net':gross-.05,'entryTimestamp':entry['timestamp'],
        'exitTimestamp':target.isoformat(),'entryLatencyMin':(a.old.timestamp(entry['timestamp'])-decision).total_seconds()/60}

def session_means(rows,field):
    timestamps=collections.defaultdict(list)
    for r in rows:timestamps[r['decisionTimestamp']].append(r[field])
    days=collections.defaultdict(list)
    for stamp,vals in sorted(timestamps.items()):days[stamp[:10]].append(statistics.mean(vals))
    return {k:statistics.mean(v) for k,v in sorted(days.items())}

BLOCK={}
def cluster(values,family=1):
    r=a.cluster(values,family)
    vals=np.asarray(list(values.values()),float);n=len(vals)
    r['block5CI95']=[None,None]
    if n>=2:
        if n not in BLOCK:
            rng=np.random.default_rng(20260919);starts=rng.integers(0,n,size=(10000,math.ceil(n/5)))
            BLOCK[n]=((starts[:,:,None]+np.arange(5))%n).reshape(10000,-1)[:,:n]
        r['block5CI95']=np.quantile(vals[BLOCK[n]].mean(axis=1),[.025,.975]).tolist()
    return r

def rows_at(events,ids,h,dimension='terminal'):
    out=[]
    for i in ids:
        e=events[i];r=e[dimension][str(h)]
        if r['status']=='AVAILABLE':out.append({**r,'selectorEventId':i,'sessionDate':e['sessionDate'],'decisionTimestamp':e['decisionTimestamp'],'symbol':e['symbol']})
    return out

def stats(rows,field='net'):
    return {'rows':len(rows),'timestamps':len({r['decisionTimestamp'] for r in rows}),'distributionRowWeighted':a.dist([r[field] for r in rows]),
        'sessionTimestampEqual':cluster(session_means(rows,field))}

def pair(events,arms,h,baseline,mode='full5',dimension='terminal',cohort=None):
    selected={};groups={}
    for arm in [a.ARMS[0],baseline]:
        ids=arms[arm] if cohort is None else cohort[arm]
        selected[arm]=rows_at(events,ids,h,dimension);g=collections.defaultdict(list)
        for r in selected[arm]:g[r['decisionTimestamp']].append(r)
        groups[arm]=g
    x,y=groups[a.ARMS[0]],groups[baseline]
    stamps=sorted(x.keys()&y.keys())
    if mode=='full5':stamps=[t for t in stamps if len(x[t])==len(y[t])==5]
    left=[r for t in stamps for r in x[t]];right=[r for t in stamps for r in y[t]]
    metrics=['gross','net'] if dimension=='terminal' else ['gross','net','MFE','MAE','absMAE','balance','giveback']
    result={'mode':mode,'scope':'ORIGINAL_FULL5_COMPLETE_ENDPOINT_TIMESTAMPS' if mode=='full5' else 'OBSERVATION_CONDITIONAL_ORIGINAL_MEMBERS_ONLY',
        'dimension':dimension,'timestamps':len(stamps),'originalRowsPerArmAtPairedTimes':5*len(stamps),'selectorObservedRows':len(left),'baselineObservedRows':len(right),
        'selectorMissingRowsAtPairedTimes':5*len(stamps)-len(left),'baselineMissingRowsAtPairedTimes':5*len(stamps)-len(right),
        'timestampSHA256':a.digest(stamps),'selectorEventSHA256':a.digest([r['selectorEventId'] for r in left]),'baselineEventSHA256':a.digest([r['selectorEventId'] for r in right]),
        'selector':stats(left),'baseline':stats(right),'differences':{},'originalPopulationNotIdentified':True}
    for field in metrics:
        xx,yy=session_means(left,field),session_means(right,field);assert xx.keys()==yy.keys()
        result['differences'][field]=cluster({k:xx[k]-yy[k] for k in xx},7 if mode=='full5' and dimension=='terminal' and baseline==a.ARMS[1] and h!='SESSION_END' else 1)
    result['minimumSampleMet']=result['differences']['net']['clusters']>=38 and len(stamps)>=76
    result['directionalClaimAllowed']=False if mode!='full5' else result['minimumSampleMet']
    result['missingnessBiasResolved']=False
    return result

def score_analysis(directory):
    import pandas as pd
    out={'role':'OBSERVATION_CONDITIONAL_FULL_PIT_UNIVERSE_RANKS','newFitCalls':0,'horizons':{}}
    for h in [15,30,60,90,120]:
        f=pd.read_csv(Path(directory)/f'score-{h}.tsv',sep='\t',dtype={'sessionDate':str,'decisionTimeJst':str})
        x={'terminalRows':len(f),'completePathRows':int(f.MFE.notna().sum()),'deciles':{},'rankIC':{}}
        for d,g in f.groupby('scoreDecile',sort=True):
            x['deciles'][str(d)]={'n':len(g),'gross':a.dist(g.gross),'net':a.dist(g.gross-.05),'MFE':a.dist(g.MFE),'MAE':a.dist(g.MAE)}
        f['absMAE']=-f.MAE
        for outcome in ['gross','MFE','absMAE']:
            ic=[];c=f[f[outcome].notna()]
            for (day,t),g in c.groupby(['sessionDate','decisionTimeJst'],sort=True):
                xx=g.savedV1Score.rank(method='average').to_numpy();yy=g[outcome].rank(method='average').to_numpy()
                if len(xx)>1 and xx.std()>0 and yy.std()>0:ic.append({'sessionDate':day,'value':float(np.corrcoef(xx,yy)[0,1])})
            x['rankIC'][outcome]={'rows':len(c),'timestamps':len(ic),'cluster':cluster(a.by_session(ic,'value'))}
        means=[x['deciles'][str(d)]['net']['mean'] for d in range(1,11)]
        x['netDecilesMonotoneNondecreasing']=all(y>=z for z,y in zip(means,means[1:]))
        out['horizons'][str(h)]=x
    return out

def audit(directory=None):
    p=load_protocol()
    if directory:
        d=Path(directory);manifest=read(d/'source-manifest.json')
        assert manifest['protocolSHA256']==sha(P)
        for f,h in manifest['outputs'].items():assert sha(d/f)==h,f
        for f,h in manifest['code'].items():assert sha(ROOT/f)==h,f
        assert all(v is False for v in manifest['safety'].values())
        assert manifest['providerRequests']==manifest['newFitCalls']==0
        x=read(d/'11_selector_vs_random_paired.json')
        for h,v in x['primaryFull5'].items():
            assert v['selectorObservedRows']==v['baselineObservedRows']==5*v['timestamps']
        ledger=read(d/'endpoint-ledger.json.gz')
        assert all(len(v)==3800 for v in ledger['arms'].values())
        for arm,ids in ledger['arms'].items():assert ids==read(a.MEMBERSHIP)['arms'][arm]
        for name,values in x['commonEndpointConditional'].items():
            assert len({v['selectorEventSHA256'] for v in values.values()})==1
            assert len({v['baselineEventSHA256'] for v in values.values()})==1
    print('PAIRABILITY_V2_AUDIT_PASS')

def diagnose(primary,conditional,score,context,arms,tails):
    informative=[h for h,r in primary.items() if r['minimumSampleMet']]
    positive=[h for h in informative if primary[h]['differences']['net']['simultaneousCI95'][0]>0]
    selector_context=[context[i] for i in arms[a.ARMS[0]]]
    prior=statistics.median(r['momentum30Pct'] for r in selector_context)
    high=sum(r['volatilityStratum']=='HIGH' for r in selector_context)/len(selector_context)
    negative_ic=[h for h,r in score['horizons'].items() if r['rankIC']['gross']['cluster']['clusterCI95'][1] is not None and r['rankIC']['gross']['cluster']['clusterCI95'][1]<0]
    monotone=any(v['netDecilesMonotoneNondecreasing'] for v in score['horizons'].values())
    tags=['I_INCONCLUSIVE_FULL_POPULATION_ECONOMIC_EDGE']
    if not monotone:tags.append('G_SCORE_NOT_ECONOMICALLY_ORDERED')
    full=tails[a.ARMS[0]]['30'];fat=full['full']['mean']>0 and all(full[k]['remaining']['mean']<=0 for k in ['top1Excluded','top5Excluded'])
    if fat:tags.append('F_FAT_TAIL_WINNER_DEPENDENCE_DESCRIPTIVE')
    # Positive gross rebound is described separately from after-cost economic edge.
    c=conditional['30']['selector']['distributionRowWeighted']['mean']
    if prior<0 and c is not None and c+.05>0:tags.append('E_REVERSAL_REBOUND_ASSOCIATION_DESCRIPTIVE')
    design=not monotone and (high>.5 or fat)
    return {'id':load_protocol()['id'],'tags':tags,'informativePrimaryHorizons':informative,'positiveAdjustedPrimaryHorizons':positive,
        'fullPopulationEconomicEdge':'NOT_IDENTIFIED_WITH_MISSING_ENDPOINTS','negativeTerminalICHorizons':negative_ic,
        'highVolSelectionRate':high,'prior30MedianPct':prior,'designOnlySupported':design,
        'nextStep':'Review Economic Selector v2 design and data-observability contract; implementation requires a separate user decision.' if design else 'Review observability and measurement evidence before further research.',
        'noTrainingOrOptimizationStarted':True,'stop':True}

def availability_csv(out,events,arms,raw):
    rawmap={p['selectorEventId']:p for p in raw['events']}
    bar_maps={i:{b['start']:b for b in a.old.materialize_path(p)} for i,p in rawmap.items()}
    grouped={arm:collections.defaultdict(list) for arm in arms}
    for arm,ids in arms.items():
        for i in ids:grouped[arm][events[i]['decisionTimestamp']].append(i)
    records={}
    for arm,g in grouped.items():
        for stamp,ids in sorted(g.items()):
            for h in H:
                key=str(h);eligible=events[ids[0]]['terminal'][key]['calendarEligible']
                slots=a.regular_slots(a.old.timestamp(stamp),end_target(stamp,h)) if eligible else []
                detail=[]
                for i in ids:
                    valid=sum(t in bar_maps[i] and bar_maps[i][t]['valid'] for t in slots)
                    detail.append({'symbol':events[i]['symbol'],'id':i,'terminalStatus':events[i]['terminal'][key]['status'],
                        'pathStatus':events[i]['path'][key]['status'],'expectedRegularBars':len(slots),'validBars':valid,'missingOrInvalidBars':len(slots)-valid})
                records[(stamp,key,arm)]={'session':stamp[:10],'timestamp':stamp,'horizon':key,'arm':arm,'originalN':5,
                    'calendarEligible':eligible,'endpointObservedN':sum(r['terminalStatus']=='AVAILABLE' for r in detail),
                    'completePathN':sum(r['pathStatus']=='AVAILABLE' for r in detail),'originalMembersAndReasons':json.dumps(detail,sort_keys=True)}
    rows=[]
    for (stamp,h,arm),r in records.items():
        r['full5Pairs']=json.dumps({other:r['endpointObservedN']==records[(stamp,h,other)]['endpointObservedN']==5 for other in arms if other!=arm},sort_keys=True)
        r['originalGroupOverlap']=json.dumps({other:len(set(grouped[arm][stamp])&set(grouped[other][stamp])) for other in arms if other!=arm},sort_keys=True)
        rows.append(r)
    with (Path(out)/'04b_v2_observability_by_timestamp.csv').open('x',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def measure(paths,context_dir,score_dir,phase_a_dir,out):
    import shutil
    p=load_protocol();out=Path(out);out.mkdir(parents=True,exist_ok=False)
    for f in Path(phase_a_dir).iterdir():
        assert sha(f)==p['phaseAHashes'][f.name],f.name
        shutil.copy2(f,out/f.name)
    shutil.copy2(BASE/'phase-a/01_start_state.json',out/'01_start_state.json')
    shutil.copy2(BASE/'07_protocol_v2_final_precommit.md',out/'07_protocol_v2_precommit.md')
    shutil.copy2(BASE/'08_protocol_v2_final_hash.json',out/'08_protocol_v2_hash.json')
    arms,prior=groups();meta=read(Path(context_dir)/'context.json');context=meta['context']
    assert set(context)==set(prior)
    assert sha(paths)==read(a.old.BASE/'measurement/manifest.json')['pathsSHA256'],'UNION_PATH_REGENERATION_DRIFT'
    raw=read(paths);events={};slot_audit=[]
    for path in raw['events']:
        i=path['selectorEventId'];full=a.evaluate(path)
        assert full['outcomes']==prior[i]['outcomes'],'V1_FULL_PATH_PARITY'
        c=context[i];c.update(priceBand=a.band(c['decisionPrice']),sessionHalf='AM' if a.old.timestamp(path['decisionTimestamp']).hour<12 else 'PM')
        e={k:full[k] for k in ['selectorEventId','sessionDate','symbol','decisionTimestamp','decisionPrice']}
        e['terminal']={str(h):terminal(path,h) for h in H};e['path']=full['outcomes'];events[i]=e
        # Exact slot audit is observations-only, never fed to frozen ranking or membership.
        slot_audit.append({'selectorEventId':i,'expectedRegularBars':len(path['future']),
            'missingBarStarts':[b['start'] for b in path['future'] if b['missing']],
            'observedMinuteCounts':dict(collections.Counter(str(b.get('observedMinutes')) for b in path['future'] if not b['missing'])),
            'terminalStatuses':{str(h):e['terminal'][str(h)]['status'] for h in H},
            'fullPathStatuses':{str(h):e['path'][str(h)]['status'] for h in H}})
    assert set(events)==set(prior)
    availability_csv(out,events,arms,raw)
    write(out/'slot-observability-audit.json.gz',{'role':'ALL_THREE_ARMS_SAME_SOURCE_AND_PROJECTOR','events':slot_audit,
        'physicalMissingnessReason':'ABSENT_SAVED_REGULAR_5M_BAR; no-trade/halt/provider/cache causes not separately identifiable.'})
    write(out/'endpoint-ledger.json.gz',{'arms':arms,'events':sorted(events.values(),key=lambda r:r['selectorEventId']),'context':context,'zeroMinute':'REFERENCE_GROSS_ZERO_ONLY'})
    write(out/'09_random_generation_manifest.json',{'random':p['random'],'momentum':p['momentum'],'membershipSHA256':sha(a.MEMBERSHIP),'arms':{arm:{'n':len(ids),'identitySHA256':a.digest(ids)} for arm,ids in arms.items()},'universeRows':1736930,'inputManifestSHA256':meta['inputManifestSHA256'],'membershipParityAllArms':True,'redraws':0,'futureAvailabilityUsedForSelection':False})
    available={arm:{str(h):{'originalN':3800,'statusCounts':dict(collections.Counter(events[i]['terminal'][str(h)]['status'] for i in ids)),
        'gross':stats(rows_at(events,ids,h),'gross'),'net':stats(rows_at(events,ids,h)),
        'costSensitivity':{str(c):a.dist([r['gross']-c for r in rows_at(events,ids,h)]) for c in [0,.05,.1,.2]}} for h in H} for arm,ids in arms.items()}
    write(out/'10_terminal_returns_by_horizon.json',{'role':'AVAILABLE_ORIGINAL_MEMBERS_DESCRIPTIVE','zeroMinute':{'gross':0,'net':None,'PF':None},'arms':available})
    comparisons={};common_ids={f'COMMON{lim}':{arm:[i for i in ids if all(events[i]['terminal'][str(h)]['status']=='AVAILABLE' for h in a.H if h<=lim)] for arm,ids in arms.items()} for lim in [60,90,120]}
    for baseline,filename in zip(a.ARMS[1:],['11_selector_vs_random_paired.json','12_momentum_comparison.json']):
        v={'primaryFull5':{str(h):pair(events,arms,h,baseline) for h in H},
            'observedMemberConditional':{str(h):pair(events,arms,h,baseline,'observed') for h in H},
            'commonEndpointConditional':{name:{str(h):pair(events,arms,h,baseline,'observed',cohort=cohort) for h in a.H if h<=int(name[6:])} for name,cohort in common_ids.items()},
            'limitations':'Incomplete-member means describe observable original members, not original Top5 policy return; no new membership, no substitution and no imputation.'}
        common=v['commonEndpointConditional']['COMMON120'];early=common['30']['differences']['net']['sessionValues'];late=common['120']['differences']['net']['sessionValues']
        assert early.keys()==late.keys()
        v['conditionalCommon120LateMinus30']=cluster({s:late[s]-early[s] for s in early})
        comparisons[baseline]=v;write(out/filename,v)
    tails={arm:{str(h):a.tails(rows_at(events,ids,h)) for h in H} for arm,ids in arms.items()};write(out/'18_tail_sensitivity.json',{'role':'OUTCOME_CONDITIONED_DIAGNOSTIC_NOT_POLICY','arms':tails})
    # Path metrics remain identical to v1; persist explicit sample labels and paired comparisons.
    path_out={'scope':'COMPLETE_INTERMEDIATE_PATHS_ONLY_CONDITIONAL','sameAsV1PerEvent':True,
        'arms':{arm:{str(h):a.summary(rows_at(events,ids,h,'path')) for h in H} for arm,ids in arms.items()},
        'paired':{base:{str(h):pair(events,arms,h,base,'observed','path') for h in H} for base in a.ARMS[1:]}}
    write(out/'13_mfe_mae_path.json',path_out)
    for target,source in [('14_peak_trough_timing.json','peak-trough-timing.json'),('15_giveback.json','giveback-summary.json'),('16_threshold_first_hit.json','peak-trough-timing.json'),('17_threshold_post_hit_descriptive.json','threshold-translation.json')]:
        write(out/target,{'scope':'V1_IDENTICAL_COMPLETE_PATH_COHORTS; FUTURE_CONDITIONED_WHERE_THRESHOLD_SELECTED','sourceSHA256':sha(V1/source),'data':read(V1/source)})
    score=score_analysis(score_dir);write(out/'19_score_return_monotonicity.json',score)
    stability={};feature_diag={}
    for arm,ids in arms.items():
        stability[arm]={str(h):{'sessions':session_means(rows_at(events,ids,h),'net'),
            'half':{part:stats([r for r in rows_at(events,ids,h) if context[r['selectorEventId']]['sessionHalf']==part]) for part in ['AM','PM']}} for h in H}
        feature_diag[arm]={field:{key:{str(h):stats(rows_at(events,[i for i in ids if str(context[i][field])==key],h)) for h in [30,120,'SESSION_END']} for key in sorted({str(context[i][field]) for i in ids})} for field in ['priceBand','volatilityStratum','liquidityBucket','segment']}
    write(out/'20_session_time_stability.json',{'observationConditional':True,'arms':stability,'primaryPairedSessionDeltas':comparisons[a.ARMS[1]]['primaryFull5']})
    write(out/'21_symbol_liquidity_price_diagnostics.json',{'conditionalStrata':feature_diag,'selectionConcentration':read(V1/'symbol-concentration.json'),
        'concentrationReturnMetricsScope':'Copied v1 complete-path returns explicitly; new endpoint conditional returns in conditionalStrata.',
        'tick':'NOT_EVALUABLE: actual dated tick schedule absent; no nominal 1JPY proxy interpreted as exchange tick.'})
    diagnosis=diagnose(comparisons[a.ARMS[1]]['primaryFull5'],comparisons[a.ARMS[1]]['observedMemberConditional'],score,context,arms,tails)
    r30=path_out['paired'][a.ARMS[1]]['30']['differences']
    if diagnosis['highVolSelectionRate']>.5 and all(r30[f]['clusterCI95'][0] is not None and r30[f]['clusterCI95'][0]>0 for f in ['MFE','absMAE']):diagnosis['tags'].append('D_VOLATILITY_RANGE_ASSOCIATION_DESCRIPTIVE')
    write(out/'diagnosis.json',diagnosis)
    (out/'22_final_selector_diagnosis.md').write_text(render(diagnosis,comparisons[a.ARMS[1]],tails,score,path_out))
    (out/'23_economic_selector_v2_design.md').write_text(design(diagnosis))
    write(out/'27_safety_and_data_boundary.json',{'safety':p['safety'],'sealed':p['sealed'],'SelectorChanged':False,'EntryChanged':False,'EXITChanged':False,'CapitalChanged':False,
        'newFitCalls':0,'providerRequests':0,'futureAvailabilityMembershipUsed':False,'allArmsExact3800Identity':True,'allUnionPathsHashParity':True,'v1AllPathMetricsParity':True,'historicalDevelopmentInSample':True})
    (out/'28_final_handoff.md').write_text('# Final handoff — STOP\n\n'+render(diagnosis,comparisons[a.ARMS[1]],tails,score,path_out)+'\n\nActive protocol SHA256: `'+sha(P)+'`. Source HEAD: `'+p['sourceHead']+'`. Exact producing/preservation commits and CI are recorded in 26_ci_report.json. No training, feature/target implementation, new acquisition, Entry/EXIT/Capital work, merge or promotion authorized by this output.\n')
    code=['scripts/phase57_selector_pairability_v2.py','scripts/phase57_selector_endpoint_scores_v2.mjs','scripts/test_phase57_selector_pairability_v2.py']
    write(out/'source-manifest.json',{'protocolSHA256':sha(P),'pathsSHA256':sha(paths),'sourcePins':p['sourcePins'],'sourceHead':p['sourceHead'],
        'code':{f:sha(ROOT/f) for f in code},'outputs':{f.name:sha(f) for f in sorted(out.iterdir())},'safety':p['safety'],'providerRequests':0,'newFitCalls':0})
    print(json.dumps({'status':'V2_ENDPOINT_AND_PATH_MEASUREMENT_COMPLETE','diagnosis':diagnosis}))

def render(d,c,tails,score,paths):
    lines=['# Frozen Selector Final Diagnosis — Measurement Protocol v2','',
        '**判定:** '+', '.join(d['tags'])+'.','',
        '今回の修復は終点リターンに不要な「途中全バー完全観測」条件を除くこと。元Top5、Immediate Entry、Random seed、Momentum、costは変更していない。欠測銘柄の再選出・補完・ゼロ代入はしない。','',
        '主estimandは両群の元Top5全5銘柄の始点・終点が観測できる同一時刻での平均net差。日内は時刻を等重み、日間はsessionを等重み。38 sessions・76 timestampsが解釈の最低条件。欠測がある元の全母集団の収益は未同定であり、この条件を満たしても欠測バイアスを解消したとは言わない。','',
        '観測できた元メンバー平均の比較は補助診断。欠測のある元Top5成績に置き換えず、原3800行と欠測件数を保存する。3/5等の新しい採用ゲートは作っていない。','',
        '| horizon | full5 paired timestamps | sessions | Selector net % | Random net % | delta pp | adjusted/pointwise CI | sample gate |','|---|---:|---:|---:|---:|---:|---|---|']
    for h,r in c['primaryFull5'].items():
        ci=r['differences']['net'];lines.append(f"| {h} | {r['timestamps']} | {ci['clusters']} | {a.fmt(r['selector']['sessionTimestampEqual']['sessionEqualMean'])} | {a.fmt(r['baseline']['sessionTimestampEqual']['sessionEqualMean'])} | {a.fmt(ci['sessionEqualMean'])} | {ci['simultaneousCI95']} | {r['minimumSampleMet']} |")
    lines+=['','## 補助：観測条件付き・元メンバーの同時刻比較','', '| horizon | paired timestamps | sessions | Selector observed rows | Random observed rows | Selector net % | Random net % | delta pp | pointwise CI |','|---|---:|---:|---:|---:|---:|---:|---:|---|']
    for h,r in c['observedMemberConditional'].items():
        ci=r['differences']['net'];lines.append(f"| {h} | {r['timestamps']} | {ci['clusters']} | {r['selectorObservedRows']} | {r['baselineObservedRows']} | {a.fmt(r['selector']['sessionTimestampEqual']['sessionEqualMean'])} | {a.fmt(r['baseline']['sessionTimestampEqual']['sessionEqualMean'])} | {a.fmt(ci['sessionEqualMean'])} | {ci['clusterCI95']} |")
    lines+=['','上表は各horizonの観測集合が異なる。時間経過の証拠として並べない。同一イベントを保つCOMMON60/90/120補助解析は11/12番JSONに保存。95% CIは記述的であり、欠測非ランダム性・全母集団への外挿を保証しない。',
        '',f"選出時のhigh-vol比率: {100*d['highVolSelectionRate']:.2f}%。選出前30分リターン中央値: {d['prior30MedianPct']:.4f}%。",'',
        '| score horizon | endpoint rows | terminal IC | 95% CI | monotone net deciles |','|---|---:|---:|---|---|']
    for h,s in score['horizons'].items():
        ic=s['rankIC']['gross']['cluster'];lines.append(f"| {h} | {s['terminalRows']} | {a.fmt(ic['sessionEqualMean'])} | {ic['clusterCI95']} | {s['netDecilesMonotoneNondecreasing']} |")
    t=tails[a.ARMS[0]]['30'];path30=paths['paired'][a.ARMS[1]]['30']['differences']
    lines+=['',f"30分available net行平均: {a.fmt(t['full']['mean'])}%。正の上位1%除外: {a.fmt(t['top1Excluded']['remaining']['mean'])}%、上位5%除外: {a.fmt(t['top5Excluded']['remaining']['mean'])}%。これは事後tail診断で、運用フィルタではない。",'',
        f"完全経路の補助30分Selector–Random差: MFE {a.fmt(path30['MFE']['sessionEqualMean'])}pp、abs(MAE) {a.fmt(path30['absMAE']['sessionEqualMean'])}pp、giveback {a.fmt(path30['giveback']['sessionEqualMean'])}pp。経路と終点の標本は異なるので、同じ観測集合の結果として混ぜない。",'',
        'first-hit/peak/troughは5分バー内区間、同じバー内の順序は不明。+1/+2/+3/+5の到達・保持・givebackは完全経路の将来条件付き記述。MFEは実現可能利益ではない。実際の銘柄・日付別tick sizeは未取得で評価不能。','',
        '言えること：固定メンバーにおける観測条件付きの相対差、PIT選出傾向、スコア順位付け、tail依存。言えないこと：欠測を含む元Top5全体の無条件経済リターン、実約定可能な利益、未知データでの優位性。','',
        '## 次工程判断','',('Economic LONG Selector v2の設計書を作成。スコアの経済順位付けと目的のずれを検討する根拠はあるが、新モデルが優れることを証明したわけではない。' if d['designOnlySupported'] else 'Economic Selector v2設計はNOT_APPLICABLE。十分な根拠なしに再設計を前提としない。'),
        d['nextStep'],'',
        'Dedicated tests/regression/CIの証拠は24/25/26番。現行戦略・Entry/EXIT/Capitalは変更なし、DEV TEST/Fresh/OOS未開封、provider0、Safety9項目false。ここでSTOP。','']
    return '\n'.join(lines)

def design(d):
    if not d['designOnlySupported']:return '# Economic LONG Selector v2\n\nNOT_APPLICABLE: diagnosis did not meet precommitted design-only rationale. No implementation or fit.\n'
    return '''# Economic LONG Selector v2 — DESIGN ONLY / NOT IMPLEMENTED

診断根拠：既存スコアの経済的な単調順位付けの弱さと、選出時の高vol・下落後への集中。観測条件付き分析であり、欠測を含む元Top5全母集団のalphaは未同定。再設計による改善は未検証。この設計はFrozen Selectorの解除・変更を許可しない。

1. **目的**：選出時点のPIT情報で、基準の即時実行価格から固定horizonの実行可能価格までのafter-cost forward valueを順位付けする。現在のsaved OPEN/CLOSEはreference markであり実際の約定価格ではない。データ契約が実行可能性を裏付けるまではexecutable label完成と呼ばない。
2. **target候補（未実装）**：既存30分を比較anchorとして固定net terminal returnを中心にする。 downside/MAEやtail-riskを補助headまたは制約として扱う選択肢を検討し、重み・形式はfit前に一案へprecommitする。未来MFE/MAEは教師ラベル候補のみで、特徴・判定時情報へ渡さない。MFE自体を取れる利益として最適化しない。
3. **horizon / multi-horizon**：5/15/30/60/120分を結果後に選び直す試験はしない。将来multi-horizon objectiveを採るなら、horizonと重みを次の実験前に固定し、現行30分baselineとの比較を残す。今回どの組合せも実装・評価しない。
4. **cost**：今回のcanonical5bpsは比較契約であり実際の全cost保証ではない。将来は手数料・spread・slippage・impactの利用可能な測定契約を別途固定。10/20bps sensitivityを事前定義して保持。結果を良くするcost変更は禁止。
5. **ranking / calibration / abstention**：最終net価値に対するrankingを優先。calibrationは許可されたDevelopment分割内のout-of-fold予測に限る設計とし、no-trade/abstentionも事前宣言・固定budgetの別候補とする。今回threshold、Top-K、cadence、universeを変更しない。
6. **liquidity / tick**：Decision時点で利用可能な情報だけ。実際のtick scheduleがなければ未評価。将来可観測性・実行可能性ゲートを加える案はSelector/universe変更なので、明示承認と新protocolを要する。未来のバー欠測を銘柄採用条件にしない。
7. **missingness**：terminal endpointと経路を分離。原Top5母集団、観測subset、欠測率を保存する。補完ゼロ・勝者filter・後日の生存銘柄listを使わない。MNARを無視した単一の点推定で全母集団の優位性を主張しない。観測改善はラベル改変ではなくsource/data-contract課題として扱う。
8. **null controls**：Frozen Selector、同一PIT universeの固定seed Random Top5、canonical Momentum30を同条件で残す。Repeated Randomを用いる場合はseed list/回数をfit前に固定し、取得可能性に合わせて再抽選しない。時間・sessionを同じにしcluster uncertaintyとtail感度を必須にする。
9. **分割**：既存76 Developmentは既に結果露出済みで、C+D fitted modelも含む。未知性能とは呼ばない。将来のDevelopment train/selection/calibrationを時系列で分離し、horizonの重複labelをpurgeする設計をprecommitする。Validation/DEV TEST/Fresh/OOSは今回未開封のまま。開封順・試行budgetは別途承認までTBD。
10. **Fresh budget**：今回の承認済み新規取得数0、今回使用数0。次工程のsession数・provider request数・料金・splitを事前確定してから別途許可を得る。今回予算を消費しない。
11. **完了条件（将来）**：source/PIT/observabilityを先に監査し、固定基準に対するafter-cost差・absolute net・downside・tail・capacityを事前基準で判定する。改善後もEntry/EXIT/Capital/Portfolio統合と未知評価は別gate。CI greenを性能改善としない。

**未開始**：target実装、training、fitting、hyperparameter search、feature selection、threshold search、新モデルmeasurement、Validation/OOS、Entry/EXIT/Capital。設計書のみでSTOP。
'''

def finalize_ci(directory,regression,head,run_id):
    import re
    d=Path(directory);reg=Path(regression);audit(d)
    logs=(reg/'targeted-tests.log').read_text();match=re.search(r'Ran (\d+) tests?',logs)
    assert match and '\nOK' in logs
    report=read(reg/'full/regression.json');assert report['status']=='PASS'
    write(d/'24_test_report.json',{'status':'PASS','dedicatedTests':int(match[1]),'targetedLogSHA256':sha(reg/'targeted-tests.log'),'commands':['scripts.test_phase57_selector_path_anatomy','scripts.test_phase57_selector_pairability_v2']})
    write(d/'25_regression_report.json',report)
    write(d/'26_ci_report.json',{'measurementJob':'SUCCESS','regressionJob':'SUCCESS','preservationJob':'RUNNING_AT_REPORT_CREATION_VERIFY_LINK_FOR_FINAL_STATUS',
        'producingHead':head,'protocolPrecommit':'65da0c9687d13acfef859e35eb9f33a9a46e9ae7','runId':run_id,
        'url':f'https://github.com/Iam-2squared/ark-terminal/actions/runs/{run_id}',
        'existingUnrelatedFailuresNotCleared':['EXIT CC Freeze Audit','old Economic Census immutable-output guard'],'mainMerged':False})
    write(d/'ci-manifest.json',{'measurementManifestSHA256':sha(d/'source-manifest.json'),'outputs':{f:sha(d/f) for f in ['24_test_report.json','25_regression_report.json','26_ci_report.json']}})

def main():
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='command',required=True)
    x=sub.add_parser('phase-a');x.add_argument('--output-dir',required=True)
    x=sub.add_parser('audit');x.add_argument('--measurement')
    x=sub.add_parser('finalize-ci')
    for key in ['directory','regression','head','run-id']:x.add_argument('--'+key,required=True)
    x=sub.add_parser('measure')
    for key in ['paths','context-dir','score-dir','phase-a-dir','output-dir']:x.add_argument('--'+key,required=True)
    x=p.parse_args()
    if x.command=='phase-a':phase_a(x.output_dir)
    elif x.command=='audit':audit(x.measurement)
    elif x.command=='finalize-ci':finalize_ci(x.directory,x.regression,x.head,x.run_id)
    else:measure(x.paths,x.context_dir,x.score_dir,x.phase_a_dir,x.output_dir)
if __name__=='__main__':main()
