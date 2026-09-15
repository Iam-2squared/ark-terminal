import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {loadFormalL0PartitionFromCache} from '../predict/long-only/phase57-long-only-l0-cache.js';
import {normalizeAndAggregateMinuteRows} from '../predict/long-only/phase57-long-only-integrated-dataset.js';
import {buildL1CrossSectionDataset} from '../predict/long-only/phase57-long-only-l1-cross-section.js';
import {buildL1DiscoveryReport} from '../predict/long-only/phase57-long-only-l1-discovery-report.js';

const arg=name=>{const i=process.argv.indexOf(name);return i<0?null:process.argv[i+1];};
const cacheRoot=path.resolve(arg('--cache-root')??''),partition=arg('--partition'),output=path.resolve(arg('--output')??'');
const unavailablePath=arg('--unavailable-sessions');
const sessionsContractPath=arg('--sessions-contract');
if(!cacheRoot||partition!=='DEVELOPMENT_A'||!output||!sessionsContractPath)throw new Error('usage: --cache-root <private cache> --partition DEVELOPMENT_A --sessions-contract <fixed-20.json> --output <sanitized report.json>');
const sourceUnavailable=new Set(unavailablePath?JSON.parse(fs.readFileSync(path.resolve(unavailablePath),'utf8')):[]);
const plan=JSON.parse(fs.readFileSync(new URL('../predict/long-only/phase57-long-only-data-plan.json',import.meta.url),'utf8'));
const allocation=JSON.parse(fs.readFileSync(new URL('../predict/long-only/phase57-long-only-session-allocation-v3.json',import.meta.url),'utf8'));
const sessionsContract=JSON.parse(fs.readFileSync(path.resolve(sessionsContractPath),'utf8'));
const approvedSessions=sessionsContract.sessions;
const approvedSessionHash=createHash('sha256').update(JSON.stringify(approvedSessions)).digest('hex');
if(approvedSessions.length!==20||approvedSessionHash!==sessionsContract.sessionListSha256||JSON.stringify(approvedSessions)!==JSON.stringify(allocation.partitions.DEVELOPMENT_A.slice(0,20)))throw new Error('L1 measurement sessions differ from fixed discovery contract');
const l0=loadFormalL0PartitionFromCache({cacheRoot,partition,plan,allocation});
const base=path.join(cacheRoot,'phase57-long-only','raw','jquants-v2'),featureRows=[],evaluatorOnlyLabels=[],sessionAudits=[];
const sha=value=>createHash('sha256').update(value).digest('hex');
const codeOf=row=>String(row?.Code??row?.code??row?.symbol??'').trim().toUpperCase();
const sectorOf=row=>String(row?.S17??row?.Sec17??row?.Sector17Code??row?.Sector33Code??row?.S33??row?.sectorCode??'UNKNOWN');

for(const sessionDate of approvedSessions){
  const sessionDir=path.join(base,sessionDate),minuteManifestPath=path.join(sessionDir,'l1-minute-manifest.json');
  if(!fs.existsSync(minuteManifestPath)){
    if(!sourceUnavailable.has(sessionDate))throw new Error(`Minute cache is unexpectedly missing for approved session: ${sessionDate}`);
    sessionAudits.push(Object.freeze({sessionDate,status:'SOURCE_UNAVAILABLE',eligibleDailySymbols:l0.rows.filter(row=>row.sessionDate===sessionDate).length}));
    continue;
  }
  const minuteManifest=JSON.parse(fs.readFileSync(minuteManifestPath,'utf8')),minutePages=JSON.parse(fs.readFileSync(path.join(sessionDir,'minute-pages.json'),'utf8'));
  if(minuteManifest.sessionDate!==sessionDate||minutePages.length!==minuteManifest.pageCount||minutePages.some(page=>sha(page.responseText)!==page.responseSha256))throw new Error(`Minute immutable-cache verification failed: ${sessionDate}`);
  const minuteRows=minutePages.flatMap(page=>JSON.parse(page.responseText).data??[]),intraday=normalizeAndAggregateMinuteRows(minuteRows);
  const masterPages=JSON.parse(fs.readFileSync(path.join(sessionDir,'master-pages.json'),'utf8')),sectorBySymbol={};
  for(const row of masterPages.flatMap(page=>JSON.parse(page.responseText).data??[])){const symbol=codeOf(row);if(symbol)sectorBySymbol[`${sessionDate}|${symbol}`]=sectorOf(row);}
  const dailyRows=l0.rows.filter(row=>row.sessionDate===sessionDate),built=buildL1CrossSectionDataset({partition,dailyRows,bars5m:intraday.bars,terminalAuctions:intraday.terminalAuctions,sectorBySymbol});
  featureRows.push(...built.featureRows);evaluatorOnlyLabels.push(...built.evaluatorOnlyLabels);
  const rawTimes=minuteRows.map(row=>String(row?.Time??row?.time??'')).filter(Boolean).sort(),symbolsWithMinute=new Set(minuteRows.map(codeOf).filter(Boolean));
  sessionAudits.push(Object.freeze({sessionDate,eligibleDailySymbols:dailyRows.length,symbolsWithMinute:symbolsWithMinute.size,minuteCoverageVsEligiblePct:dailyRows.length?Number((100*symbolsWithMinute.size/dailyRows.length).toFixed(4)):null,firstRawTime:rawTimes[0]??null,lastRawTime:rawTimes.at(-1)??null,pageCount:minuteManifest.pageCount,rawRows:minuteRows.length,...intraday.audit,l1FeatureRows:built.featureRows.length,l1LabelRows:built.evaluatorOnlyLabels.length,exclusions:built.audit.exclusions}));
  console.log(JSON.stringify({status:'L1_SESSION_MEASURED',partition,sessionDate,rawRows:minuteRows.length,featureRows:built.featureRows.length}));
}

const measuredSessionCount=sessionAudits.filter(row=>row.status!=='SOURCE_UNAVAILABLE').length;
const report=buildL1DiscoveryReport({featureRows,evaluatorOnlyLabels,audit:{partition,approvedSessionCount:approvedSessions.length,sessionListSha256:approvedSessionHash,measuredSessionCount,sourceUnavailableSessions:sessionAudits.filter(row=>row.status==='SOURCE_UNAVAILABLE').map(row=>row.sessionDate),sourceSha256:l0.sourceManifest.sourceSha256,featureRows:featureRows.length,labelRows:evaluatorOnlyLabels.length,sessionAudits}});
fs.mkdirSync(path.dirname(output),{recursive:true});fs.writeFileSync(output,`${JSON.stringify(report,null,2)}\n`,{flag:'wx'});
console.log(JSON.stringify({status:'L1_DISCOVERY_REPORT_READY',partition,featureRows:featureRows.length,labelRows:evaluatorOnlyLabels.length,output}));
