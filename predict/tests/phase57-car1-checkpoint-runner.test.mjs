import assert from 'node:assert/strict';
import test from 'node:test';
import {buildP253SessionIntegrityLedger} from '../daytrade/phase57-p25-3a-session-integrity-ledger.js';
import {buildP253EvidenceLineageManifest} from '../daytrade/phase57-p25-3b-evidence-lineage-manifest.js';
import {runP253QCheckpointedEvaluation} from '../daytrade/phase57-p25-3q-checkpointed-evaluation.js';
import {
  PHASE57_CAR1_CHECKPOINT_POLICY,
  PHASE57_CAR1_CHECKPOINT_SAFETY,
  runCar1CheckpointedSizingAttribution,
} from '../portfolio/phase57-car1-checkpoint-runner.js';

const DATE='2026-08-19';
const CUTOFF=`${DATE}T00:00:00.000Z`;
const EXIT=`${DATE}T00:05:00.000Z`;
const safety=Object.freeze({
  executionAllowed:false,brokerWriteAllowed:false,excelOrderWriteAllowed:false,rssOrderFunctionAllowed:false,
  liveTradingAllowed:false,paperTradingAllowed:false,automaticPromotionAllowed:false,productionUpdateAllowed:false,
  transmitted:false,freshHoldoutConsumed:false,
});
const historyPack=Object.freeze({
  phase:'57.p25.2k.pinned-history-bridge-cli',status:'P25_2_PINNED_HISTORY_PACK_READY',
  canonicalSourceRunId:31785422471,canonicalSnapshotSha256:'10ec0b89893823f9e2f7ba720db2d0fad8e76d642fe00f7b77d387ae6be6b12a',
  sessions:[],sessionCount:0,perSymbolSessionCount:{},methodology:{freshHoldoutConsumed:false},safety,
});

function symbols(count){
  return Array.from({length:count},(_,index)=>`${1001+index}.T`);
}

function fixture(){
  const day50=symbols(50);
  const variants={
    FIXED_5:day50.slice(0,5),
    OLD_FIXED_30:day50.slice(0,30),
    DYNAMIC_30:day50.slice(0,30),
    DYNAMIC_40:day50.slice(0,40),
    DYNAMIC_50:day50,
  };
  const universeRecord={
    phase:'57.p25.1.frozen-universe',status:'READY',ready:true,sessionDate:DATE,
    sourceSnapshotFingerprint:'f'.repeat(64),variants,
    rankAudit:{day50:day50.map((symbol,index)=>({symbol,sector:index<25?'SECTOR_A':'SECTOR_B'}))},
    methodology:{frozenBeforeSession:true},safety,
  };
  const bars=[
    {timestamp:CUTOFF,open:100,high:100,low:100,close:100,volume:1_000},
    {timestamp:EXIT,open:101,high:101,low:101,close:101,volume:1_000},
  ];
  const artifact={
    phase:'57.p25.2j.routine-nonrss-5m-source-cli',status:'P25_2_ROUTINE_5M_SESSION_READY',
    expectedSessionDates:[DATE],
    sessions:[{sessionDate:DATE,universeRecord,sessionBarsBySymbol:{'1001.T':bars},sourceProvenance:{provider:'TEST_FIXTURE'}}],
    collection:{
      ready:true,sessionDate:DATE,targetSymbolCount:50,collectedSymbolCount:50,failedSymbolCount:0,failures:[],
      sourceBySymbol:Object.fromEntries(day50.map(symbol=>[symbol,{provider:'TEST_FIXTURE'}])),
    },
    methodology:{routineDailyMarketSpeedRequired:false,boardOrTickUsed:false},safety,
  };
  const capture={artifact,artifactSha256:'a'.repeat(64),artifactPath:`${DATE}.json`};
  const captures=[capture];
  const integrity=buildP253SessionIntegrityLedger({captureArtifacts:captures});
  const lineage=buildP253EvidenceLineageManifest({historyPack,captureArtifacts:captures,sessionIntegrityLedger:integrity});
  const decisionAttempts=day50.map((symbol,index)=>({
    symbol,sessionDate:DATE,featureCutoff:CUTOFF,
    status:index===0?'PROSPECTIVE_PHASE57_FROZEN_SIGNAL_READY':'PROSPECTIVE_PHASE57_FROZEN_WAIT_READY',
    direction:index===0?1:0,signalEligible:index===0,
    confidence:index===0?0.8:null,probability:index===0?0.8:null,selectedHorizonBars:index===0?1:null,
    selectedFeatureFamily:index===0?'TEST_FEATURE':null,selectedModelType:index===0?'TEST_MODEL':null,
    selectedConfigId:index===0?'TEST_CONFIG':null,selectedThreshold:index===0?0.7:null,
    modelId:index===0?'TEST_MODEL_ID':'TEST_WAIT',artifactSha256:index===0?'b'.repeat(64):null,
    sourceBarCloseAt:CUTOFF,
    variantMemberships:Object.entries(variants).filter(([,members])=>members.includes(symbol)).map(([name])=>name),
    sector:index<25?'SECTOR_A':'SECTOR_B',
  }));
  const shard={
    phase:'57.p25.3o.sharded-prefix-replay',status:'P25_3O_PREFIX_SHARD_COMPLETE',sessionDate:DATE,
    fullTargetSymbolCount:50,fullTargetSymbols:day50,shardSymbolCount:50,shardSymbols:day50,
    commonFairCutoffCount:1,commonFairCutoffs:[CUTOFF],successfulDecisionCount:decisionAttempts.length,
    blockedDecisionCount:0,decisionAttempts,blockedDecisions:[],methodology:{fullTargetUnionUsedForFairCutoffGrid:true},safety,
  };
  const checkpoint={
    phase:'57.p25.3p.checkpoint',status:'P25_3P_CHECKPOINT_COMPLETE',schemaVersion:1,
    batchSize:80,batchCount:1,batchIndex:0,batchId:'batch-00',shardSymbols:day50,
    identities:{historyPackSha256:'c'.repeat(64),captureSha256:capture.artifactSha256,sessionDate:DATE},
    methodology:{computePlacementOnly:true,fullUnionFairCutoffGridPreserved:true},safety,shard,
  };
  const checkpointsBySession={[DATE]:[checkpoint]};
  const input={historyPack,captureArtifacts:captures,sessionIntegrityLedger:integrity,lineageManifest:lineage,checkpointsBySession};
  const sourceEvaluation=runP253QCheckpointedEvaluation(input);
  return {input,sourceEvaluation};
}

