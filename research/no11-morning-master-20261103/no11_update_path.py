#!/usr/bin/env python3
"""One cohesive launcher/collector throughput fix. Retain all user-local UI layout.

Patch the *actual* native Weekly launcher (weekend enable and resume), OneClick
read-only status, Friday 4328 D100, weekday D100 and previous 1M collectors.
No trade/entry/EXIT selection code is modified; no order functions are called.
All edits are exact-source, BOM/CRLF-preserving and idempotent.
"""
from __future__ import annotations

from pathlib import Path

MARKER = 'ARK_NO11_WEEKEND_WEEKLY_RESUME_V1'
FILES = {
    'status': 'oneclick/oneclick_status.py',
    'native': 'engine/windows/Start-No11UnifiedLauncher.ps1',
    'weekly': 'engine/windows/Prepare-No11WeeklyAfterCloseReadOnly.ps1',
    'next': 'engine/windows/Prepare-No11NextSessionNightlyReadOnly.ps1',
    'daily': 'engine/windows/Run-No11RssDailyTrendCensusReadOnly.ps1',
    'pool': 'engine/windows/Run-No11WeeklyCandidateRefreshReadOnly.ps1',
    'previous': 'engine/windows/Prepare-No11PreviousArchiveReadOnly.ps1',
    'minutes': 'engine/windows/Capture-No11RssTrainingBatchReadOnly.ps1',
}

def require(v, reason):
    if not v:
        raise ValueError('NO11_UPDATE_PATH_' + reason)

def once(text, needle, value):
    require(text.count(needle) == 1, 'SOURCE_ANCHOR_CHANGED')
    return text.replace(needle, value, 1)

def split_source(raw):
    bom = raw.startswith(b'\xef\xbb\xbf')
    s = raw.decode('utf-8-sig')
    nl = '\r\n' if '\r\n' in s else '\n'
    s = s.replace('\r\n', '\n')
    require('\r' not in s, 'UNSUPPORTED_EOL')
    return bom, nl, s

def combine(bom, nl, text):
    return (b'\xef\xbb\xbf' if bom else b'') + text.replace('\n', nl).encode('utf-8')

def high_capacity(text, *, is_daily):
    # Chart RSS has 50 physical slots. Keep three existing reserved slots.
    # In particular, never silently create 47 NEW functions when the original
    # account/market books already occupy some chart functions.
    if is_daily:
        old = "  if($existing+$BatchSize -gt 50){throw 'NO11_DAILY_CHART_CAPACITY_EXCEEDED'}"
        new = """  # ARK_NO11_FULL_PHYSICAL_RSS_47_V1
  $physical=[Math]::Min($BatchSize,50-$existing-3)
  if($physical -lt 1){throw 'NO11_DAILY_CHART_CAPACITY_EXCEEDED'}
  Write-Host ('NO11_DAILY_EFFECTIVE_RSS_CONCURRENCY={0}|LIMIT=50|RESERVED=3|EXISTING={1}' -f $physical,$existing)"""
        text = once(text, old, new)
        text = once(text,
            'for($offset=0;$offset -lt $remaining.Count;$offset+=$BatchSize)',
            'for($offset=0;$offset -lt $remaining.Count;$offset+=$physical)')
        text = once(text,
            '$remaining[$offset..([Math]::Min($offset+$BatchSize-1,$remaining.Count-1))]',
            '$remaining[$offset..([Math]::Min($offset+$physical-1,$remaining.Count-1))]')
    else:
        old = " if($existing+$BatchSize -gt 50){throw 'NO11_BATCH_CHART_CAPACITY_EXCEEDED'}"
        new = """ # ARK_NO11_FULL_PHYSICAL_RSS_47_V1
 $physical=[Math]::Min($BatchSize,50-$existing-3)
 if($physical -lt 1){throw 'NO11_BATCH_CHART_CAPACITY_EXCEEDED'}
 Write-Host ('NO11_MINUTE_EFFECTIVE_RSS_CONCURRENCY={0}|LIMIT=50|RESERVED=3|EXISTING={1}' -f $physical,$existing)"""
        text = once(text, old, new)
        text = once(text,
            'for($offset=0;$offset -lt $symbols.Count;$offset+=$BatchSize)',
            'for($offset=0;$offset -lt $symbols.Count;$offset+=$physical)')
        text = once(text,
            '$symbols[$offset..([Math]::Min($offset+$BatchSize-1,$symbols.Count-1))]',
            '$symbols[$offset..([Math]::Min($offset+$physical-1,$symbols.Count-1))]')
    return text

