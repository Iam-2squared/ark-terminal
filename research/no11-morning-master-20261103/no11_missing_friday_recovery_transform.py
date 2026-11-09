"""Real RSS Friday backfill with true observation times and calendar-derived as-of."""
from __future__ import annotations
import re

MARK='ARK_NO11_MISSING_PREVIOUS_FRIDAY_REAL_RSS_RECOVERY_V1'

def need(value,code):
    if not value:
        raise ValueError('NO11_REAL_FRIDAY_RECOVERY_'+code)

def once(s,old,new):
    need(s.count(old)==1,'SOURCE_CONTEXT_CHANGED')
    return s.replace(old,new,1)

FRIDAY_WINDOW="""
/** ARK_NO11_MISSING_PREVIOUS_FRIDAY_REAL_RSS_RECOVERY_V1.
 * Only recent real prior Friday. Never spoof observation time or date.
 */
export function latestFridayRecoveryWindow(now){
 const completed=lastCompletedSession(now);
 need(!isoFriday(completed),'NORMAL_FRIDAY_FULL_SCAN_REQUIRED');
 const days=previousJpxCashTradingDays(completed,4);
 const index=days.findIndex(isoFriday);
 need(index>=0,'FRIDAY_OUTSIDE_CURRENT_WEEK');
 const friday=days[index],elapsedCashDays=index+1;
 need(friday<completed&&nextCashDate(friday)<=completed&&
  elapsedCashDays>=1&&elapsedCashDays<=4,'FRIDAY_RECOVERY_SCOPE');
 return {schemaId:'ARK_NO11_REAL_RSS_FRIDAY_RECOVERY_WINDOW_V1',
  asOfSession:friday,sessionDate:nextCashDate(friday),
  observationDate:now.slice(0,10),latestCompletedSession:completed,
  elapsedCashDays,observationMustBeRealNow:true,
  historicalKnownAtCertified:false,productionReady:false,
  orderTransmission:false};
}
"""

def daily_tool(s):
    s=once(s,"import {createHash} from 'node:crypto';",
         "import {createHash} from 'node:crypto';\n"
         "import {previousJpxCashTradingDays,isJpxCashTradingDay} from '../runtime/jpx_cash_calendar_2026_2027.mjs';")
    s=once(s,"const here = path.dirname(fileURLToPath(import.meta.url));",
      """const here = path.dirname(fileURLToPath(import.meta.url));
const isoFriday=d=>new Date(d+'T00:00:00Z').getUTCDay()===5;
const nextCashDate=d=>{
 let day=new Date(d+'T00:00:00Z');
 for(let i=0;i<10;i++){
  day=new Date(day.getTime()+86400000);
  const candidate=day.toISOString().slice(0,10);
  if(isJpxCashTradingDay(candidate))return candidate;
 }
 throw Error('NO11_DAILY_NEXT_CASH_SESSION_MISSING');
};""")
    s=once(s,"export function makePlan(symbolBytes, now, codeSha256) {",
           FRIDAY_WINDOW+"\nexport function makePlan(symbolBytes, now, codeSha256, historicalFriday=false) {")
    s=once(s,"  const asOfSession = lastCompletedSession(now);",
           "  const recovery=historicalFriday?latestFridayRecoveryWindow(now):null;\n"
           "  const asOfSession = recovery?recovery.asOfSession:lastCompletedSession(now);")
    s=once(s,"    symbols, baselineAdded, priceBasisCertified: false, productionReady: false, orderTransmission: false};",
       """    symbols, baselineAdded,
    ...(recovery?{historicalFridayRecovery:true,
      historicalRecoveryObservedAtJst:now,
      historicalAsOfSession:asOfSession,
      laterRealSessionRowsMustBeExcludedFromG1:true,
      actualHistoricalKnownAtCertified:false}:{}),
    priceBasisCertified: false, productionReady: false, orderTransmission: false};""")
    s=once(s,
       "  if (!['plan','report'].includes(action) || rest.length % 2) throw Error('NO11_DAILY_ARGUMENTS_INVALID');",
       """  if(action==='recovery-window'){
    if(rest.length)throw Error('NO11_DAILY_RECOVERY_WINDOW_ARGUMENTS');
    console.log(JSON.stringify(latestFridayRecoveryWindow(jstNow())));
    return;
  }
  if (!['plan','report'].includes(action) || rest.length % 2) throw Error('NO11_DAILY_ARGUMENTS_INVALID');""")
    s=once(s,"    if (!['--root','--symbols','--run'].includes(rest[i]) || flags[rest[i]])",
      "    if (!['--root','--symbols','--run','--recover-last-friday'].includes(rest[i]) || flags[rest[i]])")
    s=once(s,
      "    const candidate = makePlan(fs.readFileSync(flags['--symbols']), jstNow(), codeIdentity());",
      """    if(flags['--recover-last-friday']!==undefined &&
       (action!=='plan'||flags['--recover-last-friday']!=='true'))
      throw Error('NO11_DAILY_RECOVERY_MODE_INVALID');
    const candidate = makePlan(fs.readFileSync(flags['--symbols']),
      jstNow(),codeIdentity(),flags['--recover-last-friday']==='true');""")
    return s

