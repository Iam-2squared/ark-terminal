import fs from 'node:fs';

const specificationUrl=new URL('../research/phase57-selector-minimal-hybrid-phase-a.json',import.meta.url);
export const PHASE57_SELECTOR_MINIMAL_HYBRID_PHASE_A=Object.freeze(JSON.parse(fs.readFileSync(specificationUrl,'utf8')));
export const PHASE57_SELECTOR_MINIMAL_HYBRID_SAFETY=Object.freeze(PHASE57_SELECTOR_MINIMAL_HYBRID_PHASE_A.safety);

const ISO_DATE=/^\d{4}-\d{2}-\d{2}$/;
const SHA256=/^[a-f0-9]{64}$/i;
const finite=value=>value!==null&&value!==undefined&&value!==''&&Number.isFinite(Number(value));
const sourceValidationRegistry=JSON.parse(fs.readFileSync(new URL('../research/phase57-selector-source-validation-only-registry.json',import.meta.url),'utf8'));
if(sourceValidationRegistry.policy!=='APPEND_ONLY_PERMANENT_EXCLUSION_FROM_ALL_RESEARCH_SPLITS'
  ||!Array.isArray(sourceValidationRegistry.sessions)||!sourceValidationRegistry.sessions.length
  ||sourceValidationRegistry.sessions.some(row=>!ISO_DATE.test(String(row?.sessionDate??''))||row.classification!=='SOURCE_VALIDATION_ONLY')){
  throw new Error('SOURCE_VALIDATION_ONLY exclusion registry is invalid');
}
const sourceValidationSessions=new Set(sourceValidationRegistry.sessions.map(row=>row.sessionDate));
if(sourceValidationSessions.size!==sourceValidationRegistry.sessions.length)throw new Error('SOURCE_VALIDATION_ONLY exclusion registry has duplicate sessions');

function assertSafety(safety,label){
  for(const [key,value] of Object.entries(PHASE57_SELECTOR_MINIMAL_HYBRID_SAFETY)){
    if(value===false&&safety?.[key]!==false)throw new Error(`${label} safety ${key} must remain false`);
  }
}

function sessionDateOf(session,index){
  const value=String(session?.sessionDate??'');
  if(!ISO_DATE.test(value))throw new Error(`sessions[${index}] requires YYYY-MM-DD sessionDate`);
  return value;
}

function overlaps(leftStart,leftEnd,rightStart,rightEnd){
  return leftStart<=rightEnd&&leftEnd>=rightStart;
}

function assertUnconsumedDataset(manifest,sessions){
  const dates=sessions.map(sessionDateOf);
  const first=dates[0];
  const last=dates.at(-1);
  const ancestry=new Set([
    String(manifest.datasetId??''),
    ...(Array.isArray(manifest.parentDatasetIds)?manifest.parentDatasetIds.map(String):[]),
  ]);
  for(const consumed of PHASE57_SELECTOR_MINIMAL_HYBRID_PHASE_A.consumedEvidence.datasets){
    if(ancestry.has(consumed.datasetId))throw new Error(`consumed dataset identity is forbidden: ${consumed.datasetId}`);
    if(overlaps(first,last,consumed.firstSession,consumed.lastSession)){
      const offending=dates.find(date=>date>=consumed.firstSession&&date<=consumed.lastSession);
      if(offending)throw new Error(`session ${offending} overlaps consumed hypothesis-generation evidence`);
    }
  }
}

function assertAtomicSessions(sessions){
  let previous='';
  const seen=new Set();
  for(const [index,session] of sessions.entries()){
    const date=sessionDateOf(session,index);
    if(sourceValidationSessions.has(date))throw new Error(`session ${date} is permanently SOURCE_VALIDATION_ONLY and cannot enter any research split`);
    if(seen.has(date)||previous&&date<=previous)throw new Error('sessions must be unique and strictly chronological');
    seen.add(date);previous=date;
    if(!Array.isArray(session.decisionCutoffs)||!session.decisionCutoffs.length)throw new Error(`${date} requires decisionCutoffs[]`);
    let prior=-Infinity;
    for(const cutoff of session.decisionCutoffs){
      const timestamp=Date.parse(String(cutoff??''));
      if(!Number.isFinite(timestamp)||timestamp<=prior)throw new Error(`${date} decisionCutoffs must be valid and strictly chronological`);
      prior=timestamp;
    }
    if(session.crossSectionAtomic!==true)throw new Error(`${date} must declare crossSectionAtomic=true`);
  }
}

export function planPhase57MinimalHybridFrozen120Split(sessions){
  if(!Array.isArray(sessions))throw new TypeError('sessions must be an array');
  assertAtomicSessions(sessions);
  if(sessions.length!==122)throw new Error('Fresh-120 allocation requires 122 chronological sessions including two purge sessions');
  const dates=list=>Object.freeze(list.map(session=>session.sessionDate));
  return Object.freeze({
    development:dates(sessions.slice(0,72)),
    purgeDevelopmentValidation:dates(sessions.slice(72,73)),
    validation:dates(sessions.slice(73,97)),
    purgeValidationOos:dates(sessions.slice(97,98)),
    untouchedOos:dates(sessions.slice(98,122)),
    usableSessionCount:120,purgeSessionCount:2,
    allocationPolicy:'FRESH_120_PLUS_TWO_ONE_SESSION_PURGES',
    atomicUnit:'COMPLETE_5M_CROSS_SECTION',outerGrouping:'TRADING_SESSION',
    validationReleased:false,untouchedOosReleased:false,
  });
}

