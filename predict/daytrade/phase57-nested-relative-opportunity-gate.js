import { fitHistoricalAnalogOpportunity,P23_9B_CONFIG,PHASE57_P23_9B_SAFETY } from './phase57-nonlinear-mfe-mae-intelligence.js';

export const PHASE57_P23_9C_SAFETY=Object.freeze({...PHASE57_P23_9B_SAFETY,mode:'PHASE57_NESTED_RELATIVE_OPPORTUNITY_RESEARCH_ONLY'});
export const P23_9C_CONFIG=Object.freeze({
  calibrationSessionCount:5,
  maxCalibrationRows:600,
  minimumCalibrationSignals:25,
  minimumCalibrationNetPct:0.05,
  minimumCalibrationProfitFactor:1.15,
  analogConfig:Object.freeze({...P23_9B_CONFIG,expectedRatchetNetFloorPct:-Infinity,winProbabilityFloor:0,opportunityProbabilityFloor:0,mfeMinusAdverseFloorPct:-Infinity}),
});

const finite=v=>v!==null&&v!==undefined&&Number.isFinite(Number(v));
const mean=a=>a.length?a.reduce((s,x)=>s+Number(x),0)/a.length:0;
const quantile=(a,p)=>{const x=a.map(Number).filter(Number.isFinite).sort((u,v)=>u-v);if(!x.length)return null;const i=(x.length-1)*p,l=Math.floor(i),h=Math.ceil(i);return l===h?x[l]:x[l]+(x[h]-x[l])*(i-l);};
function summarize(a){const x=a.map(Number).filter(Number.isFinite),pos=x.filter(v=>v>0).reduce((s,v)=>s+v,0),neg=-x.filter(v=>v<0).reduce((s,v)=>s+v,0);return Object.freeze({signalCount:x.length,hitRate:x.length?x.filter(v=>v>0).length/x.length:null,netAverageReturnPct:x.length?mean(x):null,profitFactor:neg>0?pos/neg:(pos>0?Infinity:null)});}

const SCORE_KINDS=Object.freeze(['OPPORTUNITY_PROBABILITY','RATCHET_NET','RISK_ADJUSTED','WIN_OPPORTUNITY_BLEND']);
const PERCENTILES=Object.freeze([0.60,0.70,0.80]);
export const P23_9C_CANDIDATES=Object.freeze(SCORE_KINDS.flatMap(kind=>PERCENTILES.map(percentile=>Object.freeze({id:`${kind}_TOP_${Math.round((1-percentile)*100)}`,kind,percentile}))));

export function opportunityScore(prediction,kind){
  if(kind==='OPPORTUNITY_PROBABILITY')return Number(prediction.opportunityProbability);
  if(kind==='RATCHET_NET')return Number(prediction.expectedRatchetNetReturnPct);
  if(kind==='WIN_OPPORTUNITY_BLEND')return 0.5*Number(prediction.winProbability)+0.5*Number(prediction.opportunityProbability);
  if(kind==='RISK_ADJUSTED')return Number(prediction.expectedRatchetNetReturnPct)+0.35*Number(prediction.expectedMfeMinusAdversePct)+0.10*(Number(prediction.opportunityProbability)-0.5);
  throw new Error(`unknown score kind ${kind}`);
}

function deterministicSample(rows,maxRows){
  const sorted=[...rows].sort((a,b)=>`${a.featureCutoff}|${a.symbol}|${a.direction}`.localeCompare(`${b.featureCutoff}|${b.symbol}|${b.direction}`));
  if(sorted.length<=maxRows)return sorted;
  const stride=Math.ceil(sorted.length/maxRows),out=[];for(let i=0;i<sorted.length;i+=stride)out.push(sorted[i]);return out.slice(0,maxRows);
}

