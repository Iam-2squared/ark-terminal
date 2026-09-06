import assert from 'node:assert/strict';
import test from 'node:test';
import fs from 'node:fs';
import {createHash} from 'node:crypto';
import {
  PHASE57_SELECTOR_MINIMAL_HYBRID_PHASE_A,
  planPhase57MinimalHybridSessionSplit,
  validatePhase57MinimalHybridDatasetAdmission,
} from '../daytrade/phase57-selector-minimal-hybrid-dataset-guard.js';

const SAFETY=Object.freeze({
  executionAllowed:false,brokerWriteAllowed:false,excelOrderWriteAllowed:false,
  rssOrderFunctionAllowed:false,liveTradingAllowed:false,paperTradingAllowed:false,
  automaticPromotionAllowed:false,productionUpdateAllowed:false,transmitted:false,
});

function sessions(count,{start='2025-02-03'}={}){
  const rows=[];
  let timestamp=Date.parse(`${start}T00:00:00.000Z`);
  while(rows.length<count){
    const day=new Date(timestamp).getUTCDay();
    if(day!==0&&day!==6){
      const sessionDate=new Date(timestamp).toISOString().slice(0,10);
      rows.push({
        sessionDate,
        crossSectionAtomic:true,
        decisionCutoffs:[`${sessionDate}T00:15:00.000Z`,`${sessionDate}T00:20:00.000Z`],
      });
    }
    timestamp+=86_400_000;
  }
  return rows;
}

function dataset(overrides={}){
  return {
    manifest:{
      datasetId:'PHASE57_MINIMAL_HYBRID_NEW_2025',
      rawSourceSha256:'a'.repeat(64),
      providerEntitlementVerified:true,
      previouslyUsedForSelectorOutcomeInspection:false,
      intervalMinutes:5,
      barTimestampMeaning:'BAR_OPEN',
      availableAtRule:'BAR_OPEN_PLUS_INTERVAL',
      noTradeMinutePolicy:'MISSING_NEVER_FABRICATE',
      missingMicrostructurePolicy:'UNKNOWN_WITH_AVAILABILITY_MASK',
      microstructureZeroFilled:false,
      completeCrossSectionAtomic:true,
      universeStatus:'POINT_IN_TIME',
      strongHistoricalClaimAllowed:true,
      safety:SAFETY,
      ...overrides,
    },
    sessions:sessions(120),
  };
}

test('Phase A bytes match the committed freeze digest',()=>{
  const bytes=fs.readFileSync(new URL('../research/phase57-selector-minimal-hybrid-phase-a.json',import.meta.url));
  const expected=fs.readFileSync(new URL('../research/phase57-selector-minimal-hybrid-phase-a.sha256',import.meta.url),'utf8').trim().split(/\s+/)[0];
  assert.equal(createHash('sha256').update(bytes).digest('hex'),expected);
  assert.equal(PHASE57_SELECTOR_MINIMAL_HYBRID_PHASE_A.status,'ARCHITECTURE_FROZEN_BEFORE_NEW_DATASET_OUTCOMES');
  assert.equal(PHASE57_SELECTOR_MINIMAL_HYBRID_PHASE_A.architecture.stage1.v3MembershipRequired,false);
  assert.equal(PHASE57_SELECTOR_MINIMAL_HYBRID_PHASE_A.architecture.combination.hardV1V3IntersectionAllowed,false);
  assert.equal(PHASE57_SELECTOR_MINIMAL_HYBRID_PHASE_A.targetCandidates.primaryTargetSelectedNow,false);
  assert.equal(PHASE57_SELECTOR_MINIMAL_HYBRID_PHASE_A.developmentProtocol.advancedMultitaskAllowed,false);
});

test('a new point-in-time dataset is admitted for Development only',()=>{
  const admitted=validatePhase57MinimalHybridDatasetAdmission(dataset());
  assert.equal(admitted.status,'MINIMAL_HYBRID_NEW_DATASET_ADMITTED_DEVELOPMENT_ONLY');
  assert.equal(admitted.developmentReleaseAllowed,true);
  assert.equal(admitted.validationReleaseAllowed,false);
  assert.equal(admitted.untouchedOosReleaseAllowed,false);
  assert.equal(admitted.split.development.length,71);
  assert.equal(admitted.split.purgeDevelopmentValidation.length,1);
  assert.equal(admitted.split.validation.length,23);
  assert.equal(admitted.split.purgeValidationOos.length,1);
  assert.equal(admitted.split.untouchedOos.length,24);
});

test('the consumed V1/V2/V3 window is rejected even under a new dataset id',()=>{
  const value=dataset();
  value.sessions=sessions(120,{start:'2026-01-05'});
  assert.throws(()=>validatePhase57MinimalHybridDatasetAdmission(value),/overlaps consumed hypothesis-generation evidence/);
});

test('consumed dataset ancestry is rejected',()=>{
  const value=dataset({parentDatasetIds:['PHASE57_SELECTOR_YAHOO_5M_24626FD37F8633F4']});
  assert.throws(()=>validatePhase57MinimalHybridDatasetAdmission(value),/consumed dataset identity is forbidden/);
});

test('source-validation sessions remain permanently excluded under new dataset identities',()=>{
  const registry=JSON.parse(fs.readFileSync(new URL('../research/phase57-selector-source-validation-only-registry.json',import.meta.url),'utf8'));
  assert.equal(registry.policy,'APPEND_ONLY_PERMANENT_EXCLUSION_FROM_ALL_RESEARCH_SPLITS');
  for(const date of ['2025-01-06','2025-01-07','2025-01-08','2025-01-09']){
    assert.ok(registry.sessions.some(row=>row.sessionDate===date&&row.classification==='SOURCE_VALIDATION_ONLY'),date);
    const value=dataset({datasetId:`OTHER_PROVIDER_NEW_ID_${date}`,parentDatasetIds:[]});
    value.sessions=sessions(120,{start:date});
    assert.throws(()=>validatePhase57MinimalHybridDatasetAdmission(value),/permanently SOURCE_VALIDATION_ONLY/);
    assert.throws(()=>planPhase57MinimalHybridSessionSplit(value.sessions),/permanently SOURCE_VALIDATION_ONLY/);
  }
});

test('unavailable microstructure must stay unknown rather than zero-filled',()=>{
  assert.throws(()=>validatePhase57MinimalHybridDatasetAdmission(dataset({
    missingMicrostructurePolicy:'ZERO_FILL',microstructureZeroFilled:true,
  })),/microstructure/);
});

test('survivorship-limited data cannot make a strong historical claim',()=>{
  assert.throws(()=>validatePhase57MinimalHybridDatasetAdmission(dataset({universeStatus:'SURVIVORSHIP_LIMITED'})),/point-in-time universe/);
});

test('every safety control remains false',()=>{
  for(const [key,value] of Object.entries(SAFETY))assert.equal(value,false,key);
  const value=dataset({safety:{...SAFETY,paperTradingAllowed:true}});
  assert.throws(()=>validatePhase57MinimalHybridDatasetAdmission(value),/paperTradingAllowed must remain false/);
});
