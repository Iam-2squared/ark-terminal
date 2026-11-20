"""Full manifest Development diagnostic. Frozen upstream; causal additional inputs."""
import argparse,collections,datetime as dt,hashlib,json,math,subprocess,tempfile
from pathlib import Path
import numpy as np
from scripts import phase57_behavior_intelligence as b
s=b.s;r=b.r;v=b.v
ROOT=b.ROOT;BASE=ROOT/'docs/evidence/phase57-behavior-full144-v1'
SAFETY=b.SAFETY;RECENT=b.RECENT;NOW=b.NOW;VARIANTS=b.VARIANTS
sha=b.sha;read=b.read;write=b.write;digest=b.digest
feature_vector=b.feature_vector;fit_score=b.fit_score;retain=b.retain;panel=b.panel;paired_effect=b.paired_effect

def verify():
 p=read(BASE/'protocol.json');assert sha(BASE/'protocol.json')==read(BASE/'protocol-lock.json')['sha256']
 for f,h in p['sourcePins'].items():assert sha(ROOT/f)==h,f
 for f,h in p['implementationPins'].items():assert sha(ROOT/f)==h,f
 plan=s.admission.plan();assert p['cohortSessions']==plan['intradayDevelopment'] and len(p['cohortSessions'])==144
 assert p['fitSessions']+p['embargoSessions']+p['evaluationSessions']==p['cohortSessions']
 assert len(plan['commonHoldout'])==244;assert all(x is False for x in p['safety'].values());b.formal.verify();return p

def who_day(meta,z,day,candidates,temporal):
 days=meta['sessions'];end=days.index(day)-1;through=days[end]+'T15:30:00+09:00';index={c:j for j,c in enumerate(meta['codes'])};out={c:[] for c in candidates}
 for lane,items in meta['targets'].items():
  cv=z['cov'][:end+1].copy()
  if lane=='intraday':cv[:,:,3]=z['intraCoverage'][:end+1]
  for k,item in enumerate(items):
   if item['globalStatus']!='USABLE':continue
   data=z[lane][:end+1,:,k];eligible=z['eligible'][:end+1,:,0 if item['tier']=='daily' else 1].copy()
   if lane=='intraday':eligible &= np.array([d in s.admission.plan()['intradayDevelopment'] for d in days[:end+1]])[:,None]
   a=s.snapshot(data,cv,eligible,item,np.arange(max(0,end-59),end+1));dr=s.drift(data,item['transform'],end)
   for code in candidates:
    if code not in index:
     out[code].append({'family':lane+'/'+item['id'],'value':None,'traitValue':None,'availability':'UNAVAILABLE','sampleConfidence':'INSUFFICIENT','temporalReliability':'MISSING_NOT_YET_AVAILABLE','uncertainty':None,'nEff':0,'coverage':0,'computedThrough':through,'evidenceClass':'MISSING_INPUT','reason':'SYMBOL_NOT_IN_MATRIX'});continue
    j=index[code];confidence=s.sample(a,j,dr[j]);tr=temporal.get((code,lane,item['id']));status='MISSING_NOT_YET_AVAILABLE'
    if tr and r.timestamp(tr['availableAt'])<r.timestamp(day+'T09:00:00+09:00'):status=tr['status']
    usable=confidence in ['HIGH','MEDIUM'] and status=='PASS' and np.isfinite(a['post'][j])
    cell={'family':lane+'/'+item['id'],'value':a['post'][j] if usable else None,'traitValue':a['post'][j],'diagnosticPastOnlyRawValue':a['raw'][j],'availability':'AVAILABLE' if usable else 'UNAVAILABLE','sampleConfidence':confidence,'temporalReliability':status,'temporalComputedThrough':tr['computedThrough'] if status!='MISSING_NOT_YET_AVAILABLE' else None,'uncertainty':a['sd'][j],'nEff':a['eff'][j],'nSessions':int(a['n'][j]),'coverage':a['coverage'][j],'computedThrough':through,'evidenceClass':'DEVELOPMENT_HISTORICAL_RECONSTRUCTION_NOT_PIT_NOT_OOS','reason':None if usable else ('WHO_UNAVAILABLE_WARMUP' if status=='MISSING_NOT_YET_AVAILABLE' else 'FORMAL_OR_CONFIDENCE_GATE')}
    out[code].append(s.coverage.clean(cell))
 return out

