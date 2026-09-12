import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {gunzipSync} from 'node:zlib';

import {
  loadAndValidateFrozenCandidate,
  reconstructEntrySession,
  summarizeStage1G,
} from './lib/phase57-stage1g-entry-reconstruction.mjs';
import {ALLOWED_SESSIONS} from './lib/phase57-stage1e-controlled-zip-extractor.mjs';

const [subsetRoot, modelPath] = process.argv.slice(2);
assert(subsetRoot, 'SUBSET_ROOT_REQUIRED');
assert(modelPath, 'MODEL_PATH_REQUIRED');
const modelBytes = fs.readFileSync(modelPath);
const model = loadAndValidateFrozenCandidate(modelBytes);
const sessions = ALLOWED_SESSIONS.map((sessionDate) => {
  const dir = path.join(subsetRoot, `subset-${sessionDate}`);
  const featureBundle = JSON.parse(gunzipSync(fs.readFileSync(path.join(dir, `${sessionDate}.features.json.gz`))));
  const barsBundle = JSON.parse(gunzipSync(fs.readFileSync(path.join(dir, `${sessionDate}.bars.json.gz`))));
  return reconstructEntrySession({featureBundle, barsBundle, model});
});
console.log(JSON.stringify(summarizeStage1G({sessions, modelBytes}), null, 2));
