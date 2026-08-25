import assert from 'node:assert/strict';
import test from 'node:test';
import {buildP253SessionIntegrityLedger} from '../daytrade/phase57-p25-3a-session-integrity-ledger.js';
import {buildP253EvidenceLineageManifest} from '../daytrade/phase57-p25-3b-evidence-lineage-manifest.js';
import {runP253QCheckpointedEvaluation} from '../daytrade/phase57-p25-3q-checkpointed-evaluation.js';
import {
  PHASE57_P25_LANE_C_FIXED_RUNNER_POLICY,
  PHASE57_P25_LANE_C_FIXED_RUNNER_SAFETY,
  runLaneCFixedCheckpointedPortfolio,
} from '../portfolio/phase57-p25-lane-c-fixed-checkpoint-runner.js';

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
    sourceBarCloseAt:CUTOFF,variantMemberships:Object.entries(variants).filter(([,members])=>members.includes(symbol)).map(([name])=>name),
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
  const input={
    historyPack,captureArtifacts:captures,sessionIntegrityLedger:integrity,lineageManifest:lineage,checkpointsBySession,
  };
  const sourceEvaluation=runP253QCheckpointedEvaluation(input);
  return {input,sourceEvaluation,checkpoint};
}

test('reconciles the formal Fixed artifact before building the all-variant allocation matrix',()=>{
  const {input,sourceEvaluation}=fixture();
  const result=runLaneCFixedCheckpointedPortfolio({...input,sourceEvaluationArtifact:sourceEvaluation});
  assert.equal(result.status,'LANE_C_FIXED_CHECKPOINTED_PORTFOLIO_MATRIX_READY');
  assert.equal(result.managementMode,'FIXED_HORIZON');
  assert.deepEqual(result.universeVariantOrder,['FIXED_5','OLD_FIXED_30','DYNAMIC_30','DYNAMIC_40','DYNAMIC_50']);
  assert.deepEqual(result.profileOrder,['CURRENT_EXISTING','MAX_10','MAX_4','MAX_3','MAX_2']);
  assert.equal(result.sourceReconciliation.exactCheckpointRecomputationMatch,true);
  assert.equal(result.sourceReconciliation.packetSummariesMatch,true);
  assert.equal(result.inputAudit.frozenTradeCount,1);
  assert.equal(result.inputAudit.resolvedTradeCount,1);
  assert.equal(result.inputAudit.unresolvedTradeCount,0);
  for(const variant of result.universeVariantOrder){
    const comparison=result.comparisons[variant];
    assert.equal(comparison.pairedAudit.candidateEntryCount,1,variant);
    assert.equal(comparison.results.CURRENT_EXISTING.status,'REFERENCE_ONLY_NOT_CAUSAL_PORTFOLIO');
    assert.equal(comparison.results.CURRENT_EXISTING.max10Equivalent,null);
    assert.equal(comparison.results.MAX_10.trade.accepted,1);
    assert.equal(result.sourceReconciliation.byUniverseVariant[variant].currentReferenceMatchesFormalP25,true);
  }
  assert.equal(result.methodology.dynamicVariantNamesAreUniverseSizesNotManagementModes,true);
  assert.equal(result.methodology.winnerSelectionAllowed,false);
  assert.equal(result.methodology.prospectiveSampleSufficient,false);
});

test('fails closed if the supplied formal evaluation differs from checkpoint recomputation',()=>{
  const {input,sourceEvaluation}=fixture();
  const tampered={...sourceEvaluation,lineageNodeCount:sourceEvaluation.lineageNodeCount+1};
  assert.throws(
    ()=>runLaneCFixedCheckpointedPortfolio({...input,sourceEvaluationArtifact:tampered}),
    /does not match checkpoint recomputation/i,
  );
});

test('fails closed if a checkpoint is not bound to the capture SHA in the lineage input',()=>{
  const {input,sourceEvaluation,checkpoint}=fixture();
  const tamperedCheckpoint={...checkpoint,identities:{...checkpoint.identities,captureSha256:'0'.repeat(64)}};
  assert.throws(
    ()=>runLaneCFixedCheckpointedPortfolio({
      ...input,checkpointsBySession:{[DATE]:[tamperedCheckpoint]},sourceEvaluationArtifact:sourceEvaluation,
    }),
    /capture identity mismatch/i,
  );
});

test('freezes Fixed-first policy, separate Current and Max10, and every research-only safety flag',()=>{
  assert.equal(PHASE57_P25_LANE_C_FIXED_RUNNER_POLICY.managementMode,'FIXED_HORIZON');
  assert.equal(PHASE57_P25_LANE_C_FIXED_RUNNER_POLICY.currentExistingReferenceOnly,true);
  assert.equal(PHASE57_P25_LANE_C_FIXED_RUNNER_POLICY.max10AssumedEquivalentToCurrent,false);
  assert.equal(PHASE57_P25_LANE_C_FIXED_RUNNER_POLICY.dynamicManagementChanged,false);
  assert.equal(PHASE57_P25_LANE_C_FIXED_RUNNER_POLICY.winnerSelectionAllowed,false);
  for(const key of [
    'executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed',
    'liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed',
    'transmitted','freshHoldoutConsumed',
  ])assert.equal(PHASE57_P25_LANE_C_FIXED_RUNNER_SAFETY[key],false,key);
});
