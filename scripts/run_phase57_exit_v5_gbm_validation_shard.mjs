import fs from 'node:fs';
import path from 'node:path';
import {
  PHASE57_EXIT_V5_DEVELOPMENT_VALIDATION_SAFETY,
  runExitV5DevelopmentValidationGbmShard,
} from '../predict/daytrade/phase57-exit-v5-development-validation.js';

function arg(name, fallback = null) {
  const index = process.argv.indexOf(name);
  return index >= 0 && index + 1 < process.argv.length ? process.argv[index + 1] : fallback;
}

function readJson(file, label) {
  try {
    return JSON.parse(fs.readFileSync(file, 'utf8'));
  } catch (error) {
    throw new Error(`${label} JSON read failed: ${error?.message ?? error}`);
  }
}

function writeAtomic(file, value) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  const temporary = `${file}.tmp-${process.pid}`;
  fs.writeFileSync(temporary, `${JSON.stringify(value, null, 2)}\n`, 'utf8');
  fs.renameSync(temporary, file);
}

const historyPath = arg('--history-pack');
const substratePath = arg('--substrate');
const validationSessionDate = arg('--validation-session');
const outputPath = arg('--output', `/tmp/phase57-exit-v5-gbm-validation-${validationSessionDate ?? 'unknown'}.json`);
if (!historyPath || !substratePath || !validationSessionDate) {
  console.error('usage: node scripts/run_phase57_exit_v5_gbm_validation_shard.mjs --history-pack <json> --substrate <json> --validation-session YYYY-MM-DD [--output <json>]');
  process.exit(2);
}

try {
  const result = runExitV5DevelopmentValidationGbmShard({
    historyPack: readJson(historyPath, 'history pack'),
    substrate: readJson(substratePath, 'substrate'),
    validationSessionDate,
  });
  const payload = { ...result, createdAt: new Date().toISOString() };
  writeAtomic(outputPath, payload);
  console.log(JSON.stringify({
    status: payload.status,
    output: outputPath,
    sessionDate: payload.sessionDate,
    pairedCount: payload.pairedCount,
    validationStateSampleCount: payload.validationStateSampleCount,
    causalAnalogCount: payload.causalAnalogCount,
    developmentFingerprint: payload.developmentFingerprint,
    gbmModelFingerprint: payload.gbmModelFingerprint,
    gbmSpec: payload.methodology.gbmSpec,
    summaries: payload.evaluation.summary.models,
    pairedDeltas: payload.evaluation.summary.pairedDeltas,
    classification: payload.classification,
    methodology: payload.methodology,
    safety: payload.safety,
  }, null, 2));
} catch (error) {
  console.error(JSON.stringify({
    status: 'BLOCKED_EXIT_V5_GBM_VALIDATION_SHARD',
    validationSessionDate,
    error: String(error?.message ?? error),
    safety: PHASE57_EXIT_V5_DEVELOPMENT_VALIDATION_SAFETY,
  }, null, 2));
  process.exit(1);
}
