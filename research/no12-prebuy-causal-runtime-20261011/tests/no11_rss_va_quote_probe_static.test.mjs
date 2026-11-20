import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
const pathToProbe=path.resolve(path.dirname(fileURLToPath(import.meta.url)),
 '../windows/Probe-No11ObservedPassRssMarketReadOnly.ps1');
const probe=fs.readFileSync(pathToProbe,'utf8');
test('same RSS market symbol count but six fields including cumulative Va and VWAP',()=>{
 assert.match(probe,/fields\.Count -ne 6/);
 assert.match(probe,/CreateInstance\(\[object\],\$symbols.Count,7\)/);
 assert.match(probe,/A2:G\{0\}/);
 assert.match(probe,/cumulativeVolumeRaw=\$cumVolume/);
 assert.match(probe,/cumulativeTurnoverRaw=\$cumTurnover/);
 assert.match(probe,/vendorVolumeWeightedAverage=\$vendorVwap/);
 assert.match(probe,/NO11_VA_CUMULATIVE_FIELDS/);
 assert.match(probe,/turnoverFieldClockCertified=false/);
 assert.match(probe,/nativeMinuteVaCertified=false/);
 assert.match(probe,/orderTransmission=\$false/);
 assert.doesNotMatch(probe,/RssStockOrder\s*\(|RssCancelOrder\s*\(|\.SaveAs\s*\(|\.Save\s*\(/);
 assert.ok([...probe].every(c=>c.charCodeAt(0)<=127));
});
