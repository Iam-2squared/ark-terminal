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
