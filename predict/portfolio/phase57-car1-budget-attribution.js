import {
  PHASE57_P25_LANE_C_ALLOCATION_PROFILES,
  PHASE57_P25_LANE_C_POLICY,
  PHASE57_P25_LANE_C_SAFETY,
  simulateLaneCPortfolio,
} from './phase57-p25-lane-c-portfolio-simulator.js';
import {
  PHASE57_CAR1_PROFILES,
  PHASE57_CAR1_SAFETY,
} from './phase57-car1-sizing-research.js';
import {buildCausalSizingGroup} from './phase57-car1-sizing-adapter.js';

const FALSE_KEYS=Object.freeze([
  'executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed',
  'liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted',
]);

const round=(value,digits=6)=>Number.isFinite(value)?Number(value.toFixed(digits)):value;
const finite=value=>value!==null&&value!==undefined&&value!==''&&Number.isFinite(Number(value));

function assertSafety(){
  for(const key of FALSE_KEYS){
    if(PHASE57_CAR1_SAFETY[key]!==false)throw new Error(`CAR-1 safety ${key} must remain false`);
    if(PHASE57_P25_LANE_C_SAFETY[key]!==false)throw new Error(`Lane C safety ${key} must remain false`);
  }
  if(PHASE57_CAR1_SAFETY.winnerSelectionAllowed!==false)throw new Error('CAR-1 winner selection must remain disabled');
}

function sessionMap(sessions){
  const map=new Map();
  for(const session of Array.isArray(sessions)?sessions:[]){
    const sessionDate=String(session?.sessionDate??'').trim();
    if(!sessionDate)throw new Error('CAR-1 sessionDate required');
    if(map.has(sessionDate))throw new Error(`duplicate CAR-1 session: ${sessionDate}`);
    map.set(sessionDate,session);
  }
  return map;
}

function decisionGroups(decisions){
  const groups=new Map();
  for(const decision of Array.isArray(decisions)?decisions:[]){
    const entry=decision?.candidateSnapshot;
    const sessionDate=String(entry?.sessionDate??'').trim();
    const timestamp=String(decision?.timestamp??entry?.entryTimestamp??'').trim();
    const key=String(entry?.key??'').trim();
    const legacyTargetBudgetJpy=Number(decision?.stateSnapshot?.targetSlotBudgetJpy);
    if(!sessionDate||!timestamp||!key||!finite(legacyTargetBudgetJpy)||legacyTargetBudgetJpy<=0){
      throw new Error('CAR-1 requires complete causal Lane C allocation decisions');
    }
    const groupKey=`${sessionDate}|${timestamp}`;
    if(!groups.has(groupKey))groups.set(groupKey,{sessionDate,timestamp,decisions:[]});
    groups.get(groupKey).decisions.push(decision);
  }
  return [...groups.values()].sort((a,b)=>a.timestamp.localeCompare(b.timestamp));
}

function barsForSession(session){
  const source=session?.sessionBarsBySymbol;
  if(source instanceof Map)return source;
  if(source&&typeof source==='object')return source;
  throw new Error(`CAR-1 session bars missing for ${session?.sessionDate??'UNKNOWN'}`);
}

function summarizeProfile(profileId,rows){
  const totalTargetBudgetJpy=rows.reduce((sum,row)=>sum+row.targetBudgetJpy,0);
  const totalLegacyTargetBudgetJpy=rows.reduce((sum,row)=>sum+row.legacyTargetBudgetJpy,0);
  const absoluteShift=rows.reduce((sum,row)=>sum+Math.abs(row.targetBudgetJpy-row.legacyTargetBudgetJpy),0);
  return Object.freeze({
    profileId,
    candidateCount:rows.length,
    totalTargetBudgetJpy:round(totalTargetBudgetJpy),
    totalLegacyTargetBudgetJpy:round(totalLegacyTargetBudgetJpy),
    l1BudgetShiftPctOfLegacy:totalLegacyTargetBudgetJpy>0?round(absoluteShift/totalLegacyTargetBudgetJpy*100):null,
    maximumWithinGroupWeight:rows.length?round(Math.max(...rows.map(row=>row.weight))):null,
    rows:Object.freeze(rows),
  });
}

