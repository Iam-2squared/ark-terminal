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
function timeBucket(timestamp){if(!timestamp)return'UNKNOWN';const p=new Intl.DateTimeFormat('en-GB',{timeZone:'Asia/Tokyo',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).formatToParts(new Date(timestamp));const o=Object.fromEntries(p.map(x=>[x.type,x.value]));const m=Number(o.hour)*60+Number(o.minute);if(m<600)return'09:00-09:59';if(m<690)return'10:00-11:29';if(m<840)return'11:30-13:59';return'14:00-15:30';}
function barsBucket(n){if(n<=1)return'1';if(n<=3)return'2-3';if(n<=6)return'4-6';if(n<=12)return'7-12';return'13+';}
function summarize(xs){const rs=xs.map(x=>Number(x.netReturnPct)).filter(Number.isFinite),eq=[1];for(const r of rs)eq.push(eq.at(-1)*(1+r/100));return Object.freeze({n:rs.length,meanNetReturnPct:mean(rs),profitFactor:profitFactor(rs),winRate:rs.length?rs.filter(x=>x>0).length/rs.length:null,netReturnPct:(eq.at(-1)-1)*100,maxDrawdownPct:maxDrawdownPct(eq),meanMfePct:mean(xs.map(x=>Number(x.mfePct)).filter(Number.isFinite)),meanMaePct:mean(xs.map(x=>Number(x.maePct)).filter(Number.isFinite)),meanGivebackPct:mean(xs.map(x=>Number(x.mfePct)-Number(x.grossReturnPct)).filter(Number.isFinite)),meanCaptureRatio:mean(xs.map(x=>Number(x.captureRatio)).filter(Number.isFinite)),meanBarsHeld:mean(xs.map(x=>Number(x.barsHeld)).filter(Number.isFinite))});}
function group(outcomes,keyFn){const m=new Map();for(const x of outcomes){const k=String(keyFn(x)??'UNKNOWN');if(!m.has(k))m.set(k,[]);m.get(k).push(x);}return Object.fromEntries([...m].map(([k,v])=>[k,summarize(v)]));}

export function evaluateIntegratedTradeResearch(rows=[],options={}){
  const accepted=(Array.isArray(rows)?rows:[]).filter(r=>r?.entryAccepted===true);
  const outcomes=[];
  const respectFrozenEntryHorizon=options.respectFrozenEntryHorizon!==false;
  for(const row of accepted){
    const frozenHorizon=finite(row?.baseHorizonBars)&&Number(row.baseHorizonBars)>0?Math.max(1,Math.floor(Number(row.baseHorizonBars))):null;
    const tradeManagement={...(options.tradeManagement??{})};
    if(respectFrozenEntryHorizon&&frozenHorizon!=null) tradeManagement.maxHoldBars=frozenHorizon;
    const out=simulateTradeManagementStateMachine(row,tradeManagement);
    if(!out)continue;
    outcomes.push(Object.freeze({
      symbol:row.symbol??null, setup:row.setup??null, entryBand:row.entryBand??null,
      entryTimestamp:row.entryTimestamp??row.futureBars?.[0]?.timestamp??null,
      baseHorizonBars:frozenHorizon,timeBucket:timeBucket(row.entryTimestamp??row.futureBars?.[0]?.timestamp),
      direction:out.direction, exitTimestamp:out.outcomeAt, exitReason:out.exitReason,
      barsHeld:out.barsHeld,barsHeldBucket:barsBucket(out.barsHeld), grossReturnPct:out.grossReturnPct, netReturnPct:out.netReturnPct,
      mfePct:out.mfePct, maePct:out.maePct, captureRatio:out.captureRatio,
      givebackPct:Number(out.mfePct)-Number(out.grossReturnPct),stateVisitCounts:out.stateVisitCounts,
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
    meanGivebackPct:mean(outcomes.map(x=>x.givebackPct).filter(finite).map(Number)),meanCaptureRatio:mean(outcomes.map(x=>x.captureRatio).filter(finite).map(Number)),
    meanBarsHeld:mean(outcomes.map(x=>x.barsHeld).filter(finite).map(Number)), finalEquity:equity.at(-1),
  });
  const attribution=Object.freeze({byDirection:group(outcomes,x=>x.direction),bySetup:group(outcomes,x=>x.setup),byExitReason:group(outcomes,x=>x.exitReason),bySymbol:group(outcomes,x=>x.symbol),byTimeBucket:group(outcomes,x=>x.timeBucket),byBarsHeld:group(outcomes,x=>x.barsHeldBucket),byFrozenHorizon:group(outcomes,x=>x.baseHorizonBars)});
  return Object.freeze({
    phase:'57.p24.3', status:'INTEGRATED_RESEARCH_EVALUATED',
    pipeline:['FROZEN_ENTRY_ACCEPTED','HOLD_OR_STRONG_HOLD','PROTECT_OR_CAUTION','EXIT_AT_OR_BEFORE_FROZEN_ENTRY_HORIZON'],
    entryPolicyExternalAndFrozen:true,frozenEntryHorizonPreserved:respectFrozenEntryHorizon, exitRiskCandidateNotRetuned:true,
    outcomes:Object.freeze(outcomes), equityCurve:Object.freeze(equity), summary,attribution,
    ...P24_1_SAFETY,
  });
}
