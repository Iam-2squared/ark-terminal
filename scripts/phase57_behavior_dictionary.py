#!/usr/bin/env python3
"""Offline, admission-first Dictionary census. No Selector or strategy imports.
Raw inputs stay private. Production L2/L3 are forbidden unless admission passes.
"""
import argparse,collections,datetime as dt,hashlib,io,json,math,os,re,resource,subprocess,tarfile,time
from pathlib import Path,PurePosixPath
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'docs/evidence/phase57-behavior-dictionary-v1'
PRECOMMIT='049ea1bb465fbf09cbf8af60c1aa1b5577467515'
FILENAMES={'daily-pages.json','master-pages.json','minute-pages.json','l0-manifest.json','l1-minute-manifest.json','l2-minute-manifest.json','v2-minute-manifest.json'}
JST=dt.timezone(dt.timedelta(hours=9))
def encoded(x):return (json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
def digest(x):return hashlib.sha256(encoded(x)).hexdigest()
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def read(p):return json.loads(Path(p).read_text())
def write(p,x):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('xb') as f:f.write(x.encode() if isinstance(x,str) else encoded(x))
def protocol():
 p=read(BASE/'protocol.json');lock=read(BASE/'protocol-lock.json')
 assert sha(BASE/'protocol.json')==lock['protocolSHA256']
 for f,h in p['sourcePins'].items():assert sha(ROOT/f)==h,f
 for f,h in p['contractPins'].items():assert sha(BASE/f)==h,f
 assert len(p['sessions']['auditAndExploration'])==57
 assert not set(p['sessions']['auditAndExploration'])&set(p['sessions']['REPORT19_PAYLOAD_CLOSED'])
 assert all(x is False for x in p['safety'].values())
 return p

def authorize_date(day,p=None):
 p=p or protocol()
 if day not in p['sessions']['auditAndExploration']:raise ValueError('SESSION_NOT_AUTHORIZED')
 return day

def archive_target(name,allowed):
 path=PurePosixPath(name)
 if path.is_absolute() or '..' in path.parts:raise ValueError('UNSAFE_ARCHIVE_PATH')
 parts=path.parts
 if 'jquants-v2' not in parts:return None
 j=parts.index('jquants-v2')
 if len(parts)!=j+3:return None
 day,filename=parts[j+1:]
 if day not in allowed or filename not in FILENAMES:return None
 return Path(day)/filename

def extract_stream(stream,destination,allowed):
 destination=Path(destination);audit={'selectedFiles':0,'skippedFiles':0,'selectedBytes':0,'selectedDates':set()}
 with tarfile.open(fileobj=stream,mode='r|gz') as tar:
  for m in tar:
   target=archive_target(m.name,allowed)
   if not target:
    if m.isfile():audit['skippedFiles']+=1
    continue
   if not m.isfile() or m.issym() or m.islnk():raise ValueError('NON_REGULAR_SELECTED_MEMBER')
   b=tar.extractfile(m).read();p=destination/target
   if p.exists():assert p.read_bytes()==b,'CONFLICTING_IMMUTABLE_INPUT'
   else:p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b);p.chmod(0o600)
   audit['selectedFiles']+=1;audit['selectedBytes']+=len(b);audit['selectedDates'].add(target.parts[0])
 audit['selectedDates']=sorted(audit['selectedDates']);return audit

