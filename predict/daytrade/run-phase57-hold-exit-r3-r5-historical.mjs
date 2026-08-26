import fs from 'node:fs';
import {enrichHistoricalIntradayBars} from './phase57-intraday-multifactor.js';
import {buildMultiHorizonMagnitudeRows} from './phase57-adaptive-horizon-magnitude.js';
import {buildIntradayHorizonDatasets,evaluateNestedAdaptiveHorizon} from './phase57-nested-adaptive-horizon.js';
import {replayNestedAdaptiveOosSignals} from './phase57-adaptive-oos-signal-replay.js';
import {runHoldExitHistoricalWalkForward,R3_R5_SAFETY} from './phase57-hold-exit-r3-r5-walkforward.js';
import {PHASE57_P25_2K_POLICY} from './phase57-p25-2k-pinned-history-bridge.js';

const packPath=process.env.PHASE57_PINNED_HISTORY_PACK||'/tmp/p25-pinned-history-pack.json';
const pack=JSON.parse(fs.readFileSync(packPath,'utf8'));
if(pack?.status!=='P25_2_PINNED_HISTORY_PACK_READY')throw Error('verified pinned history pack required');
if(pack?.canonicalSourceRunId!==PHASE57_P25_2K_POLICY.canonicalSourceRunId)throw Error('canonical source mismatch');
if(pack?.canonicalSnapshotSha256!==PHASE57_P25_2K_POLICY.canonicalSnapshotSha256)throw Error('canonical snapshot mismatch');
if(pack?.methodology?.p24CanonicalByteSnapshotOnly!==true||pack?.methodology?.pinnedSnapshotIdentityVerified!==true)throw Error('canonical byte snapshot attestation missing');

const symbols=[...PHASE57_P25_2K_POLICY.historicalUniverse],horizons=[1,3,6,12,24];
function featureRows(symbol,date,bars,enriched,base){const idx=new Map(bars.map((b,i)=>[new Date(b.timestamp).toISOString(),i])),en=new Map(enriched.map(b=>[new Date(b.timestamp).toISOString(),b])),open0=+bars[0]?.open||0;return base.flatMap(r=>{const ts=new Date(r.featureCutoff).toISOString(),i=idx.get(ts),cur=i===undefined?null:bars[i],eb=en.get(ts);if(!cur||!eb)return[];const prev=i>0?bars[i-1]:cur,pv=bars.slice(Math.max(0,i-5),i).map(b=>+b.volume||0),av=pv.length?pv.reduce((a,b)=>a+b,0)/pv.length:0;return[{symbol,sessionDate:date,featureCutoff:r.featureCutoff,features:{returnFromOpen:open0?(+cur.close/open0-1)*100:0,rangePosition:+cur.high>+cur.low?(+cur.close-+cur.low)/(+cur.high-+cur.low):.5,shortMomentum:+prev.close?(+cur.close/+prev.close-1)*100:0,relativeVolume:av>0?(+cur.volume||0)/av:1,...(eb.multiFactor||{})}}];});}
const datasets=Object.fromEntries(horizons.map(h=>[h,[]])),store=new Map();let rawBars=0;
for(const session of pack.sessions||[]){if(!symbols.includes(session.symbol))continue;const sb=(session.bars5m||[]).map(b=>({...b,sessionDate:session.sessionDate})).sort((a,b)=>a.timestamp.localeCompare(b.timestamp));if(sb.length<30)continue;rawBars+=sb.length;const enriched=enrichHistoricalIntradayBars(sb),base=buildMultiHorizonMagnitudeRows({symbol:session.symbol,sessionDate:session.sessionDate,bars:sb,horizons}),fr=featureRows(session.symbol,session.sessionDate,sb,enriched,base),ds=buildIntradayHorizonDatasets(base,{horizons,featureRows:fr});for(const h of horizons)datasets[h].push(...(ds[h]||[]));store.set(`${session.symbol}|${session.sessionDate}`,{bars:sb,index:new Map(sb.map((b,i)=>[new Date(b.timestamp).toISOString(),i]))});}
for(const h of horizons)datasets[h].sort((a,b)=>a.featureCutoff.localeCompare(b.featureCutoff));
const opts={outerTrainFraction:.6,outerTestFraction:.1,outerMinTrainRows:500,innerTrainFraction:.6,innerTestFraction:.15,innerMinTrainRows:200,thresholds:[.55,.60,.65],minInnerSignals:50,minimumInnerNetReturnPct:0,roundTripCostPct:.05};
const adaptive=evaluateNestedAdaptiveHorizon(datasets,opts),replay=replayNestedAdaptiveOosSignals(datasets,{...opts,referenceResult:adaptive});
if(replay.reconciliation&&!replay.reconciliation.matches)throw Error('signal replay mismatch');
const rowKey=r=>`${r?.symbol??''}|${r?.sessionDate??''}|${r?.featureCutoff??''}`,lookup=new Map();for(const h of horizons)for(const r of datasets[h])lookup.set(`${h}|${rowKey(r)}`,r);
const rows=[];for(const s of replay.signals){const src=lookup.get(`${s.horizonBars}|${rowKey(s)}`),st=store.get(`${s.symbol}|${s.sessionDate}`),i=st?.index.get(new Date(s.featureCutoff).toISOString());if(!src||!st||i===undefined)continue;const futureBars=st.bars.slice(i+1);if(!futureBars.length)continue;rows.push({entryAccepted:true,pointInTimeValid:true,entryBand:'FROZEN_NESTED_ADAPTIVE_OOS',symbol:s.symbol,sessionDate:s.sessionDate,setup:s.selectedFeatureFamily??null,entryTimestamp:s.featureCutoff,entryPrice:+src.entryPrice,signalDirection:+s.direction,baseHorizonBars:+s.horizonBars,contextBars:st.bars.slice(Math.max(0,i-12),i+1),futureBars});}
rows.sort((a,b)=>a.entryTimestamp.localeCompare(b.entryTimestamp));
const result=runHoldExitHistoricalWalkForward(rows,{minTrainSessions:4,validationSessions:2,testSessions:2});
if(result.outerOos.foldCount===0)throw Error(`zero folds from ${result.sessionCount} OOS entry sessions`);
const artifact={phase:'57.r3-r5',status:'HISTORICAL_HOLD_EXIT_WALK_FORWARD_MEASURED',source:'P24.9 canonical byte-frozen 5m snapshot only',canonicalSourceRunId:pack.canonicalSourceRunId,canonicalSnapshotSha256:pack.canonicalSnapshotSha256,dataWindow:{days:PHASE57_P25_2K_POLICY.canonicalWindowDays,endExclusive:PHASE57_P25_2K_POLICY.canonicalDataEndIso},symbols,rawBars,frozenEntryRows:rows.length,entrySource:'P21 nested adaptive OOS replay from canonical byte-frozen history',policy:'HOLD default -> PROTECT -> persistent deterioration EXIT; FIXED fallback when dev/validation do not both beat Fixed',result,limitations:['No order book/tick reconstruction','Current 2026-08-19..25 P25 evidence excluded from tuning and selection','Outer OOS is historical byte-frozen research, not the untouched prospective holdout'],safety:R3_R5_SAFETY};
fs.mkdirSync('artifacts',{recursive:true});fs.writeFileSync('artifacts/phase57-hold-exit-r3-r5-historical.json',JSON.stringify(artifact,null,2));console.log('R3_R5_JSON_START');console.log(JSON.stringify(artifact,null,2));console.log('R3_R5_JSON_END');
