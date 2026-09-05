import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';

const workflow=fs.readFileSync('.github/workflows/phase57-car1-selected-validation-replay.yml','utf8');
const script=fs.readFileSync('scripts/run_phase57_car1_selected_validation_replay.mjs','utf8');

test('CAR-1 selected validation workflow is manual and read-only',()=>{
  assert.match(workflow,/on:\s*\n\s*workflow_dispatch:/);
  assert.match(workflow,/permissions:\s*\n\s*contents: read\s*\n\s*actions: read/);
  assert.doesNotMatch(workflow,/\n\s*push:/);
  assert.doesNotMatch(workflow,/\n\s*schedule:/);
  assert.doesNotMatch(workflow,/contents: write/);
  assert.doesNotMatch(workflow,/pull-requests: write/);
});

test('CAR-1 selected validation workflow requires exact formal source, metadata gate, and same research head',()=>{
  assert.match(workflow,/source_run_id:/);
  assert.match(workflow,/source_run_head_sha:/);
  assert.match(workflow,/candidate_run_id:/);
  assert.match(workflow,/Phase57 P25 Checkpointed Evaluation/);
  assert.match(workflow,/phase57-car1-independent-validation-candidate\.yml/);
  assert.match(workflow,/CURRENT_RESEARCH_SHA: \$\{\{ github\.sha \}\}/);
  assert.match(workflow,/test "\$\{metadata\[3\]\}" = "\$CURRENT_RESEARCH_SHA"/);
  assert.match(workflow,/DEV_CAR1_ARTIFACT_DIGEST:/);
});

test('CAR-1 selected validation CLI recomputes the metadata gate and consumes only packet-selected replay',()=>{
  assert.match(script,/runCar1ValidationCandidateMetadata/);
  assert.match(script,/gateCar1IndependentValidationMetadataCandidate/);
  assert.match(script,/buildLaneCFixedCheckpointPackets/);
  assert.match(script,/runCar1SelectedValidationReplay/);
  assert.match(script,/selectedSessionCount!==5/);
  assert.match(script,/cumulativeChallengerPerformanceConsumed:false/);
  assert.match(script,/winnerSelectionAllowed:false/);
  assert.match(script,/promotionEligible:false/);
});
