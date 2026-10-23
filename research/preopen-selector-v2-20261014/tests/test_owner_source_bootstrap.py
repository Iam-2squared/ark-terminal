"""Inspection/transport boundaries; no originals, market grants, or fits."""
import gzip
import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('v2_source_restore', ROOT / 'tools/restore_mode_b_sources.py')
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class OwnerSourceBootstrap(unittest.TestCase):
    def source(self, data):
        return {'bytes': len(data), 'source_sha256': hashlib.sha256(data).hexdigest(),
                'original_git_blob': hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest(),
                'inspection_dates': ['2030-01-02']}

    def test_poison_prices_are_never_converted_and_other_dates_skip_identity(self):
        data = gzip.compress(b'Date,Code,O\n2030-01-02,00010,NOT_A_PRICE\n2099-01-01,,POISON\n')
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'saved.gz'; path.write_bytes(data)
            result = module.metadata_scan(path, self.source(data), 10000)
        self.assertEqual(result['date_record_counts'], {'2030-01-02': 1})
        self.assertEqual(result['other_date_records_skipped_before_identity'], 1)
        self.assertEqual(result['numeric_records_parsed'], 0)
        self.assertFalse(result['source_profile_adopted'])

    def test_hash_is_checked_before_decompression(self):
        data = b'not a gzip file'
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'saved.gz'; path.write_bytes(data + b'tamper')
            with self.assertRaisesRegex(module.V2Error, 'SIZE_MISMATCH'):
                module.metadata_scan(path, self.source(data), 10000)

    def test_decompression_limit_and_duplicate_identity_are_rejected(self):
        for text, limit, error in [
            (b'Date,Code\n' + b'2030-01-02,00010\n' * 2000, 100, 'SIZE_LIMIT'),
            (b'Date,Code\n2030-01-02,00010\n2030-01-02,00010\n', 10000, 'DUPLICATE_DATED_IDENTITY'),
        ]:
            data = gzip.compress(text)
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / 'saved.gz'; path.write_bytes(data)
                with self.assertRaisesRegex(module.V2Error, error):
                    module.metadata_scan(path, self.source(data), limit)

    def test_evaluation_purpose_refused_before_source_open(self):
        scope = {'schema': 'ARK_V2_MODE_B_SOURCE_SCOPE_DRAFT_V1', 'validation_final_teachers_included': False,
                 'source_objects': [{'original_git_blob': 'a', 'bytes': 1,
                                     'requested_dates_by_purpose': {'FINAL_TEACHER': ['2030-01-02']}}]}
        tree = {'truncated': False, 'tree': [{'type': 'blob', 'path': 'raw/saved.gz', 'sha': 'a', 'size': 1}]}
        with self.assertRaisesRegex(module.V2Error, 'EVALUATION_PURPOSE'):
            module.selected_objects(scope, tree)

    def test_source_symlink_and_escaping_path_are_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'source'; root.mkdir()
            (root / 'linked').symlink_to(Path(directory))
            with self.assertRaisesRegex(module.V2Error, 'SYMLINK'):
                module.source_path(root, 'linked/object.gz')
            with self.assertRaisesRegex(module.V2Error, 'PATH_ESCAPE'):
                module.source_path(root, '../object.gz')


if __name__ == '__main__': unittest.main()
