import {
  PHASE57_P25_LANE_C_ALLOCATION_PROFILES,
  PHASE57_P25_LANE_C_POLICY,
  PHASE57_P25_LANE_C_SAFETY,
  simulateLaneCPortfolio,
} from './phase57-p25-lane-c-portfolio-simulator.js';
import {PHASE57_CAR1_SAFETY} from './phase57-car1-sizing-research.js';
import {buildCar1PairedBudgetAttribution} from './phase57-car1-budget-attribution.js';

const LOT=PHASE57_P25_LANE_C_POLICY.lotSize;
const FALSE_KEYS=Object.freeze([
  'executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed',
  'liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted',
]);
const round=(value,digits=6)=>Number.isFinite(value)?Number(value.toFixed(digits)):value;
const mean=values=>values.length?values.reduce((sum,value)=>sum+value,0)/values.length:null;
const iso=value=>{
  const ms=Date.parse(String(value??''));
  if(!Number.isFinite(ms))throw new Error(`invalid CAR-1 replay timestamp: ${value??'MISSING'}`);
  return new Date(ms).toISOString();
};
const symbolOf=value=>{
  const symbol=String(value??'').trim().toUpperCase();
  if(!symbol)throw new Error('CAR-1 replay symbol required');
  return symbol;
};

function assertSafety(){
  for(const key of FALSE_KEYS){
    if(PHASE57_CAR1_SAFETY[key]!==false)throw new Error(`CAR-1 safety ${key} must remain false`);
    if(PHASE57_P25_LANE_C_SAFETY[key]!==false)throw new Error(`Lane C safety ${key} must remain false`);
  }
  if(PHASE57_CAR1_SAFETY.winnerSelectionAllowed!==false)throw new Error('CAR-1 winner selection must remain disabled');
}

function executionPrice(referencePrice,direction,side,slippageBps){
  const rate=Number(slippageBps)/10_000;
  const sign=side==='ENTRY'?direction:-direction;
  return referencePrice*(1+sign*rate);
}

