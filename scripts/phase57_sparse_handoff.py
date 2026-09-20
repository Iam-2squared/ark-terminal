"""Precommitted Development-only Sparse Dictionary / Reader handoff measurement."""
import argparse
import collections
import copy
import csv
import gzip
import io
import json
import math
import functools
from pathlib import Path
import numpy as np
from scripts import phase57_research_dictionary_v0 as v
from scripts import phase57_expansion_data as admission
from scripts import phase57_behavior_reader_v2 as reader
from scripts import phase57_profile_coverage as coverage

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'docs/evidence/phase57-sparse-reader-ready-v1'
SOURCE=ROOT/'docs/evidence/phase57-behavior-expansion-v1/measurement'

def read(path):
    with (gzip.open(path,'rt') if str(path).endswith('.gz') else open(path)) as f:
        return json.load(f)

def write(path,obj):
    path.write_text(json.dumps(coverage.clean(obj),sort_keys=True,indent=2,allow_nan=False)+'\n')

def gzwrite(path,obj):
    with path.open('wb') as f, gzip.GzipFile(filename='',fileobj=f,mode='wb',mtime=0) as z:
        z.write(json.dumps(coverage.clean(obj),sort_keys=True,separators=(',',':'),allow_nan=False).encode())

def definition():
    p=read(BASE/'protocol.json')['pullback']
    return {'id':p['traitId'],'definition':p['definition'],'transform':'identity','tier':'intraday','family':'swing','registryVersion':p['registryVersion']}

def targets():
    defs={r['id']:r for r in v.registry()['catalog']}
    out={}
    for lane in ['daily','intraday']:
        rows=read(SOURCE/(lane+'-reliability.json'))
        out[lane]=[{**defs[r['id']],'globalStatus':r['status']} for r in rows if r['status']=='USABLE' or r['status']=='WATCH' and r['reasons']==['calibration']]
    out['intraday'] += [{**defs['pullback_depth'],'globalStatus':'OLD_COMPARATOR_ONLY'}, {**definition(),'globalStatus':'NEW_VERSION_CANDIDATE_ONLY'}]
    return out

def invariants():
    manifest=read(SOURCE/'manifest.json')
    for name,h in manifest.items():
        assert v.saved.sha(SOURCE/name)==h,'OLD_EVIDENCE_CHANGED:'+name
    admission.plan()
    return {'measurementManifest':v.saved.sha(SOURCE/'manifest.json'),
            'registry':v.saved.sha(v.BASE/'registry.json'),
            'split':v.saved.sha(admission.B/'04_session_split_manifest.json'),
            'holdoutLock':v.saved.sha(admission.B/'07_common_holdout_lock.json'),
            'protocol':v.saved.sha(BASE/'protocol.json')}

def calendar():
    return sorted(r['Date'] for r in read(admission.B/'probe-v2/calendar.json')['data'] if r['HolDiv']=='1')

