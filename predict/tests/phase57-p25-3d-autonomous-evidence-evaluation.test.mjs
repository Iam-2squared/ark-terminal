import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';
import {assembleP253AutonomousEvidenceInputs,PHASE57_P25_3D_SAFETY} from '../daytrade/phase57-p25-3d-autonomous-evidence-evaluation.js';
import {buildP253SessionIntegrityLedger} from '../daytrade/phase57-p25-3a-session-integrity-ledger.js';
import {buildP253EvidenceLineageManifest} from '../daytrade/phase57-p25-3b-evidence-lineage-manifest.js';

const safety=Object.freeze({
  executionAllowed:false,brokerWriteAllowed:false,excelOrderWriteAllowed:false,rssOrderFunctionAllowed:false,
  liveTradingAllowed:false,paperTradingAllowed:false,automaticPromotionAllowed:false,productionUpdateAllowed:false,
  transmitted:false,freshHoldoutConsumed:false,
});
const historyPack=Object.freeze({
  phase:'57.p25.2k.pinned-history-bridge-cli',
  status:'P25_2_PINNED_HISTORY_PACK_READY',
  canonicalSourceRunId:31785422471,
  canonicalSnapshotSha256:'10ec0b89893823f9e2f7ba720db2d0fad8e76d642fe00f7b77d387ae6be6b12a',
  sessions:[],sessionCount:0,perSymbolSessionCount:{},
  methodology:{freshHoldoutConsumed:false},
  safety,
});

function readyCapture(sessionDate='2026-08-19',shaChar='a'){
  const artifact={
    phase:'57.p25.2j.routine-nonrss-5m-source-cli',
    status:'P25_2_ROUTINE_5M_SESSION_READY',
    expectedSessionDates:[sessionDate],
    sessions:[{
      sessionDate,
      universeRecord:{ready:true,sessionDate,sourceSnapshotFingerprint:'f'.repeat(64)},
      sessionBarsBySymbol:{'7203.T':[]},
      sourceProvenance:{provider:'TEST_FIXTURE'},
    }],
    collection:{
      ready:true,sessionDate,targetSymbolCount:1,collectedSymbolCount:1,failedSymbolCount:0,
      failures:[],sourceBySymbol:{'7203.T':{provider:'TEST_FIXTURE'}},
    },
    methodology:{routineDailyMarketSpeedRequired:false,boardOrTickUsed:false},
    safety,
  };
  return {artifact,artifactSha256:shaChar.repeat(64),artifactPath:`${sessionDate}.json`};
}
function blockedCapture(sessionDate='2026-08-20',shaChar='b'){
  const artifact={
    phase:'57.p25.2j.routine-nonrss-5m-source-cli',
    status:'BLOCKED_P25_ROUTINE_5M_CAPTURE',
    expectedSessionDates:[sessionDate],
    sessions:[],
    collection:{
      ready:false,sessionDate,targetSymbolCount:1,collectedSymbolCount:1,failedSymbolCount:0,
      failures:[{symbol:'7203.T',reason:'FIXTURE_BLOCK'}],sourceBySymbol:{'7203.T':{provider:'TEST_FIXTURE'}},
    },
    methodology:{routineDailyMarketSpeedRequired:false,boardOrTickUsed:false},
    safety,
  };
  return {artifact,artifactSha256:shaChar.repeat(64),artifactPath:`${sessionDate}.json`};
}
function frozenEvidence(captures){
  const integrity=buildP253SessionIntegrityLedger({captureArtifacts:captures});
  const lineage=buildP253EvidenceLineageManifest({historyPack,captureArtifacts:captures,sessionIntegrityLedger:integrity});
  return {integrity,lineage};
}

test('assembles only lineage-pinned ready captures and preserves the conservative expected-session denominator',()=>{
  const captures=[readyCapture(),blockedCapture()];
  const {integrity,lineage}=frozenEvidence(captures);
  const assembled=assembleP253AutonomousEvidenceInputs({historyPack,captureArtifacts:captures,sessionIntegrityLedger:integrity,lineageManifest:lineage});
  assert.deepEqual(assembled.expectedSessionDates,['2026-08-19','2026-08-20']);
  assert.equal(assembled.sessionInputs.length,1);
  assert.equal(assembled.sessionInputs[0].sessionDate,'2026-08-19');
  assert.equal(assembled.sessionInputs[0].sourceProvenance.captureArtifactSha256,'a'.repeat(64));
  assert.equal(assembled.sessionInputs[0].sourceProvenance.lineageManifestHeadSha256,lineage.manifestHeadSha256);
  assert.equal(assembled.methodology.currentOuterOosDoesNotSelectDynamicN,true);
});

test('fails closed when the stored lineage head is changed after evidence was frozen',()=>{
  const captures=[readyCapture()];
  const {integrity,lineage}=frozenEvidence(captures);
  const tampered={...lineage,manifestHeadSha256:'0'.repeat(64)};
  assert.throws(()=>assembleP253AutonomousEvidenceInputs({historyPack,captureArtifacts:captures,sessionIntegrityLedger:integrity,lineageManifest:tampered}),/stored lineage head does not match/i);
});

test('blocked confirmed trading day remains in pace denominator but cannot become an evaluation session input',()=>{
  const captures=[blockedCapture()];
  const {integrity,lineage}=frozenEvidence(captures);
  const assembled=assembleP253AutonomousEvidenceInputs({historyPack,captureArtifacts:captures,sessionIntegrityLedger:integrity,lineageManifest:lineage});
  assert.deepEqual(assembled.expectedSessionDates,['2026-08-20']);
  assert.equal(assembled.sessionInputs.length,0);
});

test('P25.3D keeps every execution, write, promotion and fresh-holdout surface disabled',()=>{
  for(const key of ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted','freshHoldoutConsumed']){
    assert.equal(PHASE57_P25_3D_SAFETY[key],false,key);
  }
});

test('automation runs only after successful evidence prep or manual dispatch and evaluates the exact lineage snapshot',()=>{
  const workflowUrl=new URL('../../.github/workflows/phase57-p25-evidence-evaluate.yml',import.meta.url);
  const workflow=fs.readFileSync(workflowUrl,'utf8');
  assert.ok(workflow.includes('workflows: ["Phase57 P25 Evidence Lineage Prep"]'));
  assert.ok(workflow.includes("github.event.workflow_run.conclusion == 'success'"));
  assert.ok(workflow.includes('run_p25_autonomous_evidence_evaluation.mjs'));
  assert.ok(workflow.includes('x.manifest?.nodes'));
  assert.ok(workflow.includes('gh run download 31785422471'));
  assert.ok(workflow.includes('automation/p25-evaluation-data'));
  assert.ok(workflow.includes('same lineage head already evaluated'));
  assert.doesNotMatch(workflow,/RssMarket|RssTickList|ARK_ORDER|win32com|phase58_excel/i);
});
