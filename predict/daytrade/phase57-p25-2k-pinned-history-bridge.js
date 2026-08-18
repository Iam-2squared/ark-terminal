export const PHASE57_P25_2K_SAFETY=Object.freeze({
  phase:'57.p25.2k.pinned-history-bridge',
  mode:'READ_ONLY_PINNED_P24_YAHOO_HISTORY_BRIDGE',
  researchOnly:true,
  executionAllowed:false,
  brokerWriteAllowed:false,
  excelOrderWriteAllowed:false,
  rssOrderFunctionAllowed:false,
  liveTradingAllowed:false,
  paperTradingAllowed:false,
  automaticPromotionAllowed:false,
  productionUpdateAllowed:false,
  transmitted:false,
  freshHoldoutConsumed:false,
});

export const PHASE57_P25_2K_POLICY=Object.freeze({
  canonicalSourceRunId:31785422471,
  canonicalArtifactName:'phase57-p24-9-oos-canonical-candidate',
  canonicalSnapshotSha256:'10ec0b89893823f9e2f7ba720db2d0fad8e76d642fe00f7b77d387ae6be6b12a',
  canonicalDataEndIso:'2026-08-12T06:30:00.000Z',
  canonicalWindowDays:56,
  historicalUniverse:Object.freeze(['7203.T','6758.T','9984.T','8306.T','8035.T']),
  minimumBarsPerSymbolSession:30,
  provider:'YAHOO_FINANCE_5M_PINNED_BYTE_SNAPSHOT',
  dailyMarketSpeedRequired:false,
  freshHoldoutConsumed:false,
});

const JST=new Intl.DateTimeFormat('en-CA',{
  timeZone:'Asia/Tokyo',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hourCycle:'h23',
});
const finite=value=>value!==null&&value!==undefined&&value!==''&&Number.isFinite(Number(value));
function jst(timestampMs){
  const parts=Object.fromEntries(JST.formatToParts(new Date(timestampMs)).map(x=>[x.type,x.value]));
  return {date:`${parts.year}-${parts.month}-${parts.day}`,hm:`${parts.hour}:${parts.minute}`};
}
function symbolFromUrl(url){
  try{
    const path=new URL(url).pathname.split('/').filter(Boolean);
    const index=path.indexOf('chart');
    return index>=0&&path[index+1]?decodeURIComponent(path[index+1]).toUpperCase():null;
  }catch{return null;}
}

export function assertP252PinnedP24SnapshotIdentity({snapshot,snapshotSha256}={}){
  if(String(snapshotSha256??'').toLowerCase()!==PHASE57_P25_2K_POLICY.canonicalSnapshotSha256)throw new Error('P25.2K canonical snapshot SHA-256 mismatch');
  if(snapshot?.phase!=='57.p24.9-oos-byte-snapshot')throw new Error('P25.2K canonical snapshot phase mismatch');
  if(snapshot?.dataEndIso!==PHASE57_P25_2K_POLICY.canonicalDataEndIso)throw new Error('P25.2K canonical data end mismatch');
  if(Number(snapshot?.canonicalWindowDays)!==PHASE57_P25_2K_POLICY.canonicalWindowDays)throw new Error('P25.2K canonical window mismatch');
  const symbols=(Array.isArray(snapshot?.symbols)?snapshot.symbols:[]).map(String).sort();
  const expected=[...PHASE57_P25_2K_POLICY.historicalUniverse].sort();
  if(symbols.length!==expected.length||!symbols.every((x,i)=>x===expected[i]))throw new Error('P25.2K canonical historical universe mismatch');
  if(snapshot?.methodology?.performanceObservedBeforeFreeze!==false||snapshot?.methodology?.canonicalWindowChosenBeforePerformance!==true||snapshot?.methodology?.freshHoldoutConsumed!==false)throw new Error('P25.2K canonical methodology attestation mismatch');
  return true;
}

/**
 * Extract the same five-symbol / 5m provider material frozen before P24 performance
 * observation into the historical session shape consumed by the prospective P21
 * scorer. Duplicate query1/query2 responses are de-duplicated by symbol+timestamp.
 */
