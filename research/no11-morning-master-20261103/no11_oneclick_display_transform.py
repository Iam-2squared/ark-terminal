"""Versioned presentation-only migration for existing white OneClick installs.

Do not replace the installed launcher with a repository theme. Preserve its
layout, colors, action callbacks, approval prompts, scheduling and source
checks byte-for-byte outside the two precisely identified display regions.
"""
from __future__ import annotations

import re

MARK = 'ARK_NO11_ONECLICK_BILINGUAL_DISPLAY_V2'
OLD_TOOL = "$statusTool=Join-Path $PSScriptRoot 'oneclick_status.py'"
NEW_TOOL = "$statusTool=Join-Path $PSScriptRoot 'no11_oneclick_display_v2.py'"
OLD_DISPLAY = """  $trading=if($s.mode -ceq 'AFTER_CLOSE'){'Closed for today'}elseif($s.canRequestTrade -eq $true){'Awaiting same-day approval'}else{'Not available'}
  $preopen=CanQueuePreopen $s
  $reserved=PreopenReserved $s
  if($preopen){$trading='08:30 STANDBY READY - 09:00 AUTO START'}
  if($reserved){$trading=if($s.reason -ceq 'ALREADY_STARTED_TODAY'){'TRADE REQUESTED - check logs'}else{'09:00 START RESERVED - check logs'}}
  $recovery='No current recovery request'
  if($s.PSObject.Properties.Name -contains 'runHealth'){
   $rh=$s.runHealth
   $attempt=if($rh.PSObject.Properties.Name -contains 'collectorAttempt'){$rh.collectorAttempt}else{'Unknown'}
   $recovery='Review required - collector: '+$attempt
   if($rh.PSObject.Properties.Name -contains 'entryHalted' -and $rh.entryHalted -eq $true){$trading='ENTRY HALTED - review required'}
  }
  $status.Text=('SESSION     '+$s.sessionDate+[Environment]::NewLine+
                'TRADING     '+$trading+[Environment]::NewLine+
                'DATA        '+(UiReason ([string]$s.reason))+[Environment]::NewLine+
                'RECOVERY    '+$recovery)
"""
NEW_DISPLAY = """  # ARK_NO11_ONECLICK_BILINGUAL_DISPLAY_V2
  # These two authorization inputs and the Enabled expressions below are unchanged.
  $preopen=CanQueuePreopen $s
  $reserved=PreopenReserved $s
  Need ($s.PSObject.Properties.Name -contains 'presentation') 'DISPLAY_V2_MISSING'
  $view=$s.presentation
  Need ($view.schemaId -ceq 'ARK_NO11_ONECLICK_PRESENTATION_V2' -and
        $view.readOnly -eq $true -and $view.orderTransmission -eq $false) 'DISPLAY_V2_UNSAFE'
  $status.Text=([string]$view.text).Replace("`n",[Environment]::NewLine)
  $status.AutoEllipsis=$true
  $trade.Text=[string]$view.buttons.trade
  $nightly.Text=[string]$view.buttons.nightly
  $refresh.Text=[string]$view.buttons.refresh
  $review.Text=[string]$view.buttons.review
  $logsButton.Text=[string]$view.buttons.logs
  $script:No11DisplayTip.SetToolTip($status,[string]$view.details)
"""
TOOLTIP = """# Presentation only: no new callbacks, timers or trading processes.
$script:No11DisplayTip=New-Object System.Windows.Forms.ToolTip
$script:No11DisplayTip.AutoPopDelay=20000
$script:No11DisplayTip.InitialDelay=300
$script:No11DisplayTip.ReshowDelay=100
"""


def norm(raw):
    bom = b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b''
    text = raw.decode('utf-8-sig')
    newline = '\r\n' if '\r\n' in text else '\n'
    text = text.replace('\r\n', '\n')
    if '\r' in text:
        raise ValueError('NO11_DISPLAY_MIGRATION_BARE_CARRIAGE_RETURN')
    return bom, text, newline


