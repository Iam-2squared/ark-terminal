import crypto from 'node:crypto';

export const PHASE57_P25_2J_SAFETY=Object.freeze({
  phase:'57.p25.2j.routine-nonrss-5m-source',
  mode:'READ_ONLY_ROUTINE_NON_BROKER_5M_RESEARCH_SOURCE',
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

export const PHASE57_P25_2J_POLICY=Object.freeze({
  provider:'YAHOO_FINANCE_CHART_5M',
  interval:'5m',
  includePrePost:false,
  regularSessionStartHmJst:'09:00',
  regularSessionEndHmJst:'15:30',
  minimumBarsPerSymbol:30,
  requireWholeFrozenTargetUnion:true,
  dailyMarketSpeedRequired:false,
  excelRequired:false,
  boardOrTickRequired:false,
  microstructureUsed:false,
  providerIsBrokerGroundTruth:false,
  marketSpeedVerificationSeparate:true,
});

const JST=new Intl.DateTimeFormat('en-CA',{
  timeZone:'Asia/Tokyo',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hourCycle:'h23',
});
const finite=value=>value!==null&&value!==undefined&&value!==''&&Number.isFinite(Number(value));
const normalizeSymbol=value=>String(value??'').trim().toUpperCase();
const sha=value=>crypto.createHash('sha256').update(typeof value==='string'?value:JSON.stringify(value)).digest('hex');

function jstParts(timestampMs){
  const parts=Object.fromEntries(JST.formatToParts(new Date(timestampMs)).map(x=>[x.type,x.value]));
  return {date:`${parts.year}-${parts.month}-${parts.day}`,hm:`${parts.hour}:${parts.minute}`};
}

function sessionBounds(sessionDate){
  if(!/^\d{4}-\d{2}-\d{2}$/.test(String(sessionDate??'')))throw new TypeError('sessionDate must be YYYY-MM-DD');
  const start=Date.parse(`${sessionDate}T00:00:00+09:00`);
  if(!Number.isFinite(start))throw new TypeError('invalid sessionDate');
  return {period1:Math.floor(start/1000),period2:Math.floor((start+24*60*60*1000)/1000)};
}

export function buildP252Yahoo5mUrls({symbol,sessionDate}={}){
  const normalized=normalizeSymbol(symbol);
  if(!normalized)throw new TypeError('symbol is required');
  const {period1,period2}=sessionBounds(sessionDate);
  const query=`period1=${period1}&period2=${period2}&interval=5m&includePrePost=false&events=div%2Csplits`;
  return Object.freeze([1,2].map(host=>`https://query${host}.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(normalized)}?${query}`));
}

export function parseP252Yahoo5mSessionPayload({payload,symbol,sessionDate}={}){
  const normalized=normalizeSymbol(symbol);
  if(!normalized)throw new TypeError('symbol is required');
  if(!/^\d{4}-\d{2}-\d{2}$/.test(String(sessionDate??'')))throw new TypeError('sessionDate must be YYYY-MM-DD');
  const result=payload?.chart?.result?.[0];
  if(payload?.chart?.error)throw new Error(`Yahoo chart error for ${normalized}: ${payload.chart.error?.description??'UNKNOWN'}`);
  if(!result)throw new Error(`Yahoo chart result missing for ${normalized}`);
  const timestamps=Array.isArray(result.timestamp)?result.timestamp:[];
  const quote=result.indicators?.quote?.[0]??{};
  const bars=[];
  let droppedInvalid=0,droppedOutsideSession=0;
  for(let index=0;index<timestamps.length;index+=1){
    const epoch=Number(timestamps[index]);
    const values=[quote.open?.[index],quote.high?.[index],quote.low?.[index],quote.close?.[index]];
    const volume=quote.volume?.[index];
    if(!Number.isFinite(epoch)||values.some(v=>!finite(v))||!finite(volume)){droppedInvalid+=1;continue;}
    const timestampMs=epoch*1000,{date,hm}=jstParts(timestampMs);
    if(date!==sessionDate||hm<PHASE57_P25_2J_POLICY.regularSessionStartHmJst||hm>PHASE57_P25_2J_POLICY.regularSessionEndHmJst){droppedOutsideSession+=1;continue;}
    const [open,high,low,close]=values.map(Number),v=Number(volume);
    if(Math.min(open,high,low,close)<=0||high<low||high<Math.max(open,close)||low>Math.min(open,close)||v<0){droppedInvalid+=1;continue;}
    bars.push(Object.freeze({
      timestamp:new Date(timestampMs).toISOString(),
      open,high,low,close,volume:v,
    }));
  }
  bars.sort((a,b)=>a.timestamp.localeCompare(b.timestamp));
  if(new Set(bars.map(x=>x.timestamp)).size!==bars.length)throw new Error(`duplicate Yahoo 5m timestamp for ${normalized}`);
  if(bars.length<PHASE57_P25_2J_POLICY.minimumBarsPerSymbol)throw new Error(`insufficient Yahoo 5m bars for ${normalized}: ${bars.length}`);
  return Object.freeze({
    symbol:normalized,
    sessionDate,
    provider:PHASE57_P25_2J_POLICY.provider,
    interval:'5m',
    bars:Object.freeze(bars),
    sourceQuality:Object.freeze({
      sourceRowCount:timestamps.length,
      acceptedBarCount:bars.length,
      droppedInvalidRowCount:droppedInvalid,
      droppedOutsideRegularSessionCount:droppedOutsideSession,
      exchangeTimezoneName:result?.meta?.exchangeTimezoneName??null,
      dataGranularity:result?.meta?.dataGranularity??null,
    }),
    methodology:Object.freeze({
      yahooTimestampRepresentsFiveMinuteIntervalStart:true,
      completedBarReplayUsesFullSessionOnlyAfterClose:true,
      p24HistoricalSourceParity:'YAHOO_FINANCE_5M',
      brokerGroundTruth:false,
      dailyMarketSpeedRequired:false,
      boardOrTickUsed:false,
    }),
  });
}

export async function fetchP252Yahoo5mSession({symbol,sessionDate,fetchImpl=globalThis.fetch}={}){
  if(typeof fetchImpl!=='function')throw new TypeError('fetchImpl must be a function');
  const urls=buildP252Yahoo5mUrls({symbol,sessionDate});
  const errors=[];
  for(const url of urls){
    try{
      const response=await fetchImpl(url,{headers:{'User-Agent':'Mozilla/5.0 ArkTerminalResearch/1.0','Accept':'application/json'},cache:'no-store'});
      if(!response?.ok)throw new Error(`HTTP ${response?.status??'UNKNOWN'}`);
      const payload=await response.json();
      const parsed=parseP252Yahoo5mSessionPayload({payload,symbol,sessionDate});
      return Object.freeze({...parsed,requestHost:new URL(url).host,sourcePayloadSha256:sha(payload)});
    }catch(error){errors.push(String(error?.message??error));}
  }
  throw new Error(`Yahoo 5m fetch failed for ${normalizeSymbol(symbol)}: ${errors.join(' | ')}`);
}

function targetUnion(record){
  if(record?.ready!==true||!record?.variants)throw new Error('P25.2J requires ready frozen universe record');
  const sessionDate=String(record.sessionDate??'').trim();
  if(!/^\d{4}-\d{2}-\d{2}$/.test(sessionDate))throw new Error('frozen universe sessionDate must be YYYY-MM-DD');
  const expected={FIXED_5:5,OLD_FIXED_30:30,DYNAMIC_30:30,DYNAMIC_40:40,DYNAMIC_50:50};
  const normalized={};
  for(const [variant,count] of Object.entries(expected)){
    const values=record.variants?.[variant];
    if(!Array.isArray(values)||values.length!==count)throw new Error(`${variant} must contain exactly ${count} symbols`);
    const symbols=values.map(normalizeSymbol);
    if(symbols.some(x=>!x)||new Set(symbols).size!==count)throw new Error(`${variant} contains blank or duplicate symbols`);
    normalized[variant]=symbols;
  }
  if(!normalized.DYNAMIC_30.every((x,i)=>normalized.DYNAMIC_40[i]===x)||!normalized.DYNAMIC_40.every((x,i)=>normalized.DYNAMIC_50[i]===x))throw new Error('Dynamic30/40/50 must remain nested prefixes');
  return {sessionDate,symbols:[...new Set(Object.values(normalized).flat())].sort()};
}

/** Collect one complete routine post-close 5m bundle without MARKETSPEED II. */
export async function collectP252Routine5mSession({universeRecord,fetchSession=fetchP252Yahoo5mSession}={}){
  if(typeof fetchSession!=='function')throw new TypeError('fetchSession must be a function');
  const target=targetUnion(universeRecord),sessionBarsBySymbol={},sources={},failures=[];
  for(const symbol of target.symbols){
    try{
      const result=await fetchSession({symbol,sessionDate:target.sessionDate});
      if(!result||result.symbol!==symbol||result.sessionDate!==target.sessionDate||!Array.isArray(result.bars))throw new Error('provider result identity mismatch');
      if(result.bars.length<PHASE57_P25_2J_POLICY.minimumBarsPerSymbol)throw new Error(`provider returned fewer than ${PHASE57_P25_2J_POLICY.minimumBarsPerSymbol} bars`);
      sessionBarsBySymbol[symbol]=result.bars;
      sources[symbol]=Object.freeze({
        provider:result.provider??null,
        requestHost:result.requestHost??null,
        acceptedBarCount:result.bars.length,
        sourcePayloadSha256:result.sourcePayloadSha256??null,
      });
    }catch(error){
      failures.push(Object.freeze({symbol,status:'BLOCKED_ROUTINE_5M_SYMBOL',reason:String(error?.message??error)}));
    }
  }
  const ready=failures.length===0&&Object.keys(sessionBarsBySymbol).length===target.symbols.length;
  return Object.freeze({
    phase:'57.p25.2j.routine-nonrss-5m-source',
    status:ready?'ROUTINE_NONRSS_5M_SESSION_READY':'BLOCKED_ROUTINE_NONRSS_5M_SESSION',
    ready,
    sessionDate:target.sessionDate,
    targetSymbolCount:target.symbols.length,
    collectedSymbolCount:Object.keys(sessionBarsBySymbol).length,
    failedSymbolCount:failures.length,
    failures:Object.freeze(failures),
    sessionBarsBySymbol:Object.freeze(sessionBarsBySymbol),
    sourceBySymbol:Object.freeze(sources),
    sourceProvenance:Object.freeze({
      provider:PHASE57_P25_2J_POLICY.provider,
      interval:'5m',
      routineResearchOnly:true,
      providerIsBrokerGroundTruth:false,
      dailyMarketSpeedRequired:false,
      marketSpeedVerificationSeparate:true,
      targetUnionFingerprint:sha(target.symbols),
    }),
    methodology:Object.freeze({
      wholeFrozenTargetUnionRequired:true,
      failedSymbolBlocksWholeSession:true,
      fullSessionCollectedPostClose:true,
      laterP25ReplayMustPassOnlyPrefixToScorer:true,
      boardOrTickUsed:false,
      microstructureUsed:false,
      freshHoldoutConsumed:false,
    }),
    safety:PHASE57_P25_2J_SAFETY,
  });
}

export default {collectP252Routine5mSession,fetchP252Yahoo5mSession,parseP252Yahoo5mSessionPayload,buildP252Yahoo5mUrls,PHASE57_P25_2J_POLICY,PHASE57_P25_2J_SAFETY};
