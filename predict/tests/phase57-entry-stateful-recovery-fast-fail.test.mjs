import test from 'node:test';
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
const allowed=new Set([
  'STATEFUL_ENTRY_RECOVERY_FAST_FAIL_CONTINUE_NOT_VALIDATED',
  'STATEFUL_ENTRY_RECOVERY_FAST_FAIL_KILL',
  'STATEFUL_ENTRY_RECOVERY_FAST_FAIL_INCONCLUSIVE',
  'STATEFUL_ENTRY_RECOVERY_FAST_FAIL_BLOCKED',
]);

test('stateful recovery fast-fail is deterministic, Entry-only and never auto-promotes',()=>{
  const run=()=>spawnSync('python',['-m','scripts.phase57_entry_stateful_recovery_fast_fail'],{
    cwd:root,encoding:'utf8',env:{...process.env,PYTHONDONTWRITEBYTECODE:'1'},timeout:120000
  });
  const a=run();assert.equal(a.status,0,a.stdout+a.stderr);
  const b=run();assert.equal(b.status,0,b.stdout+b.stderr);
  assert.equal(a.stdout,b.stdout);
  const r=JSON.parse(a.stdout.trim());
  assert.ok(allowed.has(r.verdict));
  assert.equal(r.fullAnchors,2743);
  assert.equal(r.primary,878);
  assert.equal(r.firstClosedDip,328);
  assert.equal(r.candidateAccepted,false);
  assert.equal(r.modelFits,0);assert.equal(r.modelPredictions,0);
  assert.equal(r.freshAccess,0);assert.equal(r.oosAccess,0);assert.equal(r.providerRequests,0);
  assert.equal(r.minuteResearchRuns,0);assert.equal(r.exitEvaluations,0);
  assert.equal(r.capitalEvaluations,0);assert.equal(r.portfolioEvaluations,0);
  assert.equal(r.mainMerge,false);
  assert.ok(Object.values(r.safety).every(v=>v===false));
  console.log('STATEFUL_ENTRY_FAST_FAIL_RESULT='+JSON.stringify(r));
});