def extract_archives(archives,destination,receipt):
 p=protocol();allowed=set(p['sessions']['auditAndExploration']);result=[]
 archives=Path(archives);files=sorted(archives.rglob('*.tar.gz.enc'))
 if not files:raise ValueError('NO_SAVED_ENCRYPTED_INPUTS')
 for f in files:
  expected=f.with_name(f.name+'.sha256').read_text().split()[0];assert sha(f)==expected,'ENCRYPTED_HASH_MISMATCH'
  proc=subprocess.Popen(['openssl','enc','-d','-aes-256-cbc','-pbkdf2','-iter','200000','-pass','env:JQUANTS_API_KEY','-in',str(f)],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
  try:record=extract_stream(proc.stdout,destination,allowed)
  finally:
   proc.stdout.close();err=proc.stderr.read();code=proc.wait()
  if code:raise ValueError('SAVED_CACHE_DECRYPTION_FAILED')
  result.append({'encryptedSHA256':expected,**record})
 write(receipt,{'archives':result,'scope':'Selected payload extraction; unselected members skipped by tar headers without JSON parsing or filesystem extraction. Shared encrypted containers are streamed, not copied as plaintext.','report19PayloadsExtracted':0,'protectedPayloadsExtracted':0})

def instant(x):
 if not x:raise ValueError('KNOWN_AT_REQUIRED')
 d=dt.datetime.fromisoformat(x.replace('Z','+00:00'))
 if d.tzinfo is None:raise ValueError('TIMEZONE_REQUIRED')
 return d

def available(records,cutoff):
 c=instant(cutoff);out=[]
 for r in records:
  if not r.get('knownAt'):continue
  if instant(r['knownAt'])>c:continue
  if instant(r['eventTime'])>c or instant(r.get('availableAt',r['eventTime']))>c:continue
  if r.get('maturityAt') and instant(r['maturityAt'])>c:continue
  out.append(r)
 return sorted(out,key=lambda r:(r['eventTime'],r['knownAt'],r.get('version',0)))

def fitted_allowed(artifact,first_use):
 return artifact['trainWindowEnd']<first_use[:10] and instant(artifact['knownAt'])<=instant(first_use)

def resolve_security(code,session,cutoff,mappings):
 rows=[r for r in mappings if r['code']==code and r['effectiveFrom']<=session<r['effectiveTo'] and instant(r['knownAt'])<=instant(cutoff)]
 if len(rows)!=1 or not rows[0].get('securityId'):raise ValueError('UNRESOLVED_SECURITY_ID')
 return rows[0]['securityId']

def corporate_action_allowed(action,cutoff):
 return bool(action.get('versionHash') and action.get('effectiveDate') and action.get('knownAt') and instant(action['knownAt'])<=instant(cutoff))

def classify_missing(evidence):
 if evidence.get('notListedVerified'):return 'NOT_LISTED'
 if evidence.get('haltOrSpecialQuoteVerified'):return 'HALT_SPECIAL_QUOTE'
 if evidence.get('feedOutageVerified'):return 'DATA_MISSING'
 if evidence.get('completeFeedVerified') and evidence.get('noTradeVerified'):return 'NO_TRADE'
 return 'UNKNOWN'

def calendar(day):
 return {'amStart':540,'amEnd':690,'pmStart':750,'pmEnd':900 if day<'2024-11-05' else 925,'close':900 if day<'2024-11-05' else 930}

def phase(day,minute):
 c=calendar(day)
 if minute in [690,c['close']]:return 'TERMINAL_AUCTION'
 if 540<=minute<690 or 750<=minute<c['pmEnd']:return 'REGULAR'
 if c['pmEnd']<=minute<c['close']:return 'PRECLOSE_NO_EXECUTION'
 return 'OUTSIDE_REGULAR'

def rolling_sessions(sessions,asof,n):return [d for d in sorted(sessions) if d<asof][-n:]
def projected_profile(profile):
 forbidden={'securityId','symbol','code','oneHot','embedding','selectorScore','selectorRank','winner','entryPnl','exitPnl'}
 return {k:v for k,v in profile.items() if k not in forbidden}

def append_trial(path,row):
 path=Path(path);prior=[json.loads(x) for x in path.read_text().splitlines()] if path.exists() else []
 if any(x['trialId']==row['trialId'] for x in prior):raise ValueError('DUPLICATE_TRIAL')
 entry={**row,'previousHash':digest(prior[-1]) if prior else None}
 with path.open('ab') as f:f.write(encoded(entry))
 return entry

def pages(path,expected=None):
 ps=read(path);rows=[]
 assert isinstance(ps,list)
 for page in ps:
  assert hashlib.sha256(page['responseText'].encode()).hexdigest()==page['responseSha256'],'PAGE_HASH_MISMATCH'
  body=json.loads(page['responseText']);rows.extend(body.get('data',[]))
 agg=hashlib.sha256(json.dumps([p['responseSha256'] for p in ps],separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
 if expected:
  assert len(ps)==expected['pageCount'],'PAGE_COUNT_MISMATCH'
  assert agg==expected['aggregateSha256'],'AGGREGATE_HASH_MISMATCH'
 return rows,{'pages':len(ps),'rows':len(rows),'aggregateSHA256':agg,'fileSHA256':sha(path),'fileBytes':path.stat().st_size,'pageKeys':sorted(set().union(*(x.keys() for x in ps))) if ps else []}

def value(row,*names):
 for n in names:
  if n in row and row[n] is not None:return row[n]
 return None

def fields_summary(rows):
 fields=collections.Counter(k for r in rows for k in r)
 known=sum(bool(value(r,'knownAt','KnownAt','publishedAt','PublishedAt')) for r in rows)
 stable=sum(bool(value(r,'securityId','SecurityId','ISIN','Isin')) for r in rows)
 return {'fieldCounts':dict(sorted(fields.items())),'explicitHistoricalKnownAtRows':known,'stableIdentifierFieldRows':stable}

def audit_session(directory,day,p):
 authorize_date(day,p);directory=Path(directory);files={f.name:{'sha256':sha(f),'bytes':f.stat().st_size} for f in sorted(directory.iterdir()) if f.name in FILENAMES}
 for required in ['l0-manifest.json','daily-pages.json','master-pages.json','minute-pages.json']:
  if required not in files:return {'sessionDate':day,'status':'MISSING_SOURCE','missing':required,'files':files}
 l0=read(directory/'l0-manifest.json');assert l0['sessionDate']==day and l0['partition'].startswith('DEVELOPMENT_')
 minute_manifests=[read(directory/f) for f in sorted(files) if f.endswith('minute-manifest.json')]
 assert minute_manifests,'MINUTE_MANIFEST_REQUIRED'
 for m in minute_manifests:assert m['sessionDate']==day and m['partition'].startswith('DEVELOPMENT_')
 daily,da=pages(directory/'daily-pages.json',l0['daily']);master,ma=pages(directory/'master-pages.json',l0['master']);minute,mi=pages(directory/'minute-pages.json',minute_manifests[0])
 for rows in [daily,master,minute]:assert all(str(value(r,'Date','date','sessionDate'))==day for r in rows),'CROSS_SESSION_PAYLOAD'
 mf=fields_summary(master);df=fields_summary(daily);mnf=fields_summary(minute)
 codes={str(value(r,'Code','code','symbol')) for r in master if str(value(r,'Mkt','marketCode')) in {'0111','0112','0113'} and str(value(r,'ProdCat','productCategory'))=='011'}
 allminute={str(value(r,'Code','code','symbol')) for r in minute};dailycodes={str(value(r,'Code','code','symbol')) for r in daily}
 segment=collections.Counter(str(value(r,'Mkt','marketCode')) for r in master)
 bykey={};duplicates=0;invalid=0;phasecounts=collections.Counter();zeroVolume=0;volMissing=0;turnMissing=0;identityMissing=0
 for r in minute:
  code=str(value(r,'Code','code','symbol'));t=str(value(r,'Time','time') or '');match=re.search(r'(\d\d):(\d\d)',t)
  if not code or not match:identityMissing+=1;continue
  h,m=map(int,match.groups());minuteof=h*60+m;key=(code,minuteof);ph=phase(day,minuteof);phasecounts[ph]+=1
  canonical=tuple(value(r,*keys) for keys in [('O','Open','open'),('H','High','high'),('L','Low','low'),('C','Close','close'),('Vo','Volume','volume'),('Va','Turnover','turnover')])
  if key in bykey:
   assert bykey[key]==canonical,'CONFLICTING_MINUTE_DUPLICATE';duplicates+=1;continue
  bykey[key]=canonical;prices=canonical[:4]
  try:valid=all(x is not None and math.isfinite(float(x)) and float(x)>0 for x in prices) and float(prices[1])>=max(float(prices[0]),float(prices[3])) and float(prices[2])<=min(float(prices[0]),float(prices[3]))
  except (TypeError,ValueError):valid=False
  if not valid:invalid+=1
  if canonical[4] is None:volMissing+=1
  elif float(canonical[4])==0:zeroVolume+=1
  if canonical[5] is None:turnMissing+=1
 regular={(code,t) for code,t in bykey if code in codes and phase(day,t)=='REGULAR'}
 c=calendar(day);expected=len(codes)*(150+c['pmEnd']-750)
 bucket=collections.Counter((code,540+(t-540)//5*5 if t<690 else 750+(t-750)//5*5) for code,t in regular)
 hist=collections.Counter(bucket.values());bycode=collections.Counter(code for code,t in regular);empty=expected-len(regular)
 return {'sessionDate':day,'status':'AUDITED_RAW_EXISTING_ONLY','files':files,'sourcePartition':l0['partition'],'fetchedAt':{'dailyMaster':l0.get('fetchedAt'),'minute':[m.get('fetchedAt') for m in minute_manifests]},'daily':{**da,**df},'master':{**ma,**mf},'minute':{**mi,**mnf},'coverage':{'eligibleDatedMasterCodes':len(codes),'minuteObservedEligibleCodes':len(codes&allminute),'dailyObservedEligibleCodes':len(codes&dailycodes),'expectedRegularMinuteSlots':expected,'observedRegularMinuteSlots':len(regular),'unobservedSlots':empty,'unobservedReason':'UNKNOWN_NOT_NO_TRADE','fiveMinuteObservedBuckets':len(bucket),'completeFiveMinuteBuckets':hist.get(5,0),'sparseFiveMinuteBucketHistogram':dict(sorted(hist.items())),'fullyObservedSymbols':sum(n==150+c['pmEnd']-750 for n in bycode.values())},'quality':{'duplicateRows':duplicates,'invalidOHLC':invalid,'invalidIdentityOrTime':identityMissing,'phaseCounts':dict(phasecounts),'zeroVolumeRowsNotProofOfNoTrade':zeroVolume,'missingVolumeRows':volMissing,'missingTurnoverRows':turnMissing,'rawRowsOutsideDatedEquityUniverse':len(allminute-codes),'masterMarketCodes':dict(sorted(segment.items()))},'corporateAction':{'nonUnitAdjFactorRows':sum(value(r,'AdjFactor','adjustmentFactor') not in [None,1,1.,'1','1.0'] for r in daily),'actionEffectiveKnownAtVersionSource':'NOT_PRESENT_IN_ALLOWED_RAW_CLASSES'},'securityMapping':'DATED_CODE_ONLY_NO_EFFECTIVE_INTERVAL_MAPPING_PROVIDED','historicalAsOfAdmitted':False}

def exposure(p):
 ledger=read(ROOT/'docs/evidence/phase57-long-only-global-data-budget/resolved-master-ledger.json')['sessions'];out=[]
 sets=p['sessions'];dev=set(sets['auditAndExploration']+sets['REPORT19_PAYLOAD_CLOSED'])
 for r in ledger:
  day=r['sessionDate'];isdev=day in dev;part='FIT38' if day in sets['priorFIT38'] else 'QUALIFY19' if day in sets['priorQUALIFY19'] else 'REPORT19' if day in sets['REPORT19_PAYLOAD_CLOSED'] else 'OUTSIDE_AUTHORIZED_DEV'
  # E3 means a previous check was consumed, not that it was independent or successful.
  level='E3' if part in ['QUALIFY19','REPORT19'] else 'E2' if isdev else 'UNKNOWN_EXPOSURE'
  out.append({'sessionDate':day,'sourceHash':p['sourcePins']['docs/evidence/phase57-long-only-global-data-budget/resolved-master-ledger.json'],'partition':part,'priorAllocations':r['allocations'],'researchStage':'HISTORICAL_MULTIPLE_STAGES' if isdev else 'METADATA_ONLY','exposure':level,'exposureLowerBound':True,'selectorUse':isdev,'entryUse':isdev,'exitUse':isdev,'anatomyOutcomeViewed':isdev,'dictionaryDesignUse':isdev,'dictionaryRawAuditAllowed':day in sets['auditAndExploration'],'confirmatoryUse':'PRIOR_DEVELOPMENT_CHECK_CONSUMED_NOT_FRESH' if level=='E3' else 'UNKNOWN_HISTORY_NO_FRESH_CLAIM','protected':r['secondaryFlags'].get('protected',False) or not isdev,'sealedThisTask':not day in sets['auditAndExploration'],'humanOutcomeExposure':'AGGREGATE_EXPOSURE_CONFIRMED; individual symbol/session review UNKNOWN' if isdev else 'UNKNOWN_EXPOSURE','machineOnlyProfileInputAllowed':False,'machineOnlyProfileInputReason':'Pending exact-version PIT admission; audit permission is not profile permission','notes':'REPORT19 already exposed by earlier research; no additional raw/strategy outcome reads this task' if part=='REPORT19' else 'No exposure downgrade or new fresh classification'})
 return out

def admission(sessions):
 present=[x for x in sessions if x['status']=='AUDITED_RAW_EXISTING_ONLY']
 checks={'all57SessionsAuditable':len(present)==57,'historicalVersionKnownAt':bool(present) and all(all(x[k]['explicitHistoricalKnownAtRows']==x[k]['rows'] for k in ['daily','master','minute']) for x in present),'stableSecurityMapping':False,'PITCorporateActionsForCrossSession':False,'unconditionalUniverseCoverage':bool(present) and all(x['coverage']['minuteObservedEligibleCodes']/max(1,x['coverage']['eligibleDatedMasterCodes'])>=.95 for x in present),'explicitMissingReasons':bool(present) and all(x['coverage']['unobservedSlots']==0 for x in present)}
 return {'status':'ADMISSION_PASS_REQUIRES_INTRINSIC_CENSUS' if all(checks.values()) else 'DICT_TRAIT_RELIABILITY_NOT_DEMONSTRATED','pass':all(checks.values()),'checks':checks,'classification':'BLOCKED_INPUT_CONTRACT' if not all(checks.values()) else 'READY','reason':'No exact historical version-knownAt, effective security code mapping or PIT action event ledger is supplied by the admitted raw classes; missing slots remain UNKNOWN. Do not backdate acquisition or infer no-trade from absence.','statisticalReliabilityFailureObserved':False,'traitsPlanned':8,'traitsStatisticallyTested':0,'dictionaryConstructed':False}

def notapp(reason):return {'status':'NOT_APPLICABLE','reason':reason,'measuredValue':None}

def run(cache,extraction,out):
 started=time.perf_counter();p=protocol();out=Path(out);out.mkdir(parents=True,exist_ok=False)
 cache=Path(cache);sessions=[audit_session(cache/d,d,p) if (cache/d).exists() else {'sessionDate':d,'status':'MISSING_SOURCE','files':{}} for d in p['sessions']['auditAndExploration']]
 ex=read(extraction);assert all(set(r['selectedDates'])<=set(p['sessions']['auditAndExploration']) for r in ex['archives'])
 gate=admission(sessions)
 if gate['pass']:raise RuntimeError('ADMISSION_PASSED: intrinsic implementation required before any freeze; no manufactured result')
 for n in ['01_start_state.json','06_pit_contract.md','07_metric_catalog.json','08_state_vocabulary_v1.json','09_trait_census_protocol.md','13_dictionary_schema.json','protocol.json','protocol-lock.json','cache-artifact-inventory.json']:
  with (out/n).open('xb') as f:f.write((BASE/n).read_bytes())
 rows=exposure(p);write(out/'02_exposure_ledger.json',{'rows':rows,'classificationCounts':dict(collections.Counter(r['exposure'] for r in rows)),'levelMeaning':{'E0':'certified unseen; never inferred from silence','E1':'unconditional behavior only','E2':'outcomes influenced design','E3':'prior confirmatory/development evaluation consumed; independence not implied','UNKNOWN_EXPOSURE':'not certifiable; blocked'},'lookHistoryComplete':False,'REPORT19NewPayloadReads':0})
 cat=read(BASE/'07_metric_catalog.json');trialpath=out/'03_trial_ledger.jsonl'
 for trait in cat['metrics']:
  append_trial(trialpath,{'trialId':trait['metricId']+':v1','hypothesisId':trait['metricId'],'family':trait['family'],'metric':trait['definition'],'window':19,'threshold':p['completionGates'],'method':trait['shrinkage'],'dataClass':'E2_E3_DEVELOPMENT_ONLY','firstTested':None,'numberOfLooks':0,'availabilityLooks':1,'result':'BLOCKED_INPUT_CONTRACT','promotedDropped':'NOT_ADMITTED','reason':gate['reason'],'codeHash':sha(Path(__file__)),'configHash':sha(BASE/'protocol.json')})
 historical=[('Selector','C-fit D-select frozen, prior trials not exhaustively countable'),('FullDayAnatomy','multiple horizons and baselines; already exposed'),('PairabilityRepairV2','observability repair; not a fresh replication'),('LowHighAnatomy','oracle/outcome-conditioned descriptive evidence'),('CausalEntry','one specification, QUALIFY and REPORT diagnostic views; economic gate failed'),('CausalEXIT','one specification, QUALIFY and REPORT diagnostic views; economic gate failed')]
 for family,reason in historical:append_trial(trialpath,{'trialId':'HISTORY:'+family,'hypothesisId':family,'family':family,'metric':'HISTORICAL_NOT_RECOMPUTED','window':'SEE_PINNED_PREVIOUS_PROTOCOLS','threshold':'UNCHANGED','method':'METADATA_ONLY','dataClass':'EXPOSED_DEVELOPMENT','firstTested':'BEFORE_CURRENT_PRECOMMIT','numberOfLooks':'UNKNOWN_HISTORICAL_TOTAL','result':'NOT_REMEASURED','promotedDropped':'UNCHANGED','reason':reason,'codeConfigHash':p['sourcePins']['docs/evidence/phase57-causal-entry-exit-recoverability-v1/protocol.json']})
 total=lambda k:sum(s['coverage'][k] for s in sessions if 'coverage' in s)
 coverage={'auditSessions':len(sessions),'auditedRawSessions':sum(s['status']=='AUDITED_RAW_EXISTING_ONLY' for s in sessions),'originalDevelopmentSessions':76,'REPORT19Skipped':19,'universeSecurityDays':total('eligibleDatedMasterCodes'),'minuteObservedSecurityDays':total('minuteObservedEligibleCodes'),'expectedMinuteSlots':total('expectedRegularMinuteSlots'),'observedMinuteSlots':total('observedRegularMinuteSlots'),'unobservedSlots':total('unobservedSlots'),'fullFiveMinuteBuckets':total('completeFiveMinuteBuckets'),'sparseFiveMinuteBuckets':total('fiveMinuteObservedBuckets')-total('completeFiveMinuteBuckets'),'missingReason':'UNKNOWN','PITAdmittedSecurityDays':0,'perSession':[{'sessionDate':s['sessionDate'],**s.get('coverage',{})} for s in sessions]}
 coverage['observedUniverseDayFraction']=coverage['minuteObservedSecurityDays']/max(1,coverage['universeSecurityDays']);coverage['observedMinuteFraction']=coverage['observedMinuteSlots']/max(1,coverage['expectedMinuteSlots'])
 inventory={'source':'EXISTING_SAVED_ENCRYPTED_FULL_CROSS_SECTION; not Selector Top5','newAcquisition':0,'scope':'57 Development dates; no REPORT19 payloads','sessions':sessions,'unavailableSourceClasses':['effective securityId code mapping','historical exact-version knownAt revisions','PIT corporate action announcements/events','halt/special quote/no-trade feed coverage','earnings known calendar','index/sector time series','dated tick regime'],'providerConstraints':'Private raw, private reconstructable derivatives, no redistribution; existing repository storage contract; entitlement not reverified for new acquisition because none authorized','raw1mRows':sum(s.get('minute',{}).get('rows',0) for s in sessions),'dailyRows':sum(s.get('daily',{}).get('rows',0) for s in sessions),'masterRows':sum(s.get('master',{}).get('rows',0) for s in sessions),'symbolIdsEmitted':False,'universeCoverageIsDatedMasterCodeProxyNotStableIdentity':True}
 write(out/'04_data_inventory.json',inventory);write(out/'05_data_quality_audit.json',{'checks':gate['checks'],'sessionQuality':[{'sessionDate':s['sessionDate'],'quality':s.get('quality'),'corporateAction':s.get('corporateAction')} for s in sessions],'knownAtNotBackdated':True,'retroactivelyAdjustedPriceUsed':False,'syntheticNoTradeImputation':False})
 write(out/'10_trait_reliability_results.json',{'status':gate['status'],'familiesPlanned':6,'traitsPlanned':8,'traitsStatisticallyTested':0,'maximumAllowedLooks':1,'lookCount':0,'results':{t['metricId']:{'status':'BLOCKED','reason':'PIT_SOURCE_ADMISSION_FAILED','adjacentWindowRankCorrelation':None,'oddEvenReliability':None,'nextWindowCalibration':None,'Brier':None,'logScore':None,'CI':None,'nEff':None,'admittedCoverage':0} for t in cat['metrics']},'D0':p['D0'],'noStrategyPnlUsed':True})
 for n in ['11_peer_baseline_comparison.json','17_shrinkage_validation.json','18_drift_validation.json','21_calibration_report.json','22_incremental_information.json']:
  write(out/n,notapp('EARLY_KILL_PIT_ADMISSION_FAILED; no values fitted or tested; no null treated as zero'))
 write(out/'12_early_kill_gate.json',gate)
 write(out/'14_l0_l1_manifest.json',{'status':'EXISTING_L0_AUDITED_L1_NOT_BUILT','inputHashes':{s['sessionDate']:s['files'] for s in sessions},'fiveMinuteCountsAreCompletenessAuditOnly':True,'archiveExtraction':ex,'L1':'BLOCKED_PIT; no production normalizer created'})
 write(out/'15_l2_manifest.json',notapp('EARLY_KILL; session-summary layer not built'));write(out/'16_l3_profile_manifest.json',notapp('EARLY_KILL; no Entry-facing profiles'))
 write(out/'20_coverage_report.json',coverage)
 # Synthetic contract results are attached in finalize, from actual unittest output.
 gates={'G0':{'status':'PASS','scope':'PROTOCOL_CONTRACT_HASH_ONLY'},'G1':{'status':'BLOCKED','reason':'actual input PIT unproven; synthetic guard tests are separate'},'G2':{'status':'BLOCKED','coverage':coverage['observedUniverseDayFraction'],'reason':'unidentified missing reasons and stable universe mapping'},**{g:notapp('EARLY_KILL_BEFORE_INTRINSIC_FIT_OR_RUNTIME') for g in ['G3','G4','G5','G6','G7']},'G8':{'status':'PASS','scope':'THIS_TASK_NO_NEW_PROTECTED_OR_REPORT_PAYLOAD_ACCESS; inherited Development exposure retained'},'G9':{'status':'NOT_FROZEN','reason':'G1-G7 not passed'}}
 write(out/'24_completion_gates_g0_g9.json',{'gates':gates,'freeze':False,'prospectiveImplemented':False,'omittedConditionalArtifacts':{'25_dictionary_freeze_manifest.json':'NOT_APPLICABLE_EARLY_KILL','26_prospective_capture_contract.md':'NOT_APPLICABLE_NO_FREEZE'}})
 write(out/'30_safety_data_boundary.json',{'safety':p['safety'],'newProviderRequests':0,'protectedPayloadReads':0,'report19PayloadReads':0,'sealedDataOpened':False,'archiveHandling':ex['scope'],'sourceSessionAllowlist':p['sessions']['auditAndExploration'],'rawReadLog':[{'sessionDate':s['sessionDate'],'files':sorted(s['files'])} for s in sessions],'sourceCodeConfigPins':p['sourcePins'],'selectorChanged':False,'capitalChanged':False,'chartContextLearning':False,'entryExitMeasurement':False,'dictionaryFits':0,'trialLooks':0,'noNewUnseenSessions':True,'exposureLedgerNotCleaned':True,'mainMerge':False,'promotion':False})
 report=f'''# JPX Stock Behavior Dictionary v1 — STOP

Verdict: **DICT_TRAIT_RELIABILITY_NOT_DEMONSTRATED / BLOCKED_INPUT_CONTRACT**.
This is an input-admission failure, not a measured negative reliability estimate.

Protocol precommit `{PRECOMMIT}`. Latest starting HEAD `{p['sourceHead']}`; exact producing HEAD/CI receipt is29_ci.json. No overwrite of prior evidence.

Exposure: original76 Development previously exposed. FIT38 is E2 lower bound; QUALIFY19/REPORT19 E3 means prior Development checks consumed, not independent confirmation. Other history remains UNKNOWN_EXPOSURE unless certified. REPORT19 had historical exposure but this task read no REPORT19 raw/strategy outcome payload. No independent fresh D0 claimed.

Audited {coverage['auditedRawSessions']}/57 existing full-cross-section Development sessions, {inventory['raw1mRows']:,} raw1m rows, {inventory['dailyRows']:,} daily rows, {inventory['masterRows']:,} dated-master rows. Dated common-equity code-days with minute observations {coverage['minuteObservedSecurityDays']:,}/{coverage['universeSecurityDays']:,} ({coverage['observedUniverseDayFraction']:.2%}); observed regular minute slots {coverage['observedMinuteFraction']:.2%}. Sparse5m buckets {coverage['sparseFiveMinuteBuckets']:,}; absent slots {coverage['unobservedSlots']:,}, reason UNKNOWN rather than NO_TRADE. These are raw coverage proxies, not PIT-valid stable-security coverage.

Exact historical-version knownAt, stable securityId/effective code mapping, PIT corporate action lineage and explicit missing/no-trade/halt reasons are not established. fetchedAt cannot be backdated. The Dictionary calendar contract separates preclose/terminal auctions; Frozen Selector semantics are untouched. [JPX calendar change](https://www.jpx.co.jp/corporate/news/news-releases/1030/20241105-01.html), [closing auction](https://www.jpx.co.jp/english/equities/trading/domestic/04.html).

Six families/eight trait definitions precommitted; **0 statistically evaluated,0 Tier1 admitted**. No peer/EB/calibration/incremental/drift result is fabricated. T7/T8 deferred. Trial ledger contains all8 planned definitions plus historical trial-family references with unknown historical look counts explicitly marked. Contracts/schema/state vocabulary are design artifacts, not a working or frozen Dictionary.

G0 contract PASS; G1/G2 BLOCKED; G3-G7 NOT_APPLICABLE; G8 current access boundary PASS; G9 NOT_FROZEN. L2/L3 not built; Dictionary v1 not frozen; prospective capture not implemented. Conditional files25/26 intentionally absent with reasons in24.

Actual audit time/RSS/storage is23_operations_benchmark.json; no full Dictionary runtime performance claim. Synthetic PIT contract tests and existing regression are27/28; production-input admission remains blocked even if tests pass.

Safety9 false; LONG/cash only; provider0; DEV TEST/Validation/OOS/Fresh sealed. No Selector/Capital change, Chart Context/Entry/EXIT research, main merge or promotion.

Next single step proposed: an evidence-only recovery plan for existing-cache historical availability, stable security mapping and missing-reason provenance, with exact data needs and no new session opening. Do not execute additional acquisition or trait search. A minimum compatible planning budget is57 existing sessions of versioned daily/master/lifecycle references and57 full-cross-section minute/status coverage; new-session budget0. Whether those historical versions exist is unknown; do not replace them with assumptions. Preserve REPORT19.
'''
 write(out/'31_final_report.md',report);write(out/'32_final_handoff.md',report+'\nCompletion: required applicable evidence recorded; STOP.\n')
 code=['scripts/phase57_behavior_dictionary.py','scripts/test_phase57_behavior_dictionary.py','.github/workflows/phase57-behavior-dictionary-v1.yml']
 write(out/'manifest.json',{'protocolSHA256':sha(BASE/'protocol.json'),'code':{f:sha(ROOT/f) for f in code},'outputs':{f.name:sha(f) for f in sorted(out.iterdir())}})
 benchmark={'scope':'existing57-session raw audit only, not Dictionary L2/L3 or production throughput','wallSeconds':time.perf_counter()-started,'peakRSSKiB':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'selectedInputBytes':sum(x['bytes'] for s in sessions for x in s['files'].values()),'deterministicEvidenceBytes':sum(f.stat().st_size for f in out.iterdir()),'rawRows':inventory['raw1mRows'],'L2L3Bytes':0,'L2L3Runtime':'NOT_APPLICABLE','hostDependent':True}
 write(out/'23_operations_benchmark.json',benchmark)
 print(json.dumps({'status':gate['status'],'sessions':coverage['auditedRawSessions'],'rawRows':inventory['raw1mRows'],'traitsTested':0,'PITAdmittedSecurityDays':0}))

def audit(directory):
 protocol();d=Path(directory);m=read(d/'manifest.json')
 assert m['protocolSHA256']==sha(BASE/'protocol.json')
 for f,h in m['code'].items():assert sha(ROOT/f)==h,f
 for f,h in m['outputs'].items():assert sha(d/f)==h,f
 s=read(d/'30_safety_data_boundary.json');assert not s['protectedPayloadReads'] and not s['report19PayloadReads'] and all(x is False for x in s['safety'].values())
 if (d/'ci-manifest.json').exists():
  cm=read(d/'ci-manifest.json');assert cm['measurementManifestSHA256']==sha(d/'manifest.json')
  for f,h in cm['outputs'].items():assert sha(d/f)==h,f
 print('BEHAVIOR_DICTIONARY_AUDIT_PASS')

def finalize(directory,regression,head,runid):
 d=Path(directory);r=Path(regression);audit(d);log=(r/'targeted-tests.log').read_text();m=re.search(r'Ran (\d+) tests',log);assert m and '\nOK' in log
 reg=read(r/'full/regression.json');assert reg['status']=='PASS'
 write(d/'19_pit_canary_results.json',{'status':'SYNTHETIC_CONTRACT_TESTS_PASS','realInputPIT':'BLOCKED','testLogSHA256':sha(r/'targeted-tests.log'),'negativeCanaryDetected':True,'futurePoisonRejected':True,'truncationInvariant':True,'noProductionPITClaim':True})
 write(d/'27_tests.json',{'status':'PASS','count':int(m[1]),'logSHA256':sha(r/'targeted-tests.log'),'deterministicRegeneration':'two full raw audit manifests identical; timing excluded, separately hashed'})
 write(d/'28_regression.json',reg)
 write(d/'29_ci.json',{'producingHead':head,'protocolPrecommit':PRECOMMIT,'runId':str(runid),'url':f'https://github.com/Iam-2squared/ark-terminal/actions/runs/{runid}','measurement':'SUCCESS','regression':'SUCCESS','preservation':'RUNNING_AT_CREATION_VERIFY_FINAL_RUN','inputAdmission':'BLOCKED_EXPECTED_FAIL_CLOSED','allPRChecksGreenClaim':False})
 write(d/'ci-manifest.json',{'measurementManifestSHA256':sha(d/'manifest.json'),'outputs':{f:sha(d/f) for f in ['19_pit_canary_results.json','23_operations_benchmark.json','27_tests.json','28_regression.json','29_ci.json']}})

def main():
 p=argparse.ArgumentParser();s=p.add_subparsers(dest='cmd',required=True)
 x=s.add_parser('extract');x.add_argument('--archives',required=True);x.add_argument('--destination',required=True);x.add_argument('--receipt',required=True)
 x=s.add_parser('run');x.add_argument('--cache',required=True);x.add_argument('--extraction',required=True);x.add_argument('--output-dir',required=True)
 x=s.add_parser('audit');x.add_argument('--directory',required=True)
 x=s.add_parser('finalize')
 for n in ['directory','regression','head','run-id']:x.add_argument('--'+n,required=True)
 a=p.parse_args()
 if a.cmd=='extract':extract_archives(a.archives,a.destination,a.receipt)
 elif a.cmd=='run':run(a.cache,a.extraction,a.output_dir)
 elif a.cmd=='audit':audit(a.directory)
 else:finalize(a.directory,a.regression,a.head,a.run_id)
if __name__=='__main__':main()
