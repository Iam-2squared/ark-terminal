import crypto from 'node:crypto';
import { selectInnerAdaptiveHorizon } from './phase57-nested-adaptive-horizon.js';
import { trainModel } from '../models/phase47-real-training.js';

export const PHASE57_P21_PROSPECTIVE_SAFETY = Object.freeze({
  phase:'57.p21.prospective-frozen-base',
  mode:'PHASE57_P21_PROSPECTIVE_READ_ONLY_RESEARCH',
  researchOnly:true,
  executionAllowed:false,
  brokerWriteAllowed:false,
  excelOrderWriteAllowed:false,
  rssOrderFunctionAllowed:false,
  liveTradingAllowed:false,
  paperTradingAllowed:false,
  automaticPromotionAllowed:false,
  productionUpdateAllowed:false,
  overnightHoldingAllowed:false,
  transmitted:false,
  freshHoldoutConsumed:false,
});

const finite=value=>value!==null&&value!==undefined&&value!==''&&Number.isFinite(Number(value));
const rowKey=row=>`${row?.symbol??''}|${row?.sessionDate??''}|${row?.featureCutoff??''}`;
const FORBIDDEN_CURRENT_OUTCOME_KEYS=Object.freeze([
  'outcomeAt','outcome','outcomes','label','actualReturnPct','futureBars','realizedReturn',
  'grossReturnPct','netReturnPct','mfePct','maePct','exitTimestamp','exitReason','hit','target',
]);

function validPriorRow(row,asOfMs){
  const cutoff=Date.parse(row?.featureCutoff??'');
  const outcome=Date.parse(row?.outcomeAt??'');
  return Boolean(row?.symbol&&row?.sessionDate)&&Number.isFinite(cutoff)&&Number.isFinite(outcome)
    && cutoff<outcome&&outcome<=asOfMs&&row?.pointInTimeValid!==false
    && finite(row?.label)&&finite(row?.actualReturnPct)&&row?.features&&typeof row.features==='object';
}

function normalizedPriorMap(input={},asOfMs){
  const entries=input instanceof Map?[...input.entries()]:Object.entries(input??{});
  const map=new Map(entries.map(([h,rows])=>[
    Number(h),(Array.isArray(rows)?rows:[]).filter(row=>validPriorRow(row,asOfMs)),
  ]).filter(([h,rows])=>Number.isInteger(h)&&h>0&&rows.length).sort((a,b)=>a[0]-b[0]));
  if(!map.size)return map;
  const sets=[...map.values()].map(rows=>new Set(rows.map(rowKey)));
  const common=new Set([...sets[0]].filter(key=>sets.every(set=>set.has(key))));
  return new Map([...map].map(([h,rows])=>[h,rows.filter(row=>common.has(rowKey(row)))]).filter(([,rows])=>rows.length));
}

function currentRowForHorizon(input,horizon){
  const rows=input instanceof Map?input.get(horizon):input?.[horizon]??input?.[String(horizon)];
  const row=Array.isArray(rows)?rows[0]:rows;
  return row&&typeof row==='object'?row:null;
}

function projectRow(row,keys=[]){
  return {
    ...row,
    features:Object.fromEntries((Array.isArray(keys)?keys:[])
      .filter(key=>finite(row?.features?.[key]))
      .map(key=>[key,Number(row.features[key])])),
  };
}

function defaultFitPredictor(rows,config){
  const model=trainModel({rows,modelType:config.type,options:config.options});
  return row=>model.predict(row);
}

function artifactHash({selection,trainingRows,asOf}){
  const payload={
    lineage:'PHASE57_P21_NESTED_ADAPTIVE_PROSPECTIVE_V1',
    asOf,
    selection:{
      horizonBars:selection.horizonBars,
      featureFamily:selection.featureFamily,
      featureKeys:selection.featureKeys,
      configId:selection.configId,
      modelType:selection.modelType,
      modelOptions:selection.modelOptions,
      threshold:selection.threshold,
    },
    trainingRows:trainingRows.map(row=>({
      key:rowKey(row),outcomeAt:row.outcomeAt,label:Number(row.label),actualReturnPct:Number(row.actualReturnPct),features:row.features,
    })),
  };
  return crypto.createHash('sha256').update(JSON.stringify(payload)).digest('hex');
}

