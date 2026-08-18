import {evaluateP252PrecommittedProspectiveComparison} from './phase57-p25-2d-precommitted-prospective-comparison.js';

export const PHASE57_P25_2H_SAFETY=Object.freeze({
  phase:'57.p25.2h.multisession-evidence-accumulator',
  mode:'READ_ONLY_PRECOMMITTED_MULTISESSION_ACCUMULATION',
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

export const PHASE57_P25_2H_VARIANTS=Object.freeze(['FIXED_5','OLD_FIXED_30','DYNAMIC_30','DYNAMIC_40','DYNAMIC_50']);

function sessionDateOf(packet){return String(packet?.sessionDate??packet?.universeRecord?.sessionDate??packet?.ledger?.sessionDate??'').trim();}
function normalizeExpected(values){
  const out=[...new Set((Array.isArray(values)?values:[]).map(String).filter(x=>/^\d{4}-\d{2}-\d{2}$/.test(x)))].sort();
  return out;
}
function tradeKey(row){return `${row?.sessionDate??''}|${row?.entryTimestamp??row?.featureCutoff??''}|${String(row?.symbol??'').toUpperCase()}`;}

function operationalFrequency({packetsBySession,expectedSessions,variant,target=400}){
  const counts=[];
  let cumulative=0,observedDays=null,total=0;
  for(let index=0;index<expectedSessions.length;index+=1){
    const sessionDate=expectedSessions[index],packet=packetsBySession.get(sessionDate);
    const entries=(packet?.ledger?.frozenTrades??[]).filter(row=>Array.isArray(row?.variantMemberships)&&row.variantMemberships.includes(variant)).length;
    total+=entries;cumulative+=entries;
    counts.push(Object.freeze({sessionDate,validFrozenEntries:entries,cumulativeValidFrozenEntries:cumulative,packetReady:Boolean(packet)}));
    if(observedDays===null&&cumulative>=target)observedDays=index+1;
  }
  const pace=expectedSessions.length?total/expectedSessions.length:0;
  return Object.freeze({
    target,
    validFrozenEntries:total,
    tradingSessions:expectedSessions.length,
    validFrozenEntriesPerTradingSession:pace,
    observedDaysToTarget:observedDays,
    paceEstimatedDaysToTarget:pace>0?target/pace:null,
    byTradingSession:Object.freeze(counts),
  });
}

/**
 * Aggregate daily P25.2 packets without selecting a Dynamic N from the results.
 * Performance metrics use the common ready-session comparison. Operational pace
 * separately counts every predeclared expected trading session, including a day
 * with no ready packet as zero Entries, so capture failures cannot make days-to-400
 * look artificially faster.
 */
export function accumulateP252MultiSessionEvidence({
  sessionPackets=[],
  expectedSessionDates=[],
}={}){
  const packets=Array.isArray(sessionPackets)?sessionPackets:[];
  const bySession=new Map(),universeRecords=[],resolvedTrades=[];
  const denominators=Object.fromEntries(PHASE57_P25_2H_VARIANTS.map(v=>[v,0]));
  const unresolvedBySession={},blockedBySession={};
  const seenTrades=new Set();

  for(const packet of packets){
    const sessionDate=sessionDateOf(packet);
    if(!/^\d{4}-\d{2}-\d{2}$/.test(sessionDate))throw new Error('P25.2H packet sessionDate must be YYYY-MM-DD');
    if(bySession.has(sessionDate))throw new Error(`duplicate P25.2 session packet: ${sessionDate}`);
    if(packet?.universeRecord?.ready!==true||String(packet.universeRecord.sessionDate??'')!==sessionDate)throw new Error(`ready frozen universe missing or mismatched for ${sessionDate}`);
    if(String(packet?.ledger?.sessionDate??sessionDate)!==sessionDate)throw new Error(`ledger session mismatch for ${sessionDate}`);
    bySession.set(sessionDate,packet);
    universeRecords.push(packet.universeRecord);
    for(const variant of PHASE57_P25_2H_VARIANTS){
      const value=Number(packet?.ledger?.eligibleDecisionCountsByVariant?.[variant]??0);
      if(!Number.isFinite(value)||value<0)throw new Error(`invalid ${variant} eligible decision denominator for ${sessionDate}`);
      denominators[variant]+=value;
    }
    const resolved=packet?.outcomes?.resolvedTrades??packet?.resolvedTrades??[];
    for(const row of resolved){
      if(String(row?.sessionDate??'')!==sessionDate)throw new Error(`resolved trade session mismatch for ${sessionDate}`);
      const key=tradeKey(row);if(seenTrades.has(key))throw new Error(`duplicate resolved trade across session packets: ${key}`);seenTrades.add(key);resolvedTrades.push(row);
    }
    const unresolved=packet?.outcomes?.unresolvedTrades??packet?.unresolvedTrades??[];
    unresolvedBySession[sessionDate]=Object.freeze(unresolved.slice());
    blockedBySession[sessionDate]=Object.freeze((packet?.blockedDecisions??packet?.replay?.blockedDecisions??[]).slice());
  }

  const packetSessions=[...bySession.keys()].sort();
  const expected=normalizeExpected(expectedSessionDates);
  const operationalSessions=expected.length?expected:packetSessions;
  for(const sessionDate of packetSessions){
    if(expected.length&&!expected.includes(sessionDate))throw new Error(`session packet ${sessionDate} is outside predeclared expectedSessionDates`);
  }
  const missingExpectedSessions=operationalSessions.filter(date=>!bySession.has(date));
  const comparison=evaluateP252PrecommittedProspectiveComparison({
    universeRecords,
    frozenTrades:resolvedTrades,
    eligibleDecisionCountsByVariant:denominators,
  });
  const operationalTradeFrequency=Object.freeze(Object.fromEntries(PHASE57_P25_2H_VARIANTS.map(variant=>[
    variant,operationalFrequency({packetsBySession:bySession,expectedSessions:operationalSessions,variant,target:400}),
  ])));

  return Object.freeze({
    phase:'57.p25.2h.multisession-evidence-accumulator',
    status:'P25_2_MULTISESSION_EVIDENCE_ACCUMULATED',
    readySessionCount:packetSessions.length,
    readySessions:Object.freeze(packetSessions),
    expectedTradingSessionCount:operationalSessions.length,
    expectedTradingSessions:Object.freeze(operationalSessions),
    missingExpectedSessionCount:missingExpectedSessions.length,
    missingExpectedSessions:Object.freeze(missingExpectedSessions),
    resolvedTradeCount:resolvedTrades.length,
    aggregateEligibleDecisionCountsByVariant:Object.freeze(denominators),
    operationalTradeFrequency,
    unresolvedBySession:Object.freeze(unresolvedBySession),
    blockedBySession:Object.freeze(blockedBySession),
    comparison,
    methodology:Object.freeze({
      allFiveVariantsRetained:true,
      currentOuterOosDoesNotSelectDynamicN:true,
      performanceComparisonUsesReadyCommonSessions:true,
      operationalPaceCountsMissingExpectedSessionsAsZeroEntries:true,
      badAndUnresolvedEvidencePreserved:true,
      entryThresholdRelaxed:false,
      postHocWinnerFiltering:false,
      freshHoldoutConsumed:false,
    }),
    safety:PHASE57_P25_2H_SAFETY,
  });
}

export default {accumulateP252MultiSessionEvidence,PHASE57_P25_2H_VARIANTS,PHASE57_P25_2H_SAFETY};
