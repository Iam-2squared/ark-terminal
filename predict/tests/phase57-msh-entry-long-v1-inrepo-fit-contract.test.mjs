import test from 'node:test';
import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here=path.dirname(fileURLToPath(import.meta.url));
const root=path.resolve(here,'../..');
const contractPath=path.join(root,'predict/research/phase57-msh-entry-long-v1-fit-contract-v1.json');
const contract=JSON.parse(fs.readFileSync(contractPath,'utf8'));
const audit=JSON.parse(fs.readFileSync(path.join(root,'predict/research/phase57-msh-entry-long-v1-inrepo-implementation-audit-v1.json'),'utf8'));
const selector=JSON.parse(fs.readFileSync(path.join(root,'predict/research/phase57-long-only-frozen-selector-v1.json'),'utf8'));
const sha256=relativePath=>crypto.createHash('sha256').update(fs.readFileSync(path.join(root,relativePath))).digest('hex');

test('reviewed in-repository fit contract is frozen without changing selector integrity',()=>{
  assert.equal(contract.freezeDecision,'MSH_ENTRY_LONG_V1_FIT_CONTRACT_FROZEN');
  assert.equal(contract.status,'FROZEN_PRE_TRAINING');
  assert.equal(selector.hashes.freezePayloadSha256,contract.sourceIntegrity.frozenSelectorPayloadSha256);
  assert.equal(selector.hashes.savedModelArtifactSha256,contract.sourceIntegrity.frozenSelectorRidgeArtifactSha256);
  assert.equal(sha256(contract.sourceIntegrity.implementationPath),contract.sourceIntegrity.implementationSha256);
  assert.equal(sha256(contract.sourceIntegrity.syntheticTestPath),contract.sourceIntegrity.syntheticTestSha256);
});

test('model mathematics and slope-only L2 contract are exact',()=>{
  const architecture=contract.architecture;
  const mathematics=contract.mathematics;
  assert.equal(architecture.modelFamily,'IN_REPOSITORY_PROPORTIONAL_ODDS_ORDINAL_LOGISTIC_REGRESSION');
  assert.equal(architecture.link,'LOGIT');
  assert.deepEqual(architecture.orderedClasses,[0,1,2,3,4]);
  assert.equal(architecture.cutpointCount,4);
  assert.equal(mathematics.sharedSlopeAcrossCutpoints,true);
  assert.equal(mathematics.cutpointParameterization.orderingGuaranteedDuringOptimization,true);
  assert.equal(mathematics.cutpointParameterization.postFitSortingAllowed,false);
  assert.equal(mathematics.objective.dataLoss,'SUM_NEGATIVE_LOG_LIKELIHOOD');
  assert.equal(mathematics.objective.l2Target,'SLOPE_BETA_ONLY');
  assert.equal(mathematics.objective.cutpointsPenalized,false);
  assert.equal(mathematics.objective.lambda,1);
  assert.equal(mathematics.objective.classWeight,'UNWEIGHTED');
});

test('solver, standardization and convergence are fail-closed',()=>{
  assert.equal(contract.fit.solver.library,'scipy.optimize.minimize');
  assert.equal(contract.fit.solver.method,'L-BFGS-B');
  assert.equal(contract.fit.solver.maxiter,2000);
  assert.equal(contract.fit.solver.ftol,1e-12);
  assert.equal(contract.fit.solver.gtol,1e-8);
  assert.equal(contract.fit.failureResult,'FIT_FAILED_NO_ARTIFACT_PROMOTION');
  assert.ok(contract.fit.failClosedGate.includes('OPTIMIZER_SUCCESS_TRUE'));
  assert.equal(contract.standardization.fitScope,'CURRENT_TRAINING_PREFIX_ONLY');
  assert.equal(contract.standardization.evaluationDataIncludedInFit,false);
  assert.equal(contract.standardization.zeroStdPolicy,'FIT_FAILED');
  assert.equal(contract.standardization.implicitImputationAllowed,false);
});

test('features labels CV decision score thresholds and state remain predeclared',()=>{
  assert.deepEqual(contract.features.mandatoryCore,['frozenSelectorRidgeScore','frozenSelectorRidgeRank']);
  assert.deepEqual(contract.features.optionalFeatures,[]);
  assert.equal(contract.features.decisionPriceRole,'REFERENCE_ONLY');
  assert.equal(contract.label.primary.labelableRows,1828);
  assert.equal(contract.label.primary.candidateRows,3800);
  assert.equal(contract.label.unlabelable.negativeClassSubstitutionAllowed,false);
  assert.equal(contract.label.supportingDiagnostic.mixedIntoPrimaryLabel,false);
  assert.equal(contract.crossValidation.type,'SESSION_GROUPED_EXPANDING_WINDOW_CHRONOLOGICAL');
  assert.equal(contract.crossValidation.evaluationFoldCount,4);
  assert.equal(contract.crossValidation.randomSplitAllowed,false);
  assert.equal(contract.decision.score.formula,'E[L]=0*P0+1*P1+2*P2+3*P3+4*P4');
  assert.deepEqual(contract.decision.thresholdCandidates.values,[1,2,3]);
  assert.deepEqual(contract.state.outputs,['ENTER','SKIP_THIS_DECISION']);
  assert.equal(contract.state.waitStateAllowed,false);
  assert.equal(contract.state.expiryStateAllowed,false);
});

test('no external ordinal dependency or unsafe path entered the frozen contract',()=>{
  assert.equal(contract.runtime.newExternalOrdinalDependency,null);
  assert.equal(contract.dataProtection.projectDataFitPerformedByFreezeAudit,false);
  assert.equal(contract.dataProtection.projectPredictionsGeneratedByFreezeAudit,0);
  assert.equal(contract.dataProtection.validationSealed,true);
  assert.equal(contract.dataProtection.oosSealed,true);
  for(const value of Object.values(contract.safety)) assert.equal(value,false);
  const requirements=fs.readFileSync(path.join(root,'tools/requirements-rss.txt'),'utf8').toLowerCase();
  const workflows=fs.readdirSync(path.join(root,'.github/workflows'))
    .filter(name=>name.endsWith('.yml')||name.endsWith('.yaml'))
    .map(name=>fs.readFileSync(path.join(root,'.github/workflows',name),'utf8'))
    .join('\n').toLowerCase();
  for(const packageName of ['statsmodels','mord']){
    assert.equal(requirements.includes(packageName),false);
    assert.equal(workflows.includes(packageName),false);
  }
});

test('freeze audit binds the final contract and records zero project-data work',()=>{
  assert.equal(audit.freezeDecision,'MSH_ENTRY_LONG_V1_FIT_CONTRACT_FROZEN');
  assert.equal(audit.freezeEffective,true);
  assert.equal(sha256('predict/research/phase57-msh-entry-long-v1-fit-contract-v1.json'),audit.finalContract.sha256);
  assert.equal(audit.syntheticAudit.overall,'PASS');
  assert.equal(audit.statsmodelsCrossCheck.result,'PASS_EQUIVALENT_PROPORTIONAL_ODDS_PARAMETERIZATION');
  assert.ok(audit.syntheticTestGates.every(gate=>gate.result==='PASS'));
  for(const value of Object.values(audit.methodology)) assert.equal(value,0);
  for(const value of Object.values(audit.safety)) assert.equal(value,false);
});
