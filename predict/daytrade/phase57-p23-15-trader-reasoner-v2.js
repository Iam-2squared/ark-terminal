import { stripOutcomeFields } from './phase57-p23-14-blind-reasoner-benchmark.js';

export const P23_15_TRADER_REASONER_POLICY = Object.freeze({
  phase:'57.p23.15',
  id:'TRADER_STYLE_CAUSAL_REASONER_V2',
  purpose:'ASSESS_TRADEABILITY_BEFORE_DIRECTIONAL_OUTCOME_IS_VISIBLE',
  developmentHypothesisDerivedFromP2314:true,
  thresholdSearchPerformed:false,
  externalVisionModelCalled:false,
  outcomeVisibleAtDecisionTime:false,
  recommendationAllowed:false,
  edgeClaimAllowed:false,
});

export const PHASE57_P23_15_SAFETY = Object.freeze({
  mode:'PHASE57_P23_15_TRADER_REASONER_READ_ONLY_RESEARCH',
  executionAllowed:false, brokerWriteAllowed:false, excelOrderWriteAllowed:false,
  rssOrderFunctionAllowed:false, liveTradingAllowed:false, paperTradingAllowed:false,
  automaticPromotionAllowed:false, productionUpdateAllowed:false,
  overnightHoldingAllowed:false, transmitted:false,
});

const finite = v => v !== null && v !== undefined && v !== '' && Number.isFinite(Number(v));
const clamp = (v,lo=0,hi=1) => Math.max(lo,Math.min(hi,Number(v)));
const val = (obj,key,fallback=.5) => finite(obj?.[key]) ? clamp(obj[key]) : fallback;

function setupFamily(setup='') {
  const s=String(setup);
  if(s.startsWith('BREAKOUT_CONTINUATION_')) return 'BREAKOUT';
  if(s.startsWith('MOMENTUM_CONTINUATION_')) return 'MOMENTUM';
  if(s.startsWith('TREND_PULLBACK_')) return 'PULLBACK';
  if(s.startsWith('RETEST_CONTINUATION_')) return 'RETEST';
  if(s.startsWith('FAILED_BREAKOUT_REVERSAL_')) return 'FAILED_BREAKOUT';
  return 'OTHER';
}

function harmonic(values) {
  const xs=values.filter(x=>finite(x)).map(x=>Math.max(.05,Number(x)));
  return xs.length ? xs.length / xs.reduce((s,x)=>s+1/x,0) : .5;
}

export function buildTraderReasoningDecision(record={}) {
  const x=stripOutcomeFields(record);
  const c=x.visualComponents ?? {};
  const structure=val(c,'structureCoherence');
  const pressure=val(c,'directionalPressure');
  const wick=val(c,'wickControl');
  const participation=val(c,'participation');
  const extension=val(c,'extensionHealth');
  const room=val(c,'spaceToObstacle');
  const volatility=val(c,'volatilityTransition');
  const geometry=val(c,'setupGeometryFit');
  const family=setupFamily(x.setup);
  const direction=x.direction;

  // P23.14 development showed strong UP/DOWN asymmetry. We encode that only as a
  // development hypothesis: shorts need clearer higher-timeframe alignment.
  const structureFloor = direction === 'DOWN' ? .65 : .55;
  const veto=[];
  if(direction==='NONE') veto.push('NO_DIRECTION');
  if(structure < structureFloor) veto.push('HTF_NOT_ALIGNED_ENOUGH');
  if(room < .40) veto.push('INSUFFICIENT_ROOM_TO_OBSTACLE');
  if(extension < .35) veto.push('OVEREXTENDED');
  if(geometry < .45) veto.push('SETUP_GEOMETRY_WEAK');
  if(wick < .30) veto.push('ADVERSE_REJECTION_RISK');

  if(family==='BREAKOUT') {
    if(geometry < .55) veto.push('BREAKOUT_NOT_CLEAN');
    if(participation < .30) veto.push('BREAKOUT_PARTICIPATION_WEAK');
  } else if(family==='MOMENTUM') {
    if(pressure < .55) veto.push('MOMENTUM_PRESSURE_WEAK');
    if(participation < .35) veto.push('MOMENTUM_PARTICIPATION_WEAK');
    if(extension < .45) veto.push('MOMENTUM_TOO_EXTENDED');
  } else if(family==='PULLBACK' || family==='RETEST') {
    if(geometry < .50) veto.push('PULLBACK_RETEST_GEOMETRY_WEAK');
    if(extension < .40) veto.push('PULLBACK_RETEST_LOCATION_POOR');
  } else if(family==='FAILED_BREAKOUT') {
    if(geometry < .50) veto.push('REVERSAL_GEOMETRY_WEAK');
    if(wick < .40) veto.push('REVERSAL_REJECTION_NOT_CLEAR');
  }

  const critical=harmonic([structure,room,extension,geometry,wick]);
  const evidence=clamp(.18*structure+.16*room+.14*extension+.14*geometry+.12*pressure+.10*wick+.09*participation+.07*volatility);
  const tradeabilityScore=clamp(.60*critical+.40*evidence);
  const decision = veto.length===0 && tradeabilityScore>=.55 ? 'QUALIFIED' : 'WAIT';
  const htfContext = structure>=.70 ? 'SUPPORTIVE' : structure<=.35 ? 'CONFLICT' : 'MIXED';

  return Object.freeze({
    key:`${x.symbol}|${x.featureCutoff}|${x.setup}`,
    symbol:x.symbol, sessionDate:x.sessionDate, featureCutoff:x.featureCutoff,
    setup:x.setup, setupFamily:family, direction,
    decision, tradeabilityScore, criticalBalance:critical, evidenceScore:evidence,
    higherTimeframeContext:htfContext,
    primaryScenario: direction==='NONE' ? 'OBSERVE' : `${family}_${direction}_CONTINUATION_OR_FOLLOW_THROUGH`,
    alternativeScenario: direction==='UP' ? 'FAILURE_OR_REVERSAL_DOWN' : direction==='DOWN' ? 'FAILURE_OR_REVERSAL_UP' : 'NONE',
    vetoReasons:Object.freeze([...new Set(veto)]),
    risk:Object.freeze({ obstacle:clamp(1-room), extension:clamp(1-extension), rejection:clamp(1-wick) }),
    evidence:Object.freeze({ structure,pressure,wick,participation,extension,room,volatility,geometry }),
    causalInputsOnly:true, futureOutcomeVisible:false, outcomeUsedForDecision:false,
    thresholdSearchPerformed:false, decisionUsedForLiveEntry:false,
    externalVisionModelCalled:false, recommendationAllowed:false,
    ...PHASE57_P23_15_SAFETY,
  });
}

export default { P23_15_TRADER_REASONER_POLICY, PHASE57_P23_15_SAFETY, buildTraderReasoningDecision };
