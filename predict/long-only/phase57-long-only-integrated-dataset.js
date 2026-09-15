import {createHash} from 'node:crypto';
import {PHASE57_LONG_ONLY_SAFETY,assertLongOnlyResearchContract} from './phase57-long-only-research-contract.js';

export const TIMESTAMP_CONTRACT='BAR_START_HALF_OPEN_AVAILABLE_AT_BAR_END_JST_TERMINAL_AUCTION_SEPARATE';
export const MARKET_SEGMENTS=Object.freeze({'0111':'PRIME','0112':'STANDARD','0113':'GROWTH'});
const sha=value=>createHash('sha256').update(JSON.stringify(value)).digest('hex');
const codeOf=row=>String(row?.Code??row?.code??row?.symbol??'').trim().toUpperCase();
const dateOf=row=>String(row?.Date??row?.date??row?.sessionDate??'');
const number=(row,...keys)=>{for(const key of keys){const value=Number(row?.[key]);if(Number.isFinite(value))return value;}return NaN;};

export function assembleLongOnlyL0Rows({dailyRows=[],masterRows=[],warmupDailyRows=[]}={}){
  assertLongOnlyResearchContract();
  const master=new Map();
  for(const row of masterRows){
    const date=dateOf(row),code=codeOf(row),segment=MARKET_SEGMENTS[String(row?.Mkt??row?.marketCode??'')];
    if(date&&code&&!master.has(`${date}|${code}`))master.set(`${date}|${code}`,{segment,commonEquity:String(row?.ProdCat??row?.productCategory??'')==='011'});
  }
  const sorted=[...dailyRows].sort((a,b)=>dateOf(a).localeCompare(dateOf(b))||codeOf(a).localeCompare(codeOf(b)));
  const previousByCode=new Map();
  for(const row of [...warmupDailyRows].sort((a,b)=>dateOf(a).localeCompare(dateOf(b))||codeOf(a).localeCompare(codeOf(b)))){
    const symbol=codeOf(row),adjustedClose=number(row,'AdjC','adjustedClose');
    if(symbol&&Number.isFinite(adjustedClose)&&adjustedClose>0)previousByCode.set(symbol,adjustedClose);
  }
  const seen=new Set(),rows=[],exclusions=[];
  const reject=(sessionDate,symbol,reason)=>exclusions.push(Object.freeze({sessionDate,symbol,reason}));
  for(const row of sorted){
    const sessionDate=dateOf(row),symbol=codeOf(row),key=`${sessionDate}|${symbol}`,adjustedClose=number(row,'AdjC','adjustedClose');
    if(!/^\d{4}-\d{2}-\d{2}$/.test(sessionDate)||!symbol||!Number.isFinite(adjustedClose)||adjustedClose<=0){reject(sessionDate,symbol,'INVALID_DAILY');continue;}
    if(seen.has(key)){reject(sessionDate,symbol,'DUPLICATE_DAILY');continue;}
    seen.add(key);
    const pit=master.get(key),previous=previousByCode.get(symbol);
    previousByCode.set(symbol,adjustedClose);
    if(!pit?.segment||!pit.commonEquity){reject(sessionDate,symbol,'NOT_ELIGIBLE_PIT_COMMON_EQUITY');continue;}
    if(!Number.isFinite(previous)||previous<=0){reject(sessionDate,symbol,'NO_PRIOR_ADJUSTED_CLOSE');continue;}
    rows.push(Object.freeze({
      sessionDate,symbol,segment:pit.segment,adjustedClose,adjustedPreviousClose:previous,
      volume:number(row,'Vo','volume'),turnover:number(row,'Va','turnover'),
      corporateActionFlag:number(row,'AdjFactor','adjustmentFactor')!==1||Boolean(row?.ExRT),
      listingMembershipPointInTime:true,
    }));
  }
  const reasons=Object.fromEntries([...new Set(exclusions.map(x=>x.reason))].sort().map(reason=>[reason,exclusions.filter(x=>x.reason===reason).length]));
  return Object.freeze({rows:Object.freeze(rows),audit:Object.freeze({inputDailyRows:dailyRows.length,inputMasterRows:masterRows.length,warmupDailyRows:warmupDailyRows.length,eligibleRows:rows.length,excludedRows:exclusions.length,exclusionCounts:Object.freeze(reasons),exclusions:Object.freeze(exclusions),corporateActionFlaggedRows:rows.filter(x=>x.corporateActionFlag).length})});
}

const minutes=(hhmm)=>{const [h,m]=String(hhmm).slice(0,5).split(':').map(Number);return h*60+m;};
const hhmm=value=>{const raw=String(value??'');const match=raw.match(/(\d{2}):(\d{2})/);return match?`${match[1]}:${match[2]}`:'';};
const isoJst=(date,totalMinutes)=>`${date}T${String(Math.floor(totalMinutes/60)).padStart(2,'0')}:${String(totalMinutes%60).padStart(2,'0')}:00+09:00`;

