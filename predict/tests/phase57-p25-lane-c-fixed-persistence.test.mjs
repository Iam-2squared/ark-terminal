import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import {gzipSync} from 'node:zlib';
import {
  buildLaneCFixedPersistenceSummary,
  LaneCFixedPersistenceInternals,
  PHASE57_P25_LANE_C_FIXED_PERSISTENCE_PROFILES as profiles,
  PHASE57_P25_LANE_C_FIXED_PERSISTENCE_VARIANTS as variants,
  validateLaneCFixedPortfolioArtifact,
} from '../portfolio/phase57-p25-lane-c-fixed-persistence.js';

const falseSafety=()=>({
  executionAllowed:false,brokerWriteAllowed:false,excelOrderWriteAllowed:false,rssOrderFunctionAllowed:false,
  liveTradingAllowed:false,paperTradingAllowed:false,automaticPromotionAllowed:false,productionUpdateAllowed:false,
  transmitted:false,freshHoldoutConsumed:false,
});

function artifactFixture(){
  const safety=falseSafety();
  const timestamp='2026-08-25T00:00:00.000Z';
  const comparisons={};
  const matrixRows=[];
  for(const variant of variants){
    const results={
      CURRENT_EXISTING:{
        status:'REFERENCE_ONLY_NOT_CAUSAL_PORTFOLIO',max10Equivalent:null,
        safety,
      },
    };
    matrixRows.push({
      managementMode:'FIXED_HORIZON',universeVariant:variant,profileId:'CURRENT_EXISTING',
      resultClass:'REFERENCE_ONLY_NOT_CAUSAL',winnerEligible:false,
    });
    for(const profileId of profiles.slice(1)){
      results[profileId]={
        status:'LANE_C_EVENT_TIME_PORTFOLIO_SIMULATED',
        return:{finalEquityJpy:1_000_000},
        equityCurve:[{timestamp,portfolioEquityJpy:1_000_000}],
        dailyEquityCurve:[{sessionDate:'2026-08-25',equityJpy:1_000_000}],
        concentrationCurve:[{timestamp,openPositionCount:0}],
        methodology:{allocatorCanSeeFutureExit:false,availableCashConstrainsPurchase:true},
        safety,
      };
      matrixRows.push({
        managementMode:'FIXED_HORIZON',universeVariant:variant,profileId,
        resultClass:'CAUSAL_EVENT_TIME_PORTFOLIO',winnerEligible:false,
      });
    }
    comparisons[variant]={
      status:'LANE_C_PAIRED_ALLOCATION_PROFILES_SIMULATED',
      resultOrder:[...profiles],results,safety,
    };
  }
  const result={
    status:'LANE_C_FIXED_CHECKPOINTED_PORTFOLIO_MATRIX_READY',managementMode:'FIXED_HORIZON',
    universeVariantOrder:[...variants],profileOrder:[...profiles],lineageManifestHeadSha256:'a'.repeat(64),
    sourceReconciliation:{
      exactCheckpointRecomputationMatch:true,packetSummariesMatch:true,
      sourceEvaluationCanonicalSha256:'b'.repeat(64),recomputedEvaluationCanonicalSha256:'b'.repeat(64),
    },
    inputAudit:{
      readySessionCount:1,expectedSessionCount:1,expectedSessionDates:['2026-08-25'],
      checkpointArtifactCount:1,frozenTradeCount:1,resolvedTradeCount:1,unresolvedTradeCount:0,packetSummaries:[],
    },
    comparisons,matrixRows,
    methodology:{
      dynamicHoldExitConnected:false,winnerSelectionAllowed:false,prospectiveSampleSufficient:false,
      availableCashConstrainsPurchase:true,unrealizedPnlInEquityButNotCash:true,
      futureExitOrReturnVisibleToAllocator:false,
    },
    safety,
  };
  return {
    schemaVersion:1,phase:'57.p25.lane-c.fixed-checkpoint-portfolio-cli',
    status:'LANE_C_FIXED_CHECKPOINTED_PORTFOLIO_ARTIFACT_WRITTEN',
    resultCanonicalSha256:LaneCFixedPersistenceInternals.canonicalSha256(result),result,
    methodology:{
      formalP25EvaluationReconciledBeforeSimulation:true,sameFrozenEntry:true,fixedHorizonExitUnchanged:true,
      currentExistingReferenceOnly:true,max10AssumedEquivalentToCurrent:false,dynamicManagementArtifactUsed:false,
      winnerSelectionAllowed:false,freshHoldoutConsumed:false,
    },
    safety,
  };
}

