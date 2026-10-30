// Offline-safe, READ ONLY bridge check of locally saved RssMarket seconds receipt.
// No price, broker, account, model coefficients or private path is printed.
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {readNo11LocalRssSecondsAsOf} from '../runtime/no11_rss_seconds_asof_adapter.mjs';
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 try{
  const args=process.argv.slice(2);
  if(args.length!==2||args[0]!=='--private-root')
   throw Error('NO11_RSS_SECONDS_ASOF_CLI_USAGE');
  const now=new Date();
  const result=readNo11LocalRssSecondsAsOf({
   privateRoot:args[1],now,decisionAt:now.toISOString()
  });
  if(result.status!=='LOCAL_RSS_SECONDS_ASOF_MARKET_SOURCE_ONLY'||
    result.productionReady!==false||result.orderTransmission!==false)
   throw Error('NO11_RSS_SECONDS_ASOF_RESULT_UNSAFE');
  console.log('NO11_RSS_SECONDS_ASOF_STATUS='+result.status);
  console.log('NO11_RSS_SECONDS_ASOF_SOURCE_AGE_MS='+result.marketSourceFreshnessMs);
  console.log('NO11_NATIVE_SELECTOR_CONNECTED=False');
  console.log('NO11_NATIVE_H2H3H5_EXECUTED=False');
  console.log('NO11_PRODUCTION_READY=False');
  console.log('ORDER_TRANSMISSION=False');
 }catch{
  console.error('NO11_RSS_SECONDS_ASOF_STATUS=BLOCKED');
  console.error('NO11_PRODUCTION_READY=False');
  console.error('ORDER_TRANSMISSION=False');
  process.exitCode=2;
 }
}
