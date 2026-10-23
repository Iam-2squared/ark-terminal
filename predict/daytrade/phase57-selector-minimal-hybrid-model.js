import {createHash} from 'node:crypto';

export const PHASE57_MINIMAL_HYBRID_MODEL_FEATURES=Object.freeze([
  'turnoverRank',
  'relativeActivity',
  'recentAbsoluteMovementAtr',
  'maSlopeAtr',
  'vwapSlopeAtr',
  'momentumAccelerationAtr',
  'pathEfficiency',
  'reversalFrequency',
  'extensionPersistenceInteraction',
  'extensionReversalInteraction',
  'marketBreadth',
  'sectorBreadth',
]);

const FORBIDDEN_DIRECT_EXTENSION_FEATURES=new Set([
  'extensionAtr','vwapDistance','vwapDistanceAtr','atrNormalizedExtension','intradayRangePosition','preSelectionMove',
]);
const finite=value=>value!==null&&value!==undefined&&value!==''&&Number.isFinite(Number(value));
const clamp=(value,min=0,max=1)=>Math.min(max,Math.max(min,Number(value)));
const round10=value=>Number(Number(value).toFixed(10));

function deepFreeze(value){
  if(value&&typeof value==='object'&&!Object.isFrozen(value)){
    for(const child of Object.values(value))deepFreeze(child);
    Object.freeze(value);
  }
  return value;
}

function mean(values){return values.reduce((sum,value)=>sum+value,0)/values.length;}

function validateFeatureNames(featureNames){
  if(!Array.isArray(featureNames)||!featureNames.length)throw new TypeError('featureNames must be a non-empty array');
  if(featureNames.length>12)throw new Error('Minimal Hybrid may train at most 12 features');
  const seen=new Set();
  for(const name of featureNames){
    if(seen.has(name))throw new Error(`duplicate model feature ${name}`);
    seen.add(name);
    if(!PHASE57_MINIMAL_HYBRID_MODEL_FEATURES.includes(name))throw new Error(`feature is outside the Minimal set: ${name}`);
    if(FORBIDDEN_DIRECT_EXTENSION_FEATURES.has(name))throw new Error(`direct extension model feature is forbidden: ${name}`);
  }
}

function validateSelectionPolicy(policy){
  if(!policy||typeof policy!=='object')throw new TypeError('selectionPolicy is required');
  if(!finite(policy.maximumSelected)||!Number.isInteger(Number(policy.maximumSelected))||Number(policy.maximumSelected)<1)throw new Error('maximumSelected must be a positive integer');
  if(!finite(policy.minimumRemainingOpportunityScore)||Number(policy.minimumRemainingOpportunityScore)<0||Number(policy.minimumRemainingOpportunityScore)>1)throw new Error('minimumRemainingOpportunityScore must be in [0,1]');
  if(!finite(policy.opportunityScale)||Number(policy.opportunityScale)<=0)throw new Error('opportunityScale must be positive');
  if(!finite(policy.maximumAbsoluteSoftAdjustment)||Number(policy.maximumAbsoluteSoftAdjustment)<0||Number(policy.maximumAbsoluteSoftAdjustment)>0.25)throw new Error('maximumAbsoluteSoftAdjustment must be in [0,0.25]');
  if(policy.source!=='ADMITTED_FRESH_DEVELOPMENT'&&policy.source!=='SYNTHETIC_FIXTURE_ONLY')throw new Error('selectionPolicy source must be Development or synthetic fixture');
  if(policy.extensionThreshold!==undefined||policy.v3Threshold!==undefined)throw new Error('extension and V3 thresholds are forbidden in Hybrid selection policy');
}

function validateTrainingContext(context,samples){
  if(context?.mode==='SYNTHETIC_FIXTURE_ONLY')return {mode:context.mode,performanceClaimAllowed:false};
  if(context?.mode!=='ADMITTED_FRESH_DEVELOPMENT')throw new Error('training context must be admitted Fresh Development or synthetic fixture');
  const admission=context.datasetAdmission;
  if(admission?.status!=='MINIMAL_HYBRID_NEW_DATASET_ADMITTED_DEVELOPMENT_ONLY')throw new Error('real model training requires admitted Fresh Development');
  const allowed=new Set(admission.split?.development??[]);
  for(const sample of samples)if(!allowed.has(sample.sessionDate))throw new Error(`training sample is outside admitted Development: ${sample.sessionDate}`);
  return {mode:context.mode,datasetId:admission.datasetId,performanceClaimAllowed:false};
}

