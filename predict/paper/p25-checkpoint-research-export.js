import { assembleP253AutonomousEvidenceInputs } from '../daytrade/phase57-p25-3d-autonomous-evidence-evaluation.js';
import { buildP253PCheckpointPlan, validateP253PCheckpointCoverage } from '../daytrade/phase57-p25-3p-checkpoint-plan.js';
import { recombineP253PrefixShards } from '../daytrade/phase57-p25-3o-sharded-prefix-replay.js';
import { buildP25ResearchPaperInputs } from './p25-frozen-ledger-paper-input.js';
import { P25_SIGNAL_INTENT_SAFETY } from './p25-signal-intent-adapter.js';

export const P25_CHECKPOINT_RESEARCH_EXPORT_VERSION = 'p25-checkpoint-research-export-v1';

function assertSafety() {
  for (const [key, value] of Object.entries(P25_SIGNAL_INTENT_SAFETY)) {
    if (value !== false) throw new Error(`checkpoint Paper export safety violation: ${key}`);
  }
}

export function exportCheckpointedP25ResearchPaperInputs({
  historyPack,
  captureArtifacts = [],
  sessionIntegrityLedger,
  lineageManifest,
  checkpointsBySession = {},
} = {}) {
  assertSafety();
  const assembled = assembleP253AutonomousEvidenceInputs({
    historyPack,
    captureArtifacts,
    sessionIntegrityLedger,
    lineageManifest,
  });

  const sessions = [];
  for (const session of assembled.sessionInputs) {
    const sessionDate = String(session.sessionDate ?? session.universeRecord?.sessionDate ?? '');
    const checkpoints = Array.isArray(checkpointsBySession?.[sessionDate]) ? checkpointsBySession[sessionDate] : [];
    if (!checkpoints.length) throw new Error(`P25 Paper export checkpoints missing for ${sessionDate}`);
    const batchSize = Number(checkpoints[0]?.batchSize);
    if (!Number.isInteger(batchSize) || batchSize < 1) throw new Error(`P25 Paper export invalid batch size for ${sessionDate}`);

    const plan = buildP253PCheckpointPlan({ universeRecord: session.universeRecord, batchSize });
    validateP253PCheckpointCoverage({ plan, checkpoints });
    const recombined = recombineP253PrefixShards({
      universeRecord: session.universeRecord,
      shards: checkpoints.map(row => row.shard),
    });

    const input = buildP25ResearchPaperInputs({
      frozenLedger: recombined.ledger,
      sessionBarsBySymbol: session.sessionBarsBySymbol ?? {},
      lineageHeadSha256: assembled.lineageManifestHeadSha256,
      universeVariant: 'PRECOMMITTED_FROZEN_LEDGER',
    });

    sessions.push(Object.freeze({
      sessionDate,
      input,
      sourceProvenance: session.sourceProvenance ?? null,
      commonFairCutoffCount: Number(recombined.commonFairCutoffCount ?? 0),
      frozenTradeCount: Number(recombined.ledger?.frozenTrades?.length ?? 0),
    }));
  }

  return Object.freeze({
    version: P25_CHECKPOINT_RESEARCH_EXPORT_VERSION,
    mode: 'research_offline_only',
    executable: false,
    lineageManifestHeadSha256: assembled.lineageManifestHeadSha256,
    sessionCount: sessions.length,
    sessions: Object.freeze(sessions),
    methodology: Object.freeze({
      checkpointRecombinationOnly: true,
      frozenLedgerReusedWithoutMutation: true,
      referencePricePointInTimeOnly: true,
      futureBarsUsedForSignalGeneration: false,
      modelOrEntrySelectionChanged: false,
      currentOuterOosDoesNotSelectDynamicN: true,
      freshHoldoutConsumed: false,
    }),
    safety: P25_SIGNAL_INTENT_SAFETY,
  });
}

export const P25CheckpointResearchExportInternals = Object.freeze({ assertSafety });
