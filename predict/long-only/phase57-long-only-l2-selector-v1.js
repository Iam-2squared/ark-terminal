import {createHash} from 'node:crypto';

export const L2_FEATURE_FAMILIES=Object.freeze({
  RETURN_MOMENTUM:Object.freeze(['currentReturnPct','momentum30Pct']),
  VWAP:Object.freeze(['vwapDistancePct','vwapSlope15Pct']),
  VOLUME:Object.freeze(['logCumulativeTurnover','volumeAccelerationRatio']),
  TREND_RANGE:Object.freeze(['trendEfficiency','rangeExpansionPct']),
  GAP_VOLATILITY:Object.freeze(['gapPct','decisionVolatilityPct','causalAtrPct']),
  TIME:Object.freeze(['timeOfDayFraction']),
  MARKET_LIQUIDITY:Object.freeze(['segmentStandard','segmentGrowth','liquidityLow','liquidityHigh']),
  BREADTH:Object.freeze(['marketBreadthPositivePct','sectorBreadthPositivePct']),
});
export const L2_FEATURES=Object.freeze(Object.values(L2_FEATURE_FAMILIES).flat());
export const L2_SELECTOR_CONTRACT=Object.freeze({
  contractId:'PHASE57_LONG_ONLY_FIXED_HORIZON_RIDGE_V1',
  fitPartition:'DEVELOPMENT_C',selectionPartition:'DEVELOPMENT_D',
  candidates:Object.freeze(['RIDGE_Y30','RIDGE_Y60','RIDGE_TWO_HEAD_30']),
  topNCandidates:Object.freeze([5,10,20]),
  ridgeLambda:0.1,downsidePenaltyLambda:0.5,
  selectionObjective:'MEAN_RETURN_BPS_MINUS_0_5_MAE_BPS_MINUS_0_25_SESSION_RETURN_STD_BPS',
  finalRefitPartitions:Object.freeze(['DEVELOPMENT_C','DEVELOPMENT_D']),
  validationMayTune:false,oosMayTune:false,
});

const forbidden=/winner|future|remaining|mfe|mae|target|label|outcome/i;
const sha=value=>createHash('sha256').update(JSON.stringify(value)).digest('hex');
const round=x=>Number.isFinite(x)?Number(x.toFixed(8)):x;
const mean=xs=>xs.length?xs.reduce((a,x)=>a+x,0)/xs.length:null;
const median=xs=>{if(!xs.length)return null;const a=[...xs].sort((x,y)=>x-y),m=Math.floor(a.length/2);return a.length%2?a[m]:(a[m-1]+a[m])/2;};
const std=xs=>{const m=mean(xs);return xs.length?Math.sqrt(mean(xs.map(x=>(x-m)**2))):null;};
const key=row=>`${row.sessionDate}|${row.symbol}|${row.decisionTimeJst}`;
const finite=x=>Number.isFinite(Number(x));

export function projectL2Features(row={}){
  if(Object.keys(row).some(name=>forbidden.test(name)))throw new Error('evaluator outcome reached L2 feature projection');
  const [hour,minute]=String(row.decisionTimeJst??'').split(':').map(Number),current=Number(row.currentPrice),segment=String(row.segment),liquidity=String(row.liquidityBucket);
  const x={
    currentReturnPct:Number(row.currentReturnPct),momentum30Pct:Number(row.momentum30Pct),
    vwapDistancePct:Number(row.vwapDistancePct),vwapSlope15Pct:Number(row.vwapSlope15Pct),
    logCumulativeTurnover:Math.log1p(Math.max(0,Number(row.cumulativeTurnover))),volumeAccelerationRatio:Number(row.volumeAccelerationRatio),
    trendEfficiency:Number(row.trendEfficiency),rangeExpansionPct:Number(row.rangeExpansionPct),
    gapPct:Number(row.gapPct),decisionVolatilityPct:Number(row.decisionVolatilityPct),causalAtrPct:current>0?100*Number(row.causalAtr)/current:NaN,
    timeOfDayFraction:((hour*60+minute)-570)/330,
    segmentStandard:segment==='STANDARD'?1:0,segmentGrowth:segment==='GROWTH'?1:0,
    liquidityLow:liquidity==='LOW'?1:0,liquidityHigh:liquidity==='HIGH'?1:0,
    marketBreadthPositivePct:Number(row.marketBreadthPositivePct),sectorBreadthPositivePct:Number(row.sectorBreadthPositivePct),
  };
  if(!L2_FEATURES.every(name=>finite(x[name])))throw new Error('complete finite causal L2 features are required');
  return x;
}

