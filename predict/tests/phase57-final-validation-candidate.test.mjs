// Artifact/contract-only regression. Never imports a model or a project runner.
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const root = fileURLToPath(new URL('../../', import.meta.url));
const evidence = 'docs/evidence/phase57-msh-entry-long-v1-final-validation-model/';
const read = name => JSON.parse(fs.readFileSync(path.join(root, name), 'utf8'));
const hash = name => createHash('sha256').update(fs.readFileSync(path.join(root, name))).digest('hex');
const canonical = value => JSON.stringify(value); // Only flat arrays used below.
const digest = value => createHash('sha256').update(canonical(value)).digest('hex');
const candidatePath = 'predict/research/phase57-msh-entry-long-v1-validation-candidate-v1.json';
const scopePath = 'predict/research/phase57-msh-entry-long-v1-final-model-scope-v1.json';
const c = read(candidatePath), s = read(scopePath);
const m = read(c.modelArtifactPath), scaler = read(c.scalerArtifactPath);
const a = read(evidence + 'construction-audit.json');

function safety(candidate) {
  for (const key of ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed',
    'rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed',
    'automaticPromotionAllowed','productionUpdateAllowed','transmitted',
    'shortAllowed','marginAllowed','leverageAllowed']) assert.equal(candidate.safety[key], false, key);
}

function governance(candidate) {
  assert.equal(candidate.status, 'VALIDATION_CANDIDATE');
  assert.equal(candidate.adopted, false);
  assert.equal(candidate.production, false);
  assert.equal(candidate.decision.threshold, 2);
  assert.deepEqual(candidate.decision.validationThresholdSet, [2]);
  assert.equal(candidate.validationGovernance.accessAuthorizedByThisTask, false);
  assert.deepEqual(candidate.validationGovernance.numericHardPassGates, []);
  assert.equal(candidate.protection.validationSealed, true);
  assert.equal(candidate.protection.oosSealed, true);
  assert.equal(candidate.state.secondEntryInSameSymbolSessionAllowed, false);
  assert.equal(candidate.state.waitStateAllowed, false);
  safety(candidate);
}

test('candidate, scope and every protected artifact match exact SHA', () => {
  assert.equal(hash(candidatePath), '4a2f52cd6f25f480fe6d7de9db525860ddf3c1600abed06b6222c0990c055a23');
  assert.equal(hash(scopePath), 'e18208a42ac034fde1f746c2f51146660f76080b33abaafe940ac6e85067686b');
  for (const [name, expected] of Object.entries(c.sourcePins)) assert.equal(hash(name), expected, name);
  assert.equal(hash('scripts/construct_phase57_final_validation_model.py'), s.constructionScriptSha256);
  assert.equal(read(evidence+'artifact-manifest.json').candidateContractSha256, hash(candidatePath));
});

test('training identity binds all76 exact sessions and1828 labelable rows', () => {
  assert.deepEqual(c.trainingIdentity, s.trainingIdentity);
  assert.deepEqual(a.trainingIdentity, s.trainingIdentity);
  const i = s.trainingIdentity;
  assert.equal(i.sessionCount, 76);
  assert.equal(i.selectionEventCount, 3800);
  assert.equal(i.labelableCount, 1828);
  assert.equal(i.unlabelableCount, 1972);
  assert.deepEqual(i.classCounts, [606,423,271,281,247]);
  assert.equal(new Set(i.trainingSessions).size,76);
  assert.deepEqual([...i.trainingSessions].sort(),i.trainingSessions);
  assert.equal(digest(i.trainingSessions),i.sessionListSha256);
});

test('exact frozen core and final scaler are paired, finite, ddof0, positive', () => {
  assert.deepEqual(m.featureOrder, ['frozenSelectorRidgeScore','frozenSelectorRidgeRank']);
  assert.equal(digest(m.featureOrder),s.trainingIdentity.featureOrderSha256);
  assert.deepEqual(c.features.optionalFeatures, []);
  assert.equal(c.features.decisionPriceRole, 'REFERENCE_ONLY');
  assert.deepEqual(m.scaler.mean,scaler.mean);
  assert.deepEqual(m.scaler.std,scaler.std);
  assert.equal(scaler.ddof,0);
  assert.ok(scaler.mean.every(Number.isFinite));
  assert.ok(scaler.std.every(x=>Number.isFinite(x)&&x>0));
  assert.equal(scaler.trainingEventIdsSha256,s.trainingIdentity.trainingEventIdsSha256);
});

