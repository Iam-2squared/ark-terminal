/**
 * Strict 2026 MarketSpeed II PRIVATE saved-source integration preflight.
 * Consumes *only* four private aggregate receipts: audit, chronological
 * replay, 5M proxy gap, price-only outcome split. No broker/Excel access.
 *
 * Real native integration is BLOCKED, never silently patched by source-only
 * price bars, fake L0 master/daily inputs, imputed Va, or future teachers.
 */
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {inspectNo11ProvisionalIntegrationPolicy} from
  './no11_provisional_shadow_integration.mjs';

export const NO11_SAVED_INTEGRATION_GATE_SCHEMA=
 'ARK_NO11_RSS_2026_SAVED_SOURCE_INTEGRATION_GATE_V1';
export const NO11_SAVED_RECEIPTS=Object.freeze({
 audit:Object.freeze({
   name:'rss-all-source-audit-04294e96395361e6.json',
   sha256:'04294e96395361e6f7030b68bd008135cbe296c588858d0e01e8023fe800f0a7'
 }),
 replay:Object.freeze({
   name:'no11-2026-replay-readiness-0385190d35d519dd.json',
   sha256:'0385190d35d519ddef0bc0107dc77c149170385d34a41a21491cfbb82b83cc60'
 }),
 selector:Object.freeze({
   name:'no11-2026-selector-source-gap-731a5095e605ad17.json',
   sha256:'731a5095e605ad17bf9b6e5f128ac912d6cd7dfe3cec5a3e38cdb4068ee75df8'
 }),
 prices:Object.freeze({
   name:'no11-2026-price-only-observability-380616e9c2d05eb4.json',
   sha256:'380616e9c2d05eb481b5ed160e35b92365822d770e23f9ed80d7295ac883c5e4'
 })
});
const DEFAULT_DAYS=[
 '2026-10-01','2026-10-02','2026-10-05','2026-10-06',
 '2026-10-07','2026-10-08','2026-10-09','2026-10-13'
];
const CLOCKS=['09:30','10:00','10:30','11:00','11:30',
 '13:00','13:30','14:00','14:30','15:00'];
const GAP_FEATURES=['segmentStandard','segmentGrowth','liquidityLow',
 'liquidityHigh','sectorBreadthPositivePct'];
const requireValue=(ok,code)=>{if(!ok)throw Error(code)};
const sha=b=>createHash('sha256').update(b).digest('hex');

function checkedReadonlyReport(root,key){
 const expected=NO11_SAVED_RECEIPTS[key];
 const file=path.join(root,expected.name),st=fs.lstatSync(file);
 requireValue(st.isFile()&&!st.isSymbolicLink()&&
   st.size>10&&st.size<300000,
   'NO11_INTEGRATION_UNSAFE_PRIVATE_REPORT_'+key);
 const raw=fs.readFileSync(file);
 requireValue(sha(raw)===expected.sha256,
   'NO11_INTEGRATION_PRIVATE_REPORT_SHA_CHANGED_'+key);
 const obj=JSON.parse(raw.toString('utf8').replace(/^\uFEFF/,''));
 requireValue(obj&&typeof obj==='object'&&!Array.isArray(obj),
   'NO11_INTEGRATION_PRIVATE_REPORT_NOT_OBJECT_'+key);
 return obj;
}
export function readNo11SavedIntegrationReports({privateRoot}={}){
 requireValue(typeof privateRoot==='string'&&path.isAbsolute(privateRoot),
   'NO11_INTEGRATION_PRIVATE_ROOT_ABSOLUTE_REQUIRED');
 const st=fs.lstatSync(privateRoot);
 requireValue(st.isDirectory()&&!st.isSymbolicLink(),
   'NO11_INTEGRATION_UNSAFE_PRIVATE_ROOT');
 return Object.freeze(Object.fromEntries(
   Object.keys(NO11_SAVED_RECEIPTS).map(k=>[
     k,checkedReadonlyReport(privateRoot,k)
   ])
 ));
}