function refreshResultSha(artifact){
  artifact.resultCanonicalSha256=LaneCFixedPersistenceInternals.canonicalSha256(artifact.result);
  return artifact;
}

test('builds a compact append-only summary while auditing every retained full curve',()=>{
  const artifact=artifactFixture();
  const raw=Buffer.from(`${JSON.stringify(artifact)}\n`);
  const archive=gzipSync(raw,{level:9,mtime:0});
  const summary=buildLaneCFixedPersistenceSummary({
    artifact,sourceRunId:'32831810521',rawArtifactBytes:raw,archiveBytes:archive,
    rawArtifactName:'fixed.json',archiveName:'fixed.json.gz',
  });
  assert.equal(summary.status,'LANE_C_FIXED_PORTFOLIO_PERSISTENCE_SUMMARY_READY');
  assert.equal(summary.evidenceDate,'2026-08-25');
  assert.deepEqual(summary.universeVariantOrder,variants);
  assert.deepEqual(summary.profileOrder,profiles);
  assert.equal(summary.matrixRows.length,25);
  assert.equal(summary.curveAudit.DYNAMIC_50.MAX_2.equityPointCount,1);
  assert.equal(summary.fullArtifact.containsFullFiveMinuteMtmEquityCurves,true);
  assert.equal(summary.fullArtifact.rawSha256,LaneCFixedPersistenceInternals.sha256(raw));
  assert.equal(summary.methodology.currentExistingReferenceOnly,true);
  assert.equal(summary.methodology.max10AssumedEquivalentToCurrent,false);
  assert.equal(summary.methodology.winnerSelectionAllowed,false);
});

test('fails closed on an unsafe flag before persistence',()=>{
  const artifact=artifactFixture();
  artifact.safety.executionAllowed=true;
  refreshResultSha(artifact);
  assert.throws(()=>validateLaneCFixedPortfolioArtifact(artifact),/executionAllowed must be false/i);
});

test('fails closed if the allocator can see future EXIT information',()=>{
  const artifact=artifactFixture();
  artifact.result.comparisons.DYNAMIC_50.results.MAX_2.methodology.allocatorCanSeeFutureExit=true;
  refreshResultSha(artifact);
  assert.throws(()=>validateLaneCFixedPortfolioArtifact(artifact),/future outcome visibility/i);
});

test('fails closed when Current and Max10 or the precommitted matrix are collapsed',()=>{
  const artifact=artifactFixture();
  artifact.result.comparisons.DYNAMIC_30.results.CURRENT_EXISTING.max10Equivalent=true;
  refreshResultSha(artifact);
  assert.throws(()=>validateLaneCFixedPortfolioArtifact(artifact),/separate from Max10/i);

  const missing=artifactFixture();
  missing.result.matrixRows.pop();
  refreshResultSha(missing);
  assert.throws(()=>validateLaneCFixedPortfolioArtifact(missing),/matrix is incomplete/i);
});

test('workflow consumes every exact checkpoint artifact and persists summary plus compressed full curves without touching Dynamic management',()=>{
  const workflow=fs.readFileSync(new URL('../../.github/workflows/phase57-p25-lane-c-fixed-portfolio.yml',import.meta.url),'utf8');
  assert.match(workflow,/workflows: \['Phase57 P25 Checkpointed Evaluation'\]/);
  assert.match(workflow,/github\.event\.workflow_run\.conclusion == 'success'/);
  assert.match(workflow,/phase57-p25-checkpointed-evaluation\.yml/);
  assert.match(workflow,/mapfile -t captures/);
  assert.match(workflow,/mapfile -t checkpoints/);
  assert.match(workflow,/run_p25_lane_c_fixed_portfolio\.mjs/);
  assert.match(workflow,/package_p25_lane_c_fixed_portfolio\.mjs/);
  assert.match(workflow,/automation\/p25-lane-c-data/);
  assert.match(workflow,/\.summary\.json/);
  assert.match(workflow,/\.json\.gz/);
  assert.match(workflow,/test ! -e \"\$target\"/);
  assert.match(workflow,/immutable no-op/);
  assert.match(workflow,/winnerEligible!==false/);
  assert.doesNotMatch(workflow,/run_p25_dynamic_management_persistence|RssMarket|RssTickList|ARK_ORDER|win32com|phase58_excel/i);
});
