import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {loadFormalL0PartitionFromCache} from '../predict/long-only/phase57-long-only-l0-cache.js';
import {normalizeAndAggregateMinuteRows} from '../predict/long-only/phase57-long-only-integrated-dataset.js';
import {buildL1CrossSectionDataset} from '../predict/long-only/phase57-long-only-l1-cross-section.js';
import {buildFixedHorizonTargets,L2_HORIZON_CONTRACT} from '../predict/long-only/phase57-long-only-l2-fixed-horizon.js';
import {chooseAndFreezeL2,runFeatureFamilyAblation,chooseFeatureSetFromAblation,L2_SELECTOR_CONTRACT} from '../predict/long-only/phase57-long-only-l2-selector-v1.js';

const arg=name=>{const i=process.argv.indexOf(name);return i<0?null:process.argv[i+1];};
const cacheRoot=path.resolve(arg('--cache-root')??''),output=path.resolve(arg('--output')??'');
if(!cacheRoot||!output)throw new Error('usage: --cache-root <private cache> --output <sanitized L2 report.json>');
const plan=JSON.parse(fs.readFileSync(new URL('../predict/long-only/phase57-long-only-data-plan.json',import.meta.url),'utf8'));
const allocation=JSON.parse(fs.readFileSync(new URL('../predict/long-only/phase57-long-only-session-allocation-v3.json',import.meta.url),'utf8'));
const sessionsContract=JSON.parse(fs.readFileSync(new URL('../predict/long-only/phase57-long-only-l2-development-sessions.json',import.meta.url),'utf8'));
const expected=[...allocation.partitions.DEVELOPMENT_C,...allocation.partitions.DEVELOPMENT_D];
const hash=value=>createHash('sha256').update(JSON.stringify(value)).digest('hex');
const sha=value=>createHash('sha256').update(value).digest('hex');
if(expected.length!==40||JSON.stringify(expected)!==JSON.stringify(sessionsContract.sessions)||hash(expected)!==sessionsContract.sessionListSha256)throw new Error('L2 measurement differs from approved C+D session contract');
const base=path.join(cacheRoot,'phase57-long-only','raw','jquants-v2');
const codeOf=row=>String(row?.Code??row?.code??row?.symbol??'').trim().toUpperCase();
const sectorOf=row=>String(row?.S17??row?.Sec17??row?.Sector17Code??row?.Sector33Code??row?.S33??row?.sectorCode??'UNKNOWN');

function buildPartition(partition){
  const l0=loadFormalL0PartitionFromCache({cacheRoot,partition,plan,allocation}),featureRows=[],targetRows=[],sessionAudits=[];
  for(const sessionDate of allocation.partitions[partition]){
    const sessionDir=path.join(base,sessionDate),manifestPath=path.join(sessionDir,'l2-minute-manifest.json');
    if(!fs.existsSync(manifestPath))throw new Error(`L2 Minute cache missing: ${sessionDate}`);
    const manifest=JSON.parse(fs.readFileSync(manifestPath,'utf8')),pages=JSON.parse(fs.readFileSync(path.join(sessionDir,'minute-pages.json'),'utf8'));
    if(manifest.sessionDate!==sessionDate||manifest.partition!==partition||manifest.sessionListSha256!==sessionsContract.sessionListSha256||pages.length!==manifest.pageCount||pages.some(page=>sha(page.responseText)!==page.responseSha256))throw new Error(`L2 immutable-cache verification failed: ${sessionDate}`);
    const minuteRows=pages.flatMap(page=>JSON.parse(page.responseText).data??[]),intraday=normalizeAndAggregateMinuteRows(minuteRows);
    const masterPages=JSON.parse(fs.readFileSync(path.join(sessionDir,'master-pages.json'),'utf8')),sectorBySymbol={};
    for(const row of masterPages.flatMap(page=>JSON.parse(page.responseText).data??[])){const symbol=codeOf(row);if(symbol)sectorBySymbol[`${sessionDate}|${symbol}`]=sectorOf(row);}
    const dailyRows=l0.rows.filter(row=>row.sessionDate===sessionDate),crossSection=buildL1CrossSectionDataset({partition,dailyRows,bars5m:intraday.bars,terminalAuctions:intraday.terminalAuctions,sectorBySymbol});
    const targets=buildFixedHorizonTargets({featureRows:crossSection.featureRows,bars5m:intraday.bars,evaluatorOnlyLabels:crossSection.evaluatorOnlyLabels});
    const targetKeys=new Set(targets.map(row=>`${row.sessionDate}|${row.symbol}|${row.decisionTimeJst}`)),features=crossSection.featureRows.filter(row=>targetKeys.has(`${row.sessionDate}|${row.symbol}|${row.decisionTimeJst}`));
    featureRows.push(...features);targetRows.push(...targets);
    sessionAudits.push({sessionDate,pageCount:manifest.pageCount,rawRows:minuteRows.length,featureRows:features.length,targetRows:targets.length,y30Rows:targets.filter(row=>Number.isFinite(row.y30Bps)).length,y60Rows:targets.filter(row=>Number.isFinite(row.y60Bps)).length,corporateActionExclusions:crossSection.audit.exclusions.CORPORATE_ACTION_UNRESOLVED,minutePriceScale:crossSection.audit.minutePriceScale});
    console.log(JSON.stringify({status:'L2_SESSION_PREPARED',partition,sessionDate,rawRows:minuteRows.length,featureRows:features.length}));
  }
  return Object.freeze({partition,featureRows:Object.freeze(featureRows),targetRows:Object.freeze(targetRows),sessionAudits:Object.freeze(sessionAudits),featureSha256:hash(featureRows),targetSha256:hash(targetRows),sourceSha256:l0.sourceManifest.sourceSha256});
}

