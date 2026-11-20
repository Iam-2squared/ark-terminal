// Local-only first-observed chart receipt; never a BUY/SELL signal or live authority.
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {recordNo12MarketFirstSeen} from '../runtime/market_first_seen_journal.mjs';
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 try{
  const a=process.argv.slice(2);
  if(a.length!==2||a[0]!=='--private-root')throw Error('NO12_FIRST_SEEN_USAGE');
  const x=recordNo12MarketFirstSeen({privateRoot:a[1]});
  console.log('NO12_FIRST_SEEN_STATUS='+x.status);
  console.log('NO12_FIRST_SEEN_CONTINUITY='+x.continuity);
  console.log('NO12_FIRST_SEEN_EVENT_COUNT='+x.eventCount);
  console.log('BROKER_ARRIVAL_CERTIFIED=False');
  console.log('PRODUCTION_READY=False');
  console.log('ORDER_TRANSMISSION=False');
 }catch{
  console.error('NO12_FIRST_SEEN_STATUS=BLOCKED');
  console.error('PRODUCTION_READY=False');
  console.error('ORDER_TRANSMISSION=False');
  process.exitCode=2;
 }
}
