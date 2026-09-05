import fs from 'node:fs';
import path from 'node:path';
import {auditPhase57MinimalHybridDataset} from '../predict/daytrade/phase57-selector-minimal-hybrid-dataset-audit.js';

function arg(name,fallback=null){const index=process.argv.indexOf(name);return index>=0&&index+1<process.argv.length?process.argv[index+1]:fallback;}
const input=arg('--dataset');
const output=arg('--output','artifacts/phase57-selector-minimal-hybrid-dataset-admission.json');
if(!input)throw new Error('usage: --dataset <dataset.json> [--output admission.json]');
const dataset=JSON.parse(fs.readFileSync(input,'utf8'));
const report=auditPhase57MinimalHybridDataset(dataset);
fs.mkdirSync(path.dirname(output),{recursive:true});
fs.writeFileSync(output,JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify({status:report.status,datasetId:report.datasetId,output,counts:report.counts,blockers:report.blockers},null,2));
if(report.status!=='MINIMAL_HYBRID_DATASET_ADMITTED_DEVELOPMENT_ONLY')process.exitCode=2;
