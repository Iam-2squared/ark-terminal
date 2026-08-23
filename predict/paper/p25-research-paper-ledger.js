import { createHash } from 'node:crypto';

export const P25_RESEARCH_PAPER_LEDGER_VERSION = 'p25-research-paper-ledger-v1';

function canonical(value) {
  if (Array.isArray(value)) return value.map(canonical);
  if (value && typeof value === 'object') {
    return Object.fromEntries(Object.keys(value).sort().map(key => [key, canonical(value[key])]));
  }
  return value;
}

function sha256(value) {
  return createHash('sha256').update(JSON.stringify(canonical(value))).digest('hex');
}

function assertDate(value) {
  const text = String(value || '');
  if (!/^\d{4}-\d{2}-\d{2}$/.test(text)) throw new Error('sessionDate must be YYYY-MM-DD.');
  return text;
}

export function createResearchPaperLedger({ accountId = 'p25-research-paper', initialCash = 1_000_000 } = {}) {
  return Object.freeze({
    version: P25_RESEARCH_PAPER_LEDGER_VERSION,
    mode: 'research_offline_only',
    executable: false,
    accountId: String(accountId),
    initialCash: Number(initialCash),
    sessions: Object.freeze([]),
    headSha256: null,
  });
}

export function appendResearchPaperSession({ ledger, sessionDate, replayResult, sourceEvaluationSha256 = null } = {}) {
  if (!ledger || ledger.version !== P25_RESEARCH_PAPER_LEDGER_VERSION) throw new Error('valid research Paper ledger is required.');
  if (!replayResult || replayResult.mode !== 'research_offline_only' || replayResult.executable !== false) throw new Error('research-only replay result is required.');
  const date = assertDate(sessionDate);
  if (ledger.sessions.some(row => row.sessionDate === date)) throw new Error(`session already exists: ${date}`);
  const previousHeadSha256 = ledger.headSha256;
  const payload = {
    sessionDate: date,
    previousHeadSha256,
    sourceEvaluationSha256: sourceEvaluationSha256 === null ? null : String(sourceEvaluationSha256),
    replayVersion: replayResult.version,
    assumptions: replayResult.assumptions,
    eventCount: replayResult.events.length,
    account: replayResult.account,
  };
  const sessionSha256 = sha256(payload);
  const session = Object.freeze({ ...payload, sessionSha256 });
  return Object.freeze({ ...ledger, sessions: Object.freeze([...ledger.sessions, session]), headSha256: sessionSha256 });
}

export function verifyResearchPaperLedger(ledger) {
  if (!ledger || ledger.version !== P25_RESEARCH_PAPER_LEDGER_VERSION) return false;
  let previous = null;
  for (const row of ledger.sessions) {
    if (row.previousHeadSha256 !== previous) return false;
    const { sessionSha256, ...payload } = row;
    if (sha256(payload) !== sessionSha256) return false;
    previous = sessionSha256;
  }
  return previous === ledger.headSha256;
}

export const P25ResearchPaperLedgerInternals = Object.freeze({ canonical, sha256, assertDate });
