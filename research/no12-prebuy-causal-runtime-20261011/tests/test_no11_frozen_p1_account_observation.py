"""Read-only account integration; all balances, prices and processes are synthetic."""
from pathlib import Path
import json
import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import no11_account_observation as account
import test_no11_frozen_p1_execution_service as old
import no11_frozen_p1_feature_runtime as features
import no11_h235_asof_forward_shadow as h


def report(allow=True, excluded=None):
    return {'schemaId': 'ARK_NO11_ACCOUNT_OBSERVATION_REPORT_V1', 'status': 'OBSERVED_READONLY',
            'sourceAt': old.at(575, 10), 'newShadowEntriesAllowed': allow,
            'excludedSymbols': excluded or [], 'productionReady': False, 'orderTransmission': False}


class AccountBindingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.env = mock.patch.dict(os.environ, {}, clear=False)
        self.env.start()
        self.before = os.environ.pop(account.ENV, None)

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def test_no_source_does_not_claim_physical_account_connected(self):
        a = account.AccountObservation(self.root, old.DAY)
        self.assertFalse(a.enabled)
        self.assertEqual(a.observe()['status'], 'NOT_CONFIGURED')

    def test_removed_environment_on_restart_retains_original_binding(self):
        os.environ[account.ENV] = str(self.root / 'observed.json')
        a = account.AccountObservation(self.root, old.DAY)
        self.assertTrue(a.enabled)
        del os.environ[account.ENV]
        b = account.AccountObservation(self.root, old.DAY)
        self.assertTrue(b.enabled)
        self.assertEqual(a.source, b.source)

    def test_changed_source_on_restart_blocks_instead_of_relaxing(self):
        os.environ[account.ENV] = str(self.root / 'observed.json')
        account.AccountObservation(self.root, old.DAY)
        os.environ[account.ENV] = str(self.root / 'other.json')
        b = account.AccountObservation(self.root, old.DAY)
        self.assertFalse(b.observe()['newShadowEntriesAllowed'])

    def test_timeout_and_invalid_response_block_without_leaking_input(self):
        os.environ[account.ENV] = str(self.root / 'observed.json')
        a = account.AccountObservation(self.root, old.DAY)
        with mock.patch.object(account.subprocess, 'run', side_effect=subprocess.TimeoutExpired('private-command', 10)):
            self.assertFalse(a.observe()['newShadowEntriesAllowed'])
        with mock.patch.object(account.subprocess, 'run', return_value=SimpleNamespace(returncode=2, stdout=json.dumps(report(True)))):
            self.assertFalse(a.observe()['newShadowEntriesAllowed'])
        self.assertNotIn('private-command', json.dumps(a.report))

    def test_valid_inspection_report_stays_separate_from_portfolio(self):
        os.environ[account.ENV] = str(self.root / 'observed.json')
        a = account.AccountObservation(self.root, old.DAY)
        with mock.patch.object(account.subprocess, 'run', return_value=SimpleNamespace(returncode=0, stdout=json.dumps(report()))):
            self.assertTrue(a.observe()['newShadowEntriesAllowed'])
        self.assertFalse((self.root / ('portfolio-shadow-' + old.DAY + '.sqlite')).exists())


class ActualPortfolioAccountGuard(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime = features.load_feature_runtime(h.ROOT)

    setUp = old.ReceivedExecutionTests.setUp
    tearDown = old.ReceivedExecutionTests.tearDown
    append_bar = old.ReceivedExecutionTests.append_bar

    def guard(self, value):
        self.runner.account = SimpleNamespace(enabled=True, report=value, observe=lambda: value)

    def test_personal_holding_excluded_before_native_funding(self):
        self.guard(report(excluded=['7203.T']))
        r = self.runner.advance(self.feed, self.inference, old.at(575, 12))
        self.assertEqual(r['buyIntentCount'], 0)
        self.assertEqual(r['cashJpy'], '1000000')

    def test_account_failure_cancels_only_local_pending_buy_and_keeps_cash(self):
        self.runner.advance(self.feed, self.inference, old.at(575, 12))
        self.guard(report(False))
        self.append_bar(575, self.feed['rows'][-1]['C'] - .05)
        r = self.runner.advance(self.feed, self.inference, old.at(576, 12))
        self.assertEqual(r['positionCount'], 0)
        self.assertEqual(r['pendingOrders'], 0)
        self.assertEqual(r['cashJpy'], '1000000')
        self.assertEqual(r['brokerTransmissions'], 0)

    def test_held_position_still_exits_when_account_source_is_down(self):
        self.runner.advance(self.feed, self.inference, old.at(575, 12))
        self.append_bar(575, self.feed['rows'][-1]['C'] - .05)
        self.runner.advance(self.feed, self.inference, old.at(576, 12))
        self.guard(report(False))
        self.assertEqual(self.runner.heartbeat(old.at(920))['sellIntentCount'], 1)
        self.append_bar(920, self.feed['rows'][-1]['C'] + .5)
        r = self.runner.advance(self.feed, self.inference, old.at(921, 12))
        self.assertEqual(r['positionCount'], 0)
        self.assertTrue(r['firstSellFillBuyHalt'])
        self.assertFalse(r['realAccountExecutionConnected'])

    def test_later_account_receipt_cannot_authorize_earlier_funding(self):
        self.guard(dict(report(), sourceAt=old.at(575, 13)))
        self.assertEqual(self.runner.advance(self.feed, self.inference, old.at(575, 12))['buyIntentCount'], 0)

    def test_unknown_simulated_order_stays_unresolved_during_account_failure(self):
        self.runner.advance(self.feed, self.inference, old.at(575, 12))
        o = next(iter(self.runner.portfolio.state()['orders'].values()))
        self.runner.portfolio.update({'schemaId': 'ARK_NO11_SIMULATED_ORDER_UPDATE_V1',
          'eventId': 'd'*64, 'orderId': o['orderId'], 'symbol': o['symbol'], 'side': 'BUY',
          'knownAtJst': old.at(575, 15), 'cumulativeQuantity': 0, 'cumulativeValueJpy': '0',
          'status': 'UNKNOWN', 'syntheticOnly': True}, old.at(575, 15))
        self.guard(report(False))
        self.runner.advance(self.feed, self.inference, old.at(575, 20))
        s = self.runner.portfolio.state()
        self.assertEqual(s['orders'][o['orderId']]['status'], 'UNKNOWN')
        self.assertTrue(s['reconciliationBlocked'])


if __name__ == '__main__':
    unittest.main()
