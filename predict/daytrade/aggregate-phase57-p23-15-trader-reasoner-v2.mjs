import fs from 'node:fs';
import path from 'node:path';
import { P23_15_TRADER_REASONER_POLICY, PHASE57_P23_15_SAFETY, buildTraderReasoningDecision } from './phase57-p23-15-trader-reasoner-v2.js';

const inputDir=process.argv[2] ?? 'artifacts/p23-14-input';
const files=fs.readdirSync(inputDir).filter(n=>n.endsWith('.json')).sort();
if(!files.length) throw new Error('no P23.15 source shards');
const mean=a=>a.length?a.reduce((s,x)=>s+Number(x),0)/a.length:null;
function pf(xs){const g=xs.filter(x=>x>0).reduce((a,b)=>a+b,0);const l=-xs.filter(x=>x<0).reduce((a,b)=>a+b,0);return l>0?g/l:g>0?Infinity:null;}
function summarize(rows){
  const v=rows.filter(r=>Number.isFinite(Number(r.directionalReturnPct)));
  const gross=v.map(r=>Number(r.directionalReturnPct));
  const net=gross.map(x=>x-.05);
  return {count:v.length,hitRate:v.length?v.filter(r=>r.hit).length/v.length:null,averageDirectionalReturnPct:mean(gross),averageNetAfterCostPct:mean(net),profitFactor:pf(net),averageMfePct:mean(v.map(r=>Number(r.mfePct)).filter(Number.isFinite)),averageMaePct:mean(v.map(r=>Number(r.maePct)).filter(Number.isFinite)),averageTradeabilityScore:mean(v.map(r=>Number(r.tradeabilityScore)).filter(Number.isFinite))};
}
function group(rows,keyFn){const m=new Map();for(const r of rows){const k=keyFn(r);if(!m.has(k))m.set(k,[]);m.get(k).push(r);}return Object.fromEntries([...m].map(([k,v])=>[k,summarize(v)]));}

const source=[];const symbols=new Set();
for(const file of files){const p=JSON.parse(fs.readFileSync(path.join(inputDir,file),'utf8'));if(p.status!=='VISUAL_CHART_REASONING_DEVELOPMENT_MEASURED') throw new Error(`bad source ${file}`);for(const s of p.symbols??[])symbols.add(s);for(const r of p.records??[])source.push(r);}
const frozen=source.map(r=>buildTraderReasoningDecision(r));
for(const d of frozen){if(d.futureOutcomeVisible!==false||d.outcomeUsedForDecision!==false||d.thresholdSearchPerformed!==false)throw new Error('causal freeze violation');}
const outcomeMap=new Map(source.map(r=>[`${r.symbol}|${r.featureCutoff}|${r.setup}`,r.outcome60m??null]));
const evaluated=frozen.map(d=>{const o=outcomeMap.get(d.key);return {...d,hit:o?.hit??null,directionalReturnPct:o?.directionalReturnPct??null,mfePct:o?.mfePct??null,maePct:o?.maePct??null,outcomeJoinedAfterDecisionFreeze:true};}).filter(r=>Number.isFinite(Number(r.directionalReturnPct)));
const qualified=evaluated.filter(r=>r.decision==='QUALIFIED');
const wait=evaluated.filter(r=>r.decision==='WAIT');
const baseline=summarize(evaluated), selected=summarize(qualified);
const result={
  phase:'57.p23.15-trader-reasoner-v2',status:'TRADER_REASONER_V2_DEVELOPMENT_MEASURED',symbolCount:symbols.size,sourceShardCount:files.length,sourceRecordCount:source.length,evaluatedCount:evaluated.length,
  policy:P23_15_TRADER_REASONER_POLICY,
  aggregate:{all:baseline,qualified:selected,wait:summarize(wait),coverage:evaluated.length?qualified.length/evaluated.length:null,developmentDelta:{hitRate:selected.hitRate!=null&&baseline.hitRate!=null?selected.hitRate-baseline.hitRate:null,averageNetAfterCostPct:selected.averageNetAfterCostPct!=null&&baseline.averageNetAfterCostPct!=null?selected.averageNetAfterCostPct-baseline.averageNetAfterCostPct:null,profitFactor:selected.profitFactor!=null&&baseline.profitFactor!=null?selected.profitFactor-baseline.profitFactor:null}},
  byDecision:group(evaluated,r=>r.decision),
  byDirectionAndDecision:group(evaluated,r=>`${r.direction}|${r.decision}`),
  bySetupFamilyAndDecision:group(evaluated,r=>`${r.setupFamily}|${r.decision}`),
  byHigherTimeframeContextAndDecision:group(evaluated,r=>`${r.higherTimeframeContext}|${r.decision}`),
  methodology:{developmentUniverseOnly:true,p2314ResultsPreviouslyObserved:true,developmentHypothesisDerivedFromP2314:true,freshHoldoutConsumed:false,untouchedTemporalOos:false,causalVisualFieldsOnlyAtDecisionTime:true,predictionFrozenBeforeOutcomeJoin:true,outcomeJoinedAfterDecisionFreeze:true,thresholdSearchPerformed:false,externalVisionModelCalled:false,sameSession60mOutcomeEvaluation:true,transactionCostPct:.05,sourceReusedWithinSameWorkflow:true},
  edgeClaimAllowed:false,recommendationAllowed:false,transmitted:false,...PHASE57_P23_15_SAFETY,
};
for(const k of ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','overnightHoldingAllowed','transmitted']) if(result[k]!==false) throw new Error(`${k} must remain false`);
fs.mkdirSync('artifacts',{recursive:true});fs.writeFileSync('artifacts/phase57-p23-15-trader-reasoner-v2.json',JSON.stringify(result,null,2));console.log(JSON.stringify(result,null,2));
