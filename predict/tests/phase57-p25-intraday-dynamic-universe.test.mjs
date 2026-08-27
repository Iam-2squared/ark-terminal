import assert from 'node:assert/strict';
import test from 'node:test';
import {buildIntradayDynamicUniverseTimeline,PHASE57_INTRADAY_UNIVERSE_SAFETY} from '../daytrade/phase57-p25-intraday-dynamic-universe.js';

function row(symbol,{sector='A',price=1000,volume=100000,volumeRatio=1,change=0,atr=2,discovery=50,technical=50,confidence=50,quality=80,scannedAt='2026-08-27T00:30:00.000Z'}={}){
  return {symbol,sector,market:'プライム',currentPrice:price,volume,volumeRatio,dailyChangePercent:change,atrPercent:atr,discoveryScore:discovery,technicalScore:technical,confidence,qualityScore:quality,scannedAt,status:'analyzed'};
}

function universe({hot='1001.T',asOf='2026-08-27T00:30:00.000Z'}={}){
  const rows=[];
  for(let i=1;i<=160;i+=1){
    const symbol=String(1000+i)+'.T';
    rows.push(row(symbol,{sector:`S${i%8}`,price:500+i,volume:100000+i*1000,volumeRatio:1+(i%5)*0.2,change:(i%7)-3,atr:1+(i%4),discovery:45+(i%11),technical:44+(i%13),confidence:55+(i%20),quality:70+(i%15),scannedAt:asOf}));
  }
  const target=rows.find(x=>x.symbol===hot);
  if(target){target.volume=5_000_000;target.volumeRatio=5;target.dailyChangePercent=7;target.atrPercent=6;target.discoveryScore=90;target.technicalScore=90;target.confidence=90;target.qualityScore=95;}
  return rows;
}

test('refreshes market-wide candidate selection on each unique 5m bucket',()=>{
  const a='2026-08-27T00:30:00.000Z';
  const b='2026-08-27T00:35:00.000Z';
  const first=universe({hot:'1001.T',asOf:a});
  const second=universe({hot:'1002.T',asOf:b});
  const result=buildIntradayDynamicUniverseTimeline({snapshots:[{asOf:a,entries:first},{asOf:b,entries:second}]});
  assert.equal(result.points.length,2);
  assert.equal(result.diagnostics.selectorCalls,2);
  assert.notDeepEqual(result.points[0].rawUniverse.map(x=>x.symbol),result.points[1].rawUniverse.map(x=>x.symbol));
  assert.equal(result.methodology.marketWideRefreshEachFiveMinutes,true);
});

test('same semantic market snapshot is deduplicated even when scan timestamp advances',()=>{
  const a='2026-08-27T00:30:00.000Z';
  const b='2026-08-27T00:35:00.000Z';
  const first=universe({hot:'1001.T',asOf:a});
  const second=first.map(x=>({...x,scannedAt:b}));
  const result=buildIntradayDynamicUniverseTimeline({snapshots:[{asOf:a,entries:first},{asOf:b,entries:second}]});
  assert.equal(result.points.length,2);
  assert.equal(result.diagnostics.selectorCalls,1);
  assert.equal(result.diagnostics.dedupHits,1);
  assert.equal(result.points[1].reusedSelection,true);
  assert.deepEqual(result.points[0].rawUniverse.map(x=>x.symbol),result.points[1].rawUniverse.map(x=>x.symbol));
});

test('only one snapshot per 5m bucket is scored',()=>{
  const a='2026-08-27T00:30:01.000Z';
  const b='2026-08-27T00:34:59.000Z';
  const result=buildIntradayDynamicUniverseTimeline({snapshots:[{asOf:a,entries:universe({asOf:a})},{asOf:b,entries:universe({asOf:b})}]});
  assert.equal(result.points.length,1);
  assert.equal(result.diagnostics.selectorCalls,1);
});

test('held symbols are excluded only at allocation gate without rewriting raw research universe',()=>{
  const asOf='2026-08-27T00:30:00.000Z';
  const result=buildIntradayDynamicUniverseTimeline({snapshots:[{asOf,entries:universe({hot:'1001.T',asOf})}],heldSymbolsByCutoff:{[asOf]:['1001.T']}});
  assert.ok(result.points[0].rawUniverse.some(x=>x.symbol==='1001.T'));
  assert.ok(!result.points[0].allocationEligibleUniverse.some(x=>x.symbol==='1001.T'));
  assert.ok(result.points[0].heldExcludedCount>=1);
});

test('lightweight prescreen reduces rows passed to full selector',()=>{
  const asOf='2026-08-27T00:30:00.000Z';
  const result=buildIntradayDynamicUniverseTimeline({snapshots:[{asOf,entries:universe({asOf})}]});
  assert.equal(result.diagnostics.inputRows,160);
  assert.equal(result.diagnostics.prescreenedRows,120);
  assert.equal(result.diagnostics.averagePrescreenRowsPerSelectorCall,120);
});

test('future outcome fields fail closed',()=>{
  const asOf='2026-08-27T00:30:00.000Z';
  const rows=universe({asOf});
  rows[0]={...rows[0],futureReturnPct:999};
  assert.throws(()=>buildIntradayDynamicUniverseTimeline({snapshots:[{asOf,entries:rows}]}),/forbidden outcome fields/);
});

test('research candidate cannot replace Frozen DYNAMIC_50 or relax Entry threshold',()=>{
  const asOf='2026-08-27T00:30:00.000Z';
  assert.throws(()=>buildIntradayDynamicUniverseTimeline({snapshots:[{asOf,entries:universe({asOf})}],policy:{replaceFrozenDynamic50:true}}),/cannot relax Entry or replace Frozen DYNAMIC_50/);
  assert.throws(()=>buildIntradayDynamicUniverseTimeline({snapshots:[{asOf,entries:universe({asOf})}],policy:{thresholdRelaxationAllowed:true}}),/cannot relax Entry or replace Frozen DYNAMIC_50/);
});

test('all trading and write surfaces remain disabled',()=>{
  for(const key of ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted','freshHoldoutConsumed']){
    assert.equal(PHASE57_INTRADAY_UNIVERSE_SAFETY[key],false,key);
  }
});
