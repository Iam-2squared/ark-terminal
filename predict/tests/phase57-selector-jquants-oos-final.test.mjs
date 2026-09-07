import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';
import {gzipSync} from 'node:zlib';

import {evaluateOosShard} from '../../scripts/evaluate_phase57_selector_jquants_oos_shard.mjs';
import {summarizeOos} from '../../scripts/summarize_phase57_selector_jquants_oos.mjs';

const allocation=JSON.parse(fs.readFileSync(new URL('../research/phase57-selector-jquants-fresh120-allocation.json',import.meta.url),'utf8'));
const release=JSON.parse(fs.readFileSync(new URL('../research/phase57-selector-minimal-hybrid-oos-release.json',import.meta.url),'utf8'));
const model=JSON.parse(fs.readFileSync(new URL('../research/phase57-selector-minimal-hybrid-development-model.json',import.meta.url),'utf8'));
const freeze=JSON.parse(fs.readFileSync(new URL('../research/phase57-selector-minimal-hybrid-development-freeze.json',import.meta.url),'utf8'));
const validationPath=new URL('../research/phase57-selector-minimal-hybrid-fresh-validation.json',import.meta.url);
const targets=value=>Object.fromEntries([1,2,3,6,12].map(horizon=>[horizon,{status:'TARGET_READY',upExcursion:value*horizon/12,downExcursion:value*0.8*horizon/12,twoSidedOpportunity:value*horizon/12,finalCloseReturn:value*0.2*horizon/12}]));

test('OOS shard requires the frozen integrity gate and never touches reserve',async()=>{
  const root=fs.mkdtempSync(path.join(os.tmpdir(),'phase57-oos-shard-'));
  try{
    fs.writeFileSync(path.join(root,'gate.json'),JSON.stringify({status:'UNTOUCHED_OOS_INTEGRITY_PASS',gateSha256:'gate',reserveSessionsTouched:0}));
    fs.writeFileSync(path.join(root,'model.json'),JSON.stringify(model));
    fs.writeFileSync(path.join(root,'freeze.json'),JSON.stringify(freeze));
    fs.writeFileSync(path.join(root,'oosAudits.json'),JSON.stringify(allocation.untouchedOos.map(sessionDate=>({sessionDate,fold:'UNTOUCHED_OOS'}))));
    const result=await evaluateOosShard({apiKey:'fixture',inputRoot:root,shardIndex:0,shardCount:3,evaluate:async({date})=>({records:[{sessionDate:date}],points:[{sessionDate:date}],structuralHashesVerified:true})});
    assert.equal(result.status,'FROZEN_SELECTORS_UNTOUCHED_OOS_SHARD_COMPLETE');
    assert.equal(result.dates.length,8);
    assert.equal(result.modelDigest,release.expectedModelDigest);
    assert.equal(result.freezeSha256,release.expectedHybridFreezeSha256);
    assert.equal(result.modelMutationPerformed,false);
    assert.equal(result.validationRetuningPerformed,false);
    assert.equal(result.reserveSessionsTouched,0);
    assert.ok(Object.values(result.safety).every(value=>value===false));
  }finally{fs.rmSync(root,{recursive:true,force:true});}
});

test('OOS summary compares all frozen selectors and separates opportunity from early detection',()=>{
  const root=fs.mkdtempSync(path.join(os.tmpdir(),'phase57-oos-summary-'));
  try{
    for(let shard=0;shard<3;shard+=1){
      const directory=path.join(root,`shard-${shard}`);fs.mkdirSync(directory);
      const dates=allocation.untouchedOos.filter((_,index)=>index%3===shard),points=[],records=[];
      for(const date of dates)for(let cutoff=0;cutoff<20;cutoff+=1){
        const featureCutoff=new Date(`${date}T${String(1+Math.floor(cutoff/12)).padStart(2,'0')}:${String((cutoff*5)%60).padStart(2,'0')}:00.000Z`).toISOString();
        points.push({sessionDate:date,featureCutoff,selectedCounts:{V1:2,V3:1,HYBRID:1}});
        for(const [selector,count,value,preMove] of [['V1',2,0.012,0.02],['V3',1,0.01,0.001],['HYBRID',1,0.014,0.02]])for(let rank=1;rank<=count;rank+=1)records.push({sessionDate:date,featureCutoff,symbol:`${selector}${rank}`,selector,rank,score:0.8,v1Rank:selector==='HYBRID'?rank:null,preSelectionMove:preMove,targetsByHorizon:targets(value)});
      }
      const write=(name,rows)=>fs.writeFileSync(path.join(directory,`${name}.ndjson.gz`),gzipSync(rows.map(JSON.stringify).join('\n')+'\n'));
      write('oos-points',points);write('oos-records',records);
      fs.writeFileSync(path.join(directory,'oos-shard.json'),JSON.stringify({dates,modelDigest:release.expectedModelDigest,freezeSha256:release.expectedHybridFreezeSha256,integrityGateSha256:'gate',validationRetuningPerformed:false,modelMutationPerformed:false,reserveSessionsTouched:0}));
    }
    const report=summarizeOos({inputRoot:root,validationPath});
    assert.equal(report.status,'FROZEN_SELECTORS_UNTOUCHED_OOS_COMPLETE');
    assert.equal(report.oosSessions,24);
    assert.equal(report.leaders.oosOpportunityLeader,'HYBRID');
    assert.equal(report.leaders.earlyDetectionLeader,'V3');
    assert.equal(report.leaders.overallSelectorCandidate,'NO_SINGLE_OVERALL_CANDIDATE_OPPORTUNITY_EARLY_TRADEOFF');
    assert.equal(report.selectors.HYBRID.sessionDispersion.positiveSessionRate,1);
    assert.equal(report.release.reserveReleased,false);
    assert.equal(report.release.reserveSessionsTouched,0);
    assert.equal(report.release.reserveSessionsRemaining,282);
    assert.equal(report.claims.productionReadyAllowed,false);
    assert.ok(Object.values(report.safety).every(value=>value===false));
  }finally{fs.rmSync(root,{recursive:true,force:true});}
});
