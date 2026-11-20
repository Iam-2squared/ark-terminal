"""Fresh synthetic tests; no previous patch suite/archive is loaded."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace, MethodType
from unittest.mock import patch
import ast
import hashlib
import json
import os
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
ENGINE = Path(os.environ['NO11_CLEAN_ENGINE']).resolve()
sys.path.insert(0, str(ENGINE / 'tools'))
sys.path.insert(0, str(HERE))
import no11_clean_runtime_guards as guards
import no11_clean_weekly as weekly
import no11_broker_execution_service as service
import no11_prepare_received_inputs as prep
import no11_input_prerequisites as prerequisites
import rebuild

DAY = '2026-11-09'
NOW = DAY + 'T09:00:10+09:00'


class FeeTests(unittest.TestCase):
    def test_legacy_config_not_mutated(self):
        value = {'orderTerms': {'sor': False}}
        before = deepcopy(value)
        guards.validate_fee_course(value)
        self.assertEqual(value, before)

    def test_zero_requires_boolean_true(self):
        for value in (False, 1, 'true', None):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, 'ZERO_REQUIRES_SOR'):
                guards.validate_fee_course({'feeCourse': 'ZERO', 'orderTerms': {'sor': value}})

    def test_zero_sor_pass(self):
        guards.validate_fee_course({'feeCourse': 'ZERO', 'orderTerms': {'sor': True}})

    def test_unknown_fee_rejected(self):
        for value in ('zero', '', True, 7):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, 'FEE_COURSE_UNKNOWN'):
                guards.validate_fee_course({'feeCourse': value})


class DispatchTests(unittest.TestCase):
    def setUp(self):
        self.command = {'kind': 'ORDER', 'side': 'SELL', 'intentId': 'intent', 'commandId': 'c' * 64,
                        'commandSha256': 'd' * 64, 'rssOrderId': 901, 'symbol': '7203.T',
                        'quantity': 100, 'account': '一般'}
        self.state = {'orders': {'intent': dict(self.command, entryId='entry', brokerOrderNumber=None)},
                      'positions': {'entry': {'symbol': '7203.T', 'account': '一般', 'quantity': 100}}}
        self.external = []
        self.permits = 0
        self.sends = 0
        self.observations = 0
        self.subject = SimpleNamespace(session=DAY, root=Path(tempfile.gettempdir()),
            config={'evidenceMode': 'OFFLINE_REPLAY', 'transport': {'mode': 'OBSERVE_ONLY'}},
            clock=lambda: NOW, source_error=None,
            source={'captureCompletedAt': NOW, 'positions': [
                {'symbol': '7203', 'account': '一般', 'quantity': 100}], 'orders': []})
        self.subject.book = SimpleNamespace(snapshot=lambda at: deepcopy(self.state),
            source_checkpoint=lambda key: list(self.external), begin_dispatch=self.begin,
            record_transport_result=lambda *args: None)
        self.subject._source_current = MethodType(service.BrokerExecution._source_current, self.subject)
        self.subject._sell_safe = MethodType(service.BrokerExecution._sell_safe, self.subject)
        self.subject._transport = self.send
        self.subject.observe_file = self.observe

    def begin(self, *args):
        self.permits += 1
        return {'dispatchPermit': {'synthetic': True}}

    def send(self, packet):
        self.sends += 1
        c = packet['command']
        return {'schemaId': 'ARK_NO11_MSII_TRANSPORT_RESULT_V1',
                'commandId': c['commandId'], 'commandSha256': c['commandSha256'],
                'rssOrderId': c['rssOrderId'], 'status': 'SENT_AWAITING_RECONCILIATION',
                'dispatchAttempted': True}

    def observe(self, at):
        self.observations += 1
        return True

    def dispatch(self):
        with patch.object(service, 'exclusive_json', return_value=None):
            return service.BrokerExecution._dispatch(self.subject, self.command, NOW)

    def blocked(self):
        with self.assertRaises(ValueError):
            self.dispatch()
        self.assertEqual((self.permits, self.sends), (0, 0))

    def test_clean_ark_sell_reaches_boundary_once(self):
        self.assertEqual(self.dispatch()['status'], 'SENT_AWAITING_RECONCILIATION')
        self.assertEqual((self.permits, self.sends), (1, 1))

    def test_manual_only_stock_not_adopted(self):
        self.state['positions'].clear()
        self.blocked()

    def test_unknown_order_cannot_borrow_holding(self):
        self.state['orders'].clear()
        self.blocked()

    def test_command_identity_mismatch(self):
        self.state['orders']['intent']['commandId'] = 'e' * 64
        self.blocked()

    def test_manual_full_sale_blocks(self):
        self.subject.source['positions'].clear()
        self.blocked()

    def test_manual_partial_sale_blocks_full_exit(self):
        self.subject.source['positions'][0]['quantity'] = 50
        self.blocked()

    def test_ledger_quantity_reduction_blocks(self):
        self.state['positions']['entry']['quantity'] = 50
        self.blocked()

    def test_manual_additional_buy_blocks_even_excess_quantity(self):
        self.subject.source['positions'][0]['quantity'] = 200
        self.blocked()

    def test_manual_rebuy_cannot_clear_sticky_exclusion(self):
        self.external.append('7203.T')
        self.blocked()
        self.assertEqual(self.external, ['7203.T'])

    def test_different_account_cannot_cover_sell(self):
        self.subject.source['positions'][0]['account'] = '特定'
        self.blocked()

    def test_unrelated_manual_holding_does_not_get_sold(self):
        self.external.append('6501.T')
        self.subject.source['positions'].append({'symbol': '6501', 'account': '一般', 'quantity': 300})
        self.dispatch()
        self.assertEqual(self.command['symbol'], '7203.T')
        self.assertEqual(self.sends, 1)

    def test_stale_observation_blocks(self):
        self.subject.source['captureCompletedAt'] = DAY + 'T08:59:00+09:00'
        self.blocked()

    def test_failed_refresh_never_uses_old_success(self):
        self.subject.config['evidenceMode'] = 'BROKER_OBSERVATION'
        self.subject.observe_file = lambda at: False
        self.blocked()

    def test_observed_manual_sale_between_prepare_and_dispatch(self):
        self.subject.config['evidenceMode'] = 'BROKER_OBSERVATION'
        def changed(at):
            self.subject.source['positions'].clear()
            return True
        self.subject.observe_file = changed
        self.blocked()

    def test_live_observer_reread_happens(self):
        self.subject.config['evidenceMode'] = 'BROKER_OBSERVATION'
        self.dispatch()
        self.assertEqual(self.observations, 1)

    def test_reversed_clock_blocks(self):
        self.subject.config['evidenceMode'] = 'BROKER_OBSERVATION'
        self.subject.clock = lambda: DAY + 'T09:00:09+09:00'
        self.blocked()

    def test_cancel_not_blocked_by_zero_stock(self):
        self.command['kind'] = 'CANCEL'
        self.subject.source = None
        self.dispatch()
        self.assertEqual(self.sends, 1)

    def test_buy_behavior_not_changed_by_sell_guard(self):
        self.command['side'] = 'BUY'
        self.subject.source = None
        self.dispatch()
        self.assertEqual(self.sends, 1)


class WeeklyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)
        self.static_sha = hashlib.sha256(b'synthetic static document').hexdigest()
        self.daily_sha = hashlib.sha256(b'synthetic daily document').hexdigest()
        (self.root / (self.static_sha + '.source')).write_bytes(b'synthetic static document')
        (self.root / (self.daily_sha + '.source')).write_bytes(b'synthetic daily document')
        self.info = {'sessionDate': DAY, 'previousSession': '2026-11-06',
                     'selectedSymbols': ['7203.T'], 'chartPlanSha256': 'a' * 64}
        self.week = {'schemaId': weekly.SCHEMA, 'weekStart': DAY, 'weekEnd': '2026-11-13',
                     'acquiredAtJst': '2026-11-06T18:00:00+09:00',
                     'knownAtJst': '2026-11-06T18:01:00+09:00',
                     'reviewStatus': 'EXTERNALLY_REVIEWED', 'productionReady': False,
                     'orderTransmission': False, 'dailyGuardDirectory': str(self.root),
                     'rows': [{'symbol': '7203.T', 'commonEquity': True, 'domesticEquity': True,
                               'listed': True, 'lotShares': 100, 'segment': 'PRIME', 'sector': 'Synthetic',
                               'sourceDocumentSha256': [self.static_sha]}]}
        self.reference = {'schemaId': prep.REFERENCE, 'sessionDate': DAY,
                          'source': 'RssMarket_SELECTED_REFERENCE_READONLY', 'readOnly': True,
                          'productionReady': False, 'orderTransmission': False,
                          'chartPlanSha256': 'a' * 64, 'selectedSymbols': ['7203.T'],
                          'capturedAtJst': DAY + 'T09:00:01+09:00',
                          'completedAtJst': DAY + 'T09:00:03+09:00',
                          'rows': [{'symbol': '7203.T', 'marketCode': 'T', 'marketDate': DAY,
                                    'previousDate': '2026-11-06', 'lotShares': 100,
                                    'marketSection': '東証P', 'previousClose': 100, 'dayBasePrice': 100}]}
        self.week_hash = hashlib.sha256(json.dumps(self.week).encode()).hexdigest()
        self.ref_hash = hashlib.sha256(json.dumps(self.reference).encode()).hexdigest()
        self.guard = {'schemaId': weekly.GUARD, 'sessionDate': DAY, 'previousSession': '2026-11-06',
                      'reviewStatus': 'EXTERNALLY_REVIEWED', 'productionReady': False, 'orderTransmission': False,
                      'knownAtJst': DAY + 'T09:00:05+09:00', 'weeklyFileSha256': self.week_hash,
                      'referenceFileSha256': self.ref_hash, 'chartPlanSha256': 'a' * 64,
                      'rows': [{'symbol': '7203.T', 'reviewStatus': 'CLEAR', 'changesReviewed': True,
                                'tradingSuspended': False, 'corporateActionsCleared': True,
                                'priceBasisVerified': True, 'reviewedPreviousClose': 100,
                                'sourceDocumentSha256': [self.daily_sha]}]}

    def assemble(self):
        (self.root / (DAY + '.json')).write_text(json.dumps(self.guard), encoding='utf-8')
        return weekly.assemble(self.info, self.reference, self.week, NOW,
                               weekly_sha=self.week_hash, reference_sha=self.ref_hash)

    def test_weekly_and_daily_feed_original_master_contract(self):
        result = self.assemble()
        prep.verify_documents(result, self.root)
        master = prep.build_master(self.info, self.reference, result,
                    reference_sha=self.ref_hash, evidence_sha='c' * 64, prepared_at=NOW)
        self.assertEqual(len(master['rows']), 1)
        self.assertFalse(master['orderTransmission'])
        self.assertFalse(master['productionReady'])

    def test_preday_static_check_does_not_certify_daily_data(self):
        prerequisites.validate_review(self.info, self.week, '2026-11-08T18:00:00+09:00')
        self.assertFalse((self.root / (DAY + '.json')).exists())

    def test_next_week_rejected(self):
        self.info['sessionDate'] = '2026-11-16'
        with self.assertRaisesRegex(ValueError, 'OUTSIDE_TARGET_WEEK'):
            weekly.validate_static(self.info, self.week, NOW)

    def test_weekend_not_session(self):
        self.info['sessionDate'] = '2026-11-14'
        with self.assertRaises(ValueError):
            weekly.validate_static(self.info, self.week, NOW)

    def test_unreviewed_static_rejected(self):
        self.week['reviewStatus'] = 'NOT_REVIEWED'
        with self.assertRaises(ValueError):
            self.assemble()

    def test_non_equity_or_wrong_lot_rejected(self):
        for key, value in [('commonEquity', False), ('domesticEquity', False), ('listed', False), ('lotShares', 1)]:
            with self.subTest(key=key):
                original = self.week['rows'][0][key]
                self.week['rows'][0][key] = value
                with self.assertRaises(ValueError):
                    self.assemble()
                self.week['rows'][0][key] = original

    def test_missing_selected_symbol_not_silently_dropped(self):
        self.info['selectedSymbols'].append('6501.T')
        with self.assertRaises(ValueError):
            self.assemble()
        self.assertEqual(len(self.info['selectedSymbols']), 2)

    def test_future_static_source_rejected(self):
        self.week['knownAtJst'] = DAY + 'T10:00:00+09:00'
        with self.assertRaises(ValueError):
            self.assemble()

    def test_daily_guard_absent_rejected(self):
        with self.assertRaises((ValueError, OSError)):
            weekly.assemble(self.info, self.reference, self.week, NOW,
                            weekly_sha=self.week_hash, reference_sha=self.ref_hash)

    def test_daily_reviews_cannot_be_assumed(self):
        for key in ('changesReviewed', 'corporateActionsCleared', 'priceBasisVerified'):
            with self.subTest(key=key):
                self.guard['rows'][0][key] = False
                with self.assertRaises(ValueError):
                    self.assemble()
                self.guard['rows'][0][key] = True

    def test_suspended_symbol_rejected(self):
        self.guard['rows'][0]['tradingSuspended'] = True
        with self.assertRaises(ValueError):
            self.assemble()

    def test_wrong_reference_and_weekly_hash_rejected(self):
        for key in ('weeklyFileSha256', 'referenceFileSha256', 'chartPlanSha256'):
            with self.subTest(key=key):
                original = self.guard[key]
                self.guard[key] = 'f' * 64
                with self.assertRaises(ValueError):
                    self.assemble()
                self.guard[key] = original

    def test_stale_or_future_daily_review_rejected(self):
        for value in ('2026-11-06T10:00:00+09:00', DAY + 'T10:00:00+09:00', DAY + 'T09:00:02+09:00'):
            with self.subTest(value=value):
                self.guard['knownAtJst'] = value
                with self.assertRaises(ValueError):
                    self.assemble()

    def test_price_mismatch_and_nan_rejected(self):
        for value in (101, float('nan'), True):
            with self.subTest(value=value):
                self.guard['rows'][0]['reviewedPreviousClose'] = value
                with self.assertRaises(ValueError):
                    self.assemble()

    def test_document_byte_tamper_rejected(self):
        result = self.assemble()
        (self.root / (self.daily_sha + '.source')).write_bytes(b'tampered')
        with self.assertRaises(ValueError):
            prep.verify_documents(result, self.root)

    def test_no_input_mutation_or_authorization(self):
        before = deepcopy((self.info, self.reference, self.week, self.guard))
        result = self.assemble()
        self.assertEqual((self.info, self.reference, self.week, self.guard), before)
        self.assertFalse(result['orderTransmission'])


class PackageTests(unittest.TestCase):
    def test_generated_targets_match_pinned_source_transform(self):
        repository = Path(os.environ['NO11_CLEAN_REPO'])
        for name in rebuild.TARGETS:
            with self.subTest(name=name):
                original = rebuild.git(repository, 'show', rebuild.BASE + ':' + rebuild.ENGINE + '/' + name)
                actual = (ENGINE / name).read_bytes()
                self.assertEqual(rebuild.normalized(actual), rebuild.transform(name, original))

    def test_python_payload_parses(self):
        for name in list(rebuild.TARGETS) + list(rebuild.ADDITIONS.values()):
            if name.endswith('.py'):
                ast.parse((ENGINE / name).read_text(encoding='utf-8'))

    def test_unknown_target_or_context_rejected(self):
        with self.assertRaises(ValueError):
            rebuild.transform('tools/unknown.py', b'pass\n')
        with self.assertRaises(ValueError):
            rebuild.transform('tools/no11_broker_execution_service.py', b'pass\n')

    def test_existing_output_refused(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(ValueError):
                rebuild.build(Path('.'), Path(folder))

    def test_line_endings_normalized_not_content(self):
        self.assertEqual(rebuild.blob(b'one\r\ntwo\r\n'), rebuild.blob(b'one\ntwo\n'))
        self.assertNotEqual(rebuild.blob(b'one\ntwo\n'), rebuild.blob(b'one\nthree\n'))

    def test_package_manifest_hashes_and_scope(self):
        package = Path(os.environ['NO11_CLEAN_PACKAGE'])
        manifest = json.loads((package / 'manifest.json').read_text(encoding='utf-8'))
        self.assertEqual(len(manifest['files']), 10)
        self.assertFalse(manifest['oldPackagesUsed'])
        for item in manifest['files']:
            data = (package / 'payload' / item['path']).read_bytes()
            self.assertEqual(hashlib.sha256(data).hexdigest(), item['outputSha256'])
            self.assertEqual(rebuild.blob(data), item['outputGitBlob'])
            self.assertNotIn('frozen', item['path'].lower())


if __name__ == '__main__':
    unittest.main(verbosity=2)
