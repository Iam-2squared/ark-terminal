export const PHASE57_P25_2E_SAFETY=Object.freeze({
  phase:'57.p25.2e.frozen-day-session-ledger',
  mode:'READ_ONLY_FROZEN_DAY_DECISION_LEDGER',
  researchOnly:true,
  executionAllowed:false,
  brokerWriteAllowed:false,
  excelOrderWriteAllowed:false,
  rssOrderFunctionAllowed:false,
  liveTradingAllowed:false,
  paperTradingAllowed:false,
  automaticPromotionAllowed:false,
  productionUpdateAllowed:false,
  transmitted:false,
  freshHoldoutConsumed:false,
});

export const PHASE57_P25_2E_POLICY=Object.freeze({
  frozenPhase57PolicyId:'PHASE57_P24_COMBINED_PROSPECTIVE_V1',
  expectedVariants:Object.freeze({
    FIXED_5:5,
    OLD_FIXED_30:30,
    DYNAMIC_30:30,
    DYNAMIC_40:40,
    DYNAMIC_50:50,
  }),
  requireNestedDynamicMembership:true,
  requireOutcomeFreeCurrentDecision:true,
  requireCompleteTargetUnionAtFeatureCutoffForComparison:true,
  entryThresholdRelaxationAllowed:false,
  universeSizeSelectionFromOuterOosAllowed:false,
  postHocWinnerFilteringAllowed:false,
  microstructureMayChangeFrozenEntry:false,
});

const FORBIDDEN_CURRENT_OUTCOME_KEYS=Object.freeze([
  'outcomeAt','outcome','outcomes','label','actualReturnPct','futureBars','futureReturnPct',
  'realizedReturn','realizedReturnPct','grossReturnPct','netReturnPct','mfePct','maePct',
  'exitTimestamp','exitReason','hit','target','tradeWin','outerOosProfitFactor',
]);

const JST=new Intl.DateTimeFormat('en-CA',{
  timeZone:'Asia/Tokyo',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hourCycle:'h23',
});

function normalizeSymbol(value){return String(value??'').trim().toUpperCase();}
function finite(value){return value!==null&&value!==undefined&&value!==''&&Number.isFinite(Number(value));}
function jstDate(timestamp){
  const ms=Date.parse(String(timestamp??''));
  if(!Number.isFinite(ms))return null;
  const parts=Object.fromEntries(JST.formatToParts(new Date(ms)).map(x=>[x.type,x.value]));
  return `${parts.year}-${parts.month}-${parts.day}`;
}
function sortedUnique(values){return [...new Set(values.map(normalizeSymbol).filter(Boolean))].sort();}

function validateUniverseRecord(record){
  if(record?.ready!==true||!record?.variants)throw new Error('P25.2E requires a ready frozen pre-open universe record');
  const sessionDate=String(record.sessionDate??'').trim();
  if(!/^\d{4}-\d{2}-\d{2}$/.test(sessionDate))throw new Error('frozen universe sessionDate must be YYYY-MM-DD');
  const normalized={};
  for(const [variant,count] of Object.entries(PHASE57_P25_2E_POLICY.expectedVariants)){
    const values=record.variants?.[variant];
    if(!Array.isArray(values)||values.length!==count)throw new Error(`${variant} must contain exactly ${count} frozen symbols`);
    const symbols=values.map(normalizeSymbol);
    if(symbols.some(x=>!x)||new Set(symbols).size!==count)throw new Error(`${variant} contains blank or duplicate symbols`);
    normalized[variant]=Object.freeze(symbols);
  }
  const d30=normalized.DYNAMIC_30,d40=normalized.DYNAMIC_40,d50=normalized.DYNAMIC_50;
  if(!d30.every((x,i)=>d40[i]===x)||!d40.every((x,i)=>d50[i]===x))throw new Error('Dynamic30/40/50 memberships must remain nested prefixes');
  const targetUnion=sortedUnique(Object.values(normalized).flat());
  return Object.freeze({sessionDate,variants:Object.freeze(normalized),targetUnion:Object.freeze(targetUnion)});
}

function rejectOutcomeFields(object,label){
  if(!object||typeof object!=='object')return;
  const forbidden=FORBIDDEN_CURRENT_OUTCOME_KEYS.filter(key=>Object.prototype.hasOwnProperty.call(object,key));
  if(forbidden.length)throw new Error(`${label} contains forbidden current outcome fields: ${forbidden.join(',')}`);
}