def labels_for_raw(m,raw,daily):
 """Separate strict horizon and source-reconciled full-session outcomes; no synthetic bars."""
 day=m['sessionDate'];start=int(m['decisionTimeJst'][:2])*60+int(m['decisionTimeJst'][3:]);close=900 if day<'2024-11-05' else 930;continuous=900 if close==900 else 925;price=m['decisionPrice']
 rows=sorted(raw,key=v.minute_time);valid=[x for x in rows if v.valid(x)];ts=[v.minute_time(x) for x in valid]
 assert len(ts)==len(set(ts)),'DUPLICATE_SOURCE'
 vols=sum(x['Vo'] for x in valid)
 recon=bool(v.valid(daily) and valid and len(valid)==len(rows) and abs(vols-daily['Vo'])<=max(1e-6,abs(daily['Vo'])*1e-9) and abs(max(x['H'] for x in valid)-daily['H'])<=1e-6 and abs(min(x['L'] for x in valid)-daily['L'])<=1e-6)
 future=[x for x in valid if (v.minute_time(x)>start if v.minute_time(x) in [690,close] else v.minute_time(x)>=start) and (540<=v.minute_time(x)<690 or 750<=v.minute_time(x)<continuous or v.minute_time(x) in [690,close])]
 # A frozen 15:00 pre-extension decision has no measurable future session.
 auction=next((x for x in valid if v.minute_time(x)==close),None)
 def metrics(xs):
  return (min(0,min(100*(x['L']/price-1) for x in xs)),max(0,max(100*(x['H']/price-1) for x in xs)),100*(xs[-1]['C']/price-1))
 out={'fullStatus':'UNAVAILABLE','fullReason':'SOURCE_DAILY_RECONCILIATION_FAILED' if not recon else 'TERMINAL_AUCTION_OR_FUTURE_UNAVAILABLE','dailySourceReconciled':recon,'maeEnd':None,'mfeEnd':None,'returnEnd':None,'order':'UNKNOWN'}
 if recon and auction and start<close and future:
  lo,hi,ret=metrics(future);li=next(i for i,x in enumerate(future) if x['L']==min(y['L'] for y in future));hi_i=next(i for i,x in enumerate(future) if x['H']==max(y['H'] for y in future))
  out.update(fullStatus='AVAILABLE',fullReason=None,maeEnd=lo,mfeEnd=hi,returnEnd=ret,order='LOW_THEN_HIGH' if li<hi_i else 'HIGH_THEN_LOW' if hi_i<li else 'UNKNOWN_SAME_MINUTE')
 for h in [30,60]:
  suffix=str(h);out.update({k+suffix:None for k in ['mae','mfe','return']});out['reason'+suffix]='LUNCH_OR_SESSION_BOUNDARY'
  end=start+h
  if end>close or start==690 or start<690<end:continue
  slots=[t for t in range(start,end,5) if 540<=t<690 or 750<=t<continuous]
  # Existing strict five-minute slot existence; no-trade minutes are not invented.
  missing=[t for t in slots if not any(t<=v.minute_time(x)<t+5 for x in valid)]
  xs=[x for x in future if (v.minute_time(x)<=end if v.minute_time(x) in [690,close] else v.minute_time(x)<end)]
  end_ok=any(v.minute_time(x)==end for x in xs) if end in [690,close] else any(end-5<=v.minute_time(x)<end for x in xs)
  if missing or not xs or not end_ok:out['reason'+suffix]='MISSING_REQUIRED_SOURCE_SLOT_OR_ENDPOINT';continue
  lo,hi,ret=metrics(xs);out.update({'mae'+suffix:lo,'mfe'+suffix:hi,'return'+suffix:ret,'reason'+suffix:None})
 return out

