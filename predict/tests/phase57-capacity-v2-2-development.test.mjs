import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {SPEC,PRECOMMIT_SHA,targetRows,fitBundlePast,infer,mapPredictions,applyFrozenPrefix,metrics,developmentGate,evaluateDevelopment,finalArtifact} from '../../scripts/run_phase57_selector_capacity_v2_2.mjs';
import {FEATURES,MODEL_DIGEST,SAFETY,hash,validateRows,auditRows} from '../../scripts/capacity_v22_checkpoint.mjs';
function fixture(){
  return Array.from({length:89},(_,day)=>{
    const date=new Date(Date.UTC(2025,0,day+1)).toISOString().slice(0,10);
    return Array.from({length:20},(_,j)=>({sessionDate:date,featureCutoff:new Date(Date.UTC(2025,0,day+1,0,30+j*5)).toISOString(),
      features:Object.fromEntries(FEATURES.map((k,i)=>[k,(day%7)/10+(j%3)/100+i])),
      availability:Object.fromEntries(FEATURES.map(k=>[k,true])),
      utilityByCapacity:Object.fromEntries(Array.from({length:20},(_,i)=>[i+1,120+i])),
      frozenSelectedUtility:100,frozenSelectedCount:6,rankedCount:30,prefixIdentity:true,modelDigest:MODEL_DIGEST,
      targets:{RANK_6_10:100,RANK_11_15:100,RANK_16_20:100}}));
  }).flat();
}
const rows=fixture(),dates=[...new Set(rows.map(r=>r.sessionDate))];
test('precommit bytes and forbidden releases are fixed',()=>{
  assert.equal(hash(fs.readFileSync(new URL('../research/phase57-selector-capacity-v2-2-precommit.json',import.meta.url))),PRECOMMIT_SHA);
  assert.deepEqual(SPEC.scope.features,FEATURES);assert.deepEqual(SPEC.scope.actions,[0,5,10,15,20]);
  assert.equal(SPEC.release.validation,false);assert.equal(SPEC.release.untouchedOos,false);assert.equal(SPEC.release.sealedReserve,false);
  assert.ok(Object.values(SAFETY).every(v=>v===false));
});
test('relative target uses stored selected baseline, not Top-N substitution or second cost',()=>{
  const r=targetRows(rows.slice(0,1))[0];assert.equal(r.relativeTargets[5],24);assert.notEqual(r.relativeTargets[5],124-125);
  assert.equal(r.relativeTargets[10]-r.relativeTargets[5],r.utilityByCapacity[10]-r.utilityByCapacity[5]);
});
test('null baseline and preserved ABSTAIN produce no fitted labels',()=>{
  const [missing,abstain]=targetRows([{...rows[0],frozenSelectedUtility:null},{...rows[1],frozenSelectedCount:0}]);
  assert.ok(Object.values(missing.relativeTargets).every(v=>v===null));assert.ok(Object.values(abstain.relativeTargets).every(v=>v===null));
});
test('mapping is fixed at -10, largest feasible prefix, no grid',()=>{
  assert.equal(mapPredictions(rows[0],{5:0,10:-9,15:-10,20:-11}),15);
  assert.equal(mapPredictions(rows[0],{5:-11,10:-12,15:-13,20:-14}),5);
  assert.equal(mapPredictions({...rows[0],frozenSelectedCount:0},{20:100}),0);
  assert.equal(mapPredictions({...rows[0],rankedCount:4},{5:100}),0);
});
test('adapter preserves exact same-K symbols and Frozen ABSTAIN',()=>{
  const ranked=Array.from({length:30},(_,i)=>({symbol:'S'+i,hybridRank:i+1})),hybrid={ranked,selected:[ranked[7]],modelDigest:MODEL_DIGEST};
  for(const k of [0,5,10,15,20])assert.deepEqual(applyFrozenPrefix(hybrid,k),ranked.slice(0,k));
  assert.throws(()=>applyFrozenPrefix({...hybrid,selected:[]},5),/ABSTAIN/);
  assert.throws(()=>applyFrozenPrefix({...hybrid,modelDigest:'changed'},5),/MODEL/);
  assert.throws(()=>applyFrozenPrefix(hybrid,7),/ACTION/);
});
test('checkpoint date whitelist rejects sealed dates, duplicates and wrong feature fields',()=>{
  validateRows(rows,dates);
  assert.throws(()=>validateRows([{...rows[0],sessionDate:'2099-01-01'},...rows.slice(1)],dates),/SESSION|SEALED/);
  assert.throws(()=>validateRows([rows[1],...rows.slice(1)],dates),/DUPLICATE/);
  assert.throws(()=>validateRows([{...rows[0],features:{...rows[0].features,futureReturn:1}},...rows.slice(1)],dates),/WHITELIST/);
});
test('semantics audit exposes baseline substitution mismatch',()=>{
  const audit=auditRows(rows);assert.equal(audit.baselineAudit.mismatchDecisions,1780);
  assert.equal(audit.baselineAudit.actualFrozenSelectedUtility,100);assert.equal(audit.baselineAudit.prefixCountUtility,125);
});
test('metric compares equal-session paired support independent of chosen action',()=>{
  const a={...rows[0],action:10},b={...rows[20],action:20,utilityByCapacity:{...rows[20].utilityByCapacity,5:null}};
  const m=metrics([a,b]);assert.equal(m.pairedDecisionCount,1);assert.equal(m.baselineUtility,100);assert.equal(m.utility,129);
  assert.equal(m.count,15);assert.equal(m.baselineCount,6);
});
test('all original numeric gates and every-block floor are enforced',()=>{
  const m={utilityDifference:-10,countRatio:1.25,absoluteIncrease:2,jumpRate:.15,pairedCoverage:1,activeAbstainCount:0};
  const guards={prefixMatch:1,leakageViolations:0,missingFeatures:0};const blocks=Array.from({length:3},()=>({...m}));
  assert.equal(developmentGate(m,blocks,guards).pass,true);
  for(const [key,value] of [['utilityDifference',-10.01],['countRatio',1.24],['absoluteIncrease',1.99],['jumpRate',.151]])assert.equal(developmentGate({...m,[key]:value},blocks,guards).pass,false);
  assert.equal(developmentGate(m,[m,m,{...m,utilityDifference:-14.46}],guards).pass,false);
  assert.equal(developmentGate(m,blocks,{...guards,leakageViolations:1}).pass,false);
});
let reference;
test('nested forward run has only past lambdas and produces a sealed Development freeze on synthetic PASS',()=>{
  reference=evaluateDevelopment(rows);
  assert.equal(reference.developmentDecisions.length,880);assert.equal(reference.gate.pass,true);
  for(const b of reference.blocks)assert.ok(b.lastLambdaOutcomeSession<=b.trainEnd&&b.trainEnd<b.testStart);
  const result=finalArtifact(reference,{synthetic:true});assert.equal(result.status,'READY_FOR_FRESH_VALIDATION');
  assert.equal(result.validationReleased,false);assert.equal(result.untouchedOosReleased,false);assert.equal(result.freezeCreated,true);
});
test('changing all outer outcomes cannot change earlier outer models or predictions',()=>{
  const changed=structuredClone(rows);
  for(const r of changed.slice(45*20)){r.frozenSelectedUtility+=10000;for(const k in r.utilityByCapacity)r.utilityByCapacity[k]-=3000;}
  const result=evaluateDevelopment(changed);
  assert.deepEqual(result.blockModels[0],reference.blockModels[0]);
  assert.deepEqual(result.developmentDecisions.slice(0,300),reference.developmentDecisions.slice(0,300));
});
test('later-block features cannot alter an earlier fit, scale, lambda or mapping',()=>{
  const changed=structuredClone(rows);for(const r of changed.slice(60*20))for(const k of FEATURES)r.features[k]+=100000;
  const result=evaluateDevelopment(changed);
  assert.deepEqual(result.blockModels[0],reference.blockModels[0]);
  assert.deepEqual(result.developmentDecisions.slice(0,300),reference.developmentDecisions.slice(0,300));
});
test('inference rejects labels as inputs and missing features fail closed',()=>{
  const bundle=reference.blockModels[0],r=rows[0];
  assert.throws(()=>infer(bundle,{features:r.features,frozenSelectedCount:6,rankedCount:30,target:99}),/WHITELIST/);
  assert.equal(infer(bundle,{features:{...r.features,marketBreadth:null},frozenSelectedCount:6,rankedCount:30}).action,0);
});
test('synthetic Development FAIL emits NO-GO with no model or release',()=>{
  const bad=rows.map(r=>({...r,frozenSelectedUtility:1000}));const result=evaluateDevelopment(bad);
  assert.equal(result.gate.pass,false);assert.equal(result.model,null);
  const final=finalArtifact(result,{synthetic:true});assert.equal(final.status,'CAPACITY_V2_2_DEVELOPMENT_NO_GO');
  assert.equal(final.freezeCreated,false);assert.equal(final.validationReleased,false);assert.equal(final.untouchedOosReleased,false);
});
test('Gate/model parity prevents disguising a FAIL as a frozen model',()=>{
  assert.throws(()=>finalArtifact({...reference,gate:{pass:false}},{synthetic:true}),/PARITY/);
});
