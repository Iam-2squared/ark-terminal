/**
 * JPX cash-equity closures for the published 2026/2027 calendars.
 * Authority (read-only): https://www.jpx.co.jp/english/corporate/about-jpx/calendar/index.html
 * Reviewed 2026-10-11. Futures/derivatives holiday trading does NOT make
 * Japanese cash equities tradable. Never infer unknown calendar years.
 * Calendar changes must be reviewed and versioned; this is not live provider evidence.
 */
export const JPX_CASH_CALENDAR_SOURCE='https://www.jpx.co.jp/english/corporate/about-jpx/calendar/index.html';
const CLOSED_DAYS=Object.freeze({
  2026:new Set([
    '2026-01-01','2026-01-02','2026-01-03','2026-01-12',
    '2026-02-11','2026-02-23','2026-03-20',
    '2026-04-29','2026-05-03','2026-05-04','2026-05-05','2026-05-06',
    '2026-07-20','2026-08-11','2026-09-21','2026-09-22','2026-09-23',
    '2026-10-12','2026-11-03','2026-11-23','2026-12-31'
  ]),
  2027:new Set([
    '2027-01-01','2027-01-02','2027-01-03','2027-01-11',
    '2027-02-11','2027-02-23','2027-03-21','2027-03-22',
    '2027-04-29','2027-05-03','2027-05-04','2027-05-05',
    '2027-07-19','2027-08-11','2027-09-20','2027-09-23',
    '2027-10-11','2027-11-03','2027-11-23','2027-12-31'
  ])
});
const invalid=code=>{throw Error(code);};
const utcDayMs=day=>{
  if(typeof day!=='string'||!/^20\d{2}-\d{2}-\d{2}$/.test(day))
    invalid('NO12_JPX_CASH_DAY_INVALID');
  const ms=Date.parse(day+'T00:00:00Z');
  if(!Number.isFinite(ms)||new Date(ms).toISOString().slice(0,10)!==day)
    invalid('NO12_JPX_CASH_DAY_INVALID');
  return ms;
};
export function isJpxCashTradingDay(day){
  const ms=utcDayMs(day),year=Number(day.slice(0,4));
  if(!Object.prototype.hasOwnProperty.call(CLOSED_DAYS,year))
    invalid('NO12_JPX_CASH_CALENDAR_YEAR_UNPINNED');
  const weekday=new Date(ms).getUTCDay();
  return weekday!==0&&weekday!==6&&!CLOSED_DAYS[year].has(day);
}
export function previousJpxCashTradingDays(anchorDay,count){
  const anchorMs=utcDayMs(anchorDay);
  if(!Number.isInteger(count)||count<1||count>15)
    invalid('NO12_JPX_CASH_CALENDAR_REQUEST_INVALID');
  const result=[];
  for(let offset=1;offset<=60&&result.length<count;offset++){
    const day=new Date(anchorMs-offset*86400000).toISOString().slice(0,10);
    if(isJpxCashTradingDay(day))result.push(day);
  }
  if(result.length!==count)invalid('NO12_JPX_CASH_CALENDAR_INCOMPLETE');
  return Object.freeze(result);
}
