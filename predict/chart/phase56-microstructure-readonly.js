export const PHASE56_MICROSTRUCTURE_SAFETY=Object.freeze({mode:'MICROSTRUCTURE_READ_ONLY_RESEARCH',executionAllowed:false,brokerWriteAllowed:false,excelOrderWriteAllowed:false,rssOrderFunctionAllowed:false,liveTradingAllowed:false,paperTradingAllowed:false,automaticPromotionAllowed:false,productionUpdateAllowed:false,humanApprovalRequired:true});
const finite=v=>v!==null&&v!==undefined&&v!==''&&Number.isFinite(Number(v));
const num=v=>finite(v)?Number(v):null;
function safeRatio(a,b){return finite(a)&&finite(b)&&Number(b)!==0?Number(a)/Number(b):null;}
function imbalance(bid,ask){if(!finite(bid)||!finite(ask))return null;const s=Number(bid)+Number(ask);return s===0?0:(Number(bid)-Number(ask))/s;}
function tickDirection(t){const x=String(t??'').toUpperCase();return ['UP','BUY','BID','+'].includes(x)?1:['DOWN','SELL','ASK','-'].includes(x)?-1:0;}
export function buildReadonlyMicrostructureFeatures({snapshot={},ticks=[]}={}){
 const bestBid=num(snapshot.bestBid??snapshot.bid),bestAsk=num(snapshot.bestAsk??snapshot.ask),bidSize=num(snapshot.bidSize??snapshot.bestBidSize),askSize=num(snapshot.askSize??snapshot.bestAskSize);
 const spread=finite(bestBid)&&finite(bestAsk)?bestAsk-bestBid:null; const mid=finite(bestBid)&&finite(bestAsk)?(bestBid+bestAsk)/2:null; const spreadBps=finite(spread)&&finite(mid)&&mid!==0?spread/mid*10000:null;
 const bookImbalance=imbalance(bidSize,askSize); const depthBid=num(snapshot.bidDepth??snapshot.totalBidDepth),depthAsk=num(snapshot.askDepth??snapshot.totalAskDepth),depthImbalance=imbalance(depthBid,depthAsk);
 const normalizedTicks=(Array.isArray(ticks)?ticks:[]).map(t=>({price:num(t.price),size:num(t.size??t.volume),direction:tickDirection(t.direction??t.side??t.tickDirection),timestamp:t.timestamp??t.time??null})).filter(t=>finite(t.price));
 const buyAgg=normalizedTicks.filter(t=>t.direction>0).reduce((s,t)=>s+(t.size??1),0),sellAgg=normalizedTicks.filter(t=>t.direction<0).reduce((s,t)=>s+(t.size??1),0),totalAgg=buyAgg+sellAgg;
 const aggressiveBuyRatio=totalAgg?buyAgg/totalAgg:null,tradeIntensity=num(snapshot.tradeIntensity)??(normalizedTicks.length||null);
 return Object.freeze({phase:'56.p6',status:(finite(bestBid)&&finite(bestAsk))?'MICROSTRUCTURE_READY':'PARTIAL_MICROSTRUCTURE',features:Object.freeze({bestBid,bestAsk,spread,spreadBps,bidSize,askSize,bookImbalance,depthImbalance,aggressiveBuyRatio,aggressiveSellRatio:aggressiveBuyRatio===null?null:1-aggressiveBuyRatio,tradeIntensity,lastTickDirection:normalizedTicks.length?normalizedTicks.at(-1).direction:0,liquidityRatio:safeRatio((bidSize??0)+(askSize??0),spreadBps??null)}),source:Object.freeze({mode:'READ_ONLY',expectedInputs:['RssMarket','RssTickList','board/depth snapshot'],rssOrderFunctionsUsed:false}),reviewOnly:true,recommendationAllowed:false,paperTradingAllowed:false,executionAllowed:false,brokerWriteAllowed:false,excelOrderWriteAllowed:false,rssOrderFunctionAllowed:false,liveTradingAllowed:false,automaticPromotionAllowed:false,productionUpdateAllowed:false,transmitted:false,humanApprovalRequired:true,safety:PHASE56_MICROSTRUCTURE_SAFETY});
}
export default buildReadonlyMicrostructureFeatures;
