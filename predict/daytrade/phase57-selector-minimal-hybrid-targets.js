const HORIZONS=Object.freeze([1,2,3,6,12]);
const finite=value=>value!==null&&value!==undefined&&value!==''&&Number.isFinite(Number(value));
const round8=value=>Number(Number(value).toFixed(8));

function timeMs(value,label){
  const result=Date.parse(String(value??''));
  if(!Number.isFinite(result))throw new TypeError(`${label} must be a valid timestamp`);
  return result;
}

function normalizeFutureBars(bars){
  if(!Array.isArray(bars))throw new TypeError('futureBars must be an array');
  const seen=new Map();
  bars.forEach((bar,index)=>{
    const availableAt=String(bar?.availableAt??'');
    const availableAtMs=timeMs(availableAt,`futureBars[${index}].availableAt`);
    const sessionDate=String(bar?.sessionDate??'');
    if(!/^\d{4}-\d{2}-\d{2}$/.test(sessionDate))throw new Error(`futureBars[${index}] requires sessionDate`);
    for(const key of ['high','low','close'])if(!finite(bar?.[key])||Number(bar[key])<=0)throw new Error(`futureBars[${index}] requires positive ${key}`);
    const row={availableAt,availableAtMs,sessionDate,high:Number(bar.high),low:Number(bar.low),close:Number(bar.close)};
    if(row.high<Math.max(row.close,row.low)||row.low>Math.min(row.close,row.high))throw new Error(`futureBars[${index}] has invalid price ordering`);
    const previous=seen.get(availableAt);
    if(previous&&JSON.stringify(previous)!==JSON.stringify(row))throw new Error(`conflicting future bar ${availableAt}`);
    if(!previous)seen.set(availableAt,row);
  });
  return [...seen.values()].sort((a,b)=>a.availableAtMs-b.availableAtMs);
}

function pathEfficiency(anchor,bars){
  let previous=anchor,path=0;
  for(const bar of bars){path+=Math.abs(bar.close/previous-1);previous=bar.close;}
  return path>0?Math.min(1,Math.abs(bars.at(-1).close/anchor-1)/path):0;
}

export function buildPhase57MinimalHybridTargets({featureCutoff,anchorPrice,sessionDate,futureBars=[]}={}){
  const cutoff=timeMs(featureCutoff,'featureCutoff');
  if(!finite(anchorPrice)||Number(anchorPrice)<=0)throw new TypeError('anchorPrice must be positive finite');
  if(!/^\d{4}-\d{2}-\d{2}$/.test(String(sessionDate??'')))throw new TypeError('sessionDate must be YYYY-MM-DD');
  const anchor=Number(anchorPrice);
  const causal=normalizeFutureBars(futureBars).filter(bar=>bar.availableAtMs>cutoff&&bar.sessionDate===sessionDate);
  const horizons={};
  for(const horizon of HORIZONS){
    if(causal.length<horizon){
      horizons[horizon]=Object.freeze({status:'INSUFFICIENT_FUTURE_BARS',upExcursion:null,downExcursion:null,twoSidedOpportunity:null,pathEfficiency:null,timeToUpExcursionBars:null,timeToDownExcursionBars:null});
      continue;
    }
    const bars=causal.slice(0,horizon);
    const highs=bars.map(bar=>bar.high);
    const lows=bars.map(bar=>bar.low);
    const maximumHigh=Math.max(...highs),minimumLow=Math.min(...lows);
    const upExcursion=Math.max(0,maximumHigh/anchor-1);
    const downExcursion=Math.max(0,1-minimumLow/anchor);
    horizons[horizon]=Object.freeze({
      status:'TARGET_READY',
      upExcursion:round8(upExcursion),
      downExcursion:round8(downExcursion),
      twoSidedOpportunity:round8(Math.max(upExcursion,downExcursion)),
      pathEfficiency:round8(pathEfficiency(anchor,bars)),
      timeToUpExcursionBars:highs.indexOf(maximumHigh)+1,
      timeToDownExcursionBars:lows.indexOf(minimumLow)+1,
      finalCloseReturn:round8(bars.at(-1).close/anchor-1),
    });
  }
  return Object.freeze({
    phase:'57.selector-minimal-hybrid.targets',
    status:'MINIMAL_HYBRID_UP_DOWN_TARGETS_READY',
    featureCutoff:new Date(cutoff).toISOString(),sessionDate,anchorPrice:anchor,
    horizons:Object.freeze(horizons),
    methodology:Object.freeze({
      upDownTargetsSeparated:true,twoSidedPrimaryTrainingTarget:false,
      futureBarsUsedForFeatures:false,sameSessionOnly:true,entryDirectionUsed:false,
    }),
  });
}

export const PHASE57_MINIMAL_HYBRID_TARGET_HORIZONS=HORIZONS;
export default {buildPhase57MinimalHybridTargets,PHASE57_MINIMAL_HYBRID_TARGET_HORIZONS};