export function calibrateRelativeOpportunityGate(trainingExamples=[],config={}){
  const cfg={...P23_9C_CONFIG,...config,analogConfig:{...P23_9C_CONFIG.analogConfig,...(config.analogConfig||{})}};
  const dates=[...new Set(trainingExamples.map(r=>String(r.sessionDate)))].sort();
  if(dates.length<Number(cfg.calibrationSessionCount)+3)return Object.freeze({selected:null,status:'INSUFFICIENT_CALIBRATION_SESSIONS'});
  const calibrationDates=dates.slice(-Number(cfg.calibrationSessionCount));
  const calibrationStart=calibrationDates[0];
  const fitRows=trainingExamples.filter(r=>String(r.sessionDate)<calibrationStart);
  const rawCalibration=trainingExamples.filter(r=>calibrationDates.includes(String(r.sessionDate)));
  const calibrationRows=deterministicSample(rawCalibration,Number(cfg.maxCalibrationRows));
  if(fitRows.length<Number(cfg.analogConfig.minTrainRows)||calibrationRows.length<Number(cfg.minimumCalibrationSignals))return Object.freeze({selected:null,status:'INSUFFICIENT_CALIBRATION_ROWS',fitRows:fitRows.length,calibrationRows:calibrationRows.length,calibrationDates});
  const model=fitHistoricalAnalogOpportunity(fitRows,cfg.analogConfig);
  const predictions=[];
  for(const row of calibrationRows){const p=model.predict(row);if(!p)continue;predictions.push(Object.freeze({row,p,realized:Number(row.realizedRatchetNetReturnPct)}));}
  const candidates=[];
  for(const spec of P23_9C_CANDIDATES){
    const scores=predictions.map(x=>opportunityScore(x.p,spec.kind));
    const threshold=quantile(scores,spec.percentile);
    const selected=predictions.filter(x=>opportunityScore(x.p,spec.kind)>=threshold);
    const summary=summarize(selected.map(x=>x.realized));
    candidates.push(Object.freeze({...spec,threshold,...summary,coverage:predictions.length?selected.length/predictions.length:0,selectionSource:'PRIOR_SESSION_CALIBRATION_ONLY'}));
  }
  const eligible=candidates.filter(c=>c.signalCount>=Number(cfg.minimumCalibrationSignals)&&finite(c.netAverageReturnPct)&&Number(c.netAverageReturnPct)>=Number(cfg.minimumCalibrationNetPct)&&finite(c.profitFactor)&&Number(c.profitFactor)>=Number(cfg.minimumCalibrationProfitFactor));
  eligible.sort((a,b)=>Number(b.netAverageReturnPct)-Number(a.netAverageReturnPct)||Number(b.profitFactor)-Number(a.profitFactor)||Number(b.signalCount)-Number(a.signalCount));
  const observed=[...candidates].sort((a,b)=>(Number(b.netAverageReturnPct)||-Infinity)-(Number(a.netAverageReturnPct)||-Infinity));
  return Object.freeze({status:eligible.length?'CALIBRATED_GATE_SELECTED':'NO_ELIGIBLE_CALIBRATION_GATE',selected:eligible[0]??null,bestObserved:observed[0]??null,
    fitRows:fitRows.length,calibrationRows:predictions.length,calibrationDates:Object.freeze(calibrationDates),candidates:Object.freeze(candidates),
    integrity:Object.freeze({calibrationPrecedesFrozenWindow:true,frozenOuterOutcomesUsedForSelection:false,sameSessionTrainingForbidden:true,candidateFamilyInformedByPriorDevelopmentDiagnostics:true})});
}