export function normalizeAndAggregateMinuteRows(rawRows=[]){
  assertLongOnlyResearchContract();
  const seen=new Map(),accepted=[],rejected=[];
  for(const row of rawRows){
    const sessionDate=dateOf(row),symbol=codeOf(row),time=hhmm(row?.Time??row?.time),minute=minutes(time);
    const open=number(row,'O','Open','open'),high=number(row,'H','High','high'),low=number(row,'L','Low','low'),close=number(row,'C','Close','close');
    const volume=number(row,'Vo','Volume','volume'),turnover=number(row,'Va','Turnover','turnover');
    const key=`${sessionDate}|${symbol}|${time}`;
    if(!/^\d{4}-\d{2}-\d{2}$/.test(sessionDate)||!symbol||!time||![open,high,low,close].every(x=>Number.isFinite(x)&&x>0)||high<Math.max(open,close)||low>Math.min(open,close)){
      rejected.push({sessionDate,symbol,time,reason:'INVALID_MINUTE'});continue;
    }
    const canonical={sessionDate,symbol,time,minute,open,high,low,close,volume:Number.isFinite(volume)?volume:0,turnover:Number.isFinite(turnover)?turnover:0};
    if(seen.has(key)){
      if(JSON.stringify(seen.get(key))!==JSON.stringify(canonical))throw new Error(`conflicting duplicate minute row: ${key}`);
      continue;
    }
    seen.set(key,canonical);accepted.push(canonical);
  }
  accepted.sort((a,b)=>a.sessionDate.localeCompare(b.sessionDate)||a.symbol.localeCompare(b.symbol)||a.minute-b.minute);
  const terminalAuctions=[],buckets=new Map();
  for(const row of accepted){
    if(row.minute===690||row.minute===930){terminalAuctions.push(Object.freeze({...row,timestampJst:isoJst(row.sessionDate,row.minute)}));continue;}
    const anchor=row.minute>=540&&row.minute<690?540:row.minute>=750&&row.minute<930?750:null;
    if(anchor===null){rejected.push({...row,reason:'OUTSIDE_CONTINUOUS_SESSION'});continue;}
    const start=anchor+Math.floor((row.minute-anchor)/5)*5,key=`${row.sessionDate}|${row.symbol}|${start}`;
    if(!buckets.has(key))buckets.set(key,[]);buckets.get(key).push(row);
  }
  const bars=[];
  for(const rows of buckets.values()){
    const first=rows[0],last=rows.at(-1);
    const anchor=first.minute>=750?750:540,barStart=anchor+Math.floor((first.minute-anchor)/5)*5;
    bars.push(Object.freeze({sessionDate:first.sessionDate,symbol:first.symbol,barStartJst:isoJst(first.sessionDate,barStart),availableAtJst:isoJst(first.sessionDate,barStart+5),open:first.open,high:Math.max(...rows.map(x=>x.high)),low:Math.min(...rows.map(x=>x.low)),close:last.close,volume:rows.reduce((a,x)=>a+x.volume,0),turnover:rows.reduce((a,x)=>a+x.turnover,0),observedMinutes:rows.length}));
  }
  bars.sort((a,b)=>a.sessionDate.localeCompare(b.sessionDate)||a.symbol.localeCompare(b.symbol)||a.barStartJst.localeCompare(b.barStartJst));
  return Object.freeze({bars:Object.freeze(bars),terminalAuctions:Object.freeze(terminalAuctions),audit:Object.freeze({rawRows:rawRows.length,acceptedMinuteRows:accepted.length,fiveMinuteBars:bars.length,terminalAuctionRows:terminalAuctions.length,rejectedRows:rejected.length}),timestampContract:TIMESTAMP_CONTRACT});
}

export function createIntegratedResearchDataset({partition,sourceManifest,dailyRows=[],masterRows=[],minuteRows=[]}={}){
  if(!partition)throw new Error('partition is required');
  const l0=assembleLongOnlyL0Rows({dailyRows,masterRows}),intraday=normalizeAndAggregateMinuteRows(minuteRows);
  const identity={partition,sourceManifest,l0Rows:l0.rows,intradayBars:intraday.bars,terminalAuctions:intraday.terminalAuctions,timestampContract:TIMESTAMP_CONTRACT};
  const datasetId=sha(identity),decisionData=Object.freeze({datasetId,partition,dailyRows:l0.rows,bars5m:intraday.bars,terminalAuctions:intraday.terminalAuctions,timestampContract:TIMESTAMP_CONTRACT});
  return Object.freeze({schemaVersion:1,datasetId,partition,sourceManifest:Object.freeze({...sourceManifest}),admissionAudit:l0.audit,intradayAudit:intraday.audit,
    consumers:Object.freeze({SELECTOR:decisionData,ENTRY:decisionData,EXIT:decisionData,ALLOCATION:decisionData,PORTFOLIO:decisionData}),
    evaluator:Object.freeze({...decisionData,evaluatorOnly:true}),safety:PHASE57_LONG_ONLY_SAFETY});
}

export default {assembleLongOnlyL0Rows,normalizeAndAggregateMinuteRows,createIntegratedResearchDataset};