test('CAR-1 checkpoint runner reconciles formal P25 evidence before exposing paired sizing rows',()=>{
  const {input,sourceEvaluation}=fixture();
  const result=runCar1CheckpointedSizingAttribution({
    ...input,
    sourceEvaluationArtifact:sourceEvaluation,
    universeVariants:['DYNAMIC_50'],
    sizingProfileIds:['EQUAL_NOTIONAL'],
  });
  assert.equal(result.status,'CAR1_CHECKPOINTED_PAIRED_SIZING_ATTRIBUTION_READY');
  assert.deepEqual(result.universeVariantOrder,['DYNAMIC_50']);
  assert.deepEqual(result.baselineProfileOrder,['MAX_10','MAX_4','MAX_3','MAX_2']);
  assert.deepEqual(result.sizingProfileOrder,['EQUAL_NOTIONAL']);
  assert.equal(result.sourceReconciliation.exactCheckpointRecomputationMatch,true);
  assert.equal(result.inputAudit.frozenTradeCount,1);
  assert.equal(result.inputAudit.resolvedTradeCount,1);
  assert.equal(result.matrixRows.length,4);
  for(const baselineProfileId of result.baselineProfileOrder){
    assert.equal(result.baselineParity.DYNAMIC_50[baselineProfileId].passed,true,baselineProfileId);
    const attribution=result.attributions.DYNAMIC_50[baselineProfileId];
    assert.equal(attribution.legacyReplayParity.passed,true,baselineProfileId);
    assert.equal(attribution.pairedAudit.sameCandidatePriority,true,baselineProfileId);
    const row=result.matrixRows.find(candidate=>candidate.baselineProfileId===baselineProfileId);
    assert.equal(row.sizingProfileId,'EQUAL_NOTIONAL');
    assert.equal(row.deltaTotalReturnPct,0);
    assert.equal(row.deltaMaxDrawdownPct,0);
    assert.equal(row.winnerEligible,false);
    assert.equal(row.formalOos,false);
  }
  assert.equal(result.methodology.parameterSearchAllowed,false);
  assert.equal(result.methodology.winnerSelectionAllowed,false);
  assert.equal(result.methodology.promotionEligible,false);
  assert.equal(result.methodology.futureOutcomeUsedBySizer,false);
  assert.equal(result.methodology.incompleteProspectiveBackfillAllowed,false);
});

test('CAR-1 checkpoint runner keeps every order and transmission boundary false',()=>{
  assert.equal(PHASE57_CAR1_CHECKPOINT_POLICY.rankingChanged,false);
  assert.equal(PHASE57_CAR1_CHECKPOINT_POLICY.selectorChanged,false);
  assert.equal(PHASE57_CAR1_CHECKPOINT_POLICY.entryChanged,false);
  assert.equal(PHASE57_CAR1_CHECKPOINT_POLICY.exitChanged,false);
  assert.equal(PHASE57_CAR1_CHECKPOINT_POLICY.parameterSearchAllowed,false);
  assert.equal(PHASE57_CAR1_CHECKPOINT_POLICY.winnerSelectionAllowed,false);
  for(const key of [
    'executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed',
    'liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted',
  ])assert.equal(PHASE57_CAR1_CHECKPOINT_SAFETY[key],false,key);
});
