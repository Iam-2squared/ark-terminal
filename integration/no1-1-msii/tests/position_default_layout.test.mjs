// Offline-only structural assertions; never open Excel or broker connection.
import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const read = name => readFileSync(new URL('../windows/'+name,import.meta.url),'utf8');
const b=read('New-No11RssWorkbook.ps1'),s=read('Get-No11ReadOnlySnapshot.ps1'),l=read('Start-No11ReadOnlySetup.ps1'),p=read('Test-No11RssStatusParser.ps1');
test('default RSS positions only; distinct versioned workbook',()=>{
 for(const x of [b,s,l])assert.ok(x.includes('Ark_No11_RSS_DefaultHeaders_v2.xlsx'));
 for(const x of [b,s,p])assert.ok(x.includes('=RssPositionList()'));
 for(const x of [b,s,p])assert.ok(!x.includes('=RssPositionList(AL2:AU2)'));
});
test('all eighteen source headings are checked',()=>{
 const headings=[["AL2","銘柄コード"],["AM2","銘柄名称"],["AN2","口座区分"],["AO2","保有数量"],["AP2","発注数量"],["AQ2","平均取得価額"],["AR2","時価"],["AS2","前日比"],["AT2","前日比率"],["AU2","時価評価額"],["AV2","評価損益額"],["AW2","評価損益率"],["AX2","銘柄情報等"],["AY2","JAX時価"],["AZ2","JNX時価"],["BA2","PER"],["BB2","PBR"],["BC2","配当利回り"]];
 for(const [key,val] of headings){
   assert.ok(b.includes(key+' = "'+val+'"'),key+' missing in builder');
   assert.ok(s.includes('"'+key+'"="'+val+'"'),key+' missing in snapshotter');
 }
});
test('price and PnL columns use verified full layout',()=>{
 for(const [name,n] of [['marketValue',47],['unrealizedPnl',48],['unrealizedPnlPercent',49]])
   assert.ok(s.includes(name+'=$acct.Cells.Item($row,'+n+').Value2'),name);
 assert.ok(s.includes('BROKER_POSITION_SYMBOL_MISSING'));
 assert.ok(s.includes('actualFeedTimestampCertified = $false'));
 assert.ok(l.includes('DoNotAutoOpenWorkbook = $true'));
});

test('formula whitelist scans only actual formula-bearing cells within a bounded rectangle',()=>{
  assert.ok(b.includes('function Assert-No11FormulaFootprint'));
  assert.ok(b.includes('$used.Cells.Item($r,$c)'));
  assert.ok(b.includes('if ([bool]$hasFormula)'));
  assert.ok(b.includes('NO11_EXTRA_FORMULA_FORBIDDEN'));
  assert.ok(b.includes('NO11_REQUIRED_FORMULA_NOT_FOUND'));
  assert.ok(b.includes('NO11_USED_RANGE_UNBOUNDED'));
  assert.ok(!b.includes('foreach ($cell in $Sheet.UsedRange.SpecialCells(-4123).Cells)'));
  assert.ok(p.includes('NO11_FORMULA_FOOTPRINT_MOCK_PASS'));
});

test('read-only setup validates receipt path and versioned workbook provenance',()=>{
  const setup=read('Start-No11ReadOnlySetup.ps1');
  assert.ok(setup.includes('NO11_DIAGNOSTIC_WRONG_WORKBOOK'));
  assert.ok(setup.includes('NO11_EXPECTED_WORKBOOK_NOT_PERSISTED'));
  assert.ok(setup.includes('NO11_DIAGNOSTIC_VERIFIED_FOR_V2'));
  assert.ok(b.includes('NO11_DIAGNOSTIC_WORKBOOK_IDENTITY_MISMATCH'));
});

test('ready workbook is copied without Excel mutation and exact source hash is checked',()=>{
  assert.ok(!b.includes('Workbooks.Add(-4167)'));
  assert.ok(!b.includes('New-No11BlankXlsx'));
  assert.ok(!b.includes('SaveAs('));
  assert.ok(b.includes('[IO.File]::Copy($template,$FullPath,$false)'));
  assert.ok(b.includes('NO11_VERIFIED_TEMPLATE_HASH_MISMATCH'));
  assert.ok(b.includes('NO11_COPIED_WORKBOOK_HASH_MISMATCH'));
  assert.ok(b.includes('NO11_READY_WORKBOOK_NOT_ACCESSIBLE_OPEN_MANUALLY'));
  assert.ok(b.includes('NO11_EXCEL_OPEN_RETURNED_FOREIGN_WORKBOOK'));
  assert.ok(b.includes('NO11_READY_WORKBOOK_NOT_READ_ONLY'));
  assert.ok(b.includes('NO11_LEGACY_WORKBOOK_OVERWRITE_FORBIDDEN'));
  assert.ok(b.includes('Application = $app'));
  assert.ok(b.includes('Workbook = $workbook'));
});
