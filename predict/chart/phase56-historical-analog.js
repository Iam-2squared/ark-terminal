export const PHASE56_ANALOG_SAFETY = Object.freeze({
  mode: 'HISTORICAL_ANALOG_RESEARCH_ONLY',
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

function finite(v){ return Number.isFinite(Number(v)); }
function clamp01(v){ return Math.max(0, Math.min(1, Number(v)||0)); }
function mean(xs){ return xs.length ? xs.reduce((a,b)=>a+b,0)/xs.length : 0; }
function median(xs){
  if(!xs.length) return 0;
  const a=[...xs].sort((x,y)=>x-y), m=Math.floor(a.length/2);
  return a.length%2 ? a[m] : (a[m-1]+a[m])/2;
}
function pct(a,b){ return finite(a)&&finite(b)&&Number(b)!==0 ? (Number(a)-Number(b))/Number(b) : null; }
function sma(bars,n){
  if(!Array.isArray(bars)||bars.length<n) return null;
  const xs=bars.slice(-n).map(b=>Number(b.close)).filter(finite);
  return xs.length===n ? mean(xs) : null;
}
function atr(bars,n=14){
  if(!Array.isArray(bars)||bars.length<n+1) return null;
  const rs=[];
  for(let i=bars.length-n;i<bars.length;i++){
    const b=bars[i], p=bars[i-1];
    if(![b?.high,b?.low,p?.close].every(finite)) return null;
    rs.push(Math.max(Number(b.high)-Number(b.low), Math.abs(Number(b.high)-Number(p.close)), Math.abs(Number(b.low)-Number(p.close))));
  }
  return mean(rs);
}
function featureVector(bars){
  if(!Array.isArray(bars)||bars.length<25) return null;
  const last=bars.at(-1), c=Number(last?.close), ma5=sma(bars,5), ma25=sma(bars,25), a=atr(bars,14);
  if(![c,ma5,ma25,a,last?.volume].every(finite)||c===0) return null;
  const recent=bars.slice(-20), vols=recent.map(b=>Number(b.volume)).filter(finite);
  const hi=Math.max(...recent.map(b=>Number(b.high)).filter(finite));
  const lo=Math.min(...recent.map(b=>Number(b.low)).filter(finite));
  const range=hi-lo;
  return Object.freeze({
    ret1:pct(c,Number(bars.at(-2)?.close)),
    ret5:pct(c,Number(bars.at(-6)?.close)),
    ma5Distance:pct(c,ma5),
    ma25Distance:pct(c,ma25),
    atrNorm:a/c,
    rangePosition:range>0 ? (c-lo)/range : 0.5,
    relativeVolume:vols.length ? Number(last.volume)/Math.max(mean(vols),1) : 1,
  });
}
const KEYS=['ret1','ret5','ma5Distance','ma25Distance','atrNorm','rangePosition','relativeVolume'];
function distance(a,b){
  let sum=0,count=0;
  for(const k of KEYS){
    if(finite(a?.[k])&&finite(b?.[k])){ const d=Number(a[k])-Number(b[k]); sum+=d*d; count++; }
  }
  return count ? Math.sqrt(sum/count) : Infinity;
}
function sessionDateOf(b){ return String(b?.sessionDate ?? b?.date ?? b?.timestamp ?? ''); }

export function findHistoricalAnalogs({bars=[], asOfIndex=null, lookback=25, horizon=5, topK=20, minGap=5}={}){
  if(!Array.isArray(bars)||bars.length<lookback+horizon+2) return Object.freeze({phase:'56.p1',status:'INSUFFICIENT_DATA',analogs:[],executionAllowed:false,transmitted:false,safety:PHASE56_ANALOG_SAFETY});
  const idx=Number.isInteger(asOfIndex)?asOfIndex:bars.length-1;
  if(idx<lookback-1||idx>=bars.length) return Object.freeze({phase:'56.p1',status:'INVALID_ASOF',analogs:[],executionAllowed:false,transmitted:false,safety:PHASE56_ANALOG_SAFETY});
  const currentBars=bars.slice(0,idx+1), current=featureVector(currentBars);
  if(!current) return Object.freeze({phase:'56.p1',status:'FEATURES_NOT_READY',analogs:[],executionAllowed:false,transmitted:false,safety:PHASE56_ANALOG_SAFETY});
  const latestCandidate=idx-Math.max(minGap,horizon);
  const candidates=[];
  for(let j=lookback-1;j<=latestCandidate;j++){
    const vec=featureVector(bars.slice(0,j+1));
    if(!vec) continue;
    const futureIndex=j+horizon;
    if(futureIndex>idx) continue; // strict point-in-time: never use outcomes after asOf
    const entry=Number(bars[j]?.close), future=Number(bars[futureIndex]?.close);
    if(!finite(entry)||!finite(future)||entry===0) continue;
    const forwardReturn=(future-entry)/entry;
    const d=distance(current,vec);
    candidates.push({index:j,sessionDate:sessionDateOf(bars[j]),distance:d,similarity:1/(1+d),forwardReturn,direction:forwardReturn>0?'UP':forwardReturn<0?'DOWN':'FLAT'});
  }
  candidates.sort((a,b)=>a.distance-b.distance);
  const analogs=candidates.slice(0,Math.max(1,topK));
  const returns=analogs.map(a=>a.forwardReturn);
  const up=returns.filter(r=>r>0).length, down=returns.filter(r=>r<0).length;
  return Object.freeze({
    phase:'56.p1',status:analogs.length?'ANALOGS_READY':'NO_ANALOGS',asOfIndex:idx,asOfSessionDate:sessionDateOf(bars[idx]),horizon,
    pointInTime:true,maxOutcomeIndexUsed:analogs.length?Math.max(...analogs.map(a=>a.index+horizon)):null,
    sampleCount:analogs.length,upRate:analogs.length?up/analogs.length:0,downRate:analogs.length?down/analogs.length:0,
    meanForwardReturn:mean(returns),medianForwardReturn:median(returns),confidence:clamp01(analogs.length/Math.max(topK,1)),
    currentFeatures:current,analogs,
    reviewOnly:true,recommendationAllowed:false,paperTradingAllowed:false,executionAllowed:false,brokerWriteAllowed:false,
    excelOrderWriteAllowed:false,rssOrderFunctionAllowed:false,liveTradingAllowed:false,automaticPromotionAllowed:false,
    productionUpdateAllowed:false,transmitted:false,humanApprovalRequired:true,safety:PHASE56_ANALOG_SAFETY,
  });
}
