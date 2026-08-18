import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';

const workflowPath='.github/workflows/phase57-p25-evidence-prep.yml';
const workflow=fs.readFileSync(workflowPath,'utf8');

test('evidence prep runs after routine capture and pins the exact canonical P24 artifact',()=>{
  assert.match(workflow,/cron: '30 8 \* \* 1-5'/);
  assert.match(workflow,/gh run download 31785422471/);
  assert.match(workflow,/phase57-p24-9-oos-canonical-candidate/);
  assert.match(workflow,/phase57-p24-9-oos-byte-snapshot\.json/);
});

test('workflow composes pinned history, session integrity and lineage CLIs without broker tooling',()=>{
  assert.match(workflow,/build_p25_pinned_history_pack\.mjs/);
  assert.match(workflow,/build_p25_session_integrity_ledger\.mjs/);
  assert.match(workflow,/build_p25_evidence_lineage_manifest\.mjs/);
  assert.doesNotMatch(workflow,/phase58_excel|RssMarket|RssTickList|ARK_ORDER|win32com/i);
});

test('daily capture and evidence branches are separate and dated lineage is immutable by head',()=>{
  assert.match(workflow,/automation\/p25-day-data/);
  assert.match(workflow,/automation\/p25-evidence-data/);
  assert.match(workflow,/manifestHeadSha256/);
  assert.match(workflow,/already exists with different lineage head/);
  assert.match(workflow,/refusing unnecessary rewrite/);
});

test('workflow keeps explicit read-only Actions permission boundary and no cancellation of an in-flight evidence snapshot',()=>{
  assert.match(workflow,/contents: write/);
  assert.match(workflow,/actions: read/);
  assert.match(workflow,/cancel-in-progress: false/);
});