function solve(matrix,vector){
  const n=vector.length,a=matrix.map((row,i)=>[...row,vector[i]]);
  for(let col=0;col<n;col++){
    let pivot=col;for(let row=col+1;row<n;row++)if(Math.abs(a[row][col])>Math.abs(a[pivot][col]))pivot=row;
    [a[col],a[pivot]]=[a[pivot],a[col]];if(Math.abs(a[col][col])<1e-10)a[col][col]=1e-10;
    const d=a[col][col];for(let j=col;j<=n;j++)a[col][j]/=d;
    for(let row=0;row<n;row++){if(row===col)continue;const f=a[row][col];for(let j=col;j<=n;j++)a[row][j]-=f*a[col][j];}
  }
  return a.map(row=>row[n]);
}

const targetFor=(row,name)=>{
  if(name==='Y30')return row.y30Bps===null||row.y30Bps===undefined?NaN:Number(row.y30Bps);
  if(name==='Y60')return row.y60Bps===null||row.y60Bps===undefined?NaN:Number(row.y60Bps);
  if(name==='UP30')return row.futureMfe30Pct===null||row.futureMfe30Pct===undefined?NaN:100*Math.max(0,Number(row.futureMfe30Pct));
  if(name==='DOWN30')return row.futureMae30Pct===null||row.futureMae30Pct===undefined?NaN:100*Math.max(0,-Number(row.futureMae30Pct));
  return NaN;
};

export function fitRidgeHead({featureRows=[],targetRows=[],targetName,lambda=L2_SELECTOR_CONTRACT.ridgeLambda,featureNames=L2_FEATURES}={}){
  const targets=new Map(targetRows.map(row=>[key(row),row])),samples=[];
  for(const row of featureRows){const target=targets.get(key(row)),y=targetFor(target??{},targetName);if(Number.isFinite(y))samples.push({x:projectL2Features(row),y});}
  if(samples.length<featureNames.length+2)throw new Error('insufficient L2 training rows');
  const means=featureNames.map(name=>mean(samples.map(s=>s.x[name])));
  const scales=featureNames.map((name,i)=>Math.sqrt(mean(samples.map(s=>(s.x[name]-means[i])**2)))||1);
  const p=featureNames.length+1,xtx=Array.from({length:p},()=>Array(p).fill(0)),xty=Array(p).fill(0);
  for(const sample of samples){
    const z=[1,...featureNames.map((name,i)=>(sample.x[name]-means[i])/scales[i])];
    for(let i=0;i<p;i++){xty[i]+=z[i]*sample.y;for(let j=0;j<p;j++)xtx[i][j]+=z[i]*z[j];}
  }
  for(let i=1;i<p;i++)xtx[i][i]+=Number(lambda)*samples.length;
  const coefficients=solve(xtx,xty),core={contractId:L2_SELECTOR_CONTRACT.contractId,targetName,featureNames,means,scales,intercept:coefficients[0],weights:coefficients.slice(1),lambda:Number(lambda),trainingRows:samples.length};
  return Object.freeze({...core,artifactSha256:sha(core)});
}