def substrate(cache,matrix,output):
 p=verify();out=Path(output);out.mkdir(parents=True,exist_ok=False);cal=s.calendar();days=p['cohortSessions'];allowed=set(days)
 saved=[{k:x[k] for k in ['selectorEventId','sessionDate','symbol','decisionTimestamp','decisionTimeJst','decisionPrice','decisionPriceAvailableAtJst','referenceAgeMin','savedV1Score','newEligibleRank']} for x in read(ROOT/b.LEDGER)['new'] if x['sessionDate'] in allowed]
 bysaved=collections.defaultdict(list)
 for x in saved:bysaved[x['sessionDate']].append(x)
 meta=read(Path(matrix)/'metadata.json');assert meta['hashes']==s.invariants();assert {x['session'] for x in meta['inputLedger']}<=set(s.admission.plan()['dailyDevelopment'])|allowed
 archive=np.load(Path(matrix)/'matrix.npz');z={k:archive[k] for k in ['daily','intraday','cov','intraCoverage','eligible']};archive.close();pins={(x['session'],x['kind']):x['sha256'] for x in meta['inputLedger']}
 # Only temporal status is used, after its own computedThrough/availableAt. Final values and final confidence are never backfilled.
 temporal={(x['symbol'],t['lane'],t['trait_id']):t['temporalReliability'] for x in read(ROOT/'docs/evidence/phase57-temporal-formal-v1/ci-result/measurement/05_profiles.json.gz') for t in x['traits']}
 histories={};last=None;rows=[];labels={};inventory=[];ledger=[]
 for day in days:
  prevday=cal[cal.index(day)-1]
  if last!=prevday:histories={}
  def pages(kind):
   s.admission.authorize(day,kind);file=Path(cache)/day/(kind+'-pages.json');assert sha(file)==pins[day,kind],(day,kind)
   values,_=v.saved.pages(file);assert all(x['Date']==day for x in values);ledger.append({'session':day,'kind':kind,'sha256':sha(file)});return values
  master=pages('master');by=collections.defaultdict(list)
  for x in pages('minute'):by[x['Code']].append(x)
  for code in by:by[code].sort(key=v.minute_time)
  inventory_row={'session':day,'previousExchangeSession':prevday,'input':'AUDITED','selectorReason':None}
  if day in bysaved:
   ms=bysaved[day];inventory_row['selector']='SAVED_EXACT_FROZEN_LEDGER';inventory_row['selectorReason']='IMMUTABLE_EXISTING_IDENTITIES'
  elif prevday not in allowed:
   ms=[];inventory_row.update(selector='UNAVAILABLE',selectorReason='EXACT_PREVIOUS_SESSION_OUTSIDE_AUTHORIZED_CACHE_NO_FORWARD_FILL')
  else:
   tmp=out/('selector-'+day+'.json');subprocess.run(['node','--max-old-space-size=4096','scripts/phase57_full144_selector.mjs',str(cache),day,prevday,str(tmp)],check=True)
   artifact=read(tmp);ms=artifact['members'];inventory_row['selectorAudit']=artifact['audit'];inventory_row['selector']='FROZEN_INFERENCE';tmp.unlink()
  who=who_day(meta,z,day,{x['symbol'] for x in ms},temporal) if ms else {}
  for m in ms:
   code=m['symbol'];minute=int(m['decisionTimeJst'][:2])*60+int(m['decisionTimeJst'][3:]);hist=histories.get(code,[]);previous=hist[-1]['daily'] if hist else None;close=900 if day<'2024-11-05' else 925
   prefix=[x for x in by[code] if v.minute_time(x)<minute and (540<=v.minute_time(x)<690 or 750<=v.minute_time(x)<close)]
   assert all(x['Date']==day and v.minute_time(x)+1<=minute for x in prefix)
   refs=[x for x in by[code] if v.valid(x) and v.minute_time(x)+(0 if v.minute_time(x) in [690,930] else 1)<=minute]
   assert refs and refs[-1]['C']==m['decisionPrice'],'FROZEN_DECISION_PRICE_SOURCE_DRIFT'
   recent=b.recent_context(day,m['decisionPrice'],prefix,hist,cal);now=b.now_context(day,minute,prefix,previous,hist,cal)
   assert all(r.timestamp(x['computedThrough'])<r.timestamp(m['decisionTimestamp']) for x in who[code])
   assert recent['computedThrough'] is None or r.timestamp(recent['computedThrough'])<r.timestamp(m['decisionTimestamp'])
   rows.append({'member':m,'WHO':who[code],'RECENT':recent,'NOW':now})
  # Current daily quotes enter only evaluator labels/history for subsequent dates.
  dc={x['Code']:x for x in pages('daily')};today=rows[-len(ms):] if ms else []
  for m in ms:labels[m['selectorEventId']]=labels_for_raw(m,by[m['symbol']],dc.get(m['symbol']))
  inventory_row.update(candidates=len(ms),WHO_AVAILABLE=sum(any(c['availability']=='AVAILABLE' for c in x['WHO']) for x in today),RECENT_AVAILABLE=sum(x['RECENT']['status']=='AVAILABLE' for x in today),NOW_AVAILABLE=sum(x['NOW']['status']=='RESEARCH_CONTEXT_AVAILABLE' for x in today),OUTCOME_30M_AVAILABLE=sum(labels[m['selectorEventId']]['mae30'] is not None for m in ms),OUTCOME_SESSION_END_AVAILABLE=sum(labels[m['selectorEventId']]['mfeEnd'] is not None for m in ms),COMMON_EVALUABLE=sum(labels[m['selectorEventId']]['mae30'] is not None and labels[m['selectorEventId']]['mfeEnd'] is not None for m in ms))
  inventory.append(inventory_row)
  universe={x['Code'] for x in master if str(x.get('Mkt')) in ['0111','0112','0113'] and str(x.get('ProdCat'))=='011'}
  for code in universe:
   hist=histories.get(code,[]);d=dc.get(code);prev=hist[-1]['daily'] if hist else None;entry={'session':day,'daily':d,'tr':None,'Va':d['Va'] if v.valid(d) else None,'C':d['C'] if v.valid(d) else None,'s':v.scale(hist),'ret':None}
   if v.valid(d) and v.valid(prev) and not v.action(d) and not v.action(prev):entry.update(tr=max(d['H']-d['L'],abs(d['H']-prev['C']),abs(d['L']-prev['C']))/prev['C'],ret=d['C']/prev['C']-1)
   bars=v.bars5(day,by[code]) if all(v.valid(x) for x in by[code]) else [];entry['barValues']={x['t']:x['Va'] for x in bars};entry['barVolumes']={x['t']:x['Vo'] for x in bars};histories[code]=(hist+[entry])[-10:]
  last=day;print(json.dumps({'substrate':inventory_row}),flush=True)
 write(out/'features.json.gz',rows);write(out/'labels.json.gz',labels);write(out/'input-ledger.json',ledger);write(out/'session-inventory.json',inventory)
 write(out/'audit.json',{'full144Inputs':len(inventory),'dictionaryPrefixOnly':True,'recentPreviousDayOnly':True,'intradayClosedBarOnly':True,'formalTemporalNoBackfill':True,'commonHoldoutOpened':0,'sealedOpened':0,'selectorUnchanged':True,'noSyntheticPrices':True,'safety':SAFETY})
 write(out/'manifest.json',{x.name:sha(x) for x in sorted(out.iterdir())})

