import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {
  allocateV3,
  groupOpportunitySets,
} from './phase57-capital-allocation-v3-entrytime.mjs';
import {
  PHASE57_P25_LANE_C_POLICY,
} from '../../predict/portfolio/phase57-p25-lane-c-portfolio-simulator.js';

export const PHASE_B_POLICY=Object.freeze({
  id:'PHASE57_CAPITAL_ALLOCATION_V3_PHASE_B_INTEGRATED_V1',
  initialCapitalJpy:PHASE57_P25_LANE_C_POLICY.initialEquityJpy,
  baseMaxNProfile:'MAX_10',
  maximumConcurrentPositions:10,
  lotSize:PHASE57_P25_LANE_C_POLICY.lotSize,
  roundTripCostPct:PHASE57_P25_LANE_C_POLICY.fixedRoundTripCostPct,
  slippageBps:PHASE57_P25_LANE_C_POLICY.baselineSlippageBps,
  eventOrder:Object.freeze(['PRICE_UPDATE','EXIT','CASH_RELEASE','ENTRY','MARK_TO_MARKET']),
  entryOrder:Object.freeze(['ENTRY_TIMESTAMP_ASC','SYMBOL_ASC']),
  simultaneousSetBudget:'CURRENT_EQUITY_DIVIDED_BY_MAX_N_TIMES_CANDIDATE_COUNT_CAPPED_BY_OPEN_SLOTS',
  unrealizedPnlMayIncreaseBuyingPower:false,
  shortSaleProceedsReusable:false,
  fullyCashCollateralizedShorts:true,
  adaptiveV2Status:'INCOMPATIBLE_INPUT_SCHEMA_NOT_MEASURED',
});

export const PHASE_B_SAFETY=Object.freeze({
  executionAllowed:false,brokerWriteAllowed:false,excelOrderWriteAllowed:false,
  rssOrderFunctionAllowed:false,liveTradingAllowed:false,paperTradingAllowed:false,
  automaticPromotionAllowed:false,productionUpdateAllowed:false,transmitted:false,
});

const finite=x=>typeof x==='number'&&Number.isFinite(x);
const mean=xs=>xs.length?xs.reduce((a,b)=>a+b,0)/xs.length:null;
const median=xs=>{if(!xs.length)return null;const a=[...xs].sort((x,y)=>x-y),m=Math.floor(a.length/2);return a.length%2?a[m]:(a[m-1]+a[m])/2;};
const round=(x,d=6)=>Number.isFinite(x)?Number(x.toFixed(d)):x;
const sha=x=>createHash('sha256').update(JSON.stringify(x)).digest('hex');
const directionNumber=x=>x===1||x==='LONG'?1:x===-1||x==='SHORT'?-1:NaN;
const pct=(direction,entry,exit)=>direction*(exit/entry-1)*100;

function decisionRows(trade){
  return [...(trade?.management?.v4??trade?.v4?.managementDecisions??[])]
    .map(d=>({
      elapsedBars:Number(d?.baseScore?.state?.elapsedBars??d?.holdingBars),
      currentReturnPct:Number(d?.currentReturnPct),
      timestamp:String(d?.timestamp??''),
    }))
    .filter(d=>Number.isFinite(d.elapsedBars)&&Number.isFinite(d.currentReturnPct)&&Number.isFinite(Date.parse(d.timestamp)))
    .sort((a,b)=>a.elapsedBars-b.elapsedBars||a.timestamp.localeCompare(b.timestamp));
}

