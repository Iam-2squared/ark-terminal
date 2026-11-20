/**
 * Read-only 2026 RSS original State9 -> Frozen First Entry P1_Q70 SOURCE gate.
 * Verifies original as-of State9 events, not a P1 feature matrix or BUY signal.
 * Never infers broker knownAt, Va, Selector watch or private model weights.
 */
import fs from 'node:fs';
import {createHash} from 'node:crypto';
import zlib from 'node:zlib';
import readline from 'node:readline';

export const STAGE4_SCHEMA='ARK_NO11_2026_RSS_STATE9_TO_FROZEN_FIRST_ENTRY_P1_GATE_V1';
export const FROZEN_ENTRY_BLOB='62f10b9f12fc968daa2a9393737f2323cdd99307';
export const MASTER_SHA='22d31026c76dd1a555a2deed2d2b5743004687a239dcc8856b5abeae47782056';
export const SOURCE_INDEX_SHA='4828a387aca426b9692fafa2322aea5384da41a1b0be69b98ace7b74fd8b86e0';
export const SOURCE_AUDIT_SHA='04294e96395361e6f7030b68bd008135cbe296c588858d0e01e8023fe800f0a7';
export const BASELINE_SHA='2e79d4f530ed492bf8c82a1df63b641ba1b3ab5c6ab4608c6a9b9c3adefbd5bc';
export const REQUIRED_GATES=Object.freeze([
 'ACTUAL_RSS_FIRST_RECEIVED_AT_NOT_CERTIFIED',
 'ORIGINAL_FROZEN_SELECTOR_WATCH_EVENT_NOT_CERTIFIED',
 'ORIGINAL_1M_VALUE_VA_AND_VWAP_NOT_CERTIFIED',
 'COMPLETE_FROZEN_P1_148_NUMERIC_15_CATEGORICAL_FEATURES_NOT_CERTIFIED',
 'ORIGINAL_P1_MODEL_PREPROCESSOR_AND_Q70_THRESHOLD_NOT_VERIFIED',
 'ORIGINAL_P1_SCORE_AND_FIRST_INTENT_NOT_REPRODUCED'
]);
const fail=code=>{throw Error(code)};
const check=(ok,code)=>{if(!ok)fail(code)};
const hex=s=>typeof s==='string'&&/^[0-9a-f]{64}$/.test(s);
export const sha256=b=>createHash('sha256').update(b).digest('hex');
export function gitBlob(b){
 const clean=Buffer.from(b.toString('utf8').replace(/\r\n/g,'\n'));
 return createHash('sha1').update(Buffer.from('blob '+clean.length+'\0')).update(clean).digest('hex');
}
export const GRID=Object.freeze([
 ...Array.from({length:151},(_,i)=>540+i),
 ...Array.from({length:175},(_,i)=>750+i),930
]);
const clock=n=>String(Math.floor(n/60)).padStart(2,'0')+':'+String(n%60).padStart(2,'0');
const minute=s=>{check(/^\d\d:\d\d$/.test(s),'NO11_P1_INVALID_CLOCK');return +s.slice(0,2)*60+(+s.slice(3))};
check(GRID.length===327,'NO11_P1_GRID_CHANGED');

