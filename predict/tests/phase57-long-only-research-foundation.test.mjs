import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import {
  PHASE57_LONG_ONLY_RESEARCH_CONTRACT,PHASE57_LONG_ONLY_SAFETY,
  assertLongOnlyOrderIntent,validatePartitionManifest,
} from '../long-only/phase57-long-only-research-contract.js';
import {buildLongOnlyL0OpportunityCensus} from '../long-only/phase57-long-only-l0-opportunity-census.js';

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

test('data plan freezes acquisition off until exact range and partition gates are complete',()=>{
  const plan=JSON.parse(fs.readFileSync(new URL('../long-only/phase57-long-only-data-plan.json',import.meta.url),'utf8'));
  assert.equal(plan.newJquantsAcquisitionAuthorized,false);
  assert.equal(plan.existingJquantsImplementation.dailyAdjustedQuotesPipelinePresent,false);
  assert.equal(plan.minimumProposedBlock.intradayDataRequiredForL0,false);
  assert.equal(plan.partitions.UNTOUCHED_OOS.opened,false);
  assert.equal(plan.safety.freshHoldoutConsumed,false);
  assert.ok(plan.auditedAssets.every(asset=>asset.formalL0Eligible===false));
});