/** Thin adapter for the selected Development Final bar5 semantics. */
export function runBar5Adapter(trade,{barCloseAt}={}){
  assert.equal(Boolean(trade?.causalEligible??trade?.causal?.eligible),true,'bar5 adapter requires causal eligible trade');
  assert.ok(trade?.v4,'bar5 adapter requires Frozen EXIT v4 continuation');
  const rows=decisionRows(trade);
  const firstBarFromTrade=Number.isFinite(Number(trade.firstBarDirectionalCloseReturnBps))
    ?Number(trade.firstBarDirectionalCloseReturnBps)/100
    :Number.isFinite(Number(trade?.entryQuality?.h1?.gross))
      ?Number(trade.entryQuality.h1.gross)/100
      :rows.find(x=>x.elapsedBars===1)?.currentReturnPct;
  assert.ok(Number.isFinite(firstBarFromTrade),'bar5 adapter first completed-bar return missing');
  const continuation=(classification,dynamicState)=>Object.freeze({
    ...trade.v4,
    classification,dynamicState,
    dynamicReason:classification,
    baseContinuation:'FROZEN_EXIT_V4',
  });
  if(firstBarFromTrade>=0)return continuation('FIRST_BAR_NON_ADVERSE_V4','NON_ADVERSE_CONTINUATION');
  const throughBar5=rows.filter(x=>x.elapsedBars<=5);
  const reclaim=throughBar5.find(x=>x.elapsedBars>1&&x.currentReturnPct>=0);
  if(reclaim)return continuation('RECOVERED_TO_V4','RECOVERED_CONTINUATION');
  const horizon=throughBar5.find(x=>x.elapsedBars===5);
  if(!horizon)return continuation('HORIZON_FALLBACK_V4','DEFENSIVE_FALLBACK_TO_NATIVE_V4');
  const entryPrice=Number(trade.entryPrice);
  const direction=directionNumber(trade.direction);
  assert.ok(entryPrice>0&&[-1,1].includes(direction),'bar5 adapter entry identity invalid');
  const close=typeof barCloseAt==='function'?Number(barCloseAt(trade.symbol,horizon.timestamp)):NaN;
  assert.ok(close>0,'bar5 adapter requires exact completed bar5 close');
  const grossReturnPct=pct(direction,entryPrice,close);
  assert.ok(Math.abs(grossReturnPct-horizon.currentReturnPct)<1e-8,'bar5 close/return parity mismatch');
  return Object.freeze({
    exitTimestamp:horizon.timestamp,
    exitPrice:close,
    exitReason:'DEFENSIVE_EXIT_BAR_5',
    barsHeld:5,
    grossReturnPct,
    netReturnPct:grossReturnPct-PHASE_B_POLICY.roundTripCostPct,
    classification:'DEFENSIVE_EXIT_BAR_5',
    dynamicState:'DEFENSIVE_EXIT',
    dynamicReason:'NO_DIRECTIONAL_CLOSE_RECLAIM_BY_BAR_5',
    baseContinuation:'FROZEN_EXIT_V4',
  });
}

export function verifyBar5Parity({blockA,blockB,barCloseAt,pinned}){
  const officialReference=trade=>{
    const rows=decisionRows(trade);
    const first=Number.isFinite(Number(trade.firstBarDirectionalCloseReturnBps))
      ?Number(trade.firstBarDirectionalCloseReturnBps)/100
      :Number.isFinite(Number(trade?.entryQuality?.h1?.gross))
        ?Number(trade.entryQuality.h1.gross)/100
        :rows.find(x=>x.elapsedBars===1)?.currentReturnPct;
    if(first>=0)return {net:Number(trade.v4.netReturnPct),classification:'FIRST_BAR_NON_ADVERSE_V4'};
    const through=rows.filter(x=>x.elapsedBars<=5);
    if(through.find(x=>x.currentReturnPct>=0))return {net:Number(trade.v4.netReturnPct),classification:'RECOVERED_TO_V4'};
    const at=through.find(x=>x.elapsedBars===5);
    if(!at)return {net:Number(trade.v4.netReturnPct),classification:'HORIZON_FALLBACK_V4'};
    return {net:at.currentReturnPct-PHASE_B_POLICY.roundTripCostPct,classification:'DEFENSIVE_EXIT_BAR_5'};
  };
  const eligible=xs=>xs.filter(t=>Boolean(t?.causalEligible??t?.causal?.eligible)&&t.v4);
  const verify=(rows,label,expected)=>{
    const results=eligible(rows).map(trade=>{
      const actual=runBar5Adapter(trade,{barCloseAt});
      const reference=officialReference(trade);
      assert.ok(Math.abs(actual.netReturnPct-reference.net)<1e-10,`${label} bar5 net parity ${trade.eventId}`);
      assert.equal(actual.classification,reference.classification,`${label} bar5 classification parity ${trade.eventId}`);
      return {eventId:trade.eventId,netReturnPct:actual.netReturnPct,classification:actual.classification,dynamicState:actual.dynamicState,exitTimestamp:actual.exitTimestamp,exitPrice:actual.exitPrice};
    });
    const net=results.reduce((s,x)=>s+x.netReturnPct,0);
    const counts={};for(const x of results)counts[x.classification]=(counts[x.classification]??0)+1;
    assert.equal(results.length,expected.n,`${label} eligible count parity`);
    assert.ok(Math.abs(net-expected.net)<1e-10,`${label} aggregate net parity`);
    assert.deepEqual(counts,expected.stateCounts,`${label} state counts parity`);
    return {label,n:results.length,netReturnPctPoints:net,stateCounts:counts,perTrade:results};
  };
  return Object.freeze({
    status:'BAR5_PARITY_PASS',
    officialImplementation:'scripts/phase57-exit-v5-development-final-sweep.mjs@ea15a594103bd6c9146f19a4aebafb83067d869b',
    pinnedArtifactSha256:pinned.archiveSha256,
    blockA:verify(blockA,'BLOCK_A',pinned.blockA),
    blockB:verify(blockB,'BLOCK_B',pinned.blockB),
    futureBarsReadAfterBar5:false,
    costAppliedExactlyOnceInAdapterNet:true,
  });
}

