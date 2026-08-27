import fs from 'node:fs';
import path from 'node:path';

const arg=(name,fallback=null)=>{const i=process.argv.indexOf(name);return i>=0&&i+1<process.argv.length?process.argv[i+1]:fallback;};
const read=file=>JSON.parse(fs.readFileSync(file,'utf8'));
const write=(file,value)=>{fs.mkdirSync(path.dirname(file),{recursive:true});fs.writeFileSync(file,JSON.stringify(value,null,2)+'\n','utf8');};
const mean=xs=>xs.length?xs.reduce((s,x)=>s+x,0)/xs.length:null;
const round=(x,d=6)=>Number.isFinite(x)?Number(x.toFixed(d)):x;
const maxPositionsOf=profileId=>{const m=/^MAX_(\d+)$/.exec(String(profileId));return m?Number(m[1]):null;};

function profileDiagnostic(profileId,result){
  const decisions=Array.isArray(result?.allocationDecisions)?result.allocationDecisions:[];
  const curve=Array.isArray(result?.equityCurve)?result.equityCurve:[];
  const accepted=decisions.filter(x=>x.status==='ACCEPTED');
  const rejected=decisions.filter(x=>x.status==='REJECTED');
  const reasonCounts={};
  for(const row of rejected)reasonCounts[row.reason]=(reasonCounts[row.reason]??0)+1;
  const slotFill=accepted.map(x=>{
    const actual=Number(x?.stateSnapshot?.actualPurchaseAmountJpy);
    const target=Number(x?.stateSnapshot?.targetSlotBudgetJpy);
    return Number.isFinite(actual)&&Number.isFinite(target)&&target>0?actual/target:null;
  }).filter(Number.isFinite);
  const averageOpenPositionCount=mean(curve.map(x=>Number(x.openPositionCount)).filter(Number.isFinite));
  const maxPositions=maxPositionsOf(profileId);
  const occupancyRatio=Number.isFinite(averageOpenPositionCount)&&Number.isFinite(maxPositions)&&maxPositions>0?averageOpenPositionCount/maxPositions:null;
  const zeroExposurePoints=curve.filter(x=>Number(x.grossExposureJpy)===0).length;
  const cashHeavyPoints=curve.filter(x=>Number(x.cashRatio)>=0.8).length;
  const avgAcceptedNotional=mean(accepted.map(x=>Number(x?.stateSnapshot?.entryNotionalJpy)).filter(Number.isFinite));
  const avgTargetBudget=mean(accepted.map(x=>Number(x?.stateSnapshot?.targetSlotBudgetJpy)).filter(Number.isFinite));
  const avgAvailableCashBefore=mean(accepted.map(x=>Number(x?.stateSnapshot?.availableCashBeforeJpy)).filter(Number.isFinite));
  return {
    profileId,
    candidateEntries:Number(result?.trade?.candidates??0),
    acceptedEntries:Number(result?.trade?.accepted??accepted.length),
    rejectedEntries:Number(result?.trade?.rejected??rejected.length),
    acceptanceRate:decisions.length?round(accepted.length/decisions.length):null,
    rejectionReasons:reasonCounts,
    finalEquityJpy:Number(result?.return?.finalEquityJpy),
    totalReturnPct:Number(result?.return?.totalReturnPct),
    maxDrawdownPct:Number(result?.risk?.maxDrawdownPct),
    profitFactor:Number(result?.trade?.profitFactor),
    averageCapitalUtilization:Number(result?.capitalEfficiency?.averageCapitalUtilization),
    averageCashRatio:Number(result?.capitalEfficiency?.averageCashRatio),
    capitalRecyclingCount:Number(result?.capitalEfficiency?.capitalRecyclingCount),
    turnover:Number(result?.capitalEfficiency?.turnover),
    averageOpenPositionCount:round(averageOpenPositionCount),
    maxPositions,
    averageSlotOccupancyRatio:round(occupancyRatio),
    zeroExposurePointRatio:curve.length?round(zeroExposurePoints/curve.length):null,
    cashAtLeast80PctPointRatio:curve.length?round(cashHeavyPoints/curve.length):null,
    averageAcceptedEntryNotionalJpy:round(avgAcceptedNotional,2),
    averageTargetSlotBudgetJpy:round(avgTargetBudget,2),
    averageAvailableCashBeforeEntryJpy:round(avgAvailableCashBefore,2),
    averageSlotBudgetFillRatio:round(mean(slotFill)),
  };
}

export function buildCapitalEfficiencyDiagnostic(source){
  if(source?.evidenceClass!=='LEGACY27_DIAGNOSTIC_ONLY')throw new Error('capital efficiency diagnostic requires legacy27 diagnostic source');
  if(source?.interpretation?.winnerSelectionAllowed!==false||source?.interpretation?.formalOos!==false||source?.interpretation?.promotionEligible!==false)throw new Error('source classification guard violation');
  const comparison=source?.full?.comparison;
  if(!comparison?.results)throw new Error('missing Lane C comparison results');
  const ids=['MAX_10','MAX_4','MAX_3','MAX_2'];
  const profiles=ids.map(id=>profileDiagnostic(id,comparison.results[id]));
  return {
    schemaVersion:1,
    phase:'57.p25.lane-c.capital-efficiency-diagnostic',
    status:'LANE_C_CAPITAL_EFFICIENCY_DIAGNOSTIC_READY',
    evidenceClass:'LEGACY27_DIAGNOSTIC_ONLY',
    purpose:'Explain why trade-level EXIT v3 edge converts weakly into portfolio return; do not tune or select an allocation winner from legacy27.',
    profiles,
    interpretation:{
      winnerSelectionAllowed:false,
      formalOos:false,
      promotionEligible:false,
      resultBasedRetuning:false,
      freshHoldoutConsumed:false,
      rankingRuleTuningAllowed:false,
      allocationRuleTuningAllowed:false,
    },
    safety:source.safety,
  };
}

const input=arg('--input');
const output=arg('--output','tmp/p25-lane-c-capital-efficiency.json');
if(input){
  const result=buildCapitalEfficiencyDiagnostic(read(input));
  write(output,result);
  console.log(JSON.stringify(result,null,2));
}
