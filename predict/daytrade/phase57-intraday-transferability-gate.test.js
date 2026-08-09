import test from 'node:test';
import assert from 'node:assert/strict';
import { assessContextTransferability, PHASE57_P20_7_SAFETY } from './phase57-intraday-transferability-gate.js';

function row(symbol, regimeLike='up', time='mid'){
  const features={ma5SlopePct:0,ma5DistancePct:0,atrPct:1,isOpening30:0,isLunchReturn:0,isClosing30:0};
  if(regimeLike==='up'){features.ma5SlopePct=1;features.ma5DistancePct=1;features.atrPct=0.5;}
  if(regimeLike==='down'){features.ma5SlopePct=-1;features.ma5DistancePct=-1;features.atrPct=0.5;}
  if(time==='open') features.isOpening30=1;
  if(time==='lunch') features.isLunchReturn=1;
  if(time==='close') features.isClosing30=1;
  return {symbol,features};
}

test('transferability passes when selected context remains structurally present',()=>{
  const selection=Array.from({length:100},(_,i)=>i<50?row('7203.T','up'):row('6758.T','down'));
  const recent=Array.from({length:50},(_,i)=>i<25?row('7203.T','up'):row('6758.T','down'));
  const context={key:'7203.T|TREND_UP|ALL',symbol:'7203.T',regime:'TREND_UP',time:'ALL',atrMedian:1};
  const r=assessContextTransferability(selection,recent,context,{minTransferRecentRows:20,minTransferShareRatio:0.8,maxTransferShareRatio:1.2});
  assert.equal(r.passes,true);
  assert.equal(r.usesLabels,false);
  assert.equal(r.usesOuterTest,false);
});

test('transferability abstains when context prevalence collapses before outer test',()=>{
  const selection=Array.from({length:100},()=>row('7203.T','up'));
  const recent=Array.from({length:50},(_,i)=>i<5?row('7203.T','up'):row('6758.T','down'));
  const context={key:'7203.T|TREND_UP|ALL',symbol:'7203.T',regime:'TREND_UP',time:'ALL',atrMedian:1};
  const r=assessContextTransferability(selection,recent,context,{minTransferRecentRows:5,minTransferShareRatio:0.6,maxTransferShareRatio:1.8});
  assert.equal(r.passes,false);
  assert.ok(r.shareRatio<0.6);
});

test('P20.7 remains research-only with all write paths disabled',()=>{
  assert.equal(PHASE57_P20_7_SAFETY.executionAllowed,false);
  assert.equal(PHASE57_P20_7_SAFETY.brokerWriteAllowed,false);
  assert.equal(PHASE57_P20_7_SAFETY.excelOrderWriteAllowed,false);
  assert.equal(PHASE57_P20_7_SAFETY.rssOrderFunctionAllowed,false);
  assert.equal(PHASE57_P20_7_SAFETY.liveTradingAllowed,false);
  assert.equal(PHASE57_P20_7_SAFETY.paperTradingAllowed,false);
  assert.equal(PHASE57_P20_7_SAFETY.automaticPromotionAllowed,false);
  assert.equal(PHASE57_P20_7_SAFETY.productionUpdateAllowed,false);
});