function normalizeSessions(sessions,managementMode){
  const entries=[],bars=[],outcomes=new Map(),seenKeys=new Set(),seenSessions=new Set();
  for(const session of [...(Array.isArray(sessions)?sessions:[])].sort((a,b)=>String(a?.sessionDate??'').localeCompare(String(b?.sessionDate??'')))){
    const sessionDate=String(session?.sessionDate??'').trim();
    if(!/^\d{4}-\d{2}-\d{2}$/.test(sessionDate))throw new Error('CAR-1 replay sessionDate must be YYYY-MM-DD');
    if(seenSessions.has(sessionDate))throw new Error(`duplicate CAR-1 replay session: ${sessionDate}`);
    seenSessions.add(sessionDate);
    const source=session?.sessionBarsBySymbol instanceof Map?session.sessionBarsBySymbol:new Map(Object.entries(session?.sessionBarsBySymbol??{}));
    const lookups=new Map();
    for(const [rawSymbol,rows] of source){
      const raw=String(rawSymbol??'');
      const symbol=symbolOf(raw.includes('.')?raw:`${raw}.T`);
      const normalized=(Array.isArray(rows)?rows:[]).map(row=>{
        const timestamp=iso(row?.timestamp??row?.time),close=Number(row?.close);
        if(!Number.isFinite(close)||close<=0)throw new Error(`invalid CAR-1 replay close for ${symbol}`);
        return Object.freeze({sessionDate,symbol,timestamp,close});
      }).sort((a,b)=>a.timestamp.localeCompare(b.timestamp));
      if(new Set(normalized.map(row=>row.timestamp)).size!==normalized.length)throw new Error(`duplicate CAR-1 replay bars for ${symbol} ${sessionDate}`);
      lookups.set(symbol,new Map(normalized.map(row=>[row.timestamp,row.close])));
      bars.push(...normalized);
    }
    for(const row of Array.isArray(session?.trades)?session.trades:[]){
      if(row?.entryAccepted!==true||row?.frozenBeforeOutcome!==true||row?.currentOutcomeUsed!==false){
        throw new Error(`CAR-1 replay accepts only frozen outcome-free Entry identities (${sessionDate})`);
      }
      const symbol=symbolOf(row?.symbol),entryTimestamp=iso(row?.entryTimestamp??row?.featureCutoff),exitTimestamp=iso(row?.exitTimestamp);
      const entryReferencePrice=Number(row?.entryPrice),exitReferencePrice=Number(row?.exitPrice),signalDirection=Number(row?.signalDirection);
      if(exitTimestamp<=entryTimestamp)throw new Error(`CAR-1 replay exit must follow Entry for ${symbol}`);
      if(!Number.isFinite(entryReferencePrice)||entryReferencePrice<=0||!Number.isFinite(exitReferencePrice)||exitReferencePrice<=0)throw new Error(`CAR-1 replay prices required for ${symbol}`);
      if(![-1,1].includes(signalDirection))throw new Error(`CAR-1 replay direction must be -1 or 1 for ${symbol}`);
      const key=`${sessionDate}|${entryTimestamp}|${symbol}`;
      if(seenKeys.has(key))throw new Error(`duplicate CAR-1 replay Entry: ${key}`);
      seenKeys.add(key);
      const lookup=lookups.get(symbol);
      if(!lookup||!Number.isFinite(lookup.get(entryTimestamp))||!Number.isFinite(lookup.get(exitTimestamp)))throw new Error(`CAR-1 replay exact bars missing for ${key}`);
      const entryMark=lookup.get(entryTimestamp),exitMark=lookup.get(exitTimestamp);
      const same=(a,b)=>Math.abs(a-b)<=Math.max(1,Math.abs(a),Math.abs(b))*1e-9;
      if(!same(entryMark,entryReferencePrice)||!same(exitMark,exitReferencePrice))throw new Error(`CAR-1 replay reference mark mismatch for ${key}`);
      const entry=Object.freeze({
        key,sessionDate,symbol,sector:String(row?.sector??'UNKNOWN').trim().toUpperCase()||'UNKNOWN',
        signalDirection,entryTimestamp,entryReferencePrice,
      });
      entries.push(entry);
      outcomes.set(key,Object.freeze({
        key,exitTimestamp,exitReferencePrice,exitReason:String(row?.exitReason??managementMode),sourceManagementMode:String(managementMode),
      }));
    }
  }
  entries.sort((a,b)=>a.entryTimestamp.localeCompare(b.entryTimestamp)||a.symbol.localeCompare(b.symbol)||a.key.localeCompare(b.key));
  bars.sort((a,b)=>a.timestamp.localeCompare(b.timestamp)||a.symbol.localeCompare(b.symbol));
  return Object.freeze({entries:Object.freeze(entries),bars:Object.freeze(bars),outcomes});
}

function valuation(state){
  let openValue=0,grossExposure=0;
  const exposures=[];
  for(const position of state.positions.values()){
    const mark=state.marks.get(position.symbol);
    if(!Number.isFinite(mark))throw new Error(`CAR-1 replay mark missing for ${position.symbol}`);
    const exposure=Math.abs(position.quantity*mark);
    const value=position.signalDirection===1
      ?position.quantity*mark
      :position.collateralJpy+(position.entryExecutionPrice-mark)*position.quantity;
    openValue+=value;grossExposure+=exposure;exposures.push({symbol:position.symbol,sector:position.sector,exposure});
  }
  return {equity:state.cash+openValue,grossExposure,exposures};
}

function recordPoint(state,event){
  const value=valuation(state);
  const total=value.grossExposure;
  const shares=key=>{
    if(total<=0)return 0;
    const by=new Map();
    for(const row of value.exposures)by.set(row[key],(by.get(row[key])??0)+row.exposure);
    return Math.max(0,...[...by.values()].map(amount=>amount/total));
  };
  state.maxSymbolShare=Math.max(state.maxSymbolShare,shares('symbol'));
  state.maxSectorShare=Math.max(state.maxSectorShare,shares('sector'));
  state.equityCurve.push(Object.freeze({
    timestamp:event.timestamp,sessionDate:event.sessionDate,portfolioEquityJpy:round(value.equity),grossExposureJpy:round(value.grossExposure),
    capitalUtilization:value.equity>0?round(value.grossExposure/value.equity):null,openPositionCount:state.positions.size,
  }));
}

