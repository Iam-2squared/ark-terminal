import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {createFrozenMainEngine,frozenMainMemberSetSha256,FROZEN_MAIN_POLICY,FROZEN_MAIN_SCHEMA} from '../lib/phase57-frozen-main-engine.mjs';
import {digest} from '../lib/phase57-offline-parity.mjs';

const base=Date.parse('2026-08-13T00:00:00Z');
const at=n=>new Date(base+n*300000).toISOString();
function analogPool(){
  const rows=[];
  for(const direction of ['LONG','SHORT'])for(const currentReturnPct of [-1,1])for(let i=0;i<40;i++)rows.push({sessionDate:'2026-08-12',symbol:`A${i}`,direction,timestamp:'2026-08-12T01:00:00.000Z',fullyRealizedAt:'2026-08-12T02:00:00.000Z',state:{currentReturnPct,elapsedBars:1},labels:{1:-.1,3:-.1,6:-.1}});
  return rows;
}
function bars(symbolIndex,count){
  const rows=[];let price=100+symbolIndex;
  for(let index=0;index<count;index++){
    let factor=1+(symbolIndex%2?-.01:.01)*(1+index/12);
    if(index===12)factor=symbolIndex%2?1.001:.97;
    if(index===13)factor=symbolIndex%2?1.001:1.0206;
    if(index>=14)factor=symbolIndex%2?1.001:1.001;
    const open=price,close=price*factor;price=close;
    rows.push({timestamp:at(index),availableAt:at(index+1),open,high:Math.max(open,close)*1.002,low:Math.min(open,close)*.998,close,volume:1000*(index+1)*(symbolIndex+1)});
  }
  return rows;
}
function point(count){
  const universe=Array.from({length:30},(_,index)=>({sourceCode:String(1000+index),symbol:`${1000+index}.T`,sector:`S${index%4}`,marketCode:'TSE',productCategory:'EQUITY',effectiveAt:'2026-08-12T00:00:00.000Z',bars:bars(index,count)}));
  return {schemaId:FROZEN_MAIN_SCHEMA,captureId:`capture-${count}`,sessionDate:'2026-08-13',timestamp:at(count),sourceClass:'SYNTHETIC_TRANSPORT_TEST',universeComplete:true,masterComplete:true,memberSetSha256:frozenMainMemberSetSha256(universe),universe,health:{connected:true,workbookHealthy:true,stale:false,rssError:false},sessionEnd:false};
}

test('frozen assets are exact and every execution capability stays disabled',()=>{
  assert.equal(FROZEN_MAIN_POLICY.capacity,'MAX_3');
  for(const [key,value] of Object.entries(FROZEN_MAIN_POLICY))if(typeof value==='boolean')assert.equal(value,false,key);
  const entryBytes=fs.readFileSync('predict/research/phase57-msh-entry-v1-model.json');
  assert.equal(digest(entryBytes),'f05def20081e51dfe7391c7e80e8b8474e5c140c42a47dc29dcd94bca367ab8a');
  assert.doesNotThrow(()=>createFrozenMainEngine({analogPool:analogPool()}));
});

test('complete PIT universe reaches selector, First ENTER, V3_B_RISK ledger and causal v4-through-v5 exit',()=>{
  const engine=createFrozenMainEngine({analogPool:analogPool()});let entered=0,exited=0,last;
  for(let count=12;count<=16;count++){
    const output=engine.step(point(count));last=output;
    assert.equal(output.health[0].shadowDecisionAllowed,true);assert.equal(output.health[0].executionDecisionAllowed,false);assert.equal(output.health[0].executionAllowed,false);assert.equal(output.health[0].transmitted,false);
    assert.equal(output.decisions[0].selection.evidence.hybridAllFromV1BroadRecall,true);
    entered+=output.ledger[0].entries.length;exited+=output.ledger[0].exits.length;
    assert.ok(Object.values(output.ledger[0].invariants).every(Boolean));
  }
  const snapshot=engine.snapshot();
  assert.equal(entered,4);assert.equal(exited,4);assert.equal(snapshot.openPositionCount,0);assert.equal(snapshot.ledger.closedTrades.length,4);
  assert.ok(snapshot.ledger.closedTrades.every(x=>x.exitReason==='V4_WINNER_GIVEBACK_CONFIRMED'));
  assert.equal(last.decisions[0].entry.events.some(x=>x.decision.action==='ENTER'),false,'no re-entry after First ENTER');
});