export function fitL2Candidate({candidateId,featureRows,targetRows,featureNames=L2_FEATURES}={}){
  if(!L2_SELECTOR_CONTRACT.candidates.includes(candidateId))throw new Error('candidate outside frozen L2 set');
  const heads=candidateId==='RIDGE_Y30'?[fitRidgeHead({featureRows,targetRows,targetName:'Y30',featureNames})]:candidateId==='RIDGE_Y60'?[fitRidgeHead({featureRows,targetRows,targetName:'Y60',featureNames})]:[fitRidgeHead({featureRows,targetRows,targetName:'UP30',featureNames}),fitRidgeHead({featureRows,targetRows,targetName:'DOWN30',featureNames})];
  const core={contractId:L2_SELECTOR_CONTRACT.contractId,candidateId,heads,downsidePenaltyLambda:L2_SELECTOR_CONTRACT.downsidePenaltyLambda};
  return Object.freeze({...core,artifactSha256:sha(core)});
}

const scoreHead=(row,head)=>{
  const x=projectL2Features(row);
  return head.intercept+head.featureNames.reduce((s,name,i)=>s+head.weights[i]*(x[name]-head.means[i])/head.scales[i],0);
};
export function scoreL2Candidate(row,artifact){
  const core=Object.fromEntries(Object.entries(artifact??{}).filter(([name])=>name!=='artifactSha256'));
  if(artifact?.contractId!==L2_SELECTOR_CONTRACT.contractId||artifact.artifactSha256!==sha(core))throw new Error('L2 artifact contract mismatch');
  if(artifact.candidateId==='RIDGE_TWO_HEAD_30')return scoreHead(row,artifact.heads[0])-artifact.downsidePenaltyLambda*scoreHead(row,artifact.heads[1]);
  return scoreHead(row,artifact.heads[0]);
}

export function selectRanked({featureRows=[],artifact,topN}={}){
  if(!L2_SELECTOR_CONTRACT.topNCandidates.includes(topN))throw new Error('topN outside frozen L2 selection set');
  const groups=new Map();
  for(const row of featureRows){const k=`${row.sessionDate}|${row.decisionTimeJst}`;if(!groups.has(k))groups.set(k,[]);groups.get(k).push(row);}
  const selected=[];
  for(const rows of groups.values())selected.push(...rows.map(row=>({row,score:scoreL2Candidate(row,artifact)})).sort((a,b)=>b.score-a.score||a.row.symbol.localeCompare(b.row.symbol)).slice(0,topN).map((x,i)=>({...x.row,selectorScore:round(x.score),selectorRank:i+1})));
  return selected;
}

function summarize(selected,targetRows,horizon){
  const targets=new Map(targetRows.map(row=>[key(row),row])),joined=selected.map(row=>({feature:row,target:targets.get(key(row))})).filter(x=>Number.isFinite(horizon===6?x.target?.y30Bps:x.target?.y60Bps));
  const y=joined.map(x=>horizon===6?x.target.y30Bps:x.target.y60Bps),mfe=joined.map(x=>horizon===6?x.target.futureMfe30Pct:x.target.futureMfe60Pct),mae=joined.map(x=>horizon===6?x.target.futureMae30Pct:x.target.futureMae60Pct);
  const sessions=[...new Set(joined.map(x=>x.feature.sessionDate))],sessionMeans=sessions.map(date=>mean(joined.filter(x=>x.feature.sessionDate===date).map(x=>horizon===6?x.target.y30Bps:x.target.y60Bps)));
  const totalWinners=targetRows.filter(row=>row.winner&&Number.isFinite(horizon===6?row.y30Bps:row.y60Bps)).length,selectedWinners=joined.filter(x=>x.target.winner).length;
  return {selected:joined.length,sessionCount:sessions.length,meanReturnBps:round(mean(y)),medianReturnBps:round(median(y)),positiveRatePct:round(100*y.filter(v=>v>0).length/y.length),meanFutureMfePct:round(mean(mfe)),meanFutureMaePct:round(mean(mae)),winnerPrecisionPct:round(100*selectedWinners/joined.length),winnerRecallPct:round(100*selectedWinners/totalWinners),positiveSessionRatePct:round(100*sessionMeans.filter(v=>v>0).length/sessionMeans.length),sessionMeanReturnStdBps:round(std(sessionMeans)),selectionObjective:round(mean(y)-0.5*Math.abs(100*mean(mae))-0.25*std(sessionMeans))};
}

