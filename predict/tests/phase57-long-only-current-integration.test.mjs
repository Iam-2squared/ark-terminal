import test from 'node:test';
import assert from 'node:assert/strict';
import {
  LONG_ONLY_CURRENT_INTEGRATION_CONTRACT,selectCurrentSelectorCandidates,buildCurrentEntryTrainingRows,
  applyCurrentEntryLongOnly,replayCurrentExitLongOnly,
} from '../long-only/phase57-long-only-current-integration.js';

const sessionDate='2024-11-11';
const bars=[];
for(let symbolIndex=0;symbolIndex<6;symbolIndex++)for(let index=0;index<18;index++){
  const total=9*60+5*(index+1),time=`${String(Math.floor(total/60)).padStart(2,'0')}:${String(total%60).padStart(2,'0')}`,price=100+symbolIndex+index*.1;
  bars.push({sessionDate,symbol:String(10000+symbolIndex),availableAtJst:`${sessionDate}T${time}:00+09:00`,open:price-.05,high:price+.1,low:price-.1,close:price,volume:1000+symbolIndex*100,turnover:price*(1000+symbolIndex*100)});
}

function feature(symbolIndex){
  return {sessionDate,symbol:String(10000+symbolIndex),segment:'PRIME',sector:`S${symbolIndex%2}`,decisionTimeJst:'09:30',decisionAtJst:`${sessionDate}T09:30:00+09:00`,currentPrice:100+symbolIndex+.5,currentReturnPct:symbolIndex,momentum30Pct:symbolIndex,vwapDistancePct:symbolIndex/2,vwapSlope15Pct:.1,cumulativeVolume:10000+symbolIndex*1000,cumulativeTurnover:1e7+symbolIndex*1e6,volumeAccelerationRatio:1+symbolIndex/10,causalAtr:.2};
}

test('current selector adapter uses causal fields and returns no outcome fields',()=>{
  const selected=selectCurrentSelectorCandidates(Array.from({length:6},(_,i)=>feature(i)));
  assert.ok(selected.length>0);assert.ok(selected.length<=LONG_ONLY_CURRENT_INTEGRATION_CONTRACT.currentSelectorCapacity);
  assert.ok(selected.every(row=>!Object.keys(row).some(name=>/future|winner|outcome/i.test(name))));
});

test('CURRENT Entry adapter is LONG-only and CURRENT EXIT remains read-only',()=>{
  const candidates=[feature(0)],training=buildCurrentEntryTrainingRows({candidateRows:candidates,bars5m:bars});
  assert.ok(training[1].length===1);assert.ok(training[3].length===1);
  const adapter={picked:{horizonBars:1,threshold:.55,featureKeys:['returnFromOpen']},artifactSha256:'a'.repeat(64),model:{predict:()=>.8}};
  const entry=applyCurrentEntryLongOnly({candidateRows:candidates,bars5m:bars,adapter});
  assert.equal(entry.accepted.length,1);assert.equal(entry.shortTrades,0);assert.equal(entry.marginTrades,0);assert.equal(entry.leverage,0);
  const trades=replayCurrentExitLongOnly({entries:entry.accepted,bars5m:bars});
  assert.equal(trades.length,1);assert.equal(trades[0].signalDirection,1);assert.ok(Number.isFinite(trades[0].netReturnPct));
});
