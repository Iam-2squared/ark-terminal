"""Exact-spec Development temporal remeasurement; no optimization or trading."""
import argparse,collections,copy,json,subprocess
from pathlib import Path
import numpy as np
from scripts import phase57_temporal_zero_diagnostic as d
from scripts import phase57_sparse_trait_contract as contract
s=d.s;r=s.reader;BASE=s.ROOT/'docs/evidence/phase57-temporal-formal-v1'


def verify():
    p=s.read(BASE/'protocol.json');path=s.ROOT/p['adoptedSpecPath']
    assert d.hashfile(path)==p['adoptedSpecSHA256']
    assert d.hashfile(path.parent/'manifest.json')==p['feasibilityManifestSHA256']
    assert d.verify_sources()==p['sourceHashes']
    spec=s.read(path)
    assert spec['temporalPolicy']==s.read(s.BASE/'protocol.json')['temporalPolicy']
    assert spec['sampleConfidence']==s.sample_policy()
    return p,spec


def restore(archives,cache,output):
    verify();p=s.admission.plan();selected={'2025-08-22','2025-08-25'}
    assert selected<=set(p['intradayDevelopment']);receipts=[]
    files=list(Path(archives).rglob('minute-017.tar.gz.enc'));assert len(files)==1
    for f in files:
        expected=f.with_name(f.name+'.sha256').read_text().split()[0];assert d.hashfile(f)==expected
        proc=subprocess.Popen(['openssl','enc','-d','-aes-256-cbc','-pbkdf2','-iter','200000','-pass','env:JQUANTS_API_KEY','-in',str(f)],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        try:receipt=s.admission.base.extract_stream(proc.stdout,cache,selected)
        finally:proc.stdout.close();err=proc.stderr.read();code=proc.wait()
        assert code==0,'DECRYPT_FAILED'
        assert set(receipt['selectedDates'])==selected
        receipts.append({'archiveSHA256':expected,**receipt})
    s.write(Path(output),receipts)


def temporal_result(periods,spec):
    result=s.temporal_summary(periods,spec['temporalPolicy'])
    result.update(computedThrough=spec['schedule']['rows'][-1]['testEnd']+'T15:30:00+09:00',availableAt=spec['schedule']['rows'][-1]['testEnd']+'T15:31:00+09:00',evidenceClass='DEVELOPMENT_DESCRIPTIVE_NOT_CONFIRMATORY_NOT_OOS')
    result['reasons']=[]
    if result['status']=='INSUFFICIENT':result['reasons']=['FEWER_THAN_THREE_ELIGIBLE_PERIODS']
    elif result['status']=='FAIL':
        p=spec['temporalPolicy']
        for name,failed in [('SIGN_CONSISTENCY',result['signConsistency']<p['minimumSignConsistency']),('RMSE',result['normalizedRMSE']>p['maximumNormalizedRMSE']),('BIAS',abs(result['normalizedBias'])>p['maximumAbsoluteNormalizedBias']),('CALIBRATION',result['calibrationSlope'] is None or not p['calibrationSlopeRange'][0]<=result['calibrationSlope']<=p['calibrationSlopeRange'][1]),('POSTERIOR_CHANGE',result['posteriorChangeRMS']>p['maximumPosteriorChangeRMS'])]:
            if failed:result['reasons'].append(name)
    return result


def watch_mapping(pairs,spec):
    x,y=pairs[0];mapping=None;checks=[]
    through=spec['schedule']['rows'][0]['testEnd']+'T15:30:00+09:00';available=spec['schedule']['rows'][0]['testEnd']+'T15:31:00+09:00'
    if len(x)>=100 and np.std(x)>1e-8:
        mapping=np.linalg.lstsq(np.column_stack([np.ones(len(x)),x]),y,rcond=None)[0]
    for f,(xx,yy) in zip(spec['schedule']['rows'][1:],pairs[1:]):
        assert r.timestamp(available)<r.timestamp(f['predictionOrigin'])
        check={'period':f['name'],'pairs':len(xx),'mappingThrough':through,'availableAt':available,'predictionOrigin':f['predictionOrigin'],'pass':False,'reason':None}
        if mapping is None:check['reason']='CALIBRATION_FIT_SUPPORT_INSUFFICIENT'
        else:
            pred=mapping[0]+mapping[1]*xx;den=np.sum((pred-pred.mean())**2)
            slope=float(np.sum((pred-pred.mean())*(yy-yy.mean()))/den) if len(xx)>=100 and den>0 else None
            mse=float(np.mean((yy-pred)**2)) if len(xx) else None;identity=float(np.mean((yy-xx)**2)) if len(xx) else None
            check.update(calibrationSlope=slope,mappedMSE=mse,identityMSE=identity,signConsistency=float(np.mean(np.sign(pred)==np.sign(yy))) if len(xx) else None)
            check['pass']=slope is not None and .5<=slope<=1.5 and mse<=identity
            if not check['pass']:check['reason']='FIXED_CALIBRATION_CONDITIONS_NOT_MET'
        checks.append(check)
    return {'fitPairs':len(x),'mapping':None if mapping is None else mapping.tolist(),'independentPeriods':checks,'newVersionCandidate':all(x['pass'] for x in checks),'oldStatus':'WATCH','promotion':False}


def run(matrix,cache,output):
    protocol,spec=verify();out=Path(output);out.mkdir(parents=True,exist_ok=False)
    meta=s.read(Path(matrix)/'metadata.json');z=np.load(Path(matrix)/'matrix.npz');p=s.admission.plan();days=meta['sessions'];codes=meta['codes'];allowed=set(p['dailyDevelopment'])|set(p['intradayDevelopment'])
    assert len(p['intradayDevelopment'])==144 and len(p['commonHoldout'])==244
    assert meta['hashes']==s.invariants() and meta['inputLedger']==s.read(d.OLD/'10_boundary_evidence.json')['inputLedger']
    observed={x['session'] for x in meta['inputLedger']};assert observed<=allowed and not observed&(set(p['excluded'])|set(p['commonHoldout']))
    assert {x['session'] for x in meta['inputLedger'] if x['kind']=='minute'}==set(p['intradayDevelopment'])
    assert days==sorted(set(days)) and codes==sorted(set(codes))
    pins={(x['session'],x['kind']):x['sha256'] for x in meta['inputLedger']}
    def pages(day,kind):
        s.admission.authorize(day,kind,p);path=Path(cache)/day/(kind+'-pages.json');assert d.hashfile(path)==pins[day,kind]
        return s.v.saved.pages(path)[0]
    prior_day='2025-08-22';last_day='2025-08-25';assert days[-1]==last_day
    prior_master={x['Code'] for x in pages(prior_day,'master') if str(x.get('Mkt')) in ['0111','0112','0113'] and str(x.get('ProdCat'))=='011'}
    last=len(days)-1;prior_index=days.index(prior_day);assert prior_index==last-1
    asof=last_day+'T15:30:00+09:00';decision=last_day+'T15:31:00+09:00'
    profiles={c:{'symbol':c,'asOf':asof,'researchOnly':True,'traits':[]} for c in codes}
    priors={c:{'symbol':c,'asOf':prior_day+'T15:30:00+09:00','researchOnly':True,'traits':[]} for c in codes}
    supporting={(x['lane'],x['trait']):x for x in s.read(s.ROOT/'docs/evidence/phase57-temporal-feasibility-v1/ci-result/measurement/02_trait_support.json')}
    artifacts=[];families=[];watches=[]
    def artifact(a,lane,trait,through,label):
        obj=s.coverage.clean({'lane':lane,'trait':trait,'computedThrough':through,'window':label,'fit':({k:v.tolist() for k,v in a['fit'].items()} if a['fit'] is not None else None),'referenceResidualSD':a['reference']})
        h=r.digest(obj);artifacts.append({'hash':h,**obj});return h
    for lane,items in meta['targets'].items():
        cv=z['cov'].copy()
        if lane=='intraday':cv[:,:,3]=z['intraCoverage']
        for k,item in enumerate(items):
            if item['globalStatus'] not in ['USABLE','WATCH']:continue
            data=z[lane][:,:,k];eligible=z['eligible'][:,:,0 if item['tier']=='daily' else 1].copy()
            if lane=='intraday':eligible &= np.array([x in p['intradayDevelopment'] for x in days])[:,None]
            periods=[[] for _ in codes];pairsets=[];masks=[];period_counts=[]
            for f in spec['schedule']['rows']:
                ix=np.arange(f['trainStartIndex'],f['anchorIndex']+1);iy=np.arange(f['testStartIndex'],f['testEndIndex']+1)
                assert days[ix[0]]==f['trainStart'] and days[ix[-1]]==f['computedThrough'][:10] and days[iy[-1]]==f['testEnd']
                assert r.timestamp(f['computedThrough'])<r.timestamp(f['predictionOrigin']) and max(ix)<min(iy)
                a,b,dr,conf,checks,reasons,ok=d.pair(data,cv,eligible,item,ix,iy,f['anchorIndex']);ref=a['reference'];nan=np.full(len(codes),np.nan)
                pb=nan.copy()
                if a['fit'] is not None:
                    fit=a['fit'];pb=np.column_stack([np.ones(len(codes)),(s.v.mean(cv[iy])-fit['mean'])/fit['sd']])@fit['beta']
                x=(a['post']-a['peer'])/ref if ref and ref>0 else nan.copy();y=(b['value']-pb)/ref if ref and ref>0 else nan.copy();change=(b['post']-a['post'])/ref if ref and ref>0 else nan.copy()
                fitmask=np.isfinite(x)&np.isfinite(y)&(a['eff']>=20)&(b['eff']>=8)&(b['n']>=8)
                pairsets.append((x[fitmask],y[fitmask]));masks.append(ok)
                ah=artifact(a,lane,item['id'],f['computedThrough'],f['name'])
                for j in range(len(codes)):
                    periods[j].append({'period':f['name'],'result':'COMPARABLE' if ok[j] else 'INSUFFICIENT','eligible':bool(ok[j]),'firstFailure':str(reasons[j]),'allFailures':[name for name,v in checks.items() if not v[j]],'x':x[j],'y':y[j],'posteriorChange':change[j],'sourceConfidence':conf[j],'sourceNSessions':int(a['n'][j]),'sourceNEff':a['eff'][j],'sourceEligibleDays':int(eligible[ix,j].sum()),'targetNSessions':int(b['n'][j]),'targetNEff':b['eff'][j],'targetEligibleDays':int(eligible[iy,j].sum()),'sourceCoverage':a['coverage'][j],'sourceUncertainty':a['sd'][j],'drift':dr[j],'computedThrough':f['computedThrough'],'predictionOrigin':f['predictionOrigin'],'targetStart':f['testStart'],'targetEnd':f['testEnd'],'sourceArtifactHash':ah})
                period_counts.append({'period':f['name'],'comparable':int(ok.sum()),'firstFailure':dict(collections.Counter(reasons.tolist()))})
            comparable=int(np.logical_and.reduce(masks).sum());assert comparable==supporting[lane,item['id']]['threePeriodComparableSymbols'],'FEASIBILITY_REGRESSION'
            current=s.snapshot(data,cv,eligible,item,np.arange(max(0,last-59),last+1));dr=s.drift(data,item['transform'],last)
            auxiliaries={str(w):s.snapshot(data,cv,eligible,item,np.arange(max(0,last-w+1),last+1)) for w in [20,250]}
            expanding=s.snapshot(data,cv,eligible,item,np.arange(last+1));ch=artifact(current,lane,item['id'],asof,'current60')
            prior=None
            if item['globalStatus']=='USABLE':
                prior=s.snapshot(data,cv,eligible,item,np.arange(max(0,prior_index-59),prior_index+1));pdr=s.drift(data,item['transform'],prior_index);ph=artifact(prior,lane,item['id'],priors[codes[0]]['asOf'],'integration60')
            tc=collections.Counter()
            for j,c in enumerate(codes):
                temporal=temporal_result(periods[j],spec);tc[temporal['status']]+=1
                def record(a,drift,at,listed,ah):
                    confidence=s.sample(a,j,drift) if listed else 'INSUFFICIENT';at_available=at[:10]+'T15:31:00+09:00'
                    return {'symbol':c,'lane':lane,'trait_id':item['id'],'globalStatus':item['globalStatus'],'sampleConfidence':confidence,'temporalReliability':temporal,'periods':periods[j],
                      'raw':a['raw'][j],'posterior':a['post'][j],'peerRelative':a['residual'][j],'peerPrediction':a['peer'][j],'nSessions':int(a['n'][j]),'nEff':a['eff'][j],'episodes':int(a['n'][j]) if item['id'] in s.v.CONDITIONAL else None,'episodeUnit':'event-bearing sessions only; individual episode counts unknown','coverage':a['coverage'][j],'shrinkWeight':a['weight'][j],
                      'uncertainty':{'posteriorSD':a['sd'][j],'referenceResidualSD':a['reference'],'CI':[a['post'][j]-1.96*a['sd'][j],a['post'][j]+1.96*a['sd'][j]]},'drift':drift,
                      'computedThrough':at,'peerArtifactThrough':at,'normalizationThrough':at,'referenceScaleThrough':at,'identityComputedThrough':at,'availableAt':at_available,'identityAvailableAt':at_available,'definitionAvailableAt':at_available,
                      'definitionHash':r.digest({key:val for key,val in item.items() if key!='globalStatus'}),'artifactHash':ah,'transform':item['transform'],'evidenceClass':'DEVELOPMENT_POSTHOC_HISTORICAL_RECONSTRUCTION_NOT_PIT_NOT_OOS','availabilityMeaning':'Logical retrospective event availability; not observed historical acquisition time','identityStatus':'DATED_MASTER_CODE_RESEARCH_ONLY' if listed else 'NOT_LISTED_AT_ASOF'}
                row=record(current,dr[j],asof,c in meta['lastMaster'],ch)
                row['stability']={'recent20Posterior':auxiliaries['20']['post'][j],'long250Posterior':auxiliaries['250']['post'][j],'expandingPosterior':expanding['post'][j],'temporal':temporal}
                profiles[c]['traits'].append(row)
                if prior is not None:
                    pr=record(prior,pdr[j],priors[c]['asOf'],c in prior_master,ph);pr['stability']={'temporal':temporal};priors[c]['traits'].append(pr)
            families.append({'lane':lane,'trait':item['id'],'globalStatus':item['globalStatus'],'threePeriodComparable':comparable,'periodCounts':period_counts,'temporal':dict(tc)})
            if item['globalStatus']=='WATCH':watches.append({'lane':lane,'trait':item['id'],**watch_mapping(pairsets,spec)})
            print(json.dumps({'formal':lane+'/'+item['id'],'comparable':comparable,'temporal':dict(tc)}),flush=True)
    profiles=s.coverage.clean(list(profiles.values()));priors=s.coverage.clean(list(priors.values()))
    coverage=contract.coverage(profiles,decision)
    assert sum(x['sampleConfidence'] in ['HIGH','MEDIUM'] for profile in profiles for x in profile['traits'] if x['globalStatus']=='USABLE')==8910
    assert coverage['oldUsableTotals']['evaluated']==36720 and coverage['all32Totals']['evaluated']==130560
    # Real forward composition on the fixed last Development day; no current-day data in Dictionary.
    integration_time=last_day+'T12:35:00+09:00';chosen=[x for x in priors if any(t['availability']=='AVAILABLE' for t in contract.payload(x,integration_time))][:3]
    minutes=pages(last_day,'minute');histories=s.read(Path(matrix)/'last-history.json.gz');integration=[]
    for profile in chosen:
        c=profile['symbol'];history=histories[c];previous=history[-1]['daily'] if history else None
        prefix=sorted([x for x in minutes if x['Code']==c and (540<=s.v.minute_time(x)<690 or 750<=s.v.minute_time(x)<755)],key=s.v.minute_time)
        context=contract.reader_context(last_day,755,prefix,previous,history,s.calendar(),profile)
        integration.append({'symbol':c,'dictionaryAsOf':profile['asOf'],'decisionTime':integration_time,'context':context})
    connections=sum(x['context']['status']=='RESEARCH_CONTEXT_AVAILABLE' and bool(x['context'].get('personality')) for x in integration)
    insufficient=[x for x in families if x['globalStatus']=='USABLE' and x['threePeriodComparable']==0]
    for x in insufficient:
        x['futureData']='More sessions/events may naturally help, but no guarantee. Fixed current Development schedule has insufficient per-symbol support; no proof of intrinsic trait impossibility and no window rescue.'
        x['minimumAdditionalDays']='UNKNOWN: symbol-specific event frequency, confidence and peer support dependent; no extra acquisition.'
    s.write(out/'01_coverage.json',coverage);s.write(out/'02_family_periods.json',families);s.write(out/'03_watch_mapping.json',watches);s.write(out/'04_insufficient_families.json',insufficient)
    s.gzwrite(out/'05_profiles.json.gz',profiles);s.gzwrite(out/'06_feature_payload.json.gz',[{'symbol':x['symbol'],'decisionTime':decision,'traits':contract.payload(x,decision)} for x in profiles]);s.write(out/'07_artifacts.json',artifacts)
    s.write(out/'08_reader_integration.json',{'tested':len(integration),'nonemptyFreshConnections':connections,'selection':'FIRST3_CODE_ORDERED_NONEMPTY_PRIOR_PROFILES_FIXED_LAST_DAY_12_35','examples':integration})
    s.write(out/'09_boundary.json',{'sourceHashes':d.verify_sources(),'adoptedSpecSHA256':protocol['adoptedSpecSHA256'],'inputLedgerSHA256':r.digest(meta['inputLedger']),'matrixSHA256':d.hashfile(Path(matrix)/'matrix.npz'),'intradayDevelopment':144,'commonHoldout':244,'commonHoldoutIntersection':sorted(observed&set(p['commonHoldout'])),'excludedIntersection':sorted(observed&set(p['excluded'])),'rawIntegrationDates':[prior_day,last_day],'providerRequests':0,'protectedPayloadReads':0,'priorExposureLedger':'UNCHANGED','safety':protocol['safety']})
    s.write(out/'10_gate_inputs.json',{'sameAsOf':asof,'dispatchableSymbols':coverage['atLeast']['1'],'dispatchableSymbolTraits':coverage['oldUsableTotals']['available'],'realReaderConnections':connections,'status':'PENDING_CONTRACTS_CI','oldGate':'BLOCKED_UNCHANGED','newEntryExitTraining':False,'productionAllowed':False})
    verify();s.write(out/'manifest.json',{x.name:d.hashfile(x) for x in sorted(out.iterdir())})

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('command',choices=['restore','measure']);p.add_argument('--archives');p.add_argument('--matrix');p.add_argument('--cache');p.add_argument('--output',required=True);a=p.parse_args()
    if a.command=='restore':restore(a.archives,a.cache,a.output)
    else:run(a.matrix,a.cache,a.output)
