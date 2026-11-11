#!/usr/bin/env python3
"""Exact-source V3 hardening; produce a candidate, never run a live transport.

Only READS may be retried. No cell write, workbook open, session initialization,
order or cancel dispatch is retried. All original V3 guards remain in place.
"""
import argparse
import hashlib
from pathlib import Path

BASE_BLOB = '7afc254f54a19b400d2e4e9cce15c23434953dba'
MARKER = '# ARK_NO11_TRANSPORT_RESILIENCE_V1'
HELPERS = r'''
# ARK_NO11_TRANSPORT_RESILIENCE_V1
function Wait-No11TransportReadiness {
 param([scriptblock]$Read,[scriptblock]$Delay={param($ms) Start-Sleep -Milliseconds $ms},[int]$Attempts=6)
 Need ($Attempts -ge 1 -and $Attempts -le 6) 'READINESS_ATTEMPTS'
 for($attempt=1;$attempt -le $Attempts;$attempt++){
  try{
   $r=& $Read
   if($r.Visible -eq $true -and $r.Ready -eq $true -and [int]$r.CalculationState -eq 0){return $r.Excel}
  }catch{
   $e=$_.Exception
   while($null -ne $e.InnerException){$e=$e.InnerException}
   # RPC_E_CALL_REJECTED / RPC_E_SERVERCALL_RETRYLATER: READ operation only.
   if($e -isnot [Runtime.InteropServices.COMException] -or
      $e.HResult -notin @(-2147418111,-2147417846)){throw}
   Write-Host ('AUTOMATIC_TRANSPORT_READ_HRESULT='+$e.HResult)
  }
  Write-Host ('AUTOMATIC_TRANSPORT_READINESS_ATTEMPT='+$attempt)
  if($attempt -lt $Attempts){& $Delay 500}
 }
 throw 'NO11_AUTO_TRANSPORT_EXCEL_NOT_READY'
}
function Assert-No11TransportSessionStable($Excel,[int]$ExpectedPid,[string]$ExpectedStartedAt){
 [uint32]$currentPid=0
 $currentHwnd=[IntPtr]([long]$Excel.Hwnd)
 $thread=[No11AutoTransportNative]::GetWindowThreadProcessId($currentHwnd,[ref]$currentPid)
 Need ($thread -gt 0 -and $currentPid -eq $ExpectedPid) 'EXCEL_SESSION_CHANGED_BEFORE_PUBLICATION'
 $current=Get-Process -Id $currentPid -ErrorAction Stop
 Need ($current.ProcessName -ieq 'EXCEL' -and
       $current.StartTime.ToUniversalTime().ToString('o') -ceq $ExpectedStartedAt) 'EXCEL_SESSION_CHANGED_BEFORE_PUBLICATION'
}
'''


def blob(raw):
    return hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()


def once(text, old, new):
    if text.count(old) != 1:
        raise ValueError('NO11_TRANSPORT_PATCH_SOURCE_CONTEXT_CHANGED')
    return text.replace(old, new, 1)


