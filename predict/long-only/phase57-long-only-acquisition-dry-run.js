import crypto from 'node:crypto';
import {evaluateLongOnlyAcquisitionGate} from './phase57-long-only-acquisition-gate.js';

const PARTITIONS=Object.freeze({
  DEVELOPMENT_A:25,
  DEVELOPMENT_B:15,
  DEVELOPMENT_C:20,
  DEVELOPMENT_D:20,
  VALIDATION:30,
  VALIDATION_REPLICATION:20,
  PRIMARY_OOS:30,
  CONTINGENCY_OOS:30,
  RESERVE:15,
});

const stable=value=>{
  if(Array.isArray(value))return value.map(stable);
  if(value&&typeof value==='object')return Object.fromEntries(Object.keys(value).sort().map(k=>[k,stable(value[k])]));
  return value;
};

export function buildLongOnlyAcquisitionDryRun(plan,{includeMinute=false,minuteSessions=0}={}){
  if(!plan||typeof plan!=='object')throw new TypeError('data plan is required');
  const gate=evaluateLongOnlyAcquisitionGate(plan);
  const totalHistorical=Object.values(PARTITIONS).reduce((a,b)=>a+b,0);
  if(totalHistorical!==plan.datasetSplit?.totalCleanHistoricalSessions)throw new Error('partition accounting mismatch');
  if(includeMinute&&(!Number.isInteger(minuteSessions)||minuteSessions<1))throw new Error('minuteSessions must be a positive integer when includeMinute=true');
  if(includeMinute&&minuteSessions>plan.datasetSplit.development.totalSessions)throw new Error('minute acquisition may not exceed released Development planning envelope');

  const warmupDailyRequests=Number(plan.l0Contract?.causalWarmup?.dailyRequests??0);
  if(warmupDailyRequests!==1||plan.l0Contract?.causalWarmup?.evaluationPartition!==false)throw new Error('one non-evaluation L0 causal warmup Daily request is required');
  const dailyRequests=totalHistorical+warmupDailyRequests;
  const masterRequests=totalHistorical;
  const priorRate=plan.dataBudget?.development80IntradayUpperPlan;
  const minutePages=includeMinute
    ? Math.ceil((priorRate.estimatedMinutePagesFromPrior90SessionRate/priorRate.sessions)*minuteSessions)
    : 0;

  const output={
    mode:'DRY_RUN_ZERO_NETWORK',
    acquisitionMayStart:false,
    gateStatus:gate.status,
    missingGates:[...gate.missing],
    historicalSessions:totalHistorical,
    causalWarmup:{sessionDate:plan.l0Contract.causalWarmup.sessionDate,evaluationPartition:false,dailyRequests:warmupDailyRequests},
    partitions:{...PARTITIONS},
    requests:{daily:dailyRequests,master:masterRequests,minutePages,total:dailyRequests+masterRequests+minutePages},
    minute:{requested:includeMinute,sessions:includeMinute?minuteSessions:0,policy:'PLANNING_ONLY_NO_PROVIDER_CALL'},
    selectorOnlyConsumptionProhibited:true,
    integratedReuse:['SELECTOR','ENTRY','EXIT','ALLOCATION','PORTFOLIO_REPLAY'],
    planSha256:gate.planSha256,
  };
  output.dryRunSha256=crypto.createHash('sha256').update(JSON.stringify(stable(output))).digest('hex');
  return Object.freeze(output);
}

export default {buildLongOnlyAcquisitionDryRun};
