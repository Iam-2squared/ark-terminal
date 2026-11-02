# Narrow JSON encoder for parsed RSS data only. Never reflect COM properties.
# Dot-source this library. No Excel attachment, network, file or broker writes.
param([switch]$PrimitiveJsonOfflineSelfTest)
function ConvertTo-No11JsonString([string]$Text) {
 $b=New-Object Text.StringBuilder
 [void]$b.Append([char]34)
 foreach($c in $Text.ToCharArray()) {
  $n=[int]$c
  if($n -eq 34){[void]$b.Append('\"')}
  elseif($n -eq 92){[void]$b.Append('\\')}
  elseif($n -eq 8){[void]$b.Append('\b')}
  elseif($n -eq 9){[void]$b.Append('\t')}
  elseif($n -eq 10){[void]$b.Append('\n')}
  elseif($n -eq 12){[void]$b.Append('\f')}
  elseif($n -eq 13){[void]$b.Append('\r')}
  elseif($n -lt 32 -or ($n -ge 55296 -and $n -le 57343)) {
   [void]$b.Append(('\u'+$n.ToString('x4')))
  }else{[void]$b.Append($c)}
 }
 [void]$b.Append([char]34)
 return $b.ToString()
}
function ConvertTo-No11PrimitiveJson($Value,[int]$Depth=0) {
 if($Depth -gt 20){throw 'NO11_JSON_MAX_DEPTH'}
 if($null -eq $Value){return 'null'}
 if($Value -is [string] -or $Value -is [char]){return (ConvertTo-No11JsonString ([string]$Value))}
 if($Value -is [bool]){if($Value){return 'true'}else{return 'false'}}
 $ci=[Globalization.CultureInfo]::InvariantCulture
 if($Value -is [double] -or $Value -is [single]) {
  $d=[double]$Value
  if([double]::IsNaN($d) -or [double]::IsInfinity($d)){throw 'NO11_JSON_NONFINITE'}
  return $d.ToString('R',$ci)
 }
 if($Value -is [decimal]){return $Value.ToString('G29',$ci)}
 if($Value -is [byte] -or $Value -is [sbyte] -or $Value -is [int16] -or
    $Value -is [uint16] -or $Value -is [int32] -or $Value -is [uint32] -or
    $Value -is [int64] -or $Value -is [uint64]){return $Value.ToString($ci)}
 if([Runtime.InteropServices.Marshal]::IsComObject($Value)){throw 'NO11_JSON_COM_FORBIDDEN'}
 if($Value -is [Collections.IDictionary]) {
  if($Value.Count -gt 20000){throw 'NO11_JSON_DICTIONARY_LIMIT'}
  $pairs=New-Object 'Collections.Generic.List[string]'
  foreach($key in @($Value.Keys)) {
   if($key -isnot [string]){throw 'NO11_JSON_KEY_TYPE'}
   $encoded=ConvertTo-No11PrimitiveJson $Value[$key] ($Depth+1)
   [void]$pairs.Add(((ConvertTo-No11JsonString $key)+':'+$encoded))
  }
  return ('{'+[string]::Join(',',$pairs.ToArray())+'}')
 }
 if($Value -is [array] -or $Value -is [Collections.IList]) {
  if($Value -is [array] -and $Value.Rank -ne 1){throw 'NO11_JSON_UNPARSED_MULTIDIMENSIONAL_ARRAY'}
  if($Value.Count -gt 20000){throw 'NO11_JSON_ARRAY_LIMIT'}
  $items=New-Object 'Collections.Generic.List[string]'
  foreach($item in $Value){[void]$items.Add((ConvertTo-No11PrimitiveJson $item ($Depth+1)))}
  return ('['+[string]::Join(',',$items.ToArray())+']')
 }
 if($Value -is [pscustomobject]) {
  $plain=[ordered]@{}
  foreach($p in $Value.PSObject.Properties) {
   if($p.MemberType -ne [Management.Automation.PSMemberTypes]::NoteProperty){throw 'NO11_JSON_REFLECTION_FORBIDDEN'}
   $plain[$p.Name]=$p.Value
  }
  return (ConvertTo-No11PrimitiveJson $plain ($Depth+1))
 }
 throw 'NO11_JSON_NON_PRIMITIVE_OBJECT'
}
if($PrimitiveJsonOfflineSelfTest) {
 $rows=@()
 for($i=0;$i -lt 24;$i++){
  $rows+=,[pscustomobject][ordered]@{symbol='7203.T';previousClose=123.4;lotShares=100;
   text=('東証'+[char]34+[char]10+'\\');none=$null;readOnly=$true}
 }
 $record=[ordered]@{rows=@($rows);empty=@();one=@(1);orderTransmission=$false}
 $json=ConvertTo-No11PrimitiveJson $record
 $parsed=$json|ConvertFrom-Json
 if(@($parsed.rows).Count -ne 24 -or @($parsed.empty).Count -ne 0 -or
    @($parsed.one).Count -ne 1 -or $parsed.rows[23].text -cne $rows[23].text -or
    $parsed.orderTransmission -ne $false){throw 'NO11_JSON_ROUNDTRIP_FAILED'}
 foreach($bad in @([datetime]::Now,[double]::NaN,[double]::PositiveInfinity)){
  $blocked=$false;try{ConvertTo-No11PrimitiveJson $bad|Out-Null}catch{$blocked=$true}
  if(-not $blocked){throw 'NO11_JSON_BAD_TYPE_ACCEPTED'}
 }
 Write-Host 'NO11_PRIMITIVE_JSON_SELFTEST=PASS_REAL_ROW_SHAPE_24'
 Write-Host 'ORDER_TRANSMISSION=False'
}
