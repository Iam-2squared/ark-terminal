import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
const src=fs.readFileSync(new URL('../windows/Prepare-No11Nov02MorningHandoffReadOnly.ps1',import.meta.url),'utf8');

test('November 2 OFF handoff seals exactly 24 approved month-end-reference symbols',()=>{
 const section=src.slice(src.indexOf('$expected=@('),src.indexOf('$step='));
 const symbols=[...section.matchAll(/'([0-9A-Z]{4}\.T)'/g)].map(m=>m[1]);
 assert.equal(symbols.length,24);
 assert.equal(new Set(symbols).size,24);
 for(const excluded of ['1690.T','2014.T','2038.T','4347.T','5029.T','2612.T',
 '7867.T','4661.T','7947.T','4911.T','9861.T','9658.T','3397.T','3197.T',
 '2702.T','6678.T','7552.T','9069.T','4922.T','4526.T','9987.T','8153.T','9024.T']){
  assert.ok(!symbols.includes(excluded),excluded);
 }
});
test('read-only Handoff never creates LIVE broker config, approval or same-day fake master',()=>{
 for(const token of [
  'NO11_NOV02_HANDOFF_PREVIOUS=24_OF_24',
  'NO11_NOV02_HANDOFF_TODAY_REFERENCE=NOT_REQUESTED',
  'morningCaptureRequiresOnlyTwoOriginalBooks=$true',
  'NO11_NOV02_RSS_SECURITY_REVIEW=NOT_YET_CLEARED',
  'NO11_NOV02_HANDOFF_BOOTSTRAP=SOURCE_FIELDS_ONLY_NOT_AN_ACTIVATED_CONFIG',
  'independentSecurityReviewPerformed=$false',
  'datedMasterCreated=$false',
  'orderTransmission=$false',
  'Write-Host',
  'SESSION_REFERENCE_REQUIRES_ACTUAL_MARKET_DAY',
  'sourceInventorySha256',
  'previousArchiveStage',
  'NO11_NOV02_RSS_REFERENCE_ROWS=',
  "Test-Path -LiteralPath $referenceScript"
 ]) assert.ok(src.includes(token),token);
 for(const forbidden of [
  /RssStockOrder\s*\(/i,/RssCancelOrder\s*\(/i,/\bStop-Process\b/,
  /Start-Process.*order/i,/approvedForSession\s*=\s*\$true/i,
  /corporateActionsCleared\s*=\s*\$true/i,
  /orderTransmission\s*=\s*\$true/i,
  /\$excel\s*=/i, /Marshal\]::GetActiveObject/
 ]) assert.doesNotMatch(src,forbidden);
});