export function inspectNo11SavedIntegrationReadiness({
 audit,replay,selector,prices
}={}){
 const training=inspectNo11ProvisionalIntegrationPolicy();
 requireValue(audit?.schemaId===
   'ARK_NO11_RSS_TRAINING_ALL_RUNS_SOURCE_AUDIT_V1'&&
   audit.result==='SOURCE_SHA256_AND_ROW_AUDIT_PASS_NOT_SUPERVISED_TRAINING'&&
   audit.symbolsRequested===4327&&audit.symbolsObserved===4071&&
   audit.symbolsUnavailable===256&&audit.dataRows===3705797&&
   audit.modelFitPerformed===false&&audit.productionReady===false&&
   audit.orderTransmission===false&&
   Array.isArray(audit.runs)&&audit.runs.length===3&&
   audit.runs.every(x=>x.fullSourceSha256Verified===true&&
     x.fullSourceOHLCVVerified===true),
   'NO11_INTEGRATION_AUDITED_RSS_SOURCE_NOT_CLEAN');
 requireValue(replay?.schemaId===
   'ARK_NO11_2026_RSS_CAUSAL_SOURCE_REPLAY_INDEX_V1'&&
   replay.sourceAuditSha256===NO11_SAVED_RECEIPTS.audit.sha256&&
   replay.sourceSymbols===4327&&replay.observedSymbols===4071&&
   replay.sourceRows===3705797&&replay.eightSessionObservedSymbols===3864&&
   replay.nativeSelectorRebuilt===false&&
   replay.nativeFirstEntryRebuilt===false&&
   replay.nativeState9FromRssCertified===false&&
   replay.historicalActualKnownAtCertified===false&&
   replay['2026SupervisedTrainingExamples']===0&&
   replay.productionReady===false&&replay.orderTransmission===false,
   'NO11_INTEGRATION_SOURCE_REPLAY_NOT_CAUSAL_CERTIFIED');
 requireValue(selector?.schemaId===
   'ARK_NO11_2026_RSS_FROZEN_SELECTOR_SOURCE_GAP_AUDIT_V1'&&
   selector.status==='RESEARCH_PRICE_SOURCE_PROXY_CREATED_NOT_NATIVE_SELECTOR'&&
   selector.scope==='all4327'&&
   selector.sourceAuditSha256===NO11_SAVED_RECEIPTS.audit.sha256&&
   selector.sourceReplayReportSha256===NO11_SAVED_RECEIPTS.replay.sha256&&
   selector.sourceIndexSha256===replay.sourceIndexSha256&&
   selector.frozenSelectorGitBlobSha===
     '6c707566eb074ce89656be1626bd5aed63d044a8'&&
   selector.symbolsInspected===4327&&
   selector.symbolsWithSourceBars===4071&&
   selector.oneMinuteSourceRows===3705797&&
   selector.completeProvisionalFiveMinuteRows===337023&&
   selector.nativeSelectorRun===false&&
   selector.nativeFirstEntryRun===false&&
   selector.nativeState9Run===false&&
   selector.frozenFiveMinuteAggregationParityCertified===false&&
   selector.historicalBarArrivalTimeCertified===false&&
   selector.originalPriorDailyEligibilityCertified===false&&
   selector.productionReady===false&&selector.orderTransmission===false&&
   Array.isArray(selector.nonPriceFrozenFeatureMetadataNotInRssCapture)&&
   GAP_FEATURES.every(f=>selector.nonPriceFrozenFeatureMetadataNotInRssCapture.includes(f)),
   'NO11_INTEGRATION_FROZEN_SELECTOR_RSS_INPUT_GAP_CHANGED');
 requireValue(prices?.schemaId===
   'ARK_NO11_RSS_2026_OBSERVED_PRICE_ONLY_OUTCOMES_V1'&&
   prices.status==='PRICE_ONLY_OBSERVED_FUTURE_NO_FROZEN_SELECTOR'&&
   prices.sourceReceiptSha256===NO11_SAVED_RECEIPTS.selector.sha256&&
   prices.source5mSha256===selector.fiveMinuteGzipSha256&&
   prices.source5mRows===337023&&
   prices.decisionPriceAnchors===59712&&
   prices.nativeSelectorExecuted===false&&
   prices.firstEntryExecuted===false&&
   prices.nativeState9Executed===false&&
   prices.new2026FrozenH235TrainingRows===0&&
   prices.modelFitPerformed===false&&
   prices.futureUnknownNeverConvertedToNegative===true&&
   prices.terminalAuctionsNotIncludedInHighLow===true&&
   prices.productionReady===false&&prices.orderTransmission===false,
   'NO11_INTEGRATION_PRICE_ONLY_OUTCOMES_NOT_RESEARCH');
 const anchors=selector.provisionalDecisionPriceAvailableSymbolsBySession;
 const points=prices.byDayDecision;
 requireValue(anchors&&points&&
   JSON.stringify(Object.keys(points).sort())===
   JSON.stringify([...DEFAULT_DAYS].sort())&&
   JSON.stringify(Object.keys(anchors).sort())===
   JSON.stringify([...DEFAULT_DAYS].sort()),
   'NO11_INTEGRATION_EIGHT_MARKET_SESSIONS_REQUIRED');
 let total=0,fullyObserved=0,hasFuture=0;
 let up5Observed=0,up5Unknown=0,down5Unknown=0;
 for(const day of DEFAULT_DAYS){
   requireValue(JSON.stringify(Object.keys(points[day]).sort())===
     JSON.stringify([...CLOCKS].sort())&&
     JSON.stringify(Object.keys(anchors[day]).sort())===
     JSON.stringify([...CLOCKS].sort()),
     'NO11_INTEGRATION_TEN_CLOCKS_REQUIRED');
   for(const clock of CLOCKS){
     const row=points[day][clock],n=anchors[day][clock];
     requireValue(Number.isInteger(n)&&n>=0&&n<=4071&&
       row&&row.priceAnchors===n&&
       Number.isInteger(row.fullFutureWindow)&&
       Number.isInteger(row.withFutureObserved)&&
       row.fullFutureWindow>=0&&
       row.withFutureObserved>=row.fullFutureWindow&&
       row.withFutureObserved<=n&&
       Number.isInteger(row.highTouch5Observed)&&
       Number.isInteger(row.highTouch5Unknown)&&
       Number.isInteger(row.lowTouch5Unknown)&&
       row.highTouch5Observed>=0&&
       row.highTouch5Unknown>=0&&
       row.lowTouch5Unknown>=0&&
       row.highTouch5Observed+row.highTouch5Unknown<=n&&
       row.highTouch5Unknown<=n-row.fullFutureWindow&&
       row.lowTouch5Unknown<=n-row.fullFutureWindow,
       'NO11_INTEGRATION_PRICE_CLOCK_SOURCE_PARITY_FAILED');
     total+=n;fullyObserved+=row.fullFutureWindow;
     hasFuture+=row.withFutureObserved;
     up5Observed+=row.highTouch5Observed;
     up5Unknown+=row.highTouch5Unknown;
     down5Unknown+=row.lowTouch5Unknown;
   }
 }
 requireValue(total===59712&&fullyObserved===17251&&
   hasFuture===58652&&up5Observed===756&&up5Unknown===41888&&
   down5Unknown===41962,
   'NO11_INTEGRATION_EIGHTY_CLOCK_PHYSICAL_REPORT_CHANGED');
 return Object.freeze({
   schemaId:NO11_SAVED_INTEGRATION_GATE_SCHEMA,
   status:'AUDITED_2026_RSS_SOURCE_READY_NATIVE_SELECTOR_AND_E2E_BLOCKED',
   provisionalTraining:training.status,
   source:Object.freeze({
     symbolsRequested:4327,symbolsObserved:4071,
     oneMinuteBars:3705797,completeResearchFiveMinuteBars:337023,
     fixedClockPriceAnchors:total,
     completeFutureObserved:fullyObserved,
     futureFullyObservedPct:Number((100*fullyObserved/total).toFixed(4)),
     observedHigh5:up5Observed,unknownHigh5:up5Unknown,
     unknownLow5:down5Unknown,
     historicalBrokerKnownAtCertified:false
   }),
   stages:Object.freeze({
     Selector:'BLOCKED_NATIVE_L0_DAILY_MASTER_ADMISSION_AND_VA_TURNOVER_PARITY',
     FirstEntry:'BLOCKED_NO_NATIVE_FROZEN_SELECTOR_EVENT',
     State9:'BLOCKED_NO_NATIVE_NORMALIZATION_AND_PATH_SOURCE_PARITY',
     H235:'2025_PROVISIONAL_TRAINED_NOT_APPLIED_TO_2026_REAL_ENTRY',
     Capital:'SYNTHETIC_MAX3_TESTED_NATIVE_V5_SAB_NOT_CONNECTED',
     EXIT:'SYNTHETIC_SHARP_DROP_TESTED_ORIGINAL_STRUCTURAL_EXIT_NOT_CONNECTED'
   }),
   safety:Object.freeze({
     new2026SupervisedTrainingRows:0,
     originalFrozenModelReplacement:false,
     orderTransmission:false,productionReady:false,
     nativeEndToEndCertified:false,mainMerge:false
   })
 });
}
