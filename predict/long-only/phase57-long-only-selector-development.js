import {createHash} from 'node:crypto';
import {buildEvaluatorOnlyL2Targets,L2_CANDIDATE_CONTRACT} from './phase57-long-only-l2-candidate-contract.js';

export const LONG_SELECTOR_FEATURES=Object.freeze([
  'currentReturnPct','momentum5Pct','momentum15Pct','momentum30Pct','momentumAccelerationPct',
  'logCumulativeTurnover','vwapDistancePct','sessionHighUpdate','rangeExpansionPct','trendEfficiency',
  'reversalRate','marketBreadthPositivePct','sectorBreadthPositivePct','timeOfDayFraction','causalAtrPct',
]);
export const LONG_SELECTOR_DEVELOPMENT_CONTRACT=Object.freeze({
  contractId:'PHASE57_LONG_ONLY_SELECTOR_LINEAR_V1',fitPartition:'DEVELOPMENT_C',selectionPartition:'DEVELOPMENT_D',
  finalRefitPartitions:Object.freeze(['DEVELOPMENT_C','DEVELOPMENT_D']),modelFamily:'RIDGE_LINEAR',regularization:0.1,
  capacityPerDecision:10,targetCandidates:L2_CANDIDATE_CONTRACT.targetCandidates,featureSets:1,thresholdSearch:false,
});
const forbidden=/winner|future|remainingUpside|lateDetection|continuationToClose|mfe|mae|target|label|outcome/i;
const sha=value=>createHash('sha256').update(JSON.stringify(value)).digest('hex');
const finite=value=>Number.isFinite(Number(value));
const round=value=>Number.isFinite(value)?Number(value.toFixed(8)):value;
const mean=values=>values.length?values.reduce((a,x)=>a+x,0)/values.length:null;
const key=row=>`${row.sessionDate}|${row.symbol}|${row.decisionTimeJst}`;

export function projectLongSelectorFeatures(row={}){
  if(Object.keys(row).some(name=>forbidden.test(name)))throw new Error('outcome field reached LONG Selector feature input');
  const [hour,minute]=String(row.decisionTimeJst??'').split(':').map(Number),current=Number(row.currentPrice),atr=Number(row.causalAtr);
  const projected={
    currentReturnPct:Number(row.currentReturnPct),momentum5Pct:Number(row.momentum5Pct),momentum15Pct:Number(row.momentum15Pct),momentum30Pct:Number(row.momentum30Pct),momentumAccelerationPct:Number(row.momentumAccelerationPct),
    logCumulativeTurnover:Math.log1p(Math.max(0,Number(row.cumulativeTurnover))),vwapDistancePct:Number(row.vwapDistancePct),sessionHighUpdate:row.sessionHighUpdate?1:0,rangeExpansionPct:Number(row.rangeExpansionPct),trendEfficiency:Number(row.trendEfficiency),
    reversalRate:Number(row.reversalCount)/Math.max(1,Number(row.observedBars)-1),marketBreadthPositivePct:Number(row.marketBreadthPositivePct),sectorBreadthPositivePct:Number(row.sectorBreadthPositivePct),
    timeOfDayFraction:((hour*60+minute)-570)/270,causalAtrPct:current>0?100*atr/current:NaN,
  };
  if(!LONG_SELECTOR_FEATURES.every(name=>finite(projected[name])))throw new Error('complete finite causal LONG Selector features are required');
  return Object.freeze(projected);
}

function solve(matrix,vector){
  const n=vector.length,a=matrix.map((row,i)=>[...row,vector[i]]);
  for(let col=0;col<n;col++){
    let pivot=col;for(let row=col+1;row<n;row++)if(Math.abs(a[row][col])>Math.abs(a[pivot][col]))pivot=row;
    [a[col],a[pivot]]=[a[pivot],a[col]];if(Math.abs(a[col][col])<1e-10)a[col][col]=1e-10;
    const divisor=a[col][col];for(let j=col;j<=n;j++)a[col][j]/=divisor;
    for(let row=0;row<n;row++){if(row===col)continue;const factor=a[row][col];for(let j=col;j<=n;j++)a[row][j]-=factor*a[col][j];}
  }
  return a.map(row=>row[n]);
}

function targetValue(label,targetId){
  const targets=buildEvaluatorOnlyL2Targets(label);
  if(targetId==='CONTINUATION_PROBABILITY')return targets.continuationProbabilityLabel;
  if(targetId==='EXPECTED_CONTINUATION_RETURN')return targets.expectedContinuationReturnPct;
  if(targetId==='RISK_ADJUSTED_REMAINING_OPPORTUNITY')return targets.riskAdjustedRemainingOpportunityPct;
  throw new Error('unknown frozen LONG Selector target');
}

export function fitLongSelectorRidge({featureRows=[],evaluatorOnlyLabels=[],targetId,regularization=LONG_SELECTOR_DEVELOPMENT_CONTRACT.regularization}={}){
  const labels=new Map(evaluatorOnlyLabels.map(row=>[key(row),row])),samples=featureRows.map(row=>({row,x:projectLongSelectorFeatures(row),label:labels.get(key(row))})).filter(x=>x.label);
  if(samples.length<LONG_SELECTOR_FEATURES.length+2)throw new Error('insufficient LONG Selector training rows');
  const means=LONG_SELECTOR_FEATURES.map(name=>mean(samples.map(x=>x.x[name]))),scales=LONG_SELECTOR_FEATURES.map((name,i)=>Math.sqrt(mean(samples.map(x=>(x.x[name]-means[i])**2)))||1);
  const design=samples.map(sample=>[1,...LONG_SELECTOR_FEATURES.map((name,i)=>(sample.x[name]-means[i])/scales[i])]),y=samples.map(sample=>targetValue(sample.label,targetId));
  const p=design[0].length,xtx=Array.from({length:p},()=>Array(p).fill(0)),xty=Array(p).fill(0);
  for(let r=0;r<design.length;r++)for(let i=0;i<p;i++){xty[i]+=design[r][i]*y[r];for(let j=0;j<p;j++)xtx[i][j]+=design[r][i]*design[r][j];}
  for(let i=1;i<p;i++)xtx[i][i]+=Number(regularization)*samples.length;
  const coefficients=solve(xtx,xty),core={contractId:LONG_SELECTOR_DEVELOPMENT_CONTRACT.contractId,targetId,featureNames:LONG_SELECTOR_FEATURES,means,scales,intercept:coefficients[0],weights:coefficients.slice(1),regularization:Number(regularization),trainingRows:samples.length};
  return Object.freeze({...core,artifactSha256:sha(core)});
}

