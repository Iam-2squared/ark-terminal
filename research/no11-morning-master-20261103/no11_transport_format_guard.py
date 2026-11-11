#!/usr/bin/env python3
"""Fix the confirmed Excel 1004 source line 193 *without* retrying orders or writes.

Original pinned V3 resilient source:
  stage SESSION_WRITE_ONCE -> BD1 guard -> BD2 zero -> BD3 session key ->
  BD4 NumberFormat='General' (line 193 in installed source layout).

On failure BD1-3 may already contain partial session initialization.
Fix by (1) validating current partial guard/session control cells, (2)
checking BD4 format and, only if necessary, setting it once BEFORE writing
any new BD1/BD2/BD3, (3) keeping the same one-shot BD1/2/3 writes and all
readbacks, broker and authorization guards exactly unchanged.

Unknown worksheet state or another-session marker always BLOCKS. No reattempt
to transmit a live order, no BD2=1, no write retry, no source replay.
"""
from __future__ import annotations

MARK='ARK_NO11_TRANSPORT_FORMAT_BEFORE_SESSION_V1'

BEFORE=""" $script:TransportStage='SESSION_WRITE_ONCE'
 $guard.Value2='ARK_NO11_SEND_ONCE'
 $trigger.Value2=0
 $session.Value2=$sessionKey
 $formula.NumberFormat='General'
 $script:TransportStage='SESSION_READBACK'"""

AFTER=""" # ARK_NO11_TRANSPORT_FORMAT_BEFORE_SESSION_V1
 # This phase has NO order trigger and NO prior session-control cell writes.
 # In a partial prior failure, only the SAME physically identified Excel
 # session may be completed, and BD2 must still be zero as checked above.
 $script:TransportStage='PARTIAL_SESSION_CONTROL_READ'
 $previousGuard=[string]$guard.Value2
 $previousSession=[string]$session.Value2
 Need ([string]::IsNullOrWhiteSpace($previousGuard) -or
       $previousGuard -ceq 'ARK_NO11_SEND_ONCE') 'UNKNOWN_PREVIOUS_GUARD'
 Need ([string]::IsNullOrWhiteSpace($previousSession) -or
       $previousSession -ceq $sessionKey) 'UNKNOWN_PREVIOUS_SESSION'
 $script:TransportStage='FORMULA_NUMBER_FORMAT_ONE_TIME'
 $formatBefore=[string]$formula.NumberFormat
 if($formatBefore -cne 'General'){
  # Only formatting is attempted here; failure happens before BD1/BD2/BD3.
  $formula.NumberFormat='General'
 }
 Need ([string]$formula.NumberFormat -ceq 'General') 'FORMULA_GENERAL_UNVERIFIED'
 Write-Host ('AUTOMATIC_TRANSPORT_FORMULA_GENERAL=' + $(if($formatBefore -ceq 'General'){'ALREADY_VALID'}else{'CHANGED_ONCE'}))
 $script:TransportStage='SESSION_WRITE_ONCE'
 $guard.Value2='ARK_NO11_SEND_ONCE'
 $trigger.Value2=0
 $session.Value2=$sessionKey
 $script:TransportStage='SESSION_READBACK'"""

def need(ok,reason):
    if not ok:raise ValueError('NO11_TRANSPORT_FORMAT_'+reason)

def transform(raw):
    bom=raw.startswith(b'\xef\xbb\xbf')
    decoded=raw.decode('utf-8-sig')
    newline='\r\n' if '\r\n' in decoded else '\n'
    src=decoded.replace('\r\n','\n')
    need('\r' not in src,'SOURCE_LINE_ENDINGS')
    if MARK in src:
        need(src.count(MARK)==1 and BEFORE not in src,'ALREADY_APPLIED_SOURCE_CHANGED')
        return raw
    need(src.count(BEFORE)==1 and
         '# ARK_NO11_TRANSPORT_RESILIENCE_V1' in src and
         src.count('$trigger.Value2=1')==0 and
         src.count("ORDER_SENT=False")>=2 and
         src.count("ORDER_TRIGGER_WRITTEN_TO_ONE=False")>=2,
         'EXPECTED_PINNED_V3_RESILIENT_SOURCE')
    # Explicit consent and exact source/Excel identity are untouched.
    for anchor in (
        "Need $SameDayOperatorApproved.IsPresent 'SAME_DAY_OPERATOR_APPROVAL_REQUIRED'",
        "Need ($SessionDate -ceq $now.ToString('yyyy-MM-dd')) 'ACTUAL_SESSION_DAY_REQUIRED'",
        "'TRIGGER_ALREADY_NONZERO'",
        "'ORDER_WORKBOOK_IDENTITY'",
        "'SESSION_INITIALIZATION_READBACK'",
        "'WORKBOOK_SET_IDENTITY'",
        "'RSS_ADDINS_NOT_UNIQUE'",
        "'SESSION_READBACK'",
        " $formula.ClearContents()",
        " $guard.Value2='ARK_NO11_SEND_ONCE'",
        " $trigger.Value2=0",
        " $session.Value2=$sessionKey",
    ):
        need(anchor in src,'FROZEN_GUARD_OR_SOURCE_NOT_FOUND')
    changed=src.replace(BEFORE,AFTER,1)
    need(changed.count(MARK)==1 and
         changed.count("$formula.NumberFormat='General'")==1 and
         changed.count("$guard.Value2='ARK_NO11_SEND_ONCE'")==1 and
         changed.count('$trigger.Value2=0')==1 and
         changed.count('$session.Value2=$sessionKey')==1 and
         changed.count('$trigger.Value2=1')==0,
         'SINGLE_WRITE_CONTRACT')
    # Verify the *entire* original source besides exactly this region,
    # including original notification, exception and broker code.
    start=src.index(BEFORE)
    need(src[:start]==changed[:start] and
         src[start+len(BEFORE):]==changed[start+len(AFTER):],
         'UNEXPECTED_CODE_CHANGE')
    return (b'\xef\xbb\xbf' if bom else b'')+changed.replace('\n',newline).encode('utf-8')
