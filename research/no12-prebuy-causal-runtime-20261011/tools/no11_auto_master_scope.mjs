/** Automatic metadata exclusion of selected candidates; never rerank, trade,
 * change Frozen rules, erase a held/Watch/EXIT chart, or fabricate a master. */
import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {validateNo11Chart50Plan} from '../runtime/no11_rss_chart_50_prescreen.mjs';
const sha=x=>createHash('sha256').update(x).digest('hex');
const need=(ok,c)=>{if(!ok)throw Error('NO11_AUTO_MASTER_'+c)};
const ROOT=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../../..');
function read(file){
 need(path.isAbsolute(file),'ABSOLUTE_PATH');
 const p=path.resolve(file),s=fs.lstatSync(p);
 need(p!==ROOT&&!p.startsWith(ROOT+path.sep)&&s.isFile()&&!s.isSymbolicLink()&&s.size<=4000000,'PRIVATE_INPUT');
 return JSON.parse(fs.readFileSync(p,'utf8').replace(/^\uFEFF/,''));
}
export function narrow(receipt,mask,eligible,evidenceHash){
 const old=receipt.chartPlan;
 const selected=validateNo11Chart50Plan({chartPlan:old,mask,sessionDate:old.sessionDate});
 need(receipt.schemaId==='ARK_NO11_CHART50_PRIVATE_EXPORT_RECEIPT_V1'&&
      receipt.productionReady===false&&receipt.orderTransmission===false,'CHART_RECEIPT');
 need(Array.isArray(eligible)&&eligible.length>0&&eligible.length<=selected.length&&
      new Set(eligible).size===eligible.length&&eligible.every(s=>selected.includes(s))&&
      /^[a-f0-9]{64}$/.test(evidenceHash),'ELIGIBILITY_SCOPE');
 const allowed=new Set(eligible),keep=new Set(old.protectedChartSymbols);
 const {planSha256,...body}=structuredClone(old);
 body.scanChartSymbols=old.scanChartSymbols.filter(s=>allowed.has(s));
 body.allRequestedChartSymbols=old.allRequestedChartSymbols.filter(s=>keep.has(s)||allowed.has(s));
 body.selectorInputSymbols=selected.filter(s=>allowed.has(s));
 body.arkChartsUsed=body.allRequestedChartSymbols.length;
 body.totalChartFunctionsBudgeted=body.arkChartsUsed+body.occupiedByOtherChartFunctions;
 body.g1UnscannedCount=mask.observedPassSymbols.length-body.selectorInputSymbols.length;
 if(body.entryUniverseMode!==undefined){
  body.reviewedEntrySymbols=body.reviewedEntrySymbols.filter(s=>allowed.has(s));
  body.unreviewedG1SymbolsExcludedFromEntry=mask.observedPassSymbols.length-body.reviewedEntrySymbols.length;
 }
 body.automaticMasterScope={schemaId:'ARK_NO11_AUTOMATIC_MASTER_SCOPE_V1',
  parentPlanSha256:planSha256,sourceEvidenceSha256:evidenceHash,
  excludedFromEntry:selected.filter(s=>!allowed.has(s)),
  aiUsed:false,protectedChartsRetained:true,noReranking:true,orderTransmission:false};
 const plan={...body,planSha256:sha(JSON.stringify(body))};
 validateNo11Chart50Plan({chartPlan:plan,mask,sessionDate:old.sessionDate});
 need(old.protectedChartSymbols.every(s=>plan.allRequestedChartSymbols.includes(s)),'EXIT_CHART_REMOVED');
 return {...structuredClone(receipt),chartPlan:plan,automaticMasterScopeApplied:true,
         parentChartPlanSha256:planSha256,automaticMasterEvidenceSha256:evidenceHash};
}
export function main(args){
 need(args.length===4,'SCOPE_ARGUMENTS');
 const [chart,maskFile,eligibilityFile,outputDir]=args;
 const evidence=read(eligibilityFile),receipt=read(chart),mask=read(maskFile);
 need(evidence.schemaId==='ARK_NO11_AUTOMATIC_MASTER_ELIGIBILITY_V1'&&
      evidence.sessionDate===receipt.chartPlan.sessionDate&&
      evidence.parentChartPlanSha256===receipt.chartPlan.planSha256&&
      evidence.orderTransmission===false,'ELIGIBILITY_CONTRACT');
 const result=narrow(receipt,mask,evidence.eligibleSymbols,sha(fs.readFileSync(eligibilityFile)));
 const root=path.resolve(outputDir);
 need(root===path.dirname(path.resolve(chart))&&!fs.lstatSync(root).isSymbolicLink(),'SCOPED_CHART_DIRECTORY');
 const raw=Buffer.from(JSON.stringify(result)+'\n');
 const target=path.join(root,'no11-chart50-private-'+sha(raw).slice(0,16)+'.json');
 if(fs.existsSync(target))need(fs.readFileSync(target).equals(raw),'SCOPED_CHART_CHANGED');
 else fs.writeFileSync(target,raw,{flag:'wx'});
 console.log(target);
}
if(process.argv[1]&&import.meta.url===pathToFileURL(path.resolve(process.argv[1])).href){
 try{main(process.argv.slice(2))}catch(e){console.error(/^NO11_AUTO_MASTER_/.test(e.message)?e.message:'NO11_AUTO_MASTER_SCOPE_FAILED');process.exitCode=2}
}
