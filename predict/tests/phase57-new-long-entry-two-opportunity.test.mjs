import test from 'node:test';
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
const env={...process.env,PYTHONDONTWRITEBYTECODE:'1'};

const runPython=(args)=>spawnSync('python',args,{cwd:root,encoding:'utf8',env,timeout:120000});

test('two-opportunity kernel and replay python tests pass',()=>{
  const p=runPython(['-m','unittest',
    'scripts.test_phase57_new_long_entry_two_opportunity',
    'scripts.test_phase57_new_long_entry_two_opportunity_replay']);
  assert.equal(p.status,0,p.stdout+p.stderr);
});

test('two-opportunity replay is deterministic and reproduces frozen Entry-location parity',()=>{
  const run=()=>runPython(['-m','scripts.phase57_new_long_entry_two_opportunity_replay']);
  const a=run();assert.equal(a.status,0,a.stdout+a.stderr);
  const b=run();assert.equal(b.status,0,b.stdout+b.stderr);
  assert.equal(a.stdout,b.stdout);
  const r=JSON.parse(a.stdout.trim());
  assert.equal(r.status,'NEW_LONG_ENTRY_TWO_OPPORTUNITY_KERNEL_PARITY_PASS');
  assert.equal(r.fullAnchors,2743);
  assert.equal(r.primary60,878);
  assert.equal(r.primaryFirstClosedDip,328);
  assert.equal(r.primaryNoFirstClosedDip,550);
  assert.equal(r.primarySecondaryResolved,328);
  assert.deepEqual(r.primaryStateCounts,{DIP_REPRICE_EMITTED:328,FIRST_BAR_CONTINUATION:550});
  assert.equal(r.dipRepriceParity.capture3.denominator,59);
  assert.equal(r.dipRepriceParity.capture3.hits,56);
  assert.equal(r.dipRepriceParity.capture5.denominator,21);
  assert.equal(r.dipRepriceParity.capture5.hits,21);
  assert.ok(Math.abs(r.dipRepriceParity.buyImprovementPct.mean-1.1184)<0.0001);
  assert.equal(r.newValidation,false);
  assert.equal(r.architecturePerformanceConclusionAllowed,false);
  assert.equal(r.modelFits,0);assert.equal(r.modelPredictions,0);
  assert.equal(r.freshAccess,0);assert.equal(r.oosAccess,0);assert.equal(r.providerRequests,0);
  assert.equal(r.minuteResearchRuns,0);assert.equal(r.exitEvaluations,0);
  assert.equal(r.capitalEvaluations,0);assert.equal(r.portfolioEvaluations,0);
  assert.equal(r.mainMerge,false);
  assert.ok(Object.values(r.safety).every(v=>v===false));
  console.log('TWO_OPPORTUNITY_ENTRY_PARITY='+JSON.stringify(r));
});
