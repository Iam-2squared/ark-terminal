import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';
import {gzipSync} from 'node:zlib';

import {summarizeValidation} from '../../scripts/summarize_phase57_selector_jquants_validation.mjs';

const allocation=JSON.parse(fs.readFileSync(new URL('../research/phase57-selector-jquants-fresh120-allocation.json',import.meta.url),'utf8'));
const targets=value=>Object.fromEntries([1,2,3,6,12].map(horizon=>[horizon,{status:'TARGET_READY',upExcursion:value*horizon/12,downExcursion:value*0.8*horizon/12,twoSidedOpportunity:value*horizon/12,finalCloseReturn:value*0.2*horizon/12}]));

test('Validation summary names only a Validation leader and keeps OOS sealed',()=>{
  const root=fs.mkdtempSync(path.join(os.tmpdir(),'phase57-validation-'));
  try{
    for(let shard=0;shard<3;shard+=1){
      const directory=path.join(root,`shard-${shard}`);fs.mkdirSync(directory);
      const dates=allocation.validation.filter((_,index)=>index%3===shard),points=[],records=[];
      for(const date of dates)for(let cutoff=0;cutoff<20;cutoff+=1){
        const featureCutoff=new Date(`${date}T${String(1+Math.floor(cutoff/12)).padStart(2,'0')}:${String((cutoff*5)%60).padStart(2,'0')}:00.000Z`).toISOString();
        points.push({sessionDate:date,featureCutoff,selectedCounts:{V1:2,V3:1,HYBRID:1}});
        for(const [selector,count,value] of [['V1',2,0.012],['V3',1,0.01],['HYBRID',1,0.014]])for(let rank=1;rank<=count;rank+=1)records.push({sessionDate:date,featureCutoff,symbol:`${selector}${rank}`,selector,rank,score:0.8,v1Rank:selector==='HYBRID'?rank:null,preSelectionMove:0.002,targetsByHorizon:targets(value)});
      }
      const write=(name,rows)=>fs.writeFileSync(path.join(directory,`${name}.ndjson.gz`),gzipSync(rows.map(JSON.stringify).join('\n')+'\n'));
      write('validation-points',points);write('validation-records',records);
      fs.writeFileSync(path.join(directory,'validation-shard.json'),JSON.stringify({dates,modelDigest:'m',freezeSha256:'f'}));
    }
    const result=summarizeValidation({inputRoot:root});
    assert.equal(result.status,'FROZEN_SELECTORS_VALIDATION_COMPLETE');
    assert.equal(result.validationLeader.status,'VALIDATION_LEADER');
    assert.equal(result.validationLeader.selector,'HYBRID');
    assert.equal(result.claims.finalWinnerAllowed,false);
    assert.equal(result.release.untouchedOosReleased,false);
    assert.equal(result.release.untouchedOosPayloadRequested,false);
    assert.ok(Object.values(result.safety).every(value=>value===false));
  }finally{fs.rmSync(root,{recursive:true,force:true});}
});
