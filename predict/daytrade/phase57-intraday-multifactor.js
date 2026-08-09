export const PHASE57_P20_SAFETY = Object.freeze({
  mode: 'PHASE57_INTRADAY_MULTIFACTOR_RESEARCH_ONLY',
  executionAllowed: false,
  brokerWriteAllowed: false,
  excelOrderWriteAllowed: false,
  rssOrderFunctionAllowed: false,
  liveTradingAllowed: false,
  paperTradingAllowed: false,
  automaticPromotionAllowed: false,
  productionUpdateAllowed: false,
});

const avg = xs => xs.length ? xs.reduce((a,b)=>a+b,0)/xs.length : 0;
const stdev = xs => {
  if (xs.length < 2) return 0;
  const m=avg(xs); return Math.sqrt(avg(xs.map(x=>(x-m)**2)));
};
const ema = (xs, period) => {
  if (!xs.length) return 0;
  const k=2/(period+1); let v=xs[0];
  for(let i=1;i<xs.length;i++) v=xs[i]*k+v*(1-k);
  return v;
};

function rsi(closes, period=14){
  if(closes.length<2) return 50;
  let gains=0,losses=0,count=0;
  for(let i=Math.max(1,closes.length-period);i<closes.length;i++){
    const d=closes[i]-closes[i-1];
    if(d>=0) gains+=d; else losses-=d; count++;
  }
  if(!count) return 50;
  if(losses===0) return gains>0?100:50;
  const rs=(gains/count)/(losses/count); return 100-(100/(1+rs));
}

function trueRange(cur, prevClose){
  return Math.max(cur.high-cur.low,Math.abs(cur.high-prevClose),Math.abs(cur.low-prevClose));
}

function jstMinutes(iso){
  const p=new Intl.DateTimeFormat('en-US',{timeZone:'Asia/Tokyo',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).formatToParts(new Date(iso));
  const o=Object.fromEntries(p.map(x=>[x.type,x.value]));
  return Number(o.hour)*60+Number(o.minute);
}

export function enrichHistoricalIntradayBars(bars=[]){
  const out=[];
  for(let i=0;i<bars.length;i++){
    const history=bars.slice(0,i+1);
    const cur=history.at(-1);
    const closes=history.map(b=>Number(b.close));
    const vols=history.map(b=>Number(b.volume||0));
    const typical=history.map(b=>(Number(b.high)+Number(b.low)+Number(b.close))/3);
    const volSum=vols.reduce((a,b)=>a+b,0);
    const vwap=volSum?history.reduce((s,b,j)=>s+typical[j]*vols[j],0)/volSum:Number(cur.close);
    const ma5=avg(closes.slice(-5));
    const ma10=avg(closes.slice(-10));
    const ma20=avg(closes.slice(-20));
    const sd20=stdev(closes.slice(-20));
    const upper=ma20+2*sd20, lower=ma20-2*sd20;
    const trs=history.map((b,j)=>j?trueRange(b,Number(history[j-1].close)):Number(b.high)-Number(b.low));
    const atr14=avg(trs.slice(-14));
    const macd=ema(closes.slice(-40),12)-ema(closes.slice(-40),26);
    const macdSeries=closes.map((_,j)=>ema(closes.slice(0,j+1),12)-ema(closes.slice(0,j+1),26));
    const signal=ema(macdSeries.slice(-20),9);
    const hh20=Math.max(...history.slice(-20).map(b=>Number(b.high)));
    const ll20=Math.min(...history.slice(-20).map(b=>Number(b.low)));
    const range20=hh20-ll20;
    const todMinutes=jstMinutes(cur.timestamp);
    const oldMa5 = i>=5 ? avg(bars.slice(Math.max(0,i-9),i-4).map(b=>Number(b.close))) : ma5;
    out.push({
      ...cur,
      multiFactor:{
        ma5DistancePct:ma5?(cur.close/ma5-1)*100:0,
        ma10DistancePct:ma10?(cur.close/ma10-1)*100:0,
        ma20DistancePct:ma20?(cur.close/ma20-1)*100:0,
        ma5SlopePct:oldMa5?(ma5/oldMa5-1)*100:0,
        rsi14:rsi(closes,14),
        macd,
        macdSignalGap:macd-signal,
        atrPct:cur.close?atr14/cur.close*100:0,
        vwapDistancePct:vwap?(cur.close/vwap-1)*100:0,
        bbPosition:upper>lower?(cur.close-lower)/(upper-lower):0.5,
        relativeVolume20:avg(vols.slice(-20,-1))>0?Number(cur.volume||0)/avg(vols.slice(-20,-1)):1,
        range20Position:range20>0?(cur.close-ll20)/range20:0.5,
        openingMinutes:Math.max(0,todMinutes-540),
        isOpening30:todMinutes>=540&&todMinutes<570?1:0,
        isLunchReturn:todMinutes>=750&&todMinutes<780?1:0,
        isClosing30:todMinutes>=900&&todMinutes<=930?1:0,
      }
    });
  }
  return out;
}

export function attachMultiFactorFeatures(rows=[], enrichedBars=[]){
  const map=new Map(enrichedBars.map(b=>[new Date(b.timestamp).toISOString(),b.multiFactor]));
  return rows.map(row=>Object.freeze({...row,features:Object.freeze({...row.features,...(map.get(new Date(row.featureCutoff).toISOString())||{})})}));
}

export default { enrichHistoricalIntradayBars, attachMultiFactorFeatures };
