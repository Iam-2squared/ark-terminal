import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';

const workflow=fs.readFileSync(new URL('../../.github/workflows/phase57-car1-sizing-attribution.yml',import.meta.url),'utf8');
const cli=fs.readFileSync(new URL('../../scripts/run_phase57_car1_checkpointed_sizing.mjs',import.meta.url),'utf8');

test('CAR-1 evidence workflow is pinned, read-only, and PR/research scoped',()=>{
  assert.match(workflow,/name: Phase57 CAR-1 Sizing Attribution/);
  assert.match(workflow,/pull_request:/);
  assert.match(workflow,/workflow_dispatch:/);
  assert.doesNotMatch(workflow,/\n\s*schedule:/);
  assert.doesNotMatch(workflow,/\n\s*workflow_run:/);
  assert.match(workflow,/permissions:\n\s+contents: read\n\s+actions: read/);
  assert.doesNotMatch(workflow,/contents: write/);
  assert.match(workflow,/SOURCE_RUN_ID: '33762588162'/);
  assert.match(workflow,/SOURCE_RUN_HEAD_SHA: '725aa956c30710de43de13110763476a4a6f1a9c'/);
  assert.match(workflow,/phase57-p25-checkpointed-evaluation\.yml/);
  assert.match(workflow,/run_phase57_car1_checkpointed_sizing\.mjs/);
  assert.doesNotMatch(workflow,/git push/);
  assert.doesNotMatch(workflow,/automation\/p25/);
  assert.match(workflow,/development evidence only/i);
  assert.match(workflow,/no winner selection/i);
});

test('CAR-1 CLI emits development evidence only and keeps interpretation locks closed',()=>{
  assert.match(cli,/developmentEvidenceOnly:true/);
  assert.match(cli,/sameFrozenEntry:true/);
  assert.match(cli,/sameFrozenExit:true/);
  assert.match(cli,/sameCandidatePriority:true/);
  assert.match(cli,/parameterSearchAllowed:false/);
  assert.match(cli,/winnerSelectionAllowed:false/);
  assert.match(cli,/promotionEligible:false/);
  assert.match(cli,/formalOos:false/);
  assert.match(cli,/incompleteProspectiveBackfillAllowed:false/);
  assert.doesNotMatch(cli,/git push/);
  assert.doesNotMatch(cli,/RssStockOrder|brokerWriteAllowed:true|liveTradingAllowed:true|paperTradingAllowed:true/);
});