test('final artifact is one valid frozen proportional-odds model', () => {
  assert.equal(c.singleFinalModel,true);
  assert.equal(c.foldReuseAllowed,false);
  assert.equal(c.ensembleAllowed,false);
  assert.equal(m.link,'LOGIT');
  assert.deepEqual(m.classes,[0,1,2,3,4]);
  assert.equal(m.beta.length,2);
  assert.ok(m.beta.every(Number.isFinite));
  assert.equal(m.cutpoints.length,4);
  assert.ok(m.cutpoints.every((x,i)=>Number.isFinite(x)&&(i===0||x>m.cutpoints[i-1])));
  assert.equal(m.regularization.lambda,1);
  assert.equal(m.regularization.cutpointsPenalized,false);
  assert.equal(m.regularization.objective,'SUM_NLL+lambda/2*||beta||^2');
  assert.equal(m.solver.method,'L-BFGS-B');
  assert.equal(m.solver.maxiter,2000);
  assert.equal(m.solver.ftol,1e-12);
  assert.equal(m.solver.gtol,1e-8);
  assert.equal(m.solver.success,true);
  assert.equal(m.solver.status,0);
  assert.ok(Number.isFinite(m.solver.objective));
  safety(m);
});

test('audit proves one construction and authorized repeat, no performance or sealed data access', () => {
  assert.equal(a.status,'PASS');
  assert.equal(a.constructionFitCalls,1);
  assert.equal(a.determinismFitCalls,1);
  assert.equal(a.constructionScalerFits,1);
  assert.equal(a.verificationScalerRecomputations,1);
  for (const k of ['developmentPerformanceEvaluations','oofRegeneration','thresholdPerformanceSearch',
    'validationAccess','oosAccess','exitAccess','shortEvaluation','externalProjectPredictions']) assert.equal(a[k],0,k);
  assert.deepEqual(a.performanceMetricsCreated,[]);
  assert.ok(Object.values(a.providerRequests).every(x=>x===0));
  assert.equal(a.determinism,'EXACT_ARTIFACT_AND_PROBE_EQUALITY');
  assert.equal(a.serialization,'EXACT_SYNTHETIC_PROBE_PROBABILITY_EQUALITY');
  assert.equal(read(evidence+'network-guard-audit.json').blockedUnexpectedNetworkAttempts,0);
});

test('candidate2 remains a prospective hypothesis, not scalar winner or adoption', () => {
  governance(c);
  assert.equal(c.candidateSelection.notFrozenScalarWinner,true);
  assert.equal(c.candidateSelection.frozenScalarWinnerRemains,1);
  assert.equal(c.developmentEvidenceVerdict,'MSH_ENTRY_LONG_V1_DEVELOPMENT_BORDERLINE');
  assert.equal(c.validationGovernance.failureResult,'MSH_ENTRY_LONG_V1_VALIDATION_FAIL');
  assert.ok(c.validationGovernance.failAction.includes('NO_1_OR_3_FALLBACK'));
});

test('mutations to threshold, safety or sealed access fail contract checks', () => {
  for (const mutate of [x=>x.decision.threshold=1, x=>x.decision.validationThresholdSet=[1,2,3],
    x=>x.safety.executionAllowed=true, x=>delete x.safety.transmitted,
    x=>x.protection.oosSealed=false, x=>x.validationGovernance.accessAuthorizedByThisTask=true]) {
    const changed=structuredClone(c);mutate(changed);assert.throws(()=>governance(changed));
  }
});

test('label/cadence/state remain distinct from future labelability and execution', () => {
  assert.equal(c.label.primary.completeContinuousFiveMinutePathRequired,true);
  assert.equal(c.label.unlabelable.negativeClassSubstitutionAllowed,false);
  assert.equal(c.label.supportingDiagnostic.mixedIntoPrimaryLabel,false);
  assert.equal(c.cadence.developmentDecisionsPerSession,10);
  assert.equal(c.cadence.decisionTimesJst.length,10);
  assert.equal(c.cadence.fiveMinuteSelectorReconstructionAllowed,false);
  assert.match(c.evaluationSemantics.decisionPopulation,/never gate action using future label availability/);
  assert.equal(c.evaluationSemantics.paperOrLiveTrading,false);
  assert.deepEqual(c.state.outputs,['ENTER','SKIP_THIS_DECISION']);
});
