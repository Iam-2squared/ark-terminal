import fs from 'node:fs';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { trainV21 } from './run_phase57_selector_capacity_v2_1.mjs';

const SOURCE_RUN = 34189128681;
const SOURCE_SHA = 'f3543b5a604d25442c28fc3cb475e89274400bd5';
const NO_MAPPING = 'V2_1_DEVELOPMENT_NO_ROBUST_MAPPING_MEETS_PRECOMMITTED_GATES';
const hash = b => createHash('sha256').update(b).digest('hex');
function check(ok) { if (!ok) throw new Error('CHECKPOINT_INTEGRITY_FAILED'); }
function readVerified(file) {
  const bytes = fs.readFileSync(file);
  check(hash(bytes) === fs.readFileSync(file + '.sha256','utf8').trim().split(/\s+/)[0]);
  return JSON.parse(bytes);
}
function safe(safety) {
  const expected = JSON.parse(fs.readFileSync('predict/research/phase57-selector-capacity-v2-1-precommit.json')).safety;
  check(Object.keys(expected).every(k => expected[k] === false && safety?.[k] === false));
}
export function recover(train, rows, source, fresh, allocation) {
  try { return { status: 'CAPACITY_V2_1_DEVELOPMENT_COMPLETE', result: train(rows,source,fresh,allocation) }; }
  catch (error) {
    if (error?.message !== NO_MAPPING) throw error;
    return { status: 'CAPACITY_V2_1_FINAL_NO_GO', reason: NO_MAPPING,
      validationReleased: false, untouchedOosReleased: false, model: null,
      automaticPromotion: false, safety: allocation.safety };
  }
}
function main() {
  const root = 'artifacts/recovery-input';
  const allocation = readVerified(root+'/allocation/allocation.json');
  const source = readVerified(root+'/source-admission/admission.json');
  const fresh = readVerified(root+'/fresh-admission/admission.json');
  [allocation, source, fresh].forEach(x => safe(x.safety));
  check(allocation.status === 'CAPACITY_V2_1_FRESH_ALLOCATION_MATERIALIZED');
  check(fresh.status === 'CAPACITY_V2_1_DATASET_ADMISSION_PASS');
  const dir = root+'/shards';
  const names = fs.readdirSync(dir).sort();
  check(names.length === 6);
  let rows = [];
  const indices = new Set();
  for(const name of names) {
    const report = readVerified(path.join(dir,name,'decision-samples.json'));
    safe(report.safety);
    check(report.status === 'CAPACITY_V2_1_DEVELOPMENT_SHARD_COMPLETE');
    check(report.datasetId === allocation.datasetId && report.shardCount === 6);
    check(Number.isInteger(report.shardIndex) && report.shardIndex >= 0 && report.shardIndex < 6 && !indices.has(report.shardIndex));
    indices.add(report.shardIndex);
    const dates = allocation.developmentDates.filter((_,i)=>i%6===report.shardIndex);
    check(report.rows.length === dates.length*20 && report.decisionCount === report.rows.length);
    check(JSON.stringify([...new Set(report.rows.map(r=>r.sessionDate))].sort()) === JSON.stringify(dates));
    rows.push(...report.rows);
  }
  rows.sort((a,b)=>a.featureCutoff.localeCompare(b.featureCutoff));
  check(rows.length === 1780 && new Set(rows.map(r=>r.featureCutoff)).size === 1780);
  const report = { ...recover(trainV21,rows,source,fresh,allocation),
    sourceRunId: SOURCE_RUN, sourceHeadSha: SOURCE_SHA,
    reusedShards: 6, sessionCount: 89, decisionCount: rows.length,
    marketDataRecomputed: false, gatesChanged: false };
  const out = 'artifacts/capacity-v2-1-development-recovery';
  fs.mkdirSync(out,{recursive:true});
  const bytes=JSON.stringify(report,null,2)+'\n';
  fs.writeFileSync(out+'/recovery-summary.json',bytes);
  fs.writeFileSync(out+'/recovery-summary.json.sha256',hash(bytes)+'  recovery-summary.json\n');
  console.log(JSON.stringify({status:report.status,reason:report.reason,reusedShards:6,sessionCount:89,decisionCount:rows.length}));
}
if(process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try { main(); } catch { console.error('CAPACITY_V2_1_RECOVERY_TECHNICAL_FAILURE'); process.exitCode=1; }
}
