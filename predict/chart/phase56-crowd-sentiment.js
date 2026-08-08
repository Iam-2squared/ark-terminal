export const PHASE56_CROWD_SENTIMENT_SAFETY=Object.freeze({mode:'CROWD_SENTIMENT_RESEARCH_ONLY',executionAllowed:false,brokerWriteAllowed:false,excelOrderWriteAllowed:false,rssOrderFunctionAllowed:false,liveTradingAllowed:false,paperTradingAllowed:false,automaticPromotionAllowed:false,productionUpdateAllowed:false,humanApprovalRequired:true});
const finite=v=>v!==null&&v!==undefined&&v!==''&&Number.isFinite(Number(v));
const clamp=(v,a,b)=>Math.min(b,Math.max(a,Number(v)));
const ts=v=>{const x=Date.parse(v);return Number.isFinite(x)?x:null;};
export function buildCrowdSentimentFeature({snapshot=null,previousSnapshot=null,asOfSessionDate=null,provider='OPTIONAL_EXTERNAL'}={}){
 if(!snapshot)return Object.freeze({phase:'56.p7',status:'NO_SENTIMENT_SOURCE',provider,optional:true,features:null,reviewOnly:true,executionAllowed:false,transmitted:false,safety:PHASE56_CROWD_SENTIMENT_SAFETY});
 const effectiveAt=snapshot.effectiveAt??snapshot.timestamp??null;
 if(effectiveAt&&asOfSessionDate&&ts(effectiveAt)>ts(asOfSessionDate))return Object.freeze({phase:'56.p7',status:'FUTURE_SENTIMENT_LEAK_BLOCKED',provider,optional:true,features:null,reviewOnly:true,executionAllowed:false,transmitted:false,safety:PHASE56_CROWD_SENTIMENT_SAFETY});
 const buy=finite(snapshot.buyPercent)?clamp(snapshot.buyPercent,0,100):null;
 const sell=finite(snapshot.sellPercent)?clamp(snapshot.sellPercent,0,100):null;
 const neutral=finite(snapshot.neutralPercent)?clamp(snapshot.neutralPercent,0,100):(buy!==null&&sell!==null?clamp(100-buy-sell,0,100):null);
 const prevBuy=finite(previousSnapshot?.buyPercent)?Number(previousSnapshot.buyPercent):null;
 const prevSell=finite(previousSnapshot?.sellPercent)?Number(previousSnapshot.sellPercent):null;
 const buyMomentum=buy!==null&&prevBuy!==null?buy-prevBuy:null;
 const sellMomentum=sell!==null&&prevSell!==null?sell-prevSell:null;
 const net=buy!==null&&sell!==null?buy-sell:null;
 return Object.freeze({phase:'56.p7',status:'CROWD_SENTIMENT_READY',provider,optional:true,effectiveAt,features:Object.freeze({buyPercent:buy,sellPercent:sell,neutralPercent:neutral,netSentiment:net,buyMomentum,sellMomentum,sentimentMomentum:buyMomentum!==null&&sellMomentum!==null?buyMomentum-sellMomentum:null}),researchPolicy:Object.freeze({officialOrPermittedSourceRequired:true,brittleScrapingNotRequired:true,commentsBodyNotRequired:true,standaloneTradingSignal:false}),reviewOnly:true,recommendationAllowed:false,paperTradingAllowed:false,executionAllowed:false,brokerWriteAllowed:false,excelOrderWriteAllowed:false,rssOrderFunctionAllowed:false,liveTradingAllowed:false,automaticPromotionAllowed:false,productionUpdateAllowed:false,transmitted:false,humanApprovalRequired:true,safety:PHASE56_CROWD_SENTIMENT_SAFETY});
}
export default buildCrowdSentimentFeature;
