export const PHASE57_P25_3A_SAFETY=Object.freeze({
  phase:'57.p25.3a.session-integrity-ledger',
  mode:'READ_ONLY_PROSPECTIVE_SESSION_INTEGRITY',
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

export const PHASE57_P25_3A_POLICY=Object.freeze({
  routineCapturePhase:'57.p25.2j.routine-nonrss-5m-source-cli',
  wholeFrozenTargetUnionRequiredForReady:true,
  partialValidBarsConfirmTradingSession:true,
  zeroValidBarsDoNotProveMarketClosed:true,
  unresolvedSessionsCountInConservativePace:true,
  verifiedNonTradingSessionRequiresExternalEvidenceId:true,
  providerOutageMayNotBeRelabeledAsHolidayFromOutcome:true,
  dailyMarketSpeedRequired:false,
  boardOrTickUsed:false,
  microstructureUsed:false,
  outerOosPerformanceMayChangeSessionClassification:false,
});

const SAFETY_FALSE_KEYS=Object.freeze([
  'executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed',
  'liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed',
  'transmitted','freshHoldoutConsumed',
]);

function normalizeDate(value){
  const text=String(value??'').trim();
  return /^\d{4}-\d{2}-\d{2}$/.test(text)?text:null;
}
function finiteInteger(value){return Number.isInteger(Number(value))&&Number(value)>=0?Number(value):null;}
function unwrap(entry){
  if(entry?.artifact&&typeof entry.artifact==='object')return {artifact:entry.artifact,artifactSha256:entry.artifactSha256??null,artifactPath:entry.artifactPath??null};
  return {artifact:entry,artifactSha256:entry?.artifactSha256??null,artifactPath:entry?.artifactPath??null};
}
function assertCaptureSafety(artifact,sessionDate){
  const safety=artifact?.safety??{};
  for(const key of SAFETY_FALSE_KEYS){
    if(safety[key]!==false)throw new Error(`P25.3A ${sessionDate}: capture safety ${key} must be false`);
  }
  if(artifact?.methodology?.routineDailyMarketSpeedRequired!==false)throw new Error(`P25.3A ${sessionDate}: routineDailyMarketSpeedRequired must be false`);
  if(artifact?.methodology?.boardOrTickUsed!==false)throw new Error(`P25.3A ${sessionDate}: boardOrTickUsed must be false`);
}
function evidenceMap(rows){
  const map=new Map();
  for(const row of Array.isArray(rows)?rows:[]){
    const sessionDate=normalizeDate(row?.sessionDate);
    const evidenceId=String(row?.evidenceId??'').trim();
    if(!sessionDate)throw new Error('P25.3A verified non-trading session requires YYYY-MM-DD sessionDate');
    if(!evidenceId)throw new Error(`P25.3A verified non-trading session ${sessionDate} requires evidenceId`);
    if(map.has(sessionDate))throw new Error(`duplicate verified non-trading classification: ${sessionDate}`);
    map.set(sessionDate,Object.freeze({sessionDate,evidenceId,source:String(row?.source??'EXTERNAL_VERIFIED_CALENDAR')}));
  }
  return map;
}

/**
 * Classify routine post-close capture attempts without confusing a total provider
 * outage with a market holiday. A ready whole-union capture proves a trading day;
 * a blocked capture with at least one valid symbol also proves a trading day and
 * therefore counts as a zero-Entry operational day. Zero valid symbols remain
 * unresolved unless an independent, pre-outcome calendar evidence ID verifies a
 * non-trading date.
 *
 * Until unresolved dates are independently classified, the recommended Days-to-400
 * denominator is conservative: unresolved weekdays remain counted. This can make
 * the pace look slower, never artificially faster.
 */
export function buildP253SessionIntegrityLedger({
  captureArtifacts=[],
  verifiedNonTradingSessions=[],
}={}){
  const verifiedClosed=evidenceMap(verifiedNonTradingSessions);
  const seen=new Set(),rows=[];
  for(const raw of Array.isArray(captureArtifacts)?captureArtifacts:[]){
    const {artifact,artifactSha256,artifactPath}=unwrap(raw);
    if(!artifact||typeof artifact!=='object')throw new TypeError('P25.3A capture artifact must be an object');
    if(artifact.phase!==PHASE57_P25_3A_POLICY.routineCapturePhase)throw new Error(`P25.3A unexpected capture phase: ${artifact.phase??'MISSING'}`);
    const collection=artifact.collection??{};
    const expectedDates=Array.isArray(artifact.expectedSessionDates)?artifact.expectedSessionDates.map(normalizeDate).filter(Boolean):[];
    const sessionDate=normalizeDate(collection.sessionDate)??(expectedDates.length===1?expectedDates[0]:null);
    if(!sessionDate)throw new Error('P25.3A capture artifact has no unambiguous sessionDate');
    if(seen.has(sessionDate))throw new Error(`duplicate P25.3A capture artifact session: ${sessionDate}`);
    seen.add(sessionDate);
    assertCaptureSafety(artifact,sessionDate);

    const target=finiteInteger(collection.targetSymbolCount),collected=finiteInteger(collection.collectedSymbolCount),failed=finiteInteger(collection.failedSymbolCount);
    if(target===null||target<1||collected===null||failed===null)throw new Error(`P25.3A ${sessionDate}: invalid collection counts`);
    if(collected>target||failed>target||collected+failed!==target)throw new Error(`P25.3A ${sessionDate}: collection counts do not reconcile`);
    const sourceCount=collection.sourceBySymbol&&typeof collection.sourceBySymbol==='object'?Object.keys(collection.sourceBySymbol).length:0;
    if(sourceCount!==collected)throw new Error(`P25.3A ${sessionDate}: sourceBySymbol count does not match collectedSymbolCount`);
    const ready=collection.ready===true;
    if(ready&&(collected!==target||failed!==0))throw new Error(`P25.3A ${sessionDate}: ready capture is not whole-union complete`);
    if(ready&&(!Array.isArray(artifact.sessions)||artifact.sessions.length!==1))throw new Error(`P25.3A ${sessionDate}: ready capture must contain one session bundle`);
    if(!ready&&Array.isArray(artifact.sessions)&&artifact.sessions.length)throw new Error(`P25.3A ${sessionDate}: blocked capture may not expose a ready session bundle`);

    const closedEvidence=verifiedClosed.get(sessionDate)??null;
    if(closedEvidence&&collected>0)throw new Error(`P25.3A ${sessionDate}: verified non-trading date conflicts with valid 5m bars`);
    let classification;
    if(closedEvidence){
      classification='VERIFIED_NON_TRADING_SESSION';
    }else if(ready){
      classification='READY_CONFIRMED_TRADING_SESSION';
    }else if(collected>0){
      classification='BLOCKED_CONFIRMED_TRADING_SESSION';
    }else{
      classification='UNRESOLVED_MARKET_CLOSED_OR_PROVIDER_FAILURE';
    }
    rows.push(Object.freeze({
      sessionDate,
      classification,
      captureReady:ready,
      targetSymbolCount:target,
      collectedSymbolCount:collected,
      failedSymbolCount:failed,
      captureStatus:String(artifact.status??'UNKNOWN'),
      artifactSha256:artifactSha256?String(artifactSha256):null,
      artifactPath:artifactPath?String(artifactPath):null,
      verifiedNonTradingEvidence:closedEvidence,
    }));
  }
  rows.sort((a,b)=>a.sessionDate.localeCompare(b.sessionDate));

  const readyTrading=rows.filter(x=>x.classification==='READY_CONFIRMED_TRADING_SESSION').map(x=>x.sessionDate);
  const blockedTrading=rows.filter(x=>x.classification==='BLOCKED_CONFIRMED_TRADING_SESSION').map(x=>x.sessionDate);
  const unresolved=rows.filter(x=>x.classification==='UNRESOLVED_MARKET_CLOSED_OR_PROVIDER_FAILURE').map(x=>x.sessionDate);
  const nonTrading=rows.filter(x=>x.classification==='VERIFIED_NON_TRADING_SESSION').map(x=>x.sessionDate);
  const confirmedTrading=[...readyTrading,...blockedTrading].sort();
  const conservativeExpected=[...confirmedTrading,...unresolved].sort();

  return Object.freeze({
    phase:'57.p25.3a.session-integrity-ledger',
    status:unresolved.length?'SESSION_INTEGRITY_HAS_UNRESOLVED_DATES':'SESSION_INTEGRITY_CLASSIFIED',
    captureArtifactCount:rows.length,
    readyTradingSessionCount:readyTrading.length,
    blockedConfirmedTradingSessionCount:blockedTrading.length,
    unresolvedSessionCount:unresolved.length,
    verifiedNonTradingSessionCount:nonTrading.length,
    rows:Object.freeze(rows),
    readyTradingSessionDates:Object.freeze(readyTrading),
    blockedConfirmedTradingSessionDates:Object.freeze(blockedTrading),
    confirmedTradingSessionDates:Object.freeze(confirmedTrading),
    unresolvedSessionDates:Object.freeze(unresolved),
    verifiedNonTradingSessionDates:Object.freeze(nonTrading),
    optimisticConfirmedTradingSessionDates:Object.freeze(confirmedTrading),
    conservativeExpectedTradingSessionDates:Object.freeze(conservativeExpected),
    recommendedExpectedSessionDatesForP252H:Object.freeze(conservativeExpected),
    methodology:Object.freeze({
      readyWholeUnionCaptureConfirmsTradingDay:true,
      partialValidBarsConfirmTradingDay:true,
      blockedConfirmedTradingDayCountsAsZeroEntryOperationalDay:true,
      zeroValidBarsNeverAutomaticallyMeansHoliday:true,
      unresolvedDateIncludedInConservativeDaysTo400:true,
      verifiedNonTradingDateRequiresIndependentEvidenceId:true,
      outerOosPerformanceUsedForClassification:false,
      dailyMarketSpeedRequired:false,
      boardOrTickUsed:false,
      microstructureUsed:false,
      freshHoldoutConsumed:false,
    }),
    safety:PHASE57_P25_3A_SAFETY,
  });
}

export default {buildP253SessionIntegrityLedger,PHASE57_P25_3A_POLICY,PHASE57_P25_3A_SAFETY};
