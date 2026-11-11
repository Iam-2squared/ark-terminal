#!/usr/bin/env python3
"""Apply real fixes to installed ARK native launch and RSS data collectors.

The local WHITE OneClick .ps1 is not opened for writing. A single durable
transaction journal holds exact before/after bytes for every modified native
file. After a crash, a new apply verifies local bytes before rollback/replay.
No order, strategy, model, trade marker or broker ledger is modified.
"""
from __future__ import annotations

import argparse
import base64
import os
from pathlib import Path
import subprocess
import sys
import tempfile

import no11_nightly_resume as n
import no11_update_path as patch
import install_no11_week_resilience as original

KINDS = tuple(patch.FILES)

def need(condition, code):
    if not condition:
        raise ValueError('NO11_LAUNCHER_UPDATE_' + code)

def paths_for(store):
    binding = n.read(n.safe(store / 'automatic-inputs.json'))
    need(binding.get('schemaId') == 'ARK_NO11_AUTOMATIC_LAUNCHER_BINDING_V1'
         and binding.get('orderTransmission') is False
         and type(binding.get('nightlyResumeTool')) is str
         and type(binding.get('nightlyResumeToolSha256')) is str,
         'RESUMABLE_NIGHTLY_MUST_BE_INSTALLED_FIRST')
    tool = n.safe(binding['nightlyResumeTool'])
    need(n.digest(tool.read_bytes()) == binding['nightlyResumeToolSha256'],
         'RESUMABLE_NIGHTLY_SOURCE_CHANGED')
    engine = n.safe(binding['engine'], True)
    files = {}
    for kind, relative in patch.FILES.items():
        if relative.startswith('engine/'):
            path = engine / relative[len('engine/'):]
        else:
            path = store / relative
        files[kind] = n.safe(path)
    # The operator's custom WHITE OneClick is independent and NEVER patched.
    ui = n.safe(store / 'oneclick/Start-No11OneClick.ps1')
    return files, ui

def quiet():
    original.quiet()

def atomic_replace(path, before, after):
    original.replace(path, before, after)

def decode_entries(j, paths):
    need(j.get('kind') == 'WEEKLY_DAILY_MAX47_LAUNCHER_UPDATE'
         and set(j.get('entries', {})) == set(KINDS)
         and j.get('orderTransmission') is False, 'JOURNAL_CONTRACT')
    entries = {}
    for kind, row in j['entries'].items():
        need(row.get('path') == str(paths[kind]), 'JOURNAL_PATH_CHANGED')
        b = base64.b64decode(row['before'], validate=True)
        a = base64.b64decode(row['after'], validate=True)
        need(n.digest(b) == row.get('beforeSha256')
             and n.digest(a) == row.get('afterSha256'), 'JOURNAL_SOURCE_CHECKSUM')
        entries[kind] = (b, a)
    return entries

def recover(store, journal, do_apply=False):
    if not journal.exists():
        return False
    paths, ui = paths_for(store)
    j = n.checkpoint(journal)
    entries = decode_entries(j, paths)
    need(n.digest(ui.read_bytes()) == j.get('whiteUiSha256'),
         'WHITE_UI_CHANGED_OUTSIDE_INSTALL')
    for kind, path in paths.items():
        b,a = entries[kind]
        need(path.read_bytes() in (b,a), 'UNEXPECTED_EXTERNAL_SOURCE_CHANGE')
    if j.get('phase') == 'COMPLETE':
        need(all(paths[k].read_bytes() == pair[1] for k,pair in entries.items()),
             'COMPLETE_FILES_MODIFIED')
        return True
    need(j.get('phase') in ('PREPARED', 'ROLLED_BACK'), 'JOURNAL_PHASE_INVALID')
    need(do_apply, 'INTERRUPTED_INSTALL_NEEDS_APPLY')
    quiet()
    for kind in reversed(KINDS):
        before, after = entries[kind]
        current = paths[kind].read_bytes()
        if current == after and current != before:
            atomic_replace(paths[kind], after, before)
    j['phase'] = 'ROLLED_BACK'
    n.atomic(journal, j)
    return False

def plan(store):
    paths, ui = paths_for(store)
    # Never change a runnable collector while a previous instance may live.
    before = {k: path.read_bytes() for k,path in paths.items()}
    after = {}
    failed = []
    for kind in KINDS:
        try:
            after[kind] = patch.transform(kind, before[kind])
            print('NO11_UPDATE_SOURCE=' + kind.upper() + '|READY', flush=True)
        except ValueError as error:
            failed.append(kind)
            print('NO11_UPDATE_FAILED_FILE=' + paths[kind].name, flush=True)
            print('NO11_UPDATE_FAILED_KIND=' + kind.upper(), flush=True)
            print('NO11_UPDATE_SOURCE_SHA256=' + n.digest(before[kind]), flush=True)
            if isinstance(error, patch.SourceAnchorChanged):
                print('NO11_UPDATE_ANCHOR_ID=' + error.anchor_id, flush=True)
                print('NO11_UPDATE_ANCHOR_MATCHES=' + str(error.match_count), flush=True)
                # Public EXPECTED source fragment only: never print private
                # workbook paths, local source contents, keys or account data.
                label = error.anchor.strip().splitlines()[0][:180]
                print('NO11_UPDATE_EXPECTED_ANCHOR=' + label, flush=True)
            reason = str(error)
            if not reason.startswith('NO11_'):
                reason = 'NO11_UPDATE_SOURCE_UNRECOGNIZED'
            print('NO11_UPDATE_SOURCE_REASON=' + reason, flush=True)
    if failed:
        raise ValueError('NO11_UPDATE_PATH_' + '_'.join(k.upper() for k in failed) + '_SOURCE_ANCHOR_CHANGED')
    # Retain exact custom UI bytes, even if a generated baseline differs.
    white_sha = n.digest(ui.read_bytes())
    # A genuine codeIdentity change creates a NEW as-of-scoped Friday plan.
    # The old code and old original receipts are kept byte-for-byte in journal.
    need('ARK_NO11_AFTERCLOSE_CONFIGURED_THIRD_BOOK_V1' in
         before['native'].decode('utf-8-sig'), 'INSTALLED_THREE_BOOK_FIX_MISSING')
    need('ARK_NO11_AFTERCLOSE_CONFIGURED_THIRD_BOOK_V1' in
         before['daily'].decode('utf-8-sig'), 'INSTALLED_DAILY_THREE_BOOK_FIX_MISSING')
    need('ARK_NO11_AFTERCLOSE_CONFIGURED_THIRD_BOOK_V1' in
         before['minutes'].decode('utf-8-sig'), 'INSTALLED_MINUTE_THREE_BOOK_FIX_MISSING')
    return paths, before, after, white_sha

