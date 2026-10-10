import json,hashlib,datetime,csv,gzip,collections,sys,tempfile
from pathlib import Path
R=Path(__file__).resolve().parents[1]; B=R/'docs/evidence/phase57-dictionary-procurement-v1'; P=R/'docs/evidence/phase57-dictionary-pit-recovery-v1/measurement'; SAVED=B/'measurement'; temp=tempfile.TemporaryDirectory() if '--verify' in sys.argv else None; O=Path(temp.name) if temp else SAVED; O.mkdir(exist_ok=True)
def h(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def out(n,x):
 p=O/n;p.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n')
def read(n):return json.loads((P/n).read_text())
p=json.loads((B/'protocol.json').read_text());ts='2026-09-19T11:01:01.642762+00:00'
sources=[]
def source(id,url,finding,limitation):
 x=dict(id=id,url=url,officialProviderStatus='OFFICIAL_PUBLIC_DOCUMENTATION',retrievedAt=ts,eventTime=None,knownAtSemantics='retrieval time describes this documentation review only',revisionSemantics='documentation may change; not historical delivered data',coverage='specification only; zero security-day certificates',confidence='DOCUMENTED_SPECIFICATION',finding=finding,limitations=limitation,hashScope='analyst paraphrase artifact, NOT provider page bytes')
 x['artifactSHA256']=hashlib.sha256(json.dumps(x,sort_keys=True).encode()).hexdigest();sources.append(x)
source('personal-minute','https://jpx-jquants.com/en/spec/eq-bars-minute','No-trade minutes omitted; unadjusted bars; errors may be overwritten. PM auction mixed into opening minute.','Missing bar alone cannot distinguish no trade and missing data.')
source('personal-master','https://jpx-jquants.com/en/spec/eq-master','Dated code snapshots available; lifecycle and predecessor/successor history not provided.','Continuity is not certified stable identity.')
source('personal-faq','https://jpx-jquants.com/en/help/data','No historical actual update-time records, version numbers, ETags or halt feed; full action dataset unavailable. Disclosure-record datasets retain original/corrected records.','No historical availability proof for exact cached OHLC bytes.')
source('tdnet','https://jpx-jquants.com/en/spec/td-list','TimelyDisclosure add-on, five-year records, official disclosure date/time; new disclosure numbers for corrections; no complete linked revision history or API availability timestamp.','Entitlement not evidenced; announcement metadata cannot certify historical price version.')
source('pro-ca','https://jpx.gitbook.io/j-quants-pro/api-reference/corporate_action','Corporate actions via SFTP/Snowflake, not API; notifications have reference and corrected/deleted CA reference. Includes mergers, delistings, splits and master changes.','Potential procurement candidate, NOT proven entitled or complete for requested57 days; exact price version and trading-state proof unresolved.')
source('pro-history','https://jpx.gitbook.io/j-quants-pro/data-spec','Corporate action history: cash dividends since2013, others since2015.','Temporal coverage does not prove current contract or exact knownAt availability.')
source('reference','https://www.jpx.co.jp/english/markets/paid-info-equities/reference/index.html','Master File and reference services require contract; fee depends on service and use scope.','No quote requested, no purchase; historical version and full lifecycle certification need provider confirmation.')
source('delisting','https://www.jpx.co.jp/english/listing/stocks/delisted/','Official delisted-company list is an event reference.','Current web list is not exhaustive historical issuance lineage or receipt archive.')
out('01_start_state.json',{'head':p['sourceHead'],'protocolPrecommit':'f3d6506775aedc3494428301c99485e93be2f10f','PR':587,'state':'OPEN_DRAFT','priorEvidenceManifestSHA256':h(P/'manifest.json'),'priorExposureSHA256':h(P/'09_exposure_ledger.json'),'priorTrialSHA256':h(P/'10_trial_ledger.jsonl'),'localUserUntrackedFilesPreserved':True})
out('02_procurement_feasibility.json',{'route':'B','status':'UNAVAILABLE_WITH_VERIFIED_EXISTING_ENTITLEMENT','universalUnavailabilityProven':False,'existingContractEvidence':{'source':'docs/evidence/phase57-long-only-minimal-acquisition-gate/gate-report.json','sourceSHA256':h(R/'docs/evidence/phase57-long-only-minimal-acquisition-gate/gate-report.json'),'snapshot':'2026-09-15 user screenshot','plan':'LIGHT + TICK_PLUS_OHLCMIN','scheduledEnd':'2026-10-06','liveReverified':False},'candidates':[{'product':'TimelyDisclosure add-on','purpose':'announcements','entitlement':'UNVERIFIED','cost':None,'purchase':False},{'product':'J-Quants Pro Corporate Action SFTP/Snowflake','purpose':'action revisions and lineage','entitlement':'UNVERIFIED','cost':None,'purchase':False},{'product':'JPXI Reference Master File','purpose':'security identity','entitlement':'UNVERIFIED','cost':None,'purchase':False}],'reason':'Personal endpoint specifications and saved receipts cannot certify historical OHLC delivery; alternatives require contract and source verification. No ordinary refetch performed.'})
out('03_provider_semantics.json',{'sources':sources,'failedDocumentationFetches':['fin-dividend HTTP403','pro llms index unavailable'],'marketDataRequests':0,'supportMessagesSent':0})
for n,prior in [('04_known_at_evidence.json','03_known_at_recovery.json'),('05_security_identity.json','04_security_identity_recovery.json'),('06_corporate_actions.json','05_corporate_action_pit.json'),('07_trading_state.json','06_missing_minute_classification.json'),('08_missing_reason.json','06_missing_minute_classification.json')]:
 out(n,{'status':'UNRESOLVED','priorArtifact':str((P/prior).relative_to(R)),'priorSHA256':h(P/prior),'newHistoricalCertificates':0,'details':'Public specification evidence does not certify any exact historical cached version; UNKNOWN preserved.'})
ledger=P/'security_session_classification.csv.gz';assert h(ledger)==p['sourceLedgerSHA256']
counts=collections.Counter();groups=collections.defaultdict(collections.Counter);symbols=set();dates=set();retro=collections.Counter();n=0
with gzip.open(ledger,'rt') as f:
 for row in csv.DictReader(f):
  # No new admissibility certificate: re-evaluate all rows without reading prices.
  cls='PIT_UNUSABLE' if row['classification']=='PIT_UNUSABLE' else 'PIT_PARTIAL'
  counts[cls]+=1;groups[row['session']][cls]+=1;symbols.add(row['code']);dates.add(row['session']);n+=1
  for metric,col in [('T1_LOG_RANGE','retrospectiveRange'),('T2_LOG_TURNOVER','retrospectiveTurnover')]:retro[metric]+=int(row[col])
assert n==218319
out('09_reclassification.json',{'rowsReclassified':n,'sourceLedgerSHA256':h(ledger),'method':'All saved audited metadata rows scanned; no new certificates => no upgrade. No raw price replay.','counts':{k:counts[k] for k in ['PIT_VERIFIED','PIT_PARTIAL','PIT_UNUSABLE']},'symbols':len(symbols),'sessions':len(dates),'bySession':groups})
coverage=read('08_coverage_after_recovery.json')
out('10_metric_specific_coverage.json',{'historicalProfileEligible':{m:{'symbolDays':0,'symbols':0,'sessions':0,'nEff':0,'marketCoverage':0,'knownAt':0,'identity':0} for m in coverage['metricEligibility']},'retrospectiveOnly':dict(retro),'missingSlots':coverage['missingRegularSlots'],'missingReason':'UNKNOWN','seedAdmitted':0,'priorCoverageSHA256':h(P/'08_coverage_after_recovery.json'),'priorDetailedCoverage':str((P/'08_coverage_after_recovery.json').relative_to(R))})
out('11_input_gate.json',{'status':'BLOCKED_INPUT_COVERAGE','gates':p['historicalGates']['G2'],'verifiedCoverage':0,'classifiedMissingCoverage':0,'traitEvaluationAllowed':False})
out('12_trait_protocol.json',{'status':'PRECOMMITTED_NOT_EXECUTED','catalog':'docs/evidence/phase57-behavior-dictionary-v1/07_metric_catalog.json','catalogSHA256':h(R/'docs/evidence/phase57-behavior-dictionary-v1/07_metric_catalog.json'),'statistics':p['statistics'],'gates':p['historicalGates']})
for n in ['13_trait_reliability','14_peer_baseline','15_calibration','16_incremental_information','17_reliability_gate','19_l0_l3_manifests','20_shrinkage','21_drift','24_dictionary_freeze_manifest']:
 out(n+'.json',{'status':'NOT_APPLICABLE','reason':'Historical input gate blocked; no trait test, dictionary, EB, drift or freeze claim','traitEvaluations':0,'tier1':0})
out('18_dictionary_schema.json',{'status':'CONTRACT_ONLY','priorSchema':read('18_dictionary_schema.json'),'foundation':'Immutable raw receipts plus draft normalization; no historical profile'})
out('22_pit_canaries.json',{'status':'LOCAL_PASS','testModule':'scripts.test_phase57_dictionary_prospective','canaries':['receipt non-retroactivity','future poison/truncation','no historical backfill','protected-budget rejection','UNKNOWN preservation','code reuse conflict','source version unknown','append-only triggers','lineage'],'scope':'Synthetic foundation guards; NOT real source PIT Gate PASS'})
out('23_g0_g9.json',{'G0':'PASS','G1':'BLOCKED_REAL_SOURCE','G2':'BLOCKED','G3':'NOT_APPLICABLE','G4':'NOT_APPLICABLE','G5':'NOT_APPLICABLE','G6':'NOT_APPLICABLE','G7':'NOT_APPLICABLE_DICTIONARY_NOT_BUILT','G8':'PASS','G9':'NOT_FROZEN'})
out('25_historical_procurement_blocker.json',{'status':'UNAVAILABLE_WITH_VERIFIED_EXISTING_ENTITLEMENT','allProvidersImpossible':False,'unresolved':['exact historical delivery version and receipt','effective-period stable identity','announcement/revision action ledger','complete trading-state provenance'],'requestedScope':{'dates':sorted(dates),'codeCount':len(symbols),'securityDays':218319},'minimumEvidence':'hash-bound archived delivery receipts + certified lifecycle and action revision ledger + trading-state intervals; confirm archives exist before obtaining prices','candidateContracts':'02_procurement_feasibility.json','cost':None,'costStatus':'QUOTE_AND_ENTITLEMENT_UNCONFIRMED','purchase':False,'samePriceRefetchRequestEstimate':860,'samePriceRefetchSolvesBlocker':False})
out('26_prospective_foundation_contract.json',{'name':'JPX_STOCK_BEHAVIOR_DICTIONARY_PROSPECTIVE_FOUNDATION_V1','status':'OFFLINE_INTAKE_IMPLEMENTED','maturity':p['prospective'],'limitations':['Not Frozen Dictionary','No scheduler activated','No provider credentials accessed','Identity/action/status claims stored with evidence references but not independently certified','Daily collection requires dedicated non-overlapping dates, exchange calendar, source entitlements, durable private storage and receipts','Accumulating60 days alone cannot guarantee reliability or freeze'],'foundationCodeSHA256':h(R/'scripts/phase57_dictionary_prospective.py')})
out('27_prospective_capture_manifest.json',{'productionCapturedSessions':0,'admittedSessions':0,'historySeedSessions':0,'dailyCollectionActive':False,'neededBasicSessions':20,'neededTier1MinimumSessions':60,'neededLongWindowSessions':250,'earliestFreezeDate':None,'dateCondition':'At least60 admitted exchange sessions from actual start plus all gates and >=1 Tier1; 250-day metrics remain insufficient until250','storage':'User-selected durable private SQLite receipt store; transactional hash chain and no update/delete APIs','retention':'Confirm source contract retention and cancellation terms before collection','sourceVersion':'null when unavailable; payload hash never impersonates provider version'})
exposure=read('09_exposure_ledger.json')
out('28_data_budget.json',{'protectedPayloadReads':0,'report19PayloadReads':0,'newPriceRequests':0,'newHistoricalCertificateRequests':0,'newStrategyOutcomeReads':0,'publicDocumentationReview':True,'exposureCountsUnchanged':exposure['classificationCounts'],'prospectiveAllocation':'NONE_ACTIVE','futureCapturedExposure':'E1, never subsequently declared unseen Entry/EXIT data'})
out('29_tests.json',{'status':'PASS','tests':95,'foundationTests':25,'inheritedContractTests':70,'command':'ARK_TEST_OFFLINE=1 python scripts/offline/kernel_exec.py python -m unittest -q scripts.test_phase57_dictionary_prospective scripts.test_phase57_dictionary_pit_recovery scripts.test_phase57_behavior_dictionary'})
out('30_regression.json',{'status':'PENDING'})
out('31_ci.json',{'status':'PENDING','startHeadChecks':'action_required; not green'})
out('32_safety.json',{'flags':p['safety'],'newAcquisition':0,'purchases':0,'messagesSent':0,'sealedPayloadReads':0,'selectorEntryExitCapitalChanges':0,'mainMerge':False})
(O/'33_final_report.md').write_text('''# Historical procurement / prospective foundation

Route B: historical input remains BLOCKED_INPUT_COVERAGE. All218,319 audited metadata rows were scanned again: VERIFIED0 / PARTIAL218,319 / UNUSABLE0. No new raw price read or certificate acquisition. Historical trait reliability remains unmeasured, not disproven.

Official personal API documentation cannot establish the required historical price delivery, identity or trading-state proof. Pro corporate-action and JPXI reference products are possible additional procurement routes; rights, price and full57-session proof coverage are unverified. Universal impossibility is not claimed. No purchase or support message was sent.

Offline prospective intake supports immutable timestamped receipts, source-version uncertainty, evidence-linked identity/action/status input, hash-chain audit, as-of replay, correction retention and draft session-aware1m-to5m summaries. It has no network, scheduler, order or promotion path. Independent source certification and daily collection activation remain required. The foundation is not a frozen Dictionary and has collected0 production sessions.

Basic20, Tier1 minimum60, long-window250 admitted exchange sessions; nEff>=12 per19-session window and at least300 securities. All original reliability/coverage gates remain. Sixty sessions are a minimum, not a guarantee. No deterministic completion date exists before source readiness and actual admitted collection start.

Historical G0/G8 PASS; G1/G2 BLOCKED; G3-G7 N/A; G9 NOT_FROZEN. Tier1=0. All9 safety flagsfalse; sealed payload reads0, provider price requests0. No historical seed admitted. Future Dictionary sessions must have dedicated allocation and become E1, never reused as unseen Entry/EXIT evidence.

Next: verify prospective source entitlement, identity/action/trading-state coverage, storage/retention and a non-overlapping calendar allocation, then activate receipt collection under the fixed contract. Additional paid contracts require explicit approval.
''')
(O/'34_final_handoff.md').write_text((O/'33_final_report.md').read_text())
# Preserve prior ledgers and append task events without downgrading history.
out('exposure_ledger_delta.json',{'priorHash':h(P/'09_exposure_ledger.json'),'event':'PIT_METADATA_RECLASSIFICATION_ONLY','newOutcomeReads':0,'exposureDowngrades':0})
out('trial_ledger_delta.json',{'priorHash':h(P/'10_trial_ledger.jsonl'),'protocolSHA256':h(B/'protocol.json'),'trial':'procurement_and_prospective_maturity_v1','newTraitTests':0,'thresholdsChanged':False})
out('artifact_manifest.json',{f.name:h(f) for f in sorted(O.iterdir()) if f.is_file() and f.name!='artifact_manifest.json'})
print('generated',len(list(O.iterdir())),'files; scanned',218319,'rows')

if temp:
 manifest=json.loads((SAVED/'artifact_manifest.json').read_text())
 for name,digest in manifest.items():
  assert h(SAVED/name)==digest, 'EVIDENCE_CHANGED:'+name
 for f in O.iterdir():
  if f.name[:2] in {'29','30','31','33','34'} or f.name=='artifact_manifest.json':continue
  assert f.read_bytes()==(SAVED/f.name).read_bytes(), 'REGEN_CHANGED:'+f.name
 temp.cleanup()
 print('All saved hashes verified; metadata-only regeneration identical')
