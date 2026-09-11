import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

const read=p=>JSON.parse(fs.readFileSync(p,'utf8'));
const cfg=read('predict/research/phase57-exit-block-a-unseen-validation-v1.json');

test('Block A freezes exactly 30 unique chronological unseen sessions',()=>{
  const dates=cfg.sessions.map(x=>x.sessionDate);
  assert.equal(dates.length,30);
  assert.equal(new Set(dates).size,30);
  assert.deepEqual(dates,[...dates].sort());
  assert(dates.every(d=>!cfg.exposed20.includes(d)));
  assert.equal(cfg.guards.datesFrozenBeforeOutcome,true);
  assert.equal(cfg.guards.noOutcomeDrivenExpansion,true);
});

test('Block A preserves frozen contracts and strict entry semantics',()=>{
  assert.equal(cfg.lockedUpstream.selectorModelDigest,'444e296d31b0e59263f268706b4c8a7c7e9e59d6f7c9547e9f90342a24040fc2');
  assert.equal(cfg.lockedUpstream.selectorFreezeSha256,'a744d599e430d23efe4dea6600e418d3410d8a18df5055b35e1cc71432bf64da');
  assert.equal(cfg.lockedUpstream.entryThreshold,0.60);
  assert.equal(cfg.lockedUpstream.entryThresholdRule,'STRICTLY_GREATER_THAN');
  assert.equal(cfg.lockedUpstream.repeatEntryAllowed,false);
  assert.equal(cfg.minimumCausalNeighbors,30);
  assert.equal(cfg.causalAnalogMode,'PER_EVENT_STRICT_PRE_SESSION_AND_FULLY_REALIZED');
});

test('labels remain future-only and no fit or retune is authorized',()=>{
  assert.equal(cfg.primaryLabel,'IMMEDIATE_ADVERSE_PLUS6_DIRECTIONAL_CLOSE_GT_ZERO');
  assert.equal(cfg.guards.noThresholdOptimization,true);
  assert.equal(cfg.guards.noWeightsOrModelFit,true);
  assert.equal(cfg.guards.noRetuning,true);
  assert.equal(cfg.frozenFeatureFamily.length,8);
});

test('all safety flags are false',()=>{
  assert.equal(Object.keys(cfg.safety).length,9);
  for(const v of Object.values(cfg.safety))assert.equal(v,false);
});

test('measurement enforces causal analogs and paired direction grouping',()=>{
  const measure=fs.readFileSync('scripts/phase57-exit-v4-20session-measure.mjs','utf8');
  const analyze=fs.readFileSync('scripts/phase57-exit-block-a-analyze.mjs','utf8');
  assert.match(measure,/a\.sessionDate<e\.sessionDate&&Date\.parse\(a\.fullyRealizedAt\)<entryTime/);
  assert.match(measure,/CAUSAL_ANALOG_POOL_TOO_SMALL/);
  assert.match(analyze,/\['LONG','SHORT'\]/);
  assert.match(analyze,/datesFrozenBeforeOutcome:true/);
  assert.match(analyze,/noThresholdOrWeightsFit:true/);
});
