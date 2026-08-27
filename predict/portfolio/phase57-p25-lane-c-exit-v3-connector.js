import {createHash} from 'node:crypto';
import {
  compareLaneCAllocationProfiles,
  PHASE57_P25_LANE_C_ALLOCATION_PROFILES,
} from './phase57-p25-lane-c-portfolio-simulator.js';
import {
  P25_EXIT_V3_DUAL_GATE_POLICY_SHA256,
} from '../daytrade/phase57-p25-exit-v3-dual-gate.js';

export const PHASE57_P25_LANE_C_EXIT_V3_CONNECTOR_SAFETY=Object.freeze({
  phase:'57.p25.lane-c.exit-v3-connector',
  mode:'READ_ONLY_DIAGNOSTIC_PORTFOLIO_RESEARCH',
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

export const PHASE57_P25_LANE_C_EXIT_V3_CONNECTOR_POLICY=Object.freeze({
  exactDynamic50Only:true,
  sameFrozenEntryAsFixed:true,
  fixedBaselineUntouched:true,
  managementMode:'EXIT_V3',
  legacy27Role:'DIAGNOSTIC_PIPELINE_VALIDATION_ONLY',
  formalOosEvidence:false,
  promotionEligible:false,
  winnerSelectionAllowed:false,
  resultBasedRetuning:false,
  allocatorCanInspectV3Outcome:false,
  expectedExitV3PolicySha256:P25_EXIT_V3_DUAL_GATE_POLICY_SHA256,
});

const FALSE_KEYS=Object.freeze([
  'executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed',
  'liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed',
  'transmitted','freshHoldoutConsumed',
]);
const iso=value=>{
  const ms=Date.parse(String(value??''));
  if(!Number.isFinite(ms))throw new Error(`Lane C EXIT v3 invalid timestamp: ${value??'MISSING'}`);
  return new Date(ms).toISOString();
};
const symbolOf=value=>String(value??'').trim().toUpperCase();
const keyOf=({sessionDate,entryTimestamp,symbol})=>`${sessionDate}|${iso(entryTimestamp)}|${symbolOf(symbol)}`;
const sha256=value=>createHash('sha256').update(JSON.stringify(value)).digest('hex');

function assertSafety(){
  for(const key of FALSE_KEYS){
    if(PHASE57_P25_LANE_C_EXIT_V3_CONNECTOR_SAFETY[key]!==false){
      throw new Error(`Lane C EXIT v3 connector safety ${key} must remain false`);
    }
  }
}

function unwrapReplay(value){
  const replay=value?.result?.pairs?value.result:value;
  if(!Array.isArray(replay?.pairs))throw new Error('Lane C EXIT v3 connector requires replay pairs');
  if(replay?.classification?.diagnosticOnly!==true)throw new Error('Lane C EXIT v3 connector accepts legacy diagnostic replay only in this connector');
  if(replay?.classification?.formalOos!==false||replay?.classification?.promotionEligible!==false){
    throw new Error('Lane C EXIT v3 connector classification guard violation');
  }
  if(replay?.methodology?.exactDynamic50Only!==true||replay?.methodology?.sameFrozenEntryAsFixed!==true){
    throw new Error('Lane C EXIT v3 connector Frozen Entry identity guard violation');
  }
  if(replay?.methodology?.resultBasedRetuning!==false||replay?.methodology?.freshHoldoutConsumed!==false){
    throw new Error('Lane C EXIT v3 connector methodology guard violation');
  }
  return replay;
}

function normalizeSessionPacketMap(sessionPackets=[]){
  const map=new Map();
  for(const packet of sessionPackets){
    const sessionDate=String(packet?.sessionDate??packet?.universeRecord?.sessionDate??'');
    if(!/^\d{4}-\d{2}-\d{2}$/.test(sessionDate))throw new Error('Lane C EXIT v3 session packet requires YYYY-MM-DD sessionDate');
    if(map.has(sessionDate))throw new Error(`Lane C EXIT v3 duplicate session packet: ${sessionDate}`);
    const sessionBarsBySymbol=packet?.sessionBarsBySymbol??{};
    map.set(sessionDate,Object.freeze({sessionDate,sessionBarsBySymbol}));
  }
  return map;
}

function buildTrade(pair){
  const fixed=pair?.fixed??{};
  const v3=pair?.v3??{};
  const sessionDate=String(pair?.sessionDate??fixed?.sessionDate??'');
  const symbol=symbolOf(pair?.symbol??fixed?.symbol);
  const entryTimestamp=iso(fixed?.entryTimestamp??fixed?.featureCutoff);
  const expectedKey=keyOf({sessionDate,entryTimestamp,symbol});
  if(String(pair?.key??'')!==expectedKey)throw new Error(`Lane C EXIT v3 pair key mismatch: ${pair?.key??'MISSING'}`);
  if(!(pair?.variantMemberships??[]).includes('DYNAMIC_50'))throw new Error(`Lane C EXIT v3 non-DYNAMIC_50 pair: ${expectedKey}`);
  if(fixed?.entryAccepted!==true||fixed?.frozenBeforeOutcome!==true||fixed?.currentOutcomeUsed!==false){
    throw new Error(`Lane C EXIT v3 pair is not a frozen outcome-free Entry: ${expectedKey}`);
  }
  if(v3?.policySha256!==P25_EXIT_V3_DUAL_GATE_POLICY_SHA256){
    throw new Error(`Lane C EXIT v3 policy hash mismatch: ${expectedKey}`);
  }
  const exitTimestamp=iso(v3?.exitTimestamp);
  if(exitTimestamp<=entryTimestamp)throw new Error(`Lane C EXIT v3 exit must follow Entry: ${expectedKey}`);
  const entryPrice=Number(fixed?.entryPrice);
  const exitPrice=Number(v3?.exitPrice);
  const signalDirection=Number(fixed?.signalDirection);
  const netReturnPct=Number(v3?.netReturnPct);
  if(!Number.isFinite(entryPrice)||entryPrice<=0||!Number.isFinite(exitPrice)||exitPrice<=0){
    throw new Error(`Lane C EXIT v3 resolved price missing: ${expectedKey}`);
  }
  if(![-1,1].includes(signalDirection))throw new Error(`Lane C EXIT v3 direction must be -1 or 1: ${expectedKey}`);
  if(!Number.isFinite(netReturnPct))throw new Error(`Lane C EXIT v3 net return missing: ${expectedKey}`);
  return Object.freeze({
    entryAccepted:true,
    frozenBeforeOutcome:true,
    currentOutcomeUsed:false,
    sessionDate,
    symbol,
    sector:fixed?.sector??'UNKNOWN',
    signalDirection,
    entryTimestamp,
    entryPrice,
    exitTimestamp,
    exitPrice,
    exitReason:String(v3?.exitReason??'EXIT_V3'),
    netReturnPct,
  });
}

export function buildP25ExitV3PortfolioSessions({replay,sessionPackets=[]}={}){
  assertSafety();
  const source=unwrapReplay(replay);
  const packets=normalizeSessionPacketMap(sessionPackets);
  const grouped=new Map();
  for(const pair of source.pairs){
    const trade=buildTrade(pair);
    if(!packets.has(trade.sessionDate))throw new Error(`Lane C EXIT v3 bars missing for session ${trade.sessionDate}`);
    if(!grouped.has(trade.sessionDate))grouped.set(trade.sessionDate,[]);
    grouped.get(trade.sessionDate).push(trade);
  }
  const sessions=[...grouped.entries()].sort(([a],[b])=>a.localeCompare(b)).map(([sessionDate,trades])=>Object.freeze({
    sessionDate,
    trades:Object.freeze([...trades].sort((a,b)=>a.entryTimestamp.localeCompare(b.entryTimestamp)||a.symbol.localeCompare(b.symbol))),
    sessionBarsBySymbol:packets.get(sessionDate).sessionBarsBySymbol,
  }));
  const keys=sessions.flatMap(session=>session.trades.map(trade=>keyOf(trade)));
  if(new Set(keys).size!==keys.length)throw new Error('Lane C EXIT v3 duplicate Frozen Entry key');
  return Object.freeze({
    sessions:Object.freeze(sessions),
    audit:Object.freeze({
      managementMode:'EXIT_V3',
      exactDynamic50Only:true,
      pairedCount:keys.length,
      candidateKeySha256:sha256(keys),
      sourceLineageManifestHeadSha256:source?.lineageManifestHeadSha256??null,
      sourcePolicySha256:source?.policySha256??null,
      diagnosticOnly:true,
      formalOos:false,
      promotionEligible:false,
      winnerSelectionAllowed:false,
      freshHoldoutConsumed:false,
    }),
    methodology:PHASE57_P25_LANE_C_EXIT_V3_CONNECTOR_POLICY,
    safety:PHASE57_P25_LANE_C_EXIT_V3_CONNECTOR_SAFETY,
  });
}

export function compareP25ExitV3LaneCAllocations({
  replay,
  sessionPackets=[],
  profiles=PHASE57_P25_LANE_C_ALLOCATION_PROFILES,
  initialEquity,
  roundTripCostPct,
  slippageBps,
}={}){
  const connected=buildP25ExitV3PortfolioSessions({replay,sessionPackets});
  const comparison=compareLaneCAllocationProfiles({
    sessions:connected.sessions,
    profiles,
    universeVariant:'DYNAMIC_50',
    managementMode:'EXIT_V3',
    ...(initialEquity!==undefined?{initialEquity}:{}),
    ...(roundTripCostPct!==undefined?{roundTripCostPct}:{}),
    ...(slippageBps!==undefined?{slippageBps}:{}),
  });
  return Object.freeze({
    phase:'57.p25.lane-c.exit-v3-allocation-matrix',
    status:'P25_EXIT_V3_LANE_C_DIAGNOSTIC_MATRIX_READY',
    connectorAudit:connected.audit,
    comparison,
    interpretation:Object.freeze({
      edgeLabel:'MANAGEMENT_X_CAPITAL_ALLOCATION',
      legacy27Role:'DIAGNOSTIC_PIPELINE_VALIDATION_ONLY',
      winnerSelectionAllowed:false,
      formalOosEvidence:false,
      promotionEligible:false,
      freshHoldoutConsumed:false,
    }),
    safety:PHASE57_P25_LANE_C_EXIT_V3_CONNECTOR_SAFETY,
  });
}

export default {
  PHASE57_P25_LANE_C_EXIT_V3_CONNECTOR_SAFETY,
  PHASE57_P25_LANE_C_EXIT_V3_CONNECTOR_POLICY,
  buildP25ExitV3PortfolioSessions,
  compareP25ExitV3LaneCAllocations,
};
