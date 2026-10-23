import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here=path.dirname(fileURLToPath(import.meta.url));
const root=path.resolve(here,'../..');
const audit=JSON.parse(fs.readFileSync(path.join(root,'predict/research/phase57-msh-entry-long-v1-ordinal-dependency-resolution-audit-v1.json'),'utf8'));

test('dependency resolution remains fail-closed when no candidate satisfies every criterion',()=>{
  assert.equal(audit.freezeDecision,'MSH_ENTRY_LONG_V1_FIT_CONTRACT_BLOCKED');
  assert.equal(audit.freezeEffective,false);
  assert.equal(audit.primaryBlocker,'NO_ACCEPTABLE_ORDINAL_DEPENDENCY');
  assert.equal(audit.selectedDependency,null);
  assert.equal(audit.repoDependencyPin.changed,false);
  assert.equal(audit.finalContract.issued,false);
  assert.equal(audit.finalContract.sha256,null);
});

test('candidate failures do not silently change model semantics',()=>{
  const byName=Object.fromEntries(audit.dependencyCandidates.map(candidate=>[candidate.package,candidate]));
  assert.equal(byName.statsmodels.proportionalOdds,true);
  assert.equal(byName.statsmodels.nativeSlopeOnlyL2,false);
  assert.equal(byName.mord.nativeSlopeOnlyL2,true);
  assert.equal(byName.mord.cutpointsUnpenalized,true);
  assert.equal(byName.mord.exactOrderedCategoricalLikelihood,false);
  assert.equal(byName.mord.convergenceStatusExposed,false);
  assert.equal(byName['scikit-learn'].proportionalOdds,false);
  assert.equal(byName['scikit-learn'].modelFamily,'BINARY_OR_MULTINOMIAL_LOGISTIC');
  assert.ok(audit.blockerDetails.some(item=>item.includes('model semantics are not relaxed')));
});

test('synthetic audit records the candidate convergence failure without project data',()=>{
  const s=audit.syntheticAudit;
  assert.equal(s.projectDataUsed,false);
  assert.equal(s.candidate,'mord==0.7');
  assert.equal(s.featureCount,2);
  assert.deepEqual(s.classes,[0,1,2,3,4]);
  assert.equal(s.fitFinite,true);
  assert.equal(s.orderedCutpoints,true);
  assert.equal(s.probabilityColumns,5);
  assert.equal(s.probabilityFinite,true);
  assert.equal(s.probabilityNonnegative,true);
  assert.ok(s.maxProbabilityRowSumError<1e-12);
  assert.equal(s.deterministicCoefficientExact,true);
  assert.equal(s.deterministicCutpointExact,true);
  assert.equal(s.deterministicProbabilityExact,true);
  assert.equal(s.serializationPredictionExact,true);
  assert.equal(s.maxIterZeroFitReturnedNormally,true);
  assert.deepEqual(s.convergenceAttributesPresent,[]);
  assert.equal(s.overall,'FAIL_CONVERGENCE_CONTRACT');
});

test('predeclared fit and decision contract remains unchanged and non-effective',()=>{
  const c=audit.unchangedCandidateContract;
  assert.deepEqual(c.mandatoryCore,['frozenSelectorRidgeScore','frozenSelectorRidgeRank']);
  assert.deepEqual(c.optionalFeatures,[]);
  assert.equal(c.decisionPriceRole,'REFERENCE_ONLY');
  assert.equal(c.model,'ONE_PROPORTIONAL_ODDS_ORDINAL_LOGISTIC_LOGIT_MODEL');
  assert.equal(c.classWeight,'UNWEIGHTED');
  assert.equal(c.decisionScore,'E[L]=0*P0+1*P1+2*P2+3*P3+4*P4');
  assert.deepEqual(c.decisionScoreRange,[0,4]);
  assert.deepEqual(c.thresholdCandidates,[1,2,3]);
  assert.deepEqual(c.state,['ENTER','SKIP_THIS_DECISION']);
});

test('project data, sealed partitions and all unsafe paths remain untouched',()=>{
  for(const value of Object.values(audit.methodology)) assert.equal(value,0);
  for(const value of Object.values(audit.safety)) assert.equal(value,false);
  assert.equal(audit.sourceIntegrity.frozenSelectorPayloadSha256,'3dc6d222d4039737c0dcfdcfa4a83372202152e29b582225419ab97c00610d59');
  assert.equal(audit.sourceIntegrity.frozenSelectorRidgeArtifactSha256,'994f1dbaba1d32e97458d5dd9d4c646ef443fbb37128650e8166001d8deabefb');
});

test('no rejected ordinal candidate is pinned into repository dependency locations',()=>{
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
