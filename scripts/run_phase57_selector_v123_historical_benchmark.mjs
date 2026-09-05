import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {evaluatePhase57SelectorHistoricalBenchmark} from '../predict/daytrade/phase57-selector-v123-historical-benchmark.js';

function arg(name,fallback=null){const index=process.argv.indexOf(name);return index>=0&&index+1<process.argv.length?process.argv[index+1]:fallback;}
const datasetPath=arg('--dataset');
const output=arg('--output','artifacts/phase57-selector-v123-benchmark.json');
const releaseOuterOos=arg('--release-outer-oos','false')==='true';
const releaseConfirmation=arg('--oos-release-confirmation','');
if(!datasetPath)throw new Error('usage: --dataset <dataset.json> [--output file] [--release-outer-oos true --oos-release-confirmation I_UNDERSTAND_THIS_CONSUMES_THE_UNTOUCHED_OOS]');
if(releaseOuterOos&&releaseConfirmation!=='I_UNDERSTAND_THIS_CONSUMES_THE_UNTOUCHED_OOS'){
  throw new Error('outer OOS release requires the exact irreversible-consumption confirmation');
}
const freezePath=new URL('../predict/research/phase57-selector-v3-freeze.json',import.meta.url);
const digestPath=new URL('../predict/research/phase57-selector-v3-freeze.sha256',import.meta.url);
const freezeBytes=fs.readFileSync(freezePath);
const actualFreezeDigest=createHash('sha256').update(freezeBytes).digest('hex');
const expectedFreezeDigest=fs.readFileSync(digestPath,'utf8').trim().split(/\s+/)[0];
if(actualFreezeDigest!==expectedFreezeDigest)throw new Error('Selector V3.0 freeze digest mismatch');
const dataset=JSON.parse(fs.readFileSync(datasetPath,'utf8'));
const benchmark=evaluatePhase57SelectorHistoricalBenchmark(dataset,{releaseOuterOos});
const artifact={
  ...benchmark,
  provenance:{
    selectorV3FreezeSha256:actualFreezeDigest,
    datasetPath,
    generatedAt:new Date().toISOString(),
    outerOosReleaseExplicitlyConfirmed:releaseOuterOos,
  },
};
fs.mkdirSync(path.dirname(output),{recursive:true});
fs.writeFileSync(output,JSON.stringify(artifact,null,2)+'\n');
console.log(JSON.stringify({
  status:artifact.status,output,datasetId:artifact.dataset.datasetId,
  sessions:artifact.dataset.sessionCount,records:artifact.development.recordCount+artifact.validation.recordCount+(releaseOuterOos?artifact.untouchedOos.recordCount:artifact.untouchedOos.recordCount),
  selectedV3Threshold:artifact.calibration.selectedThreshold,
  outerOosConsumed:artifact.outerOosConsumed,
  evidenceClassification:artifact.dataset.evidenceClassification,
},null,2));

