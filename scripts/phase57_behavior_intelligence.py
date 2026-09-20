"""Frozen-candidate, Development-only four-track research. Never an Entry policy."""
import argparse,collections,datetime as dt,gzip,hashlib,json,math,subprocess
from pathlib import Path
import numpy as np
from scripts import phase57_sparse_handoff as s
from scripts import phase57_selector_low_high_anatomy as anatomy
from scripts import phase57_temporal_formal as formal
r=s.reader;v=s.v
ROOT=s.ROOT;BASE=ROOT/'docs/evidence/phase57-behavior-intelligence-v1'
LEDGER='docs/evidence/phase57-selector-min-price75-v1/measurement/selector/selector-ledger.json.gz'
PATHS='docs/evidence/phase57-selector-min-price75-v1/measurement/new-paths.json.gz'
SAFETY={k:False for k in ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted']}
RECENT=['previous_O','previous_H','previous_L','previous_C','body','upper_wick','lower_wick','gap','position_high','position_low','position_close','range5','volatility5','trend5','up_streak','down_streak','post_large_up','post_large_down','volume','relative_volume5','volume_shock','value','relative_value5','value_shock']
NOW=['body_s','upper_wick_s','lower_wick_s','range_s','close_pdh_s','close_pdl_s','close_vwap_s','compression_ratio','pullback_depth_vnext','rvol_trading_value','trading_value_shock','rvol_volume','orh_distance','orl_distance','swing_amplitude','swing_direction','time_fraction','event_count','PDH_BREAKOUT','PDH_FAILURE','PDL_BREAKDOWN','PDL_RECLAIM','ORH_BREAKOUT','ORH_FAILURE','ORL_BREAKDOWN','ORL_RECLAIM','VWAP_RECLAIM','VWAP_LOSS']
VARIANTS={'S0':[],'S1':['WHO'],'S2':['RECENT'],'S3':['NOW'],'S4':['WHO','RECENT','NOW'],'A12':['WHO','RECENT'],'A13':['WHO','NOW'],'A23':['RECENT','NOW'],'COVERAGE_ONLY':['COVERAGE']}
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path):return s.read(path)
def write(path,obj):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    if path.suffix=='.gz':s.gzwrite(path,obj)
    else:s.write(path,obj)