function reject(state,entry,reason,targetBudgetJpy,equityBeforeEntry){
  state.rejectionCounts.set(reason,(state.rejectionCounts.get(reason)??0)+1);
  state.allocationDecisions.push(Object.freeze({
    key:entry.key,status:'REJECTED',reason,targetBudgetJpy:round(targetBudgetJpy),portfolioEquityJpy:round(equityBeforeEntry),quantity:0,
  }));
}

function enter(state,{entry,targetBudgetJpy,maxPositions,roundTripCostPct,slippageBps}){
  const equityBeforeEntry=valuation(state).equity;
  if(state.positions.size>=maxPositions){reject(state,entry,'MAX_CONCURRENT_POSITIONS',targetBudgetJpy,equityBeforeEntry);return;}
  if(state.positions.has(entry.symbol)){reject(state,entry,'SYMBOL_ALREADY_OPEN',targetBudgetJpy,equityBeforeEntry);return;}
  const entryExecutionPrice=executionPrice(entry.entryReferencePrice,entry.signalDirection,'ENTRY',slippageBps);
  const halfCostRate=Number(roundTripCostPct)/200;
  const cashRequiredPerShare=entryExecutionPrice+entry.entryReferencePrice*halfCostRate;
  const maxByBudget=Math.floor(Number(targetBudgetJpy)/entryExecutionPrice/LOT)*LOT;
  const maxByCash=Math.floor(state.cash/cashRequiredPerShare/LOT)*LOT;
  const quantity=Math.min(maxByBudget,maxByCash);
  if(quantity<LOT){
    const oneLotCashRequired=cashRequiredPerShare*LOT;
    const reason=oneLotCashRequired>state.cash?'INSUFFICIENT_AVAILABLE_CASH_FOR_100_SHARES':'TARGET_SLOT_BUDGET_BELOW_100_SHARES';
    reject(state,entry,reason,targetBudgetJpy,equityBeforeEntry);return;
  }
  const entryExecutionNotional=quantity*entryExecutionPrice,referenceNotional=quantity*entry.entryReferencePrice;
  const entryCost=referenceNotional*halfCostRate,cashRequired=entryExecutionNotional+entryCost;
  const entrySlippageCost=entry.signalDirection*(entryExecutionPrice-entry.entryReferencePrice)*quantity;
  if(cashRequired>state.cash+1e-8)throw new Error(`CAR-1 replay cash invariant failed for ${entry.key}`);
  state.cash-=cashRequired;state.realizedPnl-=entryCost;state.transactionCosts+=entryCost;state.slippageCosts+=entrySlippageCost;state.turnoverNotional+=entryExecutionNotional;
  state.positions.set(entry.symbol,Object.freeze({...entry,quantity,entryExecutionPrice,referenceNotional,entryCostJpy:entryCost,entrySlippageCostJpy:entrySlippageCost,collateralJpy:entryExecutionNotional}));
  state.openByKey.set(entry.key,entry.symbol);state.maxConcurrentPositions=Math.max(state.maxConcurrentPositions,state.positions.size);
  state.allocationDecisions.push(Object.freeze({
    key:entry.key,status:'ACCEPTED',reason:'FROZEN_PRIORITY_COUNTERFACTUAL_SIZE',targetBudgetJpy:round(targetBudgetJpy),
    portfolioEquityJpy:round(equityBeforeEntry),quantity,entryNotionalJpy:round(entryExecutionNotional),entryCostJpy:round(entryCost),
  }));
}