function maximumDrawdown(curve,initial){
  let peak=initial,maxPct=0,peakTimestamp=null,troughTimestamp=null,currentPeak=null;
  for(const row of curve){
    if(row.equityJpy>peak){peak=row.equityJpy;currentPeak=row.timestamp;}
    const d=peak>0?(peak-row.equityJpy)/peak*100:0;
    if(d>maxPct){maxPct=d;peakTimestamp=currentPeak;troughTimestamp=row.timestamp;}
  }
  return {maxDrawdownPct:maxPct,peakTimestamp,troughTimestamp};
}

function summarize({armId,allocationId,exitId,state,entries,initialCapital,budgetDivisor,lotSize,fractionalShares}){
  const finalEquity=state.cash;
  const pnls=state.closedTrades.map(x=>x.realizedPnlJpy);
  const wins=pnls.filter(x=>x>0),losses=pnls.filter(x=>x<0);
  const grossProfit=wins.reduce((a,b)=>a+b,0),grossLoss=-losses.reduce((a,b)=>a+b,0);
  const dd=maximumDrawdown(state.curve,initialCapital);
  const dailyMap=new Map();for(const x of state.curve)dailyMap.set(x.sessionDate,x.equityJpy);
  let previous=initialCapital;const daily=[...dailyMap].sort(([a],[b])=>a.localeCompare(b)).map(([sessionDate,equityJpy])=>{const returnPct=(equityJpy/previous-1)*100;previous=equityJpy;return {sessionDate,equityJpy,returnPct};});
  const worstDay=daily.length?[...daily].sort((a,b)=>a.returnPct-b.returnPct||a.sessionDate.localeCompare(b.sessionDate))[0]:null;
  const durationRows=[];for(let i=0;i<state.curve.length-1;i++){const a=state.curve[i],b=state.curve[i+1];if(a.sessionDate!==b.sessionDate)continue;const minutes=(Date.parse(b.timestamp)-Date.parse(a.timestamp))/60000;if(minutes>0)durationRows.push({minutes,...a});}
  const totalMinutes=durationRows.reduce((s,x)=>s+x.minutes,0);
  const weighted=k=>totalMinutes?durationRows.reduce((s,x)=>s+x[k]*x.minutes,0)/totalMinutes:0;
  const weightedAbs=k=>totalMinutes?durationRows.reduce((s,x)=>s+Math.abs(x[k])*x.minutes,0)/totalMinutes:0;
  const maxUtil=Math.max(0,...state.curve.map(x=>x.capitalUtilization));
  const maxGross=Math.max(0,...state.curve.map(x=>x.grossExposureJpy));
  const maxAbsNet=Math.max(0,...state.curve.map(x=>Math.abs(x.netExposureJpy)));
  const acceptedNotional=state.closedTrades.reduce((s,x)=>s+x.entryNotionalJpy,0);
  const longNotional=state.closedTrades.filter(x=>x.direction===1).reduce((s,x)=>s+x.entryNotionalJpy,0);
  const symbolNotional={};for(const x of state.closedTrades)symbolNotional[x.symbol]=(symbolNotional[x.symbol]??0)+x.entryNotionalJpy;
  const symbolPnl={};for(const x of state.closedTrades)symbolPnl[x.symbol]=(symbolPnl[x.symbol]??0)+x.realizedPnlJpy;
  const positiveSymbols=Object.entries(symbolPnl).filter(([,v])=>v>0).sort((a,b)=>b[1]-a[1]||a[0].localeCompare(b[0]));
  const totalPositive=positiveSymbols.reduce((s,[,v])=>s+v,0);
  const largestWinningTrade=[...state.closedTrades].filter(x=>x.realizedPnlJpy>0).sort((a,b)=>b.realizedPnlJpy-a.realizedPnlJpy||a.eventId.localeCompare(b.eventId))[0]??null;
  const reason={};for(const x of state.closedTrades){const r=reason[x.exitReason]??={count:0,pnlJpy:0};r.count++;r.pnlJpy+=x.realizedPnlJpy;}
  const symbolShares=Object.entries(symbolNotional).map(([symbol,value])=>({symbol,share:acceptedNotional?value/acceptedNotional:0,notionalJpy:value})).sort((a,b)=>b.share-a.share||a.symbol.localeCompare(b.symbol));
  return {
    armId,allocationId,exitId,budgetDivisor,lotSizeShares:lotSize,fractionalShares,
    initialCapitalJpy:initialCapital,finalEquityJpy:round(finalEquity),netPnlJpy:round(finalEquity-initialCapital),netReturnPct:round((finalEquity/initialCapital-1)*100),
    realizedPnlJpy:round(state.realizedPnl),unrealizedPnlJpy:0,portfolioProfitFactor:grossLoss>0?round(grossProfit/grossLoss):(grossProfit>0?'INF':null),
    maxDrawdown:{maxDrawdownPct:round(dd.maxDrawdownPct),peakTimestamp:dd.peakTimestamp,troughTimestamp:dd.troughTimestamp},worstDay:worstDay?{...worstDay,equityJpy:round(worstDay.equityJpy),returnPct:round(worstDay.returnPct)}:null,
    trade:{candidates:entries.length,accepted:state.closedTrades.length,rejected:entries.length-state.closedTrades.length,winRate:pnls.length?round(wins.length/pnls.length):null,averagePnlJpy:round(mean(pnls)),medianPnlJpy:round(median(pnls)),averageWinJpy:round(mean(wins)),averageLossJpy:round(mean(losses)),averageWinLossRatio:losses.length?round(mean(wins)/Math.abs(mean(losses))):null,largestWinningTrade:largestWinningTrade?{eventId:largestWinningTrade.eventId,symbol:largestWinningTrade.symbol,pnlJpy:largestWinningTrade.realizedPnlJpy,shareOfPositiveProfit:round(largestWinningTrade.realizedPnlJpy/grossProfit)}:null,averageHoldingMinutes:round(mean(state.closedTrades.map(x=>x.holdingMinutes))),transactionCostsJpy:round(state.transactionCosts),rejectionCounts:Object.fromEntries([...state.rejectionCounts].sort())},
    capital:{maximumConcurrentPositions:state.maxConcurrent,averageCapitalUtilization:round(weighted('capitalUtilization')),maximumCapitalUtilization:round(maxUtil),averageGrossExposureJpy:round(weighted('grossExposureJpy')),maximumGrossExposureJpy:round(maxGross),averageNetExposureJpy:round(weighted('netExposureJpy')),averageAbsoluteNetExposureJpy:round(weightedAbs('netExposureJpy')),maximumAbsoluteNetExposureJpy:round(maxAbsNet),averageCashJpy:round(weighted('cashJpy')),grossTurnoverNotionalJpy:round(state.turnoverNotional)},
    directionCapitalShare:{long:acceptedNotional?round(longNotional/acceptedNotional):null,short:acceptedNotional?round((acceptedNotional-longNotional)/acceptedNotional):null},
    symbolConcentration:{topSymbol:symbolShares[0]??null,top3Share:round(symbolShares.slice(0,3).reduce((s,x)=>s+x.share,0)),shares:symbolShares.slice(0,10).map(x=>({...x,share:round(x.share),notionalJpy:round(x.notionalJpy)}))},
    profitContribution:{top1:positiveSymbols[0]?{symbol:positiveSymbols[0][0],pnlJpy:round(positiveSymbols[0][1]),shareOfPositiveProfit:round(positiveSymbols[0][1]/totalPositive)}:null,top3:{pnlJpy:round(positiveSymbols.slice(0,3).reduce((s,[,v])=>s+v,0)),shareOfPositiveProfit:totalPositive?round(positiveSymbols.slice(0,3).reduce((s,[,v])=>s+v,0)/totalPositive):null,symbols:positiveSymbols.slice(0,3).map(([symbol])=>symbol)}},
    exitReasonDistribution:Object.fromEntries(Object.entries(reason).sort(([a],[b])=>a.localeCompare(b)).map(([k,v])=>[k,{count:v.count,pnlJpy:round(v.pnlJpy)}])),
    accounting:{cashInsufficientSkips:(state.rejectionCounts.get('INSUFFICIENT_AVAILABLE_CASH_FOR_100_SHARES')??0)+(state.rejectionCounts.get('INSUFFICIENT_AVAILABLE_CASH_FOR_FRACTIONAL_SHARE')??0),positionLimitSkips:state.rejectionCounts.get('MAX_CONCURRENT_POSITIONS')??0,costDoubleCounted:false,shortSaleProceedsReusable:false,unrealizedPnlBuyingPower:false},
    dailyEquity:daily.map(x=>({...x,equityJpy:round(x.equityJpy),returnPct:round(x.returnPct)})),
    ledgerAudit:state.ledgerAudit,ledgerTrace:state.ledgerTrace,
    curve:state.curve,closedTrades:state.closedTrades,decisions:state.decisions,
  };
}

