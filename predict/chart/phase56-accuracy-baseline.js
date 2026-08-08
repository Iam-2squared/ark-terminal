import { analyzeChartStructure } from './phase56-chart-intelligence.js';
import { analyzePriceActionFeatures } from './phase56-price-action.js';
import { analyzeChartSetupContext } from './phase56-setup-context.js';

export const PHASE56_BASELINE_SAFETY = Object.freeze({
  mode: 'CHART_ACCURACY_EVALUATION_ONLY', executionAllowed: false,
  brokerWriteAllowed: false, excelOrderWriteAllowed: false,
  rssOrderFunctionAllowed: false, liveTradingAllowed: false,
  automaticPromotionAllowed: false, productionUpdateAllowed: false,
  humanApprovalRequired: true,
});

const mean = (xs) => xs.length ? xs.reduce((a,b)=>a+b,0)/xs.length : null;

function directionalSignal(chart, setup) {
  const regime = chart.marketStructure?.regime;
  const labels = new Set(setup.labels || []);
  if (regime === 'UPTREND' || labels.has('BREAKOUT_ABOVE_LOOKBACK') || labels.has('RETEST_HOLD_ABOVE')) return 1;
  if (regime === 'DOWNTREND' || labels.has('BREAKDOWN_BELOW_LOOKBACK') || labels.has('RETEST_HOLD_BELOW')) return -1;
  return 0;
}

export function evaluateChartAccuracy({candles=[], lookback=80, horizons=[1,3,5,10,20], minimumSignals=30}={}) {
  const rows=[];
  for (let i=lookback;i<candles.length;i++) {
    const slice=candles.slice(i-lookback,i+1);
    const chart=analyzeChartStructure({bars:slice});
    const priceAction=analyzePriceActionFeatures({bars:slice});
    const setup=analyzeChartSetupContext({bars:slice});
    if (chart.status!=='CHART_CONTEXT_READY' || priceAction.status!=='PRICE_ACTION_FEATURES_READY' || setup.status!=='SETUP_CONTEXT_READY') continue;
    const signal=directionalSignal(chart,setup);
    if (!signal) continue;
    for (const h of horizons) {
      const j=i+h; if (j>=candles.length) continue;
      const entry=Number(candles[i].close), exit=Number(candles[j].close);
      if (!Number.isFinite(entry)||!Number.isFinite(exit)||entry===0) continue;
      const ret=(exit-entry)/entry;
      rows.push({index:i,horizon:h,signal,return:ret,alignedReturn:ret*signal,hit:ret*signal>0});
    }
  }
  const byHorizon=horizons.map(h=>{
    const r=rows.filter(x=>x.horizon===h);
    const aligned=r.map(x=>x.alignedReturn);
    const wins=aligned.filter(x=>x>0).reduce((a,b)=>a+b,0);
    const losses=Math.abs(aligned.filter(x=>x<0).reduce((a,b)=>a+b,0));
    return {horizon:h,samples:r.length,hitRate:r.length?mean(r.map(x=>x.hit?1:0)):null,meanAlignedReturn:mean(aligned),profitFactor:losses>0?wins/losses:(wins>0?Infinity:null),eligible:r.length>=minimumSignals};
  });
  return Object.freeze({phase:'56-baseline',status:byHorizon.some(x=>x.eligible)?'BASELINE_READY':'INSUFFICIENT_SIGNALS',byHorizon,totalSignals:new Set(rows.map(x=>x.index)).size,evaluationOnly:true,recommendationAllowed:false,paperTradingAllowed:false,executionAllowed:false,transmitted:false,safety:PHASE56_BASELINE_SAFETY});
}
