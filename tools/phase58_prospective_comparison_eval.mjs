import fs from 'node:fs';
import crypto from 'node:crypto';
import {evaluatePhase58ProspectiveComparison,PHASE58_P26_SAFETY} from '../predict/scalping/phase58-prospective-comparison-evaluator.js';
import {validateProspectiveOutcomeBoundaryJoins} from '../predict/scalping/phase58-prospective-outcome-boundary-guard.js';

function argsOf(argv){
  const out={input:null,output:null};
  for(let i=0;i<argv.length;i+=1){
    const arg=argv[i];
    if(arg==='--input')out.input=argv[++i]??null;
    else if(arg==='--output')out.output=argv[++i]??null;
    else throw new Error(`unknown argument: ${arg}`);
  }
  return out;
}

function main(){
  let args;
  try{args=argsOf(process.argv.slice(2));}
  catch(error){console.error(String(error?.message??error));return 2;}
  if(!args.input){
    console.error('usage: node tools/phase58_prospective_comparison_eval.mjs --input <sync.jsonl> [--output <report.json>]');
    return 2;
  }
  if(!fs.existsSync(args.input)){
    console.error(`synchronized capture not found: ${args.input}`);
    return 2;
  }
  const bytes=fs.readFileSync(args.input);
  const datasetSha256=crypto.createHash('sha256').update(bytes).digest('hex');
  const lines=bytes.toString('utf8').split(/\r?\n/).filter(line=>line.trim());
  const rows=[];
  for(let i=0;i<lines.length;i+=1){
    try{rows.push(JSON.parse(lines[i]));}
    catch(error){
      const out={phase:'58.p26.prospective-comparison-cli',status:'BLOCKED_MALFORMED_JSONL',complete:false,row:i+1,datasetSha256,error:String(error?.message??error),promotionEvidence:false,safety:PHASE58_P26_SAFETY};
      console.log(JSON.stringify(out,null,2));
      return 1;
    }
  }
  const rawReport=evaluatePhase58ProspectiveComparison({rows,datasetSha256});
  const outcomeIntegrity=validateProspectiveOutcomeBoundaryJoins(rawReport);
  const report=outcomeIntegrity.complete?Object.freeze({
    ...rawReport,
    outcomeJoinIntegrity:outcomeIntegrity,
  }):Object.freeze({
    ...rawReport,
    status:'BLOCKED_OUTCOME_CAPTURE_LAG',
    complete:false,
    maturedEventCount:0,
    formalNonOverlappingEventCount:0,
    allOverlappingDescriptive:null,
    formalNonOverlapping:null,
    comparisonSuppressed:true,
    outcomeJoinIntegrity:outcomeIntegrity,
    promotionEvidence:false,
    recommendationAllowed:false,
  });
  const out={
    phase:'58.p26.prospective-comparison-cli',
    status:report.status,
    complete:report.complete,
    input:args.input,
    datasetSha256,
    datasetHashComputedFromExactInputBytes:true,
    promotionEvidence:false,
    report,
    safety:PHASE58_P26_SAFETY,
  };
  if(args.output){
    const path=args.output;
    const slash=Math.max(path.lastIndexOf('/'),path.lastIndexOf('\\'));
    if(slash>=0)fs.mkdirSync(path.slice(0,slash),{recursive:true});
    fs.writeFileSync(path,JSON.stringify(out,null,2)+'\n','utf8');
    out.output=path;
  }
  console.log(JSON.stringify(out,null,2));
  return report.complete?0:1;
}

process.exitCode=main();