def patch_native(text):
    old = """ Need (-not (Test-Path -LiteralPath $marker -PathType Leaf)) ($kind+'_ALREADY_STARTED_NO_DUPLICATE')
 $receipt=[ordered]@{"""
    new = """ # ARK_NO11_WEEKEND_WEEKLY_RESUME_V1
 # A previous DATA-only launch marker is preserved, not treated as a completed
 # job. Its identical Friday/source can be retried only after old workers exit.
 # TRADE markers retain the original strictly-once behavior.
 $existingWeekly=$false
 if(Test-Path -LiteralPath $marker -PathType Leaf){
  Need ($kind -ceq 'WEEKLY') ($kind+'_ALREADY_STARTED_NO_DUPLICATE')
  $prior=Get-Content -LiteralPath $marker -Raw -Encoding UTF8|ConvertFrom-Json
  Need ($prior.schemaId -ceq 'ARK_NO11_UNIFIED_START_REQUEST_V1' -and
        $prior.kind -ceq 'WEEKLY' -and $prior.asOfDate -ceq $date -and
        $prior.sourceSha256 -ceq $sourceDigest) 'WEEKLY_OLD_REQUEST_DIFFERENT'
  # No duplicate collectors. Never delete or rewrite the earlier marker.
  $jobs=@(Get-CimInstance Win32_Process -ErrorAction Stop | Where-Object {
   $_.ProcessId -ne $PID -and
   $_.Name -match '^(powershell|pwsh|python|pythonw)([.]exe)?$' -and
   [string]$_.CommandLine -match 'Run-No11NightlyCycle[.]ps1|Run-No11ResumableNightly[.]ps1|Prepare-No11WeeklyAfterCloseReadOnly[.]ps1|Prepare-No11NextSessionNightlyReadOnly[.]ps1|no11_nightly_resume[.]py|Run-No11RssDailyTrendCensusReadOnly[.]ps1|Capture-No11RssTrainingBatchReadOnly[.]ps1'
  })
  Need ($jobs.Count -eq 0) 'WEEKLY_PREVIOUS_WORKER_STILL_RUNNING'
  $existingWeekly=$true
  Write-Host 'NO11_UNIFIED_WEEKLY_RESUME_ORIGINAL_MARKER_PRESERVED=True'
 }
 if(-not $existingWeekly){
 $receipt=[ordered]@{"""
    text = once(text, old, new)
    old = """ finally{$stream.Dispose()}
 $cmd=@('-NoLogo'"""
    new = """ finally{$stream.Dispose()}
 }
 $cmd=@('-NoLogo'"""
    text = once(text, old, new)
    # Leave RunTrade, UI and user interface exactly as installed.
    return text

def patch_status(text):
    old = '''    if now.weekday() >= 5:
        result["reason"] = "NON_TRADING_DAY"
        return result'''
    new = '''    # ARK_NO11_WEEKEND_FRIDAY_ONECLICK_V1
    # The WEEKLY button is a data collector and is valid on Sat/Sun.
    # The original native launcher resolves the REAL prior Friday; never
    # authorize Trade or create a synthetic weekend market session.
    if now.weekday() >= 5:
        if (isinstance(binding.get("dailyCycleTool"), str)
                and isinstance(binding.get("dailyCycleRoot"), str)
                and Path(binding["dailyCycleTool"]).is_file()
                and Path(binding["dailyCycleRoot"]).is_dir()):
            result.update(mode="WEEKEND_FRIDAY_DATA",
                          reason="PREVIOUS_FRIDAY_RSS_REFRESH_AVAILABLE",
                          canRunNightly=True)
        else:
            result["reason"] = "NIGHTLY_NOT_INSTALLED"
        return result'''
    return once(text, old, new)

