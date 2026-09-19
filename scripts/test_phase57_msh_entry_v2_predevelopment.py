"""Contract-only regression tests: no fitting, prediction, OOF or performance replay."""
import ast
import copy
from pathlib import Path
import tempfile
import unittest

from scripts import audit_phase57_msh_entry_v2_predevelopment as a


class PredevelopmentContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c = a.read(a.ROOT / a.CONTRACT)

    def reject(self, path, value):
        bad = copy.deepcopy(self.c)
        node = bad
        for key in path[:-1]:
            node = node[key]
        node[path[-1]] = value
        with self.assertRaises((ValueError, KeyError), msg='.'.join(map(str,path))):
            a.validate_contract(bad)

    def test_frozen_contract_source_pins_and_metadata_only_audit(self):
        receipt, plan = a.audit()
        self.assertEqual(receipt['contractSHA'], a.FROZEN_SHA)
        self.assertTrue(receipt['frozenSelectorEntryExitAllocationLedgerUnchanged'])
        self.assertEqual(sum(g['candidateEvents'] for g in plan['groups']), 3800)
        self.assertFalse(receipt['modelRuntimeImported'])
        self.assertEqual(sum(receipt['counters'].values()), 0)
        evidence = a.ROOT/a.EVIDENCE
        self.assertEqual(receipt,a.read(evidence/'static-audit.json'))
        self.assertEqual(plan,a.read(evidence/'split-metadata.json'))
        self.assertEqual(a.sha(evidence/'manifest.json'),(evidence/'manifest.sha256').read_text().strip())
        for path,expected in a.read(evidence/'manifest.json')['artifactPins'].items():
            self.assertEqual(a.sha(a.ROOT/path),expected,path)

    def test_future_symbol_rawprice_and_extra_predictors_rejected(self):
        for forbidden in ['futureMAE','futureMFE','exitPnl','symbol','decisionPrice']:
            self.reject(['features','order'], [forbidden]+a.ORDER[1:])
        self.reject(['features','activeOptionalFeatures'], ['relativeVolume5'])
        self.reject(['features','featureInteractions'], True)

    def test_missing_semantics_cannot_be_silently_relaxed(self):
        for key in ['missingIsZero','forwardFill','futureFill','nextObservationFill',
                    'interpolation','outcomeDerivedImputation','volumeMissingAsZero']:
            self.reject(['missing',key], True)

    def test_training_universe_not_277_or_181_and_no_live_claim(self):
        for n in [277,181,173]:
            self.reject(['universe','candidateCount'], n)
        self.reject(['universe','trainingNotRestrictedToV1Enter'], False)
        self.reject(['universe','fullLiveUniversePITClaim'], True)
        self.reject(['fairComparator','primaryOwnAcceptedSets'], False)

    def test_continuous_target_not_ten_tail_binary(self):
        self.reject(['target','binaryTailTarget'], True)
        self.reject(['target','horizonMinutes'], 60)
        self.reject(['target','clipping'], True)
        self.reject(['target','missingExpectedBar'], 'FORWARD_FILL')

    def test_chronology_inner_selection_and_session_boundaries(self):
        self.reject(['cv','folds',0,'innerFitOrdinals'], [1,16])
        self.reject(['cv','folds',0,'evaluationOrdinals'], [16,31])
        self.reject(['cv','folds',0,'trainDates'], self.c['universe']['sessions'][:17])
        self.reject(['cv','fitStatisticsFromEvaluation'], True)
        self.reject(['trainingRows','sameSymbolSessionAcrossTrainEval'], True)
        self.reject(['cv','randomSplit'], True)

    def test_symbol_plan_independent_of_features_and_all_outcomes(self):
        dates = self.c['universe']['sessions']
        symbols = ['10000','20000','30000','40000','50000','60000','70000','80000','90000','12340']
        # Add deterministic synthetic IDs until all five buckets occur, without outcomes.
        symbols += [str(10001+i) for i in range(60)]
        rows = [{'selectorEventId':d+'|'+s, 'symbol':s, 'sessionDate':d,
                 'decisionTimestamp':d+'T09:30:00+09:00', 'label':{'futureMAE':-90},
                 'features':{'score':999}} for d in dates for s in symbols]
        before = a.split_metadata(rows,self.c)
        for row in rows:
            row['label'] = {'futureMAE':10000,'futureExitPnl':999999}
            row['features'] = {'score':-999}
        self.assertEqual(before,a.split_metadata(rows,self.c))
        self.assertEqual(sum(g['candidateEvents'] for g in before['groups']),len(rows))
        self.assertEqual([f['heldSymbolLeakCount'] for f in before['chronologicalFolds']],[0]*4)

    def test_targeted_symbol_splits_and_weights_forbidden(self):
        self.reject(['crossSymbol','postHocRebalancing'], True)
        self.reject(['crossSymbol','heldGroupOutcomesUsedForThreshold'], True)
        self.reject(['trainingRows','symbolSpecificOverrides'], True)
        self.reject(['architecture','symbolModel'], True)

    def test_one_model_regularization_solver_and_state_frozen(self):
        self.reject(['model','family'], 'XGBOOST')
        self.reject(['model','lambda'], .1)
        self.reject(['model','solver'], 'GRID_SEARCH')
        self.reject(['architecture','primaryModelCount'], 2)
        self.reject(['state','outputs'], ['ENTER','WAIT','SKIP_THIS_DECISION'])
        self.reject(['architecture','v1ScoreGateInsideV2'], True)

    def test_threshold_grid_gate_and_sizing_mutations_rejected(self):
        self.reject(['decision','thresholdCandidatesPct'], [1.,2.,3.,5.,10.])
        self.reject(['decision','positionSizingUsesScore'], True)
        self.reject(['numericGates','primary','adverseMeanRatioMax'], 1.)
        self.reject(['numericGates','guardrails','portfolioMaxDrawdownRatioMax'], 2.)

    def test_equal_cash_cost_and_downstream_fixed(self):
        for key,value in [('exit','FIXED12'),('allocation','LONG_RANK_MAX3'),
                          ('lotSize',1),('initialCashJpy',2000000),
                          ('roundTripCostPctOfEntryNotional',0),('maximumConcurrentPositions',3)]:
            self.reject(['fairComparator',key],value)

    def test_training_access_and_all_nine_safety_flags_blocked(self):
        for flag in a.SAFETY:
            self.reject(['safety',flag],True)
        for key in self.c['currentScopeCounters']:
            self.reject(['currentScopeCounters',key],1)
        self.reject(['dataProtection','trainingAuthorizedByThisContractFreeze'],True)
        self.reject(['dataProtection','newProviderRequestsAllowed'],True)
        self.reject(['repository','mainMergeAllowed'],True)

    def test_contract_byte_mutation_fails_even_if_sidecar_rehashed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            dest = root/a.CONTRACT
            dest.parent.mkdir(parents=True)
            dest.write_bytes((a.ROOT/a.CONTRACT).read_bytes()+b' ')
            (root/(a.CONTRACT+'.sha256')).write_text(a.sha(dest)+'\n')
            with self.assertRaisesRegex(ValueError,'CONTRACT_HASH'):
                a.audit(root)

    def test_auditor_imports_only_static_standard_library(self):
        tree = ast.parse(Path(a.__file__).read_text())
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node,ast.Import):
                imported.update(x.name.split('.')[0] for x in node.names)
            elif isinstance(node,ast.ImportFrom):
                imported.add(node.module.split('.')[0])
        self.assertLessEqual(imported,{'argparse','collections','gzip','hashlib','json','pathlib'})


if __name__ == '__main__':
    unittest.main(verbosity=2)
