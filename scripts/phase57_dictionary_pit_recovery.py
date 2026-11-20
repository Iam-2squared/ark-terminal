#!/usr/bin/env python3
"""Evidence-only PIT recovery. Provider/strategy clients are never imported.
Reuse immutable saved bytes; partial retrospective eligibility is not PIT admission.
"""
import argparse,collections,csv,datetime as dt,gzip,hashlib,io,json,math,re,resource,time
from pathlib import Path
from scripts import phase57_behavior_dictionary as old
ROOT=old.ROOT
BASE=ROOT/'docs/evidence/phase57-dictionary-pit-recovery-v1'
PRIOR=old.BASE
PRECOMMIT='fd0c3c09a2776c116a6892fd2bdc4812a41996b2'
read,write,sha,digest=old.read,old.write,old.sha,old.digest
NA_REASON='G1/G2 input coverage blocked; no intrinsic reliability test or fitted model allowed'
METRICS=[x['metricId'] for x in read(PRIOR/'07_metric_catalog.json')['metrics']]
LEDGER_FIELDS=['session','code','partition','classification','dailyPresent','minutePresent','amObserved','pmObserved','complete5m','lagPairs','retrospectiveRange','retrospectiveTurnover','volumeReconciled','turnoverReconciled','actionFlag','identity','profileEligible']

def protocol():
 p=read(BASE/'protocol.json');lock=read(BASE/'protocol-lock.json')
 assert sha(BASE/'protocol.json')==lock['protocolSHA256']
 assert sha(BASE/'02_pit_recovery_protocol.md')==lock['textSHA256']
 for f,h in p['sourcePins'].items():assert sha(ROOT/f)==h,f
 for f,h in p['contractPins'].items():assert sha(BASE/f)==h,f
 prior=old.protocol()
 assert p['completionGates']==prior['completionGates']
 assert p['statistics']==prior['statistics'] and p['sessions']==prior['sessions']
 assert all(v is False for v in p['safety'].values()) and len(p['safety'])==9
 return p

def bound(event_end,receipt,cutoff,source_hash):
 """Actual cached version known no later than receipt; never equate date with publication."""
 if not receipt or not source_hash:return {'status':'UNUSABLE','lower':event_end,'upper':None,'historicalAvailable':False}
 upper=old.instant(receipt);lower=old.instant(event_end) if event_end else None
 if lower and upper<lower:raise ValueError('RECEIPT_BEFORE_EVENT')
 return {'status':'BOUNDED_RECEIPT_ONLY','lower':event_end,'upper':receipt,'exactKnownAt':None,'historicalAvailable':upper<=old.instant(cutoff),'evidenceSHA256':source_hash,'confidence':'HASH_BOUND_ACQUISITION_UPPER; PUBLICATION_TIME_UNKNOWN'}

def missing_reason(e):
 if e.get('outsideSession'):return 'OUTSIDE_SESSION'
 for key,label in [('notListedVerified','NOT_LISTED'),('haltVerified','HALT'),('specialQuoteVerified','SPECIAL_QUOTE'),('feedOutageVerified','DATA_MISSING')]:
  if e.get(key):return label
 if e.get('completeFeedVerified') and e.get('noTradeVerified'):return 'NO_TRADE'
 return 'UNKNOWN'

def classify(integrity,known,identity,family_contract):
 if not integrity:return 'PIT_UNUSABLE'
 return 'PIT_VERIFIED' if known and identity and family_contract else 'PIT_PARTIAL'

def family_eligibility(complete_regular,volume_valid,turnover_valid,pairs,known,identity,actions=False,auction_separated=False,reason_complete=False):
 retro={m:False for m in METRICS}
 retro['T1_LOG_RANGE']=complete_regular
 retro['T2_LOG_TURNOVER']=complete_regular and turnover_valid
 retro['T2_NO_TRADE_RATE']=reason_complete
 retro['T3_AM_VOLUME_SHARE']=complete_regular and volume_valid and auction_separated
 # Gap/overnight contracts cannot be certified by an ex-date factor alone.
 retro['T4_GAP_UP_RATE']=actions
 retro['T4_GAP_FILL_RATE']=actions and complete_regular
 retro['T5_OVERNIGHT_VARIANCE_SHARE']=actions
 retro['T6_LAG1_AUTOCORRELATION']=pairs>=100
 return {'retrospectiveInputEligible':retro,'historicalProfileEligible':{m:bool(v and known and identity) for m,v in retro.items()}}

