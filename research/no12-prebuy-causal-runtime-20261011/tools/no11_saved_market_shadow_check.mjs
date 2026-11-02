/**
 * Read ONLY the local market_shadow_v2.json from the already tested Windows
 * RSS watcher. No broker, no Excel, no orders, no Frozen model execution.
 */
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {readSavedNo11MarketShadow} from '../runtime/no11_saved_market_shadow_bridge.mjs';
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 try{
  const a=process.argv.slice(2);
  if(a.length!==2||a[0]!=='--market-json')throw Error('NO11_MARKET_SHADOW_CLI_USAGE');
  const result=readSavedNo11MarketShadow({file:a[1]});
  if(result.status!=='LOCAL_MARKET_ASOF_ONLY_NO_DECISION'||
     result.productionReady!==false||result.orderTransmission!==false)
   throw Error('NO11_MARKET_SHADOW_RESULT_UNSAFE');
  console.log('NO11_SAVED_RSS_MARKET_ASOF=PASS_MARKET_ONLY');
  console.log('NO11_MARKET_LOCAL_SHA256='+result.localSnapshotSha256);
  console.log('NO11_FROZEN_SELECTOR_EXECUTED=False');
  console.log('NO11_FROZEN_DECISION_ENGINE_CONNECTED=False');
  console.log('NO11_PRODUCTION_READY=False');
  console.log('ORDER_TRANSMISSION=False');
 }catch(e){
  const safe=typeof e?.message==='string'&&/^NO11_[A-Z0-9_]+$/.test(e.message)?e.message:'NO11_MARKET_SHADOW_INVALID_OR_UNREADABLE';
  console.error('NO11_SAVED_RSS_MARKET_ASOF=BLOCKED');
  console.error('NO11_MARKET_REASON='+safe);
  console.error('NO11_PRODUCTION_READY=False');
  console.error('ORDER_TRANSMISSION=False');
  process.exitCode=2;
 }
}
