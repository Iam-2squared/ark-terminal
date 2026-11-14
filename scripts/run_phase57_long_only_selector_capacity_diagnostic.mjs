import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {loadFormalL0PartitionFromCache} from '../predict/long-only/phase57-long-only-l0-cache.js';
import {normalizeAndAggregateMinuteRows} from '../predict/long-only/phase57-long-only-integrated-dataset.js';
import {buildL1CrossSectionDataset} from '../predict/long-only/phase57-long-only-l1-cross-section.js';
import {buildFixedHorizonTargets} from '../predict/long-only/phase57-long-only-l2-fixed-horizon.js';
import {fitL2Candidate} from '../predict/long-only/phase57-long-only-l2-selector-v1.js';
import {rankFrozenScore,diagnoseCapacity} from '../predict/long-only/phase57-long-only-selector-capacity-diagnostic.js';

const arg=name=>{const i=process.argv.indexOf(name);return i<0?null:process.argv[i+1];};
const cacheRoot=path.resolve(arg('--cache-root')??''),freezePath=path.resolve(arg('--freeze-report')??''),output=path.resolve(arg('--output')??'');
if(!cacheRoot||!freezePath||!output)throw new Error('usage: --cache-root <private cache> --freeze-report <L2 report> --output <sanitized report>');
const plan=JSON.parse(fs.readFileSync(new URL('../predict/long-only/phase57-long-only-data-plan.json',import.meta.url),'utf8'));
const allocation=JSON.parse(fs.readFileSync(new URL('../predict/long-only/phase57-long-only-session-allocation-v3.json',import.meta.url),'utf8'));
const sessionsContract=JSON.parse(fs.readFileSync(new URL('../predict/long-only/phase57-long-only-l2-development-sessions.json',import.meta.url),'utf8'));
const freezeReport=JSON.parse(fs.readFileSync(freezePath,'utf8'));
const shaText=value=>createHash('sha256').update(value).digest('hex');
const sha=value=>shaText(JSON.stringify(value));
const base=path.join(cacheRoot,'phase57-long-only','raw','jquants-v2');
const codeOf=row=>String(row?.Code??row?.code??row?.symbol??'').trim().toUpperCase();
const sectorOf=row=>String(row?.S17??row?.Sec17??row?.Sector17Code??row?.Sector33Code??row?.S33??row?.sectorCode??'UNKNOWN');
const rowKey=row=>`${row.sessionDate}|${row.symbol}|${row.decisionTimeJst}`;
const append=(target,source)=>{for(const row of source)target.push(row);};

if(freezeReport.status!=='L2_SELECTOR_FROZEN'||freezeReport.freeze?.freezeSha256!=='e883168e49b0ee2cf75e4b5bb1053c170b1ca58621a50ff004cd0aa973bfdf15')throw new Error('unexpected L2 freeze evidence');
if(freezeReport.audit?.validationOpened!==false||freezeReport.audit?.oosOpened!==false)throw new Error('sealed partition violation');

function loadSession(partition,sessionDate){
  const l0=loadFormalL0PartitionFromCache({cacheRoot,partition,plan,allocation}),sessionDir=path.join(base,sessionDate);
  const manifest=JSON.parse(fs.readFileSync(path.join(sessionDir,'l2-minute-manifest.json'),'utf8')),pages=JSON.parse(fs.readFileSync(path.join(sessionDir,'minute-pages.json'),'utf8'));
  if(manifest.sessionDate!==sessionDate||manifest.partition!==partition||manifest.sessionListSha256!==sessionsContract.sessionListSha256||pages.length!==manifest.pageCount||pages.some(page=>shaText(page.responseText)!==page.responseSha256))throw new Error(`immutable Minute cache mismatch: ${sessionDate}`);
  const minuteRows=pages.flatMap(page=>JSON.parse(page.responseText).data??[]),intraday=normalizeAndAggregateMinuteRows(minuteRows);
  const masterPages=JSON.parse(fs.readFileSync(path.join(sessionDir,'master-pages.json'),'utf8')),sectorBySymbol={};
  for(const row of masterPages.flatMap(page=>JSON.parse(page.responseText).data??[])){const symbol=codeOf(row);if(symbol)sectorBySymbol[`${sessionDate}|${symbol}`]=sectorOf(row);}
  const dailyRows=l0.rows.filter(row=>row.sessionDate===sessionDate),cross=buildL1CrossSectionDataset({partition,dailyRows,bars5m:intraday.bars,terminalAuctions:intraday.terminalAuctions,sectorBySymbol});
  const targets=buildFixedHorizonTargets({featureRows:cross.featureRows,bars5m:intraday.bars,evaluatorOnlyLabels:cross.evaluatorOnlyLabels}),targetKeys=new Set(targets.map(rowKey));
  return {features:cross.featureRows.filter(row=>targetKeys.has(rowKey(row))),targets,audit:{sessionDate,pageCount:manifest.pageCount,rawRows:minuteRows.length,featureRows:cross.featureRows.length,targetRows:targets.length,corporateActionExclusions:cross.audit.exclusions.CORPORATE_ACTION_UNRESOLVED}};
}

