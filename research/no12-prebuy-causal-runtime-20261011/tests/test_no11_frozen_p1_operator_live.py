"""Full MAX3 cash-only operator entry: offline-only routing and safety tests."""
from pathlib import Path
import json
import sys
import tempfile
import unittest
from unittest.mock import patch

TOOLS = Path(__file__).resolve().parents[1] / 'tools'
WINDOWS = Path(__file__).resolve().parents[1] / 'windows'
sys.path.insert(0, str(TOOLS))
import no11_received_session_bootstrap as b
import no11_received_session_controller as controller


class OrdinaryLiveBridgeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.broker_file = self.root / 'broker.json'
        self.cash_file = self.root / 'cash.json'
        self.cash_file.write_text('{}', encoding='utf-8')
        self.transport = {
            'mode': 'LIVE', 'orderTransmission': True,
            'operatorEnabled': True, 'approvedForSession': True,
            'sessionDate': '2026-11-02'
        }
        self.broker = {
            'schemaId': b.BROKER_CONFIG,
            'sessionDate': '2026-11-02',
            'evidenceMode': 'BROKER_OBSERVATION',
            'ledger': {'maxSymbols': 3, 'lotSize': 100,
                       'allocatedCashJpy': 'AUTO_SECURITIES_ACCOUNT_CASH_ONLY'},
            'transport': self.transport,
            'orderTerms': {},
            'originalArrivalTable': str(self.root / 'table.json'),
            'securitiesCashEvidenceFile': str(self.cash_file),
            'productionReady': False, 'orderTransmission': True,
        }
        self.save()

    def tearDown(self):
        self.temp.cleanup()

    def save(self):
        self.broker_file.write_text(json.dumps(self.broker), encoding='utf-8')

    def test_readonly_bootstrap_and_normal_service_can_never_accidentally_promote_live(self):
        with self.assertRaisesRegex(ValueError, 'BROKER_CONFIG_NOT_READONLY'):
            b.validate_readonly_broker_config(self.broker_file, '2026-11-02')
        b.validate_readonly_broker_config(self.broker_file, '2026-11-02',
                                          allow_explicit_live=True)
        config = {
            'sessionDate': '2026-11-02',
            'h235ModelRoot': str(self.root),
            'runtimeRoot': str(self.root),
            'brokerExecutionConfig': str(self.broker_file)
        }
        files = {k: str(self.root / (k + '.json'))
                 for k in ('plan', 'mask', 'master', 'previous')}
        prepared = {'files': files}
        with self.assertRaisesRegex(ValueError, 'BROKER_CONFIG_NOT_READONLY'):
            b.service_args(config, prepared, self.root)
        live_args = b.service_args(config, prepared, self.root,
                                  allow_explicit_live=True)
        self.assertIn('--broker-execution-config', live_args)
        self.assertNotIn('--broker-execution-readonly', live_args)

    def test_live_route_rejects_disabled_or_expired_operator_flags(self):
        for key, value in (
            ('operatorEnabled', False),
            ('approvedForSession', False),
            ('orderTransmission', False),
            ('mode', 'OBSERVE_ONLY'),
            ('sessionDate', '2026-10-30')
        ):
            with self.subTest(key=key):
                original = self.transport[key]
                self.transport[key] = value
                self.save()
                with self.assertRaisesRegex(ValueError,
                    'EXPLICIT_LIVE_APPROVAL_AND_SECURITIES_EVIDENCE_REQUIRED'):
                    b.validate_readonly_broker_config(
                        self.broker_file, '2026-11-02',
                        allow_explicit_live=True)
                self.transport[key] = original
        self.broker['orderTransmission'] = False
        self.save()
        with self.assertRaisesRegex(ValueError,
            'EXPLICIT_LIVE_APPROVAL_AND_SECURITIES_EVIDENCE_REQUIRED'):
            b.validate_readonly_broker_config(
                self.broker_file, '2026-11-02', allow_explicit_live=True)

    def test_direct_live_controller_requires_same_day_even_before_creating_run(self):
        config = {
            'sessionDate': '2026-11-02',
            'brokerExecutionConfig': str(self.broker_file),
            'h235ModelRoot': str(self.root),
            'privateRoot': str(self.root),
            'productionReady': False, 'orderTransmission': False
        }
        with patch.object(b, 'stamp', return_value='2026-10-30T09:00:00.000+09:00'):
            with self.assertRaisesRegex(ValueError, 'LIVE_REQUIRES_ACTUAL_SESSION_DAY'):
                controller.execute(config, b, allow_explicit_live=True,
                                   preflight_only=True)
        self.assertEqual(list(self.root.glob('session-*')), [])

    def test_full_max3_not_single_symbol_and_dedicated_operator_entry_exists(self):
        script=(WINDOWS / 'Run-No11ReceivedSessionOperatorLive.ps1').read_text(
            encoding='utf-8-sig')
        ordinary=(WINDOWS / 'Run-No11ReceivedSessionReadOnly.ps1').read_text(
            encoding='utf-8-sig')
        self.assertIn('IApproveFullArkLiveOrdersForThisSession', script)
        self.assertIn("NO11_OPERATOR_LIVE_MAX_ARK_POSITIONS=3", script)
        self.assertIn('AUTO_SECURITIES_ACCOUNT_CASH_ONLY', script)
        self.assertIn('account-source-', script)
        self.assertIn('Observe-No11AccountReadOnly.ps1', script)
        self.assertIn('--operator-approved-broker-live', script)
        self.assertNotIn('IApproveFullArkLiveOrdersForThisSession', ordinary)
        self.assertIn('ORDER_TRANSMISSION=False', ordinary)
        broker=(TOOLS / 'no11_broker_execution_service.py').read_text(encoding='utf-8')
        ledger=(TOOLS / 'no11_broker_execution_ledger.py').read_text(encoding='utf-8')
        self.assertIn("len(intents) <= 3", broker)
        self.assertIn("maxSymbols', 3) == 3", ledger)
        self.assertIn("lotSize', 100) == 100", ledger)


if __name__ == '__main__':
    unittest.main()
