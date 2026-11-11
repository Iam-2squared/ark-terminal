"""Additional display-only invariants; no broker or process control."""
from contextlib import redirect_stdout
from copy import deepcopy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import no11_oneclick_display_v2 as display
import no11_nightly_resume as n
from test_no11_oneclick_display_v2 import presentation


class DisplayInvariantTests(unittest.TestCase):
    def test_entry_halt_is_not_hidden_by_registered_or_reserved_state(self):
        state = {'mode': 'OPERATOR_CHECK', 'reason': 'ALREADY_STARTED_TODAY',
                 'canRequestTrade': False, 'runHealth': {'entryHalted': True,
                 'haltReasonCodes': ['NO11_BROKER_SOURCE_UNAVAILABLE']}}
        original = deepcopy(state)
        for clock in ('08:45:00', '09:01:00', '14:00:00', '20:00:00'):
            with self.subTest(clock=clock):
                out = presentation(clock, state=state, run={'state': 'REGISTERED'})
                self.assertIn('ENTRY HALTED', out['trading'])
                self.assertIn('NO11_BROKER_SOURCE_UNAVAILABLE', out['details'])
                self.assertFalse(out['liveVerified'])
                self.assertEqual(state, original)

    def test_halt_reason_does_not_leak_arbitrary_private_text(self):
        out = presentation(state={'runHealth': {'entryHalted': True,
            'haltReasonCodes': ['PRIVATE_ACCOUNT_123', 'password=SECRET', 'NO11_SERVICE_HALT']}})
        self.assertIn('NO11_SERVICE_HALT', out['details'])
        self.assertNotIn('PRIVATE', out['details'])
        self.assertNotIn('SECRET', out['details'])

    def test_unexpected_cli_exception_is_fail_closed_and_redacted(self):
        buffer = io.StringIO()
        with patch.object(display, 'inspect', side_effect=RuntimeError('PRIVATE_PATH_SECRET')), redirect_stdout(buffer):
            code = display.main(['--settings', 'synthetic.json', '--binding', 'synthetic.json'])
        self.assertEqual(code, 2)
        self.assertNotIn('PRIVATE', buffer.getvalue())
        result = json.loads(buffer.getvalue())
        self.assertFalse(result['canRequestTrade'])
        self.assertFalse(result['canRunNightly'])

    def test_repair_label_requires_receipt_hash_and_exact_current_targets(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            engine = root / 'engine'
            tools = engine / 'tools'
            tools.mkdir(parents=True)
            targets = {'BOOTSTRAP': 'no11_received_session_bootstrap.py', 'FUNDING': 'no11_rss_buying_power.py'}
            entries = {}
            for key, name in targets.items():
                path = tools / name
                path.write_bytes(b'# synthetic source\n')
                entries[key] = {'path': str(path), 'afterSha256': n.digest(path.read_bytes())}
            record = {'schemaId': n.SCHEMA, 'kind': 'ARK_NO11_AFTERCLOSE_SOURCE_REPAIR_V1',
                      'phase': 'COMPLETE', 'entries': entries, 'orderTransmission': False}
            journal = root / 'afterclose-source-repair-v1-install.json'
            n.atomic(journal, record)
            binding = {'engine': str(engine)}
            self.assertEqual(display.repair_evidence(root, binding), 'APPLIED')
            (tools / targets['FUNDING']).write_bytes(b'# unexpected replacement\n')
            self.assertEqual(display.repair_evidence(root, binding), 'UNVERIFIED')
            record['phase'] = 'PREPARED'
            n.atomic(journal, record)
            self.assertEqual(display.repair_evidence(root, binding), 'INCOMPLETE')
            journal.write_text('{"phase":"COMPLETE"}')
            self.assertEqual(display.repair_evidence(root, binding), 'UNVERIFIED')


if __name__ == '__main__':
    unittest.main(verbosity=2)
