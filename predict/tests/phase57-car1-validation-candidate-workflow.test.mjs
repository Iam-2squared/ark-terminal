import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';

const workflowPath=new URL('../../.github/workflows/phase57-car1-independent-validation-candidate.yml',import.meta.url);
const scriptPath=new URL('../../scripts/run_phase57_car1_validation_candidate_metadata.mjs',import.meta.url);
const workflow=fs.readFileSync(workflowPath,'utf8');
const script=fs.readFileSync(scriptPath,'utf8');

test('CAR-1 future validation candidate workflow is manual, read-only, pinned to the frozen development artifact, and metadata-only',()=>{
  assert.match(workflow,/workflow_dispatch:/);
  assert.doesNotMatch(workflow,/\bpush:/);
  assert.doesNotMatch(workflow,/\bschedule:/);
  assert.match(workflow,/permissions:\s*\n\s+contents: read\s*\n\s+actions: read/);
  assert.match(workflow,/DEV_CAR1_RUN_ID: '33943395885'/);
  assert.match(workflow,/DEV_CAR1_RUN_HEAD_SHA: '59d1f93e288d414d912d9ddfd1c91815c4ae8a90'/);
  assert.match(workflow,/DEV_CAR1_ARTIFACT_DIGEST: 'sha256:658853e3d257d30b95f919dc86bf131cd4b0ef7ab66e7a688a080973ac9a7ac7'/);
  assert.match(workflow,/head_branch.*main|test "\$\{metadata\[2\]\}" = 'main'/);
  assert.match(workflow,/run_phase57_car1_validation_candidate_metadata\.mjs/);
  assert.match(workflow,/Verify no cumulative challenger performance was materialized/);
  for(const forbidden of ['contents: write','pull-requests: write','RssStockOrder','brokerWriteAllowed=true','liveTradingAllowed=true','paperTradingAllowed=true']){
    assert.equal(workflow.includes(forbidden),false,forbidden);
  }
});

test('metadata-only CLI never invokes the cumulative CAR-1 challenger attribution runner',()=>{
  assert.match(script,/runCar1ValidationCandidateMetadata/);
  assert.match(script,/gateCar1IndependentValidationMetadataCandidate/);
  assert.doesNotMatch(script,/runCar1CheckpointedSizingAttribution/);
  assert.match(script,/cumulativeChallengerPerformanceMaterialized:false/);
  assert.match(script,/performanceExtractionAllowed:false/);
});
