import {createHash} from 'node:crypto';
import {PHASE57_LONG_ONLY_SAFETY} from './phase57-long-only-research-contract.js';

export const COMPARISON_STAGES=Object.freeze(['SELECTOR_ONLY','SELECTOR_ENTRY','SELECTOR_ENTRY_EXIT','FULL_INTEGRATED_PORTFOLIO']);
const round=x=>Number.isFinite(x)?Number(x.toFixed(8)):x;
const hhi=(items,key)=>{const totals=new Map(),sum=items.reduce((a,x)=>a+Math.abs(Number(x.netPnlJpy)||0),0);if(!sum)return 0;for(const item of items)totals.set(item[key]??'UNKNOWN',(totals.get(item[key]??'UNKNOWN')??0)+Math.abs(Number(item.netPnlJpy)||0));return [...totals.values()].reduce((a,x)=>a+(x/sum)**2,0);};
const maxDrawdown=curve=>{let peak=-Infinity,max=0;for(const point of curve){const v=Number(point.equityJpy);if(!Number.isFinite(v))throw new Error('equity curve contains a non-finite value');peak=Math.max(peak,v);if(peak>0)max=Math.max(max,(peak-v)/peak);}return 100*max;};

export function computeIntegratedMetrics({trades=[],equityCurve=[],opportunityCount=0,missedOpportunityCount=0}={}){
  const gains=trades.filter(x=>Number(x.netPnlJpy)>0).reduce((a,x)=>a+Number(x.netPnlJpy),0),losses=Math.abs(trades.filter(x=>Number(x.netPnlJpy)<0).reduce((a,x)=>a+Number(x.netPnlJpy),0));
  const afterCostNet=trades.reduce((a,x)=>a+(Number(x.netPnlJpy)||0),0),start=Number(equityCurve[0]?.equityJpy),end=Number(equityCurve.at(-1)?.equityJpy);
  const dd=maxDrawdown(equityCurve),portfolioReturnPct=Number.isFinite(start)&&start>0&&Number.isFinite(end)?100*(end/start-1):null;
  const utilization=equityCurve.length?equityCurve.reduce((a,x)=>a+(Number(x.investedJpy)||0)/(Number(x.equityJpy)||1),0)/equityCurve.length:null;
  return Object.freeze({afterCostNetJpy:round(afterCostNet),profitFactor:losses?round(gains/losses):(gains>0?Infinity:null),maxDrawdownPct:round(dd),returnToDrawdown:dd&&portfolioReturnPct!==null?round(portfolioReturnPct/dd):null,portfolioReturnPct:round(portfolioReturnPct),winRatePct:trades.length?round(100*trades.filter(x=>Number(x.netPnlJpy)>0).length/trades.length):null,tradeCount:trades.length,cashUtilizationPct:utilization===null?null:round(100*utilization),missedOpportunityCount,opportunityCoveragePct:opportunityCount?round(100*(opportunityCount-missedOpportunityCount)/opportunityCount):null,symbolConcentrationHhi:round(hhi(trades,'symbol')),sectorConcentrationHhi:round(hhi(trades,'sector'))});
}

const validateCandidateTrades=trades=>{
  for(const trade of trades){
    if(String(trade.side).toUpperCase()!=='LONG')throw new Error('candidate SHORT contribution must be zero');
    if(trade.accountType!=='CASH_EQUITY'||trade.margin===true||Number(trade.leverage??1)!==1)throw new Error('candidate margin or leverage is prohibited');
    if(!Number.isInteger(Number(trade.quantity))||Number(trade.quantity)<=0||Number(trade.quantity)%100!==0)throw new Error('candidate quantity must use 100-share cash-equity lots');
  }
};

