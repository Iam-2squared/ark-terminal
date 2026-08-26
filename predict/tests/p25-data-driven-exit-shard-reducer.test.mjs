import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {P25_DATA_DRIVEN_PAIRED_SAFETY,summarizeP25DataDrivenPairs} from '../daytrade/phase57-p25-data-driven-exit-multisession.js';

const here=path.dirname(fileURLToPath(import.meta.url));
const reducer=path.resolve(here,'../../scripts/reduce_p25_data_driven_exit_shards.mjs');

function shard(sessionDate,key,fixedNet,dataNet){
  const pair={key,sessionDate,symbol:key.split('|').at(-1),variantMemberships:['DYNAMIC_50'],fixed:{netReturnPct:fixedNet},dataDriven:{netReturnPct:dataNet,barsHeld:3,givebackPct:0.1,captureRatio:0.8},deltaNetReturnPct:dataNet-fixedNet,deltaBarsHeld:0};
  return {schemaVersion:1,phase:'57.p25.data-driven-exit.paired.v1',status:'P25_DATA_DRIVEN_EXIT_PAIRED_EVALUATED',result:{lineageManifestHeadSha256:'lineage-fixed',analogPoolCount:123,sessions:[{sessionDate,dynamic50FrozenCount:1,pairedCount:1,managementBlockedCount:0}],pairs:[pair]},methodology:{exactDynamic50Only:true,resultBasedRetuning:false},safety:P25_DATA_DRIVEN_PAIRED_SAFETY};
}

test('shard reducer deterministically reproduces union summary and preserves guards',()=>{
  const dir=fs.mkdtempSync(path.join(os.tmpdir(),'p25-exit-shards-'));
  const out=path.join(dir,'out.json');
  try{
    const a=shard('2026-08-19','2026-08-19|01:00|1111.T',1.0,0.5);
    const b=shard('2026-08-20','2026-08-20|01:00|2222.T',-0.5,0.25);
    fs.writeFileSync(path.join(dir,'b.json'),JSON.stringify(b));
    fs.writeFileSync(path.join(dir,'a.json'),JSON.stringify(a));
    execFileSync(process.execPath,[reducer,'--input-dir',dir,'--output',out],{stdio:'pipe'});
    const x=JSON.parse(fs.readFileSync(out,'utf8'));
    const expectedPairs=[...a.result.pairs,...b.result.pairs].sort((p,q)=>p.key.localeCompare(q.key));
    assert.deepEqual(x.result.pairs,expectedPairs);
    assert.deepEqual(x.result.summary,summarizeP25DataDrivenPairs(expectedPairs));
    assert.equal(x.result.readySessionCount,2);
    assert.equal(x.result.lineageManifestHeadSha256,'lineage-fixed');
    assert.equal(x.result.analogPoolCount,123);
    assert.equal(x.methodology.shardedComputeOnly,true);
    assert.equal(x.methodology.deterministicReduce,true);
    for(const [k,v] of Object.entries(P25_DATA_DRIVEN_PAIRED_SAFETY)) if(typeof v==='boolean') assert.equal(x.safety[k],v);
  }finally{fs.rmSync(dir,{recursive:true,force:true});}
});

test('shard reducer rejects duplicate pair keys',()=>{
  const dir=fs.mkdtempSync(path.join(os.tmpdir(),'p25-exit-shards-'));
  const out=path.join(dir,'out.json');
  try{
    const a=shard('2026-08-19','dup|01:00|1111.T',1,1);
    const b=shard('2026-08-20','dup|01:00|1111.T',1,1);
    fs.writeFileSync(path.join(dir,'a.json'),JSON.stringify(a));
    fs.writeFileSync(path.join(dir,'b.json'),JSON.stringify(b));
    assert.throws(()=>execFileSync(process.execPath,[reducer,'--input-dir',dir,'--output',out],{stdio:'pipe'}));
  }finally{fs.rmSync(dir,{recursive:true,force:true});}
});