export function evaluateSelection({selected,targetRows,horizon}={}){
  const overall=summarize(selected,targetRows,horizon),group=(field,values)=>Object.fromEntries(values.map(value=>[value,summarize(selected.filter(row=>(row[field]??'UNKNOWN')===value),targetRows,horizon)]));
  return Object.freeze({...overall,byTime:group('decisionTimeJst',[...new Set(selected.map(x=>x.decisionTimeJst))].sort()),byMarket:group('segment',['PRIME','STANDARD','GROWTH']),byLiquidity:group('liquidityBucket',['LOW','MID','HIGH']),byGap:group('gapBucket',['NON_GAP','GAP_UP'])});
}

export function rankBaseline({featureRows=[],topN,mode='MOMENTUM'}={}){
  const groups=new Map(),hashScore=row=>parseInt(sha(key(row)).slice(0,12),16);
  for(const row of featureRows){const k=`${row.sessionDate}|${row.decisionTimeJst}`;if(!groups.has(k))groups.set(k,[]);groups.get(k).push(row);}
  const out=[];for(const rows of groups.values())out.push(...[...rows].sort((a,b)=>mode==='RANDOM'?hashScore(b)-hashScore(a):Number(b.momentum30Pct)-Number(a.momentum30Pct)||a.symbol.localeCompare(b.symbol)).slice(0,topN));
  return out;
}

export function permuteTargets(targetRows=[]){
  const values=targetRows.map(row=>({y30Bps:row.y30Bps,y60Bps:row.y60Bps,futureMfe30Pct:row.futureMfe30Pct,futureMae30Pct:row.futureMae30Pct}));
  return targetRows.map((row,i)=>Object.freeze({...row,...values[(i*104729+17)%values.length]}));
}

export function runFeatureFamilyAblation({fitFeatures=[],fitTargets=[],evaluationFeatures=[],evaluationTargets=[],topN=10}={}){
  const variants=[['ALL',L2_FEATURES],...Object.entries(L2_FEATURE_FAMILIES).map(([family,names])=>[`WITHOUT_${family}`,L2_FEATURES.filter(name=>!names.includes(name))])];
  return Object.freeze(variants.map(([variant,featureNames])=>{
    const artifact=fitL2Candidate({candidateId:'RIDGE_Y30',featureRows:fitFeatures,targetRows:fitTargets,featureNames});
    const metrics=evaluateSelection({selected:selectRanked({featureRows:evaluationFeatures,artifact,topN}),targetRows:evaluationTargets,horizon:6});
    return Object.freeze({variant,featureNames,metrics,artifactSha256:artifact.artifactSha256});
  }));
}

export function chooseFeatureSetFromAblation(ablations=[]){
  const all=ablations.find(row=>row.variant==='ALL');if(!all)throw new Error('ALL feature ablation result is required');
  const eligible=ablations.filter(row=>row.variant==='ALL'||(row.metrics.selectionObjective>all.metrics.selectionObjective&&row.metrics.positiveSessionRatePct>=all.metrics.positiveSessionRatePct));
  return [...eligible].sort((a,b)=>b.metrics.selectionObjective-a.metrics.selectionObjective||b.metrics.positiveSessionRatePct-a.metrics.positiveSessionRatePct||a.featureNames.length-b.featureNames.length||a.variant.localeCompare(b.variant))[0];
}