def collect(cache,output):
    out=Path(output);out.mkdir(parents=True,exist_ok=False)
    before=invariants();p=admission.plan();allowed=set(p['dailyDevelopment'])|set(p['intradayDevelopment']);intradays=set(p['intradayDevelopment'])
    cal=calendar();grid=[d for d in cal if min(allowed)<=d<=max(allowed)];universes={};allcodes=set();ledger=[]
    pins={}
    for lane in ['daily','intraday']:
        for day,values in read(SOURCE/(lane+'-coverage.json'))['inputHashes'].items():
            pins.setdefault(day,{}).update(values)
    def pages(day,kind):
        admission.authorize(day,kind,p)
        path=Path(cache)/day/(kind+'-pages.json')
        data,receipt=v.saved.pages(path)
        assert all(r['Date']==day for r in data),'CROSS_SESSION'
        assert receipt['fileSHA256']==pins[day][kind]['fileSHA256'],'FROZEN_RAW_HASH_MISMATCH'
        ledger.append({'session':day,'kind':kind,'sha256':v.saved.sha(path)})
        return data
    for day in sorted(allowed):
        master=pages(day,'master')
        universes[day]={r['Code'] for r in master if str(r.get('Mkt')) in ['0111','0112','0113'] and str(r.get('ProdCat'))=='011'}
        allcodes.update(universes[day])
    codes=sorted(allcodes);n=len(codes);ts=targets()
    values={lane:np.full((len(grid),n,len(items)),np.nan) for lane,items in ts.items()}
    cov=np.full((len(grid),n,4),np.nan);intra_coverage=np.full((len(grid),n),np.nan);eligible=np.zeros((len(grid),n,2),bool)
    eventcounts=np.zeros((len(grid),n),np.int32);histories={c:[] for c in codes};reader_counts=collections.Counter();reader_examples=[]
    old_new=[];event_examples=[];resets=[]
    for di,day in enumerate(grid):
        if day not in allowed:
            histories={c:[] for c in codes};resets.append(day);continue
        if di==len(grid)-1:gzwrite(out/'last-history.json.gz',histories)
        daily=pages(day,'daily');assert len({r['Code'] for r in daily})==len(daily)
        dc={r['Code']:r for r in daily};by=collections.defaultdict(list)
        if day in intradays:
            for row in pages(day,'minute'):
                if row['Code'] in universes[day]:by[row['Code']].append(row)
        probes=0
        for j,code in enumerate(codes):
            hist=histories[code];d=dc.get(code) if code in universes[day] else None;prev=hist[-1]['daily'] if hist else None;s=v.scale(hist)
            entry={'session':day,'daily':d,'tr':None,'Va':d['Va'] if v.valid(d) else None,'C':d['C'] if v.valid(d) else None,'s':s,'ret':None}
            safe=v.valid(d) and v.valid(prev) and not v.action(d) and not v.action(prev)
            if safe:
                entry['tr']=max(d['H']-d['L'],abs(d['H']-prev['C']),abs(d['L']-prev['C']))/prev['C'];entry['ret']=d['C']/prev['C']-1
            rows=sorted(by[code],key=v.minute_time)
            assert len({v.minute_time(r) for r in rows})==len(rows),'DUPLICATE_MINUTE'
            ok,_=v.intraday_eligible(d,rows) if day in intradays else (False,{})
            if safe and s and len(hist)>=5:
                eligible[di,j,0]=True;daily_traits=v.daily_traits(d,prev,hist,s)
                for k,item in enumerate(ts['daily']):
                    val=daily_traits.get(item['id'])
                    if v.num(val):values['daily'][di,j,k]=val
                history_coverage=sum(v.valid(h.get('daily')) for h in hist[-10:])/len(hist[-10:])
                cov[di,j]=[math.log(max(d['Va'],1)),math.log(s),math.log(d['C']),history_coverage]
                if day in intradays:
                    intra_coverage[di,j]=sum(v.saved.phase(day,v.minute_time(r))=='REGULAR' for r in rows)/(300 if day<'2024-11-05' else 325)
                if ok:
                    eligible[di,j,1]=True;intratraits,_,extra=v.intraday_traits(day,d,prev,rows,s,hist);intratraits={**daily_traits,**intratraits};entry.update(extra)
                    bars=v.bars5(day,rows);ev=reader.pullback_events(bars,prev['C']*s)
                    entry['barVolumes']={b['t']:b['Vo'] for b in bars}
                    eventcounts[di,j]=len(ev)
                    if ev:intratraits[reader.PULLBACK_ID]=float(np.mean([x['value'] for x in ev]))
                    for k,item in enumerate(ts['intraday']):
                        val=intratraits.get(item['id'])
                        if v.num(val):values['intraday'][di,j,k]=val
                    old_new.append({'session':day,'symbol':code,'old':intratraits.get('pullback_depth'),'vnext':intratraits.get(reader.PULLBACK_ID),'eventPairs':len(ev)})
                    if ev and len(event_examples)<100:event_examples.append({'session':day,'symbol':code,'events':ev})
                    if probes<3:
                        probes+=1
                        for at in [545,570,690,755,900 if day<'2024-11-05' else 925]:
                            prefix=[r for r in rows if v.minute_time(r)<at and (540<=v.minute_time(r)<690 or 750<=v.minute_time(r)<(900 if day<'2024-11-05' else 925))]
                            ctx=reader.context(day,at,prefix,prev,hist,cal)
                            reader_counts[ctx['status']+':'+str(ctx['missingReason'])]+=1
                            if len(reader_examples)<30:reader_examples.append({'symbol':code,**ctx})
            hist.append(entry);histories[code]=hist[-10:]
        print(json.dumps({'collected':day,'minute':day in intradays,'dailyEligible':int(eligible[di,:,0].sum()),'intradayEligible':int(eligible[di,:,1].sum())}),flush=True)
    np.savez_compressed(out/'matrix.npz',daily=values['daily'],intraday=values['intraday'],cov=cov,intraCoverage=intra_coverage,eligible=eligible,eventcounts=eventcounts)
    write(out/'metadata.json',{'codes':codes,'sessions':grid,'targets':ts,'lastMaster':sorted(universes[max(allowed)]),'inputLedger':ledger,'excludedNoPayloadRead':resets,'hashes':before,'readerCounts':dict(reader_counts),'readerExamples':reader_examples,'eventExamples':event_examples})
    gzwrite(out/'pullback-comparison.json.gz',old_new)
    assert invariants()==before

