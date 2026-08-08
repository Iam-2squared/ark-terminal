import { analyzeChartStructure } from './phase56-chart-intelligence.js';
import { analyzePriceActionFeatures } from './phase56-price-action.js';
import { analyzeChartSetupContext } from './phase56-setup-context.js';

export const PHASE56_SELECTIVE_SAFETY = Object.freeze({mode:'SELECTIVE_SIGNAL_EVALUATION_ONLY',executionAllowed:false,brokerWriteAllowed:false,excelOrderWriteAllowed:false,rssOrderFunctionAllowed:false,liveTradingAllowed:false,automaticPromotionAllowed:false,productionUpdateAllowed:false,humanApprovalRequired:true});

function scoreConfluence(chart, priceAction, setup){
  let long=0, short=0; const reasons=[]; const labels=new Set([...(priceAction.labels||[]),...(setup.labels||[])]);
  const regime=chart.marketStructure?.regime;
  if(regime==='UPTREND'){long+=2;reasons.push('uptrend');}
  if(regime==='DOWNTREND'){short+=2;reasons.push('downtrend');}
  if(labels.has('BREAKOUT_ABOVE_LOOKBACK')){long+=2;reasons.push('breakout_up');}
  if(labels.has('BREAKDOWN_BELOW_LOOKBACK')){short+=2;reasons.push('breakdown_down');}
  if(labels.has('RETEST_HOLD_ABOVE')){long+=2;reasons.push('retest_long');}
  if(labels.has('RETEST_HOLD_BELOW')){short+=2;reasons.push('retest_short');}
  if(labels.has('ENGULFING_UP')||labels.has('LONG_LOWER_WICK')) long+=1;
  if(labels.has('ENGULFING_DOWN')||labels.has('LONG_UPPER_WICK')) short+=1;
  if(priceAction.volume?.elevated){ if(long>short) long+=1; else if(short>long) short+=1; reasons.push('elevated_volume'); }
  const vp=chart.vwap?.position; if(vp==='ABOVE') long+=1; if(vp==='BELOW') short+=1;
  return {long,short,reasons};
}

export function evaluateSelectiveSignal({bars=[],minimumScore=5,minimumMargin=2}={}){
  const chart=analyzeChartStructure({bars});
  const priceAction=analyzePriceActionFeatures({bars});
  const setup=analyzeChartSetupContext({bars});
  if(chart.status!=='CHART_CONTEXT_READY'||priceAction.status!=='PRICE_ACTION_FEATURES_READY'||setup.status!=='SETUP_CONTEXT_READY') return Object.freeze({phase:'56-selective',status:'ABSTAIN',signal:0,reason:'CONTEXT_NOT_READY',executionAllowed:false,transmitted:false,safety:PHASE56_SELECTIVE_SAFETY});
  const s=scoreConfluence(chart,priceAction,setup); const best=Math.max(s.long,s.short),margin=Math.abs(s.long-s.short);
  if(best<minimumScore||margin<minimumMargin) return Object.freeze({phase:'56-selective',status:'ABSTAIN',signal:0,longScore:s.long,shortScore:s.short,margin,reasons:s.reasons,evaluationOnly:true,executionAllowed:false,transmitted:false,safety:PHASE56_SELECTIVE_SAFETY});
  const signal=s.long>s.short?1:-1;
  return Object.freeze({phase:'56-selective',status:'SELECTIVE_SIGNAL',signal,longScore:s.long,shortScore:s.short,margin,reasons:s.reasons,evaluationOnly:true,recommendationAllowed:false,paperTradingAllowed:false,executionAllowed:false,transmitted:false,safety:PHASE56_SELECTIVE_SAFETY});
}