function sampleVector(sample,featureNames,index){
  if(!sample||typeof sample!=='object')throw new TypeError(`samples[${index}] must be an object`);
  if(!/^\d{4}-\d{2}-\d{2}$/.test(String(sample.sessionDate??'')))throw new Error(`samples[${index}] requires sessionDate`);
  const values=featureNames.map(name=>{
    const value=sample.features?.[name];
    if(!finite(value))throw new Error(`samples[${index}] feature ${name} is missing; missing cannot become zero`);
    return Number(value);
  });
  const up=sample.targets?.upExcursion,down=sample.targets?.downExcursion;
  if(!finite(up)||Number(up)<0||!finite(down)||Number(down)<0)throw new Error(`samples[${index}] requires non-negative separate Up/Down targets`);
  if(sample.targets?.twoSidedOpportunityUsedAsTrainingTarget===true)throw new Error('TwoSidedOpportunity cannot be the direct Primary training target');
  return {values,up:Number(up),down:Number(down)};
}

function solveLinearSystem(matrix,vector){
  const n=vector.length;
  const a=matrix.map((row,index)=>[...row,vector[index]]);
  for(let column=0;column<n;column+=1){
    let pivot=column;
    for(let row=column+1;row<n;row+=1)if(Math.abs(a[row][column])>Math.abs(a[pivot][column]))pivot=row;
    if(Math.abs(a[pivot][column])<1e-12)throw new Error('ridge system is singular');
    [a[column],a[pivot]]=[a[pivot],a[column]];
    const divisor=a[column][column];
    for(let item=column;item<=n;item+=1)a[column][item]/=divisor;
    for(let row=0;row<n;row+=1){
      if(row===column)continue;
      const factor=a[row][column];
      for(let item=column;item<=n;item+=1)a[row][item]-=factor*a[column][item];
    }
  }
  return a.map(row=>row[n]);
}

function ridgeFit(vectors,targets,lambda){
  const columns=vectors[0].length+1;
  const xtx=Array.from({length:columns},()=>Array(columns).fill(0));
  const xty=Array(columns).fill(0);
  vectors.forEach((vector,row)=>{
    const x=[1,...vector];
    for(let left=0;left<columns;left+=1){
      xty[left]+=x[left]*targets[row];
      for(let right=0;right<columns;right+=1)xtx[left][right]+=x[left]*x[right];
    }
  });
  for(let column=1;column<columns;column+=1)xtx[column][column]+=lambda;
  return solveLinearSystem(xtx,xty).map(round10);
}

function canonicalDigest(value){return createHash('sha256').update(JSON.stringify(value)).digest('hex');}

export function trainPhase57MinimalHybridModel({
  samples=[],featureNames=PHASE57_MINIMAL_HYBRID_MODEL_FEATURES,ridgeLambda=0.1,
  selectionPolicy,trainingContext,
}={}){
  validateFeatureNames(featureNames);
  validateSelectionPolicy(selectionPolicy);
  if(!Array.isArray(samples)||samples.length<featureNames.length+2)throw new Error(`at least ${featureNames.length+2} training samples are required`);
  if(!finite(ridgeLambda)||Number(ridgeLambda)<=0)throw new Error('ridgeLambda must be positive');
  const context=validateTrainingContext(trainingContext,samples);
  if(selectionPolicy.source!==context.mode)throw new Error('selectionPolicy source must match training context');
  const normalized=samples.map((sample,index)=>sampleVector(sample,featureNames,index));
  const centers=featureNames.map((_,column)=>mean(normalized.map(row=>row.values[column])));
  const scales=featureNames.map((_,column)=>{
    const variance=mean(normalized.map(row=>(row.values[column]-centers[column])**2));
    return Math.sqrt(variance)>1e-9?Math.sqrt(variance):1;
  });
  const vectors=normalized.map(row=>row.values.map((value,column)=>(value-centers[column])/scales[column]));
  const upCoefficients=ridgeFit(vectors,normalized.map(row=>row.up),Number(ridgeLambda));
  const downCoefficients=ridgeFit(vectors,normalized.map(row=>row.down),Number(ridgeLambda));
  const payload={
    schemaVersion:1,phase:'57.selector-minimal-hybrid.model',status:'MINIMAL_HYBRID_MULTI_TARGET_MODEL_READY',
    modelFamily:'TWO_INDEPENDENT_RIDGE_REGRESSIONS',featureNames:[...featureNames],
    centers:centers.map(round10),scales:scales.map(round10),upCoefficients,downCoefficients,
    ridgeLambda:Number(ridgeLambda),trainingSampleCount:samples.length,trainingContext:context,
    selectionPolicy:{
      source:selectionPolicy.source,
      maximumSelected:Number(selectionPolicy.maximumSelected),
      minimumRemainingOpportunityScore:Number(selectionPolicy.minimumRemainingOpportunityScore),
      opportunityScale:Number(selectionPolicy.opportunityScale),
      maximumAbsoluteSoftAdjustment:Number(selectionPolicy.maximumAbsoluteSoftAdjustment),
    },
    guards:{
      upDownTargetsSeparated:true,twoSidedDirectTrainingTarget:false,
      directExtensionCoefficientAllowed:false,extensionThresholdAllowed:false,
      v3MembershipOrThresholdUsed:false,missingToZero:false,
      entryExitAllocationInputsUsed:false,microstructureUsed:false,
    },
    performanceClaimAllowed:false,
  };
  payload.modelDigest=canonicalDigest(payload);
  return deepFreeze(payload);
}

