import {createHash} from 'node:crypto';

export const L2_HORIZON_CONTRACT=Object.freeze({
  schemaVersion:1,
  barSemantics:'FIVE_MINUTE_TRADING_BARS_AVAILABLE_AT_BAR_END',
  horizons:Object.freeze({Y30_BPS:6,Y60_BPS:12}),
  twoHeadHorizonBars:6,
  downsidePenaltyLambda:0.5,
  decisionRule:'TARGET_BAR_INDEX_EQUALS_DECISION_BAR_INDEX_PLUS_HORIZON_BARS',
});

const key=row=>`${row.sessionDate}|${row.symbol}|${row.decisionTimeJst}`;
const pct=(a,b)=>100*(Number(a)/Number(b)-1);
const round=x=>Number.isFinite(x)?Number(x.toFixed(8)):x;

export function buildFixedHorizonTargets({featureRows=[],bars5m=[],evaluatorOnlyLabels=[]}={}){
  const bySymbol=new Map();
  for(const bar of bars5m){
    const k=`${bar.sessionDate}|${bar.symbol}`;
    if(!bySymbol.has(k))bySymbol.set(k,[]);
    bySymbol.get(k).push(bar);
  }
  for(const rows of bySymbol.values())rows.sort((a,b)=>a.availableAtJst.localeCompare(b.availableAtJst));
  const labels=new Map(evaluatorOnlyLabels.map(row=>[key(row),row])),targets=[];
  for(const feature of featureRows){
    const rows=bySymbol.get(`${feature.sessionDate}|${feature.symbol}`)??[];
    let index=rows.findIndex(row=>row.availableAtJst===feature.decisionAtJst);
    if(index<0)index=rows.findLastIndex(row=>row.availableAtJst<=feature.decisionAtJst);
    if(index<0)continue;
    const current=Number(rows[index].close),label=labels.get(key(feature));
    const build=horizon=>{
      const terminal=rows[index+horizon];
      if(!terminal)return null;
      const path=rows.slice(index+1,index+horizon+1);
      return Object.freeze({
        returnBps:round(10000*(Number(terminal.close)/current-1)),
        futureMfePct:round(pct(Math.max(...path.map(row=>Number(row.high))),current)),
        futureMaePct:round(pct(Math.min(...path.map(row=>Number(row.low))),current)),
        targetAvailableAtJst:terminal.availableAtJst,
        bars:horizon,
      });
    };
    const h30=build(6),h60=build(12);
    if(!h30&&!h60)continue;
    targets.push(Object.freeze({
      sessionDate:feature.sessionDate,symbol:feature.symbol,decisionTimeJst:feature.decisionTimeJst,evaluatorOnly:true,
      y30Bps:h30?.returnBps??null,y60Bps:h60?.returnBps??null,
      futureMfe30Pct:h30?.futureMfePct??null,futureMae30Pct:h30?.futureMaePct??null,
      futureMfe60Pct:h60?.futureMfePct??null,futureMae60Pct:h60?.futureMaePct??null,
      target30AvailableAtJst:h30?.targetAvailableAtJst??null,target60AvailableAtJst:h60?.targetAvailableAtJst??null,
      winner:Boolean(label?.winner),largeWinner:Boolean(label?.largeWinner),
      remainingUpsidePct:Number(label?.remainingUpsidePct),timeToWinnerMinutes:Number(label?.timeToWinnerMinutes),
    }));
  }
  if(targets.some(row=>row.target30AvailableAtJst&&row.target30AvailableAtJst<=`${row.sessionDate}T${row.decisionTimeJst}:00+09:00`))throw new Error('fixed-horizon target is not strictly after decision time');
  return Object.freeze(targets);
}

export default {L2_HORIZON_CONTRACT,buildFixedHorizonTargets};