export function evaluateNestedRelativeOpportunity({trainingExamples=[],frozenTestExamples=[],config={}}={}){
  const cfg={...P23_9C_CONFIG,...config,analogConfig:{...P23_9C_CONFIG.analogConfig,...(config.analogConfig||{})}};
  const frozenDates=[...new Set(frozenTestExamples.map(r=>String(r.sessionDate)))].sort();
  if(!frozenDates.length)return Object.freeze({phase:'57.p23.9c',status:'NO_FROZEN_TEST_ROWS',executionAllowed:false});
  const earliestFrozen=frozenDates[0];
  const calibrationSource=trainingExamples.filter(r=>String(r.sessionDate)<earliestFrozen);
  const calibration=calibrateRelativeOpportunityGate(calibrationSource,cfg);
  if(!calibration.selected)return Object.freeze({phase:'57.p23.9c',status:'ABSTAIN_NO_PRIOR_CALIBRATED_GATE',calibration,predictions:Object.freeze([]),allFrozenRatchet:summarize([]),gatedFrozenRatchet:summarize([]),
    integrity:Object.freeze({frozenOuterOutcomesUsedForSelection:false,calibrationPrecedesFrozenWindow:true}),edgeClaimAllowed:false,recommendationAllowed:false,executionAllowed:false,brokerWriteAllowed:false,excelOrderWriteAllowed:false,rssOrderFunctionAllowed:false,liveTradingAllowed:false,paperTradingAllowed:false,automaticPromotionAllowed:false,productionUpdateAllowed:false,overnightHoldingAllowed:false,transmitted:false,safety:PHASE57_P23_9C_SAFETY});
  const selected=calibration.selected,predictions=[];
  for(const date of frozenDates){const historical=trainingExamples.filter(r=>String(r.sessionDate)<date);if(historical.length<Number(cfg.analogConfig.minTrainRows))continue;const model=fitHistoricalAnalogOpportunity(historical,cfg.analogConfig);for(const row of frozenTestExamples.filter(r=>String(r.sessionDate)===date)){const p=model.predict(row);if(!p)continue;const score=opportunityScore(p,selected.kind);predictions.push(Object.freeze({symbol:row.symbol,sessionDate:row.sessionDate,featureCutoff:row.featureCutoff,direction:row.direction,...p,relativeGateScore:score,relativeGateThreshold:selected.threshold,relativeGateKind:selected.kind,gatePass:score>=Number(selected.threshold),realizedRatchetNetReturnPct:Number(row.realizedRatchetNetReturnPct),outerOutcomeUsedForSelection:false}));}}
  const gated=predictions.filter(r=>r.gatePass),all=summarize(predictions.map(r=>r.realizedRatchetNetReturnPct)),gate=summarize(gated.map(r=>r.realizedRatchetNetReturnPct));
  return Object.freeze({phase:'57.p23.9c-nested-relative-opportunity',status:'NESTED_RELATIVE_OPPORTUNITY_EVALUATED',predictionCount:predictions.length,gateCount:gated.length,gateCoverage:predictions.length?gated.length/predictions.length:0,
    allFrozenRatchet:all,gatedFrozenRatchet:gate,deltas:Object.freeze({netAverageReturnPct:gate.netAverageReturnPct==null||all.netAverageReturnPct==null?null:gate.netAverageReturnPct-all.netAverageReturnPct,profitFactor:finite(gate.profitFactor)&&finite(all.profitFactor)?gate.profitFactor-all.profitFactor:null,hitRate:gate.hitRate==null||all.hitRate==null?null:gate.hitRate-all.hitRate}),
    calibration,predictions:Object.freeze(predictions),integrity:Object.freeze({trainingUsesPriorSessionsOnly:true,sameSessionTrainingForbidden:true,calibrationPrecedesFrozenWindow:true,frozenOuterOutcomesUsedForSelection:false,futureExtremaUsedAsFeatures:false,candidateFamilyInformedByPriorDevelopmentDiagnostics:true,developmentOnly:true,finalUntouchedOosEdgeClaimAllowed:false}),
    edgeClaimAllowed:false,recommendationAllowed:false,executionAllowed:false,brokerWriteAllowed:false,excelOrderWriteAllowed:false,rssOrderFunctionAllowed:false,liveTradingAllowed:false,paperTradingAllowed:false,automaticPromotionAllowed:false,productionUpdateAllowed:false,overnightHoldingAllowed:false,transmitted:false,safety:PHASE57_P23_9C_SAFETY});
}

export default {PHASE57_P23_9C_SAFETY,P23_9C_CONFIG,P23_9C_CANDIDATES,opportunityScore,calibrateRelativeOpportunityGate,evaluateNestedRelativeOpportunity};