def replace_regions(source, replacements):
    """Match canonical anchors, but splice ORIGINAL offsets, never whole-file EOLs."""
    canonical = source.replace('\r\n', '\n')
    if '\r' in canonical:
        raise ValueError('NO11_DISPLAY_MIGRATION_BARE_CARRIAGE_RETURN')
    offsets, i = [0], 0
    while i < len(source):
        i += 2 if source.startswith('\r\n', i) else 1
        offsets.append(i)
    edits = []
    default_eol = '\r\n' if '\r\n' in source else '\n'
    for before, after in replacements:
        if canonical.count(before) != 1:
            raise ValueError('NO11_DISPLAY_MIGRATION_UNKNOWN_DISPLAY_SOURCE')
        start = canonical.index(before)
        a, b = offsets[start], offsets[start + len(before)]
        original_region = source[a:b]
        eol = '\r\n' if '\r\n' in original_region else '\n' if '\n' in original_region else default_eol
        # Mixed endings INSIDE a rewritten anchor are unknown; outside are kept.
        if '\r\n' in original_region and '\n' in original_region.replace('\r\n', ''):
            raise ValueError('NO11_DISPLAY_MIGRATION_MIXED_ANCHOR_NEWLINES')
        edits.append((a, b, after.replace('\n', eol)))
    edits.sort()
    if any(edits[k][1] > edits[k + 1][0] for k in range(len(edits) - 1)):
        raise ValueError('NO11_DISPLAY_MIGRATION_OVERLAPPING_REGIONS')
    for a, b, replacement in reversed(edits):
        source = source[:a] + replacement + source[b:]
    return source


def transform(raw):
    bom, canonical, _ = norm(raw)
    source = raw.decode('utf-8-sig')
    reverse_regions = ((NEW_DISPLAY, OLD_DISPLAY), (NEW_TOOL, OLD_TOOL), (TOOLTIP, ''))
    if MARK in canonical:
        if canonical.count(MARK) != 1 or canonical.count(NEW_DISPLAY) != 1 or canonical.count(NEW_TOOL) != 1 or canonical.count(TOOLTIP) != 1:
            raise ValueError('NO11_DISPLAY_MIGRATION_CHANGED_INSTALLED_REGION')
        original = replace_regions(source, reverse_regions)
        if transform(bom + original.encode('utf-8')) != raw:
            raise ValueError('NO11_DISPLAY_MIGRATION_DERIVATION_CHANGED')
        return raw
    if (canonical.count(OLD_TOOL) != 1 or canonical.count(OLD_DISPLAY) != 1
            or canonical.count('function RefreshUi{') != 1 or NEW_TOOL in canonical):
        raise ValueError('NO11_DISPLAY_MIGRATION_UNKNOWN_DISPLAY_SOURCE')
    for anchor in ("$trade.Add_Click({", "$nightly.Add_Click({", "$review.Add_Click({",
                   "$logsButton.Add_Click({", "$refresh.Add_Click({RefreshUi})",
                   "$timer.Add_Tick({RefreshUi})", "function CanQueuePreopen($s){",
                   "function PreopenReserved($s){", "[void]$form.ShowDialog()"):
        if canonical.count(anchor) != 1:
            raise ValueError('NO11_DISPLAY_MIGRATION_CONTROL_SOURCE_CHANGED')
    guards = re.findall(r'^  \$(?:trade|nightly|review)[.]Enabled=.*$', canonical, re.M)
    changed = replace_regions(source, ((OLD_TOOL, NEW_TOOL), (OLD_DISPLAY, NEW_DISPLAY),
                                      ('function RefreshUi{', TOOLTIP + 'function RefreshUi{')))
    normalized = changed.replace('\r\n', '\n')
    if re.findall(r'^  \$(?:trade|nightly|review)[.]Enabled=.*$', normalized, re.M) != guards:
        raise ValueError('NO11_DISPLAY_MIGRATION_AUTHORIZATION_CHANGED')
    if replace_regions(changed, reverse_regions) != source:
        raise ValueError('NO11_DISPLAY_MIGRATION_OUTSIDE_SCOPE')
    return bom + changed.encode('utf-8')