export function planPhase57MinimalHybridSessionSplit(sessions,{allocationPolicy=null}={}){
  if(!Array.isArray(sessions))throw new TypeError('sessions must be an array');
  assertAtomicSessions(sessions);
  if(allocationPolicy==='FRESH_120_PLUS_TWO_ONE_SESSION_PURGES')return planPhase57MinimalHybridFrozen120Split(sessions);
  const cfg=PHASE57_SELECTOR_MINIMAL_HYBRID_PHASE_A.newDataset;
  if(sessions.length<cfg.minimumTradingSessions)throw new Error(`new Minimal Hybrid dataset requires at least ${cfg.minimumTradingSessions} sessions`);
  const purge=PHASE57_SELECTOR_MINIMAL_HYBRID_PHASE_A.causality.purgeSessionsAtEachBoundary;
  const developmentBoundary=Math.floor(sessions.length*cfg.developmentFraction);
  const validationBoundary=developmentBoundary+Math.floor(sessions.length*cfg.validationFraction);
  const dates=list=>Object.freeze(list.map(session=>session.sessionDate));
  const result={
    development:dates(sessions.slice(0,developmentBoundary-purge)),
    purgeDevelopmentValidation:dates(sessions.slice(developmentBoundary-purge,developmentBoundary)),
    validation:dates(sessions.slice(developmentBoundary,validationBoundary-purge)),
    purgeValidationOos:dates(sessions.slice(validationBoundary-purge,validationBoundary)),
    untouchedOos:dates(sessions.slice(validationBoundary)),
    atomicUnit:'COMPLETE_5M_CROSS_SECTION',
    outerGrouping:'TRADING_SESSION',
    validationReleased:false,
    untouchedOosReleased:false,
  };
  if(!result.development.length||!result.validation.length||!result.untouchedOos.length)throw new Error('session split leaves an empty fold');
  return Object.freeze(result);
}

export function validatePhase57MinimalHybridDatasetAdmission(dataset){
  if(!dataset||typeof dataset!=='object')throw new TypeError('dataset must be an object');
  const manifest=dataset.manifest;
  if(!manifest||typeof manifest!=='object')throw new TypeError('dataset.manifest is required');
  if(!Array.isArray(dataset.sessions))throw new TypeError('dataset.sessions must be an array');
  if(!String(manifest.datasetId??'').trim())throw new Error('manifest.datasetId is required');
  if(!SHA256.test(String(manifest.rawSourceSha256??'')))throw new Error('manifest.rawSourceSha256 must be a SHA-256 digest');
  if(manifest.providerEntitlementVerified!==true)throw new Error('provider entitlement must be explicitly verified');
  if(manifest.previouslyUsedForSelectorOutcomeInspection!==false)throw new Error('dataset must be unused for prior Selector outcome inspection');
  if(Number(manifest.intervalMinutes)!==PHASE57_SELECTOR_MINIMAL_HYBRID_PHASE_A.newDataset.requiredResearchIntervalMinutes){
    throw new Error('research dataset interval must be 5 minutes');
  }
  if(manifest.barTimestampMeaning!=='BAR_OPEN'||manifest.availableAtRule!=='BAR_OPEN_PLUS_INTERVAL'){
    throw new Error('dataset must declare BAR_OPEN timestamps and causal availability at bar close');
  }
  if(manifest.noTradeMinutePolicy!=='MISSING_NEVER_FABRICATE')throw new Error('no-trade minutes must remain missing');
  if(manifest.missingMicrostructurePolicy!=='UNKNOWN_WITH_AVAILABILITY_MASK')throw new Error('unavailable microstructure must remain UNKNOWN with a mask');
  if(manifest.microstructureZeroFilled===true)throw new Error('microstructure zero fill is forbidden');
  if(manifest.completeCrossSectionAtomic!==true)throw new Error('complete cross-sections must be atomic');
  if(!['POINT_IN_TIME','SURVIVORSHIP_LIMITED'].includes(manifest.universeStatus))throw new Error('universeStatus must be POINT_IN_TIME or SURVIVORSHIP_LIMITED');
  if(manifest.strongHistoricalClaimAllowed===true&&manifest.universeStatus!=='POINT_IN_TIME'){
    throw new Error('strong historical claims require a point-in-time universe');
  }
  assertSafety(manifest.safety,'dataset manifest');
  assertAtomicSessions(dataset.sessions);
  assertUnconsumedDataset(manifest,dataset.sessions);
  const split=planPhase57MinimalHybridSessionSplit(dataset.sessions,{allocationPolicy:manifest.datasetAllocationPolicy??null});
  return Object.freeze({
    status:'MINIMAL_HYBRID_NEW_DATASET_ADMITTED_DEVELOPMENT_ONLY',
    datasetId:manifest.datasetId,
    sessionCount:dataset.sessions.length,
    firstSession:dataset.sessions[0].sessionDate,
    lastSession:dataset.sessions.at(-1).sessionDate,
    universeStatus:manifest.universeStatus,
    strongHistoricalClaimAllowed:manifest.universeStatus==='POINT_IN_TIME'&&manifest.strongHistoricalClaimAllowed===true,
    developmentReleaseAllowed:true,
    validationReleaseAllowed:false,
    untouchedOosReleaseAllowed:false,
    split,
    safety:PHASE57_SELECTOR_MINIMAL_HYBRID_SAFETY,
  });
}

export default {
  validatePhase57MinimalHybridDatasetAdmission,
  planPhase57MinimalHybridSessionSplit,
  planPhase57MinimalHybridFrozen120Split,
  PHASE57_SELECTOR_MINIMAL_HYBRID_PHASE_A,
  PHASE57_SELECTOR_MINIMAL_HYBRID_SAFETY,
};