def digest(x):return hashlib.sha256(json.dumps(s.coverage.clean(x),sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
def verify():
    p=read(BASE/'protocol.json');assert sha(BASE/'protocol.json')==read(BASE/'protocol-lock.json')['sha256']
    for f,h in p['sourcePins'].items():assert sha(ROOT/f)==h,f
    for f,h in p['implementationPins'].items():assert sha(ROOT/f)==h,f
    a=s.admission.plan();assert len(a['intradayDevelopment'])==144 and len(a['commonHoldout'])==244
    assert set(p['cohortSessions'])<=set(a['intradayDevelopment']) and not set(p['cohortSessions'])&(set(a['commonHoldout'])|set(a['excluded']))
    assert p['fitSessions'][-1]<p['evaluationSessions'][0] and all(x is False for x in p['safety'].values())
    formal.verify();return p

def members(p):
    # Saved research evidence is reused; protected dates are not evaluated or projected.
    fields=['selectorEventId','sessionDate','symbol','decisionTimestamp','decisionTimeJst','decisionPrice','decisionPriceAvailableAtJst','referenceAgeMin','savedV1Score','newEligibleRank']
    rows=[{k:x[k] for k in fields} for x in read(ROOT/LEDGER)['new'] if x['sessionDate'] in p['cohortSessions']]
    rows.sort(key=lambda x:x['selectorEventId']);assert len(rows)==p['candidateCount'] and digest(rows)==p['cohortSHA256']
    return rows

def restore(archives,cache,output):
    p=verify();selected=set(p['cohortSessions']);receipts=[]
    for f in sorted(Path(archives).rglob('*.tar.gz.enc')):
        expected=f.with_name(f.name+'.sha256').read_text().split()[0];assert sha(f)==expected
        proc=subprocess.Popen(['openssl','enc','-d','-aes-256-cbc','-pbkdf2','-iter','200000','-pass','env:JQUANTS_API_KEY','-in',str(f)],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        try:receipt=s.admission.base.extract_stream(proc.stdout,cache,selected)
        finally:proc.stdout.close();err=proc.stderr.read();code=proc.wait()
        assert code==0,'DECRYPT_FAILED'
        assert set(receipt['selectedDates'])<=selected
        receipts.append({'archiveSHA256':expected,**receipt})
    assert receipts;write(output,{'receipts':receipts,'rawDatesRead':sorted(selected),'newAcquisition':0,'protectedExtraction':0})

def recent_context(day,decision_price,prefix,history,calendar):
    out={'status':'UNAVAILABLE','reason':None,'computedThrough':None,'features':{k:None for k in RECENT}}
    hist=r.history_adapter(history,day);prevday=calendar[calendar.index(day)-1]
    if not hist or hist[-1]['session']!=prevday or not v.valid(hist[-1].get('daily')):
        out['reason']='EXACT_PREVIOUS_SESSION_UNAVAILABLE';return out
    prev=hist[-1]['daily'];out['computedThrough']=prevday+'T15:30:00+09:00'
    if v.action(prev):out['reason']='CORPORATE_ACTION';return out
    assert prev['Date']<day
    f=out['features'];c=prev['C'];O,H,L=prev['O'],prev['H'],prev['L']
    f.update(previous_O=O,previous_H=H,previous_L=L,previous_C=c,body=100*(c-O)/c,upper_wick=100*(H-max(c,O))/c,lower_wick=100*(min(c,O)-L)/c,position_high=100*(decision_price/H-1),position_low=100*(decision_price/L-1),position_close=100*(decision_price/c-1),volume=prev.get('Vo'),value=prev.get('Va'))
    opening=next((x for x in prefix if v.minute_time(x)==540 and v.valid(x)),None)
    f['gap']=100*(opening['O']/c-1) if opening else None
    ds=[h.get('daily') for h in hist[-6:]]
    if len(ds)==6 and all(v.valid(x) and not v.action(x) for x in ds):
        returns=np.array([100*(b['C']/a['C']-1) for a,b in zip(ds,ds[1:])])
        up=down=0
        for ret in returns[::-1]:
            if ret<=0:break
            up+=1
        for ret in returns[::-1]:
            if ret>=0:break
            down+=1
        f.update(range5=100*(max(d['H'] for d in ds[-5:])/min(d['L'] for d in ds[-5:])-1),volatility5=float(np.std(returns)),trend5=100*(ds[-1]['C']/ds[0]['C']-1),up_streak=up,down_streak=down,post_large_up=float(returns[-1]>=3),post_large_down=float(returns[-1]<=-3))
        for raw,name in [('Vo','volume'),('Va','value')]:
            xs=[d.get(raw) for d in ds[:-1]]
            ratio=ds[-1][raw]/float(np.mean(xs)) if all(v.num(x) and x>0 for x in xs) and v.num(ds[-1].get(raw)) else None
            f['relative_'+name+'5']=ratio;f[name+'_shock']=float(ratio>=2) if ratio is not None else None
    out.update(status='AVAILABLE',reason=None);return out

def now_context(day,minute,prefix,previous,history,calendar):
    try:x=r.context(day,minute,prefix,previous,history,calendar)
    except ValueError as exc:x={'status':'UNAVAILABLE','missingReason':'REJECTED_'+str(exc),'features':{}}
    f={k:None for k in NOW}
    if x['status']=='RESEARCH_CONTEXT_AVAILABLE':
        f.update({k:x['features'].get(k) for k in NOW});bars=v.bars5(day,prefix);last=bars[-1];unit=previous['C']*x['scaleS']
        for key,level in [('orh_distance','opening_range_high'),('orl_distance','opening_range_low')]:
            ref=x['features'].get(level);f[key]=(last['C']-ref)/unit if ref is not None else None
        swings=x.get('confirmedSwings',[])
        if swings:f.update(swing_amplitude=swings[-1]['amplitude'],swing_direction=swings[-1]['direction'])
        f.update(time_fraction=(minute-540)/(390 if day>='2024-11-05' else 360),event_count=len(x['events']))
        for event in NOW[18:]:f[event]=float(any(e['type']==event for e in x['events']))
        assert all(e['availableAt']<=minute for e in x['events'])
    return {'status':x['status'],'reason':x['missingReason'],'computedThrough':day+'T%02d:%02d:00+09:00'%divmod(minute,60) if x['status']=='RESEARCH_CONTEXT_AVAILABLE' else None,'features':f,'reader':x}

def who_day(meta,z,day,candidates):
    days=meta['sessions'];end=days.index(day)-1;through=days[end]+'T15:30:00+09:00' if end>=0 else None
    index={c:j for j,c in enumerate(meta['codes'])};out={c:[] for c in candidates}
    for lane,items in meta['targets'].items():
        cv=z['cov'].copy()
        if lane=='intraday':cv[:,:,3]=z['intraCoverage']
        for k,item in enumerate(items):
            if item['globalStatus']!='USABLE':continue
            # Entire tensor is clipped BEFORE profiling: peers/scalers/drift cannot read suffix.
            data=z[lane][:end+1,:,k];cov=cv[:end+1];eligible=z['eligible'][:end+1,:,0 if item['tier']=='daily' else 1].copy()
            if lane=='intraday':eligible &= np.array([d in s.admission.plan()['intradayDevelopment'] for d in days[:end+1]])[:,None]
            assert len(data)==end+1 and days[end]<day
            a=s.snapshot(data,cov,eligible,item,np.arange(max(0,end-59),end+1));dr=s.drift(data,item['transform'],end)
            for code in candidates:
                j=index[code];confidence=s.sample(a,j,dr[j]);cell={'family':lane+'/'+item['id'],'value':None,'diagnosticPastOnlyRawValue':a['raw'][j],'availability':'UNAVAILABLE','sampleConfidence':confidence,'temporalReliability':'MISSING_NOT_YET_AVAILABLE','uncertainty':a['sd'][j],'nEff':a['eff'][j],'nSessions':int(a['n'][j]),'coverage':a['coverage'][j],'drift':dr[j],'computedThrough':through,'definitionHash':digest(item),'evidenceClass':'DEVELOPMENT_HISTORICAL_RECONSTRUCTION_NOT_PIT_NOT_OOS','reason':'FORMAL_TEMPORAL_ARTIFACT_NOT_AVAILABLE_AT_DECISION'}
                # This locked exact-ledger cohort predates even the first formal period.
                assert day<'2025-08-22'
                out[code].append(s.coverage.clean(cell))
    return out

def substrate(cache,matrix,output):
    p=verify();out=Path(output);out.mkdir(parents=True,exist_ok=False);ms=members(p);byday=collections.defaultdict(list)
    for m in ms:byday[m['sessionDate']].append(m)
    meta=read(Path(matrix)/'metadata.json');z=np.load(Path(matrix)/'matrix.npz');allowed=set(s.admission.plan()['dailyDevelopment'])|set(s.admission.plan()['intradayDevelopment'])
    assert meta['hashes']==s.invariants()
    assert {x['session'] for x in meta['inputLedger']}<=allowed
    pins={(x['session'],x['kind']):x['sha256'] for x in meta['inputLedger']}
    allcodes=sorted({x['symbol'] for x in ms});histories={c:[] for c in allcodes};calendar=s.calendar();ledger=[];rows=[];audit=collections.Counter();last=None
    for day in p['cohortSessions']:
        if last is None or calendar.index(day)!=calendar.index(last)+1:histories={c:[] for c in allcodes}
        def pages(kind):
            s.admission.authorize(day,kind);f=Path(cache)/day/(kind+'-pages.json');assert sha(f)==pins[day,kind],(day,kind)
            data,receipt=v.saved.pages(f);assert all(x['Date']==day for x in data)
            ledger.append({'session':day,'kind':kind,'sha256':sha(f)});return data
        # Current daily is deliberately opened only AFTER all current decisions.
        master=pages('master');universe={x['Code'] for x in master if str(x.get('Mkt')) in ['0111','0112','0113'] and str(x.get('ProdCat'))=='011'}
        by=collections.defaultdict(list)
        for row in pages('minute'):
            if row['Code'] in histories:by[row['Code']].append(row)
        for code in by:by[code].sort(key=v.minute_time)
        who=who_day(meta,z,day,{m['symbol'] for m in byday[day]})
        for m in byday[day]:
            code=m['symbol'];minute=int(m['decisionTimeJst'][:2])*60+int(m['decisionTimeJst'][3:]);hist=histories[code];previous=hist[-1]['daily'] if hist else None
            close=900 if day<'2024-11-05' else 925
            prefix=[x for x in by[code] if v.minute_time(x)<minute and (540<=v.minute_time(x)<690 or 750<=v.minute_time(x)<close)]
            assert all(x['Date']==day and v.minute_time(x)+1<=minute for x in prefix)
            daily=recent_context(day,m['decisionPrice'],prefix,hist,calendar)
            now=now_context(day,minute,prefix,previous,hist,calendar)
            assert all(r.timestamp(c['computedThrough'])<r.timestamp(m['decisionTimestamp']) for c in who[code])
            assert daily['computedThrough'] is None or r.timestamp(daily['computedThrough'])<r.timestamp(m['decisionTimestamp'])
            rows.append({'member':m,'WHO':who[code],'RECENT':daily,'NOW':now,'listedAtDecision':code in universe})
            audit['candidates']+=1;audit['RECENT_'+daily['status']]+=1;audit['NOW_'+now['status']]+=1
            audit['WHO_available_candidates']+=any(c['availability']=='AVAILABLE' for c in who[code])
        dc={x['Code']:x for x in pages('daily')}
        for code in allcodes:
            hist=histories[code];d=dc.get(code) if code in universe else None;prev=hist[-1]['daily'] if hist else None;scale=v.scale(hist)
            entry={'session':day,'daily':d,'tr':None,'Va':d['Va'] if v.valid(d) else None,'C':d['C'] if v.valid(d) else None,'s':scale,'ret':None}
            if v.valid(d) and v.valid(prev) and not v.action(d) and not v.action(prev):entry.update(tr=max(d['H']-d['L'],abs(d['H']-prev['C']),abs(d['L']-prev['C']))/prev['C'],ret=d['C']/prev['C']-1)
            bars=v.bars5(day,by[code]) if all(v.valid(b) for b in by[code]) else [];entry['barValues']={b['t']:b['Va'] for b in bars};entry['barVolumes']={b['t']:b['Vo'] for b in bars}
            hist.append(entry);histories[code]=hist[-10:]
        last=day;print(json.dumps({'substrate':day,'rows':len(rows),'WHOavailable':audit['WHO_available_candidates']}),flush=True)
    write(out/'features.json.gz',rows);write(out/'input-ledger.json',ledger)
    write(out/'audit.json',{'counts':dict(audit),'sourceFeatureOnly':True,'dictionaryPrefixOnly':True,'recentPreviousDayOnly':True,'intradayClosedBarOnly':True,'formalTemporalNoBackfill':True,'sameAsOf':True,'commonHoldoutOpened':0,'sealedOpened':0,'selectorUnchanged':True,'sourceMatrixLedgerSHA256':digest(meta['inputLedger']),'safety':SAFETY})
    write(out/'manifest.json',{x.name:sha(x) for x in sorted(out.iterdir())})

def labels_for(m,path):
    full=anatomy.evaluate(path,m);res={'fullStatus':full['status'],'maeEnd':full['selectionToLowPct'],'mfeEnd':full['selectionToHighPct'],'returnEnd':full['sessionEndReturnPct'],'order':full['order']}
    decision=r.timestamp(m['decisionTimestamp']);start=int(m['decisionTimeJst'][:2])*60+int(m['decisionTimeJst'][3:]);close=900 if m['sessionDate']<'2024-11-05' else 930
    mapping={x['start']:x for x in path['future']}
    for h in [30,60]:
        name=str(h);res.update({k+name:None for k in ['mae','mfe','return']})
        if start+h>close or start==690 or start<690<start+h:continue
        slots=[(decision+dt.timedelta(minutes=i)).isoformat() for i in range(0,h,5)];bars=[mapping.get(t) for t in slots]
        if any(not b or b.get('missing') or any(not isinstance(b.get(k),(int,float)) or not math.isfinite(b[k]) for k in ['o','h','l','c']) for b in bars):continue
        res.update({'mae'+name:min(0,min(b['l'] for b in bars)),'mfe'+name:max(0,max(b['h'] for b in bars)),'return'+name:bars[-1]['c']})
    return res

def feature_vector(row,families):
    out={}
    for family in families:
        if family in ['RECENT','NOW']:
            out.update({family+'/'+k:row[family]['features'].get(k) for k in (RECENT if family=='RECENT' else NOW)})
        elif family=='WHO':
            for c in row['WHO']:
                prefix='WHO/'+c['family']+'/'
                out[prefix+'value']=c['value']
                # Unreliable numeric trait estimates are NEVER used as personality values.
                for state in ['HIGH','MEDIUM','LOW','INSUFFICIENT']:out[prefix+'confidence_'+state]=float(c['sampleConfidence']==state)
                for state in ['PASS','FAIL','INSUFFICIENT','MISSING_NOT_YET_AVAILABLE']:out[prefix+'temporal_'+state]=float(c['temporalReliability']==state)
                for key in ['uncertainty','nEff','coverage']:out[prefix+key]=c[key]
        else:
            for c in row['WHO']:out['COVERAGE/'+c['family']]=float(c['availability']=='AVAILABLE')
    return out

def fit_score(train,query,y,lambda_=10):
    names=sorted(set().union(*(x.keys() for x in train)))
    x=np.array([[r.get(k) if r.get(k) is not None else np.nan for k in names] for r in train],float)
    q=np.array([[r.get(k) if r.get(k) is not None else np.nan for k in names] for r in query],float)
    nvalid=np.isfinite(x).sum(0);med=np.array([np.median(x[np.isfinite(x[:,i]),i]) if nvalid[i] else 0 for i in range(len(names))])
    # Numerical design-matrix imputation is separate from the persisted null/value contract.
    missing=~np.isfinite(x);qmissing=~np.isfinite(q);x=np.where(missing,med,x);q=np.where(qmissing,med,q)
    mu=x.mean(0);sd=x.std(0);sd=np.where(sd>1e-8,sd,1)
    x=np.column_stack([(x-mu)/sd,missing.astype(float)]);q=np.column_stack([(q-mu)/sd,qmissing.astype(float)])
    center=x.mean(0);x-=center;q-=center;ym=float(np.mean(y));weights=np.linalg.solve(x.T@x+lambda_*np.eye(x.shape[1]),x.T@(np.array(y)-ym))
    return q@weights+ym,{'names':names,'median':med.tolist(),'mean':mu.tolist(),'scale':sd.tolist(),'designCenter':center.tolist(),'weights':weights.tolist(),'intercept':ym,'lambda':lambda_,'allMissingFitColumns':[names[i] for i in range(len(names)) if nvalid[i]==0],'sampleN':len(train)}

def retain(rows,scores,fraction,variant):
    groups=collections.defaultdict(list)
    for i,row in enumerate(rows):groups[row['member']['decisionTimestamp']].append(i)
    keep=set();fallback=0
    for stamp,ix in sorted(groups.items()):
        if variant=='S0' or fraction==1:keep.update(ix);continue
        # Dictionary absence alone can NEVER drop a candidate in WHO-only mode.
        forced=[i for i in ix if variant=='S1' and not any(c['availability']=='AVAILABLE' for c in rows[i]['WHO'])]
        n=max(len(forced),int(math.ceil(len(ix)*fraction)));rest=[i for i in ix if i not in forced]
        rest.sort(key=lambda i:(float(scores[i]),rows[i]['member']['selectorEventId']))
        keep.update(forced+rest[:max(0,n-len(forced))]);fallback+=len(forced)
    return keep,fallback

def dist(values):
    x=np.array([v for v in values if v is not None and math.isfinite(v)],float)
    if not len(x):return {'n':0,**{k:None for k in ['mean','median','p01','p05','p10','p25','p75','p90','p95','p99','worst5Mean','worst5Median']}}
    tail=x[x<=np.quantile(x,.05)]
    return {'n':len(x),'mean':float(x.mean()),'median':float(np.median(x)),**{'p'+str(int(q*100)).zfill(2):float(np.quantile(x,q)) for q in [.01,.05,.1,.25,.75,.9,.95,.99]},'worst5Mean':float(tail.mean()),'worst5Median':float(np.median(tail))}

def panel(rows,labels,keep):
    common=[i for i,y in enumerate(labels) if y['mae30'] is not None and y['mfeEnd'] is not None];selected=[i for i in common if i in keep];n=len(selected)
    out={'allCandidates':len(rows),'retainedAllCandidates':len(keep),'commonCohortN':len(common),'retainedCommonN':n,'commonCohortSHA256':digest([rows[i]['member']['selectorEventId'] for i in common]),'missingOutcomeN':len(rows)-len(common),'metrics':{k:dist([labels[i][k] for i in selected]) for k in ['mae30','mae60','maeEnd','mfeEnd','return30','return60','returnEnd']}}
    for k in [1,2,3]:out['downside'+str(k)]=100*sum(labels[i]['mae30']<=-k for i in selected)/n if n else None
    out['positiveRate']=100*sum(labels[i]['return30']>0 for i in selected)/n if n else None
    out['utilityMean']=float(np.mean([labels[i]['return30']+labels[i]['mae30'] for i in selected])) if n else None
    out['preservation']={};out['lowThenHighRetention']={}
    for k in [1,2,3,5]:
        winner=[i for i in common if labels[i]['mfeEnd']>=k];hits=sum(i in keep for i in winner)
        out['preservation'][str(k)]={'baselineWinners':len(winner),'retainedWinners':hits,'pct':100*hits/len(winner) if winner else None}
        if k in [3,5]:
            lh=[i for i in winner if labels[i]['order']=='LOW_THEN_HIGH'];hits=sum(i in keep for i in lh)
            out['lowThenHighRetention'][str(k)]={'baselineWinners':len(lh),'retainedWinners':hits,'pct':100*hits/len(lh) if lh else None}
    counts=collections.Counter(rows[i]['member']['symbol'] for i in selected)
    out['symbolConcentration']={'symbols':len(counts),'HHI':sum((v/n)**2 for v in counts.values()) if n else None,'top10':counts.most_common(10)}
    return out

def paired_effect(rows,labels,keep,basekeep):
    sessions=sorted({x['member']['sessionDate'] for x in rows});effects=[]
    for day in sessions:
        ix=[i for i,x in enumerate(rows) if x['member']['sessionDate']==day and labels[i]['mae30'] is not None and labels[i]['mfeEnd'] is not None]
        a=[labels[i]['mae30']<=-2 for i in ix if i in keep];b=[labels[i]['mae30']<=-2 for i in ix if i in basekeep]
        if a and b:effects.append(float(np.mean(b)-np.mean(a))*100)
    rng=np.random.default_rng(570920);n=len(effects);boot=[]
    if n>=10:
        for _ in range(1000):
            starts=rng.integers(0,n,size=math.ceil(n/5));ix=[(start+j)%n for start in starts for j in range(5)][:n];boot.append(np.mean(np.array(effects)[ix]))
    return {'sessions':n,'meanReductionPp':float(np.mean(effects)) if effects else None,'movingBlock5CI95':np.quantile(boot,[.025,.975]).tolist() if boot else None,'positiveSessionRate':float(np.mean(np.array(effects)>0)) if effects else None,'inference':'DESCRIPTIVE_REUSED_DEVELOPMENT_NOT_CONFIRMATORY; correlated overlapping events clustered by session'}

def measure(substrate_dir,output):
    p=verify();out=Path(output);out.mkdir(parents=True,exist_ok=False);src=Path(substrate_dir)
    for name,h in read(src/'manifest.json').items():assert sha(src/name)==h
    rows=read(src/'features.json.gz');assert [x['member'] for x in sorted(rows,key=lambda x:x['member']['selectorEventId'])]==members(p)
    source={x['selectorEventId']:x for x in read(ROOT/PATHS)['events'] if x['sessionDate'] in p['cohortSessions']}
    labels=[labels_for(x['member'],source[x['member']['selectorEventId']]) for x in rows]
    fit=[i for i,x in enumerate(rows) if x['member']['sessionDate'] in p['fitSessions']];ev=[i for i,x in enumerate(rows) if x['member']['sessionDate'] in p['evaluationSessions']]
    erows=[rows[i] for i in ev];elabels=[labels[i] for i in ev];models={};pred={};quality={};summaries={};sets={};session_panels={};coverage={}
    for variant,families in VARIANTS.items():
        if variant=='S0':pred[variant]=np.array([-x['member']['savedV1Score'] for x in erows]);quality[variant]=-pred[variant];models[variant]={'frozenOnly':True};continue
        vec=[feature_vector(x,families) for x in rows];targetfit=[i for i in fit if labels[i]['mae30'] is not None]
        assert len(targetfit)>=p['minimumFitRows'] and len({rows[i]['member']['sessionDate'] for i in targetfit})>=p['minimumFitSessions']
        score,model=fit_score([vec[i] for i in targetfit],[vec[i] for i in ev],[-labels[i]['mae30'] for i in targetfit],p['ridgeLambda'])
        qfit=[i for i in fit if labels[i]['mfeEnd'] is not None];qs,qm=fit_score([vec[i] for i in qfit],[vec[i] for i in ev],[labels[i]['mfeEnd'] for i in qfit],p['ridgeLambda'])
        pred[variant]=score;quality[variant]=qs;models[variant]={'risk':model,'quality':qm,'fitThrough':p['fitSessions'][-1]+'T15:30:00+09:00','availability':'STATE_ONLY_NO_RELIABLE_TRAIT_VALUES' if variant=='S1' else 'RESEARCH_SCORE'}
    for variant in VARIANTS:
        summaries[variant]={};sets[variant]={}
        for fraction in p['retentionFractions']:
            keep,fallback=retain(erows,pred[variant],fraction,variant);sets[variant][str(fraction)]=keep
            summaries[variant][str(fraction)]={**panel(erows,elabels,keep),'dictionaryUnavailableForceRetained':fallback}
        keep=sets[variant]['0.8'];session_panels[variant]={}
        for day in p['evaluationSessions']:
            ix=[i for i,row in enumerate(erows) if row['member']['sessionDate']==day]
            session_panels[variant][day]=panel([erows[i] for i in ix],[elabels[i] for i in ix],{j for j,i in enumerate(ix) if i in keep})
    # Identical-count frozen-score and seeded hash controls; no outcome-based budgets.
    controls={};controlsets={}
    for name,scores in [('FROZEN_SCORE',pred['S0']),('HASH_RANDOM',np.array([int(hashlib.sha256(('570920|'+x['member']['selectorEventId']).encode()).hexdigest()[:12],16) for x in erows]))]:
        keep,_=retain(erows,scores,.8,name);controls[name]=panel(erows,elabels,keep);controlsets[name]=keep
    effects={k:paired_effect(erows,elabels,sets[k]['0.8'],controlsets['FROZEN_SCORE']) for k in VARIANTS if k!='S0'}
    effects['S4_vs_A23']=paired_effect(erows,elabels,sets['S4']['0.8'],sets['A23']['0.8'])
    effects['S4_vs_S2']=paired_effect(erows,elabels,sets['S4']['0.8'],sets['S2']['0.8']);effects['S4_vs_S3']=paired_effect(erows,elabels,sets['S4']['0.8'],sets['S3']['0.8'])
    for state in ['usable','unavailable','HIGH_PASS','MEDIUM_PASS','LOW','FAIL','INSUFFICIENT','MISSING']:
        def has(row):
            cells=row['WHO']
            if state=='usable':return any(c['availability']=='AVAILABLE' for c in cells)
            if state=='unavailable':return not any(c['availability']=='AVAILABLE' for c in cells)
            if state.endswith('_PASS'):return any(c['sampleConfidence']==state.split('_')[0] and c['temporalReliability']=='PASS' for c in cells)
            if state=='LOW':return any(c['sampleConfidence']=='LOW' for c in cells)
            if state=='INSUFFICIENT':return any(c['sampleConfidence']=='INSUFFICIENT' or c['temporalReliability']=='INSUFFICIENT' for c in cells)
            return any(c['temporalReliability']==('MISSING_NOT_YET_AVAILABLE' if state=='MISSING' else state) for c in cells)
        ix=[i for i,row in enumerate(erows) if has(row)]
        coverage[state]={'n':len(ix),'symbols':len({erows[i]['member']['symbol'] for i in ix}),'panels':{k:panel([erows[i] for i in ix],[elabels[i] for i in ix],{j for j,i in enumerate(ix) if i in sets[k]['0.8']}) for k in VARIANTS}}
    decisions={};baseline=summaries['S0']['0.8']
    for k,name in [('S1','DICTIONARY'),('S2','RECENT_DAILY'),('S3','INTRADAY'),('S4','COMBINED')]:
        row=summaries[k]['0.8'];effect=effects[k];ci=effect['movingBlock5CI95'];pres=[row['preservation'][str(t)]['pct'] for t in [3,5]]
        if k=='S1':status='INCONCLUSIVE';reason='No causally available formal traits in exact frozen cohort; state-only score is auxiliary and WHO-only keeps unavailable candidates.'
        elif any(x is None for x in pres) or ci is None:status='INCONCLUSIVE';reason='Insufficient paired sessions or winner denominator.'
        elif effect['meanReductionPp']>0 and min(pres)<p['minimumPreservationPct']:status='DOWNSIDE_REDUCTION_COSTS_TOO_MUCH_UPSIDE';reason='Positive downside separation but +3/+5 retention below precommitted90%.'
        elif ci[0]>0 and effect['meanReductionPp']>=p['minimumDownsideReductionPp'] and min(pres)>=p['minimumPreservationPct']:
            status=name+'_ADDS_DOWNSIDE_INFORMATION';reason='Fixed primary thresholds satisfied vs equal-budget frozen-score control.'
        else:status='NO_MEANINGFUL_INCREMENTAL_INFORMATION';reason='Precommitted effect/support/preservation thresholds not all met; absence of evidence is not proof of no information.'
        if k=='S4' and status=='COMBINED_ADDS_DOWNSIDE_INFORMATION':
            inc=[effects['S4_vs_'+q] for q in ['A23','S2','S3']]
            if all(x['movingBlock5CI95'] and x['movingBlock5CI95'][0]>0 and x['meanReductionPp']>=p['minimumDownsideReductionPp'] for x in inc):status='COMBINED_ADDS_INCREMENTAL_INFORMATION'
            else:status='NO_MEANINGFUL_INCREMENTAL_INFORMATION';reason='Combined does not satisfy fixed incremental evidence requirement over RECENT+NOW and both single-source arms.'
        decisions[k]={'status':status,'reason':reason}
    score_rows=[{'member':x['member'],'labels':elabels[i],'riskScores':{k:float(pred[k][i]) for k in VARIANTS},'qualityScores':{k:float(quality[k][i]) for k in VARIANTS},'retained80':{k:i in sets[k]['0.8'] for k in VARIANTS},'WHOusable':any(c['availability']=='AVAILABLE' for c in x['WHO'])} for i,x in enumerate(erows)]
    write(out/'comparison.json',summaries);write(out/'controls.json',controls);write(out/'effects.json',effects);write(out/'session-panels.json',session_panels);write(out/'coverage.json',coverage);write(out/'decisions.json',decisions);write(out/'models.json',models);write(out/'evaluation-ledger.json.gz',score_rows)
    write(out/'cohort.json',{'developmentAuthorizedSessions':144,'exactFrozenCandidateSessions':55,'notRegeneratedSessions':89,'fitSessions':p['fitSessions'],'embargoSessions':p['embargoSessions'],'evaluationSessions':p['evaluationSessions'],'candidateCount':len(rows),'fitCandidates':len(fit),'evaluationCandidates':len(ev),'sourceSHA256':p['cohortSHA256'],'scope':'Exact frozen selected identities only; NO claim of 144-session coverage. Inherited Selector and dictionary definitions reused Development and are not independent OOS.'})
    write(out/'audit.json',{'substrate':read(src/'audit.json'),'cohort':p['cohortSHA256'],'scoreFitBeforeEvaluation':True,'rawInputsFromDevelopmentOnly':True,'noThresholdSearch':True,'noEntryExitTraining':True,'newSealedExposure':0,'safety':SAFETY,'limitations':['WHO reliable-value effect unidentifiable: zero available traits before2025-08-22','89 authorized sessions have no saved frozen candidate ledger and are not evaluated','Frozen upstream model/registry historically reused Development: no claim of independent prospective performance','Raw records are retrospective reconstruction; acquisition-time PIT is not verified']})
    write(out/'manifest.json',{x.name:sha(x) for x in sorted(out.iterdir())})

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('command',choices=['verify','restore','substrate','measure']);parser.add_argument('--archives');parser.add_argument('--cache');parser.add_argument('--matrix');parser.add_argument('--substrate');parser.add_argument('--output');args=parser.parse_args()
    if args.command=='verify':verify();print('PRECOMMIT_VERIFIED')
    elif args.command=='restore':restore(args.archives,args.cache,args.output)
    elif args.command=='substrate':substrate(args.cache,args.matrix,args.output)
    else:measure(args.substrate,args.output)
