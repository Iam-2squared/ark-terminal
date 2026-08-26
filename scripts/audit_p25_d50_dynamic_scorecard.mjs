import fs from 'node:fs';

const file=process.argv[2];
if(!file){console.error('usage: node scripts/audit_p25_d50_dynamic_scorecard.mjs <scorecard.json>');process.exit(2);}
const x=JSON.parse(fs.readFileSync(file,'utf8'));
const d50=x?.byVariant?.DYNAMIC_50;
const all=x?.summary;
const fail=message=>{throw new Error(`DYNAMIC_50 paired audit failed: ${message}`);};
if(!d50||!all)fail('missing DYNAMIC_50 or summary');
if(Number(d50.pairedCount)!==Number(all.pairedCount))fail(`pairedCount mismatch d50=${d50.pairedCount} all=${all.pairedCount}`);
if(Number(d50.fixed?.n)!==Number(all.fixed?.n)||Number(d50.dynamic?.n)!==Number(all.dynamic?.n))fail('DYNAMIC_50 sample is not the full paired sample');
for(const key of ['netReturnPct','profitFactor','maxDrawdownPct','winRate']){
  const a=Number(d50.fixed?.[key]),b=Number(all.fixed?.[key]);
  if(!(Number.isFinite(a)&&Number.isFinite(b)&&Math.abs(a-b)<=1e-12))fail(`fixed ${key} mismatch`);
  const c=Number(d50.dynamic?.[key]),d=Number(all.dynamic?.[key]);
  if(!(Number.isFinite(c)&&Number.isFinite(d)&&Math.abs(c-d)<=1e-12))fail(`dynamic ${key} mismatch`);
}
const safety=x?.safety??{};
for(const key of ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted','freshHoldoutConsumed']){
  if(safety[key]!==false)fail(`safety.${key} must be false`);
}
const out={status:'EXACT_DYNAMIC_50_PAIRED_AUDIT_OK',pairedCount:d50.pairedCount,fixed:d50.fixed,dynamic:d50.dynamic,delta:d50.delta,lineageManifestHeadSha256:x.lineageManifestHeadSha256,safety};
console.log(JSON.stringify(out,null,2));
