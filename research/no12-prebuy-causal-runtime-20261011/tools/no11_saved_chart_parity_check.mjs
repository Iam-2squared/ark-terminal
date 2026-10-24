import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {readNo11SavedChartEvidence} from '../runtime/no11_saved_chart_evidence_audit.mjs';
import {compareNo11SavedChartParity} from '../runtime/no11_saved_chart_parity.mjs';
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 try{
  const args=process.argv.slice(2);
  if(args.length!==2||args[0]!=='--evidence')throw Error('NO11_CHART_PARITY_CLI_USAGE');
  const audited=readNo11SavedChartEvidence({file:args[1]});
  const evidence=JSON.parse(fs.readFileSync(args[1],'utf8').replace(/^\uFEFF/,''));
  const r=compareNo11SavedChartParity({evidence});
  if(audited.localFileSha256!==
    (await import('node:crypto')).createHash('sha256').update(fs.readFileSync(args[1])).digest('hex'))
   throw Error('NO11_CHART_PARITY_FILE_CHANGED');
  console.log('NO11_CHART_PARITY=LOCAL_RESEARCH_ONLY');
  console.log('NO11_CHART_PARITY_FILE_SHA256='+audited.localFileSha256);
  for(const c of r.combinations){
   console.log('NO11_PARITY_'+c.oneMinuteLabel+'_'+c.fiveMinuteLabel+
    '_MATCHED='+c.matched+'_COMPARED='+c.completeGroupsCompared+
    '_MISMATCHED='+c.mismatched+'_UNMATCHED_5M='+c.unmatchedFive);
  }
  console.log('NO11_BAR_LABEL_SEMANTICS_CERTIFIED=False');
  console.log('NO11_NATIVE_STATE9_PARITY_CERTIFIED=False');
  console.log('NO11_PRODUCTION_READY=False');
  console.log('ORDER_TRANSMISSION=False');
 }catch(e){
  const reason=typeof e?.message==='string'&&/^NO11_[A-Z0-9_]+$/.test(e.message)?
   e.message:'NO11_CHART_PARITY_EVIDENCE_INVALID';
  console.error('NO11_CHART_PARITY=BLOCKED');
  console.error('NO11_CHART_PARITY_REASON='+reason);
  console.error('NO11_PRODUCTION_READY=False');
  console.error('ORDER_TRANSMISSION=False');
  process.exitCode=2;
 }
}
