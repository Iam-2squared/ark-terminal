"""Verify locked definition + synthetic tests. Never reads market datasets."""
from __future__ import annotations
import argparse
import hashlib
import io
import json
from pathlib import Path
import platform
import unittest
import reference as r
import test_reference as cases

ROOT = Path(__file__).resolve().parent


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_lock() -> dict:
    lock = json.loads((ROOT / 'source-lock.json').read_text(encoding='utf-8'))
    for name, expected in lock['sha256'].items():
        path = (ROOT / name).resolve()
        if path.parent != ROOT or digest(path) != expected:
            raise RuntimeError('SOURCE_LOCK_MISMATCH:' + name)
    return lock


def test_ids(suite):
    for test in suite:
        if isinstance(test, unittest.TestSuite):
            yield from test_ids(test)
        else:
            yield test.id()


def run(output: Path) -> dict:
    if output.exists():
        raise RuntimeError('OUTPUT_ALREADY_EXISTS_NO_OVERWRITE')
    lock = verify_lock()
    suite = unittest.defaultTestLoader.loadTestsFromModule(cases)
    names = list(test_ids(suite))
    log = io.StringIO()
    result = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
    if not result.wasSuccessful() or result.testsRun != len(names):
        raise RuntimeError(log.getvalue())
    # Direct fixture outputs retain price paths and rational exactness, NOT stocks.
    fixture_prices = {
        'SYNTHETIC_UP_STRUCTURE': [100,102,101,103,102,104],
        'SYNTHETIC_DOWN_REBOUND': [104,102,103,100,101],
        'SYNTHETIC_RECOVERY_COMPLETE': [103,102,100,101,103],
        'SYNTHETIC_STRUCTURE_BREAK': [100,102,101,103,102,100,100],
        'SYNTHETIC_EQUAL_CLOSE_CHOP': [100,101,99,101,100],
        'SYNTHETIC_RANGE_EXIT': [100,101,100,101,100]*6+[102]}
    snapshots = []
    for name, prices in fixture_prices.items():
        bs = cases.bars(prices)
        snapshots.append({'fixture': name, 'prices': prices,
                          'snapshot': r.snapshot(bs,cases.ENDS,bs[-1].end,r.q(1))})
    summary = {
        'version': r.VERSION, 'scope': 'SYNTHETIC_ONLY',
        'testsRun': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
        'testNames': names, 'python': platform.python_version(), 'sourceSHA256':lock['sha256'],
        'fixtures': len(snapshots), 'marketStateRowsGenerated':0,
        'marketDataRead':False, 'modelsFitted':0, 'thresholdSearch':False,
        'signalsEvaluated':False, 'entryTimingEvaluated':False,
        'providerRequests':0, 'protectedDataOpened':0, 'safety':r.SAFETY,
        'scientificStateAccuracyClaim':False,
        'status':'FROZEN_CANDIDATE_SYNTHETIC_PASS_HUMAN_REVIEW_REQUIRED'}
    output.mkdir(parents=True, exist_ok=False)
    (output/'summary.json').write_text(r.canonical(summary),encoding='utf-8')
    (output/'synthetic-snapshots.json').write_text(r.canonical(snapshots),encoding='utf-8')
    manifest = {p.name:digest(p) for p in sorted(output.iterdir()) if p.is_file()}
    (output/'manifest.json').write_text(r.canonical(manifest),encoding='utf-8')
    return summary


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output',required=True,type=Path)
    args=ap.parse_args()
    z=run(args.output)
    print(json.dumps({k:z[k] for k in ('testsRun','failures','errors','fixtures','marketStateRowsGenerated','status')},ensure_ascii=False))
