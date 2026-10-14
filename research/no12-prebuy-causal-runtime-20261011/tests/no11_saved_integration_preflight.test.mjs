import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {
 inspectNo11SavedIntegrationReadiness,NO11_SAVED_RECEIPTS
} from '../runtime/no11_saved_integration_preflight.mjs';

const DAYS=['2026-10-01','2026-10-02','2026-10-05','2026-10-06',
 '2026-10-07','2026-10-08','2026-10-09','2026-10-13'];
const CLOCKS=['09:30','10:00','10:30','11:00','11:30',
 '13:00','13:30','14:00','14:30','15:00'];
const spread=(n,i)=>Math.floor(n/80)+(i<n%80?1:0);

function fixture(){
 const audit={
   schemaId:'ARK_NO11_RSS_TRAINING_ALL_RUNS_SOURCE_AUDIT_V1',
   result:'SOURCE_SHA256_AND_ROW_AUDIT_PASS_NOT_SUPERVISED_TRAINING',
   symbolsRequested:4327,symbolsObserved:4071,symbolsUnavailable:256,
   dataRows:3705797,modelFitPerformed:false,
   productionReady:false,orderTransmission:false,
   runs:[1,2,3].map(()=>({
     fullSourceSha256Verified:true,fullSourceOHLCVVerified:true
   }))
 };
 const replay={
   schemaId:'ARK_NO11_2026_RSS_CAUSAL_SOURCE_REPLAY_INDEX_V1',
   sourceAuditSha256:NO11_SAVED_RECEIPTS.audit.sha256,
   sourceSymbols:4327,observedSymbols:4071,sourceRows:3705797,
   sourceIndexSha256:'c'.repeat(64),
   eightSessionObservedSymbols:3864,
   nativeSelectorRebuilt:false,nativeFirstEntryRebuilt:false,
   nativeState9FromRssCertified:false,
   historicalActualKnownAtCertified:false,
   '2026SupervisedTrainingExamples':0,
   productionReady:false,orderTransmission:false
 };
 const selector={
   schemaId:'ARK_NO11_2026_RSS_FROZEN_SELECTOR_SOURCE_GAP_AUDIT_V1',
   status:'RESEARCH_PRICE_SOURCE_PROXY_CREATED_NOT_NATIVE_SELECTOR',
   scope:'all4327',sourceAuditSha256:NO11_SAVED_RECEIPTS.audit.sha256,
   sourceReplayReportSha256:NO11_SAVED_RECEIPTS.replay.sha256,
   sourceIndexSha256:replay.sourceIndexSha256,
   frozenSelectorGitBlobSha:'6c707566eb074ce89656be1626bd5aed63d044a8',
   symbolsInspected:4327,symbolsWithSourceBars:4071,
   oneMinuteSourceRows:3705797,completeProvisionalFiveMinuteRows:337023,
   fiveMinuteGzipSha256:'63389666d55a2cb4c21d9f9ba2fb8fbae2a92cdf3044d2b949798c66997d1f74',
   nativeSelectorRun:false,nativeFirstEntryRun:false,nativeState9Run:false,
   frozenFiveMinuteAggregationParityCertified:false,
   historicalBarArrivalTimeCertified:false,
   originalPriorDailyEligibilityCertified:false,
   productionReady:false,orderTransmission:false,
   nonPriceFrozenFeatureMetadataNotInRssCapture:[
     'segmentStandard','segmentGrowth','liquidityLow','liquidityHigh',
     'sectorBreadthPositivePct'
   ],
   provisionalDecisionPriceAvailableSymbolsBySession:{}
 };
 const prices={
   schemaId:'ARK_NO11_RSS_2026_OBSERVED_PRICE_ONLY_OUTCOMES_V1',
   status:'PRICE_ONLY_OBSERVED_FUTURE_NO_FROZEN_SELECTOR',
   sourceReceiptSha256:NO11_SAVED_RECEIPTS.selector.sha256,
   source5mSha256:selector.fiveMinuteGzipSha256,source5mRows:337023,
   decisionPriceAnchors:59712,
   nativeSelectorExecuted:false,firstEntryExecuted:false,
   nativeState9Executed:false,new2026FrozenH235TrainingRows:0,
   modelFitPerformed:false,futureUnknownNeverConvertedToNegative:true,
   terminalAuctionsNotIncludedInHighLow:true,
   productionReady:false,orderTransmission:false,
   byDayDecision:{}
 };
 let i=0;
 for(const day of DAYS){
   const ca={},cb={};
   for(const clock of CLOCKS){
     const n=spread(59712,i);
     ca[clock]=n;
     cb[clock]={
       priceAnchors:n,
       fullFutureWindow:spread(17251,i),
       withFutureObserved:spread(58652,i),
       highTouch5Observed:spread(756,i),
       highTouch5Unknown:spread(41888,i),
       lowTouch5Unknown:spread(41962,i)
     };
     i++;
   }
   selector.provisionalDecisionPriceAvailableSymbolsBySession[day]=ca;
   prices.byDayDecision[day]=cb;
 }
 return {audit,replay,selector,prices};
}

