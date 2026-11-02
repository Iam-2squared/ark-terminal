import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import zlib from 'node:zlib';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {
 GRID,FROZEN_ENTRY_BLOB,gitBlob,sha256,
 checkFrozenP1Contract,checkStage3Report,checkAsOfRow,checkPrivateAsOfArchive
} from '../runtime/no11_first_entry_p1_asof_gate.mjs';

const DAY='2026-10-13',c=n=>String(Math.floor(n/60)).padStart(2,'0')+':'+String(n%60).padStart(2,'0');
const contract=path.resolve('research/persistent-watchlist-uptrend-first-entry-20261003-v2/CORRECTED_LINEAGE_FAST_FREEZE_20261003/P1_Q70_ENTRY_CONTRACT.json');
const stage4=path.resolve('research/no12-prebuy-causal-runtime-20261011/tools/no11_2026_first_entry_p1_source_gate.mjs');
const symbols=Array.from({length:4327},(_,i)=>String(1000+i).padStart(4,'0')+'.T');
function fixture(){
 const records=[];
 for(let sym=0;sym<2;sym++){
  for(let i=0;i<GRID.length;i++){
   const clock=c(GRID[i]),missing=i===5;
   const label=missing?null:DAY+'T'+clock+':00+09:00';
   const observed=!missing&&i%10===0;
   records.push({
    schemaId:'ARK_NO11_2026_RSS_RC2_TECHNICAL_ASOF_STATE_V1',
    scheduledClock:clock,sourceLabel:label,
    researchAssumedBarEnd:label?new Date(Date.parse(label)+60000).toISOString():null,
    originalNumericStatus:missing?'NOT_AVAILABLE':'ACCEPTED',
    state9CurrentObserved:observed,formalPrimary:observed?'RISE':null,
    basis:observed?'OBSERVED_FRESH':null,
    directionBasis:observed?'CLOSE':null,
    activity:observed?'ACTIVE':null,
    originalSource:missing?null:'RSS_CHART_VALUE2_RESEARCH_ONLY_NOT_JQUANTS_V2',
    missingSourceBar:missing,actualBrokerKnownAtCertified:false,
    firstEntryP1NativeFeatureRowCertified:false,
    eligibleForNativeSelectorOrFirstEntry:false,futureOutcomeIncluded:false,
    productionReady:false,orderTransmission:false,
    symbol:symbols[sym],session:DAY,
    sourceArchiveSha256:(sym?'b':'a').repeat(64)
   });
  }
 }
 const observed=records.filter(r=>r.state9CurrentObserved).length;
 const zipped=zlib.gzipSync(Buffer.from(records.map(r=>JSON.stringify(r)).join('\n')+'\n'));
 const digest=sha256(zipped);
 const report={
  schemaId:'ARK_NO11_2026_RSS_ORIGINAL_RC2_SPARSE_MISSING_REPLAY_V1',
  status:'TECHNICAL_SPARSE_DUAL_ENGINE_PASS_RESEARCH_ONLY',
  previous:'2026-10-09',current:DAY,inspectedOriginalFirstSymbols:950,
  actualReplayedOriginalFirstEligibleCount:2,
  sourceCoverageCounters:{sourceInspected:950,replayedPairs:2,
    meetsSourceAnchorAndCurrentFloor:244},
  eligibleSourcePairsInFixedScope:244,eligibleNotReplayed:242,
  fullEligibleSetTechnicalReplayed:false,
  researchTechnicalTickCounts:{
   totalOriginalDualEngineTickAgreements:654,nativeAcceptedTicks:652,
   nativeMissingTickCalls:2,nativeObservedStateTicks:observed
  },
  privateState9AsOfEventRows:654,state9AsOfExportIsResearchOnly:true,
  privateState9AsOfGzipFilename:'no11-2026-state9-asof-research-'+digest.slice(0,16)+'.jsonl.gz',
  privateState9AsOfGzipSha256:digest,
  inputSourceIndexSha256:'4828a387aca426b9692fafa2322aea5384da41a1b0be69b98ace7b74fd8b86e0',
  originalSourceAuditSha256:'04294e96395361e6f7030b68bd008135cbe296c588858d0e01e8023fe800f0a7',
  baseline950ReportSha256:'2e79d4f530ed492bf8c82a1df63b641ba1b3ab5c6ab4608c6a9b9c3adefbd5bc',
  missingTickSemantics:'ORIGINAL_RC2_STEP_NONE_NOT_FORWARD_FILL',
  originalNativeRC2BothEnginesInvoked:true,brokerKnownAtIsInferredNotObserved:true,
  stateLabelsEligibleForLiveSelectorOrEntry:false,
  futureObservedOutcomeUsedInModelInputs:false,
  h235R0OnReal2026Candidate:false,trainingPerformed:false,
  originalFrozenFilesMutated:false,productionReady:false,
  orderTransmission:false,technicalErrorCounts:{},
  observedOriginalPrimaryStates:{RISE:observed}
 };
 return {records,zipped,report,observed};
}

