export const PHASE58_ZERO_TICK_SAFETY=Object.freeze({phase:'58.tick-classifier',researchOnly:true,executionAllowed:false,brokerWriteAllowed:false,excelOrderWriteAllowed:false,rssOrderFunctionAllowed:false,liveTradingAllowed:false,paperTradingAllowed:false,automaticPromotionAllowed:false,productionUpdateAllowed:false,transmitted:false,freshHoldoutConsumed:false});

const finite=x=>Number.isFinite(Number(x));

function normalizeTickOrder(ticks=[],inputOrder='ASC'){
  const order=String(inputOrder??'').trim().toUpperCase();
  if(order!=='ASC'&&order!=='DESC')throw new TypeError('inputOrder must be ASC or DESC');
  const rows=(Array.isArray(ticks)?ticks:[]).map((tick,sourceIndex)=>({tick:tick??{},sourceIndex}));
  const normalized=order==='DESC'?rows.slice().reverse():rows;
  return Object.freeze({
    rows:Object.freeze(normalized),
    integrity:Object.freeze({
      tickInputOrder:order,
      causalProcessingOrder:'OLDEST_TO_NEWEST',
      causalOrderNormalized:order==='DESC',
      equalTimestampOrderingPolicy:'PRESERVE_PROVIDER_SEQUENCE_AFTER_ORDER_NORMALIZATION',
      futureLeakageDetected:false,
    }),
  });
}

// Causal tick-rule continuation: a non-zero price change sets direction; equal-price
// prints inherit only the most recent non-zero direction observed earlier in causal
// time. MARKETSPEED II RssTickList is captured newest-to-oldest (DESC), so callers
// must pass that order and the classifier reverses it before any tick-rule state is
// updated. The captured dataset bytes are never mutated.
export function classifyTicksWithZeroContinuation(ticks=[],{inputOrder='ASC'}={}){
  const normalized=normalizeTickOrder(ticks,inputOrder);
  const out=[];
  let previousPrice=null;
  let lastNonZeroSide=0;
  for(let i=0;i<normalized.rows.length;i++){
    const {tick:t,sourceIndex}=normalized.rows[i];
    const price=Number(t.price??t.executionPrice??t['約定値']);
    const volume=Number(t.volume??t.size??t.executionVolume??t['出来高']??0);
    if(!finite(price)||price<=0)continue;
    let side=0,method='UNCLASSIFIED';
    if(previousPrice!==null){
      if(price>previousPrice){side=1;lastNonZeroSide=1;method='ZERO_TICK_RULE_UP';}
      else if(price<previousPrice){side=-1;lastNonZeroSide=-1;method='ZERO_TICK_RULE_DOWN';}
      else if(lastNonZeroSide!==0){side=lastNonZeroSide;method='ZERO_TICK_CONTINUATION';}
    }
    out.push(Object.freeze({index:i,sourceIndex,price,volume:finite(volume)?Math.max(0,volume):0,side,method,time:t.time??t.timestamp??null}));
    previousPrice=price;
  }
  return Object.freeze(out);
}

export function summarizeZeroTickFlow(classified=[]){
  const rows=Array.isArray(classified)?classified:[];
  const known=rows.filter(r=>r.side!==0);
  const buyVolume=known.filter(r=>r.side>0).reduce((s,r)=>s+r.volume,0);
  const sellVolume=known.filter(r=>r.side<0).reduce((s,r)=>s+r.volume,0);
  const knownVolume=buyVolume+sellVolume;
  const signedVolumeImbalance=knownVolume>0?(buyVolume-sellVolume)/knownVolume:null;
  return Object.freeze({tickCount:rows.length,classifiedCount:known.length,classifiedTickFraction:rows.length?known.length/rows.length:null,buyVolume,sellVolume,knownVolume,signedVolumeImbalance,continuationCount:rows.filter(r=>r.method==='ZERO_TICK_CONTINUATION').length,researchOnly:true,safety:PHASE58_ZERO_TICK_SAFETY});
}

export function buildZeroTickFlow(ticks=[],{inputOrder='ASC'}={}){
  const normalized=normalizeTickOrder(ticks,inputOrder);
  const classified=classifyTicksWithZeroContinuation(ticks,{inputOrder});
  return Object.freeze({phase:'58.tick-classifier',classified,features:summarizeZeroTickFlow(classified),integrity:normalized.integrity,researchOnly:true,promotionEvidence:false,safety:PHASE58_ZERO_TICK_SAFETY});
}