function exit(state,{key,outcome,roundTripCostPct,slippageBps}){
  const symbol=state.openByKey.get(key);
  if(!symbol)return;
  const position=state.positions.get(symbol),exitExecutionPrice=executionPrice(outcome.exitReferencePrice,position.signalDirection,'EXIT',slippageBps);
  const halfCostRate=Number(roundTripCostPct)/200,exitCost=position.referenceNotional*halfCostRate;
  const grossPnl=position.signalDirection*(exitExecutionPrice-position.entryExecutionPrice)*position.quantity;
  const exitSlippageCost=position.signalDirection*(outcome.exitReferencePrice-exitExecutionPrice)*position.quantity;
  const cashRelease=position.signalDirection===1
    ?exitExecutionPrice*position.quantity-exitCost
    :position.collateralJpy+grossPnl-exitCost;
  state.cash+=cashRelease;state.realizedPnl+=grossPnl-exitCost;state.transactionCosts+=exitCost;state.slippageCosts+=exitSlippageCost;state.turnoverNotional+=exitExecutionPrice*position.quantity;
  const realizedPnl=grossPnl-position.entryCostJpy-exitCost;
  state.closedTrades.push(Object.freeze({key,symbol,quantity:position.quantity,realizedPnlJpy:round(realizedPnl)}));
  state.positions.delete(symbol);state.openByKey.delete(key);
}

function maximumDrawdown(curve,initialEquity){
  let peak=initialEquity,maxDrawdownPct=0;
  for(const row of curve){peak=Math.max(peak,row.portfolioEquityJpy);if(peak>0)maxDrawdownPct=Math.max(maxDrawdownPct,(peak-row.portfolioEquityJpy)/peak*100);}
  return maxDrawdownPct;
}

function averageUtilization(curve){
  let minutes=0,weighted=0;
  for(let index=0;index<curve.length-1;index+=1){
    const row=curve[index],next=curve[index+1];
    if(row.sessionDate!==next.sessionDate)continue;
    const duration=(Date.parse(next.timestamp)-Date.parse(row.timestamp))/60_000;
    if(!Number.isFinite(duration)||duration<=0)continue;
    minutes+=duration;weighted+=(row.capitalUtilization??0)*duration;
  }
  return minutes?weighted/minutes:0;
}