export function predictPhase57MinimalHybridTargets({model,features}={}){
  if(model?.status!=='MINIMAL_HYBRID_MULTI_TARGET_MODEL_READY')throw new Error('a ready Minimal Hybrid model is required');
  validateFeatureNames(model.featureNames);
  const vector=model.featureNames.map((name,index)=>{
    const value=features?.[name];
    if(!finite(value))throw new Error(`inference feature ${name} is missing; missing cannot become zero`);
    return (Number(value)-model.centers[index])/model.scales[index];
  });
  const predict=coefficients=>coefficients[0]+vector.reduce((sum,value,index)=>sum+value*coefficients[index+1],0);
  const expectedUpExcursion=Math.max(0,predict(model.upCoefficients));
  const expectedDownExcursion=Math.max(0,predict(model.downCoefficients));
  const expectedTwoSidedOpportunity=Math.max(expectedUpExcursion,expectedDownExcursion);
  const remainingOpportunityScore=1-Math.exp(-expectedTwoSidedOpportunity/model.selectionPolicy.opportunityScale);
  return deepFreeze({
    status:'MINIMAL_HYBRID_REMAINING_OPPORTUNITY_READY',
    expectedUpExcursion:round10(expectedUpExcursion),
    expectedDownExcursion:round10(expectedDownExcursion),
    expectedTwoSidedOpportunity:round10(expectedTwoSidedOpportunity),
    remainingOpportunityScore:round10(clamp(remainingOpportunityScore)),
    directionDecision:null,
  });
}

function pearson(left,right){
  if(left.length<2)return null;
  const ml=mean(left),mr=mean(right);
  const numerator=left.reduce((sum,value,index)=>sum+(value-ml)*(right[index]-mr),0);
  const dl=Math.sqrt(left.reduce((sum,value)=>sum+(value-ml)**2,0));
  const dr=Math.sqrt(right.reduce((sum,value)=>sum+(value-mr)**2,0));
  return dl>0&&dr>0?numerator/(dl*dr):null;
}

function ranks(values){
  const order=values.map((value,index)=>({value,index})).sort((a,b)=>a.value-b.value||a.index-b.index);
  const result=Array(values.length);let start=0;
  while(start<order.length){
    let end=start;while(end+1<order.length&&order[end+1].value===order[start].value)end+=1;
    const rank=(start+end)/2+1;for(let index=start;index<=end;index+=1)result[order[index].index]=rank;start=end+1;
  }
  return result;
}

export function describePhase57MinimalHybridFeatures(samples=[]){
  if(!Array.isArray(samples)||!samples.length)throw new TypeError('samples are required');
  const up=samples.map(sample=>Number(sample.targets?.upExcursion));
  const down=samples.map(sample=>Number(sample.targets?.downExcursion));
  if(!up.every(Number.isFinite)||!down.every(Number.isFinite))throw new Error('feature diagnostics require separate finite Up/Down targets');
  const byFeature={};
  for(const name of PHASE57_MINIMAL_HYBRID_MODEL_FEATURES){
    const available=samples.map((sample,index)=>({index,value:Number(sample.features?.[name])})).filter(row=>Number.isFinite(row.value));
    const values=available.map(row=>row.value),upValues=available.map(row=>up[row.index]),downValues=available.map(row=>down[row.index]);
    byFeature[name]=Object.freeze({
      missingRate:round10(1-available.length/samples.length),
      pearsonUp:pearson(values,upValues),pearsonDown:pearson(values,downValues),
      spearmanUp:pearson(ranks(values),ranks(upValues)),spearmanDown:pearson(ranks(values),ranks(downValues)),
    });
  }
  return deepFreeze({status:'MINIMAL_HYBRID_FEATURE_DIAGNOSTICS_READY',developmentSelectionApplied:false,byFeature});
}

export default {
  trainPhase57MinimalHybridModel,predictPhase57MinimalHybridTargets,
  describePhase57MinimalHybridFeatures,PHASE57_MINIMAL_HYBRID_MODEL_FEATURES,
};
