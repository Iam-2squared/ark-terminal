import {createHash} from 'node:crypto';

export const PHASE57_P25_LANE_C_SAFETY=Object.freeze({
  phase:'57.p25.lane-c.portfolio-capital-allocation',
  mode:'READ_ONLY_EVENT_TIME_PORTFOLIO_RESEARCH',
  researchOnly:true,
  executionAllowed:false,
  brokerWriteAllowed:false,
  excelOrderWriteAllowed:false,
  rssOrderFunctionAllowed:false,
  liveTradingAllowed:false,
  paperTradingAllowed:false,
  automaticPromotionAllowed:false,
  productionUpdateAllowed:false,
  transmitted:false,
  freshHoldoutConsumed:false,
});

export const PHASE57_P25_LANE_C_POLICY=Object.freeze({
  initialEquityJpy:1_000_000,
  lotSize:100,
  fixedRoundTripCostPct:0.05,
  baselineSlippageBps:0,
  markToMarketRequired:true,
  eventOrder:Object.freeze(['PRICE_UPDATE','EXIT','CASH_RELEASE','ENTRY']),
  entryOrder:Object.freeze(['ENTRY_TIMESTAMP_ASC','SYMBOL_ASC']),
  targetSlotBudgetFormula:'CURRENT_PORTFOLIO_EQUITY_DIVIDED_BY_MAX_POSITIONS',
  purchaseCashConstraintRequired:true,
  unrealizedPnlMayIncreaseBuyingPower:false,
  sectorConstraintApplied:false,
  deterministicConfidenceRankingApplied:false,
  futureOutcomeVisibleToAllocator:false,
  winnerSelectionAllowed:false,
});

export const PHASE57_P25_LANE_C_ALLOCATOR_VISIBLE_FIELDS=Object.freeze([
  'key','sessionDate','symbol','sector','signalDirection','entryTimestamp','entryReferencePrice',
]);

export const PHASE57_P25_LANE_C_ALLOCATION_PROFILES=Object.freeze([
  Object.freeze({id:'MAX_10',label:'Max 10',maxPositions:10,sizingRule:'EQUITY_DIVIDED_BY_MAX_POSITIONS'}),
  Object.freeze({id:'MAX_4',label:'Max 4',maxPositions:4,sizingRule:'EQUITY_DIVIDED_BY_MAX_POSITIONS'}),
  Object.freeze({id:'MAX_3',label:'Max 3',maxPositions:3,sizingRule:'EQUITY_DIVIDED_BY_MAX_POSITIONS'}),
  Object.freeze({id:'MAX_2',label:'Max 2',maxPositions:2,sizingRule:'EQUITY_DIVIDED_BY_MAX_POSITIONS'}),
]);

/**
 * GitHub source-of-truth audit. Neither existing path is silently relabelled Max 10.
 * The formal P25 metric is not a causal portfolio because it averages all signals in
 * a completed session. The Paper/Shadow scaffold is causal but changes the frozen
 * Entry set (long-only) and does not process the formal Fixed-Horizon exits.
 */
export const PHASE57_P25_LANE_C_CURRENT_BASELINE_AUDIT=Object.freeze({
  status:'CURRENT_EXISTING_REFERENCE_ONLY_PENDING_CAUSAL_PRECOMMIT',
  max10AssumedEquivalent:false,
  formalP25Evaluation:Object.freeze({
    implementation:'phase57-p25-2-trade-frequency-evaluator.sessionEqualWeightPortfolio',
    semantics:'COMPLETED_SESSION_EQUAL_WEIGHT_RETURN_REFERENCE',
    eventTimeCashLedger:false,
    hundredShareLot:false,
    concurrentPositionConstraint:false,
    causalAllocationComparable:false,
    reason:'The completed-session signal count is unavailable at earlier Entry timestamps.',
  }),
  researchPaperShadow:Object.freeze({
    implementation:'p25-offline-paper-replay + paper-risk',
    defaultQuantity:100,
    maximumOrderValueJpy:300_000,
    maximumPositionValueJpy:300_000,
    minimumCashReserveJpy:50_000,
    allowShort:false,
    formalFixedExitProcessed:false,
    sameFrozenEntryComparable:false,
  }),
  laneCDisposition:Object.freeze({
    currentExistingKeptAsReference:true,
    currentExistingEligibleForWinnerSelection:false,
    causalCurrentProfileInvented:false,
    futurePrecommittedCurrentProfileSupported:true,
  }),
});

const VARIANTS=Object.freeze(['FIXED_5','OLD_FIXED_30','DYNAMIC_30','DYNAMIC_40','DYNAMIC_50']);
const FALSE_SAFETY_KEYS=Object.freeze([
  'executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed',
  'liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed',
  'transmitted','freshHoldoutConsumed',
]);

const finite=value=>value!==null&&value!==undefined&&value!==''&&Number.isFinite(Number(value));
const round=(value,digits=6)=>Number.isFinite(value)?Number(value.toFixed(digits)):value;
const mean=values=>values.length?values.reduce((sum,value)=>sum+value,0)/values.length:null;
const iso=value=>{
  const milliseconds=Date.parse(String(value??''));
  if(!Number.isFinite(milliseconds))throw new Error(`invalid Lane C timestamp: ${value??'MISSING'}`);
  return new Date(milliseconds).toISOString();
};
const normalizeSymbol=value=>{
  const symbol=String(value??'').trim().toUpperCase();
  if(!symbol)throw new Error('Lane C symbol is required');
  return symbol;
};
const normalizeSector=value=>String(value??'UNKNOWN').trim().toUpperCase()||'UNKNOWN';
const sha256=value=>createHash('sha256').update(JSON.stringify(value)).digest('hex');