/** Event-time cash ledger shared by all six arms. */
export function simulatePhaseB({opportunities,trades,allocationId,exitId,barCloseAt,marks,initialCapital=PHASE_B_POLICY.initialCapitalJpy,maxPositions=PHASE_B_POLICY.maximumConcurrentPositions,budgetDivisor=maxPositions,lotSize=PHASE_B_POLICY.lotSize,fractionalShares=false,armId=null}){
  assert.ok(['V3_0_EQUAL','V3_A_RANK','V3_B_RISK'].includes(allocationId),'unknown Phase B allocation');
  assert.ok(['FROZEN_EXIT_V4','EXIT_V5_DYNAMIC_RECLAIM_BAR_5'].includes(exitId),'unknown Phase B exit');
  assert.ok(Number.isInteger(maxPositions)&&maxPositions>0,'positive integer position limit required');
  assert.ok(finite(budgetDivisor)&&budgetDivisor>0,'positive budget divisor required');
  assert.ok(finite(lotSize)&&lotSize>0,'positive lot size required');
  const tradeById=new Map(trades.map(x=>[x.eventId,x]));
  const entries=opportunities.map(o=>{
    const t=tradeById.get(o.eventId);assert.ok(t,`trade missing ${o.eventId}`);
    const outcome=exitId==='FROZEN_EXIT_V4'?t.v4:runBar5Adapter(t,{barCloseAt});
    return {...o,entryPrice:Number(o.entryPrice),outcome};
  }).sort((a,b)=>a.decisionTimestamp.localeCompare(b.decisionTimestamp)||a.symbol.localeCompare(b.symbol));
  const sets=groupOpportunitySets(entries.map(({outcome,...x})=>({...x,outcomeUsed:false,exitUsed:false})));
  const weights=new Map();
  for(const set of sets)for(const a of allocateV3(set,allocationId))weights.set(`${set.setId}|${a.symbol}`,a.weight);
  const events=new Map();const at=(timestamp,sessionDate)=>{if(!events.has(timestamp))events.set(timestamp,{timestamp,sessionDate,marks:[],entries:[],exits:[]});const e=events.get(timestamp);assert.equal(e.sessionDate,sessionDate);return e;};
  for(const m of marks)at(m.timestamp,m.sessionDate).marks.push(m);
  for(const e of entries){at(e.decisionTimestamp,e.sessionDate).entries.push(e);at(e.outcome.exitTimestamp,e.sessionDate).exits.push(e.eventId);}
  const state={cash:initialCapital,realizedPnl:0,transactionCosts:0,turnoverNotional:0,positions:new Map(),marks:new Map(),curve:[],closedTrades:[],decisions:[],ledgerTrace:[],ledgerAudit:null,rejectionCounts:new Map(),maxConcurrent:0,completedExitCount:0};
  const reject=(entry,event,reason,target,exitsAtTimestamp)=>{state.rejectionCounts.set(reason,(state.rejectionCounts.get(reason)??0)+1);state.decisions.push({eventId:entry.eventId,timestamp:event.timestamp,status:'REJECTED',reason,targetNotionalJpy:round(target),availableCashJpy:round(state.cash),openPositions:state.positions.size,completedExitCount:state.completedExitCount,sameTimestampCashRelease:exitsAtTimestamp>0});};
  const valuation=()=>{let equity=state.cash,gross=0,net=0,long=0,short=0,unrealized=0;const positions=[];for(const p of state.positions.values()){const mark=state.marks.get(p.symbol);assert.ok(mark>0,`mark missing ${p.symbol}`);const markedNotional=mark*p.quantity,pnl=p.direction*(mark-p.entryPrice)*p.quantity;equity+=p.collateralJpy+pnl;gross+=markedNotional;net+=p.direction*markedNotional;unrealized+=pnl;if(p.direction===1)long+=markedNotional;else short+=markedNotional;positions.push({eventId:p.eventId,symbol:p.symbol,direction:p.direction===1?'LONG':'SHORT',quantity:round(p.quantity,9),entryPriceJpy:p.entryPrice,markPriceJpy:mark,referenceNotionalJpy:round(p.referenceNotional),markedNotionalJpy:round(markedNotional),lockedCollateralJpy:round(p.collateralJpy),unrealizedPnlJpy:round(pnl)});}return {equity,gross,net,long,short,unrealized,positions:positions.sort((a,b)=>a.eventId.localeCompare(b.eventId))};};
  for(const event of [...events.values()].sort((a,b)=>a.timestamp.localeCompare(b.timestamp))){
    const previousRealizedEquity=initialCapital+state.realizedPnl,eventStartCash=state.cash;
    for(const m of event.marks.sort((a,b)=>a.symbol.localeCompare(b.symbol)))state.marks.set(m.symbol,m.close);
    let exitsAtTimestamp=0,exitCashReleased=0,exitGrossPnl=0,exitFees=0;
    const exitRows=[],entryRows=[];
    for(const id of event.exits.sort()){
      const p=state.positions.get(id);if(!p)continue;const exitPrice=p.outcome.exitPrice,halfCost=p.referenceNotional*(PHASE_B_POLICY.roundTripCostPct/200),grossPnl=p.direction*(exitPrice-p.entryPrice)*p.quantity,cashRelease=p.collateralJpy+grossPnl-halfCost,realized=grossPnl-p.entryCostJpy-halfCost;
      const cashBefore=state.cash;
      state.cash+=cashRelease;state.realizedPnl+=grossPnl-halfCost;state.transactionCosts+=halfCost;state.turnoverNotional+=exitPrice*p.quantity;
      state.closedTrades.push({eventId:id,symbol:p.symbol,direction:p.direction,mshScore:p.mshScore,risk:p.recentRealizedVolatility,entryTimestamp:p.decisionTimestamp,exitTimestamp:event.timestamp,entryPrice:p.entryPrice,exitPrice,quantity:p.quantity,entryNotionalJpy:round(p.referenceNotional),transactionCostsJpy:round(p.entryCostJpy+halfCost),realizedPnlJpy:round(realized),holdingMinutes:(Date.parse(event.timestamp)-Date.parse(p.decisionTimestamp))/60000,exitReason:p.outcome.exitReason,exitClassification:p.outcome.classification??'FROZEN_EXIT_V4'});
      assert.ok(Math.abs((p.entryCostJpy+halfCost)-p.referenceNotional*(PHASE_B_POLICY.roundTripCostPct/100))<1e-7,`round-trip cost exactly once ${id}`);
      exitRows.push({eventId:id,symbol:p.symbol,direction:p.direction===1?'LONG':'SHORT',quantity:round(p.quantity,9),referenceNotionalJpy:round(p.referenceNotional),grossPnlJpy:round(grossPnl),exitFeeJpy:round(halfCost),cashReleasedJpy:round(cashRelease),cashBeforeJpy:round(cashBefore),cashAfterJpy:round(state.cash),costChargedExactlyOnce:true});
      exitCashReleased+=cashRelease;exitGrossPnl+=grossPnl;exitFees+=halfCost;
      state.positions.delete(id);state.completedExitCount++;exitsAtTimestamp++;
    }
    const buyingPowerBefore=state.cash;
    let entryCashConsumed=0,entryFees=0;
    if(event.entries.length){
      const before=valuation(),openSlots=Math.max(0,maxPositions-state.positions.size),setCount=event.entries.length,setBudget=before.equity/budgetDivisor*Math.min(setCount,openSlots);
      for(const entry of [...event.entries].sort((a,b)=>a.symbol.localeCompare(b.symbol))){
        const weight=weights.get(`${entry.sessionDate}|${entry.decisionTimestamp}|${entry.symbol}`);assert.ok(finite(weight)&&weight>0,'allocation weight missing');const target=setBudget*weight;
        if(state.positions.size>=maxPositions){reject(entry,event,'MAX_CONCURRENT_POSITIONS',target,exitsAtTimestamp);continue;}
        if([...state.positions.values()].some(p=>p.symbol===entry.symbol)){reject(entry,event,'SYMBOL_ALREADY_OPEN',target,exitsAtTimestamp);continue;}
        const halfRate=PHASE_B_POLICY.roundTripCostPct/200;
        const maxByTarget=fractionalShares?target/entry.entryPrice:Math.floor(target/entry.entryPrice/lotSize)*lotSize;
        const maxByCashRaw=state.cash/(entry.entryPrice*(1+halfRate));
        const maxByCash=fractionalShares?maxByCashRaw:Math.floor(maxByCashRaw/lotSize)*lotSize;
        const quantity=Math.min(maxByTarget,maxByCash);
        const minimumQuantity=fractionalShares?1e-9:lotSize;
        if(quantity<minimumQuantity){const oneLotCash=entry.entryPrice*(1+halfRate)*lotSize;const reason=fractionalShares?'INSUFFICIENT_AVAILABLE_CASH_FOR_FRACTIONAL_SHARE':state.cash<oneLotCash?'INSUFFICIENT_AVAILABLE_CASH_FOR_100_SHARES':'TARGET_BUDGET_BELOW_100_SHARES';reject(entry,event,reason,target,exitsAtTimestamp);continue;}
        const notional=entry.entryPrice*quantity,entryCost=notional*halfRate,cashDebit=notional+entryCost,buyingPowerBeforeEntry=state.cash;assert.ok(cashDebit<=buyingPowerBeforeEntry+1e-8,'entry required cash exceeds available buying power');state.cash-=cashDebit;state.realizedPnl-=entryCost;state.transactionCosts+=entryCost;state.turnoverNotional+=notional;state.positions.set(entry.eventId,{...entry,direction:entry.direction,quantity,referenceNotional:notional,collateralJpy:notional,entryCostJpy:entryCost});state.maxConcurrent=Math.max(state.maxConcurrent,state.positions.size);state.decisions.push({eventId:entry.eventId,timestamp:event.timestamp,status:'ACCEPTED',weight:round(weight),targetNotionalJpy:round(target),quantity:round(quantity,9),entryNotionalJpy:round(notional),cashDebitJpy:round(cashDebit),buyingPowerBeforeJpy:round(buyingPowerBeforeEntry),availableCashAfterJpy:round(state.cash),openPositions:state.positions.size,completedExitCount:state.completedExitCount,sameTimestampCashRelease:exitsAtTimestamp>0,budgetDivisor,fractionalShares});
        entryRows.push({eventId:entry.eventId,symbol:entry.symbol,direction:entry.direction===1?'LONG':'SHORT',quantity:round(quantity,9),entryNotionalJpy:round(notional),requiredCollateralJpy:round(notional),entryFeeJpy:round(entryCost),requiredCashJpy:round(cashDebit),buyingPowerBeforeJpy:round(buyingPowerBeforeEntry),buyingPowerAfterJpy:round(state.cash),shortSaleProceedsCreditedJpy:0,requiredCashWithinBuyingPower:true});entryCashConsumed+=cashDebit;entryFees+=entryCost;
      }
    }
    const v=valuation(),active=[...state.positions.values()],lockedShort=active.filter(p=>p.direction===-1).reduce((s,p)=>s+p.collateralJpy,0),shortReference=active.filter(p=>p.direction===-1).reduce((s,p)=>s+p.referenceNotional,0),lockedLong=active.filter(p=>p.direction===1).reduce((s,p)=>s+p.collateralJpy,0),lockedTotal=lockedShort+lockedLong,currentRealizedEquity=initialCapital+state.realizedPnl,costsThisTimestamp=entryFees+exitFees;
    const checks={
      availableCashNonnegative:state.cash>=-1e-7,
      shortSaleProceedsNotReused:entryRows.filter(x=>x.direction==='SHORT').every(x=>x.shortSaleProceedsCreditedJpy===0),
      unrealizedGainsExcludedFromBuyingPower:Math.abs(buyingPowerBefore-(eventStartCash+exitCashReleased))<1e-6,
      lockedShortCollateralEqualsReferenceNotional:Math.abs(lockedShort-shortReference)<1e-6&&active.filter(p=>p.direction===-1).every(p=>Math.abs(p.collateralJpy-p.referenceNotional)<1e-7),
      entryRequiredCashWithinBuyingPower:entryRows.every(x=>x.requiredCashWithinBuyingPower),
      exitReleaseBeforeSameTimestampEntry:!(exitRows.length&&entryRows.length)||Math.abs(buyingPowerBefore-(eventStartCash+exitCashReleased))<1e-6,
      grossExposureWithinCurrentEquity:v.gross<=v.equity+1e-6,
      absoluteNetExposureWithinCurrentEquity:Math.abs(v.net)<=v.equity+1e-6,
      costsChargedExactlyOnce:exitRows.every(x=>x.costChargedExactlyOnce),
      positionLimitRespected:state.positions.size<=maxPositions,
      quantityUnitValid:fractionalShares?active.every(p=>p.quantity>0):active.every(p=>Math.abs(p.quantity/lotSize-Math.round(p.quantity/lotSize))<1e-9),
      realizedEquityReconciles:Math.abs(currentRealizedEquity-(previousRealizedEquity+exitGrossPnl-costsThisTimestamp))<1e-6&&Math.abs(currentRealizedEquity-(state.cash+lockedTotal))<1e-6,
    };
    for(const [name,passed] of Object.entries(checks))assert.equal(passed,true,`ledger invariant ${name} at ${event.timestamp}`);
    const trace={timestamp:event.timestamp,sessionDate:event.sessionDate,currentRealizedEquityJpy:round(currentRealizedEquity),currentEquityJpy:round(v.equity),currentCashJpy:round(state.cash),availableCashJpy:round(state.cash),lockedShortCollateralJpy:round(lockedShort),lockedLongCapitalJpy:round(lockedLong),shortReferenceNotionalJpy:round(shortReference),longNotionalJpy:round(v.long),shortNotionalJpy:round(v.short),grossExposureJpy:round(v.gross),signedNetExposureJpy:round(v.net),absoluteNetExposureJpy:round(Math.abs(v.net)),unrealizedPnlJpy:round(v.unrealized),openPositions:v.positions,positionCount:state.positions.size,exitCashReleasedJpy:round(exitCashReleased),entryCashConsumedJpy:round(entryCashConsumed),feesJpy:round(costsThisTimestamp),buyingPowerBeforeJpy:round(buyingPowerBefore),buyingPowerAfterJpy:round(state.cash),previousRealizedEquityJpy:round(previousRealizedEquity),exitGrossPnlJpy:round(exitGrossPnl),eventOrder:PHASE_B_POLICY.eventOrder,exits:exitRows,entries:entryRows,currentEquityBasis:{grossRatio:round(v.gross/v.equity),absoluteNetRatio:round(Math.abs(v.net)/v.equity),initialCapitalComparisonNotUsedForInvariant:true},invariants:checks};
    state.ledgerTrace.push(trace);state.curve.push({timestamp:event.timestamp,sessionDate:event.sessionDate,cashJpy:round(state.cash),equityJpy:round(v.equity),realizedPnlJpy:round(state.realizedPnl),unrealizedPnlJpy:round(v.unrealized),grossExposureJpy:round(v.gross),netExposureJpy:round(v.net),longExposureJpy:round(v.long),shortExposureJpy:round(v.short),capitalUtilization:v.equity>0?round(v.gross/v.equity):null,openPositions:state.positions.size});
  }
  assert.equal(state.positions.size,0,'Phase B ended with open positions');
  assert.ok(Math.abs(state.cash-(initialCapital+state.realizedPnl))<1e-6,'Phase B final cash accounting invariant');
  state.ledgerAudit={status:'LEDGER_INVARIANTS_PASS',eventCount:state.ledgerTrace.length,violationCount:0,checks:Object.keys(state.ledgerTrace[0]?.invariants??{}),comparisonBasis:'CURRENT_MARK_TO_MARKET_EQUITY_NOT_INITIAL_CAPITAL',shortCollateralBasis:'ENTRY_REFERENCE_NOTIONAL_FULLY_CASH_COLLATERALIZED',fractionalShareQuantityCheck:fractionalShares?'THEORETICAL_FRACTIONAL_POSITIVE_QUANTITY':'EXACT_LOT_MULTIPLE'};
  return summarize({armId:armId??`${allocationId}__${exitId}`,allocationId,exitId,state,entries,initialCapital,budgetDivisor,lotSize,fractionalShares});
}

