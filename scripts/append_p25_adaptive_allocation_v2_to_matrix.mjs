import fs from 'node:fs';
import path from 'node:path';
import {simulateP25AdaptiveAllocationV2,PHASE57_P25_ADAPTIVE_ALLOCATION_V2_POLICY,PHASE57_P25_ADAPTIVE_ALLOCATION_V2_SAFETY} from '../predict/portfolio/phase57-p25-adaptive-allocation-v2.js';

const arg=(n,f=null)=>{const i=process.argv.indexOf(n);return i>=0&&i+1<process.argv.length?process.argv[i+1]:f;};
const matrixPath=arg('--matrix'),bundlePath=arg('--bundle'),output=arg('--output',matrixPath);
if(!matrixPath||!bundlePath)throw new Error('usage: --matrix <json> --bundle <json> [--output <json>]');
const matrix=JSON.parse(fs.readFileSync(matrixPath,'utf8')),bundle=JSON.parse(fs.readFileSync(bundlePath,'utf8'));
if(matrix.status!=='P25_DYNAMIC5M_CHALLENGER_MATRIX_EVALUATED'||matrix.sessionDate!==bundle.sessionDate)throw new Error('adaptive allocation matrix/bundle contract mismatch');
if(bundle.barsReady!==true||bundle.completeFiveMinuteCoverage!==true||bundle.hasDynamic5mV2EveryPoint!==true)throw new Error('adaptive allocation v2 requires complete causal v1/v2 bundle');
const sessionDate=String(matrix.sessionDate),sessionBarsBySymbol=bundle.sessionBarsBySymbol??{};
const cells={};
for(const id of ['V1_V3','V1_V4','V2_V3','V2_V4']){
  const cell=matrix.matrix?.[id];if(!cell||!Array.isArray(cell.pairs))throw new Error(`adaptive allocation missing matrix cell ${id}`);
  const trades=cell.pairs.map(p=>({
    entryAccepted:true,frozenBeforeOutcome:true,currentOutcomeUsed:false,symbol:p.symbol,sector:p.entry?.sector,
    signalDirection:Number(p.entry?.signalDirection),sessionDate,entryTimestamp:p.entry?.entryTimestamp,entryPrice:Number(p.entry?.entryPrice),
    exitTimestamp:p.outcome?.exitTimestamp,exitPrice:Number(p.outcome?.exitPrice),exitReason:p.outcome?.exitReason,
    confidence:p.entry?.confidence,probability:p.entry?.probability,selectionOpportunityScore:p.entry?.selectionOpportunityScore,selectionV2Score:p.entry?.selectionV2Score,
  }));
  const profiles={};for(const profile of PHASE57_P25_ADAPTIVE_ALLOCATION_V2_POLICY.allocationProfiles)profiles[profile.id]=simulateP25AdaptiveAllocationV2({sessions:[{sessionDate,sessionBarsBySymbol,trades}],profile});
  cells[id]={...cell,adaptiveAllocationV2:{candidateId:PHASE57_P25_ADAPTIVE_ALLOCATION_V2_POLICY.candidateId,firstFreshEligibleDate:PHASE57_P25_ADAPTIVE_ALLOCATION_V2_POLICY.firstFreshEligibleDate,profileWinnerSelected:false,profiles}};
}
const payload={...matrix,schemaVersion:2,matrix:cells,adaptiveAllocationV2:{status:'P25_ADAPTIVE_ALLOCATION_V2_ATTACHED',firstFreshEligibleDate:PHASE57_P25_ADAPTIVE_ALLOCATION_V2_POLICY.firstFreshEligibleDate,developmentEvidence:{august31Role:'FAILURE_ANALYSIS_ONLY',august31UsedForThresholdSearch:false,august31UsedForRankSearch:false,august31EligibleForPerformanceClaim:false},profileWinnerSelected:false,policy:PHASE57_P25_ADAPTIVE_ALLOCATION_V2_POLICY,safety:PHASE57_P25_ADAPTIVE_ALLOCATION_V2_SAFETY},methodology:{...matrix.methodology,adaptiveAllocationV2Parallel:true,adaptiveAllocationV2WinnerSelection:false,oneCandidateMayEnter:true,dynamicReserve:true,opportunityRanksFrozenBeforeFresh:true}};
for(const k of ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted','freshHoldoutConsumed'])if(payload.adaptiveAllocationV2.safety?.[k]!==false)throw new Error(`unsafe adaptive v2 ${k}`);
fs.mkdirSync(path.dirname(output),{recursive:true});fs.writeFileSync(output,JSON.stringify(payload,null,2)+'\n');
console.log(JSON.stringify({status:payload.adaptiveAllocationV2.status,sessionDate,cells:Object.fromEntries(Object.entries(cells).map(([id,c])=>[id,Object.fromEntries(Object.entries(c.adaptiveAllocationV2.profiles).map(([p,x])=>[p,{returnPct:x.return.totalReturnPct,maxDDPct:x.risk.maxDrawdownPct,avgUtil:x.capitalEfficiency.averageCapitalUtilization,peakUtil:x.capitalEfficiency.peakCapitalUtilization,missedHighQuality:x.capitalEfficiency.missedHighQualityCandidates}]))]))},null,2));