function assertSafety(){
  for(const key of FALSE_SAFETY_KEYS){
    if(PHASE57_P25_LANE_C_SAFETY[key]!==false)throw new Error(`Lane C safety ${key} must remain false`);
  }
}

function normalizeBar(bar,{sessionDate,symbol,index}){
  const timestamp=iso(bar?.timestamp??bar?.time);
  const close=Number(bar?.close);
  if(!Number.isFinite(close)||close<=0)throw new Error(`invalid Lane C close for ${symbol} ${sessionDate} at bar ${index}`);
  return Object.freeze({sessionDate,timestamp,symbol,close});
}

function normalizeTrade(row,{sessionDate,managementMode,index}){
  if(row?.entryAccepted!==true||row?.frozenBeforeOutcome!==true||row?.currentOutcomeUsed!==false){
    throw new Error(`Lane C accepts only frozen outcome-free Entry identities before outcome join (${sessionDate} row ${index})`);
  }
  const symbol=normalizeSymbol(row.symbol);
  const entryTimestamp=iso(row.entryTimestamp??row.featureCutoff);
  const exitTimestamp=iso(row.exitTimestamp);
  if(exitTimestamp<=entryTimestamp)throw new Error(`Lane C exit must be after Entry for ${symbol} at ${entryTimestamp}`);
  const entryReferencePrice=Number(row.entryPrice),exitReferencePrice=Number(row.exitPrice);
  const signalDirection=Number(row.signalDirection);
  if(!Number.isFinite(entryReferencePrice)||entryReferencePrice<=0||!Number.isFinite(exitReferencePrice)||exitReferencePrice<=0){
    throw new Error(`Lane C resolved prices are required for ${symbol} at ${entryTimestamp}`);
  }
  if(![-1,1].includes(signalDirection))throw new Error(`Lane C direction must be -1 or 1 for ${symbol}`);
  const key=`${sessionDate}|${entryTimestamp}|${symbol}`;
  const entry=Object.freeze({
    key,sessionDate,symbol,sector:normalizeSector(row.sector),signalDirection,entryTimestamp,entryReferencePrice,
  });
  const outcome=Object.freeze({
    key,exitTimestamp,exitReferencePrice,exitReason:String(row.exitReason??managementMode),
    netReturnPct:finite(row.netReturnPct)?Number(row.netReturnPct):null,
    sourceManagementMode:managementMode,
  });
  return Object.freeze({entry,outcome});
}

function samePrice(actual,expected){
  const scale=Math.max(1,Math.abs(actual),Math.abs(expected));
  return Math.abs(actual-expected)<=scale*1e-9;
}

function normalizeSessions(sessions,managementMode){
  const ordered=[...(Array.isArray(sessions)?sessions:[])].sort((a,b)=>String(a?.sessionDate??'').localeCompare(String(b?.sessionDate??'')));
  const seenSessions=new Set(),seenTrades=new Set(),bars=[],entries=[],outcomes=new Map(),evaluatedSessions=[];
  for(const session of ordered){
    const sessionDate=String(session?.sessionDate??'').trim();
    if(!/^\d{4}-\d{2}-\d{2}$/.test(sessionDate))throw new Error('Lane C sessionDate must be YYYY-MM-DD');
    if(seenSessions.has(sessionDate))throw new Error(`duplicate Lane C session: ${sessionDate}`);
    seenSessions.add(sessionDate);evaluatedSessions.push(sessionDate);
    const source=session?.sessionBarsBySymbol instanceof Map?session.sessionBarsBySymbol:new Map(Object.entries(session?.sessionBarsBySymbol??{}));
    const barLookup=new Map();
    for(const [rawSymbol,rows] of source){
      const symbolText=String(rawSymbol??'');
      const symbol=normalizeSymbol(symbolText.includes('.')?symbolText:`${symbolText}.T`);
      const normalized=(Array.isArray(rows)?rows:[]).map((bar,index)=>normalizeBar(bar,{sessionDate,symbol,index})).sort((a,b)=>a.timestamp.localeCompare(b.timestamp));
      if(new Set(normalized.map(bar=>bar.timestamp)).size!==normalized.length)throw new Error(`duplicate Lane C bars for ${symbol} ${sessionDate}`);
      barLookup.set(symbol,new Map(normalized.map(bar=>[bar.timestamp,bar.close])));
      bars.push(...normalized);
    }
    for(const [index,row] of (Array.isArray(session?.trades)?session.trades:[]).entries()){
      if(String(row?.sessionDate??sessionDate)!==sessionDate)throw new Error(`Lane C trade session mismatch for ${sessionDate}`);
      const normalized=normalizeTrade(row,{sessionDate,managementMode,index});
      if(seenTrades.has(normalized.entry.key))throw new Error(`duplicate Lane C frozen Entry: ${normalized.entry.key}`);
      seenTrades.add(normalized.entry.key);
      const symbolBars=barLookup.get(normalized.entry.symbol);
      if(!symbolBars)throw new Error(`Lane C bars missing for ${normalized.entry.symbol} ${sessionDate}`);
      const entryMark=symbolBars.get(normalized.entry.entryTimestamp),exitMark=symbolBars.get(normalized.outcome.exitTimestamp);
      if(!Number.isFinite(entryMark)||!samePrice(entryMark,normalized.entry.entryReferencePrice)){
        throw new Error(`Lane C Entry mark mismatch for ${normalized.entry.key}`);
      }
      if(!Number.isFinite(exitMark)||!samePrice(exitMark,normalized.outcome.exitReferencePrice)){
        throw new Error(`Lane C EXIT mark mismatch for ${normalized.entry.key}`);
      }
      entries.push(normalized.entry);outcomes.set(normalized.entry.key,normalized.outcome);
    }
  }
  entries.sort((a,b)=>a.entryTimestamp.localeCompare(b.entryTimestamp)||a.symbol.localeCompare(b.symbol)||a.key.localeCompare(b.key));
  bars.sort((a,b)=>a.timestamp.localeCompare(b.timestamp)||a.symbol.localeCompare(b.symbol));
  return Object.freeze({
    bars:Object.freeze(bars),entries:Object.freeze(entries),outcomes,evaluatedSessions:Object.freeze(evaluatedSessions),
    candidateKeySha256:sha256(entries.map(row=>row.key)),
  });
}