def snapshot(data,cov,eligible,item,indices):
    kind=item['transform'];z=v.transform(data[indices],kind);value,raw,n,eff=v.profile(z,kind)
    cv=v.mean(cov[indices]);minimum=8 if item['id'] in v.CONDITIONAL or item['id']==reader.PULLBACK_ID else 20
    mask=(eligible[indices].sum(0)>=20)&(n>=minimum)&np.isfinite(value)&np.all(np.isfinite(cv),axis=1)
    shape=len(n);nan=lambda:np.full(shape,np.nan)
    r={'raw':v.mean(data[indices]),'value':value,'n':n,'eff':eff,'peer':nan(),'residual':nan(),'post':nan(),'sd':nan(),'weight':nan(),'mask':mask,'coverage':eligible[indices].sum(0)/len(indices),'reference':None,'fit':None}
    if mask.sum()<100:return r
    x,_,beta,mu,sd=v.fit_peer((cv[mask],cv[mask]),value[mask],value[mask]);peer=x@beta;res=value[mask]-peer;weight=eff[mask]/(eff[mask]+20)
    post=peer+weight*res
    psd=np.sqrt(np.maximum(v.mean((z-v.mean(z)[None,:])**2)[mask],0)/(eff[mask]+20))
    if kind=='rate':
        prob=1/(1+np.exp(-np.clip(peer,-30,30)));alpha=eff[mask]*raw[mask]+20*prob;bet=eff[mask]*(1-raw[mask])+20*(1-prob);pp=alpha/(alpha+bet)
        post=np.log(np.clip(pp,1e-9,1-1e-9)/(1-np.clip(pp,1e-9,1-1e-9)));psd=np.sqrt(alpha*bet/((alpha+bet)**2*(alpha+bet+1)))/np.maximum(pp*(1-pp),1e-12)
    for key,val in [('peer',peer),('residual',res),('post',post),('sd',psd),('weight',weight)]:r[key][mask]=val
    r['reference']=float(np.std(res));r['fit']={'beta':beta,'mean':mu,'sd':sd};return r

def drift(data,kind,end,window=60):
    z=v.transform(data[:end+1],kind);a=z[max(0,len(z)-window):];b=z[max(0,len(z)-2*window):max(0,len(z)-window)]
    if not len(b):return [None]*data.shape[1]
    na=np.isfinite(a).sum(0);nb=np.isfinite(b).sum(0);ma=v.mean(a);mb=v.mean(b)
    se=np.sqrt(v.mean((a-ma)**2)/np.maximum(na,1)+v.mean((b-mb)**2)/np.maximum(nb,1))
    score=np.divide(ma-mb,se,out=np.full(len(na),np.nan),where=(na>=20)&(nb>=20)&(se>0))
    return [bool(abs(s)>3) if np.isfinite(s) else None for s in score]

@functools.lru_cache(maxsize=1)
def sample_policy():
    return read(coverage.BASE/'protocol.json')

def sample(s,j,d):
    ref=s['reference'];sd=s['sd'][j]
    cell={'eligible':bool(s['mask'][j]),'posterior':s['post'][j],'posterior_sd':sd,'peer_prediction':s['peer'][j],'shrinkWeight':s['weight'][j],
          'nSessions':s['n'][j],'nEff':s['eff'][j],'coverage':s['coverage'][j],'normalizedUncertainty':sd/ref if ref and ref>0 else None,'driftFlag':d}
    return coverage.confidence(cell,sample_policy())

