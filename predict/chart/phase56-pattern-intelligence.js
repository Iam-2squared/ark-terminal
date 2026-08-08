export const PHASE56_PATTERN_SAFETY = Object.freeze({
  mode: 'CHART_PATTERN_RESEARCH_ONLY', executionAllowed: false, brokerWriteAllowed: false,
  excelOrderWriteAllowed: false, rssOrderFunctionAllowed: false, liveTradingAllowed: false,
  automaticPromotionAllowed: false, productionUpdateAllowed: false, humanApprovalRequired: true,
});

const num = v => Number.isFinite(Number(v)) ? Number(v) : null;
const clamp = (v,a=0,b=1) => Math.max(a,Math.min(b,v));
function lineSlope(a,b){ return a&&b&&b.index!==a.index ? (b.price-a.price)/(b.index-a.index) : null; }
function relSlope(s, price){ return Number.isFinite(s)&&price ? s/price : null; }
function last2(a=[]){ return a.slice(-2); }

export function detectClassicChartPatterns({chartContext={}, priceAction={}, setupContext={}}={}) {
  const swings=chartContext.swings||{}; const hs=last2(swings.highs), ls=last2(swings.lows);
  const price=num(chartContext.lastClose); const hSlope=relSlope(lineSlope(hs[0],hs[1]),price); const lSlope=relSlope(lineSlope(ls[0],ls[1]),price);
  const tolerance=.008; const patterns=[];
  if(hs.length===2 && ls.length===2 && price){
    const highsEqual=Math.abs(hs[1].price-hs[0].price)/price<=tolerance;
    const lowsEqual=Math.abs(ls[1].price-ls[0].price)/price<=tolerance;
    if(highsEqual && lSlope>0) patterns.push({name:'ASCENDING_TRIANGLE',bias:'BULLISH',geometryScore:clamp(1-Math.abs(hSlope||0)*20)});
    if(lowsEqual && hSlope<0) patterns.push({name:'DESCENDING_TRIANGLE',bias:'BEARISH',geometryScore:clamp(1-Math.abs(lSlope||0)*20)});
    if(hSlope<0 && lSlope>0) patterns.push({name:'SYMMETRICAL_TRIANGLE',bias:'NEUTRAL',geometryScore:clamp((Math.abs(hSlope)+Math.abs(lSlope))*20)});
    if(highsEqual) patterns.push({name:'DOUBLE_TOP_CANDIDATE',bias:'BEARISH',geometryScore:clamp(1-Math.abs(hs[1].price-hs[0].price)/price/tolerance)});
    if(lowsEqual) patterns.push({name:'DOUBLE_BOTTOM_CANDIDATE',bias:'BULLISH',geometryScore:clamp(1-Math.abs(ls[1].price-ls[0].price)/price/tolerance)});
    if(hSlope>0 && lSlope>0 && hSlope<lSlope) patterns.push({name:'RISING_WEDGE_CANDIDATE',bias:'BEARISH',geometryScore:clamp((lSlope-hSlope)*30)});
    if(hSlope<0 && lSlope<0 && hSlope<lSlope) patterns.push({name:'FALLING_WEDGE_CANDIDATE',bias:'BULLISH',geometryScore:clamp((lSlope-hSlope)*30)});
  }
  const pa=priceAction?.latest||priceAction||{}; const relativeVolume=num(pa.relativeVolume);
  return Object.freeze({phase:'56.6',status:patterns.length?'PATTERN_CANDIDATES':'NO_CLASSIC_PATTERN',patterns,hSlope,lSlope,relativeVolume,setupStatus:setupContext.status??null,reviewOnly:true,executionAllowed:false,transmitted:false,safety:PHASE56_PATTERN_SAFETY});
}

export function scorePatternQuality({patternResult={}, chartContext={}, priceAction={}, setupContext={}, marketContext={}}={}) {
  const patterns=(patternResult.patterns||[]).map(p=>{
    let score=0.45*p.geometryScore; const reasons=[`geometry:${p.geometryScore.toFixed(3)}`];
    const rv=num((priceAction?.latest||priceAction||{}).relativeVolume);
    if(rv!==null){ const x=clamp((rv-0.8)/1.2); score+=0.2*x; reasons.push(`volume:${x.toFixed(3)}`); }
    const vp=chartContext?.vwap?.position; const aligned=(p.bias==='BULLISH'&&vp==='ABOVE')||(p.bias==='BEARISH'&&vp==='BELOW');
    if(aligned){score+=0.15; reasons.push('vwap:aligned');}
    const setup=String(setupContext?.status||''); const setupAligned=(p.bias==='BULLISH'&&/LONG|BULL|BREAKOUT|PULLBACK/.test(setup))||(p.bias==='BEARISH'&&/SHORT|BEAR|BREAKDOWN|RALLY/.test(setup));
    if(setupAligned){score+=0.1; reasons.push('setup:aligned');}
    const regime=String(marketContext?.regime||marketContext?.marketRegime||''); const marketAligned=(p.bias==='BULLISH'&&/BULL|UP/.test(regime))||(p.bias==='BEARISH'&&/BEAR|DOWN/.test(regime));
    if(marketAligned){score+=0.1; reasons.push('market:aligned');}
    return {...p,qualityScore:clamp(score),qualityBand:score>=.75?'HIGH_RESEARCH_QUALITY':score>=.55?'MEDIUM_RESEARCH_QUALITY':'LOW_RESEARCH_QUALITY',reasons};
  }).sort((a,b)=>b.qualityScore-a.qualityScore);
  return Object.freeze({phase:'56.7',status:patterns.length?'PATTERN_CONTEXT_READY':'OBSERVE',patterns,bestPattern:patterns[0]||null,reviewOnly:true,recommendationAllowed:false,paperTradingAllowed:false,executionAllowed:false,brokerWriteAllowed:false,excelOrderWriteAllowed:false,rssOrderFunctionAllowed:false,liveTradingAllowed:false,automaticPromotionAllowed:false,productionUpdateAllowed:false,transmitted:false,safety:PHASE56_PATTERN_SAFETY});
}
