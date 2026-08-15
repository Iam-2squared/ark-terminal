import {buildMicrostructureIntelligence,MARKETSPEED_II_P22_READ_ONLY_CONTRACT} from '../daytrade/phase57-microstructure-intelligence.js';

export const PHASE58_P1_SAFETY=Object.freeze({
  phase:'58.p1',mode:'MICROSTRUCTURE_DATA_FOUNDATION_READ_ONLY',
  executionAllowed:false,brokerWriteAllowed:false,excelOrderWriteAllowed:false,rssOrderFunctionAllowed:false,
  liveTradingAllowed:false,paperTradingAllowed:false,automaticPromotionAllowed:false,productionUpdateAllowed:false,
  transmitted:false,freshHoldoutConsumed:false,
});

export const PHASE58_P1_CONTRACT=Object.freeze({
  source:'MARKETSPEED_II_RSS',
  allowedFunctions:Object.freeze(['RssMarket','RssTickList']),
  forbiddenOrderFunctions:true,
  maxRssTickRows:MARKETSPEED_II_P22_READ_ONLY_CONTRACT.RssTickList.maxRows,
  nativeAggressorSideAvailable:false,
  canonicalFeatures:Object.freeze([
    'bestBid','bestAsk','bidSize','askSize','mid','spread','spreadBps','topBookImbalance',
    'bidDepth','askDepth','depthImbalance','weightedDepthImbalance','microprice','micropriceEdgeBps',
    'signedVolumeImbalance','aggressiveBuyRatio','aggressiveSellRatio','classifiedTickFraction',
    'tradeIntensityPerSecond','meanTradeSize','averageSpreadBps','spreadChangeBps',
    'averageTopBookImbalance','latestTopBookImbalance','quoteUpdateRatePerSecond','quoteStalenessMs','tickStalenessMs'
  ]),
});

const finite=x=>Number.isFinite(Number(x));
const clamp=(x,a,b)=>Math.max(a,Math.min(b,x));

export function assessMicrostructureDataQuality(result,{maxQuoteStalenessMs=5000,maxTickStalenessMs=15000,minClassifiedTickFraction=.5,minQuoteSnapshots=2}={}){
  const f=result?.features??{},q=result?.dataQuality??{};
  const checks={
    topOfBookValid:finite(f.bestBid)&&finite(f.bestAsk)&&Number(f.bestBid)>0&&Number(f.bestAsk)>=Number(f.bestBid),
    quoteHistoryAdequate:(q.quoteSnapshotCount??0)>=minQuoteSnapshots,
    noFutureQuoteAssignments:(q.futureQuoteAssignments??0)===0,
    quoteFresh:!finite(f.quoteStalenessMs)||Number(f.quoteStalenessMs)<=maxQuoteStalenessMs,
    tickFresh:!finite(f.tickStalenessMs)||Number(f.tickStalenessMs)<=maxTickStalenessMs,
    tickClassificationAdequate:(q.tickCount??0)===0||!finite(f.classifiedTickFraction)||Number(f.classifiedTickFraction)>=minClassifiedTickFraction,
  };
  const passed=Object.values(checks).every(Boolean);
  const score=Object.values(checks).filter(Boolean).length/Object.keys(checks).length;
  return Object.freeze({passed,score:clamp(score,0,1),checks:Object.freeze(checks)});
}

export function buildPhase58MicrostructureFrame(input={},qualityOptions={}){
  const base=buildMicrostructureIntelligence(input);
  const quality=assessMicrostructureDataQuality(base,qualityOptions);
  const features={};
  for(const key of PHASE58_P1_CONTRACT.canonicalFeatures)features[key]=base.features?.[key]??null;
  return Object.freeze({
    phase:'58.p1',status:quality.passed?'MICROSTRUCTURE_FRAME_READY':'MICROSTRUCTURE_FRAME_DEGRADED',
    asOf:input.asOf??null,features:Object.freeze(features),quality,
    dataQuality:base.dataQuality,source:base.source,
    contract:PHASE58_P1_CONTRACT,safety:PHASE58_P1_SAFETY,
    researchOnly:true,recommendationAllowed:false,
  });
}

export function assertPhase58ReadOnly(frame){
  for(const k of ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted']){
    if(frame?.safety?.[k]!==false)throw new Error(`Phase58 unsafe flag: ${k}`);
  }
  if(frame?.source?.rssOrderFunctionsUsed!==false)throw new Error('RSS order functions must remain unused');
  return true;
}
