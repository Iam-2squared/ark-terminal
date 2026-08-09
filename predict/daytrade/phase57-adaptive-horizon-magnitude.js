export const PHASE57_P21_SAFETY = Object.freeze({
  mode:'PHASE57_ADAPTIVE_HORIZON_MAGNITUDE_RESEARCH_ONLY',
  executionAllowed:false,
  brokerWriteAllowed:false,
  excelOrderWriteAllowed:false,
  rssOrderFunctionAllowed:false,
  liveTradingAllowed:false,
  paperTradingAllowed:false,
  automaticPromotionAllowed:false,
  productionUpdateAllowed:false,
  humanApprovalRequired:true,
});

const finite=v=>v!==null&&v!==undefined&&v!==''&&Number.isFinite(Number(v));

function normalizeBar(bar){
  const ts=bar?.timestamp??bar?.time??bar?.datetime;
  if(!ts||!finite(bar?.open)||!finite(bar?.high)||!finite(bar?.low)||!finite(bar?.close)) return null;
  return {timestamp:new Date(ts).toISOString(),open:Number(bar.open),high:Number(bar.high),low:Number(bar.low),close:Number(bar.close),volume:finite(bar.volume)?Number(bar.volume):0};
}

export function buildMultiHorizonMagnitudeRows({symbol,sessionDate,bars=[],horizons=[1,3,6,12,24]}={}){
  const hs=[...new Set(horizons.map(Number).filter(x=>Number.isInteger(x)&&x>0))].sort((a,b)=>a-b);
  const normalized=bars.map(normalizeBar).filter(Boolean).sort((a,b)=>a.timestamp.localeCompare(b.timestamp));
  const out=[];
  for(let i=5;i<normalized.length-1;i++){
    const cur=normalized[i];
    const targets={};
    for(const h of hs){
      const endIndex=i+h;
      if(endIndex>=normalized.length) continue;
      const future=normalized.slice(i+1,endIndex+1);
      const exit=normalized[endIndex];
      const entry=cur.close;
      const actualReturnPct=entry?(exit.close/entry-1)*100:0;
      const maxHigh=Math.max(...future.map(b=>b.high));
      const minLow=Math.min(...future.map(b=>b.low));
      const mfePct=entry?(maxHigh/entry-1)*100:0;
      const maePct=entry?(minLow/entry-1)*100:0;
      targets[h]=Object.freeze({horizonBars:h,outcomeAt:exit.timestamp,actualReturnPct,absMovePct:Math.abs(actualReturnPct),direction:actualReturnPct>=0?1:0,mfePct,maePct});
    }
    if(Object.keys(targets).length) out.push(Object.freeze({symbol,sessionDate,featureCutoff:cur.timestamp,entryPrice:cur.close,targets:Object.freeze(targets),pointInTimeValid:true,sourceMode:'historical_intraday_ohlcv'}));
  }
  return Object.freeze(out);
}

export function materializeHorizonRows(baseRows=[],horizonBars){
  const h=Number(horizonBars);
  return baseRows.flatMap(row=>{
    const t=row?.targets?.[h];
    if(!t) return [];
    return [Object.freeze({...row,horizonBars:h,outcomeAt:t.outcomeAt,label:t.direction,actualReturnPct:t.actualReturnPct,absMovePct:t.absMovePct,mfePct:t.mfePct,maePct:t.maePct,barrierBps:Math.abs(t.actualReturnPct)*100})];
  });
}

export function scoreMagnitudeSignals(rows=[],predictProbability,{threshold=0.55,roundTripCostPct=0.05}={}){
  const signals=[];
  for(const row of rows){
    const p=Number(predictProbability(row));
    if(!Number.isFinite(p)) continue;
    const clipped=Math.max(0.001,Math.min(0.999,p));
    const confidence=Math.max(clipped,1-clipped);
    if(confidence<threshold) continue;
    const direction=clipped>=0.5?1:0;
    const aligned=direction===1?Number(row.actualReturnPct):-Number(row.actualReturnPct);
    const netReturnPct=aligned-Number(roundTripCostPct||0);
    signals.push(Object.freeze({direction,confidence,correct:direction===Number(row.label),grossAlignedReturnPct:aligned,netReturnPct,horizonBars:Number(row.horizonBars)}));
  }
  const n=signals.length;
  const wins=signals.filter(x=>x.correct).length;
  const net=n?signals.reduce((s,x)=>s+x.netReturnPct,0)/n:null;
  const gross=n?signals.reduce((s,x)=>s+x.grossAlignedReturnPct,0)/n:null;
  const positive=signals.filter(x=>x.netReturnPct>0).reduce((s,x)=>s+x.netReturnPct,0);
  const negative=-signals.filter(x=>x.netReturnPct<0).reduce((s,x)=>s+x.netReturnPct,0);
  return Object.freeze({signalCount:n,hitRate:n?wins/n:null,grossAverageReturnPct:gross,netAverageReturnPct:net,profitFactor:negative>0?positive/negative:(positive>0?Infinity:null),signals:Object.freeze(signals)});
}

export function rankHorizonCandidates(candidates=[],{minimumSignals=30,minimumNetReturnPct=0}={}){
  const eligible=candidates.filter(c=>Number(c?.signalCount)>=minimumSignals&&finite(c?.netAverageReturnPct)&&Number(c.netAverageReturnPct)>=minimumNetReturnPct);
  const ranked=(eligible.length?eligible:candidates.filter(c=>finite(c?.netAverageReturnPct))).slice().sort((a,b)=>{
    if(Number(b.netAverageReturnPct)!==Number(a.netAverageReturnPct)) return Number(b.netAverageReturnPct)-Number(a.netAverageReturnPct);
    if(Number(b.hitRate??-Infinity)!==Number(a.hitRate??-Infinity)) return Number(b.hitRate??-Infinity)-Number(a.hitRate??-Infinity);
    return Number(b.signalCount??0)-Number(a.signalCount??0);
  });
  return Object.freeze({selected:eligible.length?(ranked[0]??null):null,bestObserved:ranked[0]??null,eligibleCount:eligible.length,minimumSignals,minimumNetReturnPct,selectionSource:'TRAIN_ONLY_REQUIRED'});
}

export default {buildMultiHorizonMagnitudeRows,materializeHorizonRows,scoreMagnitudeSignals,rankHorizonCandidates};
