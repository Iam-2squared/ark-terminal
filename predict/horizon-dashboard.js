import { getPredictionsAsync } from './backtest/storage.js';
import { compareHorizonPerformance } from './analysis/horizon-performance.js';

function finite(value) {
  return value !== null && value !== undefined && Number.isFinite(Number(value));
}

function number(value, digits = 1) {
  return finite(value) ? Number(value).toLocaleString('ja-JP', { minimumFractionDigits: digits, maximumFractionDigits: digits }) : '--';
}

function percent(value) {
  return finite(value) ? `${number(value, 1)}%` : '--';
}

function pf(value) {
  return value === Infinity ? '∞' : number(value, 2);
}

async function init() {
  const host = document.getElementById('horizonPerformanceTable');
  const badge = document.getElementById('bestHorizonBadge');
  const note = document.getElementById('horizonPerformanceNote');
  if (!host || !badge || !note) return;

  try {
    const records = await getPredictionsAsync();
    const test = records.filter((record) => record?.status === 'resolved' && record?.partition === 'test');
    const target = test.length ? test : records;
    const result = compareHorizonPerformance(target, { minimumSamples: 5 });

    badge.textContent = result.bestHorizon ? `現在の最有力: ${result.bestHorizon}営業日` : '比較データ蓄積中';
    badge.className = `dataSourceBadge ${result.bestHorizon ? 'available' : 'partial'}`;
    note.textContent = result.bestHorizon
      ? `各時間軸5件以上を最低条件として比較しています。現在の最有力は${result.bestHorizon}営業日です。サンプル増加で順位は変わります。`
      : '各時間軸5件以上の確定OOSデータがたまるまで、最強時間軸は断定しません。';

    host.innerHTML = `
      <table class="performanceTable">
        <thead><tr><th>時間軸</th><th>件数</th><th>勝率</th><th>平均</th><th>PF</th><th>Sharpe</th><th>最大DD</th><th>比較</th></tr></thead>
        <tbody>${result.horizons.map((row) => `
          <tr>
            <td>${row.horizon}営業日</td>
            <td>${row.sampleCount}</td>
            <td>${percent(row.winRate)}</td>
            <td>${percent(row.averageReturn)}</td>
            <td>${pf(row.profitFactor)}</td>
            <td>${number(row.sharpe, 2)}</td>
            <td>${percent(row.maximumDrawdown)}</td>
            <td>${row.eligible ? (row.horizon === result.bestHorizon ? '最有力' : '比較対象') : '件数不足'}</td>
          </tr>`).join('')}</tbody>
      </table>`;
  } catch (error) {
    badge.textContent = '読み込み失敗';
    badge.className = 'dataSourceBadge partial';
    note.textContent = `時間軸別成績を読み込めませんでした: ${error.message}`;
  }
}

init();
