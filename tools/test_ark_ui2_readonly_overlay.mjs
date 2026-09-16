import assert from 'node:assert/strict';
import fs from 'node:fs';
import test from 'node:test';

const source = fs.readFileSync(
  new URL('../prototypes/ark-terminal-2-readonly/public/ark-readonly-overlay.js', import.meta.url),
  'utf8',
);

test('overlay polls only the read-only GET endpoint', () => {
  assert.match(source, /const MODEL_URL = '\/api\/ui-read-model'/);
  assert.match(source, /method: 'GET'/);
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
