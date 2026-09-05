import assert from 'node:assert/strict';
import test from 'node:test';
import {buildPhase57SelectorHistoricalDatasetFromShards} from '../../scripts/lib/phase57-selector-dataset-builder.mjs';

const SAFETY={
  executionAllowed:false,brokerWriteAllowed:false,excelOrderWriteAllowed:false,
  rssOrderFunctionAllowed:false,liveTradingAllowed:false,paperTradingAllowed:false,
  automaticPromotionAllowed:false,productionUpdateAllowed:false,transmitted:false,
};
const date=index=>new Date(Date.parse('2026-01-01T00:00:00Z')+index*24*60*60_000).toISOString().slice(0,10);
function item(symbol,offset=0){
  return {
    status:'READY',symbol,sector:'TEST',market:'PRIME',
    bars:Array.from({length:31},(_,index)=>({
      timestamp:new Date(`${date(index)}T00:00:00Z`).toISOString(),
      sessionDate:date(index),open:100+offset,high:101+offset,low:99+offset,close:100.5+offset,volume:1000,
    })),
  };
}
function shard(symbols){
  return {
    schemaVersion:1,phase:'57.selector-v3.yahoo-5m-shard',status:'SELECTOR_YAHOO_5M_SHARD_READY',
    fetchedAt:'2026-09-05T00:00:00Z',range:'60d',universe:{sourceDate:'2026-09-05'},
    readyCount:symbols.length,symbols,
    methodology:{laterFetchedHistoricalReconstruction:true,exactTradingViewReplay:false},
    safety:SAFETY,
  };
}

test('shards become a compact global-symbol survivorship-limited dataset',()=>{
  const result=buildPhase57SelectorHistoricalDatasetFromShards([shard([item('1001.T'),item('1002.T',10)])],{minimumSymbolsPerSession:2});
  assert.equal(result.symbols.length,2);
  assert.equal(result.sessions.length,30);
  assert.equal(result.sessions[0].memberSymbols.length,2);
  assert.equal(result.sessions[0].decisionCutoffs.length,44);
  assert.equal(result.manifest.evidenceClassification,'SURVIVORSHIP_LIMITED_RECONSTRUCTION');
  assert.equal(result.manifest.claimsExactTradingViewReplay,false);
  assert.equal(result.manifest.currentUniverseAppliedHistorically,true);
  assert.equal(result.manifest.safety.executionAllowed,false);
});

test('conflicting duplicate symbol bars fail closed',()=>{
  const left=item('1001.T');
  const right=item('1001.T');
  right.bars[0]={...right.bars[0],close:999,high:1000};
  assert.throws(
    ()=>buildPhase57SelectorHistoricalDatasetFromShards([shard([left]),shard([right])],{minimumSymbolsPerSession:1}),
    /conflicting historical bar/,
  );
});

test('insufficient covered sessions cannot be mislabeled large-scale',()=>{
  const short=item('1001.T');
  short.bars=short.bars.slice(0,10);
  assert.throws(
    ()=>buildPhase57SelectorHistoricalDatasetFromShards([shard([short])],{minimumSymbolsPerSession:1}),
    /at least 30 required/,
  );
});

