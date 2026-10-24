import fs from 'node:fs';
import path from 'node:path';
import {
  PHASE57_EXIT_V5_DEVELOPMENT_VALIDATION_SAFETY,
  reduceExitV5DevelopmentValidationShards,
} from '../predict/daytrade/phase57-exit-v5-development-validation.js';

function arg(name, fallback = null) {
  const index = process.argv.indexOf(name);
  return index >= 0 && index + 1 < process.argv.length ? process.argv[index + 1] : fallback;
}

function writeAtomic(file, value) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  const temporary = `${file}.tmp-${process.pid}`;
  fs.writeFileSync(temporary, `${JSON.stringify(value, null, 2)}\n`, 'utf8');
  fs.renameSync(temporary, file);
}

const inputDir = arg('--input-dir');
const outputPath = arg('--output', '/tmp/phase57-exit-v5-development-validation-evidence.json');
if (!inputDir) {
  console.error('usage: node scripts/reduce_phase57_exit_v5_validation_shards.mjs --input-dir <dir> [--output <json>]');
  process.exit(2);
}

try {
  const files = fs.readdirSync(inputDir).filter((name) => name.endsWith('.json')).sort();
  const shards = files.map((name) => JSON.parse(fs.readFileSync(path.join(inputDir, name), 'utf8')));
  const result = reduceExitV5DevelopmentValidationShards(shards);
  const payload = { ...result, createdAt: new Date().toISOString() };
  writeAtomic(outputPath, payload);
  console.log(JSON.stringify({
    status: payload.status,
    output: outputPath,
    sessionDates: payload.sessionDates,
    pairedCount: payload.pairedCount,
    developmentSampleCount: payload.developmentSampleCount,
    summaries: payload.summary.models,
    pairedDeltas: payload.summary.pairedDeltas,
    classification: payload.classification,
    methodology: payload.methodology,
    safety: payload.safety,
  }, null, 2));
} catch (error) {
  console.error(JSON.stringify({
    status: 'BLOCKED_EXIT_V5_VALIDATION_REDUCE',
    error: String(error?.message ?? error),
    safety: PHASE57_EXIT_V5_DEVELOPMENT_VALIDATION_SAFETY,
  }, null, 2));
  process.exit(1);
}