function executionPrice(referencePrice,direction,side,slippageBps){
  const rate=Number(slippageBps)/10_000;
  const sign=side==='ENTRY'?direction:-direction;
  return referencePrice*(1+sign*rate);
}

function positionEquityValue(position,markPrice){
  if(position.signalDirection===1)return position.quantity*markPrice;
  return position.collateralJpy+(position.entryExecutionPrice-markPrice)*position.quantity;
}

function stateValuation(state){
  let openPositionValue=0,grossExposure=0,unrealizedPnl=0;
  const exposures=[];
  for(const position of state.positions.values()){
    const mark=state.marks.get(position.symbol);
    if(!Number.isFinite(mark))throw new Error(`Lane C mark missing for open ${position.symbol}`);
    const exposure=Math.abs(position.quantity*mark);
    const pricePnl=position.signalDirection*(mark-position.entryExecutionPrice)*position.quantity;
    openPositionValue+=positionEquityValue(position,mark);
    grossExposure+=exposure;unrealizedPnl+=pricePnl;
    exposures.push({symbol:position.symbol,sector:position.sector,exposure});
  }
  return {openPositionValue,grossExposure,unrealizedPnl,equity:state.cash+openPositionValue,exposures};
}

function concentration(exposures,key){
  const total=exposures.reduce((sum,row)=>sum+row.exposure,0);
  if(total<=0)return {largestShare:null,hhi:null,shares:{}};
  const amounts=new Map();
  for(const row of exposures)amounts.set(row[key],(amounts.get(row[key])??0)+row.exposure);
  const shares=Object.fromEntries([...amounts].sort(([a],[b])=>a.localeCompare(b)).map(([name,value])=>[name,value/total]));
  const values=Object.values(shares);
  return {largestShare:Math.max(...values),hhi:values.reduce((sum,value)=>sum+value*value,0),shares};
}

function recordPoint(state,{timestamp,sessionDate}){
  const value=stateValuation(state),symbols=concentration(value.exposures,'symbol'),sectors=concentration(value.exposures,'sector');
  const row=Object.freeze({
    timestamp,sessionDate,
    cashJpy:round(state.cash),openPositionValueJpy:round(value.openPositionValue),portfolioEquityJpy:round(value.equity),
    realizedPnlJpy:round(state.realizedPnl),unrealizedPnlJpy:round(value.unrealizedPnl),
    grossExposureJpy:round(value.grossExposure),openPositionCount:state.positions.size,
    capitalUtilization:value.equity>0?round(value.grossExposure/value.equity):null,
    cashRatio:value.equity>0?round(state.cash/value.equity):null,
  });
  const concentrationRow=Object.freeze({
    timestamp,sessionDate,openPositionCount:state.positions.size,
    symbol:Object.freeze({largestShare:round(symbols.largestShare),hhi:round(symbols.hhi),shares:Object.freeze(Object.fromEntries(Object.entries(symbols.shares).map(([key,val])=>[key,round(val)])))}),
    sector:Object.freeze({largestShare:round(sectors.largestShare),hhi:round(sectors.hhi),shares:Object.freeze(Object.fromEntries(Object.entries(sectors.shares).map(([key,val])=>[key,round(val)])))}),
  });
  state.equityCurve.push(row);state.concentrationCurve.push(concentrationRow);
}

function rejectEntry(state,{entry,timestamp,reason,targetSlotBudget,equityBeforeEntry}){
  state.allocationDecisions.push(Object.freeze({
    timestamp,status:'REJECTED',reason,
    candidateSnapshot:entry,
    stateSnapshot:Object.freeze({
      portfolioEquityJpy:round(equityBeforeEntry),availableCashJpy:round(state.cash),
      targetSlotBudgetJpy:round(targetSlotBudget),openPositionCount:state.positions.size,
    }),
  }));
  state.rejectionCounts.set(reason,(state.rejectionCounts.get(reason)??0)+1);
}