def daily_collector(s):
    need('ARK_NO11_FULL_PHYSICAL_RSS_47_V1' in s
         and 'ARK_NO11_AFTERCLOSE_CONFIGURED_THIRD_BOOK_V1' in s,
         'DAILY_MAX47_3BOOK_REQUIRED')
    s=once(s,' [switch]$OfflineSelfTest,',
      ' [switch]$OfflineSelfTest,\n [switch]$HistoricalFridayRecovery,')
    s=once(s," $text=(& node $tool plan --symbols $SymbolsFile --root $PrivateRoot | Out-String)",
       """ $planArgs=@('plan','--symbols',$SymbolsFile,'--root',$PrivateRoot)
 if($HistoricalFridayRecovery){$planArgs+=@('--recover-last-friday','true')}
 $text=(& node $tool @planArgs | Out-String)""")
    s=once(s," Write-Host ('NO11_DAILY_TARGET='+$work.plan.asOfSession)",
       """ if($HistoricalFridayRecovery){
  if($work.plan.historicalFridayRecovery -ne $true -or
     $work.plan.actualHistoricalKnownAtCertified -ne $false){
   throw 'NO11_DAILY_HISTORICAL_PROVENANCE_INVALID'
  }
  Write-Host ('NO11_DAILY_REAL_RSS_FRIDAY_HISTORICAL_OBSERVATION='+$work.plan.asOfSession)
  Write-Host 'NO11_DAILY_HISTORICAL_KNOWN_AT_CERTIFIED=False'
 }
 Write-Host ('NO11_DAILY_TARGET='+$work.plan.asOfSession)""")
    return s

