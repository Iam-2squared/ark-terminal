"""Outcome-free integrity/contamination regression, no market or model inputs."""
import copy
import hashlib
import json
from pathlib import Path
import unittest

from phase57_budget_metadata import derive, compare_previous, project_identity, validate_input
from replay_phase57_budget_without_outcomes import replay

ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / 'docs/evidence/phase57-long-only-global-budget-integrity-review'
PRIOR = ROOT / 'docs/evidence/phase57-long-only-e2e-data-responsibility'


class BudgetMetadataTests(unittest.TestCase):
    def setUp(self):
        self.fixture = json.loads((REVIEW / 'outcome-free-input.json').read_text())
        self.previous = json.loads((PRIOR / 'responsibility-budget-contract.json').read_text())

    def test_independent_derivation_matches_all_previous_numbers(self):
        self.assertTrue(compare_previous(derive(self.fixture), self.previous))

    def test_fresh_sum_has_seven_disjoint_blocks(self):
        result = derive(self.fixture)
        self.assertEqual(sum(result['blockSessions'][b] for b in 'ABCDEFG'), 195)
        self.assertEqual(result['blockSessions']['DEV'], 76)

    def test_gross_and_shared_deductions(self):
        result = derive(self.fixture)
        self.assertEqual(result['grossSessions'] - 2*76 - 2*20, result['netUniqueSessions'])
        self.assertEqual(result['netUniqueSessions'] - 76, 195)

    def test_no_event_yield_projection(self):
        result = derive(self.fixture)
        self.assertEqual(result['eventFloors'], {'DEV': 200, 'A': None, 'B': None, 'C': 97, 'D': 97, 'E': 97, 'F': None, 'G': None})
        self.assertEqual(result['newFreshEventFloors'], 291)

    def test_all_outcome_field_insertions_rejected(self):
        for location in [None, 'sourceMetadata', 'designAssumptions', 'developmentIdentity']:
            for key in ['classCounts', 'labelDistribution', 'precision', 'preservation', 'throughput', 'return', 'MFE', 'MAE', 'candidateScore', 'winnerCount', 'EXITPerformance', 'portfolioPerformance']:
                with self.subTest(location=location, field=key):
                    f = copy.deepcopy(self.fixture)
                    (f if location is None else f[location])[key] = 'SYNTHETIC_FORBIDDEN_SENTINEL'
                    with self.assertRaisesRegex(ValueError, 'METADATA_SCHEMA_REJECTED'):
                        derive(f)

    def test_unknown_fields_fail_closed_not_ignored(self):
        self.fixture['sourceMetadata']['unapprovedField'] = 1
        with self.assertRaises(ValueError):
            validate_input(self.fixture)

    def test_nested_outcome_object_cannot_replace_integer(self):
        self.fixture['sourceMetadata']['validationBlockSessions'] = {'classCounts': 'SYNTHETIC_SENTINEL'}
        with self.assertRaisesRegex(ValueError, 'INVALID_PLANNING_INTEGER'):
            derive(self.fixture)

    def test_poison_siblings_not_accessed_by_identity_projection(self):
        class Poison:
            def __repr__(self):
                raise AssertionError('FORBIDDEN_VALUE_RENDERED')
        class Source(dict):
            def __getitem__(self, key):
                if key == 'classCounts':
                    raise AssertionError('FORBIDDEN_FIELD_READ')
                return super().__getitem__(key)
        source = Source(self.fixture['developmentIdentity'], classCounts=Poison())
        self.assertEqual(project_identity(source), self.fixture['developmentIdentity'])

    def test_missing_approved_field_rejected(self):
        del self.fixture['sourceMetadata']['outerOosBlockSessions']
        with self.assertRaises(ValueError):
            derive(self.fixture)

    def test_identity_duplicate_rejected(self):
        self.fixture['developmentIdentity']['trainingSessions'][1] = self.fixture['developmentIdentity']['trainingSessions'][0]
        with self.assertRaisesRegex(ValueError, 'SESSION_IDENTITY_MISMATCH'):
            derive(self.fixture)

    def test_identity_hash_mismatch_rejected(self):
        self.fixture['developmentIdentity']['sessionListSha256'] = '0'*64
        with self.assertRaisesRegex(ValueError, 'SESSION_IDENTITY_HASH_MISMATCH'):
            derive(self.fixture)

    def test_boolean_not_a_session_count(self):
        self.fixture['sourceMetadata']['validationBlockSessions'] = True
        with self.assertRaises(ValueError):
            derive(self.fixture)

    def test_rate_cannot_be_replaced_with_observed_estimate(self):
        self.fixture['designAssumptions']['worstCaseRateDecimal'] = '0.9'
        with self.assertRaisesRegex(ValueError, 'FIXED_UNCERTAINTY_ASSUMPTIONS_CHANGED'):
            derive(self.fixture)

    def test_budget_mutation_detected(self):
        self.fixture['sourceMetadata']['validationBlockSessions'] = 20
        with self.assertRaisesRegex(ValueError, 'BUDGET_RESPONSIBILITY_CHANGED'):
            compare_previous(derive(self.fixture), self.previous)

    def test_omitted_stage_detected(self):
        self.previous['responsibilityMatrix'].pop()
        with self.assertRaises(ValueError):
            compare_previous(derive(self.fixture), self.previous)

    def test_shared_twenty_double_count_detected(self):
        self.previous['globalBudget']['netUniqueFreshSessions'] += 40
        with self.assertRaisesRegex(ValueError, 'BUDGET_ARITHMETIC_CHANGED'):
            compare_previous(derive(self.fixture), self.previous)

    def test_future_twenty_credit_detected(self):
        self.previous['globalBudget']['netUniqueFreshSessions'] -= 20
        with self.assertRaises(ValueError):
            compare_previous(derive(self.fixture), self.previous)

    def test_buffer_mutation_detected(self):
        self.fixture['designAssumptions']['bufferSessions'] = 10
        with self.assertRaises(ValueError):
            compare_previous(derive(self.fixture), self.previous)

    def test_original_builder_without_outcomes_byte_identical(self):
        result = replay()
        self.assertTrue(result['priorContractByteIdentical'])
        self.assertEqual(result['candidateOutcomeFieldsSupplied'], 0)
        self.assertEqual(set(result['candidateFieldAccesses']),
                         {'trainingIdentity.sessionCount', 'trainingIdentity.sessionListSha256', 'trainingIdentity.trainingSessions'})

    def test_rejected_value_not_leaked_in_reportable_exception(self):
        self.fixture['classCounts'] = 'SYNTHETIC_PRIVATE_OUTCOME_SENTINEL'
        with self.assertRaises(ValueError) as caught:
            derive(self.fixture)
        self.assertNotIn('SYNTHETIC_PRIVATE_OUTCOME_SENTINEL', str(caught.exception))

    def test_frozen_contract_semantically_preserves_every_budget_rule(self):
        frozen = json.loads((ROOT / 'predict/research/phase57-long-only-global-data-budget-v1.json').read_text())
        for key in frozen['semanticPreservationKeys']:
            before, after = copy.deepcopy(self.previous[key]), copy.deepcopy(frozen[key])
            if key == 'responsibilityMatrix':
                for row in before + after:
                    row.pop('status')
            self.assertEqual(before, after, key)
        self.assertTrue(compare_previous(derive(self.fixture), frozen))

    def test_frozen_sha_and_review_chain(self):
        manifest = json.loads((REVIEW / 'freeze-manifest.json').read_text())
        raw = (ROOT / manifest['contractPath']).read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), manifest['contractSha256'])
        frozen = json.loads(raw)
        self.assertEqual(hashlib.sha256((ROOT / frozen['integrityReviewPath']).read_bytes()).hexdigest(), frozen['integrityReviewSha256'])

    def test_historical_incident_not_erased_and_no_new_release(self):
        frozen = json.loads((ROOT / 'predict/research/phase57-long-only-global-data-budget-v1.json').read_text())
        self.assertEqual(frozen['historicalIncidentOccurrences'], 1)
        self.assertEqual(frozen['integrityVerdict'], 'A_NON_MATERIAL_OUTCOME_DISPLAY_INCIDENT')
        self.assertEqual(frozen['status'], 'PHASE57_LONG_ONLY_GLOBAL_DATA_BUDGET_FROZEN')
        self.assertFalse(frozen['datasetIdentityFrozen'])
        self.assertFalse(frozen['validationExecutionAuthorized'])
        self.assertFalse(frozen['providerPolicy']['actualAcquisitionAuthorized'])


if __name__ == '__main__':
    unittest.main()
