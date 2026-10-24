import fs from 'node:fs';
import path from 'node:path';
import {
  PHASE57_EXIT_V5_DEVELOPMENT_VALIDATION_SAFETY,
  prepareExitV5DevelopmentValidationSubstrate,
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
const outputPath = arg('--output', '/tmp/phase57-exit-v5-development-validation-substrate.json');
if (!historyPath) {
  console.error('usage: node scripts/prepare_phase57_exit_v5_development_validation.mjs --history-pack <json> [--output <json>]');
  process.exit(2);
}

try {
  const substrate = prepareExitV5DevelopmentValidationSubstrate(readJson(historyPath, 'history pack'));
  const payload = { ...substrate, createdAt: new Date().toISOString() };
  writeAtomic(outputPath, payload);
  console.log(JSON.stringify({
    status: payload.status,
    output: outputPath,
    frozenEntryCount: payload.frozenEntryCount,
    developmentEntryCount: payload.developmentEntryCount,
    validationEntryCount: payload.validationEntryCount,
    validationCountsByDate: payload.validationCountsByDate,
    stateSampleAudit: payload.stateSampleAudit,
    entrySetFingerprint: payload.entrySetFingerprint,
    marketDataFingerprint: payload.marketDataFingerprint,
    pairedSubstrateFingerprint: payload.pairedSubstrateFingerprint,
    safety: payload.safety,
  }, null, 2));
} catch (error) {
  console.error(JSON.stringify({
    status: 'BLOCKED_EXIT_V5_DEVELOPMENT_VALIDATION_PREPARE',
    error: String(error?.message ?? error),
    safety: PHASE57_EXIT_V5_DEVELOPMENT_VALIDATION_SAFETY,
  }, null, 2));
  process.exit(1);
}