export function executionAttribution(left,right,{label,leftName,rightName}){
  const L=new Map(left.closedTrades.map(x=>[x.eventId,x])),R=new Map(right.closedTrades.map(x=>[x.eventId,x]));
  const common=[...L.keys()].filter(k=>R.has(k)),leftOnly=[...L.keys()].filter(k=>!R.has(k)),rightOnly=[...R.keys()].filter(k=>!L.has(k));
  const commonDelta=common.reduce((s,k)=>s+R.get(k).realizedPnlJpy-L.get(k).realizedPnlJpy,0),leftOnlyContribution=-leftOnly.reduce((s,k)=>s+L.get(k).realizedPnlJpy,0),rightOnlyContribution=rightOnly.reduce((s,k)=>s+R.get(k).realizedPnlJpy,0),total=right.netPnlJpy-left.netPnlJpy;
  assert.ok(Math.abs(total-(commonDelta+leftOnlyContribution+rightOnlyContribution))<1e-3,'attribution does not recompose within sub-yen rounding tolerance');
  const leftDecisions=new Map(left.decisions.map(x=>[x.eventId,x]));
  const earlierRelease=rightOnly.filter(id=>{const rejected=leftDecisions.get(id);if(!['INSUFFICIENT_AVAILABLE_CASH_FOR_100_SHARES','MAX_CONCURRENT_POSITIONS','TARGET_BUDGET_BELOW_100_SHARES'].includes(rejected?.reason))return false;const t=Date.parse(R.get(id).entryTimestamp);return common.some(k=>Date.parse(R.get(k).exitTimestamp)<Date.parse(L.get(k).exitTimestamp)&&Date.parse(R.get(k).exitTimestamp)<=t);});
  return {label,leftArm:leftName,rightArm:rightName,totalDeltaJpy:round(total),commonTrades:{count:common.length,deltaJpy:round(commonDelta)},leftOnlyTrades:{count:leftOnly.length,contributionToDeltaJpy:round(leftOnlyContribution),eventIds:leftOnly.sort()},rightOnlyTrades:{count:rightOnly.length,contributionToDeltaJpy:round(rightOnlyContribution),eventIds:rightOnly.sort()},earlierExitCapitalReleaseAdditionalTrades:{count:earlierRelease.length,pnlJpy:round(earlierRelease.reduce((s,k)=>s+R.get(k).realizedPnlJpy,0)),eventIds:earlierRelease.sort()},recomposed:true};
}

export const phaseBHashes=({opportunities,trades,marks})=>Object.freeze({
  opportunitySha256:sha(opportunities.map(x=>({eventId:x.eventId,mshScore:x.mshScore,risk:x.recentRealizedVolatility,entryPrice:x.entryPrice}))),
  tradeOutcomeSha256:sha(trades.map(x=>({eventId:x.eventId,v4:x.v4}))),
  markSha256:sha(marks),
});