export function extractP252HistoricalSessionsFromP24Snapshot({snapshot}={}){
  if(!snapshot||typeof snapshot!=='object'||!snapshot.responses||typeof snapshot.responses!=='object')throw new TypeError('P24 byte snapshot responses are required');
  const startMs=Date.parse(snapshot.effectiveStartIso??'');
  const endMs=Date.parse(snapshot.dataEndIso??'');
  if(!Number.isFinite(startMs)||!Number.isFinite(endMs)||startMs>=endMs)throw new Error('invalid P24 canonical snapshot time bounds');
  const barsBySymbol=new Map();
  const responseErrors=[];
  for(const [url,response] of Object.entries(snapshot.responses)){
    const symbol=symbolFromUrl(url)??symbolFromUrl(response?.providerSourceUrl??'');
    if(!symbol)continue;
    if(Number(response?.status)!==200||typeof response?.body!=='string'){
      responseErrors.push(`${symbol}:${response?.status??'NO_STATUS'}`);
      continue;
    }
    let payload;
    try{payload=JSON.parse(response.body);}catch(error){throw new Error(`invalid pinned Yahoo response body for ${symbol}: ${error?.message??error}`);}
    const result=payload?.chart?.result?.[0];
    if(!result)continue;
    const timestamps=Array.isArray(result.timestamp)?result.timestamp:[],quote=result.indicators?.quote?.[0]??{};
    if(!barsBySymbol.has(symbol))barsBySymbol.set(symbol,new Map());
    const target=barsBySymbol.get(symbol);
    for(let i=0;i<timestamps.length;i+=1){
      const ms=Number(timestamps[i])*1000;
      if(!Number.isFinite(ms)||ms<startMs||ms>endMs)continue;
      const {date,hm}=jst(ms);
      if(hm<'09:00'||hm>'15:30')continue;
      const values=[quote.open?.[i],quote.high?.[i],quote.low?.[i],quote.close?.[i]],volume=quote.volume?.[i];
      if(values.some(x=>!finite(x)))continue;
      const [open,high,low,close]=values.map(Number),v=finite(volume)?Number(volume):0;
      if(Math.min(open,high,low,close)<=0||high<low||high<Math.max(open,close)||low>Math.min(open,close)||v<0)continue;
      const timestamp=new Date(ms).toISOString();
      const next={timestamp,open,high,low,close,volume:v,sessionDate:date};
      const previous=target.get(timestamp);
      if(previous&&JSON.stringify(previous)!==JSON.stringify(next))throw new Error(`conflicting duplicate pinned bar for ${symbol} ${timestamp}`);
      target.set(timestamp,next);
    }
  }
  if(responseErrors.length)throw new Error(`non-200 responses in pinned snapshot: ${responseErrors.join(',')}`);

  const expected=PHASE57_P25_2K_POLICY.historicalUniverse;
  const actual=[...barsBySymbol.keys()].sort();
  if(!expected.every(symbol=>actual.includes(symbol)))throw new Error(`pinned snapshot missing historical symbols: ${expected.filter(x=>!actual.includes(x)).join(',')}`);
  const sessions=[];
  for(const symbol of expected){
    const grouped=new Map();
    for(const bar of [...barsBySymbol.get(symbol).values()].sort((a,b)=>a.timestamp.localeCompare(b.timestamp))){
      if(!grouped.has(bar.sessionDate))grouped.set(bar.sessionDate,[]);
      grouped.get(bar.sessionDate).push({timestamp:bar.timestamp,open:bar.open,high:bar.high,low:bar.low,close:bar.close,volume:bar.volume});
    }
    for(const [sessionDate,bars5m] of [...grouped].sort(([a],[b])=>a.localeCompare(b))){
      if(bars5m.length<PHASE57_P25_2K_POLICY.minimumBarsPerSymbolSession)continue;
      sessions.push(Object.freeze({symbol,sessionDate,bars5m:Object.freeze(bars5m.map(x=>Object.freeze(x)))}));
    }
  }
  sessions.sort((a,b)=>a.sessionDate.localeCompare(b.sessionDate)||a.symbol.localeCompare(b.symbol));
  const perSymbol=Object.fromEntries(expected.map(symbol=>[symbol,sessions.filter(x=>x.symbol===symbol).length]));
  if(Object.values(perSymbol).some(n=>n===0))throw new Error('pinned history bridge produced zero usable sessions for a required symbol');
  return Object.freeze({
    phase:'57.p25.2k.pinned-history-bridge',
    status:'PINNED_P24_HISTORY_SESSIONS_READY',
    sessions:Object.freeze(sessions),
    sessionCount:sessions.length,
    perSymbolSessionCount:Object.freeze(perSymbol),
    sourceResponseCount:Object.keys(snapshot.responses).length,
    methodology:Object.freeze({
      provider:PHASE57_P25_2K_POLICY.provider,
      p24CanonicalByteSnapshotOnly:true,
      queryHostDuplicatesDeduplicated:true,
      sameP24RegularSessionFilter:true,
      sameP24MinimumSessionBars:true,
      performanceObservedBeforeFreeze:false,
      currentProspectiveOutcomeUsed:false,
      dailyMarketSpeedRequired:false,
      freshHoldoutConsumed:false,
    }),
    safety:PHASE57_P25_2K_SAFETY,
  });
}

export function buildP252PinnedHistoricalSessions({snapshot,snapshotSha256}={}){
  assertP252PinnedP24SnapshotIdentity({snapshot,snapshotSha256});
  return extractP252HistoricalSessionsFromP24Snapshot({snapshot});
}

export default {buildP252PinnedHistoricalSessions,extractP252HistoricalSessionsFromP24Snapshot,assertP252PinnedP24SnapshotIdentity,PHASE57_P25_2K_POLICY,PHASE57_P25_2K_SAFETY};
