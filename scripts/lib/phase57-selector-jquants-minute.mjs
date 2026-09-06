const API_BASE='https://api.jquants.com/';
const MINUTE_PATH='v2/equities/bars/minute';
const SAFETY=Object.freeze({
  executionAllowed:false,brokerWriteAllowed:false,excelOrderWriteAllowed:false,
  rssOrderFunctionAllowed:false,liveTradingAllowed:false,paperTradingAllowed:false,
  automaticPromotionAllowed:false,productionUpdateAllowed:false,transmitted:false,
});

const DATE=/^\d{4}-\d{2}-\d{2}$/;
const TIME=/^\d{2}:\d{2}$/;
const finite=value=>value!==null&&value!==undefined&&value!==''&&Number.isFinite(Number(value));

function requireApiKey(value){
  const key=String(value??'').trim();
  if(!key)throw new Error('JQUANTS_API_KEY is not configured');
  return key;
}

function timeParts(value){
  if(!TIME.test(String(value??'')))throw new Error(`invalid J-Quants minute time ${value}`);
  const [hour,minute]=value.split(':').map(Number);
  if(hour>23||minute>59)throw new Error(`invalid J-Quants minute time ${value}`);
  return {hour,minute,total:hour*60+minute};
}

function sourceMinuteSegment(total){
  if(total>=9*60&&total<11*60+30)return {name:'AM',start:9*60,end:11*60+30,kind:'REGULAR_CONTINUOUS_MINUTE'};
  if(total===11*60+30)return {name:'AM',start:9*60,end:11*60+30,kind:'TERMINAL_AUCTION_MINUTE'};
  if(total>=12*60+30&&total<15*60+30)return {name:'PM',start:12*60+30,end:15*60+30,kind:'REGULAR_CONTINUOUS_MINUTE'};
  if(total===15*60+30)return {name:'PM',start:12*60+30,end:15*60+30,kind:'TERMINAL_AUCTION_MINUTE'};
  return null;
}

function timestampIso(date,totalMinutes){
  const hour=String(Math.floor(totalMinutes/60)).padStart(2,'0');
  const minute=String(totalMinutes%60).padStart(2,'0');
  return new Date(`${date}T${hour}:${minute}:00+09:00`).toISOString();
}

function sameMinute(left,right){
  return ['date','time','code','open','high','low','close','volume','turnover'].every(key=>left[key]===right[key]);
}

export function normalizeJquantsMinuteRow(raw,index=0){
  const date=String(raw?.Date??'');
  const time=String(raw?.Time??'');
  const code=String(raw?.Code??'').trim().toUpperCase();
  if(!DATE.test(date))throw new Error(`minute row[${index}] has invalid Date`);
  const {total}=timeParts(time);
  const segment=sourceMinuteSegment(total);
  if(!segment)throw new Error(`minute row[${index}] is outside the supported TSE source session`);
  if(!/^(?:\d{5}|\d{3}[A-Z]\d)$/.test(code))throw new Error(`minute row[${index}] has invalid Code`);
  for(const key of ['O','H','L','C','Vo','Va']){
    if(!finite(raw?.[key]))throw new Error(`minute row[${index}] requires finite ${key}`);
  }
  const row={
    date,time,code,sessionSegment:segment.name,sourceMinuteKind:segment.kind,
    open:Number(raw.O),high:Number(raw.H),low:Number(raw.L),close:Number(raw.C),
    volume:Number(raw.Vo),turnover:Number(raw.Va),
  };
  if(row.open<=0||row.high<=0||row.low<=0||row.close<=0)throw new Error(`minute row[${index}] prices must be positive`);
  if(row.volume<0||row.turnover<0)throw new Error(`minute row[${index}] volume and turnover must be non-negative`);
  if(row.high<Math.max(row.open,row.close,row.low)||row.low>Math.min(row.open,row.close,row.high)){
    throw new Error(`minute row[${index}] has invalid OHLC ordering`);
  }
  return Object.freeze(row);
}

export function normalizeJquantsMinuteRows(rows){
  if(!Array.isArray(rows))throw new TypeError('J-Quants minute rows must be an array');
  const unique=new Map();
  rows.forEach((raw,index)=>{
    const row=normalizeJquantsMinuteRow(raw,index);
    const key=`${row.date}|${row.time}|${row.code}`;
    const previous=unique.get(key);
    if(previous&&!sameMinute(previous,row))throw new Error(`conflicting J-Quants minute duplicate ${key}`);
    if(!previous)unique.set(key,row);
  });
  return Object.freeze([...unique.values()].sort((a,b)=>
    a.date.localeCompare(b.date)||a.time.localeCompare(b.time)||a.code.localeCompare(b.code)
  ));
}

export function partitionJquantsMinuteRowsForFiveMinuteBars(rows){
  const normalized=normalizeJquantsMinuteRows(rows);
  return Object.freeze({
    regularRows:Object.freeze(normalized.filter(row=>row.sourceMinuteKind==='REGULAR_CONTINUOUS_MINUTE')),
    terminalAuctionRows:Object.freeze(normalized.filter(row=>row.sourceMinuteKind==='TERMINAL_AUCTION_MINUTE')),
  });
}

