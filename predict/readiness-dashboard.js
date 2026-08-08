import { summarizePerformance } from './backtest/engine.js';
import { getPredictionsAsync } from './backtest/storage.js';

function finite(value) {
  return value !== null && value !== undefined && Number.isFinite(Number(value));
}

function number(value, digits = 1) {
  return finite(value)
    ? Number(value).toLocaleString('ja-JP', {
        minimumFractionDigits: digits,
        maximumFractionDigits: digits,
      })
    : '--';
}

function percentRatio(value) {
  return finite(value) ? `${number(Number(value) * 100, 1)}%` : '--';
}

function percentPoint(value) {
  return finite(value) ? `${number(value, 1)}%` : '--';
}

function setText(id, value) {
  const node = document.getElementById(id);
  if (node) node.textContent = value;
}

function statusLabel(status) {
  return ({
    PRE_LIVE_REVIEW_READY: 'レビュー準備完了',
    PRE_LIVE_NOT_READY: 'まだ準備不足',
    BLOCKED: '安全ゲートで停止',
    NO_OPERATIONAL_DATA: '運用データ蓄積待ち',
    STABLE: '安定',
    NOT_READY: '準備不足',
    PASS: '通過',
  })[status] || String(status || '不明');
}

function blockerLabel(value) {
  const labels = {
    OPERATIONAL_DATA_NOT_PERSISTED_YET: '日次Dry-Run実績がまだ永続化されていません',
    INSUFFICIENT_SAMPLES: 'Dry-Runサンプル数が不足しています',
    ANOMALY_RATE_ABOVE_GATE: '異常率が基準を超えています',
    BLOCKED_RATE_ABOVE_GATE: 'ブロック率が基準を超えています',
    INSUFFICIENT_SAFE_DAYS: '連続安全日数が不足しています',
    EVIDENCE_INVALID: '安全証拠データが無効です',
    BROKER_BOUNDARY_INVALID: 'Broker境界監査が無効です',
    APPROVAL_INTEGRITY_INVALID: '承認整合性監査が無効です',
    ANOMALY_GATE_NOT_PASSED: '異常率ゲートが未通過です',
  };
  return labels[value] || value;
}

function normalizePersistedSnapshot(raw) {
  const evidence = raw?.evidence || {};
  const anomalyEvaluation = raw?.anomalyEvaluation || {};
  const sustainedSafety = raw?.sustainedSafety || {};
  const stability = raw?.stability || {};

  if (!raw || raw.status === 'NO_OPERATIONAL_DATA') {
    return {
      ...raw,
      status: 'NO_OPERATIONAL_DATA',
      metrics: {
        dryRunSamples: Number(raw?.historyCount || 0),
        simulatedCount: 0,
        blockedCount: 0,
        anomalyRate: null,
        blockedRate: null,
        consecutiveSafeDays: 0,
        requiredSafeDays: 10,
        safetyViolationCount: 0,
      },
      blockers: ['OPERATIONAL_DATA_NOT_PERSISTED_YET'],
      safety: raw || {},
    };
  }

  const blockers = [
    ...(Array.isArray(anomalyEvaluation.blockers) ? anomalyEvaluation.blockers : []),
    ...(Array.isArray(sustainedSafety.blockers) ? sustainedSafety.blockers : []),
  ];

  const status = evidence.status === 'BLOCKED'
    ? 'BLOCKED'
    : anomalyEvaluation.status === 'PASS' && sustainedSafety.status === 'STABLE'
      ? 'PRE_LIVE_REVIEW_READY'
      : 'PRE_LIVE_NOT_READY';

  return {
    ...raw,
    status,
    blockers: [...new Set(blockers)],
    metrics: {
      dryRunSamples: Number(evidence.sampleCount || raw.historyCount || 0),
      simulatedCount: Number(evidence.simulatedCount || 0),
      blockedCount: Number(evidence.blockedCount || 0),
      anomalyRate: finite(anomalyEvaluation.anomalyRate) ? Number(anomalyEvaluation.anomalyRate) : null,
      blockedRate: finite(anomalyEvaluation.blockedRate) ? Number(anomalyEvaluation.blockedRate) : null,
      consecutiveSafeDays: Number(sustainedSafety.consecutiveSafeDays || 0),
      requiredSafeDays: Number(sustainedSafety.requiredSafeDays || 10),
      safetyViolationCount: Number(evidence.safetyViolationCount || 0),
      operationalDays: Number(stability?.metrics?.dayCount || raw.historyCount || 0),
    },
    safety: raw,
  };
}

