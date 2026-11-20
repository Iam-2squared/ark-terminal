"""Offline regression tests of actual coordinator method bodies.

AST extraction avoids importing Frozen models or creating a transport. Only
parser/observer, transport and book boundaries are mocked. Ledger checkpoint
restart/no-adoption tests below use the real SQLite ledger. No trades occur.
"""
from __future__ import annotations

import ast
from copy import deepcopy
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

TOOLS = Path(__file__).resolve().parents[1] / 'tools'
sys.path.insert(0, str(TOOLS))
import no11_exit_ownership_patch as installer
import no11_broker_execution_ledger as ledger
import no11_broker_fill_attribution as attribution

ORIGINAL = (TOOLS / 'no11_broker_execution_service.py').read_text(encoding='utf-8')
PATCHED = installer.patch_text(ORIGINAL)
DAY = '2026-11-02'
NOW = DAY + 'T10:00:00.000+09:00'


def extracted(text):
    tree = ast.parse(text)
    wanted = {'_source_current', '_sell_safe', 'observe_envelope',
              '_exit_ownership_before_dispatch', '_dispatch'}
    klass = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'BrokerExecution')
    methods = [n for n in klass.body if isinstance(n, ast.FunctionDef) and n.name in wanted]
    helpers = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in {'need', 'safe_reason'}]
    compiled_class = ast.ClassDef(name='Subject', bases=[], keywords=[], body=methods, decorator_list=[])
    module = ast.fix_missing_locations(ast.Module(body=helpers + [compiled_class], type_ignores=[]))
    ns = {'ledger': ledger, 'attribution': attribution, 'json': json, 're': re,
          'deepcopy': deepcopy, 'exclusive_json': lambda *args: None,
          'ERRORS': (OSError, ValueError, KeyError, TypeError, RuntimeError, subprocess.SubprocessError)}
    exec(compile(module, '<actual-coordinator-methods>', 'exec'), ns)
    return ns['Subject']


Subject = extracted(PATCHED)
OldSubject = extracted(ORIGINAL)


class FakeBook:
    def __init__(self):
        self.checkpoints = {}
        self.state = {
            'orders': {'sell-intent': {
                'intentId': 'sell-intent', 'commandId': 'sell-command',
                'entryId': 'ark-entry', 'symbol': '8729.T', 'side': 'SELL',
                'account': '一般', 'quantity': 100, 'brokerOrderNumber': None,
                'phase': 'PREPARED'}},
            'commands': {'sell-command': {'begunAtJst': None, 'state': 'PREPARED'}},
            'positions': {'ark-entry': {'entryId': 'ark-entry', 'symbol': '8729.T',
                                        'account': '一般', 'quantity': 100}},
        }
        self.begun = []
        self.events = []

    def snapshot(self, at):
        return deepcopy(self.state)

    def source_checkpoint(self, name):
        return deepcopy(self.checkpoints.get(name))

    def checkpoint_source(self, name, value, at):
        self.checkpoints[name] = deepcopy(value)

    def observe_account(self, event, at):
        self.events.append(deepcopy(event))

    def begin_dispatch(self, command, at):
        self.begun.append(command)
        return {'dispatchPermit': {'testOnly': True}}

    def record_transport_result(self, *args):
        pass


def command():
    return {'kind': 'ORDER', 'side': 'SELL', 'symbol': '8729.T',
            'account': '一般', 'quantity': 100, 'intentId': 'sell-intent',
            'commandId': 'sell-command', 'commandSha256': 'a' * 64,
            'rssOrderId': 999}


def holding(code='8729', qty=100, account='一般'):
    return {'symbol': code, 'quantity': qty, 'account': account}


def external_order(code='8729', side='売付', status='約定', filled=100):
    return {'symbol': code, 'account': '一般', 'side': side,
            'orderNumber': 'manual-1', 'quantity': 100,
            'filledQty': filled, 'status': status}


