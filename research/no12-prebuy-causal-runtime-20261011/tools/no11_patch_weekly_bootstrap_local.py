#!/usr/bin/env python3
"""Patch only five vetted weekly-Shadow bootstrap anchors in a local-only file.

The user's modified original is never overwritten by this tool. It emits a
staged candidate and insists that all expected old anchors appear exactly once.
Unrelated local text and original line-endings are preserved. No models,
market data, network, Excel, trading or security-review operations.
"""
from __future__ import annotations

import argparse
import ast
from pathlib import Path
import re
import sys

BEFORE = [
    """            'brokerExecutionConfig', 'orderIdWorkbookPath'}""",
    """    c = deepcopy(obj)
    for name, low, high, default in""",
    """    for key in ('datedMaster', 'previousContext', 'pinsFile', 'shadowAccountConfig',
                'brokerExecutionConfig', 'orderIdWorkbookPath'):""",
    """    if 'orderIdWorkbookPath' in c:
        need(Path(c['orderIdWorkbookPath']).suffix.lower() == '.xlsx', 'ORDER_ID_WORKBOOK_TYPE')""",
    """def export_scope(config):
    run = config['dailyRun']""",
]
AFTER = [
    """            'brokerExecutionConfig', 'orderIdWorkbookPath',
            'precomputedChartReceipt', 'precomputedG1Mask', 'weeklySourceRun'}""",
    """    # Accept a complete, independently verified WEEKLY G1/Chart50 input trio.
    # No stale full-market fallback, no hidden extra pinned symbols.
    weekly_keys = {'precomputedChartReceipt', 'precomputedG1Mask', 'weeklySourceRun'}
    weekly_supplied = weekly_keys & set(obj)
    need(not weekly_supplied or weekly_supplied == weekly_keys,
         'WEEKLY_SCOPE_ALL_THREE_REQUIRED')
    need(not weekly_supplied or 'pinsFile' not in obj,
         'WEEKLY_SCOPE_ALREADY_PINNED_NO_SECOND_PINS')
    c = deepcopy(obj)
    for name, low, high, default in""",
    """    for key in ('datedMaster', 'previousContext', 'pinsFile', 'shadowAccountConfig',
                'brokerExecutionConfig', 'orderIdWorkbookPath',
                'precomputedChartReceipt', 'precomputedG1Mask'):""",
    """    if weekly_supplied:
        c['weeklySourceRun'] = str(private(c['weeklySourceRun'], True))
        run = Path(c['dailyRun'])
        need(Path(c['precomputedChartReceipt']).parent == run and
             Path(c['precomputedG1Mask']).parent == run and
             Path(c['weeklySourceRun']) != run,
             'WEEKLY_SCOPE_RECEIPTS_AND_DAILY_RUN_MUST_MATCH')
    if 'orderIdWorkbookPath' in c:
        need(Path(c['orderIdWorkbookPath']).suffix.lower() == '.xlsx', 'ORDER_ID_WORKBOOK_TYPE')""",
    """def export_scope(config):
    if 'precomputedChartReceipt' in config:
        # Verify original weekly-4328 hash, fresh 429-pool D100 observations,
        # Chart50 receipt, session and private source hashes before use.
        output = command_output(['node', str(HERE / 'no11_verified_weekly_shadow_scope.mjs'),
                                 '--run-dir', config['dailyRun'],
                                 '--weekly-source-run', config['weeklySourceRun'],
                                 '--mask', config['precomputedG1Mask'],
                                 '--chart', config['precomputedChartReceipt'],
                                 '--session', config['sessionDate']])
        need('NO11_WEEKLY_SHADOW_SCOPE=PASS_OBSERVED_NOT_EXTERNALLY_REVIEWED' in output,
             'WEEKLY_SCOPE_G1_CHART_NOT_VERIFIED')
        return (private(config['precomputedChartReceipt']),
                private(config['precomputedG1Mask']))
    run = config['dailyRun']""",
]
assert len(BEFORE) == len(AFTER) == 5