def measure(substrate_dir,output):
    p=verify();out=Path(output);out.mkdir(parents=True,exist_ok=False);src=Path(substrate_dir)
    for name,h in read(src/'manifest.json').items():assert sha(src/name)==h
    rows=read(src/'features.json.gz');source=read(src/'labels.json.gz')
    labels=[source[x['member']['selectorEventId']] for x in rows]
    p['cohortSHA256']=digest([x['member'] for x in rows])
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
        if k=='S1':status='INCONCLUSIVE';reason='Reliable WHO values have no fit-period support; only late formal availability can be described. State-only score is auxiliary; unavailable candidates retained.'
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
    write(out/'cohort.json',{'developmentAuthorizedSessions':144,'exactFrozenCandidateSessions':len({x['member']['sessionDate'] for x in rows}),'inputSessionInventory':read(src/'session-inventory.json'),'fitSessions':p['fitSessions'],'embargoSessions':p['embargoSessions'],'evaluationSessions':p['evaluationSessions'],'candidateCount':len(rows),'fitCandidates':len(fit),'evaluationCandidates':len(ev),'sourceSHA256':p['cohortSHA256'],'scope':'All144 audited. Saved55 identities unchanged; additional authorized dates use the same frozen model and upstream modules. No prior authorized exchange day => explicit unavailable. First80 fit,5 embargo,last59 evaluation. Descriptive reused Development, not independent OOS.'})
    write(out/'audit.json',{'substrate':read(src/'audit.json'),'cohort':p['cohortSHA256'],'scoreFitBeforeEvaluation':True,'rawInputsFromDevelopmentOnly':True,'noThresholdSearch':True,'noEntryExitTraining':True,'newSealedExposure':0,'safety':SAFETY,'limitations':['WHO reliable-value fit effect unidentifiable: formal status unavailable before2025-08-22','Missing authorized exact previous sessions are explicitly retained as unavailable in the144-session inventory','Frozen upstream model/registry historically reused Development: no claim of independent prospective performance','Raw records are retrospective reconstruction; acquisition-time PIT is not verified']})
    full144_diagnostics(rows,labels,erows,elabels,sets,src,out)
    write(out/'manifest.json',{x.name:sha(x) for x in sorted(out.iterdir())})


