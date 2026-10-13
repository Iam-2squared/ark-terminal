import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {auditNo11State9InputBoundary} from '../runtime/no11_state9_rss_input_boundary.mjs';
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 try{
  const a=process.argv.slice(2);
  if(a.length!==2||a[0]!=='--evidence')throw Error('NO11_STATE9_BOUNDARY_USAGE');
  const r=auditNo11State9InputBoundary({file:a[1]});
  console.log('NO11_STATE9_INPUT_BOUNDARY=MARKET_DATA_AUDITED_NOT_CONNECTED');
  console.log('NO11_EVIDENCE_SHA256='+r.evidenceSha256);
  console.log('NO11_1M_5M_PARITY_MATCHED='+r.observedParity.matched);
  console.log('NO11_1M_5M_PARITY_COMPARED='+r.observedParity.compared);
  for(const period of ['1M','5M']){
   console.log('NO11_'+period+'_OBSERVED_GAP_COUNT='+r.periods[period].observedIntraSessionGapCount);
  }
  for(const b of r.blockers)console.log('NO11_STATE9_BLOCKER='+b);
  console.log('NO11_NATIVE_STATE9_CONNECTED=False');
  console.log('NO11_PRODUCTION_READY=False');
  console.log('ORDER_TRANSMISSION=False');
 }catch(e){
  console.error('NO11_STATE9_INPUT_BOUNDARY=BLOCKED');
  console.error('NO11_PRODUCTION_READY=False');
  console.error('ORDER_TRANSMISSION=False');
  process.exitCode=2;
 }
}
