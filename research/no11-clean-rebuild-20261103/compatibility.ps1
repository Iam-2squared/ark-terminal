# Pure helpers only. No COM attach, formula evaluation, order or permission I/O.
function Assert-No11Clean([bool]$Ok,[string]$Reason) {
 if(-not $Ok){throw ('NO11_CLEAN_'+$Reason)}
}
function Convert-No11CleanFunctionName([string]$Value) {
 switch -CaseSensitive ($Value) {
  '国内株式 現物注文' {return 'RssStockOrder'}
  '国内株式　現物注文' {return 'RssStockOrder'}
  '国内株式 取消注文' {return 'RssCancelOrder'}
  '国内株式　取消注文' {return 'RssCancelOrder'}
  '国内株式 訂正注文' {return 'RssModifyOrder'}
  '国内株式　訂正注文' {return 'RssModifyOrder'}
 }
 # Preserve the established English observation path, not a send allowlist.
 Assert-No11Clean ($Value -cmatch '^Rss[A-Za-z0-9_]+$') 'UNKNOWN_RSS_FUNCTION_NAME'
 return $Value
}
function Convert-No11CleanFormula([string]$Value) {
 # Only Excel's leading implicit-intersection marker. Do not strip cell refs,
 # spaces, quotes, argument values or other formula content.
 if($Value.StartsWith('=@')){return '='+$Value.Substring(2)}
 return $Value
}
function Get-No11CleanVendorStatus([string]$Text,$Packet) {
 $value=$Text.Trim()
 if($value.Contains(' => ')){
  Assert-No11Clean (([regex]::Matches($value,' => ')).Count -eq 1) 'VENDOR_ECHO_AMBIGUOUS'
  $split=$value.IndexOf(' => ')
  $echo=Convert-No11CleanFormula $value.Substring(0,$split)
  $expected=Get-No11BoundFormula $Packet
  Assert-No11Clean ($echo -ceq $expected) 'VENDOR_ECHO_CHANGED'
  $value=$value.Substring($split+4)
 }
 return $value
}
function Read-No11CleanReferenceRows($Sheet,[int]$Count) {
 Assert-No11Clean ($Count -ge 1 -and $Count -le 50) 'REFERENCE_ROW_COUNT'
 $matrix=[array]::CreateInstance([object],$Count,12)
 for($r=0;$r -lt $Count;$r++){
  $row=$Sheet.Range(('A'+($r+1)+':L'+($r+1))).Value2
  Assert-No11Clean ($row -is [array] -and $row.Rank -eq 2 -and
   $row.GetLength(0) -eq 1 -and $row.GetLength(1) -eq 12) 'REFERENCE_ROW_SHAPE'
  for($c=0;$c -lt 12;$c++){
   $matrix.SetValue($row.GetValue($row.GetLowerBound(0),$row.GetLowerBound(1)+$c),$r,$c)
  }
 }
 # One row per COM read is NOT an atomic feed snapshot. Existing capture
 # start/end clocks and downstream reference identity checks remain in use.
 return ,$matrix
}
function Convert-No11CleanJsonString([string]$Value) {
 $b=[Text.StringBuilder]::new();[void]$b.Append('"')
 foreach($ch in $Value.ToCharArray()){
  $n=[int]$ch
  if($n -eq 34){[void]$b.Append('\"')}
  elseif($n -eq 92){[void]$b.Append('\\')}
  elseif($n -lt 32 -or ($n -ge 55296 -and $n -le 57343)){
   [void]$b.Append(('\u{0:x4}' -f $n))
  }else{[void]$b.Append($ch)}
 }
 [void]$b.Append('"');return $b.ToString()
}
function Convert-No11CleanJsonNode($Value,[int]$Depth,$Budget) {
 $Budget.Count++
 Assert-No11Clean ($Depth -le 32 -and $Budget.Count -le 100000) 'JSON_LIMIT'
 if($null -eq $Value){return 'null'}
 if($Value -is [string]){return Convert-No11CleanJsonString $Value}
 if($Value -is [bool]){if($Value){return 'true'}else{return 'false'}}
 $numeric=@([byte],[sbyte],[int16],[uint16],[int32],[uint32],[int64],[uint64],[single],[double],[decimal])
 if($Value.GetType() -in $numeric){
  $n=[double]$Value
  Assert-No11Clean (-not [double]::IsNaN($n) -and -not [double]::IsInfinity($n)) 'JSON_NONFINITE'
  if($Value -is [double] -or $Value -is [single]){return $Value.ToString('R',[Globalization.CultureInfo]::InvariantCulture)}
  return $Value.ToString([Globalization.CultureInfo]::InvariantCulture)
 }
 $b=[Text.StringBuilder]::new()
 if($Value -is [Collections.IDictionary]){
  [void]$b.Append('{');$first=$true
  foreach($key in $Value.Keys){
   Assert-No11Clean ($key -is [string]) 'JSON_KEY_TYPE'
   if(-not $first){[void]$b.Append(',')};$first=$false
   [void]$b.Append((Convert-No11CleanJsonString $key));[void]$b.Append(':')
   [void]$b.Append((Convert-No11CleanJsonNode $Value[$key] ($Depth+1) $Budget))
  }
  [void]$b.Append('}');return $b.ToString()
 }
 if($Value -is [array]){
  Assert-No11Clean ($Value.Rank -eq 1) 'JSON_ARRAY_RANK'
  [void]$b.Append('[');$first=$true
  foreach($item in $Value){
   if(-not $first){[void]$b.Append(',')};$first=$false
   [void]$b.Append((Convert-No11CleanJsonNode $item ($Depth+1) $Budget))
  }
  [void]$b.Append(']');return $b.ToString()
 }
 if($Value -is [pscustomobject]){
  [void]$b.Append('{');$first=$true
  foreach($prop in $Value.PSObject.Properties){
   Assert-No11Clean ($prop.MemberType -eq [Management.Automation.PSMemberTypes]::NoteProperty) 'JSON_PROPERTY_TYPE'
   if(-not $first){[void]$b.Append(',')};$first=$false
   [void]$b.Append((Convert-No11CleanJsonString $prop.Name));[void]$b.Append(':')
   [void]$b.Append((Convert-No11CleanJsonNode $prop.Value ($Depth+1) $Budget))
  }
  [void]$b.Append('}');return $b.ToString()
 }
 throw 'NO11_CLEAN_JSON_UNSUPPORTED_TYPE'
}
function ConvertTo-No11CleanJson($Value) {
 # Never enumerate arbitrary CLR/COM properties as ConvertTo-Json can do.
 return Convert-No11CleanJsonNode $Value 0 @{Count=0}
}
