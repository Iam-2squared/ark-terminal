import {createHash} from 'node:crypto';
import {
  PHASE57_SELECTOR_MINIMAL_HYBRID_SAFETY,
  validatePhase57MinimalHybridDatasetAdmission,
} from './phase57-selector-minimal-hybrid-dataset-guard.js';

const FALSE_SAFETY_KEYS=Object.freeze([
  'executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed',
  'liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted',
]);
const ALLOWED_EVIDENCE_CLASSES=new Set([
  'EXACT_POINT_IN_TIME','LATER_FETCHED_RECONSTRUCTION',
  'SURVIVORSHIP_LIMITED_RECONSTRUCTION','PROSPECTIVE_CAPTURE',
]);
const finite=value=>value!==null&&value!==undefined&&value!==''&&Number.isFinite(Number(value));
const round8=value=>Number(Number(value).toFixed(8));
const symbolOf=value=>String(value??'').trim().toUpperCase();

function deepFreeze(value){
  if(value&&typeof value==='object'&&!Object.isFrozen(value)){
    for(const child of Object.values(value))deepFreeze(child);
    Object.freeze(value);
  }
  return value;
}

function sha256(value){return createHash('sha256').update(JSON.stringify(value)).digest('hex');}

function jstParts(timestamp){
  const parts=new Intl.DateTimeFormat('en-CA',{
    timeZone:'Asia/Tokyo',year:'numeric',month:'2-digit',day:'2-digit',
    hour:'2-digit',minute:'2-digit',second:'2-digit',hourCycle:'h23',
  }).formatToParts(new Date(timestamp));
  const values=Object.fromEntries(parts.map(part=>[part.type,part.value]));
  return {sessionDate:`${values.year}-${values.month}-${values.day}`,time:`${values.hour}:${values.minute}`,second:values.second};
}

function regularBarOpen(time){return (time>='09:00'&&time<'11:30')||(time>='12:30'&&time<'15:30');}
function canonicalBar(bar){return JSON.stringify({
  timestamp:bar.timestamp,availableAt:bar.availableAt,sessionDate:bar.sessionDate,
  open:bar.open,high:bar.high,low:bar.low,close:bar.close,volume:bar.volume,turnover:bar.turnover??null,
});}

function distribution(values){
  if(!values.length)return {count:0,min:null,max:null,mean:null};
  return {count:values.length,min:Math.min(...values),max:Math.max(...values),mean:round8(values.reduce((sum,value)=>sum+value,0)/values.length)};
}

function manifestBlockers(manifest,blockers){
  const requiredStrings=['datasetId','sourceProvider','sourceEndpoint','acquisitionMethod','acquiredAt','reconstructionMethod','corporateActionHandling','volumeSemantics','turnoverSemantics'];
  for(const name of requiredStrings)if(!String(manifest?.[name]??'').trim())blockers.push(`MANIFEST_${name.toUpperCase()}_REQUIRED`);
  if(!Number.isFinite(Date.parse(String(manifest?.acquiredAt??''))))blockers.push('MANIFEST_ACQUIRED_AT_INVALID');
  if(!ALLOWED_EVIDENCE_CLASSES.has(manifest?.evidenceClassification))blockers.push('EVIDENCE_CLASS_INVALID');
  if(manifest?.targetLabelPolicy!=='SAME_SESSION_AFTER_CUTOFF_ONLY')blockers.push('TARGET_LABEL_POLICY_INVALID');
  if(manifest?.validationReleased!==false)blockers.push('VALIDATION_MUST_REMAIN_SEALED');
  if(manifest?.untouchedOosReleased!==false)blockers.push('UNTOUCHED_OOS_MUST_REMAIN_SEALED');
  for(const key of FALSE_SAFETY_KEYS)if(manifest?.safety?.[key]!==false)blockers.push(`SAFETY_${key}_MUST_BE_FALSE`);
}

