"""Pre-day dependency checks. Models are mocked; original scope/archive are real code."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import no11_input_prerequisites as check
import test_no11_frozen_p1_prepare_inputs as fixture
import test_no11_frozen_p1_previous_archive as prior


class PrerequisitesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture.PreparationTests.setUpClass()
        cls.scope_fixture = fixture.PreparationTests.scope_fixture

    setUp = fixture.PreparationTests.setUp
    tearDown = fixture.PreparationTests.tearDown
    write = fixture.PreparationTests.write
    save_archive = fixture.PreparationTests.save_archive

    def inspect(self, *, now=prior.PREFETCH, with_capture=False, full=False):
        evidence = self.write('prereq-evidence.json', self.evidence)
        template = self.write('prereq-template.json', self.template)
        return check.check(plan_file=self.plan, mask_file=self.mask,
            config_file=template, evidence_file=evidence, documents=self.docs,
            output_root=self.output, checked_at=now,
            capture_dir=self.capture if with_capture else None,
            require_full_shadow=full)

    def loaders(self):
        a = mock.patch.object(check.forward, 'FrozenP1Scorer', return_value=SimpleNamespace())
        b = mock.patch.object(check.h235, 'FrozenH235AsOf', return_value=SimpleNamespace(original_model_count=24))
        c = mock.patch.object(check.execution, 'settings', return_value=({}, {}))
        d = mock.patch.object(check.exits, 'load_original_exit', return_value=(object(), object()))
        return a, b, c, d

    def full_config(self):
        self.template['h235ModelRoot'] = str(self.root / 'runtime')
        self.template['shadowAccountConfig'] = str(self.write('shadow-account-fixture.json', {}))

    def test_preday_checks_do_not_create_future_master_or_start_excel(self):
        a, b, c, d = self.loaders()
        original = deepcopy(self.evidence)
        with a as p1, b as h235, c, d:
            report, path = self.inspect()
        self.assertTrue(path.is_file())
        self.assertTrue(report['p1AssetsLoaded'])
        self.assertEqual(report['h235ModelMembersVerified'], 0)
        self.assertTrue(report['previousCollectionStillRequired'])
        self.assertTrue(report['actualSessionReferenceStillRequired'])
        for key in ('shadowReady', 'modelsScored', 'excelStarted', 'actualRssVerified', 'productionReady', 'orderTransmission'):
            self.assertFalse(report[key])
        self.assertEqual(self.evidence, original)
        self.assertEqual(list(self.output.glob('dated-master-*')), [])
        self.assertEqual(list(self.output.glob('bootstrap-ready-inputs-*')), [])
        p1.assert_called_once()
        h235.assert_not_called()

    def test_full_shadow_loads_same_24_models_and_arrival_exit_dependencies(self):
        self.full_config()
        a, b, c, d = self.loaders()
        with a as p1, b as h235, c as account, d as exit_code:
            report, _ = self.inspect(full=True)
        self.assertEqual(report['h235ModelMembersVerified'], 24)
        self.assertTrue(report['shadowPortfolioAssetsChecked'])
        p1.assert_called_once()
        h235.assert_called_once()
        account.assert_called_once()
        exit_code.assert_called_once()
        self.assertFalse(report['modelsScored'])

    def test_full_shadow_not_silently_reduced_to_p1(self):
        with mock.patch.object(check.forward, 'FrozenP1Scorer') as p1:
            with self.assertRaisesRegex(ValueError, 'FULL_SHADOW_MODEL_AND_ACCOUNT_CONFIG_REQUIRED'):
                self.inspect(full=True)
            p1.assert_not_called()

    def test_missing_evidence_stops_before_models(self):
        self.evidence['rows'][0]['symbol'] = '6501.T'
        with mock.patch.object(check.forward, 'FrozenP1Scorer') as p1:
            with self.assertRaisesRegex(ValueError, 'SELECTED_SYMBOL_REVIEW_MISSING'):
                self.inspect()
            p1.assert_not_called()

    def test_unconfirmed_security_flags_are_not_automatically_filled(self):
        for key in ('commonEquity', 'corporateActionsCleared', 'priceBasisVerified'):
            with self.subTest(key=key):
                original = self.evidence['rows'][0][key]
                self.evidence['rows'][0][key] = False
                with mock.patch.object(check.forward, 'FrozenP1Scorer') as p1:
                    with self.assertRaisesRegex(ValueError, 'REVIEW_NOT_CONFIRMED'):
                        self.inspect()
                    p1.assert_not_called()
                self.evidence['rows'][0][key] = original

    def test_future_review_clock_is_rejected_without_relabeling(self):
        self.evidence['knownAtJst'] = prior.DAY + 'T09:00:00+09:00'
        with self.assertRaisesRegex(ValueError, 'EXISTING_SECURITY_REVIEW_REQUIRED'):
            self.inspect()

    def test_changed_document_fails_before_excel_or_models(self):
        (self.docs / (self.docsha + '.source')).write_bytes(b'modified')
        with mock.patch.object(check.forward, 'FrozenP1Scorer') as p1:
            with self.assertRaisesRegex(ValueError, 'DOCUMENT_BYTES_CHANGED'):
                self.inspect()
            p1.assert_not_called()
        self.assertEqual(list(self.output.glob('input-prerequisites-*')), [])

    def test_previous_source_is_checked_by_existing_hash_and_stage_logic(self):
        a, b, c, d = self.loaders()
        with a, b, c, d:
            report, _ = self.inspect(with_capture=True)
        self.assertEqual(report['suppliedPreviousUsableSymbols'], 1)
        self.assertFalse(report['previousCollectionStillRequired'])
        self.member_path.write_bytes(self.member_path.read_bytes() + b' ')
        with self.assertRaisesRegex(ValueError, 'ARCHIVE_BYTES_CHANGED'):
            self.inspect(with_capture=True)

    def test_missing_model_failure_has_no_success_report(self):
        with mock.patch.object(check.forward, 'FrozenP1Scorer', side_effect=ValueError('P1_FORWARD_PRIVATE_MODEL_MISSING')):
            with self.assertRaisesRegex(ValueError, 'PRIVATE_MODEL_MISSING'):
                self.inspect()
        self.assertEqual(list(self.output.glob('input-prerequisites-*')), [])

    def test_bad_h235_member_count_has_no_success_report(self):
        self.full_config()
        with mock.patch.object(check.forward, 'FrozenP1Scorer'), \
             mock.patch.object(check.h235, 'FrozenH235AsOf', return_value=SimpleNamespace(original_model_count=23)):
            with self.assertRaisesRegex(ValueError, 'ORIGINAL_H235_MEMBER_COUNT'):
                self.inspect(full=True)

    def test_original_arrival_failure_does_not_become_ready(self):
        self.full_config()
        with mock.patch.object(check.forward, 'FrozenP1Scorer'), \
             mock.patch.object(check.h235, 'FrozenH235AsOf', return_value=SimpleNamespace(original_model_count=24)), \
             mock.patch.object(check.execution, 'settings', side_effect=ValueError('NO11_H235_CAPITAL_ORIGINAL_ARRIVAL_HASH_MISMATCH')):
            with self.assertRaisesRegex(ValueError, 'ARRIVAL_HASH_MISMATCH'):
                self.inspect(full=True)
        self.assertEqual(list(self.output.glob('input-prerequisites-*')), [])

    def test_bad_collector_options_and_live_permission_rejected(self):
        for key, value in (('samples', True), ('historyBars', 3000), ('orderTransmission', True)):
            saved = deepcopy(self.template)
            self.template[key] = value
            with self.assertRaises(ValueError):
                self.inspect()
            self.template = saved

    def test_same_inputs_same_report_and_no_source_mutation(self):
        a, b, c, d = self.loaders()
        original = self.member_path.read_bytes()
        with a, b, c, d:
            first = self.inspect(with_capture=True)
            second = self.inspect(with_capture=True)
        self.assertEqual(first, second)
        self.assertEqual(self.member_path.read_bytes(), original)


if __name__ == '__main__':
    unittest.main()
