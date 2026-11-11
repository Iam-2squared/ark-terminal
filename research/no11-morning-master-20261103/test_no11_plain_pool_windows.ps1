param([Parameter(Mandatory=$true)][string]$Candidate)
$ErrorActionPreference='Stop'
Set-StrictMode -Version Latest
function Assert-Test([bool]$Ok,[string]$Label){if(-not $Ok){throw ('PLAIN_POOL_TEST_'+$Label)}}
$tokens=$null;$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile($Candidate,[ref]$tokens,[ref]$errors)
Assert-Test ($errors.Count -eq 0) 'PARSE'
$source=[IO.File]::ReadAllText($Candidate)
$functions=@($ast.FindAll({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -ceq 'SafePhysicalBatch'},$true))
Assert-Test ($functions.Count -eq 1) 'CAPACITY_FUNCTION'
Invoke-Expression $functions[0].Extent.Text
$lines=@($source.Replace("`r`n","`n").Split([char]10)|ForEach-Object{$_.Trim()})
$ceilingLine=@($lines|Where-Object{$_ -ceq '$ceiling=SafePhysicalBatch $existing $BatchSize'})
$startLine=@($lines|Where-Object{$_ -ceq '$physical=$ceiling;$fullWaves=0'})
$waveLine=@($lines|Where-Object{$_ -ceq '$waveEnd=[Math]::Min($remaining.Count,$offset+$physical)'})
Assert-Test ($ceilingLine.Count -eq 1 -and $startLine.Count -eq 1 -and $waveLine.Count -eq 1) 'ACTUAL_RUN_STATEMENTS'
$start=[scriptblock]::Create($ceilingLine[0]+[char]10+$startLine[0])
$wave=[scriptblock]::Create($waveLine[0])
foreach($case in @(@(0,47),@(4,43),@(19,28))){
 $existing=[int]$case[0];$BatchSize=47;$ceiling=0;$physical=0;$fullWaves=-1
 . $start
 Assert-Test ($physical -eq [int]$case[1] -and $ceiling -eq $physical -and $fullWaves -eq 0) 'MAX_FROM_FIRST_WAVE'
 foreach($count in @(429,4328)){
  $remaining=@(1..$count);$offset=0;$waveEnd=0;$sizes=@()
  while($offset -lt $remaining.Count){
   . $wave
   $size=$waveEnd-$offset
   Assert-Test ($size -eq [Math]::Min($physical,$remaining.Count-$offset)) 'NO_GROUP_UNDERFILL'
   $sizes+=@($size);$offset=$waveEnd
  }
  Assert-Test (($sizes|Measure-Object -Sum).Sum -eq $count) 'EXACT_COVERAGE'
  if($existing -eq 0 -and $count -eq 429){
   Assert-Test ($sizes.Count -eq 10 -and $sizes[-1] -eq 6 -and @($sizes|Where-Object{$_ -eq 47}).Count -eq 9) '429_MAX_WAVES'
  }
  if($existing -eq 0 -and $count -eq 4328){
   Assert-Test ($sizes.Count -eq 93 -and $sizes[-1] -eq 4 -and @($sizes|Where-Object{$_ -eq 47}).Count -eq 92) '4328_MAX_WAVES'
  }
 }
}
$recovery=@(
 foreach($node in @($ast.FindAll({param($n) $n -is [Management.Automation.Language.IfStatementAst]},$true))){
  foreach($clause in $node.Clauses){
   if(($clause.Item1.Extent.Text -replace '\s','') -ceq '$physical-lt$ceiling' -and
      $clause.Item2.Extent.Text -match 'ARK_NO11_POOL_ALWAYS_MAX_AVAILABLE_V1'){$clause.Item2}
  }
 }
)
Assert-Test ($recovery.Count -eq 1) 'RECOVERY_BLOCK_UNIQUE'
$body=$recovery[0].Extent.Text
$recover=[scriptblock]::Create($body.Substring(1,$body.Length-2))
$physical=23;$ceiling=47;$fullWaves=0
. $recover
Assert-Test ($physical -eq 47 -and $fullWaves -eq 0) 'CLEAN_WAVE_IMMEDIATE_MAX'
Assert-Test (-not $source.Contains('$AutoMaxThroughput')) 'NO_REINTRODUCED_AUTOMAX'
Write-Host 'NO11_PLAIN_POOL_WINDOWS_MAX_BATCH=PASS'
Write-Host 'EXCEL_ACCESSED=False'
Write-Host 'ORDER_TRANSMISSION=False'
