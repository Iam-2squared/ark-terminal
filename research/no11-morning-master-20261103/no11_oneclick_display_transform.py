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
        raise ValueError('NO11_DISPLAY_MIGRATION_MIXED_NEWLINES')
    return bom, text, newline


def transform(raw):
    bom, text, newline = norm(raw)
    if MARK in text:
        if text.count(MARK) != 1 or text.count(NEW_DISPLAY) != 1 or text.count(NEW_TOOL) != 1 or text.count(TOOLTIP) != 1:
            raise ValueError('NO11_DISPLAY_MIGRATION_CHANGED_INSTALLED_REGION')
        old = text.replace(NEW_DISPLAY, OLD_DISPLAY, 1).replace(NEW_TOOL, OLD_TOOL, 1).replace(TOOLTIP, '', 1)
        restored = bom + old.replace('\n', newline).encode('utf-8')
        if transform(restored) != raw:
            raise ValueError('NO11_DISPLAY_MIGRATION_DERIVATION_CHANGED')
        return raw
    if (text.count(OLD_TOOL) != 1 or text.count(OLD_DISPLAY) != 1
            or text.count('function RefreshUi{') != 1 or NEW_TOOL in text):
        raise ValueError('NO11_DISPLAY_MIGRATION_UNKNOWN_DISPLAY_SOURCE')
    # Only an actual OneClick control surface is eligible, not arbitrary scripts.
    for anchor in ("$trade.Add_Click({", "$nightly.Add_Click({", "$review.Add_Click({",
                   "$logsButton.Add_Click({", "$refresh.Add_Click({RefreshUi})",
                   "$timer.Add_Tick({RefreshUi})", "function CanQueuePreopen($s){",
                   "function PreopenReserved($s){", "[void]$form.ShowDialog()"):
        if text.count(anchor) != 1:
            raise ValueError('NO11_DISPLAY_MIGRATION_CONTROL_SOURCE_CHANGED')
    guards = re.findall(r'^  \$(?:trade|nightly|review)[.]Enabled=.*$', text, re.M)
    changed = text.replace(OLD_TOOL, NEW_TOOL, 1).replace(OLD_DISPLAY, NEW_DISPLAY, 1)
    changed = changed.replace('function RefreshUi{', TOOLTIP + 'function RefreshUi{', 1)
    if re.findall(r'^  \$(?:trade|nightly|review)[.]Enabled=.*$', changed, re.M) != guards:
        raise ValueError('NO11_DISPLAY_MIGRATION_AUTHORIZATION_CHANGED')
    # Exact reverse proof also protects arbitrary local theme/selection changes.
    reverse = changed.replace(NEW_DISPLAY, OLD_DISPLAY, 1).replace(NEW_TOOL, OLD_TOOL, 1).replace(TOOLTIP, '', 1)
    if reverse != text:
        raise ValueError('NO11_DISPLAY_MIGRATION_OUTSIDE_SCOPE')
    return bom + changed.replace('\n', newline).encode('utf-8')