def install(store, *, do_apply=False, _test=False):
    store = n.safe(store, True)
    with n.exclusive(store / 'launcher-max47-install.lock'):
        journal = store / 'launcher-max47-install-transaction.json'
        if do_apply and not _test:
            quiet()
        if recover(store, journal, do_apply=do_apply):
            return 'ALREADY_APPLIED'
        paths, before, after, ui_sha = plan(store)
        need(any(before[k] != after[k] for k in KINDS), 'NO_CHANGE')
        if not do_apply:
            return 'READY'
        if not _test:
            # Windows PowerShell 5.1 AST parser checks the *candidate* code,
            # never Excel. Source line endings and BOM survive transformation.
            with tempfile.TemporaryDirectory(prefix='no11-max47-') as folder:
                candidates = []
                for k in KINDS:
                    dest = Path(folder) / (k + ('.py' if k == 'status' else '.ps1'))
                    dest.write_bytes(after[k])
                    if k == 'status':
                        compile(after[k].decode('utf-8-sig'), str(dest), 'exec')
                    else:
                        candidates.append(dest)
                original.parse_powershell(candidates)
            quiet()
        else:
            compile(after['status'].decode('utf-8-sig'), '<status>', 'exec')
        # After staging, ensure no installed source mutated since inspection.
        need(all(paths[k].read_bytes() == before[k] for k in KINDS),
             'CONCURRENT_SOURCE_EDIT')
        need(n.digest((store / 'oneclick/Start-No11OneClick.ps1').read_bytes()) == ui_sha,
             'WHITE_UI_CHANGED')
        entries = {
            k: {'path': str(paths[k]),
                'before': base64.b64encode(before[k]).decode('ascii'),
                'after': base64.b64encode(after[k]).decode('ascii'),
                'beforeSha256': n.digest(before[k]),
                'afterSha256': n.digest(after[k])}
            for k in KINDS
        }
        j = {'schemaId': n.SCHEMA, 'kind':'WEEKLY_DAILY_MAX47_LAUNCHER_UPDATE',
             'phase':'PREPARED', 'entries': entries, 'whiteUiSha256':ui_sha,
             'orderTransmission':False}
        n.atomic(journal, j)
        try:
            for k in KINDS:
                if before[k] != after[k]:
                    atomic_replace(paths[k], before[k], after[k])
            need(all(paths[k].read_bytes() == after[k] for k in KINDS),
                 'POSTINSTALL_READBACK')
            need(n.digest((store / 'oneclick/Start-No11OneClick.ps1').read_bytes()) == ui_sha,
                 'WHITE_UI_NOT_PRESERVED')
            j['phase'] = 'COMPLETE'
            n.atomic(journal, j)
        except Exception:
            # We can only rollback sources whose bytes are still exact known
            # candidates; never roll back unrelated user edits.
            if _test:
                # recover calls quiet; mock tests can supply a no-op implementation.
                pass
            recover(store, journal, do_apply=True)
            raise
        return 'PASS'

def main(argv=None):
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--store',type=Path,required=True)
    cli.add_argument('--apply',action='store_true')
    opts = cli.parse_args(argv)
    try:
        need(os.name == 'nt', 'WINDOWS_ONLY')
        result = install(opts.store, do_apply=opts.apply)
        print('NO11_LAUNCHER_MAX47_UPDATE=' + result)
        print('WEEKLY_RSS_CONCURRENCY=UP_TO_47')
        print('DAILY_RSS_CONCURRENCY=UP_TO_47')
        print('PREVIOUS_1M_RSS_CONCURRENCY=UP_TO_47')
        print('WEEKEND_ONECLICK_UPDATE=ENABLED')
        print('DATA_JOB_RESUME=REUSES_ORIGINAL_WEEKLY_MARKER')
    except Exception as e:
        import re
        msg = str(e)
        if not re.fullmatch(r'NO11_[A-Z0-9_]+', msg):
            msg = 'NO11_LAUNCHER_UPDATE_SOURCE_OR_RUNTIME_ERROR'
        print('NO11_LAUNCHER_MAX47_UPDATE=BLOCKED|' + msg)
        raise SystemExit(2)
    finally:
        print('WHITE_UI_CHANGED=False')
        print('TRADE_LAUNCHED=False')
        print('ORDER_TRANSMISSION=False')

if __name__ == '__main__':
    main()
