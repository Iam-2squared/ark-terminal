import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {buildArkTerminalUiReadModel} from './phase57_ui_read_model.mjs';

function parseArgs(argv) {
  const values = {};
  for (let index = 2; index < argv.length; index += 2) {
    const key = argv[index];
    const value = argv[index + 1];
    if (!key?.startsWith('--') || value === undefined) throw new Error('USAGE');
    values[key.slice(2)] = value;
  }
  return values;
}

function readJson(filePath, label) {
  if (!filePath) return null;
  const resolved = path.resolve(filePath);
  if (!fs.existsSync(resolved)) throw new Error(`${label}_FILE_MISSING`);
  const parsed = JSON.parse(fs.readFileSync(resolved, 'utf8').replace(/^\uFEFF/, ''));
  if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) throw new Error(`${label}_OBJECT_REQUIRED`);
  return parsed;
}

export function exportArkTerminalUiReadModel({
  snapshotPath,
  outputPath,
  pipelinePath = null,
  ownershipPath = null,
  runtimeSafetyPath = null,
  generatedAt = new Date().toISOString(),
  maxSnapshotAgeSeconds = 30,
} = {}) {
  if (!snapshotPath || !outputPath) throw new Error('SNAPSHOT_AND_OUTPUT_REQUIRED');
  const inputs = [snapshotPath, pipelinePath, ownershipPath, runtimeSafetyPath]
    .filter(Boolean)
    .map(value => path.resolve(value));
  const output = path.resolve(outputPath);
  if (inputs.includes(output)) throw new Error('OUTPUT_MUST_NOT_OVERWRITE_INPUT');
  if (fs.existsSync(output)) throw new Error('OUTPUT_ALREADY_EXISTS');

  const accountSnapshot = readJson(snapshotPath, 'SNAPSHOT');
  const lockedPipeline = readJson(pipelinePath, 'PIPELINE');
  const ownershipBaseline = readJson(ownershipPath, 'OWNERSHIP');
  const runtimeSafety = readJson(runtimeSafetyPath, 'RUNTIME_SAFETY');
  const maxAge = Number(maxSnapshotAgeSeconds);

  const model = buildArkTerminalUiReadModel({
    accountSnapshot,
    lockedPipeline,
    ownershipBaseline,
    runtimeSafety,
    generatedAt,
    maxSnapshotAgeSeconds: maxAge,
  });

  fs.mkdirSync(path.dirname(output), {recursive: true});
  fs.writeFileSync(output, `${JSON.stringify(model, null, 2)}\n`, {encoding: 'utf8', flag: 'wx'});
  return model;
}

const isMain = process.argv[1] && fileURLToPath(import.meta.url) === path.resolve(process.argv[1]);
if (isMain) {
  try {
    const args = parseArgs(process.argv);
    if (!args.snapshot || !args.output) throw new Error('USAGE');
    const model = exportArkTerminalUiReadModel({
      snapshotPath: args.snapshot,
      outputPath: args.output,
      pipelinePath: args.pipeline || null,
      ownershipPath: args.ownership || null,
      runtimeSafetyPath: args['runtime-safety'] || null,
      generatedAt: args['generated-at'] || new Date().toISOString(),
      maxSnapshotAgeSeconds: args['max-age-seconds'] === undefined ? 30 : Number(args['max-age-seconds']),
    });
    console.log('ARK_TERMINAL_UI_READ_MODEL_EXPORTED');
    console.log(`SOURCE_STATE=${model.source.freshness.state}`);
    console.log(`TRADE_READINESS=${model.system.tradeReadiness}`);
    console.log(`BUYING_POWER=${model.home.buyingPower ?? 'UNAVAILABLE'}`);
    console.log(`POSITIONS=${model.positions.length}`);
    console.log(`MUTATIONS=false`);
  } catch (error) {
    console.error(`ARK_TERMINAL_UI_READ_MODEL_ERROR:${error.message}`);
    process.exitCode = 2;
  }
}