const C={features:[],targets:[],audit:[]},D={features:[],targets:[],audit:[]};
for(const sessionDate of allocation.partitions.DEVELOPMENT_C){const loaded=loadSession('DEVELOPMENT_C',sessionDate);append(C.features,loaded.features);append(C.targets,loaded.targets);C.audit.push(loaded.audit);console.log(JSON.stringify({status:'CAPACITY_C_SCORE_RECONSTRUCTION',sessionDate,featureRows:loaded.features.length}));}
for(const sessionDate of allocation.partitions.DEVELOPMENT_D){const loaded=loadSession('DEVELOPMENT_D',sessionDate);append(D.features,loaded.features);append(D.targets,loaded.targets);D.audit.push(loaded.audit);console.log(JSON.stringify({status:'CAPACITY_D_READY',sessionDate,featureRows:loaded.features.length}));}

const cFit=fitL2Candidate({candidateId:freezeReport.freeze.selectedCandidate,featureRows:C.features,targetRows:C.targets,featureNames:freezeReport.freeze.selectedFeatureNames});
const frozenCandidate=freezeReport.freeze.allCandidates.find(row=>row.candidateId===freezeReport.freeze.selectedCandidate&&row.topN===freezeReport.freeze.topN&&row.horizonBars===freezeReport.freeze.horizonBars);
if(!frozenCandidate||cFit.artifactSha256!==frozenCandidate.fitArtifactSha256)throw new Error('reconstructed fixed Development C score differs from frozen evidence');
const ranked=rankFrozenScore({featureRows:D.features,targetRows:D.targets,artifact:cFit}),diagnostic=diagnoseCapacity(ranked);
const report={schemaVersion:1,status:'SELECTOR_CAPACITY_DIAGNOSTIC_COMPLETE_STOP',selectorState:'CANDIDATE_V1_DIAGNOSTIC',source:{l2FreezeSha256:freezeReport.freeze.freezeSha256,developmentCArtifactSha256:cFit.artifactSha256,artifactMatch:true,selectedCandidate:freezeReport.freeze.selectedCandidate,featureNames:freezeReport.freeze.selectedFeatureNames,horizonBars:freezeReport.freeze.horizonBars,originalTopN:freezeReport.freeze.topN,evaluationPartition:'DEVELOPMENT_D',evaluationSessions:allocation.partitions.DEVELOPMENT_D,sessionListSha256:sessionsContract.sessionListSha256,jquantsRequests:0},diagnostic,audit:{developmentC:{featureRows:C.features.length,targetRows:C.targets.length,sessions:C.audit},developmentD:{featureRows:D.features.length,targetRows:D.targets.length,rankedRows:ranked.length,decisionCount:new Set(ranked.map(x=>`${x.feature.sessionDate}|${x.feature.decisionTimeJst}`)).size,sessions:D.audit},modelWeightsChanged:false,featuresChanged:false,targetChanged:false,ridgeHyperparametersChanged:false,entryChanged:false,exitChanged:false,allocationChanged:false,validationOpened:false,oosOpened:false},safety:{executionAllowed:false,brokerWriteAllowed:false,excelOrderWriteAllowed:false,rssOrderFunctionAllowed:false,liveTradingAllowed:false,paperTradingAllowed:false,shortTrades:0,marginTrades:0,leverage:0}};
report.reportSha256=sha(report);
fs.mkdirSync(path.dirname(output),{recursive:true});fs.writeFileSync(output,`${JSON.stringify(report,null,2)}\n`,{flag:'wx'});
console.log(JSON.stringify({status:report.status,capacity:Object.fromEntries(Object.entries(report.diagnostic.capacityCurve).map(([k,v])=>[k,{n:v.candidateCount,meanBps:v.meanReturnBps,medianBps:v.medianReturnBps,positiveRatePct:v.positiveRatePct,maePct:v.meanFutureMaePct,recall100:v.opportunities.GE_100_BPS.recallPct}])),spearman:report.diagnostic.scoreCalibration.spearman,reportSha256:report.reportSha256}));
