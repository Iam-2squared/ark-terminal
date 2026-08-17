import {buildPhase58MicrostructureFrame,assertPhase58ReadOnly} from './phase58-microstructure-foundation.js';

export const PHASE58_P2P3_SAFETY=Object.freeze({phase:'58.p2-p3',executionAllowed:false,brokerWriteAllowed:false,excelOrderWriteAllowed:false,rssOrderFunctionAllowed:false,liveTradingAllowed:false,paperTradingAllowed:false,automaticPromotionAllowed:false,productionUpdateAllowed:false,transmitted:false,freshHoldoutConsumed:false});
const finite=x=>Number.isFinite(Number(x));
const mean=a=>a.length?a.reduce((s,x)=>s+x,0)/a.length:null;
const sign=x=>x>0?1:x<0?-1:0;

// Order-book readiness must not be invalidated solely because RssTickList aggressor-side
// classification is weak. MARKETSPEED II RSS does not expose native aggressor side.
function orderBookQualityPassed(frame){
  const c=frame?.quality?.checks??{};
  return c.topOfBookValid===true&&c.quoteHistoryAdequate===true&&c.noFutureQuoteAssignments===true&&c.quoteFresh===true;
}

export function buildOrderBookIntelligence(frames=[]){
  const valid=(Array.isArray(frames)?frames:[]).filter(f=>f&&f.features&&orderBookQualityPassed(f));
  for(const f of valid)assertPhase58ReadOnly(f);
  const latest=valid.at(-1)?.features??{};
  const spreads=valid.map(f=>Number(f.features.spreadBps)).filter(finite);
  const top=valid.map(f=>Number(f.features.topBookImbalance)).filter(finite);
  const depth=valid.map(f=>Number(f.features.weightedDepthImbalance)).filter(finite);
  const micro=valid.map(f=>Number(f.features.micropriceEdgeBps)).filter(finite);
  const deltas=a=>a.slice(1).map((x,i)=>x-a[i]);
  const spreadDelta=deltas(spreads),topDelta=deltas(top),depthDelta=deltas(depth),microDelta=deltas(micro);
  const spreadWideningBps=spreadDelta.at(-1)??null;
  const imbalanceAcceleration=topDelta.length>=2?topDelta.at(-1)-topDelta.at(-2):null;
  const depthAcceleration=depthDelta.length>=2?depthDelta.at(-1)-depthDelta.at(-2):null;
  const liquidityShock=finite(spreadWideningBps)&&spreadWideningBps>2&&finite(latest.weightedDepthImbalance)&&Math.abs(Number(latest.weightedDepthImbalance))>.6;
  const pressureConsensus=[latest.topBookImbalance,latest.weightedDepthImbalance,latest.micropriceEdgeBps].filter(finite).map(sign);
  const consensus=pressureConsensus.length?mean(pressureConsensus):null;
  return Object.freeze({phase:'58.p2',status:valid.length>=2?'ORDER_BOOK_INTELLIGENCE_READY':'INSUFFICIENT_HISTORY',features:Object.freeze({latestSpreadBps:spreads.at(-1)??null,averageSpreadBps:mean(spreads),spreadWideningBps,topBookImbalance:top.at(-1)??null,topBookImbalanceChange:topDelta.at(-1)??null,imbalanceAcceleration,weightedDepthImbalance:depth.at(-1)??null,weightedDepthChange:depthDelta.at(-1)??null,depthAcceleration,micropriceEdgeBps:micro.at(-1)??null,micropriceEdgeChange:microDelta.at(-1)??null,pressureConsensus:consensus,liquidityShock}),sampleCount:valid.length,researchOnly:true,safety:PHASE58_P2P3_SAFETY});
}

export function buildTickFlowIntelligence(frame,history=[]){
  assertPhase58ReadOnly(frame);
  const all=[...(Array.isArray(history)?history:[]),frame].filter(Boolean);
  const rows=all.map(f=>f.features??{});
  const signed=rows.map(x=>Number(x.signedVolumeImbalance)).filter(finite);
  const intensity=rows.map(x=>Number(x.tradeIntensityPerSecond)).filter(finite);
  const classified=rows.map(x=>Number(x.classifiedTickFraction)).filter(finite);
  const current=frame.features??{};
  const flowMomentum=signed.length>=2?signed.at(-1)-signed.at(-2):null;
  const intensityBurst=intensity.length>=2&&intensity.at(-2)>0?intensity.at(-1)/intensity.at(-2):null;
  const directionalPersistence=signed.length?Math.abs(mean(signed.map(sign))):null;
  const checks=frame.quality?.checks??{};
  const reliable=checks.tickFresh===true&&checks.tickClassificationAdequate===true&&checks.noFutureQuoteAssignments===true;
  return Object.freeze({phase:'58.p3',status:reliable?'TICK_FLOW_INTELLIGENCE_READY':'TICK_FLOW_DEGRADED',features:Object.freeze({signedVolumeImbalance:finite(current.signedVolumeImbalance)?Number(current.signedVolumeImbalance):null,aggressiveBuyRatio:finite(current.aggressiveBuyRatio)?Number(current.aggressiveBuyRatio):null,tradeIntensityPerSecond:finite(current.tradeIntensityPerSecond)?Number(current.tradeIntensityPerSecond):null,flowMomentum,intensityBurst,directionalPersistence,classifiedTickFraction:classified.at(-1)??null,averageClassifiedTickFraction:mean(classified)}),sampleCount:rows.length,researchOnly:true,safety:PHASE58_P2P3_SAFETY});
}

export function buildPhase58P2P3(inputSeries=[],qualityOptions={}){
  const frames=(Array.isArray(inputSeries)?inputSeries:[]).map(x=>buildPhase58MicrostructureFrame(x,qualityOptions));
  const book=buildOrderBookIntelligence(frames);
  const flow=frames.length?buildTickFlowIntelligence(frames.at(-1),frames.slice(0,-1)):null;
  return Object.freeze({phase:'58.p2-p3',frames:Object.freeze(frames),orderBook:book,tickFlow:flow,safety:PHASE58_P2P3_SAFETY});
}