/**
 * Prospective analogue of the frozen P21 nested-adaptive OOS base used by P24.
 * All model/horizon/feature/threshold selection is performed only on fully-realized
 * rows whose outcomeAt is <= the current feature cutoff. The current row must be
 * outcome-free and is scored exactly once after the prior-only selection/refit.
 */
export function buildProspectiveP21FrozenDecision({
  historicalHorizonRowsByBars={},
  currentRowsByHorizon={},
  options={},
}={}){
  const candidateRows=[];
  const currentEntries=currentRowsByHorizon instanceof Map?[...currentRowsByHorizon.entries()]:Object.entries(currentRowsByHorizon??{});
  for(const [h,value] of currentEntries){
    const row=Array.isArray(value)?value[0]:value;
    if(row&&typeof row==='object')candidateRows.push([Number(h),row]);
  }
  if(!candidateRows.length)return Object.freeze({phase:'57.p21.prospective-frozen-base',status:'BLOCKED_NO_CURRENT_FEATURE_ROW',complete:false,safety:PHASE57_P21_PROSPECTIVE_SAFETY});

  const cutoffs=[...new Set(candidateRows.map(([,row])=>String(row.featureCutoff??'')))];
  const asOf=cutoffs.length===1?cutoffs[0]:null;
  const asOfMs=Date.parse(asOf??'');
  const blockers=[];
  if(!asOf||!Number.isFinite(asOfMs))blockers.push('INVALID_OR_MIXED_CURRENT_FEATURE_CUTOFF');
  for(const [,row] of candidateRows){
    const forbidden=FORBIDDEN_CURRENT_OUTCOME_KEYS.filter(key=>Object.prototype.hasOwnProperty.call(row,key));
    if(forbidden.length)blockers.push(`CURRENT_ROW_CONTAINS_OUTCOME_FIELDS:${forbidden.join(',')}`);
    if(!row?.symbol||!row?.sessionDate||!row?.features||typeof row.features!=='object')blockers.push('INVALID_CURRENT_FEATURE_ROW');
    if(row?.pointInTimeValid===false)blockers.push('CURRENT_ROW_POINT_IN_TIME_INVALID');
  }
  if(blockers.length)return Object.freeze({phase:'57.p21.prospective-frozen-base',status:'BLOCKED_CURRENT_ROW_INTEGRITY',complete:false,blockers:Object.freeze(blockers),safety:PHASE57_P21_PROSPECTIVE_SAFETY});

  const priorMap=normalizedPriorMap(historicalHorizonRowsByBars,asOfMs);
  if(!priorMap.size)return Object.freeze({phase:'57.p21.prospective-frozen-base',status:'BLOCKED_NO_FULLY_REALIZED_PRIOR_HISTORY',complete:false,asOf,safety:PHASE57_P21_PROSPECTIVE_SAFETY});

  const selection=selectInnerAdaptiveHorizon(Object.fromEntries(priorMap),options);
  if(!selection.selected)return Object.freeze({
    phase:'57.p21.prospective-frozen-base',status:'ABSTAIN_NO_ELIGIBLE_PRIOR_ONLY_SELECTION',complete:true,decision:Object.freeze({
      direction:0,confidence:null,setup:null,context:Object.freeze({reason:'NO_ELIGIBLE_PRIOR_ONLY_SELECTION'}),asOf,
      frozenByPhase57:true,pointInTimeOnly:true,futureOutcomeUsed:false,thresholdSearchAfterCapture:false,entryRetunedAfterCapture:false,
    }),selection,safety:PHASE57_P21_PROSPECTIVE_SAFETY,
  });

  const picked=selection.selected;
  const current=currentRowForHorizon(currentRowsByHorizon,Number(picked.horizonBars));
  if(!current)return Object.freeze({phase:'57.p21.prospective-frozen-base',status:'BLOCKED_MISSING_CURRENT_SELECTED_HORIZON_ROW',complete:false,selectedHorizonBars:picked.horizonBars,safety:PHASE57_P21_PROSPECTIVE_SAFETY});
  const currentForbidden=FORBIDDEN_CURRENT_OUTCOME_KEYS.filter(key=>Object.prototype.hasOwnProperty.call(current,key));
  if(currentForbidden.length)return Object.freeze({phase:'57.p21.prospective-frozen-base',status:'BLOCKED_CURRENT_SELECTED_ROW_HAS_OUTCOME',complete:false,forbiddenOutcomeFields:Object.freeze(currentForbidden),safety:PHASE57_P21_PROSPECTIVE_SAFETY});

  const trainRows=(priorMap.get(Number(picked.horizonBars))??[]).map(row=>projectRow(row,picked.featureKeys));
  if(!trainRows.length)return Object.freeze({phase:'57.p21.prospective-frozen-base',status:'BLOCKED_NO_SELECTED_HORIZON_TRAINING_ROWS',complete:false,safety:PHASE57_P21_PROSPECTIVE_SAFETY});
  const projectedCurrent=projectRow(current,picked.featureKeys);
  if(!Object.keys(projectedCurrent.features??{}).length)return Object.freeze({phase:'57.p21.prospective-frozen-base',status:'BLOCKED_CURRENT_FEATURE_FAMILY_UNAVAILABLE',complete:false,safety:PHASE57_P21_PROSPECTIVE_SAFETY});

  const config={id:picked.configId,type:picked.modelType,options:picked.modelOptions};
  const fitPredictor=options.fitPredictor??defaultFitPredictor;
  const predictor=fitPredictor(trainRows,config,{horizonBars:picked.horizonBars,featureFamily:picked.featureFamily,threshold:picked.threshold,stage:'PROSPECTIVE_REFIT_PRIOR_ONLY'});
  if(typeof predictor!=='function')throw new TypeError('fitPredictor must return a predictor function');
  const raw=Number(predictor(projectedCurrent));
  if(!Number.isFinite(raw))return Object.freeze({phase:'57.p21.prospective-frozen-base',status:'ABSTAIN_NONFINITE_PROSPECTIVE_SCORE',complete:true,asOf,safety:PHASE57_P21_PROSPECTIVE_SAFETY});
  const probability=Math.max(0.001,Math.min(0.999,raw));
  const confidence=Math.max(probability,1-probability);
  const eligible=confidence>=Number(picked.threshold);
  const direction=eligible?(probability>=0.5?1:-1):0;
  const maxPriorOutcomeAt=trainRows.map(row=>row.outcomeAt).filter(Boolean).sort().at(-1)??null;
  const artifactSha256=artifactHash({selection:picked,trainingRows:trainRows,asOf});
  const modelId=`phase57-p21-prospective-${String(picked.configId).toLowerCase()}-h${Number(picked.horizonBars)}`;
  const decision=Object.freeze({
    direction,
    confidence,
    setup:picked.featureFamily??null,
    context:Object.freeze({
      probability,
      signalEligible:eligible,
      selectedHorizonBars:Number(picked.horizonBars),
      selectedFeatureFamily:picked.featureFamily,
      selectedModelType:picked.modelType,
      selectedConfigId:picked.configId,
      selectedThreshold:Number(picked.threshold),
      priorTrainingRows:trainRows.length,
      maxPriorOutcomeAt,
      selectionSource:'P21_INNER_WALK_FORWARD_PRIOR_ONLY',
    }),
    asOf,
    frozenByPhase57:true,
    pointInTimeOnly:true,
    futureOutcomeUsed:false,
    thresholdSearchAfterCapture:false,
    entryRetunedAfterCapture:false,
  });
  return Object.freeze({
    phase:'57.p21.prospective-frozen-base',
    status:eligible?'PROSPECTIVE_PHASE57_FROZEN_SIGNAL_READY':'PROSPECTIVE_PHASE57_FROZEN_WAIT_READY',
    complete:true,
    decision,
    modelId,
    artifactSha256,
    selection,
    integrity:Object.freeze({
      currentOutcomeFieldsForbidden:true,
      currentOutcomeUsed:false,
      priorRowsFullyRealizedBeforeCurrentCutoff:true,
      horizonFeatureModelThresholdSelectionPriorOnly:true,
      refitPriorOnly:true,
      directionEncoding:'LONG=1,SHORT=-1,WAIT=0',
      freshHoldoutConsumed:false,
    }),
    safety:PHASE57_P21_PROSPECTIVE_SAFETY,
  });
}

export default {buildProspectiveP21FrozenDecision,PHASE57_P21_PROSPECTIVE_SAFETY};