function replayWithBudgetMap({sessions,budgetByKey,maxPositions,initialEquity,managementMode,roundTripCostPct,slippageBps}){
  const normalized=normalizeSessions(sessions,managementMode),events=new Map(),entriesByKey=new Map(normalized.entries.map(row=>[row.key,row]));
  const eventAt=(timestamp,sessionDate)=>{
    if(!events.has(timestamp))events.set(timestamp,{timestamp,sessionDate,marks:[],entries:[],exits:[]});
    const event=events.get(timestamp);
    if(event.sessionDate!==sessionDate)throw new Error(`CAR-1 replay timestamp spans sessions: ${timestamp}`);
    return event;
  };
  for(const bar of normalized.bars)eventAt(bar.timestamp,bar.sessionDate).marks.push(bar);
  for(const entry of normalized.entries){
    eventAt(entry.entryTimestamp,entry.sessionDate).entries.push(entry.key);
    const outcome=normalized.outcomes.get(entry.key);eventAt(outcome.exitTimestamp,entry.sessionDate).exits.push(entry.key);
    if(!Number.isFinite(Number(budgetByKey.get(entry.key)))||Number(budgetByKey.get(entry.key))<=0)throw new Error(`CAR-1 replay target budget missing for ${entry.key}`);
  }
  const state={
    cash:Number(initialEquity),realizedPnl:0,positions:new Map(),openByKey:new Map(),marks:new Map(),transactionCosts:0,slippageCosts:0,turnoverNotional:0,
    equityCurve:[],allocationDecisions:[],closedTrades:[],rejectionCounts:new Map(),maxConcurrentPositions:0,maxSymbolShare:0,maxSectorShare:0,
  };
  for(const event of [...events.values()].sort((a,b)=>a.timestamp.localeCompare(b.timestamp))){
    for(const bar of event.marks.sort((a,b)=>a.symbol.localeCompare(b.symbol)))state.marks.set(bar.symbol,bar.close);
    for(const key of event.exits.sort((a,b)=>a.localeCompare(b)))exit(state,{key,outcome:normalized.outcomes.get(key),roundTripCostPct,slippageBps});
    for(const key of event.entries.sort((a,b)=>{
      const left=entriesByKey.get(a),right=entriesByKey.get(b);return left.symbol.localeCompare(right.symbol)||left.key.localeCompare(right.key);
    }))enter(state,{entry:entriesByKey.get(key),targetBudgetJpy:Number(budgetByKey.get(key)),maxPositions,roundTripCostPct,slippageBps});
    recordPoint(state,event);
  }
  if(state.positions.size||state.openByKey.size)throw new Error('CAR-1 replay ended with open positions');
  const accountingDifference=state.cash-(Number(initialEquity)+state.realizedPnl);
  if(Math.abs(accountingDifference)>1e-6)throw new Error(`CAR-1 replay accounting invariant failed: ${accountingDifference}`);
  const finalEquity=state.equityCurve.length?state.equityCurve.at(-1).portfolioEquityJpy:Number(initialEquity);
  const pnls=state.closedTrades.map(row=>row.realizedPnlJpy),grossProfit=pnls.filter(value=>value>0).reduce((sum,value)=>sum+value,0),grossLoss=-pnls.filter(value=>value<0).reduce((sum,value)=>sum+value,0);
  const averageEquity=mean(state.equityCurve.map(row=>row.portfolioEquityJpy))??Number(initialEquity);
  return Object.freeze({
    finalEquityJpy:round(finalEquity),totalReturnPct:round((finalEquity/Number(initialEquity)-1)*100),maxDrawdownPct:round(maximumDrawdown(state.equityCurve,Number(initialEquity))),
    acceptedTradeCount:state.closedTrades.length,rejectedTradeCount:normalized.entries.length-state.closedTrades.length,
    winRate:pnls.length?round(pnls.filter(value=>value>0).length/pnls.length):null,
    profitFactor:grossLoss>0?round(grossProfit/grossLoss):(grossProfit>0?Infinity:null),
    averageCapitalUtilization:round(averageUtilization(state.equityCurve)),
    turnover:averageEquity>0?round(state.turnoverNotional/averageEquity):null,
    totalTransactionCostsJpy:round(state.transactionCosts),totalAdverseSlippageJpy:round(state.slippageCosts),
    observedMaximumConcurrentPositions:state.maxConcurrentPositions,maximumSymbolShare:round(state.maxSymbolShare),maximumSectorShare:round(state.maxSectorShare),
    allocationDecisions:Object.freeze(state.allocationDecisions),closedTrades:Object.freeze(state.closedTrades),equityCurve:Object.freeze(state.equityCurve),
    rejectionCounts:Object.freeze(Object.fromEntries([...state.rejectionCounts].sort(([a],[b])=>a.localeCompare(b)))),
  });
}

function assertLegacyParity(baseline,control){
  const close=(a,b,tolerance=1e-4)=>Math.abs(Number(a)-Number(b))<=tolerance;
  if(!close(baseline.return.finalEquityJpy,control.finalEquityJpy)||!close(baseline.return.totalReturnPct,control.totalReturnPct,1e-6))throw new Error('CAR-1 legacy replay final-equity parity failed');
  if(!close(baseline.risk.maxDrawdownPct,control.maxDrawdownPct,1e-6))throw new Error('CAR-1 legacy replay MaxDD parity failed');
  if(baseline.trade.accepted!==control.acceptedTradeCount||baseline.trade.rejected!==control.rejectedTradeCount)throw new Error('CAR-1 legacy replay trade-cardinality parity failed');
  const baselineClosed=new Map(baseline.closedTrades.map(row=>[row.key,row]));
  if(baselineClosed.size!==control.closedTrades.length)throw new Error('CAR-1 legacy replay closed-trade parity failed');
  for(const row of control.closedTrades){
    const expected=baselineClosed.get(row.key);
    if(!expected||expected.quantity!==row.quantity||!close(expected.realizedPnlJpy,row.realizedPnlJpy,1e-4))throw new Error(`CAR-1 legacy replay trade parity failed for ${row.key}`);
  }
  return Object.freeze({
    passed:true,finalEquityDeltaJpy:round(control.finalEquityJpy-baseline.return.finalEquityJpy),
    maxDrawdownDeltaPct:round(control.maxDrawdownPct-baseline.risk.maxDrawdownPct),acceptedTradeDelta:control.acceptedTradeCount-baseline.trade.accepted,
  });
}

