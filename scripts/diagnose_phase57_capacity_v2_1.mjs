import fs from 'node:fs';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const sha = s => createHash('sha256').update(s).digest('hex');
export function replaceOnce(source, before, after) {
  if (source.split(before).length !== 2) throw new Error('DIAGNOSTIC_ANCHOR_MISMATCH');
  return source.replace(before, after);
}
export function instrumentTrainer(source) {
  if (sha(source) !== 'b3bf9db5c33d282bcc9aabece765251f22923fe9f0bcf70afb028c182cef532b') throw new Error('FROZEN_TRAINER_HASH_MISMATCH');
  source = replaceOnce(source, '  let best = null;\n  for (const a of grids.RANK_6_10)', '  const diagnostics = [];\n  let best = null;\n  for (const a of grids.RANK_6_10)');
  source = replaceOnce(source, '        if (\n          eligible &&', '        diagnostics.push(candidate);\n        if (\n          eligible &&');
  return replaceOnce(source, '  assert(best, "V2_1_DEVELOPMENT_NO_ROBUST_MAPPING_MEETS_PRECOMMITTED_GATES");', '  return { diagnostics, choices, grids, oofDecisionCount: oofRows.length, eligibleCount: diagnostics.filter(c => c.eligible).length };');
}
export function summarize(result, spec) {
  const g = spec.mappingSelectionContract.eligibleGlobalGates;
  const floor = spec.mappingSelectionContract.eligibleFoldGate.minimumUtilityDifferenceBpsInEveryHeldOutFold;
  const gates = {
    globalUtility: c => Number.isFinite(c.global.utilityDifference) && c.global.utilityDifference >= g.utilityDifferenceMinimumBps,
    relativeCount: c => Number.isFinite(c.global.countRatio) && c.global.countRatio >= g.meanCandidateCountMinimumRelativeIncrease,
    absoluteCount: c => Number.isFinite(c.global.absoluteIncrease) && c.global.absoluteIncrease >= g.meanCandidateCountMinimumAbsoluteIncrease,
    stability: c => Number.isFinite(c.global.jump) && c.global.jump <= g.maximumAdjacentDecisionJumpGreaterThanFiveRate,
    everyFoldUtility: c => Number.isFinite(c.worstFoldUtilityDifference) && c.worstFoldUtilityDifference >= floor,
  };
  const candidates = result.diagnostics.map(c => {
    const failures = Object.entries(gates).filter(([,pass])=>!pass(c)).map(([name])=>name);
    if (c.eligible !== (failures.length === 0)) throw new Error('ELIGIBILITY_PARITY_FAILED');
    return {...c, failures};
  });
  return { classification: 'DEVELOPMENT_DIAGNOSTIC_ONLY', modelPromoted: false,
    validationReleased: false, untouchedOosReleased: false,
    candidateCount: candidates.length, uniqueThresholdCount: new Set(candidates.map(c=>JSON.stringify(c.thresholds))).size,
    eligibleCount: candidates.filter(c=>c.eligible).length,
    failedByGate: Object.fromEntries(Object.keys(gates).map(k=>[k,candidates.filter(c=>c.failures.includes(k)).length])),
    choices: result.choices, grids: result.grids, oofDecisionCount: result.oofDecisionCount, candidates };
}
function main() {
  const trainerPath = 'scripts/run_phase57_selector_capacity_v2_1.mjs';
  const runnerPath = 'scripts/recover_phase57_capacity_v2_1_development.mjs';
  const trainer = fs.readFileSync(trainerPath,'utf8');
  let runner = fs.readFileSync(runnerPath,'utf8');
  if (sha(runner) !== '73f88e5241959b07d3a998c34107e7d8d0df0418a435f262cc6f55dee3d585f1') throw new Error('RECOVERY_HASH_MISMATCH');
  runner = replaceOnce(runner, './run_phase57_selector_capacity_v2_1.mjs', './capacity_v21_diagnostic_instrumented.mjs');
  runner = replaceOnce(runner, '...recover(trainV21,rows,source,fresh,allocation)', "status: 'CAPACITY_V2_1_DIAGNOSTIC_COMPLETE', result: trainV21(rows,source,fresh,allocation)");
  runner = runner.replaceAll('artifacts/capacity-v2-1-development-recovery','artifacts/capacity-v2-1-development-diagnostic');
  const generated = ['scripts/capacity_v21_diagnostic_instrumented.mjs','scripts/capacity_v21_diagnostic_runner.mjs'];
  if (generated.some(p=>fs.existsSync(p))) throw new Error('TEMP_FILE_ALREADY_EXISTS');
  try {
    fs.writeFileSync(generated[0], instrumentTrainer(trainer));
    fs.writeFileSync(generated[1],runner);
    const run = spawnSync(process.execPath,[generated[1]],{encoding:'utf8'});
    if (run.status !== 0) throw new Error('DIAGNOSTIC_CHECKPOINT_OR_TRAINING_FAILED');
    const root = 'artifacts/capacity-v2-1-development-diagnostic';
    const report = JSON.parse(fs.readFileSync(root+'/recovery-summary.json'));
    const summary = {...summarize(report.result,JSON.parse(fs.readFileSync('predict/research/phase57-selector-capacity-v2-1-precommit.json'))),
      sourceRunId: report.sourceRunId, sourceHeadSha: report.sourceHeadSha,
      reusedShards:report.reusedShards, sessionCount:report.sessionCount, decisionCount:report.decisionCount,
      marketDataRecomputed:false, gatesChanged:false, frozenTrainerSha256:sha(trainer)};
    const bytes=JSON.stringify(summary,null,2)+'\n';
    fs.writeFileSync(root+'/diagnostic-summary.json',bytes);
    fs.writeFileSync(root+'/diagnostic-summary.json.sha256',sha(bytes)+'  diagnostic-summary.json\n');
    console.log(bytes);
  } finally { for(const p of generated) fs.rmSync(p,{force:true}); }
}
if(process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try { main(); } catch(error) { console.error(error.message); process.exitCode=1; }
}
