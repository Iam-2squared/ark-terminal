import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import {
  PHASE57_LONG_ONLY_RESEARCH_CONTRACT,PHASE57_LONG_ONLY_SAFETY,
  assertLongOnlyOrderIntent,validatePartitionManifest,
} from '../long-only/phase57-long-only-research-contract.js';
import {buildLongOnlyL0OpportunityCensus} from '../long-only/phase57-long-only-l0-opportunity-census.js';
import {
  assertReleasedPartition,assertReserveReplacement,evaluateLongOnlyAcquisitionGate,
  REQUIRED_PHASE57_LONG_ONLY_ACQUISITION_GATES,
} from '../long-only/phase57-long-only-acquisition-gate.js';

test('LONG-only contract prohibits every credit, short and leverage path',()=>{
  assert.equal(PHASE57_LONG_ONLY_RESEARCH_CONTRACT.longOnly,true);
  assert.equal(PHASE57_LONG_ONLY_RESEARCH_CONTRACT.accountType,'CASH_EQUITY');
  for(const key of ['marginBuyAllowed','shortSellAllowed','marginSellAllowed','shortEntryAllowed','shortPositionAllowed','leverageAllowed'])assert.equal(PHASE57_LONG_ONLY_RESEARCH_CONTRACT[key],false);
  for(const key of ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed'])assert.equal(PHASE57_LONG_ONLY_SAFETY[key],false);
});

test('cash and lot constraints reject impossible or short intents',()=>{
  assert.equal(assertLongOnlyOrderIntent({side:'LONG',accountType:'CASH_EQUITY',quantity:200,price:1000},{availableCashJpy:200000}),true);
  assert.throws(()=>assertLongOnlyOrderIntent({side:'SHORT',accountType:'CASH_EQUITY',quantity:100,price:1000},{availableCashJpy:200000}),/prohibited/);
  assert.throws(()=>assertLongOnlyOrderIntent({side:'LONG',accountType:'MARGIN',quantity:100,price:1000},{availableCashJpy:200000}),/CASH_EQUITY/);
  assert.throws(()=>assertLongOnlyOrderIntent({side:'LONG',accountType:'CASH_EQUITY',quantity:150,price:1000},{availableCashJpy:200000}),/lot size/);
  assert.throws(()=>assertLongOnlyOrderIntent({side:'LONG',accountType:'CASH_EQUITY',quantity:300,price:1000},{availableCashJpy:200000}),/available cash/);
});

test('initial partition manifest is disjoint and keeps non-development outcomes sealed',()=>{
  const manifest=validatePartitionManifest({
    DEVELOPMENT:{sessions:['2024-01-04','2024-01-05'],opened:true},
    VALIDATION:{sessions:['2024-01-09'],opened:false},
    UNTOUCHED_OOS:{sessions:['2024-01-10'],opened:false},
    FINAL_CONFIRMATION_FRESH:{sessions:['2024-01-11'],opened:false},
  });
  assert.match(manifest.manifestSha256,/^[a-f0-9]{64}$/);
  assert.throws(()=>validatePartitionManifest({DEVELOPMENT:{sessions:['2024-01-04'],opened:true},VALIDATION:{sessions:['2024-01-04'],opened:false}}),/overlap/);
  assert.throws(()=>validatePartitionManifest({DEVELOPMENT:{sessions:['2024-01-04'],opened:true},UNTOUCHED_OOS:{sessions:['2024-01-10'],opened:true}}),/must remain unopened/);
});

test('L0 census calculates exact market and segment distributions from development rows',()=>{
  const rows=[
    ['2024-01-04','1111','PRIME',104,100],['2024-01-04','2222','STANDARD',106,100],['2024-01-04','3333','GROWTH',111,100],
    ['2024-01-05','1111','PRIME',102,100],['2024-01-05','2222','STANDARD',105,100],['2024-01-05','3333','GROWTH',90,100],
  ].map(([sessionDate,symbol,segment,adjustedClose,adjustedPreviousClose])=>({sessionDate,symbol,segment,adjustedClose,adjustedPreviousClose,listingMembershipPointInTime:true}));
  const result=buildLongOnlyL0OpportunityCensus({rows,sourceManifest:{sourceIdentity:'FIXTURE',sourceSha256:'a'.repeat(64),timestampContract:'JPX_OFFICIAL_SESSION_DATE_V1'}});
  assert.equal(result.overall.gte3Pct.summary.mean,2);
  assert.equal(result.overall.gte5Pct.summary.mean,1.5);
  assert.equal(result.overall.gte10Pct.summary.mean,.5);
  assert.equal(result.bySegment.GROWTH.gte10Pct.summary.mean,.5);
  assert.equal(result.methodology.untouchedOosConsumed,false);
});

test('L0 fails closed on missing point-in-time membership, duplicates or sealed partitions',()=>{
  const base={sessionDate:'2024-01-04',symbol:'1111',segment:'PRIME',adjustedClose:104,adjustedPreviousClose:100,listingMembershipPointInTime:true};
  const sourceManifest={sourceIdentity:'FIXTURE',sourceSha256:'a'.repeat(64),timestampContract:'JPX_OFFICIAL_SESSION_DATE_V1'};
  assert.throws(()=>buildLongOnlyL0OpportunityCensus({rows:[{...base,listingMembershipPointInTime:false}],sourceManifest}),/point-in-time/);
  assert.throws(()=>buildLongOnlyL0OpportunityCensus({rows:[base,base],sourceManifest}),/duplicate/);
  assert.throws(()=>buildLongOnlyL0OpportunityCensus({rows:[base],partition:'UNTOUCHED_OOS',sourceManifest}),/DEVELOPMENT only/);
});

test('reviewed data plan conserves all 205 clean sessions and reserves 15 for admission failures',()=>{
  const plan=JSON.parse(fs.readFileSync(new URL('../long-only/phase57-long-only-data-plan.json',import.meta.url),'utf8'));
  assert.equal(plan.schemaVersion,3);
  assert.equal(plan.newJquantsAcquisitionAuthorized,false);
  assert.equal(plan.currentEntitlementEvidence.basePlan,'LIGHT');
  assert.equal(plan.currentEntitlementEvidence.minuteAddon,'TICK_PLUS_OHLCMIN');
  assert.equal(plan.currentEntitlementEvidence.basePlanActive,true);
  assert.equal(plan.currentEntitlementEvidence.minuteAddonActive,true);
  assert.equal(plan.l0Contract.intradayDataRequired,false);
  assert.equal(plan.datasetSplit.development.totalSessions,80);
  assert.deepEqual(Object.values(plan.datasetSplit.development.blocks).map(block=>block.sessions),[25,15,20,20]);
  assert.equal(plan.datasetSplit.reserve.sessions,15);
  assert.equal(plan.partitionAccounting.sum,205);
  assert.equal(plan.partitionAccounting.sum,plan.datasetSplit.totalCleanHistoricalSessions);
  assert.equal(plan.datasetSplit.development.integratedReuseRequired,true);
  assert.equal(plan.datasetSplit.development.selectorOnlyConsumptionProhibited,true);
  assert.equal(plan.integratedResearchDataset.entryExitAllocationReuseRequired,true);
  assert.equal(plan.intradayConservation.finalModelFitMustUseFullCrossSection,true);
  assert.equal(plan.purgeEmbargoContract.crossCloseTargetAllowed,false);
});

test('acquisition gate remains fail-closed after entitlement and Claude re-attestation',()=>{
  const plan=JSON.parse(fs.readFileSync(new URL('../long-only/phase57-long-only-data-plan.json',import.meta.url),'utf8'));
  const gate=evaluateLongOnlyAcquisitionGate(plan);
  assert.equal(gate.status,'BLOCKED');
  assert.equal(gate.acquisitionMayStart,false);
  assert.equal(plan.preAcquisitionGate.exactCurrentEntitlementReattested,true);
  assert.equal(plan.preAcquisitionGate.claudeIndependentReviewReceived,true);
  assert.equal(plan.preAcquisitionGate.claudeCriticalBlockersResolved,true);
  for(const key of ['storageDeletionTermsReattested','freshExactDatesFrozen','operatorExplicitAcquisitionApproval'])assert.ok(gate.missing.includes(key));
  for(const key of ['integratedDataReuseContractFrozen','humanOverfittingControlsFrozen','independentReviewDispositionFrozen'])assert.ok(!gate.missing.includes(key));
  assert.match(gate.planSha256,/^[a-f0-9]{64}$/);
  assert.equal(REQUIRED_PHASE57_LONG_ONLY_ACQUISITION_GATES.length,18);
});

test('sealed validation and OOS partitions require hashed release evidence and contingency cannot open for poor performance',()=>{
  assert.throws(()=>assertReleasedPartition({partition:'PRIMARY_OOS',plan:{}}),/sealed/);
  assert.throws(()=>assertReleasedPartition({partition:'PRIMARY_OOS',plan:{runtimeReleaseEvidence:{PRIMARY_OOS:{released:true,releaseSha256:'bad'}}}}),/sealed/);
  assert.equal(assertReleasedPartition({partition:'DEVELOPMENT_A',plan:{runtimeReleaseEvidence:{DEVELOPMENT_A:{released:true,releaseSha256:'a'.repeat(64)}}}}),true);
  assert.throws(()=>assertReleasedPartition({partition:'CONTINGENCY_OOS',plan:{runtimeReleaseEvidence:{CONTINGENCY_OOS:{released:true,releaseSha256:'b'.repeat(64),reason:'POOR_PERFORMANCE'}}}}),/not permitted/);
  assert.equal(assertReleasedPartition({partition:'CONTINGENCY_OOS',plan:{runtimeReleaseEvidence:{CONTINGENCY_OOS:{released:true,releaseSha256:'b'.repeat(64),reason:'PRIMARY_EVALUATION_INVALIDATED_NON_PERFORMANCE'}}}}),true);
});

test('reserve deployment is mechanical and requires hashed admission-failure evidence',()=>{
  const plan=JSON.parse(fs.readFileSync(new URL('../long-only/phase57-long-only-data-plan.json',import.meta.url),'utf8'));
  assert.equal(assertReserveReplacement({plan,reserveSessionId:'R01',replacementFor:'DEVELOPMENT_A:03',trigger:'RAW_HASH_MISMATCH',evidenceSha256:'c'.repeat(64)}),true);
  assert.throws(()=>assertReserveReplacement({plan,reserveSessionId:'R02',replacementFor:'DEVELOPMENT_A:04',trigger:'BAD_PERFORMANCE',evidenceSha256:'d'.repeat(64)}),/not precommitted/);
  assert.throws(()=>assertReserveReplacement({plan,reserveSessionId:'R03',replacementFor:'DEVELOPMENT_A:05',trigger:'RAW_HASH_MISMATCH',evidenceSha256:'bad'}),/hashed/);
});
