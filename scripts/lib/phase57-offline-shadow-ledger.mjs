// Offline incremental port of the frozen Phase B event loop. Upstream file remains unchanged.
import assert from 'node:assert/strict';
import {allocateV3,groupOpportunitySets} from './phase57-capital-allocation-v3-entrytime.mjs';
import {PHASE_B_POLICY} from './phase57-capital-allocation-v3-phase-b.mjs';
const finite=x=>typeof x==='number'&&Number.isFinite(x);
const round=(x,d=6)=>Number.isFinite(x)?Number(x.toFixed(d)):x;
export function createOfflineShadowLedger(){
  const initialCapital=1_000_000,maxPositions=10,budgetDivisor=3,lotSize=100,fractionalShares=false;
  let last=-Infinity,halted=false;
  const state={cash:initialCapital,realizedPnl:0,transactionCosts:0,turnoverNotional:0,positions:new Map(),marks:new Map(),curve:[],closedTrades:[],decisions:[],ledgerTrace:[],ledgerAudit:null,rejectionCounts:new Map(),maxConcurrent:0,completedExitCount:0};
  const reject=(entry,event,reason,target,exitsAtTimestamp)=>{state.rejectionCounts.set(reason,(state.rejectionCounts.get(reason)??0)+1);state.decisions.push({eventId:entry.eventId,timestamp:event.timestamp,status:'REJECTED',reason,targetNotionalJpy:round(target),availableCashJpy:round(state.cash),openPositions:state.positions.size,completedExitCount:state.completedExitCount,sameTimestampCashRelease:exitsAtTimestamp>0});};
  const valuation=()=>{let equity=state.cash,gross=0,net=0,long=0,short=0,unrealized=0;const positions=[];for(const p of state.positions.values()){const mark=state.marks.get(p.symbol);assert.ok(mark>0,`mark missing ${p.symbol}`);const markedNotional=mark*p.quantity,pnl=p.direction*(mark-p.entryPrice)*p.quantity;equity+=p.collateralJpy+pnl;gross+=markedNotional;net+=p.direction*markedNotional;unrealized+=pnl;if(p.direction===1)long+=markedNotional;else short+=markedNotional;positions.push({eventId:p.eventId,symbol:p.symbol,direction:p.direction===1?'LONG':'SHORT',quantity:round(p.quantity,9),entryPriceJpy:p.entryPrice,markPriceJpy:mark,referenceNotionalJpy:round(p.referenceNotional),markedNotionalJpy:round(markedNotional),lockedCollateralJpy:round(p.collateralJpy),unrealizedPnlJpy:round(pnl)});}return {equity,gross,net,long,short,unrealized,positions:positions.sort((a,b)=>a.eventId.localeCompare(b.eventId))};};
  function applyEvent(event){
    const weights=new Map();
    for(const set of groupOpportunitySets(event.entries))for(const w of allocateV3(set,'V3_B_RISK'))weights.set(`${set.setId}|${w.symbol}`,w.weight);
    for(const x of event.exitDecisions){const p=state.positions.get(x.eventId);if(p)p.outcome=x;}

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
  return {
    step(input){
      if(halted)throw Error('LEDGER_HALTED');
      try{
        const event=structuredClone(input),t=Date.parse(event.timestamp);
        assert.ok(Number.isFinite(t)&&t>last,'STRICT_EVENT_ORDER');
        assert.ok(Array.isArray(event.marks)&&Array.isArray(event.entries)&&Array.isArray(event.exitDecisions),'EVENT_SCHEMA');
        assert.equal(event.sessionDate,new Date(t+32400000).toISOString().slice(0,10));
        assert.ok(event.sessionDate>='2026-06-18'&&event.sessionDate<='2026-09-09','RESERVED_OR_UNAPPROVED_SESSION_LOCKED');
        const seen=new Set();
        for(const m of event.marks){assert.ok(finite(m.close)&&m.close>0&&!seen.has(m.symbol),'INVALID_OR_DUPLICATE_MARK');seen.add(m.symbol);}
        const ids=new Set();
        for(const e of event.entries){assert.equal(Date.parse(e.decisionTimestamp),t);assert.equal(e.sessionDate,event.sessionDate);assert.ok(finite(e.entryPrice)&&e.entryPrice>0&&[-1,1].includes(e.direction)&&!ids.has(e.eventId),'INVALID_ENTRY');assert.ok(!('outcome' in e),'FUTURE_OUTCOME_FORBIDDEN');ids.add(e.eventId);}
        const exits=new Set();
        for(const e of event.exitDecisions){assert.equal(Date.parse(e.exitTimestamp),t);assert.ok(finite(e.exitPrice)&&e.exitPrice>0&&!exits.has(e.eventId),'INVALID_EXIT');exits.add(e.eventId);}
        event.exits=[...exits];
        applyEvent(event);last=t;
        return structuredClone(state.ledgerTrace.at(-1));
      }catch(e){halted=true;throw e;}
    },
    snapshot(){return structuredClone({cash:state.cash,closedTrades:state.closedTrades,decisions:state.decisions,curve:state.curve,ledgerTrace:state.ledgerTrace,halted});}
  };
}