def full144_diagnostics(rows,labels,erows,elabels,sets,src,out):
 inv=read(src/'session-inventory.json');funnel={}
 for key in ['candidates','WHO_AVAILABLE','RECENT_AVAILABLE','NOW_AVAILABLE','OUTCOME_30M_AVAILABLE','OUTCOME_SESSION_END_AVAILABLE','COMMON_EVALUABLE']:
  funnel[key]={'sessions':sum(x[key]>0 for x in inv),'events':sum(x[key] for x in inv)}
 funnel['inputSessions']=len(inv);funnel['availabilityIsNotSequentialExclusion']=True
 # Separate per-outcome denominators prevent one unavailable horizon from erasing another.
 horizons={}
 for suffix in ['30','60','End']:
  valid=[i for i,y in enumerate(elabels) if y['mae'+suffix] is not None];variants={}
  for variant,fracs in sets.items():
   keep=fracs['0.8'];ix=[i for i in valid if i in keep]
   variants[variant]={'baselineEvaluableN':len(valid),'retainedEvaluableN':len(ix),'mae':b.dist([elabels[i]['mae'+suffix] for i in ix]),'mfe':b.dist([elabels[i]['mfe'+suffix] for i in ix]),'return':b.dist([elabels[i]['return'+suffix] for i in ix]),'downsideRates':{str(t):100*sum(elabels[i]['mae'+suffix]<=-t for i in ix)/len(ix) if ix else None for t in [1,2,3]},'preservation':{str(t):{'baselineWinners':sum(elabels[i]['mfe'+suffix]>=t for i in valid),'retainedWinners':sum(elabels[i]['mfe'+suffix]>=t for i in ix)} for t in [1,2,3,5]}}
  horizons[suffix]=variants
 write(out/'full144-funnel.json',funnel);write(out/'independent-horizon-panels.json',horizons)
 write(out/'availability-reasons.json',{'session':inv,'event':[{'id':x['member']['selectorEventId'],'session':x['member']['sessionDate'],'WHO':'WHO_AVAILABLE' if any(c['availability']=='AVAILABLE' for c in x['WHO']) else 'WHO_UNAVAILABLE','RECENT':x['RECENT']['reason'],'NOW':x['NOW']['reason'],'outcome30':y['reason30'],'outcome60':y['reason60'],'sessionEnd':y['fullReason']} for x,y in zip(rows,labels)]})

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('command',choices=['verify','substrate','measure']);p.add_argument('--cache');p.add_argument('--matrix');p.add_argument('--substrate');p.add_argument('--output');a=p.parse_args()
 if a.command=='verify':verify();print('FULL144_PRECOMMIT_VERIFIED')
 elif a.command=='substrate':substrate(a.cache,a.matrix,a.output)
 else:measure(a.substrate,a.output)
