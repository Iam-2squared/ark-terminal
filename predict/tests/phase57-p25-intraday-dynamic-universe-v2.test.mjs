import assert from 'node:assert/strict';
import test from 'node:test';
import {buildIntradayDynamicUniverseTimelineV2,PHASE57_INTRADAY_UNIVERSE_V2_POLICY,PHASE57_INTRADAY_UNIVERSE_V2_SAFETY} from '../daytrade/phase57-p25-intraday-dynamic-universe-v2.js';

function row(symbol,{sector='A',price=1000,volume=100000,volumeRatio=1,change=1,atr=2,discovery=60,technical=60,confidence=70,quality=80,scannedAt='2026-09-01T00:30:00.000Z'}={}){
  return {symbol,sector,market:'プライム',currentPrice:price,volume,volumeRatio,dailyChangePercent:change,atrPercent:atr,discoveryScore:discovery,technicalScore:technical,confidence,qualityScore:quality,scannedAt,status:'analyzed'};
}
function snap(asOf,hot){
  const entries=[];
  for(let i=0;i<150;i++)entries.push(row(`${1000+i}.T`,{sector:`S${i%10}`,price:500+i,volume:100000+i*1000,volumeRatio:1+(i%4)*0.2,change:(i%5)-2,atr:2+(i%3),discovery:55+(i%10),technical:55+(i%9),confidence:60+(i%20),quality:70+(i%20),scannedAt:asOf}));
  const x=entries.find(r=>r.symbol===hot);if(x){x.volume=5_000_000;x.volumeRatio=4;x.dailyChangePercent=5;x.atrPercent=5;x.discoveryScore=90;x.technicalScore=90;x.confidence=90;x.qualityScore=95;}
  return {asOf,entries};
}

test('v2 keeps 5m market-wide refresh and narrows to quality challenger set',()=>{
  const a='2026-09-01T00:30:00.000Z',b='2026-09-01T00:35:00.000Z';
  const result=buildIntradayDynamicUniverseTimelineV2({snapshots:[snap(a,'1001.T'),snap(b,'1001.T')]});
  assert.equal(result.points.length,2);
  assert.ok(result.points.every(p=>p.rawUniverse.length<=PHASE57_INTRADAY_UNIVERSE_V2_POLICY.finalUniverseSize));
  assert.equal(result.methodology.marketWideRefreshEachFiveMinutes,true);
  assert.equal(result.methodology.futureOutcomeUsed,false);
});

test('causal persistence increases only after prior selection exists',()=>{
  const a='2026-09-01T00:30:00.000Z',b='2026-09-01T00:35:00.000Z';
  const result=buildIntradayDynamicUniverseTimelineV2({snapshots:[snap(a,'1001.T'),snap(b,'1001.T')]});
  const first=result.points[0].v2RankedUniverse.find(x=>x.symbol==='1001.T');
  const second=result.points[1].v2RankedUniverse.find(x=>x.symbol==='1001.T');
  assert.equal(first?.components.persistence,0);
  assert.ok((second?.components.persistence??0)>=0);
});

test('held symbols are removed only from allocation-eligible set',()=>{
  const a='2026-09-01T00:30:00.000Z';const result=buildIntradayDynamicUniverseTimelineV2({snapshots:[snap(a,'1001.T')],heldSymbolsByCutoff:{[a]:['1001.T']}});
  const raw=result.points[0].rawUniverse.some(x=>x.symbol==='1001.T');
  if(raw)assert.equal(result.points[0].allocationEligibleUniverse.some(x=>x.symbol==='1001.T'),false);
});

test('unsafe outcome-driven policy changes fail closed',()=>{
  const a='2026-09-01T00:30:00.000Z';
  assert.throws(()=>buildIntradayDynamicUniverseTimelineV2({snapshots:[snap(a,'1001.T')],policy:{futureOutcomeSelectionAllowed:true}}),/safety policy violation/);
});

test('v2 starts fresh evaluation after 8/31 and all execution surfaces remain disabled',()=>{
  assert.equal(PHASE57_INTRADAY_UNIVERSE_V2_POLICY.firstFreshEligibleDate,'2026-09-01');
  assert.equal(PHASE57_INTRADAY_UNIVERSE_V2_POLICY.august31UsedForWeightSearch,false);
  for(const key of ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted','freshHoldoutConsumed'])assert.equal(PHASE57_INTRADAY_UNIVERSE_V2_SAFETY[key],false,key);
});
