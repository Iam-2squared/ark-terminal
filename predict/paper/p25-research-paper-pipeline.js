import { buildP25ResearchPaperInputs } from './p25-frozen-ledger-paper-input.js';
import { replayP25ResearchSignals } from './p25-offline-paper-replay.js';
import { createResearchPaperLedger, appendResearchPaperSession, verifyResearchPaperLedger } from './p25-research-paper-ledger.js';
import { buildP25PaperShadowReport } from '../shadow/p25-paper-shadow-report.js';
import { evaluateP25PaperKillSwitch } from '../shadow/p25-paper-kill-switch.js';
import { P25_SIGNAL_INTENT_SAFETY } from './p25-signal-intent-adapter.js';

export const P25_RESEARCH_PAPER_PIPELINE_VERSION = 'p25-research-paper-pipeline-v1';

function assertSafety() {
  for (const [key, value] of Object.entries(P25_SIGNAL_INTENT_SAFETY)) {
    if (value !== false) throw new Error(`research Paper pipeline safety violation: ${key}`);
  }
}

function addMarks(rows, marks = {}) {
  return rows.map(row => {
    const value = marks?.[row.signal.symbol];
    const mark = Number(value);
    return Number.isFinite(mark) && mark > 0 ? { ...row, markPrice: mark } : row;
  });
}

export function runP25ResearchPaperPipeline({
  sessions = [],
  initialCash = 1_000_000,
  quantity = 100,
  commissionPerFill = 0,
  slippageBps = 0,
  riskPolicy = {},
  shadowOptions = {},
  killSwitchPolicy = {},
} = {}) {
  assertSafety();
  if (!Array.isArray(sessions)) throw new Error('sessions must be an array.');
  const ordered = [...sessions].sort((a, b) => String(a.sessionDate).localeCompare(String(b.sessionDate)));
  const seen = new Set();
  let account = null;
  let ledger = createResearchPaperLedger({ initialCash });
  const reports = [];

  for (const session of ordered) {
    const sessionDate = String(session?.sessionDate ?? '');
    if (!/^\d{4}-\d{2}-\d{2}$/.test(sessionDate)) throw new Error('sessionDate must be YYYY-MM-DD.');
    if (seen.has(sessionDate)) throw new Error(`duplicate research Paper session: ${sessionDate}`);
    seen.add(sessionDate);

    const input = buildP25ResearchPaperInputs({
      frozenLedger: session.frozenLedger,
      sessionBarsBySymbol: session.sessionBarsBySymbol ?? {},
      lineageHeadSha256: session.lineageHeadSha256,
      universeVariant: 'PRECOMMITTED_FROZEN_LEDGER',
    });
    const replay = replayP25ResearchSignals({
      signals: addMarks(input.rows, session.markPrices),
      initialCash,
      quantity,
      riskPolicy,
      commissionPerFill,
      slippageBps,
      startingAccount: account,
    });
    account = replay.account;
    const shadowReport = buildP25PaperShadowReport({ replayResult: replay, observations: session.shadowObservations ?? {}, options: shadowOptions });
    const killSwitch = evaluateP25PaperKillSwitch({ account, shadowReport, safety: P25_SIGNAL_INTENT_SAFETY, policy: killSwitchPolicy });
    ledger = appendResearchPaperSession({ ledger, sessionDate, replayResult: replay, sourceEvaluationSha256: session.sourceEvaluationSha256 ?? null });
    if (!verifyResearchPaperLedger(ledger)) throw new Error('research Paper ledger integrity failure.');
    reports.push(Object.freeze({ sessionDate, input, replay, shadowReport, killSwitch }));
    if (killSwitch.tripped) break;
  }

  return Object.freeze({
    version: P25_RESEARCH_PAPER_PIPELINE_VERSION,
    mode: 'research_offline_only',
    executable: false,
    safety: P25_SIGNAL_INTENT_SAFETY,
    completedSessionCount: reports.length,
    halted: reports.some(row => row.killSwitch.tripped),
    account,
    ledger,
    reports: Object.freeze(reports),
  });
}

export const P25ResearchPaperPipelineInternals = Object.freeze({ assertSafety, addMarks });
