import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import fs from 'node:fs';
import test from 'node:test';

const overlayPath = new URL('../prototypes/ark-terminal-2-readonly/public/ark-readonly-overlay.js', import.meta.url);
const indexPath = new URL('../prototypes/ark-terminal-2-readonly/public/index.html', import.meta.url);
const source = fs.readFileSync(overlayPath, 'utf8');

test('frozen Ark Terminal 2.0 distribution snapshot is byte-identical to the approved UI', () => {
  const sha256 = createHash('sha256').update(fs.readFileSync(indexPath)).digest('hex');
  assert.equal(sha256, '4d630234fc64c1b5d8df50851fde1989158e61a1db36d799d247fc8ae8f98870');
});

test('overlay polls only the read-only GET endpoint', () => {
  assert.match(source, /const MODEL_URL = '\/api\/ui-read-model'/);
  assert.match(source, /method:\s*'GET'/);
  assert.doesNotMatch(source, /method:\s*'POST'/);
  assert.doesNotMatch(source, /method:\s*'DELETE'/);
});

test('overlay replaces all six screens instead of leaving demo data visible', () => {
  for (const screen of ['HOME','SELECTOR','POSITIONS','ORDERS','PERFORMANCE','SYSTEM']) {
    assert.ok(source.includes(`case '${screen}'`), `missing ${screen}`);
  }
  assert.match(source, /ローカルRead Modelを取得できるまでダミーデータは表示しません/);
  assert.match(source, /デモの損益・勝率は実運用画面には表示しません/);
});

test('mutation controls are disabled in the overlay', () => {
  assert.match(source, /\.preflightButton,\.killButton,\.stageButton,\.cancelOrder/);
  assert.match(source, /button\.disabled = true/);
  for (const capability of ['orderSubmit','orderCancel','killSwitchChange','brokerWrite','excelOrderWrite','rssOrderFunction']) {
    assert.ok(source.includes(capability));
  }
});