function enterPosition(state,{entry,profile,timestamp,roundTripCostPct,slippageBps,exitsAtTimestamp}){
  const valuation=stateValuation(state),equityBeforeEntry=valuation.equity,targetSlotBudget=equityBeforeEntry/profile.maxPositions;
  if(state.positions.size>=profile.maxPositions){
    rejectEntry(state,{entry,timestamp,reason:'MAX_CONCURRENT_POSITIONS',targetSlotBudget,equityBeforeEntry});return;
  }
  if(state.positions.has(entry.symbol)){
    rejectEntry(state,{entry,timestamp,reason:'SYMBOL_ALREADY_OPEN',targetSlotBudget,equityBeforeEntry});return;
  }
  const entryExecutionPrice=executionPrice(entry.entryReferencePrice,entry.signalDirection,'ENTRY',slippageBps);
  const halfCostRate=Number(roundTripCostPct)/200;
  const cashRequiredPerShare=entryExecutionPrice+entry.entryReferencePrice*halfCostRate;
  const maxByBudget=Math.floor(targetSlotBudget/entryExecutionPrice/PHASE57_P25_LANE_C_POLICY.lotSize)*PHASE57_P25_LANE_C_POLICY.lotSize;
  const maxByCash=Math.floor(state.cash/cashRequiredPerShare/PHASE57_P25_LANE_C_POLICY.lotSize)*PHASE57_P25_LANE_C_POLICY.lotSize;
  const quantity=Math.min(maxByBudget,maxByCash);
  if(quantity<PHASE57_P25_LANE_C_POLICY.lotSize){
    const oneLotCashRequired=cashRequiredPerShare*PHASE57_P25_LANE_C_POLICY.lotSize;
    const reason=oneLotCashRequired>state.cash?'INSUFFICIENT_AVAILABLE_CASH_FOR_100_SHARES':'TARGET_SLOT_BUDGET_BELOW_100_SHARES';
    rejectEntry(state,{entry,timestamp,reason,targetSlotBudget,equityBeforeEntry});return;
  }
  const entryExecutionNotional=quantity*entryExecutionPrice;
  const referenceNotional=quantity*entry.entryReferencePrice;
  const entryCost=referenceNotional*halfCostRate;
  const entrySlippageCost=entry.signalDirection*(entryExecutionPrice-entry.entryReferencePrice)*quantity;
  const cashRequired=entryExecutionNotional+entryCost;
  if(cashRequired>state.cash+1e-8)throw new Error(`Lane C cash invariant failed for ${entry.key}`);
  state.cash-=cashRequired;state.realizedPnl-=entryCost;state.transactionCosts+=entryCost;
  state.slippageCosts+=entrySlippageCost;state.turnoverNotional+=entryExecutionNotional;
  const position=Object.freeze({
    ...entry,quantity,entryExecutionPrice,referenceNotional,entryCostJpy:entryCost,
    entrySlippageCostJpy:entrySlippageCost,collateralJpy:entryExecutionNotional,
  });
  state.positions.set(entry.symbol,position);state.openByKey.set(entry.key,entry.symbol);
  state.maxConcurrentPositions=Math.max(state.maxConcurrentPositions,state.positions.size);
  const recycled=state.completedExitCount>0;
  if(recycled)state.capitalRecyclingCount+=1;
  if(exitsAtTimestamp>0)state.sameTimestampCapitalRecyclingCount+=1;
  state.allocationDecisions.push(Object.freeze({
    timestamp,status:'ACCEPTED',reason:'DETERMINISTIC_TIME_SYMBOL_ORDER',candidateSnapshot:entry,
    stateSnapshot:Object.freeze({
      portfolioEquityJpy:round(equityBeforeEntry),availableCashBeforeJpy:round(state.cash+cashRequired),
      targetSlotBudgetJpy:round(targetSlotBudget),actualPurchaseAmountJpy:round(cashRequired),
      entryNotionalJpy:round(entryExecutionNotional),entryCostJpy:round(entryCost),quantity,
      openPositionCountAfter:state.positions.size,recycledCapitalAvailable:recycled,
      sameTimestampExitCashReleased:exitsAtTimestamp>0,
    }),
  }));
}

function exitPosition(state,{key,outcome,timestamp,roundTripCostPct,slippageBps}){
  const symbol=state.openByKey.get(key);
  if(!symbol)return false;
  const position=state.positions.get(symbol);
  const exitExecutionPrice=executionPrice(outcome.exitReferencePrice,position.signalDirection,'EXIT',slippageBps);
  const halfCostRate=Number(roundTripCostPct)/200;
  const exitCost=position.referenceNotional*halfCostRate;
  const grossPnl=position.signalDirection*(exitExecutionPrice-position.entryExecutionPrice)*position.quantity;
  const referenceGrossPnl=position.signalDirection*(outcome.exitReferencePrice-position.entryReferencePrice)*position.quantity;
  const exitSlippageCost=position.signalDirection*(outcome.exitReferencePrice-exitExecutionPrice)*position.quantity;
  const cashRelease=position.signalDirection===1
    ?exitExecutionPrice*position.quantity-exitCost
    :position.collateralJpy+grossPnl-exitCost;
  state.cash+=cashRelease;state.realizedPnl+=grossPnl-exitCost;state.transactionCosts+=exitCost;
  state.slippageCosts+=exitSlippageCost;
  state.turnoverNotional+=exitExecutionPrice*position.quantity;
  const realizedPnl=grossPnl-position.entryCostJpy-exitCost;
  state.closedTrades.push(Object.freeze({
    key,symbol,sector:position.sector,signalDirection:position.signalDirection,
    entryTimestamp:position.entryTimestamp,exitTimestamp:timestamp,quantity:position.quantity,
    entryReferencePrice:position.entryReferencePrice,exitReferencePrice:outcome.exitReferencePrice,
    entryExecutionPrice:round(position.entryExecutionPrice),exitExecutionPrice:round(exitExecutionPrice),
    entryNotionalJpy:round(position.collateralJpy),cashReleasedJpy:round(cashRelease),
    referenceGrossPnlJpy:round(referenceGrossPnl),executionGrossPnlJpy:round(grossPnl),
    transactionCostsJpy:round(position.entryCostJpy+exitCost),slippageCostJpy:round(position.entrySlippageCostJpy+exitSlippageCost),
    realizedPnlJpy:round(realizedPnl),
    holdingMinutes:(Date.parse(timestamp)-Date.parse(position.entryTimestamp))/60_000,
    exitReason:outcome.exitReason,sourceManagementMode:outcome.sourceManagementMode,
  }));
  state.positions.delete(symbol);state.openByKey.delete(key);state.completedExitCount+=1;
  return true;
}