test('incomplete membership, mapping drift, future bars, unhealthy source and order-shaped fields fail closed',()=>{
  const mutations=[
    x=>{x.universeComplete=false;},
    x=>{x.memberSetSha256='0'.repeat(64);},
    x=>{x.universe[0].bars.at(-1).availableAt=at(13);},
    x=>{x.health.stale=true;},
    x=>{x.order={symbol:'1000.T'};},
    x=>{x.universe[0].effectiveAt=at(13);},
  ];
  for(const mutate of mutations){const input=point(12);mutate(input);assert.throws(()=>createFrozenMainEngine({analogPool:analogPool()}).step(input));}
});

test('post-cutoff analog data and nonmonotonic decision points are rejected',()=>{
  const invalid=analogPool();invalid[0]={...invalid[0],sessionDate:'2026-08-13'};
  assert.throws(()=>createFrozenMainEngine({analogPool:invalid}),/ANALOG_POOL_NOT_CAUSAL/);
  const engine=createFrozenMainEngine({analogPool:analogPool()});engine.step(point(12));assert.throws(()=>engine.step(point(12)),/POINT_NONMONOTONIC/);assert.equal(engine.snapshot().halted,true);assert.throws(()=>engine.step(point(13)),/ENGINE_HALTED/);
});

test('historical bar revisions and missing management bars halt the engine',()=>{
  const revised=createFrozenMainEngine({analogPool:analogPool()});revised.step(point(12));const changed=point(13);changed.universe[0].bars[0].close+=1;changed.universe[0].bars[0].high+=1;assert.throws(()=>revised.step(changed),/HISTORICAL_BAR_REVISION/);
  const missing=createFrozenMainEngine({analogPool:analogPool()});missing.step(point(12));const stale=point(13);for(const row of stale.universe)row.bars=row.bars.slice(0,-1);assert.throws(()=>missing.step(stale),/OPEN_POSITION_MANAGEMENT_BAR_MISSING/);
});

test('runner writes a sealed hash-chain journal and immutable channel export',()=>{
  const directory=fs.mkdtempSync(path.join(os.tmpdir(),'ark-frozen-main-'));
  try{
    const input=path.join(directory,'packet.json'),journal=path.join(directory,'journal'),exported=path.join(directory,'export');
    fs.writeFileSync(input,JSON.stringify({schemaId:'ARK_PHASE57_FROZEN_MAIN_PACKET_V1',repoHead:'a'.repeat(40),points:[12,13,14,15,16].map(point),analogPool:analogPool()}));
    const result=JSON.parse(execFileSync(process.execPath,['scripts/phase57-frozen-main-runner.mjs','--input',input,'--journal-dir',journal,'--export-dir',exported],{cwd:process.cwd(),encoding:'utf8'}));
    assert.equal(result.status,'PARTIAL_SHADOW_SESSION');assert.equal(result.report.closedTradeCount,4);assert.equal(result.report.realOrderTransmissionEnabled,false);
    const manifest=JSON.parse(fs.readFileSync(path.join(exported,'manifest.json')));assert.equal(manifest.files.ledger.rows,5);assert.equal(manifest.files.report.rows,1);assert.equal(manifest.realSessionCaptured,false);
    const journalRows=fs.readFileSync(path.join(journal,'session.jsonl'),'utf8').trim().split('\n').map(JSON.parse);assert.equal(journalRows.at(-1).kind,'SEAL');assert.equal(journalRows.length,7);
  }finally{fs.rmSync(directory,{recursive:true,force:true});}
});