def transform(raw):
    bom = raw.startswith(b'\xef\xbb\xbf')
    decoded = raw.decode('utf-8-sig')
    newline = '\r\n' if '\r\n' in decoded else '\n'
    text = decoded.replace('\r\n', '\n')
    if '\r' in text or blob(text.encode('utf-8')) != BASE_BLOB:
        raise ValueError('NO11_TRANSPORT_PATCH_UNKNOWN_LOCAL_SOURCE')
    before = text
    text = once(text, '$excel=$null;$orderBook=$null;$sheet=$null',
                HELPERS + "\n$script:TransportStage='PRECHECK'\n$excel=$null;$orderBook=$null;$sheet=$null")
    old = " $excel=[Runtime.InteropServices.Marshal]::GetActiveObject('Excel.Application')\n Need ($excel.Visible -eq $true -and $excel.Ready -eq $true -and [int]$excel.CalculationState -eq 0) 'EXCEL_NOT_READY'"
    new = """ $script:TransportStage='EXCEL_READINESS'
 $excel=Wait-No11TransportReadiness -Read {
  $app=[Runtime.InteropServices.Marshal]::GetActiveObject('Excel.Application')
  [pscustomobject]@{Excel=$app;Visible=$app.Visible;Ready=$app.Ready;CalculationState=$app.CalculationState}
 }
 $script:TransportStage='EXCEL_IDENTITY'"""
    text = once(text, old, new)
    for anchor, stage in (
        (' $opened=@{}', 'WORKBOOK_INVENTORY'),
        (' $orderKey=$order.ToLowerInvariant()', 'ORDER_WORKBOOK'),
        (" $guard=$sheet.Range('BD1');", 'CONTROL_VALIDATION'),
        (' $startedAtUtc=$process.StartTime.', 'SESSION_IDENTITY'),
        (" $guard.Value2='ARK_NO11_SEND_ONCE'", 'SESSION_WRITE_ONCE'),
        (" Need ([string]$guard.Value2 -ceq 'ARK_NO11_SEND_ONCE'", 'SESSION_READBACK'),
        (' $saved=@($excel.Workbooks', 'WORKBOOK_RECHECK'),
        (' $addinPaths=@()', 'ADDIN_INVENTORY'),
        (" $dispatch=Join-Path $root 'transport-dispatch'", 'DISPATCH_DIRECTORY'),
        (" $file=WriteImmutableJson $root $transport 'automatic-live-transport'", 'RECEIPT_PUBLICATION'),
    ):
        text = once(text, anchor, " $script:TransportStage='" + stage + "'\n" + anchor)
    pub = " $script:TransportStage='RECEIPT_PUBLICATION'"
    text = once(text, pub, " $script:TransportStage='FINAL_EXCEL_SESSION_IDENTITY'\n Assert-No11TransportSessionStable $excel ([int]$excelPid) $startedAtUtc\n" + pub)
    catch = " $reason=[string]$_.Exception.Message"
    details = """ Write-Host ('AUTOMATIC_TRANSPORT_DIAGNOSTIC_STAGE='+$script:TransportStage)
 $failure=$_.Exception
 while($null -ne $failure.InnerException){$failure=$failure.InnerException}
 $kind=$failure.GetType().Name
 if($kind -cnotmatch '^[A-Za-z0-9_]{1,80}$'){$kind='REDACTED'}
 Write-Host ('AUTOMATIC_TRANSPORT_EXCEPTION_KIND='+$kind)
 Write-Host ('AUTOMATIC_TRANSPORT_HRESULT='+[int]$failure.HResult)
 Write-Host ('AUTOMATIC_TRANSPORT_SOURCE_LINE='+[int]$_.InvocationInfo.ScriptLineNumber)
"""
    text = once(text, catch, details + catch)
    # Structural assertions, not a replacement for Windows execution tests.
    for token in ("$trigger.Value2=0", "$guard.Value2='ARK_NO11_SEND_ONCE'",
                  '$session.Value2=$sessionKey', '$formula.ClearContents()',
                  '$orderBook=$excel.Workbooks.Open($order)'):
        if before.count(token) != 1 or text.count(token) != 1:
            raise ValueError('NO11_TRANSPORT_PATCH_WRITE_MULTIPLICITY')
    if '$trigger.Value2=1' in text:
        raise ValueError('NO11_TRANSPORT_PATCH_ORDER_WRITE_FORBIDDEN')
    return (b'\xef\xbb\xbf' if bom else b'') + text.replace('\n', newline).encode('utf-8')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--candidate', type=Path, required=True)
    a = p.parse_args()
    if a.candidate.exists() or a.source.resolve() == a.candidate.resolve():
        raise SystemExit('NO11_TRANSPORT_PATCH_CANDIDATE_MUST_BE_NEW')
    result = transform(a.source.read_bytes())
    with a.candidate.open('xb') as f:
        f.write(result)
    print('NO11_TRANSPORT_RESILIENCE_CANDIDATE=CREATED_ONLY')
    print('READ_RETRIES_ONLY=True\nSESSION_WRITES_RETRIED=False\nTRADE_LAUNCHED=False\nORDER_TRANSMISSION=False')

if __name__ == '__main__':
    main()
