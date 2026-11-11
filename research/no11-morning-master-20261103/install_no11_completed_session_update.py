#!/usr/bin/env python3
"""Permanent DATA update-path upgrade; no simulated clock, dates or Trade call.

The native calendar determines the latest completed cash session. A Friday full
sweep may therefore be collected on its following cash day, while original D100
validation excludes today's partial rows. Weekday pools use the same calendar.
Only the native data-launch function, read-only button status, date eligibility
and collector handoff are changed. Installed 47-slot and Clean logic is retained.
"""
from __future__ import annotations
import argparse
import base64
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import no11_nightly_resume as n
import no11_update_path as context

MARK = 'ARK_NO11_LATEST_COMPLETED_SESSION_DATA_V1'
RELATIVE = {
    'status': 'oneclick/oneclick_status.py',
    'native': 'engine/windows/Start-No11UnifiedLauncher.ps1',
    'planner': 'engine/tools/no11_weekly_g1_refresh.mjs',
    'weekly': 'engine/windows/Prepare-No11WeeklyAfterCloseReadOnly.ps1',
    'next': 'engine/windows/Prepare-No11NextSessionNightlyReadOnly.ps1',
}
OLD_WINDOW = """export function nightlyWindow(now){
  const local=now.slice(0,10),clock=now.slice(11,16);
  const date=lastCompletedSession(now);
  const sameEvening=isJpxCashTradingDay(local)&&date===local&&clock>='18:00';
  const followingPreopen=nextCashDate(date)===local&&clock<'08:30'&&!isoFriday(date);
  need(sameEvening||followingPreopen,'CURRENT_COMPLETED_CASH_SESSION_REQUIRED');
  return {date,now,followingPreopen};
}"""
NEW_WINDOW = """export function nightlyWindow(now){
  // ARK_NO11_LATEST_COMPLETED_SESSION_DATA_V1
  // DATA acquisition is not trade authorization. Keep the real observation
  // clock, and let the unchanged calendar select the last finalized session.
  const date=lastCompletedSession(now);
  const local=now.slice(0,10),clock=now.slice(11,16);
  const target=nextCashDate(date);
  need(date<=local&&target>=local,'CURRENT_COMPLETED_CASH_SESSION_REQUIRED');
  const followingPreopen=target===local&&clock<'08:30';
  const daytimeHistoricalRecovery=target===local&&date<local&&clock>='08:30';
  return {date,now,followingPreopen,daytimeHistoricalRecovery};
}"""
NATIVE_RUN = """function RunWeekly($cfg){
 # ARK_NO11_LATEST_COMPLETED_SESSION_DATA_V1
 # Use the SAME calendar as the physical collector; no hard-coded Monday,
 # pretend weekend, -Now override, synthetic source date or Trade call.
 $scheduleTool=Join-Path (Split-Path -Parent $PSScriptRoot) 'tools\\no11_weekly_g1_refresh.mjs'
 [void](LocalFile $scheduleTool 'DATA_CALENDAR')
 $scheduleLines=@(& node $scheduleTool schedule)
 Need ($LASTEXITCODE -eq 0 -and $scheduleLines.Count -eq 1) 'DATA_CALENDAR_FAILED'
 $schedule=([string]$scheduleLines[0]|ConvertFrom-Json)
 Need ($schedule.schemaId -ceq 'ARK_NO11_WEEKLY_REFRESH_SCHEDULE_V1' -and
       $schedule.orderTransmission -eq $false) 'DATA_CALENDAR_CONTRACT'
 $sourceDay=[string]$schedule.asOfSession
 $targetDay=[string]$schedule.sessionDate
 $list=LocalFile $cfg.fullSymbolsFile 'ORIGINAL_SYMBOLS'
 CheckExcel $cfg $false
 $arguments=@('-FullSymbolsFile',$list)
 $now=Clock
 if($now.DayOfWeek -in @([DayOfWeek]::Saturday,[DayOfWeek]::Sunday)){
  $arguments+=@('-WeekendFriday')
 }
 $sha=(Get-FileHash -LiteralPath $list -Algorithm SHA256).Hash.ToLowerInvariant()
 StartChild 'WEEKLY' $weekly $arguments $sha $sourceDay
 Write-Host ('NO11_UNIFIED_DATA_ASOF='+$sourceDay)
 Write-Host ('NO11_UNIFIED_DATA_TARGET='+$targetDay)
 Write-Host ('NO11_UNIFIED_DATA_SCOPE='+[string]$schedule.mode)
 Write-Host 'ORDER_TRANSMISSION=False'
}
"""
NEXT_CHECK = """ if($CompletedSessionUpdate){
  # ARK_NO11_LATEST_COMPLETED_SESSION_DATA_V1
  # The target pair comes from the real calendar, NOT from operator backdating.
  $calendarTool=Join-Path $base 'tools\\no11_weekly_g1_refresh.mjs'
  $calendarLines=@(& node $calendarTool schedule)
  Need ($LASTEXITCODE -eq 0 -and $calendarLines.Count -eq 1) 'COMPLETED_CALENDAR_FAILED'
  $calendar=([string]$calendarLines[0]|ConvertFrom-Json)
  Need ($calendar.schemaId -ceq 'ARK_NO11_WEEKLY_REFRESH_SCHEDULE_V1' -and
        $calendar.orderTransmission -eq $false -and
        $calendar.asOfSession -ceq $AsOfSession -and
        $calendar.sessionDate -ceq $SessionDate) 'COMPLETED_SESSION_PAIR_CHANGED'
  Write-Host ('NO11_NIGHTLY_ACTUAL_SOURCE_ASOF='+$AsOfSession)
  Write-Host ('NO11_NIGHTLY_ACTUAL_TARGET_SESSION='+$SessionDate)
 }elseif($WeekendFriday){"""


