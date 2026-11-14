"""Append-only/hash guards for CORE caching; no market data or model fitting."""
import os
from pathlib import Path
import tempfile
import unittest
from scripts.phase57_exit_core_cache_r35 import build


class CacheSafetyTests(unittest.TestCase):
    def test_existing_failure_evidence_is_never_replaced(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d, 'existing'); out.mkdir()
            failure = out / 'FAILURE.json'
            failure.write_bytes(b'ORIGINAL_FAILURE_EVIDENCE')
            with self.assertRaisesRegex(FileExistsError, 'APPEND_ONLY'):
                build(Path(d, 'absent-input'), Path(d, 'absent-contract'), out)
            self.assertEqual(failure.read_bytes(), b'ORIGINAL_FAILURE_EVIDENCE')
            self.assertEqual([p.name for p in out.iterdir()], ['FAILURE.json'])

    def test_invalid_contract_cannot_create_output(self):
        with tempfile.TemporaryDirectory() as d:
            contract = Path(d, 'invalid.json'); contract.write_text('{}')
            out = Path(d, 'output')
            with self.assertRaisesRegex(ValueError, 'CONTRACT_HASH'):
                build(Path(d, 'source'), contract, out)
            self.assertFalse(out.exists())

    def test_invalid_manifest_cannot_create_output(self):
        with tempfile.TemporaryDirectory() as d:
            source = Path(d, 'input'); source.mkdir()
            (source / 'manifest.json').write_text('{}')
            out = Path(d, 'output')
            with self.assertRaisesRegex(ValueError, 'MANIFEST_HASH'):
                build(source, Path(os.environ['R33_FIT_CONTRACT']), out)
            self.assertFalse(out.exists())


if __name__ == '__main__':
    unittest.main()