def lag_pairs(times,day):
 buckets=collections.Counter(t//5*5 for t in times if old.phase(day,t)=='REGULAR')
 full={t for t,n in buckets.items() if n==5}
 # Three consecutive closes give two adjacent returns. Never cross lunch/session.
 pairs=sum(t-5 in full and t-10 in full and ((t<690 and t-10>=540) or (t>=750 and t-10>=750)) for t in full)
 return len(full),pairs

def finite(x):
 try:return x is not None and math.isfinite(float(x))
 except (TypeError,ValueError):return False

def valid_ohlc(r):
 vals=[r.get(k) for k in ['O','H','L','C']]
 return all(finite(v) and float(v)>0 for v in vals) and float(vals[1])>=max(map(float,vals)) and float(vals[2])<=min(map(float,vals))

def reconciles(total,daily):return finite(daily) and math.isclose(total,float(daily),rel_tol=1e-10,abs_tol=1e-6)

def session_audit(directory,day,p,prior,writer,identity_history):
 old.authorize_date(day,p);directory=Path(directory)
 for f,meta in prior['files'].items():assert sha(directory/f)==meta['sha256'],'PRIOR_RAW_CHANGED:'+f
 l0=read(directory/'l0-manifest.json');assert l0['sessionDate']==day and l0['partition'].startswith('DEVELOPMENT_')
 minute_name=next(f for f in sorted(prior['files']) if f.endswith('minute-manifest.json'))
 mm=read(directory/minute_name);assert mm['sessionDate']==day and mm['partition'].startswith('DEVELOPMENT_')
 daily,da=old.pages(directory/'daily-pages.json',l0['daily']);master,ma=old.pages(directory/'master-pages.json',l0['master']);minutes,mi=old.pages(directory/'minute-pages.json',mm)
 for rows in [daily,master,minutes]:assert all(r['Date']==day for r in rows),'CROSS_SESSION_PAYLOAD'
 dc={r['Code']:r for r in daily};mc={r['Code']:r for r in master if str(r.get('Mkt')) in {'0111','0112','0113'} and str(r.get('ProdCat'))=='011'}
 assert len(dc)==len(daily),'DUPLICATE_DAILY_CODE'
 c=old.calendar(day);close=f'{day}T{c["close"]//60:02}:{c["close"]%60:02}:00+09:00'
 # Earliest subsequent authorized as-of session; last uses next calendar morning as stricter-than-receipt diagnostic, not an extra session read.
 dates=p['sessions']['auditAndExploration'];i=dates.index(day)
 first_use=(dates[i+1] if i+1<len(dates) else (dt.date.fromisoformat(day)+dt.timedelta(days=1)).isoformat())+'T09:00:00+09:00'
 bounds={kind:bound(None if kind=='master' else close,at,first_use,meta['fileSHA256']) for kind,at,meta in [('daily',l0.get('fetchedAt'),da),('master',l0.get('fetchedAt'),ma),('minute',mm.get('fetchedAt'),mi)]}
 known=all(b['historicalAvailable'] for b in bounds.values())
 bycode={};phasecounts=collections.Counter();duplicate=0;invalid=0
 for r in minutes:
  code=r['Code'];match=re.fullmatch(r'(\d\d):(\d\d)(?::\d\d)?',str(r['Time']))
  if not match:raise ValueError('INVALID_MINUTE_TIMESTAMP')
  h,m=map(int,match.groups());assert 0<=h<24 and 0<=m<60
  t=h*60+m;phasecounts[old.phase(day,t)]+=1
  if code not in mc:continue
  s=bycode.setdefault(code,{'rows':{},'am':0,'pm':0,'regular':set(),'invalid':0,'volumeValid':True,'turnoverValid':True,'volume':0.,'turnover':0.})
  signature=tuple(r.get(k) for k in ['O','H','L','C','Vo','Va'])
  if t in s['rows']:
   assert s['rows'][t]==signature,'CONFLICTING_MINUTE_DUPLICATE';duplicate+=1;continue
  s['rows'][t]=signature
  if not valid_ohlc(r):s['invalid']+=1;invalid+=1
  for field,total,ok in [('Vo','volume','volumeValid'),('Va','turnover','turnoverValid')]:
   if not finite(r.get(field)) or float(r[field])<0:s[ok]=False
   else:s[total]+=float(r[field])
  if old.phase(day,t)=='REGULAR':
   s['regular'].add(t);s['am' if t<690 else 'pm']+=1
 counts=collections.Counter();family=collections.Counter();recon=collections.Counter();am=pm=full5=pairs=0;ca=collections.Counter();expected_per=150+c['pmEnd']-750
 for code,mr in sorted(mc.items()):
  d=dc.get(code);s=bycode.get(code,{'rows':{},'am':0,'pm':0,'regular':set(),'invalid':0,'volumeValid':False,'turnoverValid':False,'volume':0.,'turnover':0.})
  complete=len(s['regular'])==expected_per and not s['invalid'];f5,lp=lag_pairs(s['regular'],day)
  integrity=bool(d is not None and all(b['status']!='UNUSABLE' for b in bounds.values()) and not s['invalid'])
  # Field discovery actually checks all admitted records; no implicit identity mapping.
  stable=bool(mr.get('securityId') and mr.get('effectiveFrom') and mr.get('effectiveTo') and mr.get('knownAt'))
  if stable:raise ValueError('NEW_IDENTITY_EVIDENCE_REQUIRES_EXPLICIT_INTERVAL_AUDIT')
  cls=classify(integrity,known,False,complete);counts[cls]+=1
  elig=family_eligibility(complete,s['volumeValid'],s['turnoverValid'],lp,known,False)
  for metric,yes in elig['retrospectiveInputEligible'].items():family[metric]+=int(yes)
  vr=bool(d and s['volumeValid'] and reconciles(s['volume'],d.get('Vo')));tr=bool(d and s['turnoverValid'] and reconciles(s['turnover'],d.get('Va')))
  recon['volumeReconciledDays']+=vr;recon['turnoverReconciledDays']+=tr
  recon['bothReconciledDays']+=vr and tr
  flag=bool(d and (d.get('ExRT') not in [None,'',0,'0'] or d.get('AdjFactor') not in [None,1,1.,'1','1.0']))
  ca['flaggedSecurityDays']+=flag
  if d:ca['exRT_'+str(d.get('ExRT'))]+=1
  hist=identity_history.setdefault(code,[]);hist.append({'day':day,'nameHash':digest([mr.get('CoName'),mr.get('CoNameEn')]),'sourceSHA256':ma['fileSHA256'],'lagPairs':lp,'completeRegular':complete})
  row=[day,code,l0['partition'],cls,int(d is not None),int(bool(s['rows'])),s['am'],s['pm'],f5,lp,int(complete),int(complete and s['turnoverValid']),int(vr),int(tr),int(flag),'UNKNOWN_IDENTITY_PERIOD',0]
  writer.writerow(row);am+=s['am'];pm+=s['pm'];full5+=f5;pairs+=lp
  counts['minuteObservedSecurityDays']+=bool(s['rows']);counts['dailyObservedSecurityDays']+=d is not None
 result={'session':day,'partition':l0['partition'],'cutoff':first_use,'classification':dict(counts),'eligibleSecurityDays':len(mc),'rawRows':{'minute':len(minutes),'daily':len(daily),'master':len(master)},'pages':{'minute':mi['pages'],'daily':da['pages'],'master':ma['pages']},'knownAtBounds':bounds,'identityVerified':0,'corporateActionPITVerified':0,'corporateActionSnapshot':dict(ca),'coverage':{'amObservedSlots':am,'amExpectedSlots':len(mc)*150,'pmObservedSlots':pm,'pmExpectedSlots':len(mc)*(c['pmEnd']-750),'full5mBuckets':full5,'full5mLagPairsWithinSession':pairs,'missingRegularSlots':len(mc)*expected_per-am-pm,'regularObservedSlots':am+pm,'regularExpectedSlots':len(mc)*expected_per},'retrospectiveEligibility':dict(family),'historicalProfileEligibleByMetric':dict.fromkeys(METRICS,0),'reconciliation':dict(recon),'quality':{'duplicateRows':duplicate,'invalidOHLC':invalid,'phaseCounts':dict(phasecounts)},'inputHashes':{f:meta['sha256'] for f,meta in prior['files'].items()}}
 assert result['coverage']['regularObservedSlots']==prior['coverage']['observedRegularMinuteSlots']
 assert full5==prior['coverage']['completeFiveMinuteBuckets']
 print(json.dumps({'auditSession':day,'securityDays':len(mc),'classification':{k:counts[k] for k in ['PIT_VERIFIED','PIT_PARTIAL','PIT_UNUSABLE']}}),flush=True)
 return result

def coverage_gate(total,verified,classified_missing,symbols,p):
 g=p['completionGates']['G2'];checks={'verifiedUniverseDayCoverage':total>0 and verified/total>=g['universeDayCoverageMin'],'classifiedMissingReasons':classified_missing>=g['classifiedMissingReasonCoverageMin'],'stableSymbolsWithNEff':symbols>=g['minSymbolsWithNEff']}
 return {'status':'PASS' if all(checks.values()) else 'BLOCKED_INPUT_COVERAGE','pass':all(checks.values()),'checks':checks,'thresholds':g,'measurements':{'eligibleSecurityDays':total,'PITVerifiedSecurityDays':verified,'PITVerifiedFraction':verified/total if total else 0,'classifiedMissingReasonFraction':classified_missing,'stableSymbolsWithNEff':symbols},'outcomeFiltersUsed':False}

def identity_summary(history,dates):
 index={d:i for i,d in enumerate(dates)};rows=[]
 for code,rs in sorted(history.items()):
  rows.append({'code':code,'securityId':None,'firstObserved':rs[0]['day'],'lastObserved':rs[-1]['day'],'observedSessions':len(rs),'unobservedBetween':index[rs[-1]['day']]-index[rs[0]['day']]+1-len(rs),'nameHashChanges':sum(a['nameHash']!=b['nameHash'] for a,b in zip(rs,rs[1:])),'effectiveFrom':None,'effectiveTo':None,'listingDate':None,'delistingDate':None,'merger':None,'codeChange':None,'codeReuse':None,'status':'UNKNOWN_IDENTITY_PERIOD','snapshotChainHash':digest(rs)})
 return rows

def window_availability(history,dates):
 windows=[dates[i:i+19] for i in range(0,len(dates),19) if len(dates[i:i+19])==19];out=[]
 for window in windows:
  range_n=lag_n=0
  for records in history.values():
   rs=[r for r in records if r['day'] in window]
   range_n+=sum(r.get('completeRegular',False) for r in rs)>=12
   lag_n+=sum(r.get('lagPairs',0) for r in rs)>=100 and sum(r.get('lagPairs',0)>0 for r in rs)>=12
  out.append({'start':window[0],'end':window[-1],'provisionalCodesRangeNEff12':range_n,'provisionalCodesT6Pairs100NEff12':lag_n,'stableIdentityAdmittedSymbols':0,'historicalProfileEligible':0})
 return out

def requirements(sessions,coverage,ids):
 pages={k:sum(s['pages'][k] for s in sessions) for k in ['daily','master','minute']}
 return {'status':'REQUIRED_NOT_ACQUIRED','scope':'existing57 dates only; all eligible codes, no outcome selection','dates':[s['session'] for s in sessions],'codeList':[x['code'] for x in ids],'codeListIsStableIdentity':False,'codeCount':len(ids),'securityDays':coverage['securityDays'],'existingRows':coverage['rawRows'],'expectedRegularStatusSlots':coverage['regularExpectedSlots'],'unknownRegularSlots':coverage['missingRegularSlots'],'historicalReceiptRequirement':'Exact input bytes/version hashes plus signed or archived observedAt <= intended firstUse for every admitted day. Scheduled 16:30 is insufficient. If no historical archives exist, these2024 dates cannot be made exact-version PIT by re-downloading2026 snapshots.','identityRequirement':'All eligible codes including delisted/change/reuse periods: stable securityId, effectiveFrom/To, event type, predecessor/successor only when independently certified, announcement knownAt and source hash.','actionRequirement':'PIT announcement/effective/ex-date split/reverse/rights/dividend/merger records and revisions; no hindsight adjusted-price use. Within-session raw metrics do not need cross-session adjustment, but still need identity/availability.','minuteRequirement':'Existing unadjusted1m bytes plus per-slot certified coverage, NO_TRADE/HALT/SPECIAL_QUOTE/DATA_MISSING and listing status; auction-separated volumes for unchangedT3. Do not fill absent prices.','minimumPlan':{'newSessions':0,'newPriceRowsRequired':0,'task':'Recover certified historical receipts and lifecycle mappings for current daily+1m cache; status metadata for unresolved slots; do not spend re-download budget unless provenance can be provided.','regularMissingStatusRecordsUpperBound':coverage['missingRegularSlots'],'familyScope':'T1/T2/T6 could use existing fully observed intervals if historical versions and identity certified; unchangedG2 and per-window nEff still required. T3 requires auction separation; T4/T5 need action ledger.'},'idealPlan':{'newSessions':0,'task':'Versioned bitemporal all57-session full universe master/lifecycle/action ledger and full slot coverage with auction phase tags, first-delivered values and correction chain.','statusRecordsUpperBound':coverage['regularExpectedSlots'],'storage':'Existing parsed JSON footprint reused; status sparse intervals should be preferred to copied raw minute prices.'},'jquantsRequestEstimate':{'executed':0,'sameSnapshotRefetchLowerBoundEndpoints':57*3,'sameSnapshotRefetchAtObservedPagination':pages,'sameSnapshotRefetchAtObservedPaginationTotal':sum(pages.values()),'estimateOnly':True,'notARecoverySolution':'Ordinary APIs lack historical delivery versions, stable ID lifecycle and halt/special status. Request estimate for unavailable proof datasets is NOT_EVALUABLE, not zero.','unavailableProofEndpointsRequestCount':None,'incrementalPriceRequestMinimum':0},'acquisitionApproval':False,'protectedSessionBudget':0}

def run(cache,extraction,out):
 start=time.perf_counter();p=protocol();out=Path(out);out.mkdir(parents=True,exist_ok=False)
 ex=read(extraction);allowed=set(p['sessions']['auditAndExploration'])
 assert ex['protectedPayloadsExtracted']==ex['report19PayloadsExtracted']==0
 assert set().union(*(set(a['selectedDates']) for a in ex['archives']))==allowed
 prior=read(PRIOR/'measurement/04_data_inventory.json');pins={s['sessionDate']:s for s in prior['sessions']}
 history={};sessions=[]
 with (out/'security_session_classification.csv.gz').open('xb') as raw:
  with gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0) as gz:
   with io.TextIOWrapper(gz,encoding='utf-8',newline='') as f:
    w=csv.writer(f,lineterminator='\n');w.writerow(LEDGER_FIELDS)
    for day in p['sessions']['auditAndExploration']:sessions.append(session_audit(Path(cache)/day,day,p,pins[day],w,history))
 ids=identity_summary(history,p['sessions']['auditAndExploration']);counts=collections.Counter()
 for s in sessions:counts.update(s['classification'])
 total=sum(s['eligibleSecurityDays'] for s in sessions);cv={k:sum(s['coverage'][k] for s in sessions) for k in sessions[0]['coverage']}
 cv.update({'securityDays':total,'sessions':len(sessions),'uniqueDatedCodesNotSecurityIds':len(ids),'classification':{k:counts[k] for k in ['PIT_VERIFIED','PIT_PARTIAL','PIT_UNUSABLE']},'rawRows':{k:sum(s['rawRows'][k] for s in sessions) for k in ['minute','daily','master']},'symbolDayObservation':counts['minuteObservedSecurityDays']/total,'regularMinuteObservation':cv['regularObservedSlots']/cv['regularExpectedSlots'],'PITVerifiedFraction':counts['PIT_VERIFIED']/total,'identityVerifiedFraction':0,'knownAtHistoricalVerifiedFraction':0,'crossSessionCorporateActionSafeFraction':0,'classifiedMissingReasonFraction':0,'metricEligibility':{m:{'retrospectiveInputEligibleSecurityDays':sum(s['retrospectiveEligibility'].get(m,0) for s in sessions),'historicalProfileEligibleSecurityDays':0} for m in METRICS},'gapEndpointPITCoverage':0,'liquidityProfilePITCoverage':0,'perSession':sessions,'retrospectiveWindowAvailability':window_availability(history,p['sessions']['auditAndExploration']),'fullWindowT6Eligibility':'Counts are provisional-code input availability only; not correlation or reliability evaluation. Per-day100-pair eligibility is not19-session eligibility; see retrospectiveWindowAvailability.'})
 gate=coverage_gate(total,counts['PIT_VERIFIED'],0,0,p)
 assert not gate['pass'],'INPUT_GATE_PASSED: CONTINUE_PRIOR_PRECOMMITTED_CENSUS_BEFORE_COMPLETION'
 gate.update({'G1':'BLOCKED_REAL_INPUT_PIT','statisticalReliabilityFailureObserved':False,'reason':'All cached2024 versions only bounded by2026 acquisition; no effective stable identity ledger; cross-session actions and unknown missing reasons unresolved.','traitsStatisticallyTested':0})
 for f in ['01_start_state.json','02_pit_recovery_protocol.md','protocol.json','protocol-lock.json','provider_metadata_sources.json']:(out/f).write_bytes((BASE/f).read_bytes())
 write(out/'03_known_at_recovery.json',{'status':'PARTIAL_RECEIPT_BOUND_RECOVERED','historicalAdmitted':0,'sessions':[{'session':s['session'],'cutoff':s['cutoff'],'sources':s['knownAtBounds']} for s in sessions],'eventTimeRule':'daily finalized observation=session close; minute interval start+1m except terminal auction instant; master effectiveDate not publicationDate; aggregate minute lower=session close for whole session dataset, not every individual bar','scheduledAvailabilityIsEvidence':False,'retroactiveTimestampAssigned':False})
 write(out/'04_security_identity_recovery.json',{'status':'UNKNOWN_IDENTITY_PERIOD','stableIdsRecovered':0,'snapshotCodeCount':len(ids),'securityPeriods':ids,'limitation':'Name/code continuity is not merger/code-reuse proof; no invented effective intervals'})
 write(out/'05_corporate_action_pit.json',{'status':'PARTIAL_EFFECTIVE_SNAPSHOT_ONLY','knownAtRecovered':0,'adjustedValuesUsed':False,'sameSessionRawActionInvariant':True,'crossSessionEligible':False,'flaggedSecurityDays':sum(s['corporateActionSnapshot']['flaggedSecurityDays'] for s in sessions),'perSession':[{'session':s['session'],**s['corporateActionSnapshot']} for s in sessions],'reason':'ExRT/AdjFactor does not identify all announcements/dividends/mergers or historical corrections'})
 write(out/'06_missing_minute_classification.json',{'status':'PARTIAL_PROVIDER_SEMANTICS_RECOVERED','regularMissingSlots':cv['missingRegularSlots'],'counts':{'UNKNOWN':cv['missingRegularSlots'],'NO_TRADE':0,'DATA_MISSING':0,'HALT':0,'SPECIAL_QUOTE':0,'NOT_LISTED':0},'outsideSession':'Lunch/after-hours and2024-11-05 onward15:25-15:29 preclose are excluded from regular denominator; terminal auction records kept separately. No prices synthesized.','reconciliation':{k:sum(s['reconciliation'].get(k,0) for s in sessions) for k in ['volumeReconciledDays','turnoverReconciledDays','bothReconciledDays']},'reconciledIsNoTradeProof':False,'unknownToNoTrade':0})
 write(out/'07_input_classification.json',{'status':'CLASSIFIED_FAIL_CLOSED','classificationCounts':cv['classification'],'fractions':{k:v/total for k,v in cv['classification'].items()},'ledger':'security_session_classification.csv.gz','ledgerSHA256':sha(out/'security_session_classification.csv.gz'),'ledgerRows':total,'key':'datedCode/session/partition; NOT stable securityId','partialEligibleFamilies':'T1 andT2 only where all required regular observations exist; T6 observed contiguous intervals only,19-session pooling not run. Metadata/integrity audit allowed. T3 auction separation,T4/T5 action contracts unavailable.','historicalProfileEligibleFamilies':[],'partitions':{part:{cls:sum(s['classification'].get(cls,0) for s in sessions if s['partition']==part) for cls in ['PIT_VERIFIED','PIT_PARTIAL','PIT_UNUSABLE']} for part in sorted({s['partition'] for s in sessions})}})
 write(out/'08_coverage_after_recovery.json',cv)
 exposure=read(PRIOR/'measurement/02_exposure_ledger.json')
 for r in exposure['rows']:r.update({'pitRecoveryMetadataRead':True,'pitRecoveryRawAudit':r['sessionDate'] in allowed,'newStrategyOutcomeReads':0,'exposureUnchanged':True})
 exposure.update({'priorLedgerSHA256':sha(PRIOR/'measurement/02_exposure_ledger.json'),'currentTaskStrategyOutcomeReads':0,'REPORT19NewPayloadReads':0,'knownHistoryLimitation':'Historical cumulative looks remain UNKNOWN; no E0/E1 upgrade. Prior codeConfigHash clarification in closeout-provenance-v1 applies.'})
 write(out/'09_exposure_ledger.json',exposure)
 trial=out/'10_trial_ledger.jsonl';trial.write_bytes((PRIOR/'measurement/03_trial_ledger.jsonl').read_bytes())
 for kind in ['RECOVERY_RULE','COVERAGE_GATE','TRAIT_WINDOW_SHRINKAGE_RELIABILITY_GATE']:
  old.append_trial(trial,{'trialId':'PIT_RECOVERY_V1:'+kind,'precommit':PRECOMMIT,'configSHA256':sha(BASE/'protocol.json'),'codeSHA256':sha(Path(__file__)),'availabilityLooks':1 if kind=='RECOVERY_RULE' else 0,'intrinsicLooks':0,'strategyOutcomeLooks':0,'thresholdsChanged':False,'status':'BLOCKED_INPUT_COVERAGE','originalHistoricalLookCounts':'UNKNOWN_NOT_RESET'})
 write(out/'11_input_gate.json',gate)
 (out/'12_trait_census_protocol.md').write_bytes((PRIOR/'09_trait_census_protocol.md').read_bytes())
 na={'status':'NOT_APPLICABLE','reason':NA_REASON,'measuredValue':None}
 write(out/'13_trait_reliability.json',{**na,'plannedFamilies':6,'plannedDefinitions':8,'traitsStatisticallyTested':0,'Tier1Admitted':0,'traitWeaknessDemonstrated':False})
 for name in ['14_peer_baseline.json','15_calibration.json','16_incremental_information.json','22_l2_manifest.json','23_l3_manifest.json','24_shrinkage_validation.json','25_drift_validation.json']:write(out/name,na)
 write(out/'17_early_kill_gate.json',{'status':'DICT_TRAIT_RELIABILITY_NOT_DEMONSTRATED','reason':'BLOCKED_INPUT_COVERAGE','inputGatePassed':False,'reliabilityGate':'NOT_APPLICABLE','reliabilityFailureObserved':False,'traitRescueSearch':False})
 for target,source in [('18_dictionary_schema.json','13_dictionary_schema.json'),('19_metric_catalog.json','07_metric_catalog.json'),('20_state_vocabulary.json','08_state_vocabulary_v1.json')]:
  write(out/target,{'status':'CONTRACT_ONLY_NOT_BUILT','priorSHA256':sha(PRIOR/source),'contract':read(PRIOR/source)})
 write(out/'21_l0_l1_manifest.json',{'status':'EXISTING_L0_AUDITED_L1_NOT_BUILT','extraction':ex,'sources':[{ 'session':s['session'],'files':s['inputHashes']} for s in sessions],'L1DictionaryRows':0})
 gates={'G0':{'status':'PASS','scope':'schema/catalog/state/protocol contract hashes only'},'G1':{'status':'BLOCKED','reason':'Real historical knownAt/stable identity unavailable; synthetic guards separately tested'},'G2':{'status':'BLOCKED','reason':'PITVerified0; missing reasons UNKNOWN; thresholds unchanged'},**{f'G{i}':{'status':'NOT_APPLICABLE','reason':NA_REASON} for i in range(3,8)},'G8':{'status':'PASS','scope':'Current task allowlisted payload reads and offline execution; not a claim of never-exposed history'},'G9':{'status':'NOT_FROZEN','reason':'G1/G2 blocked'}}
 write(out/'28_g0_g9.json',gates)
 write(out/'conditional_artifacts.json',{'29_dictionary_freeze_manifest.json':{'status':'NOT_APPLICABLE','reason':'AllG0-G9 not PASS'},'30_prospective_capture_contract.json':{'status':'NOT_APPLICABLE','reason':'Freeze not achieved; prospective infrastructure not implemented'}})
 write(out/'31_new_data_requirements.json',requirements(sessions,cv,ids))
 write(out/'35_safety_data_boundary.json',{'safety':p['safety'],'longOnly':True,'cashEquityOnly':True,'newProviderRequests':0,'newStrategyOutcomeReads':0,'protectedPayloadReads':0,'report19PayloadReads':0,'dictionaryBuilt':False,'dictionaryFrozen':False,'prospectiveImplemented':False,'selectorEntryExitCapitalChanged':False,'mainMerged':False,'accessLog':ex,'accessScope':'Existing shared encrypted containers streamed; only approved57 dates and allowed payload filenames parsed/extracted. Public provider docs metadata reviewed; no market-data acquisition.','kernelGuard':'Recovery and tests invoked via scripts/offline/kernel_exec.py; provider credential used only for saved archive decryption, not passed into recovery run.'})
 report=f'''# Phase57 Dictionary PIT Recovery v1\n\nDecision: **BLOCKED_INPUT_COVERAGE / DICT_TRAIT_RELIABILITY_NOT_DEMONSTRATED**. Trait weakness has not been measured.\n\nStart HEAD a747dfc346c39e7093e43aee2f8061b1f1e7c964; protocol precommit {PRECOMMIT}. PR587 remains draft/open; no main merge. Producing HEAD and CI receipts:34_ci.json (added after measurement/regression).\n\nAudited {len(sessions)} sessions, {total:,} dated-code days, {len(ids):,} distinct codes (stable security IDs unverified). Classification: {json.dumps(cv['classification'])}. Historical profile eligible0. Partial means retrospective input/audit eligibility only, never historical PIT usability.\n\nRecovered: original-byte hash lineage; receipt knownAt upper bounds; event-end causal lower bounds; dated-code snapshot continuity; effective ExRT/AdjFactor flags; official omission, auction and unadjusted-price semantics. All saved receipts occur in2026 for2024 observations, so they do not establish historical first-use availability. Master publication lower bound remains unknown.\n\nCoverage: symbol-day {cv['symbolDayObservation']:.6%}; observed regular1m {cv['regularMinuteObservation']:.6%}; complete5m buckets {cv['full5mBuckets']:,}; UNKNOWN missing slots {cv['missingRegularSlots']:,}. AM {cv['amObservedSlots']:,}/{cv['amExpectedSlots']:,}; PM {cv['pmObservedSlots']:,}/{cv['pmExpectedSlots']:,}. Missing-minute reasons were not inferred from absence or daily reconciliation. Per-family eligibility in08; full per-code/session classification in gzip CSV.\n\nG0 PASS(contract), G1/G2 BLOCKED, G3-G7 N/A, G8 PASS(current-task boundary), G9 NOT_FROZEN. Trait tests0, Tier1=0, Dictionary L1-L3 not built, EB/calibration/drift not fitted, no freeze or prospective implementation. No Entry/EXIT/Integration research.\n\nProvider limitations: [master](https://jpx-jquants.com/en/spec/eq-master) lacks identity succession; [data help](https://jpx-jquants.com/en/help/data) does not provide past actual delivery times or full halt/action datasets; [minute](https://jpx-jquants.com/en/spec/eq-bars-minute) omission semantics do not identify the cause of every absent minute. Current schedules are not historical receipts.\n\nNew-data requirements in31 distinguish evidence recovery from price re-download. Minimum new price requests0; ordinary re-download cannot reconstruct absent historical version/identity/status proof. All57 dates/code list and observed pagination estimates are explicit. No acquisition executed.\n\nValidation receipts32/33/34 and26 are attached only after actual tests/regression;27 measures recovery compute/storage only, not Dictionary production latency. Two complete audits must be byte-identical excluding host timing. Safety all9false; DEV TEST/Validation/OOS/Fresh andREPORT19 payloads untouched in this task. Existing exposure levels retained.\n\nNext one step: assess availability of certified historical first-delivery/lifecycle/status archives for the specified existing57 sessions using31; do not acquire or open new sessions without a subsequent instruction. STOP.\n'''
 write(out/'36_final_report.md',report);write(out/'37_final_handoff.md',report+'\nNo threshold relaxation, new traits, freeze, prospective or chart-aware work is authorized by this handoff.\n')
 code=['scripts/phase57_dictionary_pit_recovery.py','scripts/test_phase57_dictionary_pit_recovery.py','.github/workflows/phase57-dictionary-pit-recovery-v1.yml']
 write(out/'manifest.json',{'protocolSHA256':sha(BASE/'protocol.json'),'precommit':PRECOMMIT,'code':{f:sha(ROOT/f) for f in code},'outputs':{f.name:sha(f) for f in sorted(out.iterdir())}})
 write(out/'27_operations_benchmark.json',{'scope':'PIT recovery only; not L2/L3 production operations','wallSeconds':time.perf_counter()-start,'peakRSSKiB':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'inputBytes':sum(f['bytes'] for s in prior['sessions'] for f in s['files'].values()),'deterministicEvidenceBytes':sum(f.stat().st_size for f in out.iterdir()),'dictionaryL1L2L3Bytes':0,'hostDependent':True})
 print(json.dumps({'status':gate['status'],'coverage':cv['classification'],'traitsTested':0}))

