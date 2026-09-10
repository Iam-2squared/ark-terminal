import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';

const NEW_PATH=process.env.NEW_INVENTORY_PATH;
const OLD_V2_PATH=process.env.ADMISSION_V2_PATH;
const OLD_V21_PATH=process.env.ADMISSION_V21_PATH;
const OUT=process.env.FINALIZE_OUT_DIR??'predict/research';
const DOC=process.env.FINALIZE_DOC_PATH??'docs/phase57-exit-v4-jquants-stage2-fast-allocation-freeze.md';
const TIER2='2aa9fd80596c0f71f2359fb132288a15d563e3fab8e22ecbac54fda308a54a70';
const SCHEMA='f060c654f0d5af5f105f8ba20c47b78950ad433305b735d42f6cbd68f8e2823b';
const SAFETY={executionAllowed:false,brokerWriteAllowed:false,excelOrderWriteAllowed:false,rssOrderFunctionAllowed:false,liveTradingAllowed:false,paperTradingAllowed:false,automaticPromotionAllowed:false,productionUpdateAllowed:false,transmitted:false};
const read=file=>JSON.parse(fs.readFileSync(file,'utf8'));
const sha=value=>crypto.createHash('sha256').update(value).digest('hex');
const capacity=n=>({conservative:n*2,base:Number((n*2.9).toFixed(1)),optimistic:Number((n*3.4).toFixed(1))});
const boundary=rows=>rows.length?{first:rows[0].sessionDate,last:rows.at(-1).sessionDate,count:rows.length}:{first:null,last:null,count:0};
function write(name,value,{compact=false}={}){const text=JSON.stringify(value,null,compact?0:2)+'\n';fs.mkdirSync(OUT,{recursive:true});fs.writeFileSync(path.join(OUT,name),text);const digest=sha(text);fs.writeFileSync(path.join(OUT,name.replace(/\.json$/,'.sha256')),`${digest}  ${name}\n`);return digest;}

