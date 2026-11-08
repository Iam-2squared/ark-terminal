param([Parameter(Mandatory=$true)][string]$Candidate)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
$t=$null;$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile($Candidate,[ref]$t,[ref]$errors)
if($errors.Count){$errors|ForEach-Object{Write-Host $_.Message};throw 'CANDIDATE_PARSE_FAILED'}
$names=@('Need','Wait-No11TransportReadiness','Assert-No11TransportSessionStable')
$functions=@($ast.FindAll({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -in $names},$true))
if($functions.Count -ne 3){throw 'HELPER_FUNCTIONS_NOT_FOUND'}
foreach($f in $functions){Invoke-Expression $f.Extent.Text}
function Check([bool]$value,[string]$reason){if(-not $value){throw ('TEST_FAILED_'+$reason)}}
$script:Calls=0;$script:Delays=0
$delay={param($ms) Check ($ms -eq 500) 'DELAY';$script:Delays++}
$read={
 $script:Calls++
 if($script:Calls -lt 3){throw [Runtime.InteropServices.COMException]::new('mock transient',-2147418111)}
 [pscustomobject]@{Visible=$true;Ready=$true;CalculationState=0;Excel='MOCK_APP'}
}
$value=Wait-No11TransportReadiness -Read $read -Delay $delay
Check ($value -ceq 'MOCK_APP' -and $script:Calls -eq 3 -and $script:Delays -eq 2) 'TRANSIENT_RECOVERS'

$script:Calls=0;$script:Delays=0
$value=Wait-No11TransportReadiness -Delay $delay -Read {
 $script:Calls++
 if($script:Calls -eq 1){throw [Runtime.InteropServices.COMException]::new('busy',-2147417846)}
 [pscustomobject]@{Visible=$true;Ready=$true;CalculationState=0;Excel='MOCK_APP'}
}
Check ($value -ceq 'MOCK_APP' -and $script:Calls -eq 2 -and $script:Delays -eq 1) 'RETRY_LATER'

$script:Calls=0;$script:Delays=0
$blocked=$false
try{[void](Wait-No11TransportReadiness -Read {$script:Calls++;throw [InvalidOperationException]::new('permanent')} -Delay $delay)}catch{$blocked=$true}
Check ($blocked -and $script:Calls -eq 1 -and $script:Delays -eq 0) 'UNKNOWN_EXCEPTION_NOT_RETRIED'

$script:Calls=0;$script:Delays=0
$blocked=$false
try{[void](Wait-No11TransportReadiness -Read {$script:Calls++;throw [Runtime.InteropServices.COMException]::new('access denied',-2147024891)} -Delay $delay)}catch{$blocked=$true}
Check ($blocked -and $script:Calls -eq 1 -and $script:Delays -eq 0) 'PERMANENT_COM_NOT_RETRIED'

$script:Calls=0;$script:Delays=0
$blocked=$false
try{[void](Wait-No11TransportReadiness -Read {$script:Calls++;[pscustomobject]@{Visible=$true;Ready=$false;CalculationState=1;Excel='MOCK'}} -Delay $delay)}catch{$blocked=($_.Exception.Message -ceq 'NO11_AUTO_TRANSPORT_EXCEL_NOT_READY')}
Check ($blocked -and $script:Calls -eq 6 -and $script:Delays -eq 5) 'BOUNDED_WAIT'

Add-Type -TypeDefinition @'
using System;
public static class No11AutoTransportNative {
 public static uint Pid=4321;
 public static uint GetWindowThreadProcessId(IntPtr hwnd,out uint pid){pid=Pid;return 9876;}
}
'@
$script:Start=[datetime]::SpecifyKind([datetime]'2026-11-06T08:00:00',[DateTimeKind]::Utc)
function Get-Process {param($Id,$ErrorAction) return [pscustomobject]@{ProcessName='EXCEL';StartTime=$script:Start}}
$stamp=$script:Start.ToString('o')
Assert-No11TransportSessionStable ([pscustomobject]@{Hwnd=12345}) 4321 $stamp
[No11AutoTransportNative]::Pid=4322
$blocked=$false
try{Assert-No11TransportSessionStable ([pscustomobject]@{Hwnd=12345}) 4321 $stamp}catch{$blocked=$true}
Check $blocked 'PID_CHANGED_BLOCKED'
[No11AutoTransportNative]::Pid=4321
$script:Start=$script:Start.AddMinutes(1)
$blocked=$false
try{Assert-No11TransportSessionStable ([pscustomobject]@{Hwnd=12345}) 4321 $stamp}catch{$blocked=$true}
Check $blocked 'PID_REUSED_START_TIME_CHANGED_BLOCKED'
Write-Host 'NO11_TRANSPORT_READINESS_WINDOWS_TESTS=7_PASS'
Write-Host 'REAL_EXCEL_ACCESSED=False'
Write-Host 'ORDER_TRANSMISSION=False'