const developmentC=buildPartition('DEVELOPMENT_C'),developmentD=buildPartition('DEVELOPMENT_D');
const firstC=new Set(allocation.partitions.DEVELOPMENT_C.slice(0,10)),lastC=new Set(allocation.partitions.DEVELOPMENT_C.slice(10));
const ablations=runFeatureFamilyAblation({
  fitFeatures:developmentC.featureRows.filter(row=>firstC.has(row.sessionDate)),
  fitTargets:developmentC.targetRows.filter(row=>firstC.has(row.sessionDate)),
  evaluationFeatures:developmentC.featureRows.filter(row=>lastC.has(row.sessionDate)),
  evaluationTargets:developmentC.targetRows.filter(row=>lastC.has(row.sessionDate)),
  topN:10,
});
const selectedFeatureSet=chooseFeatureSetFromAblation(ablations);
const freeze=chooseAndFreezeL2({developmentC,developmentD,featureNames:selectedFeatureSet.featureNames});
const report={schemaVersion:1,status:freeze.labelShufflePass?'L2_SELECTOR_FROZEN':'L2_NO_FREEZE_NEGATIVE_CONTROL_FAILED',sessionListSha256:sessionsContract.sessionListSha256,horizonContract:L2_HORIZON_CONTRACT,selectorContract:L2_SELECTOR_CONTRACT,audit:{developmentC:{featureRows:developmentC.featureRows.length,targetRows:developmentC.targetRows.length,featureSha256:developmentC.featureSha256,targetSha256:developmentC.targetSha256,sourceSha256:developmentC.sourceSha256,sessionAudits:developmentC.sessionAudits},developmentD:{featureRows:developmentD.featureRows.length,targetRows:developmentD.targetRows.length,featureSha256:developmentD.featureSha256,targetSha256:developmentD.targetSha256,sourceSha256:developmentD.sourceSha256,sessionAudits:developmentD.sessionAudits},labelFieldsReachDecisionPipeline:false,validationOpened:false,oosOpened:false},featureFamilyAblation:ablations,selectedFeatureSet:{variant:selectedFeatureSet.variant,featureNames:selectedFeatureSet.featureNames,developmentCMetrics:selectedFeatureSet.metrics},freeze};
fs.mkdirSync(path.dirname(output),{recursive:true});fs.writeFileSync(output,`${JSON.stringify(report,null,2)}\n`,{flag:'wx'});
console.log(JSON.stringify({status:report.status,selectedCandidate:freeze.selectedCandidate,horizonBars:freeze.horizonBars,topN:freeze.topN,freezeSha256:freeze.freezeSha256,labelShufflePass:freeze.labelShufflePass,output}));
if(!freeze.labelShufflePass)process.exitCode=2;
