import fs from 'node:fs';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { CONTRACT, CONTRACT_SHA256, FEATURES, sha256 } from './phase57-minimal-stateful-entry.mjs';

const read = name => fs.readFileSync(new URL(`../../predict/research/${name}`, import.meta.url));
const digest = bytes => createHash('sha256').update(bytes).digest('hex');
const allocationBytes = read('phase57-entry-development-allocation-v1.json');
const fitBytes = read('phase57-entry-development-fit-v1.json');
const frozen = value => {if(value && typeof value==='object'){Object.values(value).forEach(frozen);Object.freeze(value);}return value;};
export const ALLOCATION = frozen(JSON.parse(allocationBytes));
export const FIT = frozen(JSON.parse(fitBytes));
export const ALLOCATION_SHA = digest(allocationBytes);
export const FIT_SHA = digest(fitBytes);

export function verifyDevelopmentContracts() {
  const freeze=JSON.parse(read('phase57-entry-development-freeze-sha256.json'));
  for(const [path,sha] of Object.entries(freeze.files)) assert.equal(digest(read(path.split('/').at(-1))),sha,'FROZEN_CONTRACT_BYTES_CHANGED');
  const pre = JSON.parse(read('phase57-entry-reserve87-full-source-parity-precommit.json'));
  assert.equal(CONTRACT_SHA256, FIT.frozenContract.sha256);
  assert.deepEqual(FIT.features, FEATURES);
  assert.deepEqual(FIT.target, CONTRACT.target);
  assert.deepEqual(FIT.statePolicy, CONTRACT.statePolicy);
  assert.deepEqual(FIT.featureDefinitions, CONTRACT.featureDefinitions);
  assert.equal(ALLOCATION.sessions.length, 58);
  assert.equal(new Set(ALLOCATION.sessions.map(s=>s.sessionDate)).size, 58);
  assert.deepEqual(ALLOCATION.sessions.map(s=>s.sessionDate), pre.sessions);
  ALLOCATION.sessions.forEach((s,i)=>{
    assert.equal(s.reserveOrdinal, i<29 ? 121+i : 122+i);
    assert.equal(s.sessionId, `RESERVE_${s.reserveOrdinal}`);
    assert.equal(s.purge, false);
    assert.notEqual(s.sessionDate, '2025-11-21');
  });
  assert.equal(ALLOCATION.outcomesViewedAtCreation, false);
  for (const obj of [FIT, ALLOCATION]) assert(Object.values(obj.safety).every(v=>v===false));
  assert.equal(FIT.freshValidationAllowed, false);
  assert.equal(FIT.freshOosAllowed, false);
  const evaluated = new Set();
  FIT.cv.folds.forEach(f=>{
    assert(f.train[0]===0 && f.train[1]<f.embargo[0] && f.embargo[0]<f.evaluate[0]);
    for(let i=f.evaluate[0]; i<=f.evaluate[1]; i++){
      assert(i<58 && !evaluated.has(i)); evaluated.add(i);
    }
  });
  assert.equal(evaluated.size, 28);
  return {allocationSha256:ALLOCATION_SHA, fitSha256:FIT_SHA, featureTargetStateSha256:CONTRACT_SHA256};
}

export function foldSessions(index) {
  verifyDevelopmentContracts();
  const f=FIT.cv.folds[index]; assert(f, 'UNKNOWN_FOLD');
  const range=r=>ALLOCATION.sessions.slice(r[0],r[1]+1).map(s=>s.sessionDate);
  return {train:range(f.train), evaluate:range(f.evaluate), embargo:f.embargo.map(i=>ALLOCATION.sessions[i].sessionDate)};
}

