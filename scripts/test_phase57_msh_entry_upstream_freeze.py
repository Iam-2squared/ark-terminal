"""Entry-only artifact integrity. No model import, prediction, path or EXIT access."""
import copy
import gzip
import hashlib
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'docs/evidence/phase57-msh-entry-long-v1-upstream-freeze'
PRIOR = ROOT / 'docs/evidence/phase57-msh-entry-long-v1-historical-remeasurement'
SHA = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
READ = lambda p: json.loads(p.read_text())
SAFETY = ['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted']


def validate(m):
    required = ['status','freezeDate','repo','branch','PR','selectorFreezeCommit','selectorPayloadSHA','selectorRidgeSHA','candidateContractSHA','finalModelSHA','finalScalerSHA','threshold','decisionScore','features','optionalFeatures','state','direction','cashEquityOnly','historicalDatasetPeriod','historicalSessions','historicalExposureStatus','historicalVerdict','freshValidationStatus','selectorPrecision','candidatePrecision','candidateEnterCount','candidateEnterPerSession','oldCurrentEntryEnterCount','oldCurrentEntryEnterPerSession','opportunityPreservation','strict30mMAE','knownLimitations','downstreamPurpose','entryModificationPolicy','safety']
    assert all(k in m for k in required)
    assert m['status'] == 'MSH_ENTRY_LONG_V1_FROZEN_FOR_EXIT_RESEARCH'
    assert m['threshold'] == 2.0
    assert m['decisionScore'] == 'P1 + 2P2 + 3P3 + 4P4'
    assert m['features'] == ['frozenSelectorRidgeScore','frozenSelectorRidgeRank']
    assert m['optionalFeatures'] == [] and m['decisionPrice'] == 'REFERENCE_ONLY'
    assert m['state'] == ['ENTER','SKIP_THIS_DECISION']
    assert m['wait'] is None and m['expiry'] is None
    assert m['persistentSkip'] is False and m['reentryAfterEnterAllowed'] is False
    assert m['direction'] == 'LONG' and m['cashEquityOnly'] is True
    assert all(m[k] is False for k in ['shortAllowed','marginAllowed','leverageAllowed','officialValidationPass','prospectivePass'])
    assert m['historicalVerdict'] == 'BORDERLINE' and m['freshValidationStatus'] == 'PENDING' and m['oosStatus'] == 'PENDING_SEALED'
    assert m['historicalSessions'] == 76 and m['candidateEnterCount'] == 277
    assert m['entryModificationPolicy']['allowed'] is False
    assert set(m['safety']) == set(SAFETY) and all(m['safety'][k] is False for k in SAFETY)


class FreezeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = READ(BASE / 'manifest.json')

    def test_schema_and_frozen_semantics(self):
        validate(self.m)
        candidate = READ(ROOT / 'predict/research/phase57-msh-entry-long-v1-validation-candidate-v1.json')
        self.assertEqual(candidate['decision']['threshold'], self.m['threshold'])
        self.assertEqual(candidate['decision']['validationThresholdSet'], [2.0])
        self.assertEqual(candidate['features']['mandatoryCore'], self.m['features'])
        self.assertEqual(candidate['features']['optionalFeatures'], [])
        self.assertEqual(candidate['cadence']['decisionTimesJst'], self.m['cadenceJst'])

    def test_sha_pins_and_manifest_digest(self):
        for path, expected in self.m['evidencePins'].items():
            self.assertEqual(SHA(ROOT / path), expected, path)
        self.assertEqual(SHA(BASE / 'manifest.json'), (BASE / 'manifest.sha256').read_text().split()[0])
        self.assertEqual(SHA(BASE / 'scope-transition.json'), self.m['scopeTransitionSHA'])
        mapping = {'candidateContractSHA':'predict/research/phase57-msh-entry-long-v1-validation-candidate-v1.json','finalModelSHA':'docs/evidence/phase57-msh-entry-long-v1-final-validation-model/final-model.json','finalScalerSHA':'docs/evidence/phase57-msh-entry-long-v1-final-validation-model/final-scaler.json','globalBudgetSHA':'predict/research/phase57-long-only-global-data-budget-v1.json'}
        for field, path in mapping.items():
            self.assertEqual(self.m[field], SHA(ROOT / path))

    def test_selector_identity(self):
        selector = READ(ROOT / 'predict/research/phase57-long-only-frozen-selector-v1.json')
        payload = selector['freezePayload']
        canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(',',':')).encode()
        self.assertEqual(hashlib.sha256(canonical).hexdigest(), self.m['selectorPayloadSHA'])
        self.assertEqual(self.m['selectorRidgeSHA'], '994f1dbaba1d32e97458d5dd9d4c646ef443fbb37128650e8166001d8deabefb')

    def test_saved_277_identity_not_regenerated(self):
        ledger = self.m['historicalEnterLedger']
        self.assertEqual(SHA(ROOT / ledger['path']), ledger['sha256'])
        entries = READ(ROOT / ledger['path'])
        self.assertEqual(len(entries), 277)
        self.assertEqual(len({e['symbolSessionId'] for e in entries}), 277)
        saved = [json.loads(line) for line in gzip.open(PRIOR/'frozen-predictions.ndjson.gz','rt')]
        self.assertEqual([e['selectorEventId'] for e in entries], [e['selectorEventId'] for e in saved if e['state']=='ENTER'])
        source = {e['selectorEventId']:e for e in map(json.loads,gzip.open(ROOT/'docs/evidence/phase57-msh-entry-long-v1-preimplementation-feasibility-events.ndjson.gz','rt'))}
        for e in entries:
            self.assertEqual(e, {k:source[e['selectorEventId']][k] for k in ledger['fields']})
            self.assertEqual(source[e['selectorEventId']]['direction'], 'LONG')

    def test_historical_reference_exact_no_remeasurement(self):
        m = READ(PRIOR/'measurement.json')
        self.assertEqual(self.m['candidatePrecision'],m['candidateActualEntry']['high'])
        self.assertEqual(self.m['selectorPrecision'],m['selectorFirstOpportunity']['high'])
        self.assertEqual(self.m['opportunityPreservation'],m['preservation'])
        self.assertEqual(self.m['strict30mMAE'],m['candidateActualEntry']['trueMaePct'])
        self.assertEqual(self.m['candidateEnterPerSession'],m['enterPerSession'])
        self.assertEqual(self.m['precisionDenominators'],{'selector':1303,'candidate':181})
        self.assertEqual(READ(PRIOR/'assessment.json')['verdict'],self.m['historicalVerdictCode'])

    def test_scope_disclosure_and_no_new_access(self):
        x=READ(BASE/'scope-transition.json')
        self.assertTrue(x['priorWorkDisclosure']['exitSourceInspectionPerformed'])
        self.assertEqual(x['priorWorkDisclosure']['historicalDiagnosticAndReplayJobStarted'],1)
        self.assertFalse(x['priorWorkDisclosure']['resultOpened'])
        self.assertFalse(x['priorWorkDisclosure']['resultUsedForFreeze'])
        self.assertTrue(all(v == 0 for v in x['newFreezeScope'].values()))
        self.assertEqual(self.m['freshBudgetConsumed'],0)
        self.assertEqual(self.m['globalFreshBudgetRemaining'],195)

    def test_forbidden_mutations_rejected(self):
        mutations=[('threshold',1.0),('threshold',3.0),('features',['frozenSelectorRidgeScore']),('optionalFeatures',['Momentum3']),('direction','SHORT'),('freshValidationStatus','PASS'),('officialValidationPass',True),('wait','WAIT'),('reentryAfterEnterAllowed',True)]
        for k,v in mutations:
            bad=copy.deepcopy(self.m);bad[k]=v
            with self.assertRaises(AssertionError,msg=k):validate(bad)
        bad=copy.deepcopy(self.m);bad['safety']['executionAllowed']=True
        with self.assertRaises(AssertionError):validate(bad)


if __name__=='__main__':
    unittest.main(verbosity=2)