def folds(sessions,p):
    allowed=p['intradayDevelopment'];index={d:i for i,d in enumerate(sessions)};out=[]
    for count in [60,80,100]:
        day=allowed[count-1];end=index[day];test=[d for d in allowed if index[d]>end+5][:20]
        if len(test)==20:out.append({'anchor':day,'end':end,'train':np.arange(max(0,end-59),end+1),'test':np.arange(index[test[0]],index[test[-1]]+1),'testStart':test[0],'testEnd':test[-1]})
    return out

def temporal_summary(records,policy):
    good=[r for r in records if r['eligible']]
    out={'status':'INSUFFICIENT','folds':len(good),'signConsistency':None,'normalizedRMSE':None,'normalizedBias':None,'calibrationSlope':None,'posteriorChangeRMS':None}
    if len(good)<policy['minimumFolds']:return out
    x=np.array([r['x'] for r in good]);y=np.array([r['y'] for r in good]);postdiff=np.array([r['posteriorChange'] for r in good])
    sign=float(np.mean(np.sign(x)==np.sign(y)));rmse=float(np.sqrt(np.mean((y-x)**2)));bias=float(np.mean(y-x));den=float(np.sum((x-x.mean())**2))
    slope=float(np.sum((x-x.mean())*(y-y.mean()))/den) if np.std(x)>=policy['minimumNormalizedPredictionSD'] else None
    change=float(np.sqrt(np.mean(postdiff**2)))
    passed=sign>=policy['minimumSignConsistency'] and rmse<=policy['maximumNormalizedRMSE'] and abs(bias)<=policy['maximumAbsoluteNormalizedBias'] and slope is not None and .5<=slope<=1.5 and change<=policy['maximumPosteriorChangeRMS']
    out.update(status='PASS' if passed else 'FAIL',signConsistency=sign,normalizedRMSE=rmse,normalizedBias=bias,calibrationSlope=slope,posteriorChangeRMS=change)
    return out