def next_session(s):
    need('ARK_NO11_LATEST_COMPLETED_SESSION_DATA_V1' in s and
         'ARK_NO11_NEXT_SESSION_MAX47_V1' in s,
         'NEXT_MAX47_CALENDAR_REQUIRED')
    s=once(s,' [switch]$CompletedSessionUpdate,',
         ' [switch]$CompletedSessionUpdate,\n [switch]$HistoricalFridayRecovery,')
    s=once(s,' if($CompletedSessionUpdate){',
       """ if($HistoricalFridayRecovery){
  Need (-not $WeekendFriday -and -not $CompletedSessionUpdate) 'HISTORICAL_MODE_CONFLICT'
  $calendarTool=Join-Path $base 'tools\no11_rss_daily_trend_census.mjs'
  $recoveryLines=@(& node $calendarTool recovery-window)
  Need ($LASTEXITCODE -eq 0 -and $recoveryLines.Count -eq 1) 'HISTORICAL_WINDOW_MISSING'
  $recovery=([string]$recoveryLines[0]|ConvertFrom-Json)
  Need ($recovery.schemaId -ceq 'ARK_NO11_REAL_RSS_FRIDAY_RECOVERY_WINDOW_V1' -and
        $recovery.asOfSession -ceq $AsOfSession -and
        $recovery.sessionDate -ceq $SessionDate -and
        $recovery.observationMustBeRealNow -eq $true -and
        $recovery.historicalKnownAtCertified -eq $false -and
        $recovery.orderTransmission -eq $false) 'HISTORICAL_WINDOW_OR_PAIR_INVALID'
  Write-Host ('NO11_NIGHTLY_HISTORICAL_FRIDAY_OBSERVED_NOW='+$AsOfSession)
  Write-Host 'NO11_NIGHTLY_HISTORICAL_KNOWN_AT_CERTIFIED=False'
 }elseif($CompletedSessionUpdate){""")
    tick=chr(96)
    old=(" & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $dailyScript "+tick+"\n"
         "  -SymbolsFile $SymbolsFile -PrivateRoot $DailyRoot "+tick+"\n"
         "  -BatchSize $DailyBatchSize -WaitSeconds $DailyWaitSeconds")
    new=""" $dailyArgs=@('-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass',
  '-File',$dailyScript,'-SymbolsFile',$SymbolsFile,
  '-PrivateRoot',$DailyRoot,'-BatchSize',[string]$DailyBatchSize,
  '-WaitSeconds',[string]$DailyWaitSeconds)
 if($HistoricalFridayRecovery){$dailyArgs+=@('-HistoricalFridayRecovery')}
 & powershell.exe @dailyArgs"""
    s=once(s,old,new)
    s=once(s,
       " $identityLines=@(& node $identityTool plan --symbols $SymbolsFile --root $DailyRoot)",
       """ $identityArgs=@('plan','--symbols',$SymbolsFile,'--root',$DailyRoot)
 if($HistoricalFridayRecovery){$identityArgs+=@('--recover-last-friday','true')}
 $identityLines=@(& node $identityTool @identityArgs)""")
    return s