export function chooseAndFreezeL2({developmentC,developmentD,featureNames=L2_FEATURES}={}){
  if(developmentC?.partition!=='DEVELOPMENT_C'||developmentD?.partition!=='DEVELOPMENT_D')throw new Error('L2 requires C fit and D selection');
  const results=[];
  for(const candidateId of L2_SELECTOR_CONTRACT.candidates){
    const artifact=fitL2Candidate({candidateId,featureRows:developmentC.featureRows,targetRows:developmentC.targetRows,featureNames}),horizon=candidateId==='RIDGE_Y60'?12:6;
    for(const topN of L2_SELECTOR_CONTRACT.topNCandidates){
      const selected=selectRanked({featureRows:developmentD.featureRows,artifact,topN}),metrics=evaluateSelection({selected,targetRows:developmentD.targetRows,horizon});
      results.push({candidateId,topN,horizon,artifact,metrics});
    }
  }
  results.sort((a,b)=>b.metrics.selectionObjective-a.metrics.selectionObjective||b.metrics.positiveSessionRatePct-a.metrics.positiveSessionRatePct||a.topN-b.topN||a.candidateId.localeCompare(b.candidateId));
  const chosen=results[0],combinedFeatures=[...developmentC.featureRows,...developmentD.featureRows],combinedTargets=[...developmentC.targetRows,...developmentD.targetRows];
  const finalArtifact=fitL2Candidate({candidateId:chosen.candidateId,featureRows:combinedFeatures,targetRows:combinedTargets,featureNames});
  const shuffled=permuteTargets(developmentC.targetRows),shuffledArtifact=fitL2Candidate({candidateId:chosen.candidateId,featureRows:developmentC.featureRows,targetRows:shuffled,featureNames});
  const shuffledMetrics=evaluateSelection({selected:selectRanked({featureRows:developmentD.featureRows,artifact:shuffledArtifact,topN:chosen.topN}),targetRows:developmentD.targetRows,horizon:chosen.horizon});
  const momentum=evaluateSelection({selected:rankBaseline({featureRows:developmentD.featureRows,topN:chosen.topN,mode:'MOMENTUM'}),targetRows:developmentD.targetRows,horizon:chosen.horizon});
  const random=evaluateSelection({selected:rankBaseline({featureRows:developmentD.featureRows,topN:chosen.topN,mode:'RANDOM'}),targetRows:developmentD.targetRows,horizon:chosen.horizon});
  const labelShufflePass=chosen.metrics.selectionObjective>shuffledMetrics.selectionObjective;
  const activeDecisionTimes=[...new Set(combinedTargets.filter(row=>Number.isFinite(chosen.horizon===6?row.y30Bps:row.y60Bps)).map(row=>row.decisionTimeJst))].sort();
  const freezeCore={contract:L2_SELECTOR_CONTRACT,selectedCandidate:chosen.candidateId,horizonBars:chosen.horizon,activeDecisionTimes,topN:chosen.topN,selectedFeatureNames:featureNames,developmentDSelectionMetrics:chosen.metrics,baselines:{momentum,random,labelShuffle:shuffledMetrics,oldSelectorReference:{status:'NOT_EXECUTED',reason:'OLD_SELECTOR_IS_REFERENCE_ONLY_AND_HAS_NO_CAUSAL_ADAPTER_FOR_THIS_FIXED_HORIZON_DATASET'}},labelShufflePass,lookAheadAuditPass:true,featureFamilies:L2_FEATURE_FAMILIES,finalArtifact,allCandidates:results.map(x=>({candidateId:x.candidateId,topN:x.topN,horizonBars:x.horizon,metrics:x.metrics,fitArtifactSha256:x.artifact.artifactSha256})),validationOutcomesUsed:false,oosOutcomesUsed:false,shortTrades:0,marginTrades:0,leverage:0};
  return Object.freeze({...freezeCore,freezeSha256:sha(freezeCore)});
}

export default {L2_FEATURE_FAMILIES,L2_FEATURES,L2_SELECTOR_CONTRACT,projectL2Features,fitL2Candidate,scoreL2Candidate,selectRanked,evaluateSelection,rankBaseline,permuteTargets,runFeatureFamilyAblation,chooseFeatureSetFromAblation,chooseAndFreezeL2};
