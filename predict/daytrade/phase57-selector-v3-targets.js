import {PHASE57_SELECTOR_V3_FREEZE,PHASE57_SELECTOR_V3_SAFETY} from './phase57-selector-v3.js';

const finite=value=>value!==null&&value!==undefined&&value!==''&&Number.isFinite(Number(value));
const round8=value=>Number(Number(value).toFixed(8));

function timeMs(value,label){
  const parsed=Date.parse(String(value??''));
  if(!Number.isFinite(parsed))throw new TypeError(`${label} must be a valid timestamp`);
  return parsed;
}

function normalizeFutureBar(bar,index){
  if(!bar||typeof bar!=='object')throw new TypeError(`futureBars[${index}] must be an object`);
  const availableAt=String(bar.availableAt??'');
  const availableAtMs=timeMs(availableAt,`futureBars[${index}].availableAt`);
  const sessionDate=String(bar.sessionDate??'').trim();
  if(!/^\d{4}-\d{2}-\d{2}$/.test(sessionDate))throw new Error(`futureBars[${index}] requires YYYY-MM-DD sessionDate`);
  for(const key of ['high','low']){
    if(!finite(bar[key])||Number(bar[key])<=0)throw new Error(`futureBars[${index}] requires positive finite ${key}`);
  }
  const normalized={availableAt,availableAtMs,sessionDate,high:Number(bar.high),low:Number(bar.low)};
  if(normalized.high<normalized.low)throw new Error(`futureBars[${index}] high is below low`);
  return normalized;
}

function sameBar(left,right){
  return left.availableAt===right.availableAt&&left.sessionDate===right.sessionDate&&left.high===right.high&&left.low===right.low;
}

function normalizeFutureBars(bars){
  if(!Array.isArray(bars))throw new TypeError('futureBars must be an array');
  const byAvailableAt=new Map();
  bars.forEach((bar,index)=>{
    const normalized=normalizeFutureBar(bar,index);
    const previous=byAvailableAt.get(normalized.availableAt);
    if(previous&&!sameBar(previous,normalized))throw new Error(`conflicting future bar at ${normalized.availableAt}`);
    if(!previous)byAvailableAt.set(normalized.availableAt,normalized);
  });
  return [...byAvailableAt.values()].sort((a,b)=>a.availableAtMs-b.availableAtMs);
}

function barrierFirst(bars,anchorPrice,barrierBps){
  const distance=Number(barrierBps)/10000;
  const upper=anchorPrice*(1+distance);
  const lower=anchorPrice*(1-distance);
  for(let index=0;index<bars.length;index+=1){
    const bar=bars[index];
    const upperTouched=bar.high>=upper;
    const lowerTouched=bar.low<=lower;
    if(upperTouched&&lowerTouched){
      return {
        status:'AMBIGUOUS_SAME_BAR',barIndex:index+1,availableAt:bar.availableAt,
        upArm:'AMBIGUOUS_SAME_BAR',downArm:'AMBIGUOUS_SAME_BAR',
      };
    }
    if(upperTouched){
      return {status:'UP_FIRST',barIndex:index+1,availableAt:bar.availableAt,upArm:'FAVORABLE_FIRST',downArm:'ADVERSE_FIRST'};
    }
    if(lowerTouched){
      return {status:'DOWN_FIRST',barIndex:index+1,availableAt:bar.availableAt,upArm:'ADVERSE_FIRST',downArm:'FAVORABLE_FIRST'};
    }
  }
  return {status:'NOT_REACHED',barIndex:null,availableAt:null,upArm:'NOT_REACHED',downArm:'NOT_REACHED'};
}

export function buildPhase57SelectorNativeTargets({
  featureCutoff,
  anchorPrice,
  sessionDate,
  futureBars=[],
}={}){
  const featureCutoffMs=timeMs(featureCutoff,'featureCutoff');
  if(!finite(anchorPrice)||Number(anchorPrice)<=0)throw new TypeError('anchorPrice must be positive finite');
  if(!/^\d{4}-\d{2}-\d{2}$/.test(String(sessionDate??'')))throw new TypeError('sessionDate must be YYYY-MM-DD');
  const anchor=Number(anchorPrice);
  const normalized=normalizeFutureBars(futureBars);
  const causalFuture=normalized.filter(bar=>bar.availableAtMs>featureCutoffMs&&bar.sessionDate===sessionDate);
  const horizons={};
  for(const horizon of PHASE57_SELECTOR_V3_FREEZE.targets.horizonBars){
    if(causalFuture.length<horizon){
      horizons[horizon]={
        status:'INSUFFICIENT_FUTURE_BARS',requiredBars:horizon,availableBars:causalFuture.length,
        upExcursion:null,downExcursion:null,twoSidedOpportunity:null,costAdjustedTwoSidedUtility:null,barriers:null,
      };
      continue;
    }
    const bars=causalFuture.slice(0,horizon);
    const maximumHigh=Math.max(...bars.map(bar=>bar.high));
    const minimumLow=Math.min(...bars.map(bar=>bar.low));
    const upExcursion=Math.max(0,maximumHigh/anchor-1);
    const downExcursion=Math.max(0,1-minimumLow/anchor);
    const twoSidedOpportunity=Math.max(upExcursion,downExcursion);
    const costAdjustedTwoSidedUtility=twoSidedOpportunity-PHASE57_SELECTOR_V3_FREEZE.targets.roundTripCostBps/10000;
    const barriers=Object.fromEntries(PHASE57_SELECTOR_V3_FREEZE.targets.barrierBps.map(bps=>[
      String(bps),barrierFirst(bars,anchor,bps),
    ]));
    horizons[horizon]={
      status:'TARGET_READY',requiredBars:horizon,availableBars:causalFuture.length,
      upExcursion:round8(upExcursion),downExcursion:round8(downExcursion),
      twoSidedOpportunity:round8(twoSidedOpportunity),
      costAdjustedTwoSidedUtility:round8(costAdjustedTwoSidedUtility),
      maximumHigh,minimumLow,barriers,
    };
  }
  return Object.freeze({
    phase:'57.selector-v3.0.native-targets',
    status:'SELECTOR_NATIVE_TARGETS_BUILT',
    featureCutoff:new Date(featureCutoffMs).toISOString(),
    anchorPrice:anchor,sessionDate,
    futureBarCount:causalFuture.length,
    primaryHorizonBars:PHASE57_SELECTOR_V3_FREEZE.targets.primaryHorizonBars,
    horizons:Object.freeze(horizons),
    methodology:Object.freeze({
      entryIndependent:true,directionIndependentPrimary:true,
      futureBarsUsedOnlyForTargets:true,overnightBarsExcluded:true,
      ambiguousSameBarOrderInferred:false,
    }),
    safety:PHASE57_SELECTOR_V3_SAFETY,
  });
}

export default {buildPhase57SelectorNativeTargets};