export function scoreLongSelector(feature,artifact){
  const x=projectLongSelectorFeatures(feature);
  if(artifact?.contractId!==LONG_SELECTOR_DEVELOPMENT_CONTRACT.contractId||JSON.stringify(artifact.featureNames)!==JSON.stringify(LONG_SELECTOR_FEATURES)||artifact.artifactSha256!==sha(Object.fromEntries(Object.entries(artifact).filter(([name])=>name!=='artifactSha256'))))throw new Error('LONG Selector artifact contract mismatch');
  const raw=Number(artifact.intercept)+LONG_SELECTOR_FEATURES.reduce((sum,name,i)=>sum+Number(artifact.weights[i])*(x[name]-Number(artifact.means[i]))/Number(artifact.scales[i]),0);
  return artifact.targetId==='CONTINUATION_PROBABILITY'?Math.max(0,Math.min(1,raw)):raw;
}

export function selectLongCandidates({featureRows=[],artifact,capacityPerDecision=LONG_SELECTOR_DEVELOPMENT_CONTRACT.capacityPerDecision}={}){
  const groups=new Map();for(const row of featureRows){const k=`${row.sessionDate}|${row.decisionTimeJst}`;if(!groups.has(k))groups.set(k,[]);groups.get(k).push(row);}
  const selected=[];for(const rows of groups.values())selected.push(...rows.map(row=>({row,score:scoreLongSelector(row,artifact)})).sort((a,b)=>b.score-a.score||a.row.symbol.localeCompare(b.row.symbol)).slice(0,capacityPerDecision).map((x,rank)=>Object.freeze({...x.row,selectorScore:round(x.score),selectorRank:rank+1,selectorArtifactSha256:artifact.artifactSha256})));
  return Object.freeze(selected.sort((a,b)=>key(a).localeCompare(key(b))));
}

function evaluateCandidate(selected,allLabels){
  const labels=new Map(allLabels.map(row=>[key(row),row])),joined=selected.map(row=>({row,label:labels.get(key(row))})).filter(x=>x.label),allWinners=allLabels.filter(x=>x.winner).length;
  const risk=joined.map(x=>buildEvaluatorOnlyL2Targets(x.label).riskAdjustedRemainingOpportunityPct),mfe=joined.map(x=>Number(x.label.futureMfePct)),mae=joined.map(x=>Number(x.label.futureMaePct));
  return Object.freeze({selected:joined.length,meanRiskAdjustedOpportunityPct:round(mean(risk)),meanFutureMfePct:round(mean(mfe)),meanFutureMaePct:round(mean(mae)),winnerPrecisionPct:joined.length?round(100*joined.filter(x=>x.label.winner).length/joined.length):null,winnerRecallPct:allWinners?round(100*joined.filter(x=>x.label.winner).length/allWinners):null});
}

export function runLongSelectorDevelopment({developmentC,developmentD}={}){
  if(developmentC?.partition!=='DEVELOPMENT_C'||developmentD?.partition!=='DEVELOPMENT_D')throw new Error('LONG Selector selection requires Development C fit and Development D selection');
  const results=LONG_SELECTOR_DEVELOPMENT_CONTRACT.targetCandidates.map(targetId=>{
    const artifact=fitLongSelectorRidge({featureRows:developmentC.featureRows,evaluatorOnlyLabels:developmentC.evaluatorOnlyLabels,targetId});
    const selected=selectLongCandidates({featureRows:developmentD.featureRows,artifact});
    return Object.freeze({targetId,artifact,metrics:evaluateCandidate(selected,developmentD.evaluatorOnlyLabels)});
  }).sort((a,b)=>(b.metrics.meanRiskAdjustedOpportunityPct??-Infinity)-(a.metrics.meanRiskAdjustedOpportunityPct??-Infinity)||a.targetId.localeCompare(b.targetId));
  const winner=results[0],finalArtifact=fitLongSelectorRidge({featureRows:[...developmentC.featureRows,...developmentD.featureRows],evaluatorOnlyLabels:[...developmentC.evaluatorOnlyLabels,...developmentD.evaluatorOnlyLabels],targetId:winner.targetId});
  const freeze={contract:LONG_SELECTOR_DEVELOPMENT_CONTRACT,selectedTarget:winner.targetId,developmentSelectionMetrics:winner.metrics,finalArtifact,allCandidates:results.map(x=>({targetId:x.targetId,metrics:x.metrics,fitArtifactSha256:x.artifact.artifactSha256})),validationOutcomesUsed:false,oosOutcomesUsed:false};
  return Object.freeze({...freeze,freezeSha256:sha(freeze)});
}

export default {LONG_SELECTOR_FEATURES,LONG_SELECTOR_DEVELOPMENT_CONTRACT,projectLongSelectorFeatures,fitLongSelectorRidge,scoreLongSelector,selectLongCandidates,runLongSelectorDevelopment};