export function aggregateJquantsMinutesToFiveMinuteBars(rows,{sourceMinuteTimestampMeaning}={}){
  if(sourceMinuteTimestampMeaning!=='BAR_START_HALF_OPEN_INCLUDING_TERMINAL_AUCTION_MINUTES'){
    throw new Error('J-Quants minute timestamp contract must be the Tick-proven frozen contract');
  }
  const {regularRows:normalized}=partitionJquantsMinuteRowsForFiveMinuteBars(rows);
  const bins=new Map();
  for(const row of normalized){
    const {total}=timeParts(row.time);
    const segment=sourceMinuteSegment(total);
    const binStart=segment.start+Math.floor((total-segment.start)/5)*5;
    const key=`${row.date}|${row.code}|${segment.name}|${binStart}`;
    if(!bins.has(key))bins.set(key,{date:row.date,code:row.code,segment:segment.name,binStart,rows:[]});
    bins.get(key).rows.push(row);
  }
  const bars=[...bins.values()].map(bin=>{
    const ordered=bin.rows.sort((a,b)=>a.time.localeCompare(b.time));
    const first=ordered[0];
    const last=ordered.at(-1);
    return Object.freeze({
      symbol:`${bin.code.slice(0,-1)}.T`,
      sourceCode:bin.code,
      sessionDate:bin.date,
      sessionSegment:bin.segment,
      timestamp:timestampIso(bin.date,bin.binStart),
      availableAt:timestampIso(bin.date,bin.binStart+5),
      open:first.open,
      high:Math.max(...ordered.map(row=>row.high)),
      low:Math.min(...ordered.map(row=>row.low)),
      close:last.close,
      volume:ordered.reduce((sum,row)=>sum+row.volume,0),
      turnover:ordered.reduce((sum,row)=>sum+row.turnover,0),
      observedMinuteCount:ordered.length,
      missingNoTradeMinuteCount:5-ordered.length,
      fabricatedMinuteCount:0,
    });
  });
  return Object.freeze(bars.sort((a,b)=>
    a.timestamp.localeCompare(b.timestamp)||a.symbol.localeCompare(b.symbol)
  ));
}

async function fetchPage({apiKey,fetchImpl,apiBase,query,paginationKey}){
  const url=new URL(MINUTE_PATH,apiBase);
  for(const [key,value] of Object.entries(query))if(value!==null&&value!==undefined&&String(value)!=='')url.searchParams.set(key,String(value));
  if(paginationKey)url.searchParams.set('pagination_key',paginationKey);
  const response=await fetchImpl(url,{cache:'no-store',headers:{Accept:'application/json','x-api-key':apiKey}});
  if(!response.ok)throw new Error(`J-Quants minute OHLC HTTP ${response.status}`);
  return response.json();
}

export async function fetchJquantsMinuteRows({
  apiKey,code=null,date=null,from=null,to=null,fetchImpl=globalThis.fetch,
  apiBase=API_BASE,maximumPages=1000,
}={}){
  if(typeof fetchImpl!=='function')throw new TypeError('J-Quants minute provider requires fetch');
  const token=requireApiKey(apiKey);
  if(!code&&!date)throw new Error('J-Quants minute request requires code or date');
  if((from||to)&&!code)throw new Error('from/to minute request requires code');
  const query={code,date,from,to};
  const rows=[];
  const seenKeys=new Set();
  let paginationKey=null;
  for(let page=0;page<maximumPages;page+=1){
    const payload=await fetchPage({apiKey:token,fetchImpl,apiBase,query,paginationKey});
    if(!Array.isArray(payload?.data))throw new Error('J-Quants minute payload requires data[]');
    rows.push(...payload.data);
    const next=String(payload.pagination_key??payload.paginationKey??'').trim();
    if(!next)break;
    if(seenKeys.has(next))throw new Error('J-Quants minute pagination key repeated');
    seenKeys.add(next);paginationKey=next;
    if(page===maximumPages-1)throw new Error('J-Quants minute pagination exceeded maximumPages');
  }
  return Object.freeze({
    phase:'57.selector-minimal-hybrid.jquants-minute-source',
    status:'JQUANTS_MINUTE_ROWS_READY',
    rows:normalizeJquantsMinuteRows(rows),
    methodology:Object.freeze({
      endpoint:'/v2/equities/bars/minute',
      sourceIntervalMinutes:1,
      noTradeMinutesFabricated:false,
      sourceMinuteTimestampMeaningVerifiedByOperator:false,
      providerEntitlementVerifiedByOperator:false,
    }),
    safety:SAFETY,
  });
}

export const PHASE57_SELECTOR_JQUANTS_MINUTE_SAFETY=SAFETY;
export const Phase57SelectorJquantsMinuteInternals=Object.freeze({API_BASE,MINUTE_PATH,sourceMinuteSegment,timestampIso});

export default {
  normalizeJquantsMinuteRow,
  normalizeJquantsMinuteRows,
  partitionJquantsMinuteRowsForFiveMinuteBars,
  aggregateJquantsMinutesToFiveMinuteBars,
  fetchJquantsMinuteRows,
  PHASE57_SELECTOR_JQUANTS_MINUTE_SAFETY,
};
