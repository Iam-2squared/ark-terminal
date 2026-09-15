#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {SourceObserver} from './lib/phase57-source-observer.mjs';
import {EvidenceLog,digest,FREEZE,SAFETY} from './lib/phase57-offline-parity.mjs';
const [input,output]=process.argv.slice(2);
if(!input||!output)throw Error('USAGE: node scripts/phase57-source-diagnostic.mjs capture.jsonl NEW_OUTPUT_DIRECTORY');
const bytes=fs.readFileSync(input),observer=new SourceObserver();
fs.mkdirSync(output,{recursive:false});
const journal=new EvidenceLog(path.join(output,'source-diagnostic.jsonl'));
try{
  journal.append('IDENTITY',{mode:'SOURCE_SEMANTICS_ONLY',freezeSha256:FREEZE,repoHead:execFileSync('git',['rev-parse','HEAD'],{encoding:'utf8'}).trim(),rawInputHash:digest(bytes),safety:SAFETY});
  for(const line of bytes.toString('utf8').split('\n').filter(Boolean)){
    const packet=JSON.parse(line);const observation=observer.step(packet);journal.append('OBSERVATION',{packet,observation});
  }
  const report=observer.report();journal.append('SEAL',{report,reportHash:digest(JSON.stringify(report))});
  fs.writeFileSync(path.join(output,'summary.json'),JSON.stringify(report,null,2)+'\n',{flag:'wx'});
  console.log(JSON.stringify({status:'SOURCE_DIAGNOSTIC_RECORDED_NOT_VERIFIED',captures:report.captures,output,strategyCalculated:false}));
}catch(e){journal.append('HALT',{reason:e.message});throw e;}finally{journal.close();}