function renderSnapshot(snapshot) {
  const metrics = snapshot?.metrics || {};
  const badge = document.getElementById('preLiveStatusBadge');
  if (badge) {
    badge.textContent = statusLabel(snapshot?.status);
    badge.className = `dataSourceBadge ${snapshot?.status === 'PRE_LIVE_REVIEW_READY' ? 'available' : 'partial'}`;
  }

  setText('dryRunSamples', Number(metrics.dryRunSamples || 0).toLocaleString('ja-JP'));
  setText('dryRunSimulated', Number(metrics.simulatedCount || 0).toLocaleString('ja-JP'));
  setText('dryRunBlocked', Number(metrics.blockedCount || 0).toLocaleString('ja-JP'));
  setText('dryRunAnomalyRate', percentRatio(metrics.anomalyRate));
  setText('dryRunBlockedRate', percentRatio(metrics.blockedRate));
  setText('dryRunSafeDays', `${Number(metrics.consecutiveSafeDays || 0)} / ${Number(metrics.requiredSafeDays || 10)}日`);
  setText('dryRunSafetyViolations', Number(metrics.safetyViolationCount || 0).toLocaleString('ja-JP'));
  setText('dryRunOperationalDays', Number(metrics.operationalDays || 0).toLocaleString('ja-JP'));
  setText('snapshotGeneratedAt', snapshot?.generatedAt ? new Date(snapshot.generatedAt).toLocaleString('ja-JP') : '未生成');
  setText('snapshotSource', snapshot?.source || '未生成');

  const blockers = Array.isArray(snapshot?.blockers) ? snapshot.blockers : [];
  const host = document.getElementById('preLiveBlockers');
  if (host) {
    host.innerHTML = blockers.length
      ? `<ul>${blockers.map((item) => `<li>${blockerLabel(item)}</li>`).join('')}</ul>`
      : '<p class="emptyState">現在のブロッカーはありません。</p>';
  }

  const safety = snapshot?.safety || {};
  const safetyRows = [
    ['実注文', snapshot?.executionAllowed === false],
    ['Broker書き込み', safety.brokerWriteAllowed === false],
    ['Excel注文書き込み', safety.excelOrderWriteAllowed === false],
    ['RSS注文関数', safety.rssOrderFunctionAllowed === false],
    ['Live trading', safety.liveTradingAllowed === false],
    ['自動昇格', safety.automaticPromotionAllowed === false],
    ['本番更新', safety.productionUpdateAllowed === false],
    ['送信済み注文', safety.transmitted === false],
  ];
  const safetyHost = document.getElementById('safetyBoundaryTable');
  if (safetyHost) {
    safetyHost.innerHTML = `
      <table class="performanceTable">
        <thead><tr><th>境界</th><th>状態</th></tr></thead>
        <tbody>${safetyRows.map(([name, safe]) => `<tr><td>${name}</td><td>${safe ? '無効・安全側' : '要確認'}</td></tr>`).join('')}</tbody>
      </table>`;
  }
}

async function renderPredictionMetrics() {
  const records = await getPredictionsAsync();
  const resolved = records.filter((record) => record.status === 'resolved');
  const test = resolved.filter((record) => record.partition === 'test');
  const target = test.length ? test : resolved;
  const metrics = summarizePerformance(target);

  setText('predictionSamples', Number(metrics.sampleCount || 0).toLocaleString('ja-JP'));
  setText('predictionWinRate', percentPoint(metrics.winRate));
  setText('predictionProfitFactor', metrics.profitFactor === Infinity ? '∞' : number(metrics.profitFactor, 2));
  setText('predictionSharpe', number(metrics.sharpe, 2));
  setText('predictionMaxDrawdown', percentPoint(metrics.maximumDrawdown));
  setText('predictionScope', test.length ? '最終テスト期間' : '確定済み全期間');
}

async function loadPersistedReadiness() {
  const candidates = [
    '../data/phase52-dry-run/readiness.json',
    './data/phase52-readiness.json',
  ];

  let lastError = null;
  for (const url of candidates) {
    try {
      const response = await fetch(url, { cache: 'no-store' });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const payload = await response.json();
      return normalizePersistedSnapshot(payload);
    } catch (error) {
      lastError = error;
    }
  }
  throw lastError || new Error('readiness snapshot not found');
}

async function init() {
  try {
    renderSnapshot(await loadPersistedReadiness());
  } catch (error) {
    setText('snapshotGeneratedAt', '読み込み失敗');
    const host = document.getElementById('preLiveBlockers');
    if (host) host.textContent = `Read-only snapshotを読み込めませんでした: ${error.message}`;
  }

  try {
    await renderPredictionMetrics();
  } catch (error) {
    setText('predictionScope', `成績読み込み失敗: ${error.message}`);
  }
}

init();