export function auditCashEquityLedger(trades,{initialCashJpy}={}){
  validateCandidateTrades(trades);
  const initial=Number(initialCashJpy);if(!Number.isFinite(initial)||initial<=0)throw new Error('positive initial cash is required');
  const events=[];
  for(const [index,trade] of trades.entries()){
    const quantity=Number(trade.quantity),entryPrice=Number(trade.entryPrice),exitPrice=Number(trade.exitPrice),entryCost=Number(trade.entryCostJpy??0),exitCost=Number(trade.exitCostJpy??0);
    if(!trade.entryAt||!trade.exitAt||String(trade.exitAt)<String(trade.entryAt))throw new Error('ordered entryAt and exitAt are required');
    if(![entryPrice,exitPrice,entryCost,exitCost].every(Number.isFinite)||entryPrice<=0||exitPrice<=0||entryCost<0||exitCost<0)throw new Error('valid execution prices and costs are required');
    events.push({at:String(trade.entryAt),kind:'ENTRY',index,amount:quantity*entryPrice+entryCost});
    events.push({at:String(trade.exitAt),kind:'EXIT',index,amount:quantity*exitPrice-exitCost});
  }
  events.sort((a,b)=>a.at.localeCompare(b.at)||(a.kind==='EXIT'?-1:1)||a.index-b.index);
  let cash=initial,minCash=initial;const locks=[];
  for(const event of events){
    if(event.kind==='ENTRY'){
      if(event.amount>cash+1e-9)throw new Error(`cash-equity entry exceeds available cash at ${event.at}`);
      cash-=event.amount;locks.push(Object.freeze({...event,cashAfterJpy:round(cash)}));
    }else{cash+=event.amount;locks.push(Object.freeze({...event,cashAfterJpy:round(cash)}));}
    minCash=Math.min(minCash,cash);
  }
  return Object.freeze({initialCashJpy:round(initial),endingCashJpy:round(cash),minimumCashJpy:round(minCash),cashNeverNegative:minCash>=-1e-9,exitCashReleaseAndReuseApplied:true,events:Object.freeze(locks)});
}

export function compareLongOnlyIntegratedSystems({evaluationSessions,costModelSha256,baseline,candidate,frozenGoNoGoRule={netDeltaMustBePositive:true,maxDrawdownMayNotIncrease:true}}={}){
  const sessions=[...new Set((evaluationSessions??[]).map(String))].sort();
  if(!sessions.length)throw new Error('same non-empty evaluation window is required');
  if(!/^[a-f0-9]{64}$/.test(costModelSha256??''))throw new Error('frozen cost model SHA-256 is required');
  for(const system of [baseline,candidate]){
    if(system?.costModelSha256!==costModelSha256)throw new Error('same cost model is required');
    if(JSON.stringify([...new Set(system.evaluationSessions??[])].sort())!==JSON.stringify(sessions))throw new Error('same evaluation window is required');
    if(!COMPARISON_STAGES.every(stage=>system.stages?.[stage]))throw new Error('all four integration stages are required');
  }
  validateCandidateTrades(candidate.stages.FULL_INTEGRATED_PORTFOLIO.trades??[]);
  const cashLedgerAudit=auditCashEquityLedger(candidate.stages.FULL_INTEGRATED_PORTFOLIO.trades??[],{initialCashJpy:candidate.initialCashJpy});
  const stages={};
  for(const stage of COMPARISON_STAGES){
    const baselineMetrics=computeIntegratedMetrics(baseline.stages[stage]),candidateMetrics=computeIntegratedMetrics(candidate.stages[stage]);
    stages[stage]=Object.freeze({baseline:baselineMetrics,candidate:candidateMetrics,delta:Object.freeze({afterCostNetJpy:round(candidateMetrics.afterCostNetJpy-baselineMetrics.afterCostNetJpy),maxDrawdownPct:round(candidateMetrics.maxDrawdownPct-baselineMetrics.maxDrawdownPct),portfolioReturnPct:round(candidateMetrics.portfolioReturnPct-baselineMetrics.portfolioReturnPct),tradeCount:candidateMetrics.tradeCount-baselineMetrics.tradeCount,opportunityCoveragePct:round((candidateMetrics.opportunityCoveragePct??0)-(baselineMetrics.opportunityCoveragePct??0))})});
  }
  const full=stages.FULL_INTEGRATED_PORTFOLIO;
  const pass=(!frozenGoNoGoRule.netDeltaMustBePositive||full.delta.afterCostNetJpy>0)&&(!frozenGoNoGoRule.maxDrawdownMayNotIncrease||full.delta.maxDrawdownPct<=0);
  const contract={evaluationSessions:sessions,costModelSha256,frozenGoNoGoRule};
  return Object.freeze({schemaVersion:1,status:pass?'CANDIDATE_BEATS_BASELINE_UNDER_FROZEN_RULE':'CANDIDATE_DOES_NOT_BEAT_BASELINE_UNDER_FROZEN_RULE',pass,comparisonContractSha256:createHash('sha256').update(JSON.stringify(contract)).digest('hex'),stages:Object.freeze(stages),proof:Object.freeze({candidateShortTrades:0,candidateMarginTrades:0,sameEvaluationWindow:true,sameCostModel:true,cashLedgerAudit}),safety:PHASE57_LONG_ONLY_SAFETY});
}

export default {computeIntegratedMetrics,auditCashEquityLedger,compareLongOnlyIntegratedSystems};