function unwrapPhase57Result(input){
  if(!input||typeof input!=='object')throw new TypeError('phase57 result must be an object');
  const snapshot=input.snapshot&&typeof input.snapshot==='object'?input.snapshot:null;
  const phase57=input.phase57&&typeof input.phase57==='object'?input.phase57:null;
  const decision=phase57?.decision??snapshot?.decision??input.decision??null;
  const provenance=input.provenance&&typeof input.provenance==='object'?input.provenance:{};
  const symbol=normalizeSymbol(input.currentSymbol??provenance.currentSymbol??snapshot?.symbol??decision?.symbol);
  const featureCutoff=String(decision?.asOf??snapshot?.asOf??provenance.currentFeatureCutoff??'').trim();
  if(!snapshot||!phase57||!decision)throw new Error('phase57 result must contain snapshot, phase57 and phase57.decision');
  if(!symbol)throw new Error('phase57 result current symbol is missing');
  if(!Number.isFinite(Date.parse(featureCutoff)))throw new Error(`phase57 feature cutoff is invalid for ${symbol}`);
  rejectOutcomeFields(snapshot,'phase57 snapshot');
  rejectOutcomeFields(decision,'phase57 decision');
  if(decision.futureOutcomeUsed!==false)throw new Error(`phase57 decision must attest futureOutcomeUsed=false for ${symbol}`);
  if(decision.frozenByPhase57!==true||decision.pointInTimeOnly!==true)throw new Error(`phase57 decision is not frozen point-in-time for ${symbol}`);
  const context=decision.context&&typeof decision.context==='object'?decision.context:{};
  const direction=Number(decision.direction);
  if(![-1,0,1].includes(direction))throw new Error(`invalid Phase57 direction for ${symbol}`);
  const signalEligible=context.signalEligible===true;
  if(direction!==0&&!signalEligible)throw new Error(`non-WAIT Phase57 direction must be signalEligible for ${symbol}`);
  if(direction===0&&signalEligible)throw new Error(`WAIT Phase57 direction cannot be signalEligible for ${symbol}`);
  if(direction!==0&&!Number.isInteger(Number(context.selectedHorizonBars)))throw new Error(`signal missing selected horizon for ${symbol}`);
  if(direction!==0&&!finite(decision.confidence))throw new Error(`signal missing confidence for ${symbol}`);
  const policyId=String(input.policyId??input.frozenPolicyId??PHASE57_P25_2E_POLICY.frozenPhase57PolicyId);
  if(policyId!==PHASE57_P25_2E_POLICY.frozenPhase57PolicyId)throw new Error(`unexpected Phase57 policyId for ${symbol}: ${policyId}`);
  return Object.freeze({input,snapshot,phase57,decision,context,provenance,symbol,featureCutoff,direction,signalEligible,policyId});
}

function sectorMap(record){
  const map=new Map();
  for(const row of record?.rankAudit?.day50??[]){
    const symbol=normalizeSymbol(row?.symbol);
    if(symbol)map.set(symbol,String(row?.sector??'UNKNOWN'));
  }
  return map;
}

function membershipsFor(symbol,variants){
  return Object.freeze(Object.entries(variants).filter(([,symbols])=>symbols.includes(symbol)).map(([variant])=>variant));
}

function cutoffAudit(attempts,targetUnion){
  const groups=new Map();
  for(const attempt of attempts){
    if(!groups.has(attempt.featureCutoff))groups.set(attempt.featureCutoff,new Set());
    groups.get(attempt.featureCutoff).add(attempt.symbol);
  }
  return Object.freeze([...groups.entries()].sort(([a],[b])=>a.localeCompare(b)).map(([featureCutoff,symbols])=>{
    const missing=targetUnion.filter(symbol=>!symbols.has(symbol));
    return Object.freeze({
      featureCutoff,
      expectedTargetCount:targetUnion.length,
      scoredTargetCount:symbols.size,
      complete:missing.length===0,
      missingSymbols:Object.freeze(missing),
    });
  }));
}

/**
 * Convert outcome-free prospective Phase57 decisions into the immutable Day ledger
 * consumed later by the P25.2D five-variant outcome join. A signal is comparison-
 * eligible only when every symbol in the precommitted five-variant target union was
 * scored at the same feature cutoff. Partial cutoffs are retained but cannot create
 * comparison trades, preventing selective capture from inflating Dynamic N results.
 */