function standardDeviation(values){
  if(values.length<2)return null;
  const average=mean(values);
  return Math.sqrt(values.reduce((sum,value)=>sum+(value-average)**2,0)/(values.length-1));
}

function maximumDrawdown(curve,initialEquity){
  let peak=initialEquity,maxDrawdownPct=0,troughTimestamp=null,peakTimestamp=null,currentPeakTimestamp=null;
  for(const row of curve){
    if(row.portfolioEquityJpy>peak){peak=row.portfolioEquityJpy;currentPeakTimestamp=row.timestamp;}
    if(peak<=0)continue;
    const drawdown=(peak-row.portfolioEquityJpy)/peak*100;
    if(drawdown>maxDrawdownPct){maxDrawdownPct=drawdown;troughTimestamp=row.timestamp;peakTimestamp=currentPeakTimestamp;}
  }
  return {maxDrawdownPct,peakTimestamp,troughTimestamp};
}

function dailyRisk(curve,initialEquity){
  const closes=new Map();
  for(const row of curve)closes.set(row.sessionDate,row);
  let previous=initialEquity;
  const daily=[...closes].sort(([a],[b])=>a.localeCompare(b)).map(([sessionDate,row])=>{
    const returnDecimal=previous>0?row.portfolioEquityJpy/previous-1:0;previous=row.portfolioEquityJpy;
    return Object.freeze({sessionDate,equityJpy:row.portfolioEquityJpy,returnPct:returnDecimal*100,returnDecimal});
  });
  const returns=daily.map(row=>row.returnDecimal),deviation=standardDeviation(returns);
  const downside=Math.sqrt(mean(returns.map(value=>Math.min(0,value)**2))??0);
  const worst=daily.length?[...daily].sort((a,b)=>a.returnDecimal-b.returnDecimal||a.sessionDate.localeCompare(b.sessionDate))[0]:null;
  return {
    daily:Object.freeze(daily),
    annualizedVolatility:deviation===null?null:deviation*Math.sqrt(252),
    sharpe:deviation&&deviation>0?(mean(returns)/deviation)*Math.sqrt(252):null,
    annualizedDownsideRisk:returns.length?downside*Math.sqrt(252):null,
    sortino:downside>0?(mean(returns)*252)/(downside*Math.sqrt(252)):null,
    worstDailyPeriod:worst?Object.freeze({sessionDate:worst.sessionDate,returnPct:worst.returnPct}):null,
  };
}

function capitalEfficiency(curve,state,initialEquity){
  let minutes=0,weightedExposure=0,weightedUtilization=0,weightedCashRatio=0,idleMinutes=0;
  for(let index=0;index<curve.length-1;index+=1){
    const row=curve[index],next=curve[index+1];
    if(row.sessionDate!==next.sessionDate)continue;
    const duration=(Date.parse(next.timestamp)-Date.parse(row.timestamp))/60_000;
    if(!Number.isFinite(duration)||duration<=0)continue;
    minutes+=duration;weightedExposure+=row.grossExposureJpy*duration;
    weightedUtilization+=(row.capitalUtilization??0)*duration;weightedCashRatio+=(row.cashRatio??0)*duration;
    if(row.openPositionCount===0)idleMinutes+=duration;
  }
  const averageEquity=mean(curve.map(row=>row.portfolioEquityJpy))??initialEquity;
  return {
    observedMarketMinutes:minutes,
    averageDeployedCapitalJpy:minutes?weightedExposure/minutes:0,
    averageCapitalUtilization:minutes?weightedUtilization/minutes:0,
    averageCashRatio:minutes?weightedCashRatio/minutes:1,
    idleCashDurationMinutes:idleMinutes,
    turnover:averageEquity>0?state.turnoverNotional/averageEquity:null,
    grossTurnoverNotionalJpy:state.turnoverNotional,
    capitalRecyclingCount:state.capitalRecyclingCount,
    sameTimestampCapitalRecyclingCount:state.sameTimestampCapitalRecyclingCount,
  };
}

