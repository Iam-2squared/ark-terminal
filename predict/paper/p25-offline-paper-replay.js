import { createPaperAccount } from './paper-account.js';
import { submitPaperOrder, executePaperOrder, markPaperAccount } from './paper-engine.js';
import { createP25ResearchIntent, toPaperOrderResearchDraft, P25_SIGNAL_INTENT_SAFETY } from './p25-signal-intent-adapter.js';

export const P25_OFFLINE_PAPER_REPLAY_VERSION = 'p25-offline-paper-replay-v1';

function finitePositive(value, name) {
  const number = Number(value);
  if (!Number.isFinite(number) || number <= 0) throw new Error(`${name} must be positive.`);
  return number;
}

function assertOfflineSafety() {
  for (const [key, value] of Object.entries(P25_SIGNAL_INTENT_SAFETY)) {
    if (value !== false) throw new Error(`offline replay safety violation: ${key}`);
  }
}

export function replayP25ResearchSignals({
  signals = [],
  initialCash = 1_000_000,
  quantity = 100,
  riskPolicy = {},
  commissionPerFill = 0,
  slippageBps = 0,
  accountId = 'p25-research-paper',
} = {}) {
  assertOfflineSafety();
  if (!Array.isArray(signals)) throw new Error('signals must be an array.');
  if (!Number.isFinite(Number(slippageBps)) || Number(slippageBps) < 0) throw new Error('slippageBps must be non-negative.');
  if (!Number.isFinite(Number(commissionPerFill)) || Number(commissionPerFill) < 0) throw new Error('commissionPerFill must be non-negative.');

  let account = createPaperAccount({ accountId, initialCash });
  const events = [];

  for (const row of signals) {
    const intent = createP25ResearchIntent(row.signal);
    const draft = toPaperOrderResearchDraft(intent, { quantity });
    if (!draft.eligible) {
      events.push({ intentId: intent.intentId, symbol: intent.symbol, status: 'observe_only', reason: draft.reason });
      continue;
    }

    const referencePrice = finitePositive(row.referencePrice, 'referencePrice');
    const fillPrice = referencePrice * (1 + Number(slippageBps) / 10_000);
    const submitted = submitPaperOrder({
      account,
      orderInput: draft.orderInput,
      estimatedPrice: fillPrice,
      riskPolicy,
      submittedAt: intent.sourceTimestamp,
    });
    account = submitted.account;

    if (!submitted.risk.passed) {
      events.push({ intentId: intent.intentId, symbol: intent.symbol, status: 'risk_rejected', reasons: submitted.risk.reasons });
      continue;
    }

    const executed = executePaperOrder({
      account,
      orderId: submitted.order.orderId,
      fillPrice,
      commission: Number(commissionPerFill),
      filledAt: intent.sourceTimestamp,
    });
    account = executed.account;
    events.push({
      intentId: intent.intentId,
      symbol: intent.symbol,
      status: 'simulated_fill',
      referencePrice,
      fillPrice,
      slippageBps: Number(slippageBps),
      commission: Number(commissionPerFill),
      provenance: {
        evidenceDate: intent.evidenceDate,
        universeVariant: intent.universeVariant,
        modelVersion: intent.modelVersion,
        lineageHeadSha256: intent.lineageHeadSha256,
      },
    });
  }

  const marks = {};
  for (const row of signals) {
    if (row.markPrice !== null && row.markPrice !== undefined) marks[String(row.signal.symbol).toUpperCase()] = finitePositive(row.markPrice, 'markPrice');
  }
  if (Object.keys(marks).length > 0) account = markPaperAccount({ account, prices: marks });

  return Object.freeze({
    version: P25_OFFLINE_PAPER_REPLAY_VERSION,
    mode: 'research_offline_only',
    executable: false,
    safety: P25_SIGNAL_INTENT_SAFETY,
    assumptions: Object.freeze({ initialCash: Number(initialCash), quantity: Number(quantity), commissionPerFill: Number(commissionPerFill), slippageBps: Number(slippageBps) }),
    events: Object.freeze(events),
    account: Object.freeze(account),
  });
}

export const P25OfflinePaperReplayInternals = Object.freeze({ assertOfflineSafety, finitePositive });