def patch_text(text: str) -> tuple[str, bool]:
    """Return (patched, changed) or fail; refuse partial/mismatched weekly wiring."""
    if 'precomputedChartReceipt' in text:
        if all(marker in text for marker in (
            "weekly_supplied = weekly_keys & set(obj)",
            "'precomputedChartReceipt', 'precomputedG1Mask', 'weeklySourceRun'",
            "def export_scope(config):\n    if 'precomputedChartReceipt' in config:",
            "NO11_WEEKLY_SHADOW_SCOPE=PASS_OBSERVED_NOT_EXTERNALLY_REVIEWED",
            "WEEKLY_SCOPE_RECEIPTS_AND_DAILY_RUN_MUST_MATCH",
        )):
            # One earlier integration can already exist with private local changes.
            ast.parse(text)
            return text, False
        raise ValueError('NO11_BOOTSTRAP_PATCH_PARTIAL_WEEKLY_WIRING')
    amended = text
    for old, new in zip(BEFORE, AFTER):
        count = amended.count(old)
        if count != 1:
            raise ValueError('NO11_BOOTSTRAP_PATCH_ANCHOR_MISMATCH')
        amended = amended.replace(old, new, 1)
    if text == amended:
        raise ValueError('NO11_BOOTSTRAP_PATCH_UNCHANGED')
    ast.parse(amended)
    # Explicitly preserve the read-only production contract.
    for critical in ("obj['orderTransmission'] is False",
                     "'CONFIG_NOT_READONLY'",
                     "'EXACTLY_ONE_PREVIOUS_SOURCE_REQUIRED'",
                     "validate_readonly_broker_config("):
        if critical not in amended:
            raise ValueError('NO11_BOOTSTRAP_PATCH_READONLY_GUARD_LOST')
    return amended, True


def patch_bytes(source: bytes) -> tuple[bytes, bool]:
    prefix = b'\xef\xbb\xbf' if source.startswith(b'\xef\xbb\xbf') else b''
    body = source[len(prefix):]
    raw = body.decode('utf-8', errors='strict')
    crlf = '\r\n' in raw
    if crlf and '\n' in raw.replace('\r\n', ''):
        raise ValueError('NO11_BOOTSTRAP_PATCH_MIXED_NEWLINES')
    normalized = raw.replace('\r\n', '\n')
    updated, changed = patch_text(normalized)
    output = updated.replace('\n', '\r\n') if crlf else updated
    return prefix + output.encode('utf-8'), changed


def run(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--staged-output', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        original, stage = args.input, args.staged_output
        if (not original.is_absolute() or not stage.is_absolute() or
                original.resolve() == stage.resolve() or
                original.name != 'no11_received_session_bootstrap.py' or
                stage.exists() or not original.is_file() or
                any(p.is_symlink() for p in (original, *original.parents,
                                             stage, *stage.parents))):
            raise ValueError('NO11_BOOTSTRAP_PATCH_SOURCE_PATH')
        result, changed = patch_bytes(original.read_bytes())
        with stage.open('xb') as stream:
            stream.write(result)
            stream.flush()
        print('NO11_BOOTSTRAP_PATCH_STAGED=' + str(stage))
        print('NO11_BOOTSTRAP_PATCH_MODE=' +
              ('FIVE_ANCHOR_LOCAL_PRESERVING' if changed else 'ALREADY_WIRED_NO_CHANGE'))
        print('NO11_BOOTSTRAP_PATCH_SOURCE_ORIGINAL_UNTOUCHED=True')
        print('ORDER_TRANSMISSION=False')
        return 0
    except (OSError, UnicodeError, ValueError, SyntaxError) as error:
        label = str(error)
        if not re.fullmatch('NO11_BOOTSTRAP_PATCH_[A-Z0-9_]+', label):
            label = 'NO11_BOOTSTRAP_PATCH_SOURCE_OR_PARSE_UNAVAILABLE'
        print('NO11_BOOTSTRAP_PATCH=BLOCKED|' + label)
        print('ORDER_TRANSMISSION=False')
        return 2


if __name__ == '__main__':
    sys.exit(run())
