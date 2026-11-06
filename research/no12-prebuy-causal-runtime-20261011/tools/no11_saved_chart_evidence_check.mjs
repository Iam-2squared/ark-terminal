import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {readNo11SavedChartEvidence} from '../runtime/no11_saved_chart_evidence_audit.mjs';
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 try{
  const a=process.argv.slice(2);
  if(a.length!==2||a[0]!=='--evidence')throw Error('NO11_CHART_AUDIT_CLI_USAGE');
  const r=readNo11SavedChartEvidence({file:a[1]});
  console.log('NO11_CHART_EVIDENCE_AUDIT=PASS_MARKET_ONLY');
  console.log('NO11_CHART_EVIDENCE_SHA256='+r.localFileSha256);
  for(const p of ['1M','5M']){
   const v=r.periods[p];
   console.log('NO11_CHART_'+p+'_OBSERVED_ROWS='+v.observedRows);
   console.log('NO11_CHART_'+p+'_CONSERVATIVE_CLOSED='+v.conservativelyClosedRows);
   console.log('NO11_CHART_'+p+'_NOT_CONSERVATIVE_CLOSED='+v.notConservativelyClosedRows);
   console.log('NO11_CHART_'+p+'_SESSIONS='+v.observedSessions);
  }
  console.log('NO11_CHART_BAR_LABEL_CERTIFIED=False');
  console.log('NO11_CHART_MISSING_BARS_CERTIFIED=False');
  console.log('NO11_FROZEN_STATE9_CONNECTED=False');
  console.log('NO11_PRODUCTION_READY=False');
  console.log('ORDER_TRANSMISSION=False');
 }catch(e){
  const safe=typeof e?.message==='string'&&/^NO11_[A-Z0-9_]+$/.test(e.message)?e.message:'NO11_CHART_EVIDENCE_UNREADABLE';
  console.error('NO11_CHART_EVIDENCE_AUDIT=BLOCKED');
  console.error('NO11_CHART_EVIDENCE_REASON='+safe);
  console.error('NO11_PRODUCTION_READY=False');
  console.error('ORDER_TRANSMISSION=False');
  process.exitCode=2;
 }
}
