export const PHASE56_TECHNICAL_FUSION_SAFETY = Object.freeze({
  mode: 'TECHNICAL_FUSION_RESEARCH_ONLY',
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
function n(v){ return finite(v) ? Number(v) : null; }
function ratio(a,b){ return finite(a)&&finite(b)&&Number(b)!==0 ? Number(a)/Number(b) : null; }
function distance(a,b){ return finite(a)&&finite(b)&&Number(b)!==0 ? (Number(a)-Number(b))/Number(b) : null; }
function direction(value, neutral=0){ return !finite(value) ? 'UNKNOWN' : Number(value)>neutral ? 'UP' : Number(value)<neutral ? 'DOWN' : 'FLAT'; }

export function buildTechnicalFusionFeatures({indicators={}, asOfSessionDate=null}={}){
  const price=n(indicators.currentPrice);
  const ma=indicators.movingAverages||{};
  const macd=indicators.macd||{};
  const adx=indicators.adx||{};
  const atr=indicators.atr||{};
  const bb=indicators.bollingerBands||{};
  const stochastic=indicators.stochastic||{};
  const volume=indicators.volume||{};
  const ma5=n(ma.ma5), ma25=n(ma.ma25), ma75=n(ma.ma75), ma200=n(ma.ma200);
  const features={
    price,
    ma5Distance:distance(price,ma5),
    ma25Distance:distance(price,ma25),
    ma75Distance:distance(price,ma75),
    ma200Distance:distance(price,ma200),
    maStack: [price,ma5,ma25,ma75,ma200].every(finite) ? (price>ma5&&ma5>ma25&&ma25>ma75&&ma75>ma200?'BULL_STACK':price<ma5&&ma5<ma25&&ma25<ma75&&ma75<ma200?'BEAR_STACK':'MIXED') : 'UNKNOWN',
    ma5Slope: finite(ma.previousMa5)&&finite(ma5) ? Number(ma5)-Number(ma.previousMa5) : null,
    ma25Slope: finite(ma.previousMa25)&&finite(ma25) ? Number(ma25)-Number(ma.previousMa25) : null,
    rsi:n(indicators.rsi),
    macdHistogram:n(macd.histogram),
    macdDirection:direction(macd.histogram),
    adx:n(adx.value),
    plusDi:n(adx.plusDi),
    minusDi:n(adx.minusDi),
    trendDirection: finite(adx.plusDi)&&finite(adx.minusDi) ? (Number(adx.plusDi)>=Number(adx.minusDi)?'UP':'DOWN') : 'UNKNOWN',
    atrPercent:n(atr.percent),
    vwapDistance:distance(price,indicators.vwap),
    bollingerPercentB:n(bb.percentB),
    bollingerWidth: finite(bb.upper)&&finite(bb.lower)&&finite(bb.middle)&&Number(bb.middle)!==0 ? (Number(bb.upper)-Number(bb.lower))/Number(bb.middle) : null,
    stochasticK:n(stochastic.k),
    stochasticD:n(stochastic.d),
    stochasticSpread: finite(stochastic.k)&&finite(stochastic.d) ? Number(stochastic.k)-Number(stochastic.d) : null,
    relativeVolume:n(volume.ratio),
    priceChangePercent:n(indicators.priceChangePercent),
  };
  const available=Object.values(features).filter(v=>v!==null&&v!=='UNKNOWN').length;
  return Object.freeze({
    phase:'56.p3', status:available>=8?'TECHNICAL_FEATURES_READY':'PARTIAL_TECHNICAL_FEATURES', asOfSessionDate,
    features:Object.freeze(features), availableFeatureCount:available,
    interactions:Object.freeze({
      trendVolume: features.maStack==='BULL_STACK'&&finite(features.relativeVolume)&&features.relativeVolume>=1.5 ? 'BULL_TREND_VOLUME_CONFIRM' : features.maStack==='BEAR_STACK'&&finite(features.relativeVolume)&&features.relativeVolume>=1.5 ? 'BEAR_TREND_VOLUME_CONFIRM' : 'NONE',
      vwapMomentum: finite(features.vwapDistance)&&finite(features.macdHistogram) ? (features.vwapDistance>=0&&features.macdHistogram>=0?'ABOVE_VWAP_POSITIVE_MACD':features.vwapDistance<0&&features.macdHistogram<0?'BELOW_VWAP_NEGATIVE_MACD':'MIXED') : 'UNKNOWN',
      trendStrength: finite(features.adx) ? (features.adx>=25?`${features.trendDirection}_STRONG`:`${features.trendDirection}_WEAK`) : 'UNKNOWN',
      volatilityVolume: finite(features.atrPercent)&&finite(features.relativeVolume) ? (features.relativeVolume>=1.5&&features.atrPercent>=4?'HIGH_VOL_HIGH_VOLUME':features.relativeVolume>=1.5?'VOLUME_EXPANSION':'NORMAL') : 'UNKNOWN',
    }),
    reviewOnly:true, recommendationAllowed:false, paperTradingAllowed:false, executionAllowed:false,
    brokerWriteAllowed:false, excelOrderWriteAllowed:false, rssOrderFunctionAllowed:false, liveTradingAllowed:false,
    automaticPromotionAllowed:false, productionUpdateAllowed:false, transmitted:false, humanApprovalRequired:true,
    safety:PHASE56_TECHNICAL_FUSION_SAFETY,
  });
}

export default buildTechnicalFusionFeatures;
