import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';
import {gzipSync} from 'node:zlib';

import {developHybrid} from '../../scripts/develop_phase57_selector_jquants_hybrid.mjs';
import {PHASE57_MINIMAL_HYBRID_MODEL_FEATURES} from '../daytrade/phase57-selector-minimal-hybrid-model.js';

const allocation=JSON.parse(fs.readFileSync(new URL('../research/phase57-selector-jquants-fresh120-allocation.json',import.meta.url),'utf8'));
const allDates=[...allocation.development,...allocation.purgeDevelopmentValidation,...allocation.validation,...allocation.purgeValidationOos,...allocation.untouchedOos].sort();
const foldOf=date=>allocation.development.includes(date)?'DEVELOPMENT':allocation.validation.includes(date)?'VALIDATION':allocation.untouchedOos.includes(date)?'UNTOUCHED_OOS':'PURGE';

function audit(date){
  const fold=foldOf(date),development=fold==='DEVELOPMENT';
  return {status:'SESSION_STRUCTURAL_AUDIT_PASS',sessionDate:date,fold,pageCount:1,paginationComplete:true,rawMinuteRows:10,normalizedMinuteRows:10,
    regularMinuteRows:10,terminalAuctionRows:0,fiveMinuteBars:2,eligibleJpxSymbolCount:1,exactDuplicateRows:0,timestampConflicts:0,invalidMinuteRows:0,
    lunchViolations:0,futureAvailabilityViolations:0,masterRows:1,masterInvalidRows:0,masterDuplicateCodes:0,minuteSha256:'a'.repeat(64),fiveMinuteSha256:'b'.repeat(64),
    memberSetSha256:'c'.repeat(64),symbolCoverage:[{symbol:'1001.T',fiveMinuteBars:2}],rawPersisted:false,secretPersisted:false,
    featureCalculationPerformed:development,labelGenerationPerformed:development,outcomeInspectionPerformed:false,researchPayloadReleased:development,
    validationReleased:false,untouchedOosReleased:false};
}

function sample(date,index){
  const features=Object.fromEntries(PHASE57_MINIMAL_HYBRID_MODEL_FEATURES.map((name,column)=>[name,Math.sin((index+1)*(column+1)/17)+Math.cos((index+3)/(column+2))]));
  const base=0.001+Math.abs(Math.sin(index/11))*0.01;
  const targetsByHorizon=Object.fromEntries([1,2,3,6,12].map(horizon=>[horizon,{status:'TARGET_READY',upExcursion:base*horizon/12,downExcursion:(base*0.8+Math.abs(Math.cos(index/7))*0.002)*horizon/12,twoSidedOpportunity:base*horizon/12}]));
  return {sessionDate:date,featureCutoff:new Date(`${date}T01:${String(index%60).padStart(2,'0')}:00.000Z`).toISOString(),symbol:`${1001+index%5}.T`,v1Rank:index%5+1,v1BaseScore:0.4+(index%5)/20,features,targetsByHorizon};
}

test('Development pipeline admits compact shards, selects features, trains Ridge, and keeps OOS sealed',()=>{
  const root=fs.mkdtempSync(path.join(os.tmpdir(),'phase57-development-'));
  try{
    for(let shard=0;shard<6;shard+=1){
      const directory=path.join(root,`shard-${shard}`);fs.mkdirSync(directory);
      const sessionAudits=allDates.filter((_,index)=>index%6===shard).map(audit);
      fs.writeFileSync(path.join(directory,'audit.json'),JSON.stringify({shardSha256:String(shard).padStart(64,'0'),sessionAudits}));
      const samples=allocation.development.filter((_,index)=>index%6===shard).flatMap((date,index)=>[sample(date,index*2+shard),sample(date,index*2+shard+1)]);
      fs.writeFileSync(path.join(directory,'development-samples.ndjson.gz'),gzipSync(samples.map(row=>JSON.stringify(row)).join('\n')+'\n'));
    }
    const result=developHybrid({inputRoot:root});
    assert.equal(result.datasetAdmission.status,'MINIMAL_HYBRID_DATASET_ADMITTED_DEVELOPMENT_ONLY');
    assert.equal(result.developmentSummary.status,'MINIMAL_HYBRID_DEVELOPMENT_COMPLETE');
    assert.equal(result.freeze.status,'MINIMAL_HYBRID_FROZEN_BEFORE_VALIDATION');
    assert.equal(result.model.modelFamily,'TWO_INDEPENDENT_RIDGE_REGRESSIONS');
    assert.ok(result.model.featureNames.length<=12);
    assert.equal(result.datasetAdmission.release.validationReleased,false);
    assert.equal(result.datasetAdmission.release.untouchedOosReleased,false);
    assert.equal(result.freeze.untouchedOosReleased,false);
    assert.ok(Object.values(result.freeze.safety).every(value=>value===false));
  }finally{fs.rmSync(root,{recursive:true,force:true});}
});
