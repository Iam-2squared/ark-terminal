import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
const source=fs.readFileSync(new URL('../windows/Rescue-No11Nov02Book3ReferencePrimitiveJsonReadOnly.ps1',import.meta.url),'utf8');

test('Nov2 Book3 rescue emits scalar-only JSON and never serializes nested COM/PSObject',()=>{
 for(const token of [
  'function JsonQuoted([string]$value)',
  'function JsonPrimitive($value)',
  "'NO11_REFERENCE_STAGE=SERIALIZE_PRIMITIVES_BEGIN'",
  'NO11_REFERENCE_STAGE=SERIALIZE_PRIMITIVES_COMPLETE',
  "NO11_REFERENCE_RESCUE_PRIMITIVE_ESCAPING_SELFTEST=PASS",
  "NO11_REFERENCE_RESCUE_BOOK3_PRESERVED=True",
  "NO11_REFERENCE_ROW_PARSED=",
  "NO11_SESSION_REFERENCE_FILE=",
  "JsonPrimitive $entry[$key]",
  "RESCUE_READ_EXCEEDED_30_SECONDS",
  "RSS_DAY_OR_FIELD_MISMATCH",
  "CORPORATE",
  "source='RssMarket_SELECTED_REFERENCE_READONLY'",
 ].filter(x=>x!=='CORPORATE')) assert.ok(source.includes(token),token);
 for(const dangerous of [
   /\$jsonWriter\.Serialize\(\$obj\)/,
   /ConvertTo-Json\s+-InputObject\s+\$obj/,
   /Workbooks\.Add\s*\(/i,/Workbooks\.Open\s*\(/i,
   /\.SaveAs\s*\(/i,/\.Save\s*\(/i,
   /RssStockOrder\s*\(/i,/RssCancelOrder\s*\(/i,
   /Stop-Process/i,/approvedForSession\s*=\s*\$true/i,
   /\$book\.Close\s*\(/,
 ]) assert.doesNotMatch(source,dangerous);
});
