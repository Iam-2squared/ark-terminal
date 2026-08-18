import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';

const workflowUrl=new URL('../../.github/workflows/phase57-p25-evidence-prep.yml',import.meta.url);
const workflow=fs.readFileSync(workflowUrl,'utf8');

test('evidence prep runs after routine capture and pins the exact canonical P24 artifact',()=>{
  assert.ok(workflow.includes("cron: '30 8 * * 1-5'"));
  assert.ok(workflow.includes('gh run download 31785422471'));
  assert.ok(workflow.includes('phase57-p24-9-oos-canonical-candidate'));
  assert.ok(workflow.includes('phase57-p24-9-oos-byte-snapshot.json'));
});

test('workflow composes pinned history, session integrity and lineage CLIs without broker tooling',()=>{
  assert.ok(workflow.includes('build_p25_pinned_history_pack.mjs'));
  assert.ok(workflow.includes('build_p25_session_integrity_ledger.mjs'));
  assert.ok(workflow.includes('build_p25_evidence_lineage_manifest.mjs'));
  assert.doesNotMatch(workflow,/phase58_excel|RssMarket|RssTickList|ARK_ORDER|win32com/i);
});

test('daily capture and evidence branches are separate and dated lineage is immutable by head',()=>{
  assert.ok(workflow.includes('automation/p25-day-data'));
  assert.ok(workflow.includes('automation/p25-evidence-data'));
  assert.ok(workflow.includes('manifestHeadSha256'));
  assert.ok(workflow.includes('already exists with different lineage head'));
  assert.ok(workflow.includes('refusing unnecessary rewrite'));
});

test('workflow keeps explicit read-only Actions permission boundary and no cancellation of an in-flight evidence snapshot',()=>{
  assert.ok(workflow.includes('contents: write'));
  assert.ok(workflow.includes('actions: read'));
  assert.ok(workflow.includes('cancel-in-progress: false'));
});