def weekly(s):
    need('ARK_NO11_FRIDAY_AND_WEEKDAY_MAX47_V1' in s and
         'ARK_NO11_LATEST_COMPLETED_SESSION_DATA_V1' in s,
         'WEEKLY_MAX47_CALENDAR_REQUIRED')
    anchor=" Need ($mode -ceq 'WEEKLY_POOL_CANDIDATES_ONLY') 'UNKNOWN_SCHEDULE_MODE'"
    insert=r"""
 # Missing this week's full-market Friday: recover only via REAL RssChart(D,100)
 # observed NOW; later observed rows are not Friday bars.
 if([string]::IsNullOrWhiteSpace($WeeklyRun) -and
    $WeeklySourcePolicy -ceq 'RSS_FULL_FRIDAY'){
  $recoverTool=Join-Path $base 'tools\no11_rss_daily_trend_census.mjs'
  $recoveryLines=@(& node $recoverTool recovery-window)
  Need ($LASTEXITCODE -eq 0 -and $recoveryLines.Count -eq 1) 'REAL_FRIDAY_RECOVERY_WINDOW_FAILED'
  $recovery=([string]$recoveryLines[0]|ConvertFrom-Json)
  $fridayDate=[string]$recovery.asOfSession
  $fridayTarget=[string]$recovery.sessionDate
  Need ($recovery.schemaId -ceq 'ARK_NO11_REAL_RSS_FRIDAY_RECOVERY_WINDOW_V1' -and
        $recovery.latestCompletedSession -ceq $asOf -and
        $recovery.orderTransmission -eq $false -and
        $recovery.historicalKnownAtCertified -eq $false) 'RECOVERY_CLOCK_OR_SCOPE_CHANGED'
  $completeFriday=@(
   foreach($dir in @(Get-ChildItem -LiteralPath $DailyRoot -Directory -Filter ('daily-'+$fridayDate+'-*') -ErrorAction SilentlyContinue)){
    try{
     $p=Join-Path $dir.FullName 'plan.json'
     $s=Join-Path $dir.FullName 'sources'
     if(-not (Test-Path -LiteralPath $p -PathType Leaf) -or
        -not (Test-Path -LiteralPath $s -PathType Container)){continue}
     $v=Get-Content -LiteralPath $p -Raw -Encoding UTF8|ConvertFrom-Json
     if($v.schemaId -cne 'ARK_NO11_RSS_DAILY_CENSUS_PLAN_V1' -or
        $v.asOfSession -cne $fridayDate -or
        @($v.symbols).Count -ne 4328){continue}
     if(@(Get-ChildItem -LiteralPath $s -File -Filter '*.json').Count -eq 4328){
      [pscustomobject]@{run=$dir.FullName;asOf=$fridayDate}
     }
    }catch{continue}
   }
  )
  if($completeFriday.Count -eq 0){
   Write-Host ('NO11_WEEKLY_RECOVER_MISSING_FRIDAY=REAL_RSS_FULL_4328|ASOF_'+$fridayDate)
   $rargs=@('-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass',
     '-File',$full,'-HistoricalFridayRecovery',
     '-AsOfSession',$fridayDate,'-SessionDate',$fridayTarget,
     '-SymbolsFile',$FullSymbolsFile,'-DailyRoot',$DailyRoot,
     '-PythonExecutable',$PythonExecutable,
     '-DailyBatchSize',[string]$FullBatchSize,
     '-DailyWaitSeconds',[string]$FullWaitSeconds,
     '-MinuteBatchSize',[string]$MinuteBatchSize,
     '-MinuteWaitSeconds',[string]$MinuteWaitSeconds)
   & powershell.exe @rargs
   Need ($LASTEXITCODE -eq 0) 'REAL_FRIDAY_4328_RECOVERY_INCOMPLETE'
   Write-Host ('NO11_WEEKLY_RECOVER_MISSING_FRIDAY=D100_AND_PREVIOUS_DONE|ASOF_'+$fridayDate)
  }else{
   Write-Host ('NO11_WEEKLY_RECOVER_MISSING_FRIDAY=EXISTING_4328_CHECKED_DOWNSTREAM|ASOF_'+$fridayDate)
  }
 }
"""
    s=once(s,anchor,anchor+'\n'+insert)
    old="  Need ($choices.Count -gt 0) 'COMPLETE_FULL_SWEEP_NOT_FOUND'"
    new="""  if($WeeklySourcePolicy -ceq 'RSS_FULL_FRIDAY' -and $mode -ceq 'WEEKLY_POOL_CANDIDATES_ONLY'){
   $choices=@($choices|Where-Object {$_.date -ceq $fridayDate})
  }
  Need ($choices.Count -gt 0) 'COMPLETE_CURRENT_FRIDAY_FULL_SWEEP_NOT_FOUND'"""
    s=once(s,old,new)
    return s

def worker(s):
    need('ARK_NO11_CIRCUIT_AUDIT_V1' in s and
         'ARK_NO11_NIGHTLY_RESUME_WORKER_PROBE_V2' in s and
         'DataUpdate-' in s,'WORKER_INTEGRATED_REQUIRED')
    return once(s,"    work = root / 'resumable-nightly' / (asof + '_' + target)",
       """    # Old failed as-of checkpoint remains intact for audit, never erased.
    work = root / 'resumable-nightly' / (asof + '_' + target + '-real-friday-v1')""")

def transform(kind,raw):
    bom=raw.startswith(b'\xef\xbb\xbf')
    s=raw.decode('utf-8-sig')
    newline='\r\n' if '\r\n' in s else '\n'
    s=s.replace('\r\n','\n');need('\r' not in s,'LINE_ENDINGS')
    if MARK in s:return raw
    make={'dailyTool':daily_tool,'dailyCollector':daily_collector,
          'next':next_session,'weekly':weekly,'worker':worker}.get(kind)
    need(make is not None,'UNKNOWN_TARGET')
    out=make(s)
    need(MARK in out,'MARKER_MISSING')
    if kind=='worker':compile(out,kind,'exec')
    if kind in ('next','weekly','dailyCollector'):
        need('ORDER_TRANSMISSION=False' in out,'DATA_ONLY_CHECK_MISSING')
    return (b'\xef\xbb\xbf' if bom else b'')+out.replace('\n',newline).encode('utf-8')