export function buildP252FrozenDaySessionLedger({
  universeRecord,
  phase57Results=[],
}={}){
  const universe=validateUniverseRecord(universeRecord);
  const targetSet=new Set(universe.targetUnion);
  const sectors=sectorMap(universeRecord);
  const attempts=[];
  const seen=new Set();
  for(const raw of Array.isArray(phase57Results)?phase57Results:[]){
    const item=unwrapPhase57Result(raw);
    if(!targetSet.has(item.symbol))throw new Error(`Phase57 result symbol is outside frozen P25.2 target union: ${item.symbol}`);
    if(jstDate(item.featureCutoff)!==universe.sessionDate)throw new Error(`Phase57 feature cutoff is outside frozen session ${universe.sessionDate}: ${item.symbol}`);
    const sourceSession=String(item.provenance?.currentSessionDate??item.input?.sessionDate??item.snapshot?.sessionDate??'').trim();
    if(sourceSession&&sourceSession!==universe.sessionDate)throw new Error(`Phase57 source session mismatch for ${item.symbol}`);
    const key=`${item.symbol}|${item.featureCutoff}`;
    if(seen.has(key))throw new Error(`duplicate Phase57 decision for ${key}`);
    seen.add(key);
    attempts.push(Object.freeze({
      symbol:item.symbol,
      sessionDate:universe.sessionDate,
      featureCutoff:item.featureCutoff,
      status:String(item.phase57?.status??item.input?.status??'UNKNOWN'),
      direction:item.direction,
      signalEligible:item.signalEligible,
      confidence:finite(item.decision.confidence)?Number(item.decision.confidence):null,
      probability:finite(item.context.probability)?Number(item.context.probability):null,
      selectedHorizonBars:Number.isInteger(Number(item.context.selectedHorizonBars))?Number(item.context.selectedHorizonBars):null,
      selectedFeatureFamily:item.context.selectedFeatureFamily??item.decision.setup??null,
      selectedModelType:item.context.selectedModelType??null,
      selectedConfigId:item.context.selectedConfigId??null,
      selectedThreshold:finite(item.context.selectedThreshold)?Number(item.context.selectedThreshold):null,
      modelId:item.phase57?.modelId??null,
      artifactSha256:item.phase57?.artifactSha256??null,
      sourceBarCloseAt:item.snapshot?.context?.sourceBarCloseAt??null,
      variantMemberships:membershipsFor(item.symbol,universe.variants),
      sector:sectors.get(item.symbol)??'UNKNOWN',
    }));
  }
  attempts.sort((a,b)=>a.featureCutoff.localeCompare(b.featureCutoff)||a.symbol.localeCompare(b.symbol));
  const cutoffs=cutoffAudit(attempts,universe.targetUnion);
  const completeCutoffs=new Set(cutoffs.filter(x=>x.complete).map(x=>x.featureCutoff));
  const rawSignals=attempts.filter(x=>x.signalEligible&&x.direction!==0);
  const comparisonSignals=rawSignals.filter(x=>completeCutoffs.has(x.featureCutoff));
  const frozenTrades=Object.freeze(comparisonSignals.map(row=>Object.freeze({
    entryAccepted:true,
    symbol:row.symbol,
    sessionDate:row.sessionDate,
    entryTimestamp:row.featureCutoff,
    featureCutoff:row.featureCutoff,
    signalDirection:row.direction,
    direction:row.direction===1?'LONG':'SHORT',
    baseHorizonBars:row.selectedHorizonBars,
    confidence:row.confidence,
    probability:row.probability,
    selectedFeatureFamily:row.selectedFeatureFamily,
    selectedModelType:row.selectedModelType,
    selectedConfigId:row.selectedConfigId,
    selectedThreshold:row.selectedThreshold,
    modelId:row.modelId,
    artifactSha256:row.artifactSha256,
    sector:row.sector,
    variantMemberships:row.variantMemberships,
    outcomePending:true,
    frozenBeforeOutcome:true,
    currentOutcomeUsed:false,
  })));
  const eligibleDecisionCountsByVariant={};
  for(const variant of Object.keys(PHASE57_P25_2E_POLICY.expectedVariants)){
    eligibleDecisionCountsByVariant[variant]=attempts.filter(row=>completeCutoffs.has(row.featureCutoff)&&row.variantMemberships.includes(variant)).length;
  }
  return Object.freeze({
    phase:'57.p25.2e.frozen-day-session-ledger',
    status:cutoffs.length&&completeCutoffs.size===cutoffs.length?'FROZEN_DAY_SESSION_LEDGER_READY':'FROZEN_DAY_SESSION_LEDGER_PARTIAL',
    sessionDate:universe.sessionDate,
    frozenTargetSymbolCount:universe.targetUnion.length,
    frozenTargetSymbols:universe.targetUnion,
    inputDecisionCount:Array.isArray(phase57Results)?phase57Results.length:0,
    acceptedDecisionCount:attempts.length,
    rawFrozenSignalCount:rawSignals.length,
    comparisonEligibleFrozenSignalCount:frozenTrades.length,
    featureCutoffCount:cutoffs.length,
    completeFeatureCutoffCount:completeCutoffs.size,
    cutoffAudit:cutoffs,
    decisionAttempts:Object.freeze(attempts),
    frozenTrades,
    eligibleDecisionCountsByVariant:Object.freeze(eligibleDecisionCountsByVariant),
    methodology:Object.freeze({
      frozenUniverseBeforeSession:true,
      phase57PolicyFrozen:true,
      currentOutcomeFieldsForbidden:true,
      incompleteCutoffSignalsRetainedButExcludedFromComparison:true,
      completeTargetUnionRequiredAtEachComparisonCutoff:true,
      entryThresholdRelaxed:false,
      microstructureChangesFrozenEntry:false,
      universeSizeSelectedFromOuterOos:false,
      postHocWinnerFiltering:false,
      freshHoldoutConsumed:false,
    }),
    safety:PHASE57_P25_2E_SAFETY,
  });
}

export default {buildP252FrozenDaySessionLedger,PHASE57_P25_2E_POLICY,PHASE57_P25_2E_SAFETY};