def evaluate(matrix,output):
    src=Path(matrix);out=Path(output);out.mkdir(parents=True,exist_ok=False);before=invariants();meta=read(src/'metadata.json');assert before==meta['hashes'];p=admission.plan();protocol=read(BASE/'protocol.json')
    arrays=np.load(src/'matrix.npz');sessions=meta['sessions'];codes=meta['codes'];last=len(sessions)-1;asof=sessions[-1]+'T15:30:00+09:00';schedule=folds(sessions,p)
    profiles={c:{'symbol':c,'securityIdentity':{'code':c,'asOfMaster':sessions[-1],'listed':c in meta['lastMaster']},'asOf':asof,'researchOnly':True,'traits':[]} for c in codes}
    summary=[];foldrows=[];watch=[];temporal_records=[];artifacts=[];prior_candidates={}
    def artifact(s,lane,trait,through,window):
        fit={k:val.tolist() for k,val in s['fit'].items()} if s['fit'] else None
        obj={'lane':lane,'trait':trait,'computedThrough':through,'window':window,'fit':fit,'referenceResidualSD':s['reference']}
        obj=coverage.clean(obj);obj['hash']=reader.digest(obj);artifacts.append(obj);return obj['hash']
    for lane,items in meta['targets'].items():
        lane_values=arrays[lane];lane_cov=arrays['cov'].copy()
        if lane=='intraday':lane_cov[:,:,3]=arrays['intraCoverage']
        for k,item in enumerate(items):
            data=lane_values[:,:,k];tier=0 if item['tier']=='daily' else 1;eligible=arrays['eligible'][:,:,tier].copy()
            if lane=='intraday':eligible &= np.array([d in p['intradayDevelopment'] for d in sessions])[:,None]
            cv=lane_cov;per_symbol=[[] for _ in codes];foldpairs=[]
            for fi,f in enumerate(schedule):
                a=snapshot(data,cv,eligible,item,f['train']);b=snapshot(data,cv,eligible,item,f['test']);dr=drift(data,item['transform'],f['end']);ref=a['reference']
                artifact(a,lane,item['id'],f['anchor']+'T15:30:00+09:00','fold'+str(fi))
                ae=snapshot(data,cv,eligible,item,np.arange(f['end']+1))
                artifact(ae,lane,item['id'],f['anchor']+'T15:30:00+09:00','expandingFold'+str(fi))
                testcv=v.mean(cv[f['test']]);fit=a['fit'];pb=np.full(len(codes),np.nan)
                if fit is not None:pb=np.column_stack([np.ones(len(codes)),(testcv-fit['mean'])/fit['sd']])@fit['beta']
                x=(a['post']-a['peer'])/ref if ref and ref>0 else np.full(len(codes),np.nan)
                y=(b['value']-pb)/ref if ref and ref>0 else np.full(len(codes),np.nan)
                source_conf=[sample(a,j,dr[j]) for j in range(len(codes))]
                ok=np.array([q in ['HIGH','MEDIUM'] for q in source_conf])&(a['eff']>=20)&(b['eff']>=8)&(b['n']>=8)&np.isfinite(x)&np.isfinite(y)
                postchange=(b['post']-a['post'])/ref if ref and ref>0 else np.full(len(codes),np.nan);ok &= np.isfinite(postchange)
                for j in range(len(codes)):
                    r={'fold':fi,'eligible':bool(ok[j]),'x':x[j],'y':y[j],'posteriorChange':postchange[j],'sourceNEff':a['eff'][j],'targetNEff':b['eff'][j],'sourceConfidence':source_conf[j]}
                    per_symbol[j].append(r)
                    if ok[j]:temporal_records.append({'lane':lane,'trait':item['id'],'symbol':codes[j],**r})
                allfit=np.isfinite(x)&np.isfinite(y)&(a['eff']>=20)&(b['eff']>=8)&(b['n']>=8)
                foldpairs.append((x[allfit],y[allfit]))
                foldrows.append({'lane':lane,'trait':item['id'],'fold':fi,'anchor':f['anchor'],'testStart':f['testStart'],'testEnd':f['testEnd'],'eligibleHMSymbols':int(ok.sum()),'allFitPairs':int(allfit.sum()),'rawReliability':v.spearman(a['value'][allfit],b['value'][allfit]),'incrementalReliability':v.spearman(x[allfit],y[allfit]),'expandingRawReliability':v.spearman(ae['value'],b['value']),'recentVsExpandingPosterior':v.spearman(a['post'],ae['post'])})
            current=snapshot(data,cv,eligible,item,np.arange(max(0,last-59),last+1));short=snapshot(data,cv,eligible,item,np.arange(max(0,last-19),last+1));long=snapshot(data,cv,eligible,item,np.arange(max(0,last-249),last+1));expanding=snapshot(data,cv,eligible,item,np.arange(last+1));dr=drift(data,item['transform'],last)
            fit_hash=artifact(current,lane,item['id'],asof,60)
            prior=None
            if item['globalStatus']=='USABLE' and sessions[last-1] in set(p['dailyDevelopment'])|set(p['intradayDevelopment']):
                prior=snapshot(data,cv,eligible,item,np.arange(max(0,last-60),last));prior_dr=drift(data,item['transform'],last-1)
                prior_asof=sessions[last-1]+'T15:30:00+09:00';prior_hash=artifact(prior,lane,item['id'],prior_asof,'integrationPrior60')
            confcounts=collections.Counter();temcounts=collections.Counter();passing=0
            for j,code in enumerate(codes):
                conf=sample(current,j,dr[j]);tem=temporal_summary(per_symbol[j],protocol['temporalPolicy']);temcounts[tem['status']]+=1
                listed=profiles[code]['securityIdentity']['listed']
                if not listed:conf='INSUFFICIENT'
                confcounts[conf]+=1
                record={'symbol':code,'lane':lane,'trait_id':item['id'],'raw':current['raw'][j],'posterior':current['post'][j],'peerRelative':current['residual'][j],'peerPrediction':current['peer'][j],
                        'globalStatus':item['globalStatus'],'sampleConfidence':conf,'temporalReliability':tem,'nSessions':int(current['n'][j]),'nEff':current['eff'][j],
                        'episodes':int(current['n'][j]) if item['id'] in v.CONDITIONAL or item['id']==reader.PULLBACK_ID else None,
                        'episodeUnit':'event-bearing sessions, not independent intraday events','shrinkWeight':current['weight'][j],
                        'uncertainty':{'posteriorSD':current['sd'][j],'referenceResidualSD':current['reference'],'CI':[current['post'][j]-1.96*current['sd'][j],current['post'][j]+1.96*current['sd'][j]]},
                        'stability':{'recent20Posterior':short['post'][j],'long250Posterior':long['post'][j],'expandingPosterior':expanding['post'][j],'temporal':tem['status']},'drift':dr[j],
                        'computedThrough':asof,'peerArtifactThrough':asof,'normalizationThrough':asof,'referenceScaleThrough':asof,'artifactHash':fit_hash,
                        'definitionHash':reader.digest({key:val for key,val in item.items() if key!='globalStatus'}),'transform':item['transform'],
                        'evidenceClass':protocol['evidenceClass'],'identityStatus':'DATED_MASTER_CODE_RESEARCH_ONLY' if listed else 'NOT_LISTED_AT_ASOF'}
                profiles[code]['traits'].append(record)
                if prior is not None and listed and tem['status']=='PASS' and prior_dr[j] is not True:
                    prior_conf=sample(prior,j,prior_dr[j])
                    if prior_conf in ['HIGH','MEDIUM']:
                        pr={**record,'sampleConfidence':prior_conf,'raw':prior['raw'][j],'posterior':prior['post'][j],'peerRelative':prior['residual'][j],'peerPrediction':prior['peer'][j],'nSessions':int(prior['n'][j]),'nEff':prior['eff'][j],'shrinkWeight':prior['weight'][j],'drift':prior_dr[j],'artifactHash':prior_hash,
                            'episodes':int(prior['n'][j]) if item['id'] in v.CONDITIONAL else None,
                            'uncertainty':{'posteriorSD':prior['sd'][j],'referenceResidualSD':prior['reference']},'stability':{'temporal':tem['status']}}
                        for key in ['computedThrough','peerArtifactThrough','normalizationThrough','referenceScaleThrough']:pr[key]=prior_asof
                        prior_candidates.setdefault(code,{'symbol':code,'asOf':prior_asof,'researchOnly':True,'traits':[]})['traits'].append(pr)
                if item['globalStatus']=='USABLE' and conf in ['HIGH','MEDIUM'] and tem['status']=='PASS' and dr[j] is not True:passing+=1
            summary.append({'lane':lane,'trait':item['id'],'globalStatus':item['globalStatus'],'symbols':len(codes),'sampleConfidence':dict(confcounts),'temporalReliability':dict(temcounts),'dispatchableSymbols':passing})
            if item['globalStatus']=='WATCH':
                x,y=foldpairs[0];mapping=None;checks=[]
                if len(x)>=100 and np.std(x)>1e-8:
                    mapping=np.linalg.lstsq(np.column_stack([np.ones(len(x)),x]),y,rcond=None)[0]
                    for xx,yy in foldpairs[1:]:
                        pred=mapping[0]+mapping[1]*xx;den=np.sum((pred-pred.mean())**2)
                        slope=float(np.sum((pred-pred.mean())*(yy-yy.mean()))/den) if len(xx)>=100 and den>0 else None
                        mse=float(np.mean((yy-pred)**2)) if len(xx) else None;identity=float(np.mean((yy-xx)**2)) if len(xx) else None
                        checks.append({'pairs':len(xx),'calibrationSlope':slope,'mappedMSE':mse,'identityMSE':identity,'signConsistency':float(np.mean(np.sign(pred)==np.sign(yy))) if len(xx) else None,'pass':slope is not None and .5<=slope<=1.5 and mse<=identity})
                watch.append({'lane':lane,'trait':item['id'],'mappingFold1':mapping.tolist() if mapping is not None else None,'independentPeriods':checks,'newVersionCandidate':len(checks)==2 and all(x['pass'] for x in checks),'oldStatus':'WATCH','promotion':False})
            print(json.dumps({'evaluated':lane+'/'+item['id'],'dispatchable':passing}),flush=True)
    # Numeric JSON nulls preserve unavailable values; no fabricated peer prior.
    profiles=coverage.clean(profiles)
    decision=sessions[-1]+'T15:31:00+09:00'
    candidates={c:reader.dispatch(s,decision) for c,s in profiles.items()}
    counts={view:coverage.bins(len({r['trait_id'] for r in rows if view=='combined' or r['lane']==view}) for rows in candidates.values()) for view in ['daily','intraday','combined']}
    hmcounts=coverage.bins(len({r['trait_id'] for r in s['traits'] if r['globalStatus']=='USABLE' and r['sampleConfidence'] in ['HIGH','MEDIUM']}) for s in profiles.values())
    passed=sum(bool(r) for r in candidates.values())
    paired=read(src/'pullback-comparison.json.gz');pairs=[r for r in paired if r['old'] is not None and r['vnext'] is not None]
    pullback={'registry':definition(),'symbolSessions':len(paired),'eventBearingSessions':sum(r['vnext'] is not None for r in paired),'eventPairs':int(arrays['eventcounts'].sum()),'pairedOldNewSessions':len(pairs),'oldMedian':coverage.stats(r['old'] for r in paired),'vnextMedian':coverage.stats(r['vnext'] for r in paired),'pairedDifference':coverage.stats(r['vnext']-r['old'] for r in pairs),'temporalResult':next(r for r in summary if r['trait']==reader.PULLBACK_ID),'newGlobalStatus':'CANDIDATE_ONLY_NOT_PROMOTED','events':meta['eventExamples']}
    # Freeze data-dependent gate inputs; contract/CI receipts are separate requirements.
    gate={'status':'DATA_ELIGIBLE_PENDING_CONTRACT_CI' if passed and meta['readerCounts'].get('RESEARCH_CONTEXT_AVAILABLE:None',0)>0 else 'BLOCKED',
          'dispatchableResearchSymbols':passed,'sameAsOf':asof,'sameAsOfContract':True,'temporalMeasured':True,
          'productionAllowed':False,'entryExitDesignAllowed':False,
          'reasons':[] if passed else ['NO_USABLE_SAMPLE_HM_AND_TEMPORAL_PASS_SYMBOL_TRAIT'],
          'requiredBeforeReady':['contractTestsPASS','fullRegressionPASS','deterministicRegenerationPASS','rawReceiptAndBoundaryPASS','freshSameSessionReaderAtUse'],
          'dataOnlyNoAutomaticPromotion':True}
    write(out/'01_trait_coverage.json',summary);write(out/'02_walk_forward.json',foldrows);write(out/'03_watch_mapping.json',watch);write(out/'04_pullback_vnext.json',pullback)
    write(out/'05_coverage.json',{'symbols':len(codes),'listedAtAsOf':len(meta['lastMaster']),'sampleHMCounts':hmcounts,'temporalDispatchCounts':counts,'nonemptyDispatch':passed,'asOf':asof})
    gzwrite(out/'06_sparse_profiles.json.gz',list(profiles.values()));gzwrite(out/'07_temporal_symbol_folds.json.gz',temporal_records)
    write(out/'08_reader.json',{'counts':meta['readerCounts'],'examples':meta['readerExamples'],'sharedFor':'Entry_AND_EXIT','decisionsImplemented':False})
    write(out/'09_handoff_gate.json',gate)
    write(out/'10_boundary_evidence.json',{'sourceHashes':before,'inputLedger':meta['inputLedger'],'excludedNoPayloadRead':meta['excludedNoPayloadRead'],'observedPayloadSessions':sorted(set(r['session'] for r in meta['inputLedger'])),'commonHoldoutIntersection':sorted(set(r['session'] for r in meta['inputLedger'])&set(p['commonHoldout'])),'excludedIntersection':sorted(set(r['session'] for r in meta['inputLedger'])&set(p['excluded'])),'providerRequests':0,'previousExposureLedger':'PRESERVED_UNCHANGED','safety':p['safety']})
    write(out/'11_asof_artifacts.json',artifacts)
    gzwrite(out/'12_integration_prior_profiles.json.gz',prior_candidates)
    assert invariants()==before
    write(out/'manifest.json',{f.name:v.saved.sha(f) for f in sorted(out.iterdir())})

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('command',choices=['collect','evaluate']);ap.add_argument('--cache');ap.add_argument('--matrix');ap.add_argument('--output',required=True);args=ap.parse_args()
    if args.command=='collect':collect(args.cache,args.output)
    else:evaluate(args.matrix,args.output)
