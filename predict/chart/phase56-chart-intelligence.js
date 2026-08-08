export const PHASE56_SAFETY = Object.freeze({
  mode: 'CHART_INTELLIGENCE_READ_ONLY', executionAllowed: false, brokerWriteAllowed: false,
  excelOrderWriteAllowed: false, rssOrderFunctionAllowed: false, liveTradingAllowed: false,
  automaticPromotionAllowed: false, productionUpdateAllowed: false, humanApprovalRequired: true,
});

function n(v) { const x = Number(v); return Number.isFinite(x) ? x : null; }
function normalizeBars(bars = []) {
  return bars.map((b, i) => ({ i, time: b.time ?? b.timestamp ?? i, open:n(b.open), high:n(b.high), low:n(b.low), close:n(b.close), volume:n(b.volume) ?? 0, vwap:n(b.vwap) }))
    .filter(b => [b.open,b.high,b.low,b.close].every(Number.isFinite) && b.high >= b.low);
}
function swingPoints(bars, radius = 2) {
  const highs=[], lows=[];
  for(let i=radius;i<bars.length-radius;i++){
    const w=bars.slice(i-radius,i+radius+1), b=bars[i];
    if(w.every((x,j)=>j===radius || b.high>x.high)) highs.push({index:i,price:b.high,time:b.time});
    if(w.every((x,j)=>j===radius || b.low<x.low)) lows.push({index:i,price:b.low,time:b.time});
  }
  return {highs,lows};
}
function structure(swings) {
  const hs=swings.highs.slice(-2), ls=swings.lows.slice(-2);
  const highState=hs.length<2?'UNKNOWN':hs[1].price>hs[0].price?'HH':hs[1].price<hs[0].price?'LH':'EH';
  const lowState=ls.length<2?'UNKNOWN':ls[1].price>ls[0].price?'HL':ls[1].price<ls[0].price?'LL':'EL';
  const regime=highState==='HH'&&lowState==='HL'?'UPTREND':highState==='LH'&&lowState==='LL'?'DOWNTREND':'RANGE_OR_TRANSITION';
  return {highState,lowState,regime};
}
function zones(swings, lastClose, tolerancePct=.003) {
  const pts=[...swings.highs,...swings.lows].sort((a,b)=>a.price-b.price), out=[];
  for(const p of pts){ const z=out.find(x=>Math.abs(x.price-p.price)/Math.max(1,p.price)<=tolerancePct); if(z){z.touches++;z.price=(z.price*(z.touches-1)+p.price)/z.touches;} else out.push({price:p.price,touches:1}); }
  return out.filter(z=>z.touches>=2).map(z=>({...z,type:z.price<=lastClose?'SUPPORT':'RESISTANCE',distancePct:(z.price-lastClose)/lastClose})).sort((a,b)=>Math.abs(a.distancePct)-Math.abs(b.distancePct)).slice(0,6);
}
export function analyzeChartStructure({bars=[], swingRadius=2, zoneTolerancePct=.003}={}){
  const clean=normalizeBars(bars), blockers=[];
  if(clean.length < Math.max(10,swingRadius*2+5)) blockers.push('INSUFFICIENT_BARS');
  if(blockers.length) return Object.freeze({phase:'56.0',status:'OBSERVE',blockers,executionAllowed:false,transmitted:false,safety:PHASE56_SAFETY});
  const swings=swingPoints(clean,swingRadius), s=structure(swings), last=clean.at(-1), zs=zones(swings,last.close,zoneTolerancePct);
  const vwap=last.vwap; const vwapPosition=Number.isFinite(vwap)?last.close>vwap?'ABOVE':last.close<vwap?'BELOW':'AT':'UNKNOWN';
  return Object.freeze({phase:'56.0',status:'CHART_CONTEXT_READY',barCount:clean.length,lastClose:last.close,marketStructure:s,swings,zones:zs,vwap:{value:vwap,position:vwapPosition,distancePct:Number.isFinite(vwap)?(last.close-vwap)/vwap:null},reviewOnly:true,executionAllowed:false,brokerWriteAllowed:false,excelOrderWriteAllowed:false,rssOrderFunctionAllowed:false,liveTradingAllowed:false,automaticPromotionAllowed:false,productionUpdateAllowed:false,transmitted:false,humanApprovalRequired:true,safety:PHASE56_SAFETY});
}
