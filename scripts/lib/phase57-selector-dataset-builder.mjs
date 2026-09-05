import {createHash} from 'node:crypto';

export const PHASE57_SELECTOR_DATASET_SAFETY=Object.freeze({
  executionAllowed:false,brokerWriteAllowed:false,excelOrderWriteAllowed:false,
  rssOrderFunctionAllowed:false,liveTradingAllowed:false,paperTradingAllowed:false,
  automaticPromotionAllowed:false,productionUpdateAllowed:false,transmitted:false,
});

const sha=value=>createHash('sha256').update(JSON.stringify(value)).digest('hex');
const symbolOf=value=>String(value??'').trim().toUpperCase();

function assertShard(shard,index){
  if(shard?.phase!=='57.selector-v3.yahoo-5m-shard'||shard?.status!=='SELECTOR_YAHOO_5M_SHARD_READY'){
    throw new Error(`shard[${index}] is not a ready Selector Yahoo 5m shard`);
  }
  for(const [key,value] of Object.entries(PHASE57_SELECTOR_DATASET_SAFETY)){
    if(value===false&&shard?.safety?.[key]!==false)throw new Error(`shard[${index}] safety ${key} must remain false`);
  }
  if(shard?.methodology?.laterFetchedHistoricalReconstruction!==true||shard?.methodology?.exactTradingViewReplay!==false){
    throw new Error(`shard[${index}] reconstruction provenance is invalid`);
  }
  if(!Array.isArray(shard.symbols))throw new Error(`shard[${index}] symbols[] missing`);
}

function sameBar(left,right){
  return ['timestamp','sessionDate','open','high','low','close','volume'].every(key=>left[key]===right[key]);
}

function decisionTimes(){
  const times=[];
  const add=(startHour,startMinute,endHour,endMinute)=>{
    let value=startHour*60+startMinute;
    const end=endHour*60+endMinute;
    while(value<=end){
      times.push(`${String(Math.floor(value/60)).padStart(2,'0')}:${String(value%60).padStart(2,'0')}`);
      value+=5;
    }
  };
  add(9,15,11,0);
  add(12,45,14,30);
  return times;
}

function cutoffIso(sessionDate,time){
  return new Date(`${sessionDate}T${time}:00+09:00`).toISOString();
}

export function buildPhase57SelectorHistoricalDatasetFromShards(shards,{minimumSymbolsPerSession=200}={}){
  if(!Array.isArray(shards)||!shards.length)throw new TypeError('at least one shard is required');
  if(!Number.isInteger(Number(minimumSymbolsPerSession))||Number(minimumSymbolsPerSession)<1)throw new TypeError('minimumSymbolsPerSession must be positive integer');
  shards.forEach(assertShard);
  const merged=new Map();
  for(const shard of shards){
    for(const item of shard.symbols){
      const symbol=symbolOf(item.symbol);
      if(!symbol)throw new Error('shard symbol is missing');
      if(!merged.has(symbol))merged.set(symbol,{
        symbol,sector:String(item.sector??'').trim()||'UNKNOWN',market:item.market??null,
        providerMeta:item.providerMeta??null,bars:new Map(),
      });
      const target=merged.get(symbol);
      if(target.sector!==(String(item.sector??'').trim()||'UNKNOWN')||target.market!==(item.market??null)){
        throw new Error(`conflicting metadata for ${symbol}`);
      }
      for(const bar of item.bars??[]){
        const key=String(bar.timestamp??'');
        if(!key)throw new Error(`${symbol} bar missing timestamp`);
        const previous=target.bars.get(key);
        if(previous&&!sameBar(previous,bar))throw new Error(`conflicting historical bar ${symbol} ${key}`);
        if(!previous)target.bars.set(key,Object.freeze({...bar}));
      }
    }
  }
  const symbols=[...merged.values()].map(item=>Object.freeze({
    symbol:item.symbol,sector:item.sector,market:item.market,providerMeta:item.providerMeta,
    bars:Object.freeze([...item.bars.values()].sort((a,b)=>String(a.timestamp).localeCompare(String(b.timestamp)))),
  })).filter(item=>item.bars.length).sort((a,b)=>a.symbol.localeCompare(b.symbol));
  const allDates=[...new Set(symbols.flatMap(item=>item.bars.map(bar=>bar.sessionDate)))].sort();
  const sessions=[];
  const coverage=[];
  for(const sessionDate of allDates){
    const members=symbols.filter(item=>{
      const current=item.bars.some(bar=>bar.sessionDate===sessionDate);
      const prior=item.bars.some(bar=>bar.sessionDate<sessionDate);
      return current&&prior;
    }).map(item=>item.symbol);
    coverage.push({sessionDate,memberSymbols:members.length});
    if(members.length<Number(minimumSymbolsPerSession))continue;
    sessions.push(Object.freeze({
      sessionDate,
      decisionCutoffs:Object.freeze(decisionTimes().map(time=>cutoffIso(sessionDate,time))),
      memberSymbols:Object.freeze(members),
    }));
  }
  if(sessions.length<30)throw new Error(`only ${sessions.length} sessions meet minimumSymbolsPerSession=${minimumSymbolsPerSession}; at least 30 required`);
  const sourceIdentity=shards.map(shard=>({
    fetchedAt:shard.fetchedAt,range:shard.range,universe:shard.universe,
    readyCount:shard.readyCount,symbolDigest:sha((shard.symbols??[]).map(item=>item.symbol)),
  }));
  const datasetId=`PHASE57_SELECTOR_YAHOO_5M_${sha(sourceIdentity).slice(0,16).toUpperCase()}`;
  return Object.freeze({
    manifest:Object.freeze({
      schemaVersion:1,datasetId,
      evidenceClassification:'SURVIVORSHIP_LIMITED_RECONSTRUCTION',
      universeStatus:'SURVIVORSHIP_LIMITED',
      claimsExactTradingViewReplay:false,
      intervalMinutes:5,barTimestampMeaning:'BAR_OPEN',
      source:'Yahoo Finance chart API later-fetched historical OHLCV',
      constructedAt:new Date().toISOString(),
      sourceIdentity:Object.freeze(sourceIdentity),
      providerTermsStatus:'OPERATOR_VERIFICATION_REQUIRED_BEFORE_SCALE',
      currentUniverseAppliedHistorically:true,
      limitations:Object.freeze([
        'Not an exact TradingView realtime scanner replay',
        'Current JPX metadata applied historically; delistings, new listings, transfers and symbol changes can cause survivorship bias',
        'Historical order book, spread, depth, quote staleness and tick ordering are unavailable',
        'Sparse no-trade intervals are retained as sparse; no OHLC bar is fabricated',
      ]),
      safety:PHASE57_SELECTOR_DATASET_SAFETY,
    }),
    symbols:Object.freeze(symbols),
    sessions:Object.freeze(sessions),
    coverage:Object.freeze(coverage),
  });
}

export default {buildPhase57SelectorHistoricalDatasetFromShards,PHASE57_SELECTOR_DATASET_SAFETY};

