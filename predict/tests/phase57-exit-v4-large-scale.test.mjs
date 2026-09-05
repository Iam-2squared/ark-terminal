import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {
  PHASE57_EXIT_V4_LARGE_SCALE_CONTRACT,
  PHASE57_EXIT_V4_LARGE_SCALE_SAFETY,
  assertExitV4PairedIdentity,
  buildExitV4StressProbe,
  buildFrozenExitV4Universe,
  simulateFixedProbeExit,
  summarizeExitV4LargeScale,
} from '../daytrade/phase57-exit-v4-large-scale.js';
import {scoreP25ExitV2StateConditioned} from '../daytrade/phase57-p25-exit-v2-state-conditioned.js';
import {buildExactExitV4AnalogIndex,scoreP25ExitV2ExactIndexed} from '../daytrade/phase57-exit-v4-exact-indexed-replay.js';

const here=path.dirname(fileURLToPath(import.meta.url));
const repoRoot=path.resolve(here,'../..');

function universe(){
  const rows=[];
  for(const [market,count,prefix] of [['プライム',260,'1'],['スタンダード',180,'2'],['グロース',120,'3']]){
    for(let i=0;i<count;i+=1)rows.push({code:`${prefix}${String(i).padStart(3,'0')}`,symbol:`${prefix}${String(i).padStart(3,'0')}.T`,name:`N${i}`,market,sector:`S${i%4}`});
  }
  return rows;
}

function bars(){
  return Array.from({length:61},(_,i)=>{
    const close=100+i*0.1+(i%4===0?-0.2:0);
    return {timestamp:new Date(Date.parse('2026-09-01T00:00:00.000Z')+i*300000).toISOString(),open:close-0.05,high:close+0.2,low:close-0.2,close,volume:1000+i};
  });
}

test('large-scale universe is deterministic, quota-frozen, and nested only by common deterministic ranking',()=>{
  const a=buildFrozenExitV4Universe({universe:universe()}),b=buildFrozenExitV4Universe({universe:universe().reverse()});
  assert.equal(a.manifestSha256,b.manifestSha256);
  assert.equal(a.pilot.length,50);
  assert.equal(a.expansion.length,500);
  assert.deepEqual(Object.fromEntries(Object.entries(Object.groupBy(a.pilot,x=>x.market)).map(([k,v])=>[k,v.length])),{'プライム':24,'スタンダード':16,'グロース':10});
  assert.deepEqual(Object.fromEntries(Object.entries(Object.groupBy(a.expansion,x=>x.market)).map(([k,v])=>[k,v.length])),{'プライム':240,'スタンダード':160,'グロース':100});
  assert.equal(new Set(a.expansion.map(x=>x.symbol)).size,500);
  assert.equal(a.methodology.outcomeBasedUniverseSelection,false);
  assert.equal(a.methodology.analogPoolRefitAllowed,false);
});

test('stress probe uses only predetermined entry state and then freezes exactly 24 future bars',()=>{
  const probe=buildExitV4StressProbe({session:{symbol:'1301.T',sessionDate:'2026-09-01',bars:bars()}});
  assert.equal(probe.ready,true);
  assert.equal(probe.row.entryTimestamp,'2026-09-01T01:30:00.000Z');
  assert.equal(probe.row.contextBars.length,12);
  assert.equal(probe.row.futureBars.length,24);
  assert.equal(probe.row.entryAccepted,true);
  assert.equal(probe.row.frozenBeforeOutcome,true);
  assert.equal(probe.row.currentOutcomeUsed,false);
  const fixed=simulateFixedProbeExit({row:probe.row});
  assert.equal(fixed.barsHeld,24);
  assert.equal(fixed.exitReason,'FIXED_24_BAR_EXIT');
});

test('paired identity fails closed on any non-EXIT mismatch',()=>{
  const common={probeId:'x',symbol:'1301.T',sessionDate:'2026-09-01',entryTimestamp:'t',entryPrice:100,signalDirection:'LONG',marketDataSha256:'h',roundTripCostPct:0.05,allocationUnits:1};
  assert.equal(assertExitV4PairedIdentity({probe:common,v4:{...common},fixed:{...common}}).ready,true);
  assert.throws(()=>assertExitV4PairedIdentity({probe:common,v4:{...common,entryPrice:101},fixed:{...common}}),/entryPrice/);
});

test('summary remains diagnostic-only and safety locks stay false',()=>{
  const result=summarizeExitV4LargeScale([
    {probeId:'a',variant:'V4',netReturnPct:1,barsHeld:2},
    {probeId:'b',variant:'V4',netReturnPct:-0.5,barsHeld:4},
    {probeId:'a',variant:'FIXED_24',netReturnPct:0.2,barsHeld:24},
    {probeId:'b',variant:'FIXED_24',netReturnPct:-0.1,barsHeld:24},
  ]);
  assert.equal(result.pairCount,2);
  assert.equal(result.variants.V4.profitFactor,2);
  assert.equal(PHASE57_EXIT_V4_LARGE_SCALE_CONTRACT.formalOosEvidence,false);
  assert.equal(PHASE57_EXIT_V4_LARGE_SCALE_CONTRACT.currentUniverseSurvivorshipBias,true);
  for(const key of ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted'])assert.equal(PHASE57_EXIT_V4_LARGE_SCALE_SAFETY[key],false,key);
});

test('large-scale scripts are read-only research utilities',()=>{
  const fetcher=fs.readFileSync(path.join(repoRoot,'scripts/fetch_phase57_exit_v4_large_scale_5m_shard.mjs'),'utf8');
  assert.match(fetcher,/fetchP252Yahoo5mSession/);
  assert.match(fetcher,/failedSessionsNeverFabricated:true/);
  assert.doesNotMatch(fetcher,/MarketSpeed|brokerWrite|rssOrderFunction|liveTradingAllowed:true|paperTradingAllowed:true/);
});

test('exact indexed scorer is byte-equivalent to frozen v4 base scoring, including stable ties',()=>{
  const observed=bars().slice(19,27);
  const analogPool=Array.from({length:120},(_,i)=>Object.freeze({
    sessionDate:i%2?'2026-08-11':'2026-08-12',
    fullyRealizedAt:`2026-08-${i%2?'11':'12'}T06:00:00.000Z`,
    direction:'LONG',
    state:Object.freeze({currentReturnPct:i<90?0.2:0.3,bestReturnPct:0.4,givebackPctPoints:0.2,atrPct:0.3,momentumPct:0.1,bodyPressure:0.2,directionalRangePos:0.6,elapsedBars:8}),
    labels:Object.freeze({1:(i%7-3)/100,3:(i%9-4)/100,6:(i%11-5)/100}),
  }));
  const args={entryPrice:observed[0].close,direction:'LONG',observedBars:observed.slice(1),timestamp:'2026-09-01T01:30:00.000Z',sessionDate:'2026-09-01'};
  const original=scoreP25ExitV2StateConditioned({...args,analogPool});
  const indexed=scoreP25ExitV2ExactIndexed({...args,index:buildExactExitV4AnalogIndex(analogPool)});
  assert.deepEqual(indexed,original);
});