export function checkFrozenP1Contract(x){
 const m=x?.feature_manifest;
 check(x?.document_id==='WORK_FIRST_ENTRY_V2_CORRECTED_LINEAGE_FAST_FREEZE_20261003'&&
   x.EntryFrozen_requires_independent_audit_PASS===true&&
   x.family==='P1'&&x.Primary_Freeze_Target==='P1_Q70'&&
   x.decision?.threshold_policy==='Q70'&&
   x.decision?.first_cross==='score>=threshold at earliest causal row'&&
   x.watch?.activation==='first valid Selector selection'&&
   x.watch?.repeated_Selector==='refresh same watch; no parallel candidate'&&
   x.watch?.missing_source_bar_generated===false&&
   m?.P0_numeric?.length===110&&m?.P1_numeric?.length===148&&
   m?.P1_categorical?.length===15&&
   ['w5/value','activity/1/value','vwapDistancePct','activeMinutesSinceSelector','state/observed']
     .every(k=>m.P1_numeric.includes(k))&&
   ['state/formal_primary','history/previous_distinct_formal_primary']
     .every(k=>m.P1_categorical.includes(k))&&
   x.safety?.productionReady===false&&x.safety?.rssOrderFunctionAllowed===false&&
   x.safety?.automaticPromotionAllowed===false,
   'NO11_P1_FROZEN_CONTRACT_CHANGED');
 return Object.freeze({frozenContractGitBlob:FROZEN_ENTRY_BLOB,
   family:'P1',policy:'Q70',p0Numeric:110,p1Numeric:148,p1Categorical:15,
   privateModelArtifactsVerified:false,originalP1ModelExecuted:false});
}
export function checkStage3Report(r){
 const n=r?.actualReplayedOriginalFirstEligibleCount,c=r?.researchTechnicalTickCounts;
 check(r?.schemaId==='ARK_NO11_2026_RSS_ORIGINAL_RC2_SPARSE_MISSING_REPLAY_V1'&&
   r.status==='TECHNICAL_SPARSE_DUAL_ENGINE_PASS_RESEARCH_ONLY'&&
   r.previous==='2026-10-09'&&r.current==='2026-10-13'&&
   r.inspectedOriginalFirstSymbols===950&&
   Number.isInteger(n)&&n>0&&n<=244&&
   r.sourceCoverageCounters?.sourceInspected===950&&
   r.sourceCoverageCounters?.replayedPairs===n&&
   r.sourceCoverageCounters?.meetsSourceAnchorAndCurrentFloor===244&&
   r.eligibleSourcePairsInFixedScope===244&&r.eligibleNotReplayed===244-n&&
   r.fullEligibleSetTechnicalReplayed===(n===244)&&
   c?.totalOriginalDualEngineTickAgreements===n*327&&
   c.nativeAcceptedTicks+c.nativeMissingTickCalls===n*327&&
   c.nativeObservedStateTicks<=c.nativeAcceptedTicks&&
   r.privateState9AsOfEventRows===n*327&&
   r.state9AsOfExportIsResearchOnly===true&&
   /^no11-2026-state9-asof-research-[0-9a-f]{16}\.jsonl\.gz$/.test(r.privateState9AsOfGzipFilename||'')&&
   hex(r.privateState9AsOfGzipSha256)&&
   r.privateState9AsOfGzipFilename.includes(r.privateState9AsOfGzipSha256.slice(0,16))&&
   r.inputSourceIndexSha256===SOURCE_INDEX_SHA&&
   r.originalSourceAuditSha256===SOURCE_AUDIT_SHA&&
   r.baseline950ReportSha256===BASELINE_SHA&&
   r.missingTickSemantics==='ORIGINAL_RC2_STEP_NONE_NOT_FORWARD_FILL'&&
   r.originalNativeRC2BothEnginesInvoked===true&&
   r.brokerKnownAtIsInferredNotObserved===true&&
   r.stateLabelsEligibleForLiveSelectorOrEntry===false&&
   r.futureObservedOutcomeUsedInModelInputs===false&&
   r.h235R0OnReal2026Candidate===false&&
   r.trainingPerformed===false&&r.originalFrozenFilesMutated===false&&
   r.productionReady===false&&r.orderTransmission===false&&
   r.technicalErrorCounts&&Object.keys(r.technicalErrorCounts).length===0,
   'NO11_P1_STAGE3_RECEIPT_NOT_VERIFIED');
 return n;
}
const ALLOWED=new Set([
 'schemaId','scheduledClock','researchAssumedBarEnd','sourceLabel',
 'originalNumericStatus','state9CurrentObserved','formalPrimary','basis',
 'directionBasis','activity','originalSource','missingSourceBar',
 'actualBrokerKnownAtCertified','firstEntryP1NativeFeatureRowCertified',
 'eligibleForNativeSelectorOrFirstEntry','futureOutcomeIncluded',
 'productionReady','orderTransmission','symbol','session','sourceArchiveSha256'
]);
export function checkAsOfRow(x,day='2026-10-13'){
 check(x&&typeof x==='object'&&!Array.isArray(x)&&
   Object.keys(x).length===ALLOWED.size&&Object.keys(x).every(k=>ALLOWED.has(k))&&
   x.schemaId==='ARK_NO11_2026_RSS_RC2_TECHNICAL_ASOF_STATE_V1'&&
   x.session===day&&/^[0-9A-Z]{4}\.T$/.test(x.symbol||'')&&
   hex(x.sourceArchiveSha256)&&GRID.includes(minute(x.scheduledClock))&&
   typeof x.missingSourceBar==='boolean'&&
   typeof x.state9CurrentObserved==='boolean'&&
   x.actualBrokerKnownAtCertified===false&&
   x.firstEntryP1NativeFeatureRowCertified===false&&
   x.eligibleForNativeSelectorOrFirstEntry===false&&
   x.futureOutcomeIncluded===false&&x.productionReady===false&&
   x.orderTransmission===false,'NO11_P1_UNSAFE_ASOF_ROW');
 if(x.missingSourceBar){
   check(x.sourceLabel===null&&x.researchAssumedBarEnd===null&&
     x.originalNumericStatus==='NOT_AVAILABLE'&&
     x.state9CurrentObserved===false&&x.formalPrimary===null&&
     x.basis===null&&x.directionBasis===null&&x.activity===null&&
     x.originalSource===null,'NO11_P1_MISSING_BAR_FILLED');
 }else{
   check(x.sourceLabel===day+'T'+x.scheduledClock+':00+09:00'&&
     x.originalNumericStatus==='ACCEPTED'&&
     x.originalSource==='RSS_CHART_VALUE2_RESEARCH_ONLY_NOT_JQUANTS_V2'&&
     Date.parse(x.researchAssumedBarEnd)===Date.parse(x.sourceLabel)+60000,
     'NO11_P1_ASOF_SOURCE_TIME_INVALID');
   check(x.state9CurrentObserved?typeof x.formalPrimary==='string'&&
     x.formalPrimary.length>0:x.formalPrimary===null,
     'NO11_P1_STALE_OR_MISSING_STATE');
 }
 return x;
}
export async function checkPrivateAsOfArchive({report,archive,masterOrder}){
 const expected=checkStage3Report(report);
 check(Array.isArray(masterOrder)&&masterOrder.length===4327&&
   new Set(masterOrder).size===4327,'NO11_P1_MASTER_ORDER_INVALID');
 const order=new Map(masterOrder.map((s,i)=>[s,i]));
 const stat=fs.lstatSync(archive);
 check(stat.isFile()&&!stat.isSymbolicLink()&&stat.size>0&&stat.size<128*1024*1024,
   'NO11_P1_PRIVATE_GZIP_UNSAFE');
 check(sha256(fs.readFileSync(archive))===report.privateState9AsOfGzipSha256,
   'NO11_P1_PRIVATE_GZIP_HASH_CHANGED');
 let symbol=null,prevIndex=-1,local=0,symbols=0,accepted=0,missing=0,observed=0;
 const states=new Map();
 const input=readline.createInterface({
   input:fs.createReadStream(archive).pipe(zlib.createGunzip()),crlfDelay:Infinity
 });
 try{
  for await(const line of input){
   check(line.length>0&&line.length<5000,'NO11_P1_GZIP_LINE_INVALID');
   const r=checkAsOfRow(JSON.parse(line),report.current);
   if(r.symbol!==symbol){
     check(symbol===null||local===327,'NO11_P1_ASOF_SYMBOL_GRID_INCOMPLETE');
     const i=order.get(r.symbol);
     check(Number.isInteger(i)&&i>prevIndex,'NO11_P1_ASOF_SYMBOL_ORDER_CHANGED');
     symbol=r.symbol;prevIndex=i;local=0;symbols++;
     check(symbols<=expected,'NO11_P1_TOO_MANY_SYMBOLS');
   }
   check(local<327&&r.scheduledClock===clock(GRID[local]),
     'NO11_P1_ASOF_CLOCK_ORDER_CHANGED');
   local++;
   if(r.missingSourceBar)missing++;else accepted++;
   if(r.state9CurrentObserved){
     observed++;states.set(r.formalPrimary,(states.get(r.formalPrimary)||0)+1);
   }
  }
 }finally{input.close();}
 check(local===327&&symbols===expected&&
   accepted===report.researchTechnicalTickCounts.nativeAcceptedTicks&&
   missing===report.researchTechnicalTickCounts.nativeMissingTickCalls&&
   observed===report.researchTechnicalTickCounts.nativeObservedStateTicks&&
   JSON.stringify(Object.fromEntries([...states].sort()))===
     JSON.stringify(report.observedOriginalPrimaryStates),
   'NO11_P1_ASOF_EVENT_COUNTS_DIVERGED');
 return Object.freeze({state9ResearchSymbols:symbols,
   scheduledState9Ticks:symbols*327,acceptedSource1m:accepted,
   explicitlyMissingSource1m:missing,observedState9PrimaryTicks:observed,
   full244ResearchScope:symbols===244});
}