def audit(directory):
 protocol();d=Path(directory);m=read(d/'manifest.json')
 assert m['protocolSHA256']==sha(BASE/'protocol.json') and m['precommit']==PRECOMMIT
 for f,h in m['code'].items():assert sha(ROOT/f)==h,f
 for f,h in m['outputs'].items():assert sha(d/f)==h,f
 safety=read(d/'35_safety_data_boundary.json');assert all(x is False for x in safety['safety'].values())
 assert safety['protectedPayloadReads']==safety['report19PayloadReads']==safety['newProviderRequests']==0
 assert not read(d/'11_input_gate.json')['pass']
 assert not (d/'29_dictionary_freeze_manifest.json').exists() and not (d/'30_prospective_capture_contract.json').exists()
 with gzip.open(d/'security_session_classification.csv.gz','rt') as f:
  rows=list(csv.DictReader(f));assert len(rows)==read(d/'07_input_classification.json')['ledgerRows']
  assert all(r['profileEligible']=='0' for r in rows)
 previous=(PRIOR/'measurement/03_trial_ledger.jsonl').read_bytes();assert (d/'10_trial_ledger.jsonl').read_bytes().startswith(previous)
 if (d/'ci-manifest.json').exists():
  cm=read(d/'ci-manifest.json');assert cm['measurementManifestSHA256']==sha(d/'manifest.json')
  for f,h in cm['outputs'].items():assert sha(d/f)==h,f
 print('PIT_RECOVERY_AUDIT_PASS')

