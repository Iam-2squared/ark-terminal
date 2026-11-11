"""Scoped locale and original-template compatibility, not trade authorization.

The original creator writes DISABLED / 0 / UNCONFIGURED_RSS_SESSION / empty.
Never infer these strings from their lengths. Allow only exact matching values
under the existing same-day approval, zero trigger and physical-session gates.
No formatting write is needed for an already standard Japanese General cell.
"""
from __future__ import annotations

MARK = 'ARK_NO11_EXCEL_LOCALE_TEMPLATE_V1'
HELPER = r'''# ARK_NO11_EXCEL_GENERAL_EN_JA_V1
function Test-No11LocaleGeneral($Cell){
 $normal=$Cell.NumberFormat
 $local=$Cell.NumberFormatLocal
 if($normal -isnot [string] -or $local -isnot [string]){return $false}
 $ja=-join [char[]]@(0x0047,0x002F,0x6A19,0x6E96)
 return (($normal -ceq 'General' -and ($local -ceq 'General' -or $local -ceq $ja)) -or
         ($normal -ceq $ja -and $local -ceq $ja))
}
'''
OLD_STATE = r''' $previousGuard=[string]$guard.Value2
 $previousSession=[string]$session.Value2
 Need ([string]::IsNullOrWhiteSpace($previousGuard) -or
       $previousGuard -ceq 'ARK_NO11_SEND_ONCE') 'UNKNOWN_PREVIOUS_GUARD'
 Need ([string]::IsNullOrWhiteSpace($previousSession) -or
       $previousSession -ceq $sessionKey) 'UNKNOWN_PREVIOUS_SESSION' '''.rstrip()
NEW_STATE = r''' # ARK_NO11_EXCEL_LOCALE_TEMPLATE_V1
 $previousGuard=[string]$guard.Value2
 $previousSession=[string]$session.Value2
 # Exact values from New-No11BrokerReadOnlyWorkbook.ps1. Lengths are NOT proof.
 $inertTemplate=($previousGuard -ceq 'DISABLED' -and
                 $previousSession -ceq 'UNCONFIGURED_RSS_SESSION' -and
                 $trigger.Value2 -is [ValueType] -and
                 $trigger.Value2 -isnot [bool] -and [double]$trigger.Value2 -eq 0)
 if(-not $inertTemplate){
  Need ([string]::IsNullOrWhiteSpace($previousGuard) -or
        $previousGuard -ceq 'ARK_NO11_SEND_ONCE') 'UNKNOWN_PREVIOUS_GUARD'
  Need ([string]::IsNullOrWhiteSpace($previousSession) -or
        $previousSession -ceq $sessionKey) 'UNKNOWN_PREVIOUS_SESSION'
 }
 Write-Host ('AUTOMATIC_TRANSPORT_CONTROL_ORIGIN='+$(if($inertTemplate){'EXACT_INERT_TEMPLATE'}else{'EMPTY_OR_CURRENT_SESSION'}))'''
OLD_FORMAT = r''' $formatBefore=[string]$formula.NumberFormat
 if($formatBefore -cne 'General'){
  # Only formatting is attempted here; failure happens before BD1/BD2/BD3.
  $formula.NumberFormat='General'
 }
 Need ([string]$formula.NumberFormat -ceq 'General') 'FORMULA_GENERAL_UNVERIFIED'
 Write-Host ('AUTOMATIC_TRANSPORT_FORMULA_GENERAL=' + $(if($formatBefore -ceq 'General'){'ALREADY_VALID'}else{'CHANGED_ONCE'}))'''
NEW_FORMAT = r''' $formatWasGeneral=Test-No11LocaleGeneral $formula
 if(-not $formatWasGeneral){
  # Existing one-shot conversion remains for nonstandard formats only.
  $formula.NumberFormat='General'
 }
 Need (Test-No11LocaleGeneral $formula) 'FORMULA_GENERAL_UNVERIFIED'
 Write-Host ('AUTOMATIC_TRANSPORT_FORMULA_GENERAL='+$(if($formatWasGeneral){'ALREADY_VALID_NO_FORMAT_WRITE'}else{'CHANGED_ONCE'}))'''


def need(ok, why):
    if not ok:
        raise ValueError('NO11_LOCALE_TEMPLATE_' + why)


def unpack(raw):
    text = raw.decode('utf-8-sig')
    nl = '\r\n' if '\r\n' in text else '\n'
    text = text.replace('\r\n', '\n')
    need('\r' not in text, 'LINE_ENDINGS')
    return text, nl, raw.startswith(b'\xef\xbb\xbf')


def pack(text, nl, bom):
    return (b'\xef\xbb\xbf' if bom else b'') + text.replace('\n', nl).encode('utf-8')


def once(text, before, after):
    need(text.count(before) == 1, 'SOURCE_ANCHOR_CHANGED')
    return text.replace(before, after, 1)


def transform_probe(raw):
    text, nl, bom = unpack(raw)
    if MARK in text:
        need(NEW_STATE in text and NEW_FORMAT in text and HELPER in text, 'INSTALLED_PROBE_CHANGED')
        return raw
    need('ARK_NO11_TRANSPORT_FORMAT_BEFORE_SESSION_V1' in text, 'FORMAT_FIRST_REQUIRED')
    need(text.count('$trigger.Value2=1') == 0 and text.count('$trigger.Value2=0') == 1,
         'PROBE_MUST_NOT_SEND')
    for token in ('SAME_DAY_OPERATOR_APPROVAL_REQUIRED', 'ACTUAL_SESSION_DAY_REQUIRED',
                  'TRIGGER_ALREADY_NONZERO', 'ORDER_CONTROL_CELLS',
                  'SESSION_INITIALIZATION_READBACK', 'RSS_ADDINS_NOT_UNIQUE'):
        need(token in text, 'PROBE_GUARD_MISSING')
    text = once(text, OLD_STATE, NEW_STATE)
    text = once(text, OLD_FORMAT, NEW_FORMAT)
    text = once(text, '$excel=$null;$orderBook=$null;$sheet=$null',
                HELPER + '\n$excel=$null;$orderBook=$null;$sheet=$null')
    return pack(text, nl, bom)


def transform_sender(raw):
    text, nl, bom = unpack(raw)
    old = "[string]$formula.NumberFormat -ceq 'General'"
    new = '(Test-No11LocaleGeneral $formula)'
    if HELPER in text:
        need(old not in text and text.count(new) == 1, 'INSTALLED_SENDER_CHANGED')
        return raw
    need(text.count('$state.trigger.Value2=1') == 1 and
         text.count('$state.trigger.Value2=0') == 1, 'ONE_SHOT_TRANSPORT_REQUIRED')
    # Only the standard-format predicate changes. Core/permit/BUY/SELL/CANCEL
    # sequencing, trigger writes, marker consumption and reconciliation stay.
    text = once(text, old, new)
    text = once(text, 'function New-No11ExcelSink($Packet){',
                HELPER + '\nfunction New-No11ExcelSink($Packet){')
    return pack(text, nl, bom)


def transform_js(raw):
    text, nl, bom = unpack(raw)
    old = r'/\.xlsx$/i.test(config.workbookPath)'
    new = r'/\.(?:xlsx|xlsb|xlsm)$/i.test(config.workbookPath)'
    if old not in text:
        need(text.count(new) == 1, 'TRANSPORT_CONTAINER_CHECK_CHANGED')
        return raw
    return pack(once(text, old, new), nl, bom)