def transform(kind, raw):
    require(kind in FILES, 'UNKNOWN_SOURCE_KIND')
    bom, nl, text = split_source(raw)
    markers = {
        'native': MARKER,
        'status': 'ARK_NO11_WEEKEND_FRIDAY_ONECLICK_V1',
        'daily': 'ARK_NO11_FULL_PHYSICAL_RSS_47_V1',
        'minutes': 'ARK_NO11_FULL_PHYSICAL_RSS_47_V1',
        'weekly': 'ARK_NO11_FRIDAY_AND_WEEKDAY_MAX47_V1',
        'next': 'ARK_NO11_NEXT_SESSION_MAX47_V1',
        'pool': 'ARK_NO11_WEEKDAY_POOL_MAX47_V1',
        'previous': 'ARK_NO11_PREVIOUS_1M_MAX47_V1',
    }
    if markers[kind] in text:
        require(text.count(markers[kind]) == 1, 'ALREADY_PATCHED_AMBIGUOUS')
        return raw
    if kind == 'status':
        text = patch_status(text)
    elif kind == 'native':
        require('ARK_NO11_AFTERCLOSE_CONFIGURED_THIRD_BOOK_V1' in text
                and "'Run-No11NightlyCycle.ps1'" in text, 'INSTALLED_NATIVE_NOT_READY')
        text = patch_native(text)
    elif kind == 'weekly':
        text = once(text,
            ' [ValidateRange(1,20)][int]$FullBatchSize=10,',
            ' # ARK_NO11_FRIDAY_AND_WEEKDAY_MAX47_V1\n [ValidateRange(1,47)][int]$FullBatchSize=47,')
        text = once(text, ' [ValidateRange(1,47)][int]$RefreshBatchSize=30,',
                          ' [ValidateRange(1,47)][int]$RefreshBatchSize=47,')
        text = once(text, ' [ValidateRange(1,20)][int]$MinuteBatchSize=5,',
                          ' [ValidateRange(1,47)][int]$MinuteBatchSize=47,')
    elif kind == 'next':
        text = once(text, ' [ValidateRange(1,20)][int]$DailyBatchSize=20,',
                          ' # ARK_NO11_NEXT_SESSION_MAX47_V1\n [ValidateRange(1,47)][int]$DailyBatchSize=47,')
        text = once(text, ' [ValidateRange(1,20)][int]$MinuteBatchSize=5,',
                          ' [ValidateRange(1,47)][int]$MinuteBatchSize=47,')
    elif kind == 'previous':
        text = once(text, ' [ValidateRange(1,20)][int]$BatchSize=20,',
                          ' # ARK_NO11_PREVIOUS_1M_MAX47_V1\n [ValidateRange(1,47)][int]$BatchSize=47,')
    elif kind == 'pool':
        text = once(text, ' [ValidateRange(1,47)][int]$BatchSize=30,',
                          ' # ARK_NO11_WEEKDAY_POOL_MAX47_V1\n [ValidateRange(1,47)][int]$BatchSize=47,')
        # The optional old AutoMax switch was counterproductive for a normal
        # full-throughput run: it forced initial 5/10/20/40-call ramps.
        # Start at the physically available ceiling, just like the standard
        # path. Keep automatic reduction ONLY on real busy/partial results.
        text = once(text,
            '  $physical=if($AutoMaxThroughput){[Math]::Min(5,$ceiling)}else{$ceiling}',
            '  $physical=$ceiling')
        # GroupSize is a reporting interval, NOT a hard RSS call boundary.
        # E.g. positions 94..140 must be a full 47-function wave, rather than
        # 6 functions to finish the first logical 100-symbol group.
        text = once(text,
            '   $waveEnd=NextWaveEnd $offset $remaining.Count $GroupSize $physical',
            '   $waveEnd=[Math]::Min($remaining.Count,$offset+$physical)')
        # After an actual degraded wave, restore maximal utilization
        # immediately after the next clean wave, not through artificial ramps.
        old = """   }elseif($physical -lt $ceiling){
    $fullWaves++
    if($AutoMaxThroughput -or $fullWaves -ge 2){
     $physical=if($AutoMaxThroughput){
      NextAutoMaxBatch $physical $ceiling $true
     }else{
      [Math]::Min($ceiling,$physical+5)
     }
     $fullWaves=0
     Write-Host ('NO11_DAILY_BATCH_TUNE=FULL_WAVES_RAISED_TO_{0}' -f $physical)
    }
   }"""
        new = """   }elseif($physical -lt $ceiling){
    # ARK_NO11_POOL_ALWAYS_MAX_AVAILABLE_V1
    # A verified clean wave means temporary RSS degradation has recovered.
    # Restore the full available slot budget for the NEXT wave.
    $physical=$ceiling
    $fullWaves=0
    Write-Host ('NO11_DAILY_BATCH_TUNE=CLEAN_WAVE_RESTORED_MAX_{0}' -f $physical)
   }"""
        text = once(text, old, new)
        # Group-complete telemetry may no longer land on a perfect hundred.
        # Keep progress visible whenever a logical group boundary is crossed.
        text = once(text,
            '   if($offset -eq $remaining.Count -or $offset % $GroupSize -eq 0){',
            '   if($offset -eq $remaining.Count -or [Math]::Floor(($offset-1)/$GroupSize) -ne [Math]::Floor(($offset-$batch.Count)/$GroupSize)){')
        text = once(text,
            "  Write-Host ('NO11_DAILY_BATCH_POLICY=GROUP_{0}|PHYSICAL_MAX_{1}|ORIGINAL_CHARTS_{2}|RESERVE_3|LIMIT_50' -f $GroupSize,$ceiling,$existing)",
            "  Write-Host ('NO11_DAILY_BATCH_POLICY=GROUP_{0}|PHYSICAL_MAX_{1}|ORIGINAL_CHARTS_{2}|RESERVE_3|LIMIT_50|FIRST_WAVE_MAX=True|GROUP_SPLIT_DISABLED=True' -f $GroupSize,$ceiling,$existing)")
    elif kind == 'daily':
        text = once(text, ' [ValidateRange(1,20)][int]$BatchSize=20,',
                          ' [ValidateRange(1,47)][int]$BatchSize=47,')
        text = high_capacity(text, is_daily=True)
    elif kind == 'minutes':
        text = once(text, ' [ValidateRange(1,20)][int]$BatchSize=20,',
                          ' [ValidateRange(1,47)][int]$BatchSize=47,')
        text = high_capacity(text, is_daily=False)
    require(markers[kind] in text, 'MARKER_MISSING')
    if kind in ('daily', 'minutes'):
        require(text.count('$physical=[Math]::Min($BatchSize,50-$existing-3)') == 1
                and '47' in text, 'PHYSICAL_CAP_NOT_PROVEN')
    return combine(bom, nl, text)
