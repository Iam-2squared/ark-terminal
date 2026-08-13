import fs from 'node:fs';
import {P23_51_FRESH_HOLDOUT_POLICY,assertP2351Safety} from './phase57-p23-51-fresh-holdout-policy.js';

assertP2351Safety();
const JST=new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Tokyo',year:'numeric',month:'2-digit',day:'2-digit'});
const ymd=d=>{const p=Object.fromEntries(JST.formatToParts(d).map(x=>[x.type,x.value]));return `${p.year}-${p.month}-${p.day}`;};
const start=P23_51_FRESH_HOLDOUT_POLICY.temporalHoldoutStartJst;
const today=ymd(new Date());
const holidays=new Set(); // Intentionally empty: readiness uses weekdays only and can only overestimate, never consume.
function businessDates(a,b){const out=[];for(let d=new Date(`${a}T00:00:00+09:00`);ymd(d)<=b;d=new Date(d.getTime()+86400000)){const wd=new Intl.DateTimeFormat('en-US',{timeZone:'Asia/Tokyo',weekday:'short'}).format(d);const s=ymd(d);if(wd!=='Sat'&&wd!=='Sun'&&!holidays.has(s))out.push(s);}return out;}
const dates=businessDates(start,today);
const completedSessions=Math.max(0,dates.length-1); // Never count the current JST date as completed.
const required=P23_51_FRESH_HOLDOUT_POLICY.minimumCompletedSessions;
const readyByCalendar=completedSessions>=required;
const result={
  phase:'57.p23.51-holdout-readiness',
  status:readyByCalendar?'CALENDAR_READY_FOR_ONE_SHOT_MEASUREMENT':'WAIT_FOR_MORE_COMPLETED_SESSIONS',
  policy:{candidate:P23_51_FRESH_HOLDOUT_POLICY.candidate,baseline:P23_51_FRESH_HOLDOUT_POLICY.baseline,temporalHoldoutStartJst:start,minimumCompletedSessions:required,minimumScoredRows:P23_51_FRESH_HOLDOUT_POLICY.minimumScoredRows,minimumRowsPerDirection:P23_51_FRESH_HOLDOUT_POLICY.minimumRowsPerDirection},
  observed:{todayJst:today,completedWeekdaySessionsUpperBound:completedSessions},
  readyByCalendar,
  outcomeDataRead:false,
  scoresComputed:false,
  freshHoldoutConsumed:false,
  note:'This guard intentionally does not fetch market data or labels. Weekday count is only a conservative scheduling gate; the one-shot runner must separately verify actual completed sessions and sample minima before revealing metrics.',
  executionAllowed:false,brokerWriteAllowed:false,excelOrderWriteAllowed:false,rssOrderFunctionAllowed:false,liveTradingAllowed:false,automaticPromotionAllowed:false,productionUpdateAllowed:false
};
for(const k of ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed'])if(result[k]!==false)throw Error(k);
if(result.outcomeDataRead||result.scoresComputed||result.freshHoldoutConsumed)throw Error('P23.51 readiness must not consume holdout');
fs.mkdirSync('artifacts',{recursive:true});
fs.writeFileSync('artifacts/phase57-p23-51-holdout-readiness.json',JSON.stringify(result,null,2));
console.log(JSON.stringify(result,null,2));