const SAFETY=Object.freeze({
  executionAllowed:false,brokerWriteAllowed:false,excelOrderWriteAllowed:false,
  rssOrderFunctionAllowed:false,liveTradingAllowed:false,paperTradingAllowed:false,
  automaticPromotionAllowed:false,productionUpdateAllowed:false,transmitted:false,
});

function jstParts(timestampMs){
  const parts=new Intl.DateTimeFormat('en-CA',{
    timeZone:'Asia/Tokyo',year:'numeric',month:'2-digit',day:'2-digit',
    hour:'2-digit',minute:'2-digit',hourCycle:'h23',
  }).formatToParts(new Date(timestampMs));
  const values=Object.fromEntries(parts.map(part=>[part.type,part.value]));
  return {sessionDate:`${values.year}-${values.month}-${values.day}`,time:`${values.hour}:${values.minute}`};
}

function regularSessionBar(time){
  return (time>='09:00'&&time<'11:30')||(time>='12:30'&&time<'15:30');
}

export function parseYahooChart5mPayload({symbol,sector='UNKNOWN',market=null,payload}={}){
  const result=payload?.chart?.result?.[0];
  if(!result)throw new Error(`${symbol} Yahoo chart has no result: ${JSON.stringify(payload?.chart?.error??null)}`);
  const timestamps=result.timestamp??[];
  const quote=result.indicators?.quote?.[0]??{};
  const bars=[];
  const seen=new Set();
  for(let index=0;index<timestamps.length;index+=1){
    const timestampMs=Number(timestamps[index])*1000;
    if(!Number.isFinite(timestampMs))continue;
    const {sessionDate,time}=jstParts(timestampMs);
    if(!regularSessionBar(time))continue;
    const values={
      open:Number(quote.open?.[index]),high:Number(quote.high?.[index]),
      low:Number(quote.low?.[index]),close:Number(quote.close?.[index]),
      volume:Number(quote.volume?.[index]),
    };
    if(!Object.values(values).every(Number.isFinite))continue;
    if(values.open<=0||values.high<=0||values.low<=0||values.close<=0||values.volume<0)continue;
    if(values.high<Math.max(values.open,values.close,values.low)||values.low>Math.min(values.open,values.close,values.high))continue;
    const timestamp=new Date(timestampMs).toISOString();
    if(seen.has(timestamp))continue;
    seen.add(timestamp);
    bars.push({timestamp,sessionDate,...values});
  }
  bars.sort((a,b)=>a.timestamp.localeCompare(b.timestamp));
  if(!bars.length)throw new Error(`${symbol} Yahoo chart contains no valid regular-session 5m bars`);
  return Object.freeze({
    symbol:String(symbol??'').trim().toUpperCase(),sector:String(sector??'').trim()||'UNKNOWN',market,
    bars:Object.freeze(bars),
    providerMeta:Object.freeze({
      exchangeName:result.meta?.exchangeName??null,
      exchangeTimezoneName:result.meta?.exchangeTimezoneName??null,
      currency:result.meta?.currency??null,
      instrumentType:result.meta?.instrumentType??null,
      dataGranularity:result.meta?.dataGranularity??null,
      firstTradeDate:result.meta?.firstTradeDate??null,
    }),
  });
}

const delay=ms=>new Promise(resolve=>setTimeout(resolve,ms));

export async function fetchYahooChart5m({
  symbol,sector='UNKNOWN',market=null,range='60d',attempts=4,baseDelayMs=750,fetchImpl=fetch,
}={}){
  if(!symbol)throw new TypeError('symbol is required');
  const url=`https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(symbol)}?range=${encodeURIComponent(range)}&interval=5m&includePrePost=false&events=div%2Csplits`;
  let lastError=null;
  for(let attempt=1;attempt<=attempts;attempt+=1){
    try{
      const response=await fetchImpl(url,{headers:{'User-Agent':'Mozilla/5.0 ArkTerminalResearch/1.0','Accept':'application/json'}});
      if(!response.ok){
        const body=(await response.text()).slice(0,200);
        const error=new Error(`${symbol} Yahoo chart HTTP ${response.status}: ${body}`);
        error.retryable=response.status===429||response.status>=500;
        throw error;
      }
      return parseYahooChart5mPayload({symbol,sector,market,payload:await response.json()});
    }catch(error){
      lastError=error;
      if(attempt>=attempts||error?.retryable===false)break;
      await delay(baseDelayMs*2**(attempt-1));
    }
  }
  throw lastError??new Error(`${symbol} Yahoo chart failed`);
}

export const PHASE57_SELECTOR_YAHOO_SAFETY=SAFETY;