test('2025 provisional gate joins all four 2026 private source receipts without inventing native signals',()=>{
 const r=inspectNo11SavedIntegrationReadiness(fixture());
 assert.equal(r.source.fixedClockPriceAnchors,59712);
 assert.equal(r.source.completeFutureObserved,17251);
 assert.equal(r.source.observedHigh5,756);
 assert.equal(r.source.unknownHigh5,41888);
 assert.equal(r.source.unknownLow5,41962);
 assert.equal(r.stages.H235,'2025_PROVISIONAL_TRAINED_NOT_APPLIED_TO_2026_REAL_ENTRY');
 assert.equal(r.stages.Selector,'BLOCKED_NATIVE_L0_DAILY_MASTER_ADMISSION_AND_VA_TURNOVER_PARITY');
 assert.equal(r.safety.new2026SupervisedTrainingRows,0);
 assert.equal(r.safety.nativeEndToEndCertified,false);
 assert.equal(r.safety.orderTransmission,false);
});

test('native Frozen claims, chronological discrepancy and a future unknown changed to false negative fail closed',()=>{
 const x=fixture();x.selector.nativeSelectorRun=true;
 assert.throws(()=>inspectNo11SavedIntegrationReadiness(x),
   /SELECTOR_RSS_INPUT_GAP_CHANGED/);
 const y=fixture();y.prices.byDayDecision[DAYS[0]][CLOCKS[0]].priceAnchors-=1;
 assert.throws(()=>inspectNo11SavedIntegrationReadiness(y),
   /PRICE_CLOCK_SOURCE_PARITY_FAILED/);
 const z=fixture();z.prices.byDayDecision[DAYS[0]][CLOCKS[0]].highTouch5Unknown+=50;
 assert.throws(()=>inspectNo11SavedIntegrationReadiness(z),
   /PRICE_CLOCK_SOURCE_PARITY_FAILED/);
 const a=fixture();a.prices.modelFitPerformed=true;
 assert.throws(()=>inspectNo11SavedIntegrationReadiness(a),
   /PRICE_ONLY_OUTCOMES_NOT_RESEARCH/);
 const b=fixture();b.replay.historicalActualKnownAtCertified=true;
 assert.throws(()=>inspectNo11SavedIntegrationReadiness(b),
   /SOURCE_REPLAY_NOT_CAUSAL_CERTIFIED/);
});

test('offline gate CLI refuses absent private root and never imports broker/network/Excel APIs',()=>{
 const script=new URL('../tools/no11_saved_integration_preflight.mjs',import.meta.url);
 const proc=spawnSync(process.execPath,[fileURLToPath(script),
   '--private-root','/nonexistent-ark-provisional-shadow'],{
    encoding:'utf8',timeout:10000
   });
 assert.equal(proc.status,2);
 assert.match(proc.stderr,/NO11_PROVISIONAL_INTEGRATION_READONLY_PREFLIGHT=BLOCKED/);
 assert.match(proc.stderr,/ORDER_TRANSMISSION=False/);
 const sources=[
  fs.readFileSync(script,'utf8'),
  fs.readFileSync(new URL('../runtime/no11_saved_integration_preflight.mjs',import.meta.url),'utf8')
 ].join('\n');
 for(const p of [/RssStockOrder\s*\(/,/RssCancelOrder\s*\(/,
   /Excel\.Application/,/\bfetch\s*\(/,/node:net/,/node:http/,
   /productionReady\s*:\s*true/,/orderTransmission\s*:\s*true/])
   assert.doesNotMatch(sources,p);
});
