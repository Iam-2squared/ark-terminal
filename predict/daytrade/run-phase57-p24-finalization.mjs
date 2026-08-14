import fs from 'node:fs';

const inputPath=process.env.P24_8_INPUT||'artifacts/phase57-p24-p2350-aligned-COMBINED.json';
const outputPath=process.env.P24_8_OUTPUT||'artifacts/phase57-p24-finalization-COMBINED.json';
const x=JSON.parse(fs.readFileSync(inputPath,'utf8'));

const finite=v=>v!==null&&v!==undefined&&v!==''&&Number.isFinite(Number(v));
const safetyKeys=['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted','freshHoldoutConsumed'];
const fail=[];
const require=(ok,msg)=>{if(!ok)fail.push(msg);};

require(x?.phase==='57.p24.7','input must be P24.7');
require(x?.methodology?.entryAndHorizonFrozen===true,'Entry/horizon must remain frozen');
require(x?.methodology?.p2350RowGenerationReused===true,'P23.50 frozen row generation must be reused');
require(x?.methodology?.p2350TrainingUniversePredeclared30===true,'P23.50 training universe must remain predeclared');
require(x?.methodology?.p23RiskPriorSessionsOnly===true,'P23.50 risk must remain prior-session-only');
require(x?.methodology?.parameterSweep===false,'same-OOS parameter sweep forbidden');
require(x?.methodology?.postHocSymbolFiltering===false,'post-hoc symbol filtering forbidden');
require(x?.methodology?.entryRetuning===false,'Entry retuning forbidden');
require(x?.methodology?.freshHoldoutConsumed===false,'fresh holdout must remain untouched');
for(const k of safetyKeys) require(x?.safety?.[k]===false,`${k} must remain false`);

const base=x?.fixedHorizonBaseline??{},integrated=x?.riskConditioned??{},exits=x?.exitCounts??{};
require(finite(base.n)&&Number(base.n)>=200,'fixed baseline needs >=200 trades');
require(finite(integrated.n)&&Number(integrated.n)===Number(base.n),'integrated trade count must match fixed baseline');
require(finite(integrated.netReturnPct)&&Number(integrated.netReturnPct)>0,'integrated historical OOS Net must be positive');
require(finite(integrated.profitFactor)&&Number(integrated.profitFactor)>1,'integrated historical OOS PF must exceed 1');
require(finite(integrated.maxDrawdownPct)&&finite(base.maxDrawdownPct)&&Number(integrated.maxDrawdownPct)<=Number(base.maxDrawdownPct)+5,'integrated MaxDD deterioration exceeds guardrail');
require(Number(exits.riskReadyObservations)>0&&Number(exits.riskReadyTrades)>0,'Dynamic Risk must actually be ready');
require(Number(exits.riskTriggeredTrades)>0,'Dynamic Risk must actually trigger at least one exit');

function partitionAudit(groups={}){
  const eligible=Object.entries(groups).filter(([,v])=>Number(v?.n)>=30&&finite(v?.profitFactor));
  const profitable=eligible.filter(([,v])=>Number(v.profitFactor)>1&&Number(v.netReturnPct)>0);
  const losing=eligible.filter(([,v])=>Number(v.profitFactor)<=1||Number(v.netReturnPct)<=0);
  return {eligiblePartitions:eligible.length,profitablePartitions:profitable.length,losingPartitions:losing.length,losingKeys:losing.map(([k])=>k)};
}
const stability={
  direction:partitionAudit(x?.stability?.byDirection),
  symbol:partitionAudit(x?.stability?.bySymbol),
  time:partitionAudit(x?.stability?.byTimeBucket),
};
const stableAcrossEligiblePartitions=[stability.direction,stability.symbol,stability.time].every(a=>a.eligiblePartitions===0||a.losingPartitions===0);
const integratedDominates=Number(integrated.netReturnPct)>=Number(base.netReturnPct)&&Number(integrated.profitFactor)>=Number(base.profitFactor)&&Number(integrated.maxDrawdownPct)<=Number(base.maxDrawdownPct);

// P24.8 is a decision/freeze gate, not another tuning pass. If the integrated
// overlay does not dominate and remain stable, the already-frozen fixed-horizon
// policy remains the Phase57 benchmark/default for the next validation stage.
const decision=integratedDominates&&stableAcrossEligiblePartitions
  ?'PROMOTE_INTEGRATED_ONLY_TO_FRESH_VALIDATION'
  :'DEFER_TO_FIXED_HORIZON_BASELINE';

const out={
  phase:'57.p24.8',
  status:fail.length?'BLOCKED':'PHASE57_DEVELOPMENT_COMPLETE',
  phase57DevelopmentComplete:fail.length===0,
  productionReady:false,
  liveTradingAllowed:false,
  decision,
  frozenDefault:decision==='DEFER_TO_FIXED_HORIZON_BASELINE'?'FIXED_HORIZON_BASELINE':'P24_7_INTEGRATED_CANDIDATE',
  comparison:{
    trades:Number(base.n),
    fixedHorizon:{netReturnPct:base.netReturnPct,profitFactor:base.profitFactor,winRate:base.winRate,maxDrawdownPct:base.maxDrawdownPct,finalEquity:base.finalEquity},
    integrated:{netReturnPct:integrated.netReturnPct,profitFactor:integrated.profitFactor,winRate:integrated.winRate,maxDrawdownPct:integrated.maxDrawdownPct,finalEquity:integrated.finalEquity},
    dynamicRisk:{riskReadyObservations:exits.riskReadyObservations,riskReadyTrades:exits.riskReadyTrades,riskTriggeredTrades:exits.riskTriggeredTrades,directionAlignedTrades:exits.directionAlignedTrades},
  },
  stability:{...stability,stableAcrossEligiblePartitions},
  methodology:{
    noNewTuning:true,
    sameOosThresholdSweep:false,
    postHocSymbolFiltering:false,
    entryRetuning:false,
    p2350PriorOnly:true,
    freshHoldoutConsumed:false,
    fixedBaselineMayBeDefaultWithoutClaimingDynamicRiskCausality:true,
  },
  completionRationale:decision==='DEFER_TO_FIXED_HORIZON_BASELINE'
    ?'P24.7 proves a genuinely active, profitable integrated Dynamic-Risk path, but it does not beat the identical frozen fixed-horizon baseline and has losing eligible partitions. Phase57 development therefore freezes the fixed-horizon policy as the benchmark/default and keeps Dynamic Risk as a research/conditional overlay for fresh validation.'
    :'The integrated policy beats the identical frozen baseline on Net/PF/MaxDD and has no losing eligible partitions; it is promoted only to fresh validation, never to production.',
  nextValidationStage:'ONE_SHOT_FRESH_HOLDOUT_AFTER_PRECOMMITTED_READINESS; THEN PHASE58 ONLY AFTER VALIDATION DECISION',
  unresolvedBlockers:fail,
  safety:Object.fromEntries(safetyKeys.map(k=>[k,false])),
};

fs.mkdirSync(new URL('../../artifacts/',import.meta.url),{recursive:true});
fs.writeFileSync(outputPath,JSON.stringify(out,null,2));
console.log(JSON.stringify(out,null,2));
if(fail.length) process.exitCode=1;
