import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here=path.dirname(fileURLToPath(import.meta.url));
const root=path.resolve(here,'../..');
const audit=JSON.parse(fs.readFileSync(path.join(root,'predict/research/phase57-msh-entry-long-v1-fit-contract-freeze-audit-v1.json'),'utf8'));

test('fit contract stays blocked instead of silently changing ordinal model semantics',()=>{
  assert.equal(audit.freezeDecision,'MSH_ENTRY_LONG_V1_FIT_CONTRACT_BLOCKED');
  assert.equal(audit.freezeEffective,false);
  assert.equal(audit.blocker.code,'ORDINAL_IMPLEMENTATION_BLOCKED');
  assert.equal(audit.candidateContract.model.family,'PROPORTIONAL_ODDS_ORDINAL_LOGISTIC_REGRESSION');
  assert.equal(audit.candidateContract.model.implementationSource,null);
  assert.equal(audit.candidateContract.model.binaryDecompositionAllowed,false);
  assert.equal(audit.candidateContract.model.multinomialSubstitutionAllowed,false);
});

test('repo manifests do not currently pin an ordinal implementation',()=>{
  const predictPackage=JSON.parse(fs.readFileSync(path.join(root,'predict/package.json'),'utf8'));
  const requirements=fs.readFileSync(path.join(root,'tools/requirements-rss.txt'),'utf8').toLowerCase();
  const workflowText=fs.readdirSync(path.join(root,'.github/workflows'))
    .filter(name=>name.endsWith('.yml')||name.endsWith('.yaml'))
    .map(name=>fs.readFileSync(path.join(root,'.github/workflows',name),'utf8'))
    .join('\n').toLowerCase();
  const declared=JSON.stringify({...predictPackage.dependencies,...predictPackage.devDependencies}).toLowerCase();
  for(const packageName of ['statsmodels','mord']){
    assert.equal(declared.includes(packageName),false);
    assert.equal(requirements.includes(packageName),false);
    assert.equal(workflowText.includes(packageName),false);
  }
});

test('candidate decisions are result-independent but remain non-effective',()=>{
  const c=audit.candidateContract;
  assert.equal(c.effective,false);
  assert.equal(c.features.selectedPolicy,'OPTION_A_SELECTOR_SCORE_AND_RANK_ONLY');
  assert.deepEqual(c.features.mandatoryCore,['frozenSelectorRidgeScore','frozenSelectorRidgeRank']);
  assert.equal(c.features.mandatoryCoreAvailabilityPct,100);
  assert.deepEqual(c.thresholdCandidates.values,[1,2,3]);
  assert.equal(c.thresholdCandidates.count,3);
  assert.equal(c.decisionScore.formula,'E[L] = 0*P0 + 1*P1 + 2*P2 + 3*P3 + 4*P4');
  assert.deepEqual(c.decisionScore.range,[0,4]);
  assert.equal(c.classWeight.policy,'UNWEIGHTED');
  assert.deepEqual(c.classWeight.weightsByClass,[1,1,1,1,1]);
  assert.equal(c.crossValidation.evaluationFoldCount,4);
});

test('blocked audit performs no training and keeps all safety switches false',()=>{
  for(const value of Object.values(audit.methodology)) assert.equal(value,0);
  for(const value of Object.values(audit.safety)) assert.equal(value,false);
  assert.equal(audit.sourceIntegrity.frozenSelectorPayloadSha256,'3dc6d222d4039737c0dcfdcfa4a83372202152e29b582225419ab97c00610d59');
  assert.equal(audit.sourceIntegrity.feasibilityReportSha256,'f7cb8d98891b4a764454939677e03ecc7117fd7cb81d112583e5b8dca6c149df');
  assert.equal(audit.contractReview.ordinalImplementationSourcePinned,false);
  assert.equal(audit.contractReview.l2AndSolverSemanticsFrozen,false);
  assert.deepEqual(audit.contractReview.internalContradictions,[]);
});
