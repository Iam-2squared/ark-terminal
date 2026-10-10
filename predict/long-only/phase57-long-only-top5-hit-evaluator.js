// Evaluator-only +1% extension for ELIGIBILITY-TOP5-HIT-DISTRIBUTION-1.
const minuteOf=value=>{const match=String(value??'').match(/(\d{2}):(\d{2})/);return match?Number(match[1])*60+Number(match[2]):NaN;};

export function measureOnePct({bars=[],auctions=[],reference=null,decisionTimeJst=null}={}){
  const empty={highOpportunity1:null,closeOpportunity1:null,auctionCloseOpportunity1:null,timeToHigh1Min:null,timeToClose1Min:null};
  const decision=minuteOf(decisionTimeJst);
  if(!(reference>0)||!Number.isFinite(decision))return empty;
  const futureBars=bars.filter(row=>minuteOf(row.barStartJst)>=decision&&minuteOf(row.availableAtJst)>decision);
  const futureAuctions=auctions.filter(row=>row.minute>decision);
  if(!futureBars.length&&!futureAuctions.length)return empty;
  const ratio=1.01;
  const high=futureBars.find(row=>row.high/reference>=ratio)??null;
  const closeBar=futureBars.find(row=>row.close/reference>=ratio)??null;
  const auction=futureAuctions.find(row=>row.close/reference>=ratio)??null;
  const closeMinutes=[closeBar?minuteOf(closeBar.availableAtJst):null,auction?.minute??null].filter(Number.isFinite).sort((a,b)=>a-b);
  return {highOpportunity1:high?1:0,closeOpportunity1:closeMinutes.length?1:0,auctionCloseOpportunity1:auction?1:0,
    timeToHigh1Min:high?minuteOf(high.availableAtJst)-decision:null,timeToClose1Min:closeMinutes.length?closeMinutes[0]-decision:null};
}

export default {measureOnePct};