def normalized(positions=None, orders=None):
    return {'positions': [holding()] if positions is None else positions,
            'orders': [] if orders is None else orders,
            'captureCompletedAt': NOW, 'snapshotSha256': 'd' * 64,
            'buyingPower': 100000, 'idRows': [], 'executions': []}


def subject(cls=Subject):
    s = cls()
    s.book = FakeBook()
    s.session = DAY
    s.config = {'evidenceMode': 'BROKER_OBSERVATION', 'ledger': {'account': '一般', 'externalSymbols': []},
                'transport': {'mode': 'DISABLED'}}
    s.source = normalized()
    s.source_error = None
    s.clock = lambda: NOW
    s._fees = lambda: {}
    s.halts = []
    s.halt_entry = lambda why, at: s.halts.append(why)
    s.summary = lambda at: {'testOnly': True}
    s.root = Path('/not-used-transport-directory')
    s.transports = []
    s.refreshes = []

    def refresh(at):
        s.refreshes.append(at)
        return True

    def transport(packet):
        s.transports.append(packet)
        c = packet['command']
        return {'schemaId': 'ARK_NO11_MSII_TRANSPORT_RESULT_V1',
                'commandId': c['commandId'], 'commandSha256': c['commandSha256'],
                'rssOrderId': c['rssOrderId'], 'status': 'NOT_SENT',
                'dispatchAttempted': False}

    s.observe_file = refresh
    s._transport = transport
    return s


def ingest(s, data):
    # The actual normalize/attribution algorithms are tested elsewhere. This
    # fixture is their normalized output; execute the real ownership code.
    s.bridge = lambda request: deepcopy(data)
    envelope = {'schemaId': 'ARK_NO11_ACCOUNT_OBSERVATION_ENVELOPE_V1',
                'status': 'OBSERVED', 'readOnly': True, 'productionReady': False,
                'orderTransmission': False, 'snapshot': {}, 'brokerObservation': {}}
    with patch.object(attribution, 'inspect_source', return_value={'latchedIssues': []}):
        s.observe_envelope(envelope, NOW)


class ExistingProtection(unittest.TestCase):
    def test_unrelated_manual_holding_does_not_enter_ark_ledger(self):
        s = subject()
        ingest(s, normalized(positions=[holding(), holding('408A')]))
        self.assertEqual(s.book.checkpoints['broker.externalSymbols'], ['408A.T'])
        self.assertEqual(list(s.book.state['positions']), ['ark-entry'])
        s._sell_safe(s.book.state['orders']['sell-intent'], NOW)

    def test_manual_full_sale_blocks_exit(self):
        s = subject()
        ingest(s, normalized(positions=[], orders=[external_order()]))
        with self.assertRaisesRegex(ValueError, 'PERSONAL_POSITION_CONFLICT'):
            s._sell_safe(s.book.state['orders']['sell-intent'], NOW)

    def test_zero_holding_blocks_even_without_manual_order_row(self):
        s = subject()
        s.source['positions'] = []
        with self.assertRaisesRegex(ValueError, 'BROKER_HOLDINGS_NOT_CONFIRMED'):
            s._sell_safe(s.book.state['orders']['sell-intent'], NOW)

    def test_partial_manual_sale_never_rounds_up_or_sells_original_quantity(self):
        s = subject()
        s.source['positions'] = [holding(qty=50)]
        with self.assertRaisesRegex(ValueError, 'BROKER_HOLDINGS_NOT_CONFIRMED'):
            s._sell_safe(s.book.state['orders']['sell-intent'], NOW)

    def test_same_symbol_manual_rebuy_cannot_recreate_ark_ownership(self):
        s = subject()
        # The sell and repurchase happen between polls: quantity looks unchanged.
        ingest(s, normalized(orders=[external_order()]))
        ingest(s, normalized())
        self.assertIn('8729.T', s.book.checkpoints['broker.externalSymbols'])
        with self.assertRaisesRegex(ValueError, 'PERSONAL_POSITION_CONFLICT'):
            s._sell_safe(s.book.state['orders']['sell-intent'], NOW)

    def test_manual_additional_buy_not_sold_as_ark_shares(self):
        s = subject()
        ingest(s, normalized(positions=[holding(qty=200)], orders=[external_order(side='買付')]))
        self.assertEqual(s.book.state['positions']['ark-entry']['quantity'], 100)
        with self.assertRaisesRegex(ValueError, 'PERSONAL_POSITION_CONFLICT'):
            s._sell_safe(s.book.state['orders']['sell-intent'], NOW)

    def test_external_pending_sell_reservation_blocks(self):
        s = subject()
        s.source['orders'] = [external_order(status='執行中', filled=0)]
        with self.assertRaisesRegex(ValueError, 'EXTERNAL_SELL_RESERVATION'):
            s._sell_safe(s.book.state['orders']['sell-intent'], NOW)

    def test_other_account_holding_cannot_cover_exit(self):
        s = subject()
        s.source['positions'] = [holding(account='特定')]
        with self.assertRaisesRegex(ValueError, 'BROKER_HOLDINGS_NOT_CONFIRMED'):
            s._sell_safe(s.book.state['orders']['sell-intent'], NOW)

    def test_stale_holdings_fail_closed(self):
        s = subject()
        s.source['captureCompletedAt'] = DAY + 'T09:59:00.000+09:00'
        with self.assertRaisesRegex(ValueError, 'CURRENT_HOLDINGS_REQUIRED'):
            s._sell_safe(s.book.state['orders']['sell-intent'], NOW)


