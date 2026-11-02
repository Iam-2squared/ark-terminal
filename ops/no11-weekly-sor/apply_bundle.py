#!/usr/bin/env python3
"""Apply the audited adapter changes to a clean candidate worktree only.

CI applies the same migration before regression tests. Never reset a user's
working tree, alter frozen models, open Excel, or enable broker orders.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

BASE = '7ee286122b2eaf7e4f9a96797216786f60e567dc'
REL = 'research/no12-prebuy-causal-runtime-20261011/'


def once(text, old, new):
    if text.count(old) != 1:
        raise ValueError('NO11_BUNDLE_PATCH_CONTEXT_NOT_UNIQUE: ' + old[:75])
    return text.replace(old, new, 1)


def canonical(raw):
    return raw.decode('utf-8').replace('\r\n', '\n')


def original(root, relative):
    p = subprocess.run(['git', '-C', str(root), 'show', BASE + ':' + relative],
                       capture_output=True, check=True)
    return canonical(p.stdout)


def transformed(relative, text):
    if relative.endswith('windows/Read-No11BrokerSnapshot.ps1'):
        anchor = "function Assert-No11Broker([bool]$Ok,[string]$Code) {"
        helpers = '''. (Join-Path $PSScriptRoot 'Convert-No11PrimitiveJson.ps1')
# Actual RssOrderIDList displays Japanese function labels. Preserve them in
# functionNameRaw, bind only an exact recognized canonical function.
function Convert-No11RssFunctionName([string]$Value) {
 $raw=$Value.Trim()
 if($raw -cmatch '^Rss[A-Za-z0-9_]+$'){return $raw}
 $compact=$raw -replace '[ \\u3000]',''
 switch -CaseSensitive ($compact) {
  '国内株式現物注文' {return 'RssStockOrder'}
  '国内株式取消注文' {return 'RssCancelOrder'}
  '国内株式訂正注文' {return 'RssModifyOrder'}
  '国内株式信用新規' {return 'RssMarginOpenOrder'}
  '国内株式信用返済' {return 'RssMarginCloseOrder'}
  default {throw 'NO11_BROKER_UNKNOWN_RSS_FUNCTION_LABEL'}
 }
}
'''
        text = once(text, anchor, helpers + '\n' + anchor)
        text = once(text,
            "$fn=Get-No11BrokerText (Get-No11BrokerCell $Data $r 1)",
            "$rawFn=Get-No11BrokerText (Get-No11BrokerCell $Data $r 1)\n     $fn=Convert-No11RssFunctionName $rawFn")
        text = once(text, 'functionName=$fn;', 'functionName=$fn;functionNameRaw=$rawFn;')
        text = text.replace('ConvertTo-Json -InputObject $_ -Compress -Depth 8', 'ConvertTo-No11PrimitiveJson $_')
        text = once(text,
            "ConvertTo-Json -InputObject ([ordered]@{orders=$orders;executions=$executions;positions=$positions;buyingPower=$Snapshot.buyingPower}) -Compress -Depth 10",
            "ConvertTo-No11PrimitiveJson ([ordered]@{orders=$orders;executions=$executions;positions=$positions;buyingPower=$Snapshot.buyingPower})")
        text = once(text,
            '(ConvertTo-Json -InputObject $tablesA -Depth 20 -Compress) -ceq (ConvertTo-Json -InputObject $tablesB -Depth 20 -Compress)',
            '(ConvertTo-No11PrimitiveJson $tablesA) -ceq (ConvertTo-No11PrimitiveJson $tablesB)')
    elif relative.endswith('windows/Observe-No11AccountReadOnly.ps1'):
        text = once(text, '(ConvertTo-Json -InputObject $value -Depth 20 -Compress)',
                    '(ConvertTo-No11PrimitiveJson $value)')
    elif relative.endswith('windows/Invoke-No11MsiiOrder.ps1'):
        text = once(text, "'^発注済み[（(]発注ID='", "'^発注済み[（(](?:発注|注文)ID='")
    elif relative.endswith('tools/no11_broker_snapshot.mjs'):
        anchor = 'function normalizeId(row,sessionDate,end){'
        fn = '''export function normalizeRssFunctionName(value){
 text(value,'FUNCTION',80);
 if(/^Rss[A-Za-z0-9_]+$/.test(value))return value;
 const labels={'国内株式現物注文':'RssStockOrder','国内株式取消注文':'RssCancelOrder',
  '国内株式訂正注文':'RssModifyOrder','国内株式信用新規':'RssMarginOpenOrder',
  '国内株式信用返済':'RssMarginCloseOrder'};
 const result=labels[value.replace(/[ \\u3000]/g,'')];
 need(typeof result==='string','UNKNOWN_RSS_FUNCTION_LABEL');return result;
}
'''
        text = once(text, anchor, fn + anchor)
        text = once(text,
            "need(row&&validMsiiOrderId(row.rssOrderId),'RSS_ID');text(row.functionName,'FUNCTION',80);\n need(/^Rss[A-Za-z0-9_]+$/.test(row.functionName),'FUNCTION');",
            "need(row&&validMsiiOrderId(row.rssOrderId),'RSS_ID');\n const functionName=normalizeRssFunctionName(row.functionName);")
        text = once(text, 'return {...row,orderDate:day};',
            'return {...row,...(functionName!==row.functionName?{functionNameRaw:row.functionName}:{}),functionName,orderDate:day};')
    elif relative.endswith('tools/no11_broker_execution_service.py'):
        anchor = "    ledger.money(config.get('reserveChargesJpy', '0'))"
        text = once(text, anchor,
            "    # Operational profile ZERO must route both BUY and SELL via SOR.\n"
            "    need(config.get('feeCourse') != 'ZERO' or terms['sor'] is True,\n"
            "         'ZERO_COURSE_REQUIRES_SOR')\n" + anchor)
    return text


def collector_v2(text):
    text = once(text, "$ci=[Globalization.CultureInfo]::InvariantCulture",
        ". (Join-Path $PSScriptRoot 'Convert-No11PrimitiveJson.ps1')\n$ci=[Globalization.CultureInfo]::InvariantCulture")
    old = """ Write-Host 'NO11_REFERENCE_STAGE=READ_RSS_MARKET_VALUES'
 $start=Stamp;$values=$sheet.Range($range).Value2;$end=Stamp
 Need ($values -is [array] -and $values.Rank -eq 2 -and $values.GetLength(0) -eq $symbols.Count -and $values.GetLength(1) -eq 12) 'READ_SHAPE'
 $rows=@();$r0=$values.GetLowerBound(0);$c0=$values.GetLowerBound(1)
 for($i=0;$i -lt $symbols.Count;$i++){
  $r=$r0+$i"""
    new = """ Write-Host 'NO11_REFERENCE_STAGE=READ_ROWS_V2'
 $rows=@();$start=Stamp
 for($i=0;$i -lt $symbols.Count;$i++){
  $rowNo=$i+1
  $values=$sheet.Range(('A'+$rowNo+':L'+$rowNo)).Value2
  Need ($values -is [array] -and $values.Rank -eq 2 -and
        $values.GetLength(0) -eq 1 -and $values.GetLength(1) -eq 12) 'READ_SHAPE'
  $r=$values.GetLowerBound(0);$c0=$values.GetLowerBound(1)"""
    text = once(text, old, new)
    text = once(text, " $obj=[ordered]@{schemaId='ARK_NO11_RSS_SESSION_REFERENCE_CAPTURE_V1'",
        " $end=Stamp\n Write-Host ('NO11_REFERENCE_ROWS_V2_PARSED='+$rows.Count)\n $obj=[ordered]@{schemaId='ARK_NO11_RSS_SESSION_REFERENCE_CAPTURE_V1'")
    text = once(text, '(ConvertTo-Json -InputObject $obj -Depth 10 -Compress)',
                '(ConvertTo-No11PrimitiveJson $obj)')
    text = once(text, "if($OfflineSelfTest){", "if($OfflineSelfTest){\n . (Join-Path $PSScriptRoot 'Convert-No11PrimitiveJson.ps1') -PrimitiveJsonOfflineSelfTest")
    return text


def apply(root, check=False):
    root = root.resolve(strict=True)
    files = [REL + p for p in (
        'windows/Read-No11BrokerSnapshot.ps1', 'windows/Observe-No11AccountReadOnly.ps1',
        'windows/Invoke-No11MsiiOrder.ps1', 'tools/no11_broker_snapshot.mjs',
        'tools/no11_broker_execution_service.py')]
    plan = {}
    for relative in files:
        before = original(root, relative)
        after = transformed(relative, before)
        if before == after:
            raise ValueError('NO11_BUNDLE_NO_TRANSFORM:' + relative)
        plan[relative] = (before, after)
    original_collector = original(root, REL + 'windows/Capture-No11SessionReferenceReadOnly.ps1')
    plan[REL + 'windows/Capture-No11SessionReferenceV2ReadOnly.ps1'] = (None, collector_v2(original_collector))
    # Validate every file before writing any. No local source overwrite.
    for relative, (before, after) in plan.items():
        target = root / relative
        if target.is_symlink() or any(p.is_symlink() for p in target.parents):
            raise ValueError('NO11_BUNDLE_SYMLINK')
        if target.exists():
            current = canonical(target.read_bytes())
            if current not in (before, after):
                raise ValueError('NO11_BUNDLE_LOCAL_CHANGE_REVIEW_REQUIRED:' + relative)
        elif before is not None:
            raise ValueError('NO11_BUNDLE_SOURCE_MISSING:' + relative)
    reports = []
    for relative, (before, after) in plan.items():
        target = root / relative
        changed = not target.exists() or canonical(target.read_bytes()) != after
        if check and changed:
            raise ValueError('NO11_BUNDLE_NOT_APPLIED:' + relative)
        if changed:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(after.encode('utf-8'))
        reports.append({'path': relative, 'sha256': hashlib.sha256(after.encode('utf-8')).hexdigest()})
    return reports


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--check', action='store_true')
    a = parser.parse_args()
    result = apply(a.root, a.check)
    print(json.dumps({'status': 'SOURCE_ADAPTER_PATCH_APPLIED', 'files': result,
                      'frozenStrategyModified': False, 'orderTransmission': False}))


if __name__ == '__main__':
    main()