// General offline numerical solver. This does not open datasets, score live markets,
// authorize validation, or create an artifact accepted by the research state engine.
export function solveWeightedLogistic(x, y, weights) {
  const n=x.length, p=10;
  assert(n>0 && y.length===n && weights.length===n, 'INVALID_TRAINING_SHAPE');
  assert(x.every(r=>r.length===p && r.every(Number.isFinite)), 'MISSING_FEATURE');
  assert(y.every(v=>v===0||v===1) && new Set(y).size===2, 'BOTH_CLASSES_REQUIRED');
  assert(weights.every(w=>Number.isFinite(w)&&w>0), 'INVALID_WEIGHTS');
  const mass=weights.reduce((a,b)=>a+b,0), w=weights.map(v=>v/mass);
  const means=Array.from({length:p},(_,j)=>x.reduce((s,r,i)=>s+w[i]*r[j],0));
  const scales=means.map((m,j)=>Math.sqrt(x.reduce((s,r,i)=>s+w[i]*(r[j]-m)**2,0))||1);
  const z=x.map(r=>[1,...r.map((v,j)=>(v-means[j])/scales[j])]);
  const sigmoid=v=>v>=0?1/(1+Math.exp(-v)):Math.exp(v)/(1+Math.exp(v));
  const loss=b=>z.reduce((s,r,i)=>{
    const a=r.reduce((v,q,j)=>v+q*b[j],0);
    return s+w[i]*(Math.max(a,0)-y[i]*a+Math.log1p(Math.exp(-Math.abs(a))));
  },FIT.model.l2Lambda/2*b.slice(1).reduce((s,v)=>s+v*v,0));
  let b=Array(p+1).fill(0);
  for(let iteration=0;iteration<FIT.model.maxIterations;iteration++){
    const g=Array(p+1).fill(0), h=Array.from({length:p+1},()=>Array(p+1).fill(0));
    z.forEach((r,i)=>{
      const pr=sigmoid(r.reduce((s,v,j)=>s+v*b[j],0));
      for(let j=0;j<=p;j++){
        g[j]+=w[i]*(pr-y[i])*r[j];
        for(let k=0;k<=p;k++)h[j][k]+=w[i]*pr*(1-pr)*r[j]*r[k];
      }
    });
    for(let j=1;j<=p;j++){g[j]+=FIT.model.l2Lambda*b[j];h[j][j]+=FIT.model.l2Lambda;}
    if(Math.max(...g.map(Math.abs))<=FIT.model.gradientInfinityTolerance)
      return {weights:b.slice(1),intercept:b[0],means,scales,iterations:iteration,converged:true,objective:loss(b)};
    const a=h.map((r,i)=>[...r,g[i]]);
    for(let j=0;j<=p;j++){
      let pivot=j;for(let k=j+1;k<=p;k++)if(Math.abs(a[k][j])>Math.abs(a[pivot][j]))pivot=k;
      assert(Math.abs(a[pivot][j])>1e-14, 'SINGULAR_HESSIAN');
      [a[j],a[pivot]]=[a[pivot],a[j]];
      const d=a[j][j];for(let k=j;k<=p+1;k++)a[j][k]/=d;
      for(let i=0;i<=p;i++)if(i!==j){const q=a[i][j];for(let k=j;k<=p+1;k++)a[i][k]-=q*a[j][k];}
    }
    const delta=a.map(r=>r[p+1]), descent=g.reduce((s,v,j)=>s+v*delta[j],0), old=loss(b);
    let step=1, accepted=false;
    for(let k=0;k<FIT.model.backtracking.maxSteps;k++){
      const next=b.map((v,j)=>v-step*delta[j]);
      if(loss(next)<=old-FIT.model.backtracking.armijo*step*descent){b=next;accepted=true;break;}
      step*=FIT.model.backtracking.multiplier;
    }
    assert(accepted, 'OPTIMIZER_LINE_SEARCH_FAILED');
  }
  throw Error('OPTIMIZER_NOT_CONVERGED');
}

export function verifyFrozenRow(row) {
  const {featureSha256,...core}=row;
  assert.equal(sha256(core),featureSha256,'FEATURE_BYTES_CHANGED');
  assert.equal(row.contractSha256,CONTRACT_SHA256);
  assert(ALLOCATION.sessions.some(s=>s.sessionDate===row.sessionDate),'SESSION_NOT_ALLOCATED');
  assert(Number.isFinite(Date.parse(row.latestAvailableAt)) && Date.parse(row.latestAvailableAt)<=Date.parse(row.decisionTimestamp),'FUTURE_FEATURE');
  assert.deepEqual(Object.keys(row.features),FEATURES);
  assert(FEATURES.every(k=>Number.isFinite(row.features[k])));
  return true;
}