if(!NEW_PATH||!OLD_V2_PATH||!OLD_V21_PATH)throw new Error('NEW_INVENTORY_PATH, ADMISSION_V2_PATH and ADMISSION_V21_PATH are required');
const fresh=read(NEW_PATH);
if(fresh.status!=='FAST_METADATA_INVENTORY_COMPLETE')throw new Error('NEW_METADATA_INVENTORY_INCOMPLETE');
const oldRows=[...read(OLD_V2_PATH).auditBySession,...read(OLD_V21_PATH).auditBySession].sort((a,b)=>a.sessionDate.localeCompare(b.sessionDate));
if(oldRows.length!==179||new Set(oldRows.map(x=>x.sessionDate)).size!==179)throw new Error('OLD_METADATA_179_REQUIRED');
const eligible=fresh.sessions.filter(row=>row.status==='ELIGIBLE').sort((a,b)=>a.sessionDate.localeCompare(b.sessionDate));
const blocked=fresh.sessions.filter(row=>row.status!=='ELIGIBLE').sort((a,b)=>a.sessionDate.localeCompare(b.sessionDate));
const idealDownstream={validation:30,historicalHoldout:25,untouchedOos:30,futureReserve:30};
const reserveMinimum=Object.values(idealDownstream).reduce((sum,value)=>sum+value,0);
if(eligible.length<64)throw new Error('ALLOCATION_CAPACITY_CRITICAL_FAIL');
const devA=eligible.length>=175?Math.min(70,eligible.length-reserveMinimum):Math.min(69,eligible.length-4);
const remainingAfterDevA=eligible.length-devA;
let downstream;
if(remainingAfterDevA>=reserveMinimum){
  downstream={...idealDownstream};
}else{
  const keys=Object.keys(idealDownstream);
  downstream=Object.fromEntries(keys.map(key=>[key,1]));
  let remaining=remainingAfterDevA-keys.length;
  while(remaining>0){
    const key=keys
      .filter(candidate=>downstream[candidate]<idealDownstream[candidate])
      .sort((a,b)=>(downstream[a]/idealDownstream[a])-(downstream[b]/idealDownstream[b])||a.localeCompare(b))[0];
    if(!key)break;
    downstream[key]+=1;
    remaining-=1;
  }
}
const devB=Math.max(0,remainingAfterDevA-Object.values(downstream).reduce((sum,value)=>sum+value,0));
let cursor=0;
const split={};
split.devA=eligible.slice(cursor,cursor+=devA);
split.devB=eligible.slice(cursor,cursor+=devB);
split.validation=eligible.slice(cursor,cursor+=downstream.validation);
split.historicalHoldout=eligible.slice(cursor,cursor+=downstream.historicalHoldout);
split.untouchedOos=eligible.slice(cursor,cursor+=downstream.untouchedOos);
split.futureReserve=eligible.slice(cursor,cursor+=downstream.futureReserve);
if(cursor!==eligible.length)throw new Error('ALLOCATION_CURSOR_MISMATCH');
const allocationClassByDate=new Map([
  ...split.devA.map(x=>[x.sessionDate,'DEV_A_LOCKED']),...split.devB.map(x=>[x.sessionDate,'DEV_B_LOCKED']),
  ...split.validation.map(x=>[x.sessionDate,'VALIDATION_LOCKED']),...split.historicalHoldout.map(x=>[x.sessionDate,'HISTORICAL_HOLDOUT_LOCKED']),
  ...split.untouchedOos.map(x=>[x.sessionDate,'UNTOUCHED_OOS_SEALED']),...split.futureReserve.map(x=>[x.sessionDate,'FUTURE_RESERVE_SEALED']),
]);
const oldInventory=oldRows.map(row=>({sessionDate:row.sessionDate,status:'DIAGNOSTIC_ONLY_PRIOR_RESEARCH_EXPOSURE',source:{provider:'J_QUANTS',endpointOrFileClass:'/v2/equities/bars/minute',artifactLineage:row.sessionDate<='2025-10-08'?'capacity-v2-admission-summary-34153192882':'capacity-v2-1-admission-summary-34189128681',rawPersisted:false},counts:{normalizedMinuteRows:row.normalizedMinuteRows,fiveMinuteBars:row.fiveMinuteBars,eligibleJpxSymbolCount:row.eligibleJpxSymbolCount},fingerprints:{minuteSha256:row.minuteSha256,fiveMinuteSha256:row.fiveMinuteSha256,memberSetSha256:row.memberSetSha256},allocationClass:'DIAGNOSTIC_ONLY',exposureStatus:'PRIOR_RESEARCH_EXPOSED',outcomesAccessedHere:false,futureLabelsGeneratedHere:false}));
const newInventory=fresh.sessions.map(row=>{
  const {symbols:_symbols,...metadata}=row;
  return {...metadata,allocationClass:row.status==='ELIGIBLE'?allocationClassByDate.get(row.sessionDate):'BLOCKED_NOT_USABLE',exposureStatus:'METADATA_ONLY_OUTCOME_UNTOUCHED'};
});
const inventory={schemaVersion:1,inventoryId:'PHASE57_EXIT_V4_STAGE2_FAST_SESSION_METADATA_INVENTORY_V1',asOfJst:'2026-09-10',status:'EXACT_METADATA_INVENTORY_COMPLETE',range:fresh.range,totalJquantsSessionsDiscovered:fresh.discoveredSessionCount,existingVerifiedMetadataSessions:oldInventory.length,newlyAuditedMetadataSessions:newInventory.length,eligibleAllocationSessions:eligible.length,blockedSessions:blocked.length,protectedExternal:{first:'2026-01-08',last:'2026-06-11',count:103,newAccess:0},freshExternal:{first:'2026-09-10',reservedCount:25,newAccess:0},sessions:[...newInventory,...oldInventory].sort((a,b)=>a.sessionDate.localeCompare(b.sessionDate)),accessLedger:{newRawSessions:0,newSealedOutcomeSessions:0,protected180To282:0,freshValidationOrOos:0,exitOutcomes:0,futureLabels:0,exitInvocations:0},safety:SAFETY};
const inventoryDigest=write('phase57-exit-v4-stage2-session-metadata-inventory-v1.json',inventory,{compact:true});
const manifest={schemaVersion:1,schemaId:'PHASE57_EXIT_V4_STAGE2_ALLOCATION_MANIFEST_V1',asOfJst:'2026-09-10',status:'FROZEN_RESULT_BLIND',contractVersion:'1.1.0',tier2ContractDigest:TIER2,ordering:'SESSION_DATE_ASCENDING_WITH_EXCLUDED_GAPS',randomShuffleAllowed:false,outcomeFieldsIncluded:false,sessions:inventory.sessions.map(row=>({sessionDate:row.sessionDate,eligibilityStatus:row.status==='ELIGIBLE'?'ELIGIBLE':row.status.startsWith('DIAGNOSTIC')?'DIAGNOSTIC':'EXCLUDED',allocationClass:row.allocationClass,exposureStatus:row.exposureStatus,lineageRef:row.source?.artifactLineage??row.fingerprints?.minuteSha256??null,blockingReasons:row.blockingReasons??[],contractDigest:TIER2})),externalProtectionLedger:{protected180To282:{sessions:103,newAccess:0,allocationAllowed:false},freshValidationOrOos:{sessions:25,newAccess:0,allocationAllowed:false}},safety:SAFETY};
const manifestDigest=write('phase57-exit-v4-stage2-allocation-manifest-v1.json',manifest);
const boundaries=Object.fromEntries(Object.entries(split).map(([key,rows])=>[key,boundary(rows)]));
const idealDownstreamHeld=Object.entries(idealDownstream).every(([key,value])=>split[key].length>=value);
const devATargetHeld=capacity(split.devA.length).base>=200;
const devTotalExtensionHeld=capacity(split.devA.length+split.devB.length).base>=500;
const gate=idealDownstreamHeld&&devATargetHeld&&devTotalExtensionHeld?'DATA_ALLOCATION_FROZEN_DEV_A_READY':'DATA_ALLOCATION_CAPACITY_CONSTRAINED_BUT_USABLE';
const contract={schemaVersion:1,contractId:'PHASE57_EXIT_V4_STAGE2_DATA_ALLOCATION_CONTRACT_V1',contractVersion:'1.1.0',asOfJst:'2026-09-10',status:'FROZEN_RESULT_BLIND',finalGate:gate,tier2Contract:{version:'1.0.0',sha256:TIER2,eligibilitySchemaSha256:SCHEMA,modifiedHere:false},pool:{exactSessionLevelInventoryAvailable:true,confirmedEligibleSessions:eligible.length,confirmedBlockedSessions:blocked.length,diagnosticPriorExposureSessions:oldInventory.length,protectedExternalSessions:103,freshExternalSessions:25},allocationUnit:'JST_TRADING_SESSION',ordering:'OLDEST_ELIGIBLE_TO_NEWEST_ELIGIBLE',randomShuffleAllowed:false,oneSessionOneSplit:true,allocation:{frozen:true,manifestComplete:true,purgeEmbargoDecision:'NONE_SESSION_LOCAL_SELECTOR_AND_ENTRY_STATE',sessionCounts:Object.fromEntries(Object.entries(split).map(([key,rows])=>[key,rows.length])),dateBoundaries:boundaries},developmentPolicy:{devATargetIndependentFirstEnter:200,devAExpectedFirstEnter:capacity(split.devA.length),devBTotalExpectedFirstEnter:capacity(split.devA.length+split.devB.length),devAOnlyMayBecomeNextUnlockCandidate:true,developmentUnlocked:false},protection:{exposedAssignedOosOrReserve:0,protected180To282ReallocationAllowed:false,freshValidationOrOosReallocationAllowed:false,resultBasedReshuffleAllowed:false},stage3:{devAUnlockCandidate:true,developmentUnlocked:false,explicitFutureAuthorizationRequired:true},accessLedger:inventory.accessLedger,safety:SAFETY};
const contractDigest=write('phase57-exit-v4-stage2-data-allocation-contract-v1.json',contract);
const summary={schemaVersion:1,summaryId:'PHASE57_EXIT_V4_STAGE2_CAPACITY_ELIGIBILITY_SUMMARY_V1',asOfJst:'2026-09-10',basis:'METADATA_AND_PRE_OUTCOME_ESTIMATES_ONLY',pool:{discovered:fresh.discoveredSessionCount,eligible:eligible.length,blocked:blocked.length,diagnosticPriorExposure:oldInventory.length,protectedExternal:103,freshExternal:25},blockingReasonCounts:fresh.blockingReasonCounts,expectedFirstEnterPerSession:{conservative:2,base:2.9,optimistic:3.4},allocation:Object.fromEntries(Object.entries(split).map(([key,rows])=>[key,{...boundary(rows),expectedFirstEnter:capacity(rows.length)}])),devATarget200:{conservative:capacity(split.devA.length).conservative>=200,base:capacity(split.devA.length).base>=200,optimistic:capacity(split.devA.length).optimistic>=200},devBTarget500:{conservative:capacity(split.devA.length+split.devB.length).conservative>=500,base:capacity(split.devA.length+split.devB.length).base>=500,optimistic:capacity(split.devA.length+split.devB.length).optimistic>=500},finalGate:gate};
const summaryDigest=write('phase57-exit-v4-stage2-capacity-eligibility-summary-v1.json',summary);
const handoff={schemaVersion:1,handoffId:'PHASE57_EXIT_V4_STAGE2_DEV_A_HANDOFF_V1',status:'DEV_A_LOCKED_READY_FOR_SEPARATE_AUTHORIZATION',tier2ContractDigest:TIER2,allocationContractDigest:contractDigest,allocationManifestDigest:manifestDigest,sessionMetadataInventoryDigest:inventoryDigest,devASessions:split.devA.map(x=>x.sessionDate),devASessionsSha256:sha(split.devA.map(x=>x.sessionDate).join('\n')+'\n'),devAUnlockCandidate:true,developmentUnlocked:false,pairedEvaluatorRequired:true,pairedComparison:['FIXED_SESSION_END','EXIT_V3_FROZEN','EXIT_V4_FROZEN'],sameFrozenInputsRequired:true,explicitFutureAuthorizationRequired:true,prohibited:['DEVELOPMENT_OUTCOME_ACCESS_WITHOUT_AUTHORIZATION','VALIDATION_ACCESS','HISTORICAL_HOLDOUT_ACCESS','OOS_ACCESS','PROSPECTIVE_ACCESS'],safety:SAFETY};
const handoffDigest=write('phase57-exit-v4-stage2-dev-a-handoff-v1.json',handoff);
const audit={schemaVersion:1,auditId:'PHASE57_EXIT_V4_JQUANTS_STAGE2_FAST_ALLOCATION_FREEZE_V1',stage:'2_FAST_METADATA_INVENTORY_ALLOCATION_FREEZE',asOfJst:'2026-09-10',status:gate,pullRequest:581,draft:true,mainChanged:false,tier2Contract:{sha256:TIER2,modified:false},artifacts:{inventorySha256:inventoryDigest,allocationManifestSha256:manifestDigest,allocationContractSha256:contractDigest,capacitySummarySha256:summaryDigest,devAHandoffSha256:handoffDigest},pool:summary.pool,allocation:contract.allocation,accessLedger:inventory.accessLedger,hardStop:'ACTIVE',safety:SAFETY};
const auditDigest=write('phase57-exit-v4-jquants-stage2-fast-allocation-freeze-v1.json',audit);
const lines=[
  '# Phase57 EXIT v4 — Stage 2 Fast Metadata Inventory / Allocation Freeze','',
  `Final Gate: **${gate}**.`,'',
  'No EXIT outcome, future label, Protected content, or Fresh content was opened. The allocation is chronological and result-blind. Existing 179-session input metadata is retained as diagnostic prior-exposure lineage and is not reused for OOS or Future Reserve.','',
  '## Exact pool','',
  '| Class | Sessions |','|---|---:|',
  `| J-Quants sessions discovered | ${fresh.discoveredSessionCount} |`,`| Newly audited metadata-only | ${newInventory.length} |`,`| Eligible allocation pool | ${eligible.length} |`,`| Blocked | ${blocked.length} |`,`| Prior-exposure diagnostic | ${oldInventory.length} |`,`| Protected external | 103 |`,`| Fresh external | 25 |`,'',
  '## Frozen allocation','',
  '| Split | Sessions | First | Last | Expected First ENTER C/B/O |','|---|---:|---|---|---|',
  ...Object.entries(split).map(([key,rows])=>{const b=boundary(rows),c=capacity(rows.length);return `| ${key} | ${rows.length} | ${b.first??'—'} | ${b.last??'—'} | ${c.conservative} / ${c.base} / ${c.optimistic} |`; }),'',
  'Purge/embargo: **NONE** because Frozen Hybrid and MSH-Entry state are constructed anew per session; no cross-session state is carried.','',
  '## Frozen digests','',
  '| Artifact | SHA-256 |','|---|---|',`| Metadata inventory | \`${inventoryDigest}\` |`,`| Allocation manifest | \`${manifestDigest}\` |`,`| Allocation contract | \`${contractDigest}\` |`,`| Capacity summary | \`${summaryDigest}\` |`,`| DEV-A handoff | \`${handoffDigest}\` |`,`| Audit | \`${auditDigest}\` |`,'',
  '## Access and safety','',
  '| Item | Result |','|---|---:|','| EXIT outcomes | 0 |','| Future labels | 0 |','| Protected access | 0 |','| Fresh access | 0 |','| Raw persisted | 0 |','| Safety flags | ALL FALSE |','',
  '## Hard stop','',
  'DEV-A remains locked. Stage 3 requires a separate explicit authorization. Validation, Holdout, OOS, Prospective, merge, Ready, auto-merge, and promotion were not started.',''
];
fs.mkdirSync(path.dirname(DOC),{recursive:true});fs.writeFileSync(DOC,lines.join('\n'));
console.log(JSON.stringify({gate,eligible:eligible.length,blocked:blocked.length,counts:Object.fromEntries(Object.entries(split).map(([k,v])=>[k,v.length])),digests:{inventoryDigest,manifestDigest,contractDigest,summaryDigest,handoffDigest,auditDigest}},null,2));
