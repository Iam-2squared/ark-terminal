"""Synthetic order fixtures with real SQLite durability; no real brokerage I/O."""
from pathlib import Path
from types import MethodType
import tempfile
import unittest

import test_rebuild as fixtures
import no11_broker_execution_ledger as ledger
import no11_broker_execution_service as service


class OwnershipPersistenceTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.DispatchTests('test_clean_ark_sell_reaches_boundary_once')
        self.fixture.setUp()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'ownership.sqlite'
        self.config = {'schemaId': ledger.CONFIG_SCHEMA, 'sessionDate': fixtures.DAY,
                       'account': '一般', 'allocatedCashJpy': '100000',
                       'externalSymbols': [], 'evidenceMode': 'OFFLINE_REPLAY'}
        self.store = ledger.BrokerExecutionLedger(self.path, self.config)
        self.addCleanup(lambda: self.store.close())
        self.fixture.subject.book.source_checkpoint = lambda key: self.store.source_checkpoint(key)
        self.fixture.subject.book.checkpoint_source = lambda key, value, at: self.store.checkpoint_source(key, value, at)
        self.fixture.subject.halt_entry = MethodType(service.BrokerExecution.halt_entry, self.fixture.subject)

    def mismatch(self, quantity):
        self.fixture.subject.source['positions'][0]['quantity'] = quantity
        with self.assertRaisesRegex(ValueError, 'EXIT_MIXED_OR_CHANGED_HOLDING'):
            self.fixture.dispatch()
        self.assertEqual(self.store.source_checkpoint('broker.externalSymbols'), ['7203.T'])
        self.assertIn('NO11_CLEAN_OWNERSHIP_MISMATCH', self.store.source_checkpoint('controller.entryHalt'))
        self.assertEqual((self.fixture.permits, self.fixture.sends), (0, 0))

    def test_observed_zero_then_rebuy_is_still_excluded(self):
        self.mismatch(0)
        self.fixture.subject.source['positions'][0]['quantity'] = 100
        self.fixture.blocked()

    def test_partial_manual_sale_then_rebuy_is_still_excluded(self):
        self.mismatch(50)
        self.fixture.subject.source['positions'][0]['quantity'] = 100
        self.fixture.blocked()

    def test_additional_manual_buy_then_sale_does_not_clear_exclusion(self):
        self.mismatch(200)
        self.fixture.subject.source['positions'][0]['quantity'] = 100
        self.fixture.blocked()

    def test_quantity_conflict_survives_actual_sqlite_reopen(self):
        self.mismatch(0)
        self.store.close()
        self.store = ledger.BrokerExecutionLedger(self.path, self.config)
        self.fixture.subject.source['positions'][0]['quantity'] = 100
        self.fixture.blocked()
        self.assertEqual(self.store.source_checkpoint('broker.externalSymbols'), ['7203.T'])
        # Real checkpoint writes must not create positions, fills or orders.
        actual = self.store.snapshot(fixtures.NOW)
        self.assertEqual(actual['positions'], {})
        self.assertEqual(actual['orders'], {})

    def test_existing_personal_exclusions_are_preserved(self):
        self.store.checkpoint_source('broker.externalSymbols', ['6501.T'], fixtures.NOW)
        self.fixture.subject.source['positions'][0]['quantity'] = 200
        with self.assertRaisesRegex(ValueError, 'EXIT_MIXED_OR_CHANGED_HOLDING'):
            self.fixture.dispatch()
        self.assertEqual(self.store.source_checkpoint('broker.externalSymbols'), ['6501.T', '7203.T'])

    def test_fresh_balanced_sell_does_not_create_a_conflict(self):
        self.fixture.dispatch()
        self.assertIsNone(self.store.source_checkpoint('broker.externalSymbols'))
        self.assertEqual((self.fixture.permits, self.fixture.sends), (1, 1))


if __name__ == '__main__':
    unittest.main(verbosity=2)