export function buildCar1PairedBudgetAttribution({
  sessions=[],
  baselineProfile=PHASE57_P25_LANE_C_ALLOCATION_PROFILES[0],
  profileIds=PHASE57_CAR1_PROFILES.map(row=>row.id),
  initialEquity=PHASE57_P25_LANE_C_POLICY.initialEquityJpy,
  managementMode='FIXED_HORIZON',
  universeVariant='DYNAMIC_50',
  roundTripCostPct=PHASE57_P25_LANE_C_POLICY.fixedRoundTripCostPct,
  slippageBps=PHASE57_P25_LANE_C_POLICY.baselineSlippageBps,
}={}){
  assertSafety();
  const selectedProfileIds=[...(Array.isArray(profileIds)?profileIds:[])];
  if(!selectedProfileIds.length)throw new Error('CAR-1 requires at least one sizing profile');
  if(new Set(selectedProfileIds).size!==selectedProfileIds.length)throw new Error('duplicate CAR-1 sizing profile');
  const known=new Set(PHASE57_CAR1_PROFILES.map(row=>row.id));
  for(const profileId of selectedProfileIds)if(!known.has(profileId))throw new Error(`unknown CAR-1 sizing profile: ${profileId}`);

  const baseline=simulateLaneCPortfolio({
    sessions,profile:baselineProfile,initialEquity,managementMode,universeVariant,roundTripCostPct,slippageBps,
  });
  const sessionsByDate=sessionMap(sessions);
  const groups=decisionGroups(baseline.allocationDecisions);
  const rowsByProfile=new Map(selectedProfileIds.map(profileId=>[profileId,[]]));
  const groupAudits=[];

  for(const group of groups){
    const session=sessionsByDate.get(group.sessionDate);
    if(!session)throw new Error(`CAR-1 source session missing for ${group.sessionDate}`);
    const entries=group.decisions.map(row=>row.candidateSnapshot);
    const envelopeJpy=group.decisions.reduce((sum,row)=>sum+Number(row.stateSnapshot.targetSlotBudgetJpy),0);
    if(!Number.isFinite(envelopeJpy)||envelopeJpy<=0)throw new Error(`invalid CAR-1 legacy budget envelope at ${group.timestamp}`);
    const legacyByKey=new Map(group.decisions.map(row=>[row.candidateSnapshot.key,Number(row.stateSnapshot.targetSlotBudgetJpy)]));

    for(const profileId of selectedProfileIds){
      const sizingGroup=buildCausalSizingGroup({profileId,entries,barsBySymbol:barsForSession(session)});
      if(sizingGroup.weights.length!==entries.length)throw new Error(`CAR-1 candidate count changed for ${profileId}`);
      const candidateByKey=new Map(sizingGroup.candidates.map(row=>[row.key,row]));
      const weightTotal=sizingGroup.weights.reduce((sum,row)=>sum+row.weight,0);
      if(Math.abs(weightTotal-1)>1e-10)throw new Error(`CAR-1 weights do not sum to one for ${profileId}`);
      for(const weightRow of sizingGroup.weights){
        const candidate=candidateByKey.get(weightRow.key);
        const legacyTargetBudgetJpy=legacyByKey.get(weightRow.key);
        if(!candidate||!Number.isFinite(legacyTargetBudgetJpy))throw new Error(`CAR-1 paired candidate missing: ${weightRow.key}`);
        const targetBudgetJpy=envelopeJpy*weightRow.weight;
        rowsByProfile.get(profileId).push(Object.freeze({
          sessionDate:group.sessionDate,
          entryTimestamp:group.timestamp,
          key:weightRow.key,
          symbol:candidate.symbol,
          weight:round(weightRow.weight,12),
          targetBudgetJpy:round(targetBudgetJpy),
          legacyTargetBudgetJpy:round(legacyTargetBudgetJpy),
          budgetDeltaJpy:round(targetBudgetJpy-legacyTargetBudgetJpy),
          riskSnapshot:candidate.riskSnapshot,
        }));
      }
    }

    groupAudits.push(Object.freeze({
      sessionDate:group.sessionDate,
      entryTimestamp:group.timestamp,
      candidateCount:entries.length,
      legacyTargetBudgetEnvelopeJpy:round(envelopeJpy),
      candidateKeys:Object.freeze(entries.map(row=>row.key)),
    }));
  }

  const profileResults={};
  for(const profileId of selectedProfileIds){
    const rows=rowsByProfile.get(profileId);
    if(rows.length!==baseline.input.candidateEntryCount)throw new Error(`CAR-1 paired candidate cardinality changed for ${profileId}`);
    profileResults[profileId]=summarizeProfile(profileId,rows);
  }

  return Object.freeze({
    phase:'57.car1.capital-allocation-sizing',
    status:'CAR1_PAIRED_TARGET_BUDGET_ATTRIBUTION',
    baselineProfile:Object.freeze({...baseline.profile}),
    baselineInput:baseline.input,
    baselinePortfolioMetrics:Object.freeze({
      totalReturnPct:baseline.return.totalReturnPct,
      profitFactor:baseline.trade.profitFactor,
      maxDrawdownPct:baseline.risk.maxDrawdownPct,
      averageCapitalUtilization:baseline.capitalEfficiency.averageCapitalUtilization,
      observedMaximumConcurrentPositions:baseline.concentration.observedMaximumConcurrentPositions,
    }),
    profileOrder:Object.freeze(selectedProfileIds),
    profiles:Object.freeze(profileResults),
    groups:Object.freeze(groupAudits),
    pairedAudit:Object.freeze({
      sameFrozenEntryCandidates:true,
      candidateEntryCount:baseline.input.candidateEntryCount,
      candidateKeySha256:baseline.input.candidateKeySha256,
      sameEntryPrice:true,
      sameDirection:true,
      sameFrozenExit:true,
      sameCostAssumption:true,
      sameCandidatePriority:true,
      legacyBudgetEnvelopePreserved:true,
      futureOutcomeUsed:false,
      portfolioOutcomeSimulatedForChallengers:false,
    }),
    methodology:Object.freeze({
      laneCBaselineSimulatorUsed:true,
      legacyBudgetEnvelopeSource:'LANE_C_ALLOCATION_DECISION_TARGET_SLOT_BUDGET',
      challengerExecutionApplied:false,
      purpose:'PRE_EXECUTION_SIZING_ATTRIBUTION_BEFORE_PORTFOLIO_HOOK',
      winnerSelectionAllowed:false,
      parameterSearchAllowed:false,
      automaticPromotionAllowed:false,
    }),
    safety:Object.freeze({car1:PHASE57_CAR1_SAFETY,laneC:PHASE57_P25_LANE_C_SAFETY}),
  });
}

export default {buildCar1PairedBudgetAttribution};