export function runCar1CounterfactualPortfolioAttribution({
  sessions=[],baselineProfile=PHASE57_P25_LANE_C_ALLOCATION_PROFILES[0],profileIds,
  initialEquity=PHASE57_P25_LANE_C_POLICY.initialEquityJpy,managementMode='FIXED_HORIZON',universeVariant='DYNAMIC_50',
  roundTripCostPct=PHASE57_P25_LANE_C_POLICY.fixedRoundTripCostPct,slippageBps=PHASE57_P25_LANE_C_POLICY.baselineSlippageBps,
}={}){
  assertSafety();
  const baseline=simulateLaneCPortfolio({sessions,profile:baselineProfile,initialEquity,managementMode,universeVariant,roundTripCostPct,slippageBps});
  const attribution=buildCar1PairedBudgetAttribution({sessions,baselineProfile,profileIds,initialEquity,managementMode,universeVariant,roundTripCostPct,slippageBps});
  const legacyBudgetByKey=new Map(baseline.allocationDecisions.map(row=>[row.candidateSnapshot.key,Number(row.stateSnapshot.targetSlotBudgetJpy)]));
  const control=replayWithBudgetMap({sessions,budgetByKey:legacyBudgetByKey,maxPositions:Number(baselineProfile.maxPositions),initialEquity:Number(initialEquity),managementMode:String(managementMode),roundTripCostPct:Number(roundTripCostPct),slippageBps:Number(slippageBps)});
  const parity=assertLegacyParity(baseline,control);
  const results={};
  for(const profileId of attribution.profileOrder){
    const budgetByKey=new Map(attribution.profiles[profileId].rows.map(row=>[row.key,row.targetBudgetJpy]));
    results[profileId]=replayWithBudgetMap({sessions,budgetByKey,maxPositions:Number(baselineProfile.maxPositions),initialEquity:Number(initialEquity),managementMode:String(managementMode),roundTripCostPct:Number(roundTripCostPct),slippageBps:Number(slippageBps)});
  }
  return Object.freeze({
    phase:'57.car1.capital-allocation-sizing',status:'CAR1_PARITY_GATED_COUNTERFACTUAL_PORTFOLIO_ATTRIBUTION',
    baselineProfile:Object.freeze({...baseline.profile}),profileOrder:attribution.profileOrder,
    baseline:Object.freeze({
      totalReturnPct:baseline.return.totalReturnPct,profitFactor:baseline.trade.profitFactor,maxDrawdownPct:baseline.risk.maxDrawdownPct,
      acceptedTradeCount:baseline.trade.accepted,averageCapitalUtilization:baseline.capitalEfficiency.averageCapitalUtilization,
    }),
    legacyReplayParity:parity,results:Object.freeze(results),budgetAttribution:attribution,
    pairedAudit:Object.freeze({
      candidateKeySha256:baseline.input.candidateKeySha256,candidateEntryCount:baseline.input.candidateEntryCount,
      sameFrozenEntryCandidates:true,sameEntryPrice:true,sameDirection:true,sameFrozenExit:true,sameCostAssumption:true,sameCandidatePriority:true,
      baselineBudgetEnvelopeAnchored:true,challengerSelfCompoundingSizing:false,futureOutcomeUsedBySizer:false,
    }),
    interpretation:Object.freeze({
      researchOnly:true,positionSizingAttributionOnly:true,rankingChanged:false,entryChanged:false,exitChanged:false,
      winnerSelectionAllowed:false,parameterSearchAllowed:false,promotionEligible:false,formalOos:false,
      note:'Challenger budgets are anchored to the causal Lane C baseline envelope to isolate sizing. Self-compounding challenger sizing is a separate later test.',
    }),
    safety:Object.freeze({car1:PHASE57_CAR1_SAFETY,laneC:PHASE57_P25_LANE_C_SAFETY}),
  });
}

export default {runCar1CounterfactualPortfolioAttribution};
