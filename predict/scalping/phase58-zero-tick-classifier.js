export const PHASE58_ZERO_TICK_SAFETY=Object.freeze({phase:'58.tick-classifier',researchOnly:true,executionAllowed:false,brokerWriteAllowed:false,excelOrderWriteAllowed:false,rssOrderFunctionAllowed:false,liveTradingAllowed:false,paperTradingAllowed:false,automaticPromotionAllowed:false,productionUpdateAllowed:false,transmitted:false,freshHoldoutConsumed:false});

const finite=x=>Number.isFinite(Number(x));

// Causal tick-rule continuation: a non-zero price change sets direction; equal-price
// prints inherit the most recent non-zero direction. This uses only present/past ticks,
// never future prices, and does not assume a native aggressor-side field from RssTickList.
export function classifyTicksWithZeroContinuation(ticks=[]){
  const rows=Array.isArray(ticks)?ticks:[];
  const out=[];
  let previousPrice=null;
  let lastNonZeroSide=0;
  for(let i=0;i<rows.length;i++){
    const t=rows[i]??{};
    const price=Number(t.price??t.executionPrice??t['約定値']);
    const volume=Number(t.volume??t.size??t.executionVolume??t['出来高']??0);
    if(!finite(price)||price<=0)continue;
    let side=0,method='UNCLASSIFIED';
    if(previousPrice!==null){
      if(price>previousPrice){side=1;lastNonZeroSide=1;method='ZERO_TICK_RULE_UP';}
      else if(price<previousPrice){side=-1;lastNonZeroSide=-1;method='ZERO_TICK_RULE_DOWN';}
      else if(lastNonZeroSide!==0){side=lastNonZeroSide;method='ZERO_TICK_CONTINUATION';}
    }
    out.push(Object.freeze({index:i,price,volume:finite(volume)?Math.max(0,volume):0,side,method,time:t.time??t.timestamp??null}));
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

export function buildZeroTickFlow(ticks=[]){
  const classified=classifyTicksWithZeroContinuation(ticks);
  return Object.freeze({phase:'58.tick-classifier',classified,features:summarizeZeroTickFlow(classified),researchOnly:true,promotionEvidence:false,safety:PHASE58_ZERO_TICK_SAFETY});
}