function summarizeSimulation({state,profile,normalized,initialEquity,managementMode,universeVariant,roundTripCostPct,slippageBps}){
  const curve=state.equityCurve,finalValue=curve.length?curve[curve.length-1].portfolioEquityJpy:initialEquity;
  const drawdown=maximumDrawdown(curve,initialEquity),risk=dailyRisk(curve,initialEquity),efficiency=capitalEfficiency(curve,state,initialEquity);
  const tradePnls=state.closedTrades.map(row=>row.realizedPnlJpy),grossProfit=tradePnls.filter(value=>value>0).reduce((sum,value)=>sum+value,0),grossLoss=-tradePnls.filter(value=>value<0).reduce((sum,value)=>sum+value,0);
  const firstDate=normalized.evaluatedSessions[0],lastDate=normalized.evaluatedSessions.at(-1);
  const elapsedYears=firstDate&&lastDate?(Date.parse(`${lastDate}T00:00:00Z`)-Date.parse(`${firstDate}T00:00:00Z`))/(365.25*24*60*60*1000):0;
  const maxSymbolShare=Math.max(0,...state.concentrationCurve.map(row=>row.symbol.largestShare??0));
  const maxSectorShare=Math.max(0,...state.concentrationCurve.map(row=>row.sector.largestShare??0));
  return Object.freeze({
    phase:'57.p25.lane-c.portfolio-capital-allocation',status:'LANE_C_EVENT_TIME_PORTFOLIO_SIMULATED',
    profile:Object.freeze({...profile}),managementMode,universeVariant,
    input:Object.freeze({
      evaluatedSessionCount:normalized.evaluatedSessions.length,candidateEntryCount:normalized.entries.length,
      candidateKeySha256:normalized.candidateKeySha256,roundTripCostPct,slippageBps,
    }),
    return:Object.freeze({
      initialEquityJpy:round(initialEquity),finalEquityJpy:round(finalValue),totalReturnPct:round((finalValue/initialEquity-1)*100),
      cagrPct:elapsedYears>=1&&finalValue>0?round((Math.pow(finalValue/initialEquity,1/elapsedYears)-1)*100):null,
      cagrEligible:elapsedYears>=1,realizedPnlJpy:round(state.realizedPnl),unrealizedPnlJpy:0,
    }),
    costs:Object.freeze({
      roundTripCostPct,slippageBps,totalTransactionCostsJpy:round(state.transactionCosts),
      totalAdverseSlippageJpy:round(state.slippageCosts),
    }),
    risk:Object.freeze({
      maxDrawdownPct:round(drawdown.maxDrawdownPct),maxDrawdownPeakTimestamp:drawdown.peakTimestamp,maxDrawdownTroughTimestamp:drawdown.troughTimestamp,
      annualizedVolatilityPct:round(risk.annualizedVolatility===null?null:risk.annualizedVolatility*100),
      sharpe:round(risk.sharpe),annualizedDownsideRiskPct:round(risk.annualizedDownsideRisk===null?null:risk.annualizedDownsideRisk*100),
      sortino:round(risk.sortino),worstDailyPeriod:risk.worstDailyPeriod,
    }),
    trade:Object.freeze({
      candidates:normalized.entries.length,accepted:state.closedTrades.length,rejected:normalized.entries.length-state.closedTrades.length,
      winRate:tradePnls.length?round(tradePnls.filter(value=>value>0).length/tradePnls.length):null,
      averagePnlJpy:round(mean(tradePnls)),profitFactor:grossLoss>0?round(grossProfit/grossLoss):(grossProfit>0?Infinity:null),
      averageHoldingMinutes:round(mean(state.closedTrades.map(row=>row.holdingMinutes))),
      rejectionCounts:Object.freeze(Object.fromEntries([...state.rejectionCounts].sort(([a],[b])=>a.localeCompare(b)))),
    }),
    capitalEfficiency:Object.freeze(Object.fromEntries(Object.entries(efficiency).map(([key,value])=>[key,round(value)]))),
    concentration:Object.freeze({
      configuredMaximumConcurrentPositions:profile.maxPositions,observedMaximumConcurrentPositions:state.maxConcurrentPositions,
      maximumSymbolShare:round(maxSymbolShare),maximumSectorShare:round(maxSectorShare),sectorConstraintApplied:false,
    }),
    equityCurve:Object.freeze(curve),dailyEquityCurve:risk.daily,concentrationCurve:Object.freeze(state.concentrationCurve),
    allocationDecisions:Object.freeze(state.allocationDecisions),closedTrades:Object.freeze(state.closedTrades),
    methodology:Object.freeze({
      eventTimeOnly:true,priceUpdateBeforeExitBeforeEntry:true,availableCashConstrainsPurchase:true,
      unrealizedPnlInEquityButNotCash:true,hundredShareLot:true,fullyCashCollateralizedShorts:true,
      shortSaleProceedsReusable:false,confidenceRankingApplied:false,simultaneousEntryOrder:'TIMESTAMP_THEN_SYMBOL',
      allocatorCanSeeFutureExit:false,sectorConstraintApplied:false,winnerSelectionAllowed:false,
      signalEdgeChanged:false,managementEdgeChanged:false,freshHoldoutConsumed:false,
    }),
    safety:PHASE57_P25_LANE_C_SAFETY,
  });
}