test('Frozen First Entry P1_Q70 original contract is pinned, not a substitute H235 or score',()=>{
 const raw=fs.readFileSync(contract);
 assert.equal(gitBlob(raw),FROZEN_ENTRY_BLOB);
 const result=checkFrozenP1Contract(JSON.parse(raw));
 assert.equal(result.p1Numeric,148);
 assert.equal(result.p1Categorical,15);
 assert.equal(result.privateModelArtifactsVerified,false);
 assert.equal(result.originalP1ModelExecuted,false);
 const modified=JSON.parse(raw);modified.feature_manifest.P1_numeric.pop();
 assert.throws(()=>checkFrozenP1Contract(modified),/FROZEN_CONTRACT_CHANGED/);
});

test('Synthetic 2-symbol private State9 as-of 654 ticks verify original clock, missing and state totals',async()=>{
 const {records,zipped,report,observed}=fixture();
 assert.equal(checkStage3Report(report),2);
 const tmp=fs.mkdtempSync(path.join(os.tmpdir(),'no11-p1-stage4-'));
 try{
  const file=path.join(tmp,report.privateState9AsOfGzipFilename);
  fs.writeFileSync(file,zipped);
  const summary=await checkPrivateAsOfArchive({report,archive:file,masterOrder:symbols});
  assert.equal(summary.state9ResearchSymbols,2);
  assert.equal(summary.scheduledState9Ticks,654);
  assert.equal(summary.acceptedSource1m,652);
  assert.equal(summary.explicitlyMissingSource1m,2);
  assert.equal(summary.observedState9PrimaryTicks,observed);
  const changed={...records[5],formalPrimary:'RISE'};
  assert.throws(()=>checkAsOfRow(changed),/MISSING_BAR_FILLED/);
  const unsafe={...records[0],actualBrokerKnownAtCertified:true};
  assert.throws(()=>checkAsOfRow(unsafe),/UNSAFE_ASOF_ROW/);
  const future={...records[0],futureOutcomeIncluded:true};
  assert.throws(()=>checkAsOfRow(future),/UNSAFE_ASOF_ROW/);
  const stale={...records[1],formalPrimary:'RISE'};
  assert.throws(()=>checkAsOfRow(stale),/STALE_OR_MISSING_STATE/);
  const bad={...report,privateState9AsOfGzipSha256:'0'.repeat(64)};
  await assert.rejects(()=>checkPrivateAsOfArchive({report:bad,archive:file,masterOrder:symbols}),
    /PRIVATE_GZIP_HASH_CHANGED|STAGE3_RECEIPT_NOT_VERIFIED/);
  const swapped=records.slice();
  [swapped[0],swapped[1]]=[swapped[1],swapped[0]];
  const swappedGzip=zlib.gzipSync(Buffer.from(swapped.map(r=>JSON.stringify(r)).join('\n')+'\n'));
  const swappedHash=sha256(swappedGzip);
  const reordered={...report,privateState9AsOfGzipSha256:swappedHash,
    privateState9AsOfGzipFilename:'no11-2026-state9-asof-research-'+swappedHash.slice(0,16)+'.jsonl.gz'};
  const swappedFile=path.join(tmp,reordered.privateState9AsOfGzipFilename);
  fs.writeFileSync(swappedFile,swappedGzip);
  await assert.rejects(()=>checkPrivateAsOfArchive({
    report:reordered,archive:swappedFile,masterOrder:symbols
  }),/ASOF_CLOCK_ORDER_CHANGED/);
 }finally{fs.rmSync(tmp,{recursive:true,force:true});}
});

test('Native P1 gate refuses missing original private evidence, never sends orders or fabricates models',()=>{
 const p=spawnSync(process.execPath,[fileURLToPath(new URL('../tools/no11_2026_first_entry_p1_source_gate.mjs',import.meta.url))],{
  encoding:'utf8',timeout:15000
 });
 assert.equal(p.status,2,p.stderr||p.stdout);
 assert.match(p.stderr,/NO11_FIRST_ENTRY_P1_STAGE4=BLOCKED/);
 assert.match(p.stderr,/ORDER_TRANSMISSION=False/);
 const code=fs.readFileSync(stage4,'utf8')+
   fs.readFileSync(new URL('../runtime/no11_first_entry_p1_asof_gate.mjs',import.meta.url),'utf8');
 for(const forbidden of [/RssStockOrder/,/RssCancelOrder/,/Excel.Application/,
  /node:net/,/node:http/,/fetch\s*\(/,/productionReady\s*:\s*true/,
  /orderTransmission\s*:\s*true/])assert.doesNotMatch(code,forbidden);
});