export function auditPhase57MinimalHybridDataset(dataset){
  const blockers=[];
  if(!dataset||typeof dataset!=='object'||Array.isArray(dataset)){
    return deepFreeze({status:'MINIMAL_HYBRID_DATASET_ADMISSION_REJECTED',blockers:['DATASET_OBJECT_REQUIRED'],admission:null});
  }
  const manifest=dataset.manifest??{};
  manifestBlockers(manifest,blockers);
  const symbols=Array.isArray(dataset.symbols)?dataset.symbols:[];
  const sessions=Array.isArray(dataset.sessions)?dataset.sessions:[];
  if(!symbols.length)blockers.push('SYMBOLS_REQUIRED');
  if(!sessions.length)blockers.push('SESSIONS_REQUIRED');

  const sessionMap=new Map();
  for(const session of sessions){
    const date=String(session?.sessionDate??'');
    const members=Array.isArray(session?.memberSymbols)?session.memberSymbols.map(symbolOf).filter(Boolean):[];
    if(!members.length)blockers.push(`SESSION_${date||'UNKNOWN'}_MEMBERS_REQUIRED`);
    if(new Set(members).size!==members.length)blockers.push(`SESSION_${date||'UNKNOWN'}_MEMBERS_DUPLICATE`);
    sessionMap.set(date,{members:new Set(members),barCount:0,observedSymbols:new Set(),crossSections:new Set()});
  }

  const symbolSeen=new Set(),barSeen=new Map(),symbolStats=new Map();
  let totalBars=0,duplicateBars=0,timestampConflicts=0,lunchViolations=0;
  let futureAvailabilityViolations=0,invalidBars=0,missingTurnoverBars=0;
  for(const item of symbols){
    const symbol=symbolOf(item?.symbol);
    if(!symbol){blockers.push('SYMBOL_ID_REQUIRED');continue;}
    if(symbolSeen.has(symbol)){blockers.push(`DUPLICATE_SYMBOL_${symbol}`);continue;}
    symbolSeen.add(symbol);
    const bars=Array.isArray(item?.bars)?item.bars:[];
    const seenSessions=new Set();let validCount=0;
    for(const bar of bars){
      totalBars+=1;
      const timestamp=Date.parse(String(bar?.timestamp??''));
      const availableAt=Date.parse(String(bar?.availableAt??''));
      const key=`${symbol}|${String(bar?.timestamp??'')}`;
      const encoded=canonicalBar(bar??{});
      if(barSeen.has(key)){
        if(barSeen.get(key)===encoded)duplicateBars+=1;else timestampConflicts+=1;
        continue;
      }
      barSeen.set(key,encoded);
      const prices=['open','high','low','close'].map(name=>Number(bar?.[name]));
      const volume=Number(bar?.volume);
      if(!Number.isFinite(timestamp)||!Number.isFinite(availableAt)||!prices.every(Number.isFinite)||!finite(bar?.volume)
        ||prices.some(value=>value<=0)||volume<0||prices[1]<Math.max(prices[0],prices[2],prices[3])
        ||prices[2]>Math.min(prices[0],prices[1],prices[3])){
        invalidBars+=1;continue;
      }
      const parts=jstParts(timestamp);
      if(parts.sessionDate!==String(bar?.sessionDate??''))invalidBars+=1;
      if(!regularBarOpen(parts.time)||Number(parts.time.slice(3))%5!==0||parts.second!=='00')lunchViolations+=1;
      if(availableAt!==timestamp+5*60_000)futureAvailabilityViolations+=1;
      if(!finite(bar?.turnover))missingTurnoverBars+=1;
      validCount+=1;seenSessions.add(String(bar.sessionDate));
      const session=sessionMap.get(String(bar.sessionDate));
      if(session?.members.has(symbol)){
        session.barCount+=1;session.observedSymbols.add(symbol);session.crossSections.add(String(bar.availableAt));
      }
    }
    symbolStats.set(symbol,{symbol,barCount:validCount,sessionCount:seenSessions.size});
  }
  if(duplicateBars)blockers.push('DUPLICATE_BARS_PRESENT');
  if(timestampConflicts)blockers.push('TIMESTAMP_CONFLICTS_PRESENT');
  if(lunchViolations)blockers.push('LUNCH_OR_SESSION_VIOLATIONS_PRESENT');
  if(futureAvailabilityViolations)blockers.push('BAR_AVAILABILITY_SEMANTICS_VIOLATION');
  if(invalidBars)blockers.push('INVALID_BARS_PRESENT');

  const coverageBySession=sessions.map(session=>{
    const date=String(session.sessionDate),row=sessionMap.get(date);
    const memberCount=row?.members.size??0,observedSymbolCount=row?.observedSymbols.size??0;
    const expectedBars=memberCount*66;
    return {
      sessionDate:date,memberCount,observedSymbolCount,barCount:row?.barCount??0,
      totalCrossSections:row?.crossSections.size??0,
      missingBars:Math.max(0,expectedBars-(row?.barCount??0)),
      symbolCoverageRate:memberCount?round8(observedSymbolCount/memberCount):0,
    };
  });
  const coverageBySymbol=[...symbolStats.values()].sort((a,b)=>a.symbol.localeCompare(b.symbol));

  let admission=null;
  try{admission=validatePhase57MinimalHybridDatasetAdmission(dataset);}catch(error){blockers.push(`ADMISSION_GUARD:${String(error?.message??error)}`);}
  const uniqueBlockers=[...new Set(blockers)];
  const status=uniqueBlockers.length?'MINIMAL_HYBRID_DATASET_ADMISSION_REJECTED':'MINIMAL_HYBRID_DATASET_ADMITTED_DEVELOPMENT_ONLY';
  const reportCore={
    schemaVersion:1,phase:'57.selector-minimal-hybrid.dataset-admission-audit',status,
    datasetId:String(manifest.datasetId??''),source:String(manifest.sourceProvider??''),
    acquisitionMethod:String(manifest.acquisitionMethod??''),evidenceClassification:manifest.evidenceClassification??null,
    period:{firstSession:sessions[0]?.sessionDate??null,lastSession:sessions.at(-1)?.sessionDate??null},
    counts:{
      sessionCount:sessions.length,symbolCount:symbolSeen.size,totalBars,
      totalCrossSections:coverageBySession.reduce((sum,row)=>sum+row.totalCrossSections,0),
      missingBars:coverageBySession.reduce((sum,row)=>sum+row.missingBars,0),
      duplicateBars,timestampConflicts,lunchViolations,futureAvailabilityViolations,invalidBars,missingTurnoverBars,
    },
    coverageSummary:{
      sessionSymbolCoverage:distribution(coverageBySession.map(row=>row.symbolCoverageRate)),
      sessionBarCount:distribution(coverageBySession.map(row=>row.barCount)),
      symbolBarCount:distribution(coverageBySymbol.map(row=>row.barCount)),
      symbolSessionCount:distribution(coverageBySymbol.map(row=>row.sessionCount)),
    },
    coverageBySession,coverageBySymbol,
    provenance:{
      sourceEndpoint:manifest.sourceEndpoint??null,acquiredAt:manifest.acquiredAt??null,
      rawSourceSha256:manifest.rawSourceSha256??null,parentDatasetIds:manifest.parentDatasetIds??[],
      reconstructionMethod:manifest.reconstructionMethod??null,universeStatus:manifest.universeStatus??null,
      survivorshipLimitation:manifest.survivorshipLimitation??null,
      corporateActionHandling:manifest.corporateActionHandling??null,
      volumeSemantics:manifest.volumeSemantics??null,turnoverSemantics:manifest.turnoverSemantics??null,
    },
    release:{developmentReleased:status==='MINIMAL_HYBRID_DATASET_ADMITTED_DEVELOPMENT_ONLY',validationReleased:false,untouchedOosReleased:false},
    training:{featureScreeningPerformed:false,modelFittingPerformed:false,thresholdTuningPerformed:false},
    blockers:uniqueBlockers,admission,
    safety:PHASE57_SELECTOR_MINIMAL_HYBRID_SAFETY,
  };
  return deepFreeze({...reportCore,reportSha256:sha256(reportCore)});
}

export function requirePhase57MinimalHybridDatasetAdmission(dataset){
  const report=auditPhase57MinimalHybridDataset(dataset);
  if(report.status!=='MINIMAL_HYBRID_DATASET_ADMITTED_DEVELOPMENT_ONLY')throw new Error(`Minimal Hybrid dataset admission failed: ${report.blockers.join(' | ')}`);
  return report;
}

export default {auditPhase57MinimalHybridDataset,requirePhase57MinimalHybridDatasetAdmission};
