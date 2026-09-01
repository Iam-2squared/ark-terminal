import fs from 'node:fs';
import path from 'node:path';
import {spawnSync} from 'node:child_process';

const sourcePath='scripts/run_p25_partial_abcd_postclose.mjs';
const tmpPath='scripts/.tmp-run-p25-incomplete-outcome-coverage.mjs';
const args=process.argv.slice(2);

let src=fs.readFileSync(sourcePath,'utf8');
const mustReplace=(from,to,label)=>{
  if(!src.includes(from))throw new Error(`incomplete outcome wrapper patch target missing: ${label}`);
  src=src.replace(from,to);
};

mustReplace(
  "const partialDir=arg('--partial-dir'),historyPath=arg('--history-pack'),output=arg('--output','tmp/p25-partial-abcd.json');",
  "const partialDir=arg('--partial-dir'),historyPath=arg('--history-pack'),output=arg('--output','tmp/p25-partial-abcd.json');\nconst allowIncompleteOutcomeCoverage=arg('--allow-incomplete-outcome-coverage','false')==='true';",
  'flag',
);

mustReplace(
  "const response=await fetch(url,{headers:{'User-Agent':'Mozilla/5.0 ArkTerminalResearch/1.0','Accept':'application/json'},cache:'no-store'});",
  "const response=await fetch(url,{headers:{'User-Agent':'Mozilla/5.0 ArkTerminalResearch/1.0','Accept':'application/json'},cache:'no-store',signal:AbortSignal.timeout(12000)});",
  'bounded Yahoo 5m fetch timeout',
);

mustReplace(
  "await Promise.all(Array.from({length:Math.min(10,allSymbols.length)},()=>worker()));",
  "await Promise.all(Array.from({length:Math.min(20,allSymbols.length)},()=>worker()));",
  'bounded Yahoo 5m fetch concurrency',
);

mustReplace(
  "if(failures.length||Object.keys(sessionBarsBySymbol).length!==allSymbols.length)throw new Error(`post-close sparse 5m collection incomplete ${Object.keys(sessionBarsBySymbol).length}/${allSymbols.length}: ${JSON.stringify(failures.slice(0,12))}`);",
  "const unavailableSymbols=failures.map(x=>sym(x.symbol)).sort();\nconst usableSymbolSet=new Set(Object.keys(sessionBarsBySymbol));\nif((failures.length||Object.keys(sessionBarsBySymbol).length!==allSymbols.length)&&!allowIncompleteOutcomeCoverage)throw new Error(`post-close sparse 5m collection incomplete ${Object.keys(sessionBarsBySymbol).length}/${allSymbols.length}: ${JSON.stringify(failures.slice(0,12))}`);\nif(allowIncompleteOutcomeCoverage&&Object.keys(sessionBarsBySymbol).length===0)throw new Error('post-close sparse 5m collection has zero usable symbols');",
  'strict post-close coverage gate',
);

mustReplace(
  "  for(const symbol of d50){\n    const full=sessionBarsBySymbol[symbol]??[],prefix=full.filter(bar=>Date.parse(bar.timestamp)+5*60_000<=observedMs);",
  "  for(const symbol of d50){\n    if(allowIncompleteOutcomeCoverage&&!usableSymbolSet.has(symbol))continue;\n    const full=sessionBarsBySymbol[symbol]??[],prefix=full.filter(bar=>Date.parse(bar.timestamp)+5*60_000<=observedMs);",
  'D50 unavailable-symbol skip',
);

mustReplace(
  "const dynamicBundle={schemaVersion:1,phase:'57.p25.partial-dynamic5m-postclose-bundle'",
  "const evaluableDynamicUnion=dynamicUnion.filter(s=>usableSymbolSet.has(s));\nconst dynamicBundle={schemaVersion:1,phase:'57.p25.partial-dynamic5m-postclose-bundle'",
  'evaluable dynamic union',
);

mustReplace(
  "selectedSymbolUnionCount:dynamicUnion.length,selectedSymbolUnion:dynamicUnion",
  "selectedSymbolUnionCount:evaluableDynamicUnion.length,selectedSymbolUnion:evaluableDynamicUnion,originalSelectedSymbolUnionCount:dynamicUnion.length,originalSelectedSymbolUnion:dynamicUnion,evaluationExcludedSymbolsDueToMissingPostCloseBars:dynamicUnion.filter(s=>!usableSymbolSet.has(s))",
  'dynamic union coverage metadata',
);

mustReplace(
  "selected:(x.selected??[]).map(r=>({symbol:sym(r.symbol)",
  "selected:(x.selected??[]).filter(r=>usableSymbolSet.has(sym(r.symbol))).map(r=>({symbol:sym(r.symbol)",
  'dynamic point filtering',
);

mustReplace(
  "sessionBarsBySymbol:Object.fromEntries(dynamicUnion.map(s=>[s,sessionBarsBySymbol[s]]))",
  "sessionBarsBySymbol:Object.fromEntries(evaluableDynamicUnion.map(s=>[s,sessionBarsBySymbol[s]]))",
  'dynamic bars coverage',
);

mustReplace(
  "fs.writeFileSync(output,JSON.stringify(payload,null,2)+'\\n');",
  "payload.classification.outcomeCoverageComplete=unavailableSymbols.length===0;\npayload.classification.outcomeCoverageDiagnosticOnly=unavailableSymbols.length>0;\npayload.classification.formalOos=false;\npayload.classification.promotionEligible=false;\npayload.classification.evaluationExcludedSymbolsDueToMissingPostCloseBars=unavailableSymbols;\npayload.classification.d50EvaluationUniverseRequested=d50.length;\npayload.classification.d50EvaluationUniverseUsable=d50.filter(s=>usableSymbolSet.has(s)).length;\npayload.classification.d50EvaluationExcludedSymbols=d50.filter(s=>!usableSymbolSet.has(s));\npayload.inputs.requestedPostCloseBarsSymbolCount=allSymbols.length;\npayload.inputs.usablePostCloseBarsSymbolCount=Object.keys(sessionBarsBySymbol).length;\npayload.inputs.unavailablePostCloseBarsSymbolCount=unavailableSymbols.length;\npayload.inputs.unavailablePostCloseBarsSymbols=unavailableSymbols;\npayload.methodology.missingPostCloseBarsNeverBackfilledInterpolatedOrReplaced=true;\npayload.methodology.outcomeCoverageIncompleteDiagnostic=unavailableSymbols.length>0;\npayload.methodology.originalFrozenMembershipPreservedInSourceEvidence=true;\nfs.writeFileSync(output,JSON.stringify(payload,null,2)+'\\n');",
  'payload coverage attestation',
);

fs.writeFileSync(tmpPath,src);
try{
  const child=spawnSync(process.execPath,[tmpPath,...args,'--allow-incomplete-outcome-coverage','true'],{encoding:'utf8',stdio:['ignore','pipe','pipe'],timeout:24*60*1000,killSignal:'SIGKILL'});
  process.stdout.write(child.stdout??'');
  process.stderr.write(child.stderr??'');
  if(child.error)throw child.error;
  if(child.status!==0)process.exit(child.status??1);
}finally{
  try{fs.unlinkSync(tmpPath);}catch{}
}