class DispatchRecheck(unittest.TestCase):
    def test_original_boundary_did_not_refresh_after_preparation(self):
        s = subject(OldSubject)
        s.observe_file = lambda at: self.fail('original unexpectedly refreshed')
        s._dispatch(command(), NOW)
        self.assertEqual(len(s.begun if hasattr(s, 'begun') else s.book.begun), 1)
        self.assertEqual(len(s.transports), 1)

    def test_manual_sale_between_prepare_and_send_blocks_before_permit(self):
        s = subject()
        s._sell_safe(s.book.state['orders']['sell-intent'], NOW)
        def changed(at):
            s.source['positions'] = []
            return True
        s.observe_file = changed
        with self.assertRaisesRegex(ValueError, 'BROKER_HOLDINGS_NOT_CONFIRMED'):
            s._dispatch(command(), NOW)
        self.assertEqual(s.book.begun, [])
        self.assertEqual(s.transports, [])

    def test_manual_rebuy_after_prepare_still_blocked(self):
        s = subject()
        def changed(at):
            ingest(s, normalized(orders=[external_order()]))
            return True
        s.observe_file = changed
        with self.assertRaisesRegex(ValueError, 'PERSONAL_POSITION_CONFLICT'):
            s._dispatch(command(), NOW)
        self.assertEqual(s.book.begun, [])

    def test_manual_only_holding_never_gets_dispatch_permit(self):
        s = subject()
        s.book.state['positions'] = {}
        with self.assertRaisesRegex(ValueError, 'EXIT_NOT_REMAINING_ARK_OWNED'):
            s._dispatch(command(), NOW)
        self.assertEqual(s.book.begun, [])

    def test_ledger_quantity_reduction_blocks_prepared_oversell(self):
        s = subject()
        s.book.state['positions']['ark-entry']['quantity'] = 50
        with self.assertRaisesRegex(ValueError, 'EXIT_NOT_REMAINING_ARK_OWNED'):
            s._dispatch(command(), NOW)
        self.assertEqual(s.transports, [])

    def test_unregistered_command_cannot_borrow_a_manual_holding(self):
        s = subject()
        c = command()
        c['commandId'] = 'unregistered'
        with self.assertRaisesRegex(ValueError, 'EXIT_RECORDED_ORDER_REQUIRED'):
            s._dispatch(c, NOW)
        self.assertEqual(s.transports, [])

    def test_failed_refresh_never_falls_back_to_old_success(self):
        s = subject()
        s.observe_file = lambda at: False
        with self.assertRaisesRegex(ValueError, 'EXIT_FRESH_BROKER_OBSERVATION_REQUIRED'):
            s._dispatch(command(), NOW)
        self.assertEqual(s.book.begun, [])

    def test_clean_owned_exit_reaches_mock_sink_once(self):
        s = subject()
        s._dispatch(command(), NOW)
        self.assertEqual(s.refreshes, [NOW])
        self.assertEqual(len(s.book.begun), 1)
        self.assertEqual(len(s.transports), 1)

    def test_cancellation_is_not_blocked_by_missing_holdings(self):
        s = subject()
        s.source['positions'] = []
        c = command()
        c['kind'] = 'CANCEL'
        self.assertEqual(s._exit_ownership_before_dispatch(c, NOW), NOW)
        self.assertEqual(s.refreshes, [])

    def test_buy_behavior_not_changed_by_sell_guard(self):
        s = subject()
        c = command()
        c['side'] = 'BUY'
        self.assertEqual(s._exit_ownership_before_dispatch(c, NOW), NOW)
        self.assertEqual(s.refreshes, [])

    def test_offline_mode_never_opens_live_observation_file(self):
        s = subject()
        s.config['evidenceMode'] = 'OFFLINE_REPLAY'
        s.observe_file = lambda at: self.fail('offline must not open live source')
        self.assertEqual(s._exit_ownership_before_dispatch(command(), NOW), NOW)


