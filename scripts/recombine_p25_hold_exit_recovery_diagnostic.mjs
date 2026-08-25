import fs from 'node:fs';
import path from 'node:path';

const arg=(name,fallback=null)=>{const i=process.argv.indexOf(name);return i>=0&&i+1<process.argv.length?process.argv[i+1]:fallback;};
const dir=arg('--shard-dir'),output=arg('--output','/tmp/p25-hold-exit-recovery-combined.json');
if(!dir)throw new Error('missing --shard-dir');
const files=fs.readdirSync(dir).filter(x=>x.endsWith('.json')).sort();
if(!files.length)throw new Error('no diagnostic shards');
const shards=files.map(f=>JSON.parse(fs.readFileSync(path.join(dir,f),'utf8'))).sort((a,b)=>String(a.sessionDate).localeCompare(String(b.sessionDate)));
const lineage=[...new Set(shards.map(x=>x.lineageManifestHeadSha256))];if(lineage.length!==1)throw new Error('lineage mismatch');
const pairs=shards.flatMap(x=>x.diagnostic?.pairs??[]).sort((a,b)=>String(a.key).localeCompare(String(b.key)));
const mean=xs=>xs.length?xs.reduce((a,b)=>a+b,0)/xs.length:null;
const median=xs=>{if(!xs.length)return null;const s=[...xs].sort((a,b)=>a-b),m=Math.floor(s.length/2);return s.length%2?s[m]:(s[m-1]+s[m])/2;};
function pf(xs){const gp=xs.filter(x=>x>0).reduce((a,b)=>a+b,0),gl=-xs.filter(x=>x<0).reduce((a,b)=>a+b,0);return gl>0?gp/gl:(gp>0?Infinity:null);}
function dd(xs){let eq=1,peak=1,max=0;for(const r of xs){eq*=1+r/100;peak=Math.max(peak,eq);max=Math.max(max,(peak-eq)/peak*100);}return max;}
function summarize(key){const rs=pairs.map(x=>Number(x?.[key]?.netReturnPct)).filter(Number.isFinite);let eq=1;for(const r of rs)eq*=1+r/100;return{n:rs.length,netReturnPct:(eq-1)*100,meanNetReturnPct:mean(rs),medianNetReturnPct:median(rs),winRate:rs.length?rs.filter(x=>x>0).length/rs.length:null,profitFactor:pf(rs),maxDrawdownPct:dd(rs)};}
const exitReasons={};for(const p of pairs){const k=String(p.currentFull?.exitReason??'UNKNOWN');(exitReasons[k]??=[]).push(p);}
const attribution=Object.fromEntries(Object.entries(exitReasons).map(([k,v])=>[k,{n:v.length,meanDeltaCurrentVsFixed:mean(v.map(x=>Number(x.deltaCurrentVsFixed))),meanDeltaLegacyVsFixed:mean(v.map(x=>Number(x.deltaLegacyVsFixed))),meanBarsDeltaCurrent:mean(v.map(x=>Number(x.currentFull?.barsHeld)-Number(x.fixed?.barsHeld))),meanGivebackPct:mean(v.map(x=>Number(x.currentFull?.givebackPct)).filter(Number.isFinite)),meanCaptureRatio:mean(v.map(x=>Number(x.currentFull?.captureRatio)).filter(Number.isFinite))}]));
const harm=pairs.filter(x=>x.classification==='CURRENT_FULL_HARM_LEGACY_PRESERVED').length;
const out={schemaVersion:1,phase:'57.p25.recovery.r1-r2.combined',status:'HOLD_EXIT_RECOVERY_COMBINED_READY',lineageManifestHeadSha256:lineage[0],sessions:shards.map(x=>({sessionDate:x.sessionDate,frozenTradeCount:x.frozenTradeCount,fixedResolvedCount:x.fixedResolvedCount,pairedCount:x.pairedCount})),pairedCount:pairs.length,summary:{fixed:summarize('fixed'),legacySelective:summarize('legacySelective'),currentFull:summarize('currentFull')},diagnosis:{currentFullHarmLegacyPreservedCount:harm,currentFullBetterCount:pairs.filter(x=>Number(x.deltaCurrentVsFixed)>0).length,currentFullWorseCount:pairs.filter(x=>Number(x.deltaCurrentVsFixed)<0).length,equalCount:pairs.filter(x=>Number(x.deltaCurrentVsFixed)===0).length,attribution},pairs,limitations:[...new Set(shards.flatMap(x=>x.diagnostic?.limitations??[]))],methodology:{sameFiveSessionFrozenEvidence:true,p247NonRiskFallbackExact:true,p2350DynamicRiskExactReplay:false,noParameterRetuning:true,winnerSelection:false,freshHoldoutConsumed:false},safety:shards[0].safety};
for(const k of ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted','freshHoldoutConsumed'])if(out.safety?.[k]!==false)throw new Error(`safety ${k}`);
fs.writeFileSync(output,JSON.stringify(out,null,2)+'\n');console.log(JSON.stringify({status:out.status,pairedCount:out.pairedCount,summary:out.summary,diagnosis:out.diagnosis,limitations:out.limitations},null,2));