def need(ok, code):
    if not ok:
        raise ValueError('NO11_COMPLETED_UPDATE_' + code)


def transform(kind, raw):
    bom, newline, text = context.split_source(raw)
    if MARK in text:
        return raw
    if kind == 'planner':
        text = context.once(text, OLD_WINDOW, NEW_WINDOW)
    elif kind == 'native':
        start = text.find('function RunWeekly($cfg){')
        end = text.find('function StopRunningEngine(', start)
        need(start >= 0 and end > start, 'NATIVE_DATA_FUNCTION_MISSING')
        old = text[start:end]
        need(old.count("StartChild 'WEEKLY'") == 1 and 'CheckExcel $cfg $false' in old
             and "'WEEKLY_OR_DAILY_AFTERCLOSE_REQUIRED'" in old, 'NATIVE_DATA_FUNCTION_CHANGED')
        text = text[:start] + NATIVE_RUN + text[end:]
    elif kind == 'status':
        anchor = '    if now.weekday() >= 5:'
        inserted = """    # ARK_NO11_LATEST_COMPLETED_SESSION_DATA_V1
    # Enable only the DATA button; all existing Trade evaluation below remains.
    result['canRunNightly'] = (
        isinstance(binding.get('dailyCycleTool'), str)
        and isinstance(binding.get('dailyCycleRoot'), str)
        and Path(binding['dailyCycleTool']).is_file()
        and Path(binding['dailyCycleRoot']).is_dir())
"""
        text = context.once(text, anchor, inserted + anchor)
        compile(text, 'oneclick_status.py', 'exec')
    elif kind == 'weekly':
        # Full RSS path always validates the real as-of/target pair downstream.
        # Existing max47 params and weekday/Clean file references stay intact.
        anchor = '   \'-SessionDate\',$session,\'-AsOfSession\',$asOf,'
        text = context.once(text, anchor, "   '-SessionDate',$session,'-AsOfSession',$asOf,'-CompletedSessionUpdate',")
        text = '# ' + MARK + '\n' + text
    elif kind == 'next':
        text = context.once(text, ' [switch]$WeekendFriday,',
                            ' [switch]$WeekendFriday,\n [switch]$CompletedSessionUpdate,')
        text = context.once(text, ' if($WeekendFriday){', NEXT_CHECK)
    else:
        need(False, 'UNKNOWN_TARGET')
    return context.combine(bom, newline, text)


def installed_paths(store):
    b = n.read(store / 'automatic-inputs.json')
    need(b.get('schemaId') == 'ARK_NO11_AUTOMATIC_LAUNCHER_BINDING_V1'
         and b.get('orderTransmission') is False, 'BINDING_CONTRACT')
    engine = n.safe(b['engine'], True)
    paths = {k: n.safe(engine / rel[7:] if rel.startswith('engine/') else store / rel)
             for k, rel in RELATIVE.items()}
    return paths, n.safe(store / 'oneclick/Start-No11OneClick.ps1')


def quiet():
    n.no_workers()
    # Patch files only after the already-requested UI closure; never kill Excel.
    cmd = ("$ErrorActionPreference='Stop';try{$p=@(Get-CimInstance Win32_Process|Where-Object{"
           "$_.ProcessId -ne $PID -and $_.Name -match '^(powershell|pwsh)([.]exe)?$' -and "
           "[string]$_.CommandLine -match 'Start-No11OneClick[.]ps1|Start-No11UnifiedLauncher[.]ps1'"
           "});if($p.Count){exit 3};exit 0}catch{exit 4}")
    r = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', cmd],
                       capture_output=True, timeout=30, check=False)
    need(r.returncode == 0, 'CLOSE_UI_OR_PROCESS_QUERY_FAILED')


