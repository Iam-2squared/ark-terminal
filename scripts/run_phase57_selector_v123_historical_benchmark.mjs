import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {createGzip} from 'node:zlib';
import {Readable} from 'node:stream';
import {pipeline} from 'node:stream/promises';
import {
  evaluatePhase57SelectorHistoricalBenchmark,
  splitPhase57SelectorHistoricalSessions,
  validatePhase57SelectorHistoricalDataset,
} from '../predict/daytrade/phase57-selector-v123-historical-benchmark.js';

function arg(name,fallback=null){const index=process.argv.indexOf(name);return index>=0&&index+1<process.argv.length?process.argv[index+1]:fallback;}
const datasetPath=arg('--dataset');
const output=arg('--output','artifacts/phase57-selector-v123-benchmark.json');
const selectionLedgerOutput=arg('--selection-ledger-output','artifacts/phase57-selector-v123-selection-outcomes.ndjson.gz');
const releaseOuterOos=arg('--release-outer-oos','false')==='true';
const releaseConfirmation=arg('--oos-release-confirmation','');
const suppliedAnalysisContractDigest=arg('--oos-analysis-contract-sha256','');
if(!datasetPath)throw new Error('usage: --dataset <dataset.json> [--output file] [--release-outer-oos true --oos-release-confirmation I_UNDERSTAND_THIS_CONSUMES_THE_UNTOUCHED_OOS --oos-analysis-contract-sha256 <frozen sha256>]');
if(releaseOuterOos&&releaseConfirmation!=='I_UNDERSTAND_THIS_CONSUMES_THE_UNTOUCHED_OOS'){
  throw new Error('outer OOS release requires the exact irreversible-consumption confirmation');
}
const freezePath=new URL('../predict/research/phase57-selector-v3-freeze.json',import.meta.url);
const digestPath=new URL('../predict/research/phase57-selector-v3-freeze.sha256',import.meta.url);
const freezeBytes=fs.readFileSync(freezePath);
const actualFreezeDigest=createHash('sha256').update(freezeBytes).digest('hex');
const expectedFreezeDigest=fs.readFileSync(digestPath,'utf8').trim().split(/\s+/)[0];
if(actualFreezeDigest!==expectedFreezeDigest)throw new Error('Selector V3.0 freeze digest mismatch');
const analysisContractPath=new URL('../predict/research/phase57-selector-oos-analysis-contract.json',import.meta.url);
const analysisContractDigestPath=new URL('../predict/research/phase57-selector-oos-analysis-contract.sha256',import.meta.url);
const analysisContractBytes=fs.readFileSync(analysisContractPath);
const actualAnalysisContractDigest=createHash('sha256').update(analysisContractBytes).digest('hex');
const expectedAnalysisContractDigest=fs.readFileSync(analysisContractDigestPath,'utf8').trim().split(/\s+/)[0];
if(actualAnalysisContractDigest!==expectedAnalysisContractDigest)throw new Error('OOS Analysis Contract digest mismatch');
const analysisContract=JSON.parse(analysisContractBytes);
if(analysisContract.status!=='FROZEN_BEFORE_UNTOUCHED_OOS_RELEASE')throw new Error('OOS Analysis Contract is not frozen');
if(analysisContract.selectorV3Freeze?.sha256!==actualFreezeDigest)throw new Error('OOS Analysis Contract V3 digest mismatch');
if(releaseOuterOos&&suppliedAnalysisContractDigest!==actualAnalysisContractDigest){
  throw new Error('outer OOS release requires the exact frozen OOS Analysis Contract SHA-256');
}
const dataset=JSON.parse(fs.readFileSync(datasetPath,'utf8'));
const datasetValidation=validatePhase57SelectorHistoricalDataset(dataset);
const plannedSplit=splitPhase57SelectorHistoricalSessions(dataset.sessions);
if(releaseOuterOos){
  const boundary=analysisContract.evidenceBoundary;
  const expectedOos=boundary?.untouchedOos?.sessions??[];
  if(datasetValidation.datasetId!==boundary?.datasetId||datasetValidation.datasetDigest!==boundary?.datasetDigest){
    throw new Error('outer OOS dataset identity does not match the frozen Analysis Contract');
  }
  if(datasetValidation.benchmarkScope!==boundary?.benchmarkScope||datasetValidation.evidenceClassification!==boundary?.evidenceClassification){
    throw new Error('outer OOS evidence boundary does not match the frozen Analysis Contract');
  }
  if(JSON.stringify(plannedSplit.untouchedOos)!==JSON.stringify(expectedOos)){
    throw new Error('outer OOS sessions do not match the frozen Analysis Contract');
  }
}
const benchmark=evaluatePhase57SelectorHistoricalBenchmark(dataset,{releaseOuterOos,includeSelectionOutcomes:true});
if(releaseOuterOos){
  const boundary=analysisContract.evidenceBoundary;
  if(benchmark.calibration.selectedThreshold!==boundary?.expectedSelectedV3Threshold){
    throw new Error('outer OOS V3 threshold does not match the frozen Analysis Contract');
  }
  if(benchmark.untouchedOos.primaryInference?.winnerDecision?.automaticPromotionAllowed!==false){
    throw new Error('outer OOS automatic promotion guard missing');
  }
}
const folds=[['development',benchmark.development],['validation',benchmark.validation]];
if(releaseOuterOos)folds.push(['untouchedOos',benchmark.untouchedOos]);
function *ledgerLines(){
  for(const [fold,value] of folds){
    for(const point of value.selectionPoints??[])yield `${JSON.stringify({recordType:'SELECTOR_SELECTION_POINT',fold,...point})}\n`;
    for(const outcome of value.selectionOutcomes??[])yield `${JSON.stringify({fold,...outcome})}\n`;
  }
}
fs.mkdirSync(path.dirname(selectionLedgerOutput),{recursive:true});
await pipeline(Readable.from(ledgerLines()),createGzip({level:9}),fs.createWriteStream(selectionLedgerOutput));
const selectionLedgerSha256=createHash('sha256').update(fs.readFileSync(selectionLedgerOutput)).digest('hex');
function summaryOnly(value){
  if(!value||typeof value!=='object')return value;
  const {selectionOutcomes,selectionPoints,...summary}=value;
  return summary;
}
const artifact={
  ...benchmark,
  development:summaryOnly(benchmark.development),
  validation:summaryOnly(benchmark.validation),
  untouchedOos:summaryOnly(benchmark.untouchedOos),
  provenance:{
    selectorV3FreezeSha256:actualFreezeDigest,
    oosAnalysisContractSha256:actualAnalysisContractDigest,
    datasetPath,
    selectionLedgerOutput,
    selectionLedgerSha256,
    generatedAt:new Date().toISOString(),
    outerOosReleaseExplicitlyConfirmed:releaseOuterOos,
    outerOosAnalysisContractVerified:releaseOuterOos,
  },
};
fs.mkdirSync(path.dirname(output),{recursive:true});
fs.writeFileSync(output,JSON.stringify(artifact,null,2)+'\n');
console.log(JSON.stringify({
  status:artifact.status,output,datasetId:artifact.dataset.datasetId,
  sessions:artifact.dataset.sessionCount,records:artifact.development.recordCount+artifact.validation.recordCount+(releaseOuterOos?artifact.untouchedOos.recordCount:artifact.untouchedOos.recordCount),
  selectedV3Threshold:artifact.calibration.selectedThreshold,
  selectionLedgerOutput,
  selectionOutcomeRecords:folds.reduce((sum,[,value])=>sum+(value.selectionOutcomeRecordCount??0),0),
  outerOosConsumed:artifact.outerOosConsumed,
  oosAnalysisContractSha256:artifact.provenance.oosAnalysisContractSha256,
  evidenceClassification:artifact.dataset.evidenceClassification,
},null,2));