export function simulateLaneCPortfolio({
  sessions=[],profile=PHASE57_P25_LANE_C_ALLOCATION_PROFILES[0],initialEquity=PHASE57_P25_LANE_C_POLICY.initialEquityJpy,
  managementMode='FIXED_HORIZON',universeVariant='DYNAMIC_50',roundTripCostPct=PHASE57_P25_LANE_C_POLICY.fixedRoundTripCostPct,
  slippageBps=PHASE57_P25_LANE_C_POLICY.baselineSlippageBps,
}={}){
  assertSafety();
  if(!finite(initialEquity)||Number(initialEquity)<=0)throw new Error('Lane C initialEquity must be positive');
  if(!profile||!Number.isInteger(Number(profile.maxPositions))||Number(profile.maxPositions)<1)throw new Error('Lane C causal profile requires a positive maxPositions');
  if(!finite(roundTripCostPct)||Number(roundTripCostPct)<0)throw new Error('Lane C roundTripCostPct must be non-negative');
  if(!finite(slippageBps)||Number(slippageBps)<0)throw new Error('Lane C slippageBps must be non-negative');
  const normalized=normalizeSessions(sessions,String(managementMode));
  const events=new Map();
  const eventAt=(timestamp,sessionDate)=>{
    if(!events.has(timestamp))events.set(timestamp,{timestamp,sessionDate,marks:[],exits:[],entries:[]});
    const event=events.get(timestamp);
    if(event.sessionDate!==sessionDate)throw new Error(`Lane C timestamp spans multiple sessions: ${timestamp}`);
    return event;
  };
  for(const bar of normalized.bars)eventAt(bar.timestamp,bar.sessionDate).marks.push(bar);
  for(const entry of normalized.entries){
    eventAt(entry.entryTimestamp,entry.sessionDate).entries.push(entry.key);
    const outcome=normalized.outcomes.get(entry.key);eventAt(outcome.exitTimestamp,entry.sessionDate).exits.push(entry.key);
  }
  const entriesByKey=new Map(normalized.entries.map(entry=>[entry.key,entry]));
  const state={
    cash:Number(initialEquity),realizedPnl:0,positions:new Map(),openByKey:new Map(),marks:new Map(),
    completedExitCount:0,capitalRecyclingCount:0,sameTimestampCapitalRecyclingCount:0,maxConcurrentPositions:0,
    transactionCosts:0,slippageCosts:0,turnoverNotional:0,equityCurve:[],concentrationCurve:[],allocationDecisions:[],closedTrades:[],rejectionCounts:new Map(),
  };
  for(const event of [...events.values()].sort((a,b)=>a.timestamp.localeCompare(b.timestamp))){
    for(const bar of event.marks.sort((a,b)=>a.symbol.localeCompare(b.symbol)))state.marks.set(bar.symbol,bar.close);
    let exitsAtTimestamp=0;
    for(const key of event.exits.sort((a,b)=>a.localeCompare(b))){
      const outcome=normalized.outcomes.get(key);
      if(exitPosition(state,{key,outcome,timestamp:event.timestamp,roundTripCostPct:Number(roundTripCostPct),slippageBps:Number(slippageBps)}))exitsAtTimestamp+=1;
    }
    for(const key of event.entries.sort((a,b)=>{
      const left=entriesByKey.get(a),right=entriesByKey.get(b);return left.symbol.localeCompare(right.symbol)||left.key.localeCompare(right.key);
    })){
      enterPosition(state,{entry:entriesByKey.get(key),profile,timestamp:event.timestamp,roundTripCostPct:Number(roundTripCostPct),slippageBps:Number(slippageBps),exitsAtTimestamp});
    }
    recordPoint(state,{timestamp:event.timestamp,sessionDate:event.sessionDate});
  }
  if(state.positions.size||state.openByKey.size)throw new Error('Lane C ended with unresolved open positions');
  const accountingDifference=state.cash-(Number(initialEquity)+state.realizedPnl);
  if(Math.abs(accountingDifference)>1e-6)throw new Error(`Lane C accounting invariant failed: ${accountingDifference}`);
  return summarizeSimulation({
    state,profile:Object.freeze({...profile,maxPositions:Number(profile.maxPositions)}),normalized,initialEquity:Number(initialEquity),
    managementMode:String(managementMode),universeVariant:String(universeVariant),roundTripCostPct:Number(roundTripCostPct),slippageBps:Number(slippageBps),
  });
}

export function buildP252FixedPortfolioSessions({sessionPackets=[],universeVariant='DYNAMIC_50'}={}){
  if(!VARIANTS.includes(universeVariant))throw new Error(`unknown Lane C universe variant: ${universeVariant}`);
  const sessions=[];
  for(const packet of [...(Array.isArray(sessionPackets)?sessionPackets:[])].sort((a,b)=>String(a?.sessionDate??'').localeCompare(String(b?.sessionDate??'')))){
    const sessionDate=String(packet?.sessionDate??packet?.universeRecord?.sessionDate??'');
    const universe=packet?.universeRecord;
    if(universe?.ready!==true||String(universe?.sessionDate??'')!==sessionDate)throw new Error(`Lane C requires ready frozen universe for ${sessionDate||'UNKNOWN'}`);
    const members=universe?.variants?.[universeVariant];
    if(!Array.isArray(members))throw new Error(`Lane C ${universeVariant} membership missing for ${sessionDate}`);
    const membership=new Set(members.map(value=>normalizeSymbol(value)));
    const resolved=packet?.outcomes?.resolvedTrades??packet?.resolvedTrades??[];
    const trades=resolved.filter(row=>membership.has(normalizeSymbol(row?.symbol)));
    const sessionBarsBySymbol=packet?.sessionBarsBySymbol??packet?.sessionInput?.sessionBarsBySymbol;
    if(!sessionBarsBySymbol||typeof sessionBarsBySymbol!=='object')throw new Error(`Lane C session bars missing for ${sessionDate}`);
    sessions.push(Object.freeze({
      sessionDate,trades:Object.freeze(trades.slice()),sessionBarsBySymbol,
      sourceProvenance:packet?.sourceProvenance??packet?.sessionInput?.sourceProvenance??null,
    }));
  }
  return Object.freeze(sessions);
}