def replace(path, before, after):
    need(n.safe(path).read_bytes() == before, 'CONCURRENT_EDIT')
    temporary = None
    try:
        with tempfile.NamedTemporaryFile('wb', dir=path.parent, delete=False) as out:
            temporary = Path(out.name)
            out.write(after); out.flush(); os.fsync(out.fileno())
        need(path.read_bytes() == before, 'CONCURRENT_EDIT')
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def parse_candidates(after):
    with tempfile.TemporaryDirectory(prefix='ark-completed-update-') as tmp:
        root = Path(tmp)
        harness = root / 'parse.ps1'
        harness.write_text('param([string]$Target)\n$t=$null;$e=$null;[void][Management.Automation.Language.Parser]::ParseFile($Target,[ref]$t,[ref]$e);if($e.Count){exit 2}\n', encoding='utf-8')
        for kind, raw in after.items():
            suffix = '.mjs' if kind == 'planner' else '.py' if kind == 'status' else '.ps1'
            file = root / (kind + suffix)
            file.write_bytes(raw)
            if suffix == '.py':
                compile(raw.decode('utf-8-sig'), str(file), 'exec')
                continue
            args = ['node', '--check', str(file)] if suffix == '.mjs' else [
                'powershell.exe', '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass',
                '-File', str(harness), '-Target', str(file)]
            result = subprocess.run(args, capture_output=True, timeout=30, check=False)
            need(result.returncode == 0, 'CANDIDATE_PARSE_' + kind.upper())


def recover(journal, paths, ui, do_apply):
    if not journal.exists():
        return False
    state = n.checkpoint(journal)
    need(state.get('kind') == MARK and set(state.get('entries', {})) == set(paths), 'JOURNAL_KIND')
    need(n.digest(ui.read_bytes()) == state.get('whiteUiSha256'), 'WHITE_UI_EXTERNAL_CHANGE')
    values = {}
    for key, path in paths.items():
        row = state['entries'][key]
        need(row['path'] == str(path), 'JOURNAL_PATH')
        values[key] = tuple(base64.b64decode(row[x], validate=True) for x in ('before', 'after'))
        need(path.read_bytes() in values[key], 'JOURNAL_UNKNOWN_EDIT')
    if state['phase'] == 'COMPLETE':
        need(all(paths[k].read_bytes() == v[1] for k, v in values.items()), 'COMPLETE_CHANGED')
        return True
    need(state['phase'] in ('PREPARED', 'RESTORED') and do_apply, 'INTERRUPTED_INSTALL_REQUIRES_APPLY')
    for key in reversed(tuple(paths)):
        before, after = values[key]
        if paths[key].read_bytes() == after and before != after:
            replace(paths[key], after, before)
    state['phase'] = 'RESTORED'
    n.atomic(journal, state)
    return False


def install(store, do_apply=False, _test=False):
    store = n.safe(store, True)
    with n.exclusive(store / 'unified-refresh-install.lock'):
        paths, ui = installed_paths(store)
        journal = store / 'completed-session-update-transaction.json'
        if do_apply and not _test:
            quiet()
        if recover(journal, paths, ui, do_apply):
            return 'ALREADY_APPLIED'
        before = {k: p.read_bytes() for k, p in paths.items()}
        after = {k: transform(k, raw) for k, raw in before.items()}
        for key in paths:
            print('NO11_COMPLETED_UPDATE_SOURCE=' + key.upper() + '|READY', flush=True)
        if not do_apply:
            return 'READY'
        if not _test:
            parse_candidates(after)
            quiet()
        need(all(paths[k].read_bytes() == raw for k, raw in before.items()), 'CONCURRENT_EDIT')
        state = {'schemaId': n.SCHEMA, 'kind': MARK, 'phase': 'PREPARED',
                 'whiteUiSha256': n.digest(ui.read_bytes()), 'orderTransmission': False,
                 'entries': {k: {'path': str(paths[k]),
                     'before': base64.b64encode(before[k]).decode('ascii'),
                     'after': base64.b64encode(after[k]).decode('ascii')} for k in paths}}
        n.atomic(journal, state)
        try:
            # Publish calendar first, UI last. Existing jobs were checked above.
            for key in ('planner', 'next', 'weekly', 'native', 'status'):
                if before[key] != after[key]:
                    replace(paths[key], before[key], after[key])
            need(all(paths[k].read_bytes() == raw for k, raw in after.items()), 'READBACK')
            need(n.digest(ui.read_bytes()) == state['whiteUiSha256'], 'WHITE_UI_CHANGED')
            state['phase'] = 'COMPLETE'; n.atomic(journal, state)
        except Exception:
            recover(journal, paths, ui, True)
            raise
        return 'PASS'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--store', type=Path, required=True)
    p.add_argument('--apply', action='store_true')
    args = p.parse_args()
    try:
        need(os.name == 'nt', 'WINDOWS_ONLY')
        status = install(args.store, args.apply)
        print('NO11_COMPLETED_SESSION_UPDATE=' + status)
        print('NORMAL_UPDATE_BUTTON=LATEST_COMPLETED_SESSION')
        print('EXISTING_MAX47_CONFIGURATION_PRESERVED=True')
    except Exception as error:
        reason = str(error)
        if not re.fullmatch(r'NO11_[A-Z0-9_]+', reason):
            reason = 'NO11_COMPLETED_UPDATE_LOCAL_SOURCE_OR_RUNTIME'
        print('NO11_COMPLETED_SESSION_UPDATE=BLOCKED|' + reason)
        raise SystemExit(2)
    finally:
        print('WHITE_ONECLICK_GUI_CHANGED=False\nTRADE_LAUNCHED=False\nORDER_TRANSMISSION=False')

if __name__ == '__main__':
    main()