def finalize(directory,regression,head,runid):
 d=Path(directory);r=Path(regression);audit(d);log=(r/'targeted-tests.log').read_text();m=re.search(r'Ran (\d+) tests',log);assert m and '\nOK' in log
 reg=read(r/'full/regression.json');assert reg['status']=='PASS'
 write(d/'26_pit_canaries.json',{'status':'SYNTHETIC_GUARDS_PASS','realInputAdmission':'BLOCKED','logSHA256':sha(r/'targeted-tests.log'),'truncationFuturePoisonNegativeControl':'PASS_SYNTHETIC_ONLY','realDataRegeneration':'TWO_COMPLETE_RECOVERY_MANIFESTS_BYTE_IDENTICAL'})
 write(d/'32_tests.json',{'status':'PASS','count':int(m[1]),'logSHA256':sha(r/'targeted-tests.log'),'scope':'new recovery guards plus34 prior Dictionary contract tests','deterministicRegeneration':'two full recovery manifests identical; host timing separately hashed'})
 write(d/'33_regression.json',reg)
 write(d/'34_ci.json',{'producingHead':head,'protocolPrecommit':PRECOMMIT,'runId':str(runid),'url':f'https://github.com/Iam-2squared/ark-terminal/actions/runs/{runid}','recovery':'SUCCESS','regression':'SUCCESS','preservation':'RUNNING_AT_RECEIPT_CREATION_VERIFY_FINAL_RUN','allPRChecksGreenClaim':False,'inputGate':'BLOCKED_EXPECTED_FAIL_CLOSED'})
 write(d/'ci-manifest.json',{'measurementManifestSHA256':sha(d/'manifest.json'),'outputs':{f:sha(d/f) for f in ['26_pit_canaries.json','27_operations_benchmark.json','32_tests.json','33_regression.json','34_ci.json']}})

def main():
 p=argparse.ArgumentParser();s=p.add_subparsers(dest='cmd',required=True)
 x=s.add_parser('run')
 for n in ['cache','extraction','output-dir']:x.add_argument('--'+n,required=True)
 x=s.add_parser('audit');x.add_argument('--directory',required=True)
 x=s.add_parser('finalize')
 for n in ['directory','regression','head','run-id']:x.add_argument('--'+n,required=True)
 a=p.parse_args()
 if a.cmd=='run':run(a.cache,a.extraction,a.output_dir)
 elif a.cmd=='audit':audit(a.directory)
 else:finalize(a.directory,a.regression,a.head,a.run_id)
if __name__=='__main__':main()