export function buildCurrentExistingReference({sessions=[],initialEquity=PHASE57_P25_LANE_C_POLICY.initialEquityJpy}={}){
  assertSafety();
  if(!finite(initialEquity)||Number(initialEquity)<=0)throw new Error('Lane C Current reference initialEquity must be positive');
  const ordered=[...(Array.isArray(sessions)?sessions:[])].sort((a,b)=>String(a?.sessionDate??'').localeCompare(String(b?.sessionDate??'')));
  let equity=Number(initialEquity),peak=equity,maxDrawdownPct=0;
  const curve=[];
  for(const session of ordered){
    const rows=(Array.isArray(session?.trades)?session.trades:[]).filter(row=>finite(row?.netReturnPct)).map(row=>Number(row.netReturnPct));
    const returnPct=mean(rows)??0;equity*=1+returnPct/100;peak=Math.max(peak,equity);
    if(peak>0)maxDrawdownPct=Math.max(maxDrawdownPct,(peak-equity)/peak*100);
    curve.push(Object.freeze({sessionDate:String(session.sessionDate),returnPct:round(returnPct),normalizedEquity:round(equity/Number(initialEquity))}));
  }
  return Object.freeze({
    id:'CURRENT_EXISTING',label:'Current / Existing Baseline',status:'REFERENCE_ONLY_NOT_CAUSAL_PORTFOLIO',
    eligibleForCapitalAllocationWinnerSelection:false,comparableWithEventDrivenProfiles:false,max10Equivalent:null,
    sourceMetric:'P25_SESSION_EQUAL_WEIGHT_PORTFOLIO',
    referenceMetrics:Object.freeze({initialEquityJpy:Number(initialEquity),illustrativeFinalEquityJpy:round(equity),totalReturnPct:round((equity/Number(initialEquity)-1)*100),maxDrawdownPct:round(maxDrawdownPct)}),
    sessionCurve:Object.freeze(curve),
    limitations:Object.freeze({cashLedger:false,hundredShareLot:false,eventTimeCapitalLock:false,causalEntryAllocation:false,portfolioMtm5m:false}),
    methodology:Object.freeze({referenceOnly:true,notUsedToChooseWinner:true,causalCurrentRuleInvented:false}),
    audit:PHASE57_P25_LANE_C_CURRENT_BASELINE_AUDIT,safety:PHASE57_P25_LANE_C_SAFETY,
  });
}

export function compareLaneCAllocationProfiles({
  sessions=[],profiles=PHASE57_P25_LANE_C_ALLOCATION_PROFILES,initialEquity=PHASE57_P25_LANE_C_POLICY.initialEquityJpy,
  managementMode='FIXED_HORIZON',universeVariant='DYNAMIC_50',roundTripCostPct=PHASE57_P25_LANE_C_POLICY.fixedRoundTripCostPct,
  slippageBps=PHASE57_P25_LANE_C_POLICY.baselineSlippageBps,
}={}){
  const selected=Array.isArray(profiles)?profiles:[];
  if(!selected.length)throw new Error('Lane C comparison requires at least one causal allocation profile');
  const current=buildCurrentExistingReference({sessions,initialEquity});
  const results={CURRENT_EXISTING:current};let candidateKeySha256=null,candidateEntryCount=null;
  for(const profile of selected){
    if(results[profile.id])throw new Error(`duplicate Lane C profile id: ${profile.id}`);
    const result=simulateLaneCPortfolio({sessions,profile,initialEquity,managementMode,universeVariant,roundTripCostPct,slippageBps});
    if(candidateKeySha256===null){candidateKeySha256=result.input.candidateKeySha256;candidateEntryCount=result.input.candidateEntryCount;}
    if(result.input.candidateKeySha256!==candidateKeySha256||result.input.candidateEntryCount!==candidateEntryCount)throw new Error('Lane C paired candidate identity changed across allocation profiles');
    results[profile.id]=result;
  }
  return Object.freeze({
    phase:'57.p25.lane-c.portfolio-capital-allocation',status:'LANE_C_PAIRED_ALLOCATION_PROFILES_SIMULATED',
    managementMode:String(managementMode),universeVariant:String(universeVariant),initialEquityJpy:Number(initialEquity),
    resultOrder:Object.freeze(['CURRENT_EXISTING',...selected.map(profile=>profile.id)]),results:Object.freeze(results),
    pairedAudit:Object.freeze({sameFrozenEntryCandidates:true,candidateEntryCount,candidateKeySha256,sameManagementResult:true,onlyCausalAllocationProfileChanged:true}),
    interpretation:Object.freeze({
      signalEdgeMeasuredHere:false,managementEdgeMeasuredHere:false,capitalAllocationEdgeMeasuredWithinCausalProfiles:true,
      managementTimesAllocationRequiresFixedVsDynamicMatrix:true,currentExistingReferenceExcludedFromCausalWinnerComparison:true,
      winnerSelectionAllowed:false,prospectiveSampleSufficient:false,
    }),
    safety:PHASE57_P25_LANE_C_SAFETY,
  });
}

export default {
  simulateLaneCPortfolio,compareLaneCAllocationProfiles,buildP252FixedPortfolioSessions,buildCurrentExistingReference,
  PHASE57_P25_LANE_C_SAFETY,PHASE57_P25_LANE_C_POLICY,PHASE57_P25_LANE_C_ALLOCATION_PROFILES,
  PHASE57_P25_LANE_C_CURRENT_BASELINE_AUDIT,PHASE57_P25_LANE_C_ALLOCATOR_VISIBLE_FIELDS,
};
