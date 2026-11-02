/**
 * Explicit SYNTHETIC-ONLY bridge to the ORIGINAL audited Frozen Capital v5
 * Python allocator and S/A/B slot reservation. Not No.1.1 native execution:
 * ranked candidates and training arrival statistics are fabricated test
 * inputs, NOT inferred from 2025 provisional H2/H3/H5 or 2026 RSS.
 */
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';

const EXECUTABLE=new URL(
  '../tools/no11_capital_v5_crlf_safe_synthetic.py',import.meta.url);
const FREEZE='10c94c92c4bd2a59a22744667fd0210252602df4';
const AUTHORITY='710656491be06235901b45c50a8b5cbd714ba4eb';
const bad=s=>{throw Error(s)};
const checked=(ok,s)=>{if(!ok)bad(s)};
const SYM=s=>String(s).endsWith('.T')?String(s):String(s)+'.T';

export function runNo11SyntheticOriginalCapitalV5({
 mode,request,rankedCandidates,startingCashYen,pythonExecutable=null
}={}){
 checked(mode==='SYNTHETIC_OFFLINE_ONLY',
   'NO11_CAPITAL_V5_LIVE_OR_BROKER_EXECUTION_FORBIDDEN');
 checked(request?.schemaId==='ARK_NO11_FROZEN_V5_SYNTHETIC_BRIDGE_V1'&&
   request.evidenceMode==='SYNTHETIC_OFFLINE_ONLY'&&
   request.strategyFreezeCommit===FREEZE&&
   request.capitalAuthorityCommit===AUTHORITY&&
   request.researchInputProvenance==='EXPLICIT_SYNTHETIC_NOT_H235_RANK'&&
   request.afterFirstLegalSellFill===false&&
   request.pendingBrokerOrders===false&&
   request.sessionVerified===false&&
   request.productionReady===false&&request.orderTransmission===false&&
   request.arkManagedSymbols?.length===0&&
   request.existingBands?.length===0&&
   request.arkCapitalInputs?.exposure===0&&
   request.arkCapitalInputs?.equity===startingCashYen&&
   request.arkCapitalInputs?.cash===startingCashYen&&
   Number.isSafeInteger(startingCashYen)&&startingCashYen>0&&
   request.preorderedCandidates?.length>0&&
   request.preorderedCandidates.length<=20&&
   typeof request.syntheticTrainingTables==='object'&&
   Array.isArray(rankedCandidates),
   'NO11_CAPITAL_V5_SYNTHETIC_SOURCE_CONTRACT_INVALID');
 const eligible=new Map(rankedCandidates.map(x=>[x.entryId,x]));
 checked(eligible.size===rankedCandidates.length,
   'NO11_CAPITAL_V5_DUPLICATED_RANKED_ID');
 const sourceById=new Map();
 for(const row of request.preorderedCandidates){
   checked(row&&typeof row==='object'&&!Array.isArray(row)&&
     eligible.has(row.entry_id)&&!sourceById.has(row.entry_id)&&
     SYM(row.brokerSymbol)===eligible.get(row.entry_id).symbol&&
     String(row.raw_reference)===
        String(eligible.get(row.entry_id).syntheticReferencePrice)&&
     typeof row.ML==='number'&&Number.isFinite(row.ML)&&
     typeof row.capital_score==='number'&&Number.isFinite(row.capital_score),
     'NO11_CAPITAL_V5_UNBOUND_OR_INCONSISTENT_PREBUY_RANK');
   sourceById.set(row.entry_id,row);
 }
 checked(pythonExecutable===null||
   (typeof pythonExecutable==='string'&&
    /^[A-Za-z0-9._:-]{2,32}$/.test(pythonExecutable)),
   'NO11_CAPITAL_V5_PYTHON_EXECUTABLE_UNSAFE');
 // User Windows machines commonly have only the py -3.12 launcher; CI
 // machines may instead expose python. No shell and no arbitrary commands.
 const choices=pythonExecutable!==null
   ? [{exe:pythonExecutable,base:['-B']}]
   : process.platform==='win32'
     ? [{exe:'py',base:['-3.12','-B']},{exe:'python',base:['-B']}]
     : [{exe:'python3',base:['-B']},{exe:'python',base:['-B']}];
 let run=null,output=null;
 for(const choice of choices){
   run=spawnSync(choice.exe,[...choice.base,fileURLToPath(EXECUTABLE)],{
     input:JSON.stringify(request)+'\n',encoding:'utf8',
     timeout:30000,maxBuffer:1024*1024,windowsHide:true
   });
   try{output=JSON.parse(run.stdout);}catch{output=null;}
   if(output?.status==='BLOCKED')break; // real fail-closed result; no fallback
   if(run.status===0&&
      output?.schemaId==='ARK_NO11_FROZEN_CAPITAL_V5_OFFLINE_RESULT_V1')
     break;
 }
 if(run?.status!==0){
   // The frozen synthetic bridge emits a bounded code, never private values.
   let reason='UNKNOWN';
   if(output?.status==='BLOCKED'&&typeof output.reason==='string'&&
      /^[A-Z][A-Z0-9_]{2,100}$/.test(output.reason))
     reason=output.reason;
   bad('NO11_CAPITAL_V5_ORIGINAL_PYTHON_GATE_FAILED:'+reason);
 }
 checked(output&&typeof output==='object',
   'NO11_CAPITAL_V5_PYTHON_RESULT_NOT_JSON');
 checked(output?.schemaId==='ARK_NO11_FROZEN_CAPITAL_V5_OFFLINE_RESULT_V1'&&
   output.status==='SYNTHETIC_SHADOW_ONLY'&&
   output.strategyFreezeCommit===FREEZE&&
   output.capitalAuthorityCommit===AUTHORITY&&
   output.liveFeedTimestampCertified===false&&
   output.frozenEntryCertified===false&&
   output.orderAllowed===false&&
   output.rssOrderFunctionAllowed===false&&
   output.transmitted===false&&
   output.productionReady===false&&
   output.inputCashJpy===String(startingCashYen)&&
   Array.isArray(output.allocations)&&
   output.allocations.length<=3,
   'NO11_CAPITAL_V5_ORIGINAL_PYTHON_RESULT_UNSAFE');
 const funded=new Map();
 for(const a of output.allocations){
   checked(sourceById.has(a.entry_id)&&
     a.quantity>=0&&Number.isSafeInteger(a.quantity)&&
     a.quantity%100===0&&
     a.band===sourceById.get(a.entry_id).rank&&
     !funded.has(a.entry_id),
     'NO11_CAPITAL_V5_ALLOCATION_ID_OR_BAND_MISMATCH');
   if(a.quantity>0){
     checked(eligible.get(a.entry_id).quantity===a.quantity,
       'NO11_CAPITAL_V5_CASH_LIFECYCLE_QUANTITY_PARITY_REQUIRED');
     funded.set(a.entry_id,a.quantity);
   }
 }
 checked(output.fundedCount===funded.size&&
   output.admittedCount===output.allocations.length,
   'NO11_CAPITAL_V5_MODEL_FUNDING_COUNT_MISMATCH');
 return Object.freeze({
   schemaId:'ARK_NO11_ORIGINAL_V5_PYTHON_SYNTHETIC_STAGE_V1',
   status:'ORIGINAL_FROZEN_V5_PYTHON_SAB_COMPUTED_ON_EXPLICIT_SYNTHETIC_INPUT',
   fundedCount:funded.size,
   fundedEntries:Object.freeze([...funded.entries()].map(([entryId,quantity])=>
     Object.freeze({entryId,quantity}))),
   allocatedDebitJpy:output.allocatedDebitJpy,
   remainingBuyingPowerJpy:output.remainingBuyingPowerJpy,
   originalFrozenCapitalV5PythonExecutedOnSynthetic:true,
   nativeLiveFrozenCapitalV5Executed:false,
   originalFrozenR0H235Executed:false,
   hasBrokerCashProof:false,
   orderTransmission:false,productionReady:false
 });
}
