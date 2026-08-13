import { simulateTradeManagementStateMachine } from './phase57-trade-management-state-machine.js';

export const P24_1_SAFETY = Object.freeze({
  phase:'57.p24.1', mode:'ENTRY_HOLD_PROTECT_EXIT_INTEGRATION_RESEARCH',
  executionAllowed:false, brokerWriteAllowed:false, excelOrderWriteAllowed:false,
  rssOrderFunctionAllowed:false, liveTradingAllowed:false, paperTradingAllowed:false,
  automaticPromotionAllowed:false, productionUpdateAllowed:false, transmitted:false,
  freshHoldoutConsumed:false,
});

const finite=x=>Number.isFinite(Number(x));
const mean=a=>a.length?a.reduce((s,x)=>s+x,0)/a.length:null;

function maxDrawdownPct(equity){let peak=equity[0]??1,max=0;for(const x of equity){peak=Math.max(peak,x);if(peak>0)max=Math.max(max,(peak-x)/peak*100);}return max;}
function profitFactor(xs){const gp=xs.filter(x=>x>0).reduce((s,x)=>s+x,0),gl=-xs.filter(x=>x<0).reduce((s,x)=>s+x,0);return gl>0?gp/gl:(gp>0?Infinity:null);}

export function evaluateIntegratedTradeResearch(rows=[],options={}){
  const accepted=(Array.isArray(rows)?rows:[]).filter(r=>r?.entryAccepted===true);
  const outcomes=[];
  for(const row of accepted){
    const out=simulateTradeManagementStateMachine(row,options.tradeManagement??{});
    if(!out)continue;
    outcomes.push(Object.freeze({
      symbol:row.symbol??null, setup:row.setup??null, entryBand:row.entryBand??null,
      entryTimestamp:row.entryTimestamp??row.futureBars?.[0]?.timestamp??null,
      direction:out.direction, exitTimestamp:out.outcomeAt, exitReason:out.exitReason,
      barsHeld:out.barsHeld, grossReturnPct:out.grossReturnPct, netReturnPct:out.netReturnPct,
      mfePct:out.mfePct, maePct:out.maePct, captureRatio:out.captureRatio,
      stateVisitCounts:out.stateVisitCounts,
    }));
  }
  const returns=outcomes.map(x=>Number(x.netReturnPct)).filter(Number.isFinite);
  const equity=[1];for(const r of returns)equity.push(equity.at(-1)*(1+r/100));
  const wins=returns.filter(x=>x>0).length;
  const summary=Object.freeze({
    n:returns.length, acceptedEntryCount:accepted.length, coverage:accepted.length?returns.length/accepted.length:0,
    netReturnPct:(equity.at(-1)-1)*100, meanNetReturnPct:mean(returns), medianNetReturnPct:returns.length?[...returns].sort((a,b)=>a-b)[Math.floor((returns.length-1)/2)]:null,
    winRate:returns.length?wins/returns.length:null, profitFactor:profitFactor(returns), maxDrawdownPct:maxDrawdownPct(equity),
    meanMfePct:mean(outcomes.map(x=>x.mfePct).filter(finite).map(Number)), meanMaePct:mean(outcomes.map(x=>x.maePct).filter(finite).map(Number)),
    meanBarsHeld:mean(outcomes.map(x=>x.barsHeld).filter(finite).map(Number)), finalEquity:equity.at(-1),
  });
  return Object.freeze({
    phase:'57.p24.1', status:'INTEGRATED_RESEARCH_EVALUATED',
    pipeline:['ENTRY_ACCEPTED','HOLD_OR_STRONG_HOLD','PROTECT_OR_CAUTION','EXIT'],
    entryPolicyExternalAndFrozen:true, exitRiskCandidateNotRetuned:true,
    outcomes:Object.freeze(outcomes), equityCurve:Object.freeze(equity), summary,
    ...P24_1_SAFETY,
  });
}
