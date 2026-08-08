export const PHASE56_STOCK_CHARACTERISTICS_SAFETY = Object.freeze({
  mode: 'STOCK_CHARACTERISTICS_RESEARCH_ONLY',
  executionAllowed: false,
  brokerWriteAllowed: false,
  excelOrderWriteAllowed: false,
  rssOrderFunctionAllowed: false,
  liveTradingAllowed: false,
  paperTradingAllowed: false,
  automaticPromotionAllowed: false,
  productionUpdateAllowed: false,
  humanApprovalRequired: true,
});

function finite(v){ return v !== null && v !== undefined && v !== '' && Number.isFinite(Number(v)); }
function upper(v,fallback='UNKNOWN'){ const s=String(v ?? '').trim(); return s ? s.toUpperCase() : fallback; }
function asTime(v){ const t=Date.parse(v); return Number.isFinite(t) ? t : null; }
function classify(value,bands){
  if(!finite(value)) return 'UNKNOWN';
  const n=Number(value);
  for(const band of bands) if(n < band.max) return band.label;
  return bands.at(-1)?.label ?? 'UNKNOWN';
}
function mean(xs){ return xs.length ? xs.reduce((a,b)=>a+b,0)/xs.length : null; }

export function marketCapBucket(value){
  return classify(value,[
    {max:10_000_000_000,label:'UNDER_10B'},
    {max:50_000_000_000,label:'10B_50B'},
    {max:300_000_000_000,label:'50B_300B'},
    {max:1_000_000_000_000,label:'300B_1T'},
    {max:Number.POSITIVE_INFINITY,label:'OVER_1T'},
  ]);
}
export function priceBucket(value){
  return classify(value,[
    {max:100,label:'UNDER_100'},
    {max:500,label:'100_500'},
    {max:1_000,label:'500_1000'},
    {max:3_000,label:'1000_3000'},
    {max:Number.POSITIVE_INFINITY,label:'OVER_3000'},
  ]);
}
export function tradingValueBucket(value){
  return classify(value,[
    {max:100_000_000,label:'UNDER_100M'},
    {max:1_000_000_000,label:'100M_1B'},
    {max:10_000_000_000,label:'1B_10B'},
    {max:Number.POSITIVE_INFINITY,label:'OVER_10B'},
  ]);
}
export function liquidityBucket(value){
  if(!finite(value)) return 'UNKNOWN';
  const n=Number(value);
  if(n>=10_000_000_000) return 'VERY_HIGH';
  if(n>=1_000_000_000) return 'HIGH';
  if(n>=100_000_000) return 'MEDIUM';
  return 'LOW';
}

function readClose(bar){ return finite(bar?.close) ? Number(bar.close) : null; }
function readVolume(bar){ return finite(bar?.volume) ? Number(bar.volume) : null; }
function sessionDate(bar){ return String(bar?.sessionDate ?? bar?.date ?? bar?.timestamp ?? ''); }

export function buildStockCharacteristics({bars=[], asOfIndex=null, metadata={}}={}){
  if(!Array.isArray(bars)||bars.length===0) return Object.freeze({phase:'56.p2',status:'INSUFFICIENT_DATA',executionAllowed:false,transmitted:false,safety:PHASE56_STOCK_CHARACTERISTICS_SAFETY});
  const idx=Number.isInteger(asOfIndex)?asOfIndex:bars.length-1;
  if(idx<0||idx>=bars.length) return Object.freeze({phase:'56.p2',status:'INVALID_ASOF',executionAllowed:false,transmitted:false,safety:PHASE56_STOCK_CHARACTERISTICS_SAFETY});

  const asOfSessionDate=sessionDate(bars[idx]);
  const asOfTime=asTime(asOfSessionDate);
  const effectiveAt=metadata?.effectiveAt ?? metadata?.asOf ?? null;
  const effectiveTime=effectiveAt ? asTime(effectiveAt) : null;
  if(effectiveAt && asOfTime !== null && (effectiveTime === null || effectiveTime > asOfTime)) {
    return Object.freeze({phase:'56.p2',status:'METADATA_FUTURE_LEAK_BLOCKED',asOfIndex:idx,asOfSessionDate,effectiveAt,pointInTime:false,executionAllowed:false,transmitted:false,safety:PHASE56_STOCK_CHARACTERISTICS_SAFETY});
  }

  const history=bars.slice(0,idx+1);
  const last=history.at(-1);
  const close=readClose(last);
  const recent=history.slice(-20);
  const dailyTradingValues=recent.map(b=>{
    const c=readClose(b),v=readVolume(b);
    return c!==null&&v!==null?c*v:null;
  }).filter(finite);
  const averageTradingValue20=mean(dailyTradingValues);
  const lastTradingValue=close!==null&&readVolume(last)!==null?close*readVolume(last):null;
  const marketCap=finite(metadata?.marketCap ?? metadata?.marketCapitalization)?Number(metadata.marketCap ?? metadata.marketCapitalization):null;
  const sharesOutstanding=finite(metadata?.sharesOutstanding)?Number(metadata.sharesOutstanding):null;
  const derivedMarketCap=marketCap ?? (close!==null&&sharesOutstanding!==null?close*sharesOutstanding:null);

  return Object.freeze({
    phase:'56.p2',status:'STOCK_CHARACTERISTICS_READY',asOfIndex:idx,asOfSessionDate,pointInTime:true,
    symbol:upper(metadata?.symbol ?? metadata?.ticker ?? metadata?.code),
    sector:String(metadata?.sector ?? metadata?.industry ?? 'UNKNOWN').trim() || 'UNKNOWN',
    marketSegment:upper(metadata?.marketSegment ?? metadata?.marketSection ?? metadata?.market),
    indexMembership:Array.isArray(metadata?.indexMembership)?metadata.indexMembership.map(x=>upper(x)).filter(x=>x!=='UNKNOWN'):[],
    close,marketCap:derivedMarketCap,marketCapBucket:marketCapBucket(derivedMarketCap),priceBucket:priceBucket(close),
    lastTradingValue,averageTradingValue20,tradingValueBucket:tradingValueBucket(averageTradingValue20),liquidityBucket:liquidityBucket(averageTradingValue20),
    metadataEffectiveAt:effectiveAt,
    reviewOnly:true,recommendationAllowed:false,paperTradingAllowed:false,executionAllowed:false,brokerWriteAllowed:false,
    excelOrderWriteAllowed:false,rssOrderFunctionAllowed:false,liveTradingAllowed:false,automaticPromotionAllowed:false,
    productionUpdateAllowed:false,transmitted:false,humanApprovalRequired:true,safety:PHASE56_STOCK_CHARACTERISTICS_SAFETY,
  });
}