class PersistenceAndInstaller(unittest.TestCase):
    def test_actual_sqlite_manual_exclusion_survives_restart_without_adoption(self):
        config = {'schemaId': ledger.CONFIG_SCHEMA, 'sessionDate': DAY, 'account': '一般',
                  'allocatedCashJpy': '100000', 'externalSymbols': [], 'maxSymbols': 3,
                  'lotSize': 100, 'evidenceMode': 'OFFLINE_REPLAY',
                  'productionReady': False, 'orderTransmission': False}
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / 'ledger.sqlite'
            book = ledger.BrokerExecutionLedger(path, config)
            try:
                book.checkpoint_source('broker.externalSymbols', ['8729.T'], NOW)
                event = {'schemaId': ledger.ACCOUNT_SCHEMA, 'eventId': '1' * 64,
                         'sessionDate': DAY, 'account': '一般', 'knownAtJst': NOW,
                         'buyingPowerJpy': '100000', 'externalSymbols': ['8729.T'],
                         'evidenceMode': 'OFFLINE_REPLAY', 'sourceSnapshotSha256': '2' * 64}
                book.observe_account(event, NOW)
                self.assertEqual(book.snapshot(NOW)['positions'], {})
            finally:
                book.close()
            book = ledger.BrokerExecutionLedger(path, config)
            try:
                self.assertEqual(book.source_checkpoint('broker.externalSymbols'), ['8729.T'])
                self.assertEqual(book.snapshot(NOW)['positions'], {})
            finally:
                book.close()

    def test_patch_is_idempotent(self):
        self.assertEqual(installer.patch_text(PATCHED), PATCHED)

    def test_patch_refuses_unreviewed_source_change(self):
        with self.assertRaisesRegex(ValueError, 'PINNED_SOURCE_MISMATCH'):
            installer.patch_text(ORIGINAL + '\n# unreviewed\n')

    def test_staging_never_overwrites_original_or_existing_output(self):
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / 'original.py'
            dest = Path(td) / 'new.py'
            src.write_text(ORIGINAL, encoding='utf-8')
            before = src.read_bytes()
            installer.stage(src, dest)
            self.assertEqual(src.read_bytes(), before)
            self.assertEqual(dest.read_text(encoding='utf-8'), PATCHED)
            with self.assertRaisesRegex(ValueError, 'NEW_ISOLATED_OUTPUT_REQUIRED'):
                installer.stage(src, dest)
            with self.assertRaisesRegex(ValueError, 'NEW_ISOLATED_OUTPUT_REQUIRED'):
                installer.stage(src, src)


if __name__ == '__main__':
    unittest.main(verbosity=2)
