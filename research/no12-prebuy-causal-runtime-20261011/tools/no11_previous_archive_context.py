#!/usr/bin/env python3
"""Existing RSS training-archive format -> existing previous-context format.

Offline source preparation only. No model fitting, account reads, Excel writes,
orders or network. Prefetch may run before the target session; session context
is emitted only on that session with an existing verified master. No flags or
historical receipt clocks are promoted to certified by this adapter.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

import no11_received_session_bootstrap as bootstrap
import no11_rss_state9_p1_runner as received

ROOT = bootstrap.ROOT
SCHEMA = 'ARK_NO11_PREVIOUS_ARCHIVE_STAGE_V1'
PROGRESS = 'ARK_NO11_RSS_TRAINING_CAPTURE_PROGRESS_V1'
ARCHIVE = 'ARK_NO11_RSS_TRAINING_SYMBOL_ARCHIVE_V1'
GOOD = 'OBSERVED_ARCHIVE_NOT_TRAINING_CERTIFIED'
INSTANT = re.compile(r'^20\d\d-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d{1,7})?\+09:00$')
MEMBER = re.compile(r'^[0-9]{5}-[0-9A-Z]{4}_T-1M\.json$')


def need(value, code):
    if not value:
        raise ValueError('NO11_PREVIOUS_ARCHIVE_' + code)


def now_jst():
    return datetime.now(timezone(timedelta(hours=9))).isoformat(timespec='milliseconds')


def instant(value):
    need(type(value) is str and INSTANT.fullmatch(value), 'CLOCK_INVALID')
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        raise ValueError('NO11_PREVIOUS_ARCHIVE_CLOCK_INVALID') from None


def scope(plan_file, mask_file):
    """Use the original calendar and chart-plan validator; do not re-rank."""
    plan_file, mask_file = bootstrap.private(plan_file), bootstrap.private(mask_file)
    plan, _ = bootstrap.load_json(plan_file)
    mask, _ = bootstrap.load_json(mask_file)
    module = (ROOT / 'research/no12-prebuy-causal-runtime-20261011/runtime/no11_rss_chart_50_prescreen.mjs').as_uri()
    script = ('import {validateNo11Chart50Plan} from ' + json.dumps(module) + ';'
              'let s="";for await(const c of process.stdin)s+=c;'
              'const {receipt,mask}=JSON.parse(s),p=receipt.chartPlan;'
              'if(receipt.schemaId!=="ARK_NO11_CHART50_PRIVATE_EXPORT_RECEIPT_V1"||'
              'receipt.productionReady!==false||receipt.orderTransmission!==false)process.exit(2);'
              'console.log(JSON.stringify(validateNo11Chart50Plan({chartPlan:p,mask,sessionDate:p.sessionDate})));')
    result = subprocess.run(['node', '--input-type=module', '-e', script],
                            input=json.dumps({'receipt': plan, 'mask': mask}, allow_nan=False),
                            text=True, capture_output=True, encoding='utf-8', timeout=30, check=False)
    need(result.returncode == 0, 'CHART_PLAN_OR_MASK_INVALID')
    selected = json.loads(result.stdout)
    need(type(selected) is list and 1 <= len(selected) <= 50, 'SELECTED_SCOPE_INVALID')
    session = plan['chartPlan']['sessionDate']
    prior = received.previous_cash_session(ROOT, session)
    need(plan['chartPlan']['asOfSession'] == prior and mask['asOfSession'] == prior,
         'PREVIOUS_SESSION_MISMATCH')
    return {'sessionDate': session, 'previousSession': prior,
            'chartPlanSha256': plan['chartPlan']['planSha256'], 'selectedSymbols': selected}


def write_symbols(plan_file, mask_file, output_root):
    info = scope(plan_file, mask_file)
    root = bootstrap.private(output_root, True)
    data = ('\n'.join(info['selectedSymbols']) + '\n').encode('utf-8')
    sha = hashlib.sha256(data).hexdigest()
    file = root / ('previous-symbols-' + sha + '.txt')
    need(not file.is_symlink(), 'SYMBOL_OUTPUT_SYMLINK')
    if file.exists():
        need(file.read_bytes() == data, 'SYMBOL_OUTPUT_CHANGED')
    else:
        with file.open('xb') as handle:
            handle.write(data)
    return file, info


def checkpoint(capture_dir):
    root = bootstrap.private(capture_dir, True)
    names = list(root.glob('progress-*.json'))
    need(1 <= len(names) <= 250, 'CAPTURE_PROGRESS_REQUIRED')
    need(all(re.fullmatch(r'progress-[0-9]{5}\.json', p.name) for p in names),
         'PROGRESS_FILENAME_INVALID')
    file = max(names, key=lambda p: int(p.stem.split('-')[1]))
    record, sha = bootstrap.load_json(file, 2000000)
    members = record.get('files')
    need(record.get('schemaId') == PROGRESS and record.get('productionReady') is False
         and record.get('orderTransmission') is False and type(members) is list
         and type(record.get('completed')) is int and type(record.get('requested')) is int
         and len(members) == record['completed'] == int(file.stem.split('-')[1])
         and 1 <= record['completed'] <= record['requested'] <= 5000, 'PROGRESS_CONTRACT_INVALID')
    symbols, files = set(), set()
    for item in members:
        need(type(item) is dict and type(item.get('symbol')) is str
             and re.fullmatch(r'[0-9A-Z]{4}\.T', item['symbol'])
             and type(item.get('file')) is str and MEMBER.fullmatch(item['file'])
             and item['file'].endswith('-' + item['symbol'].replace('.', '_') + '-1M.json')
             and type(item.get('sha256')) is str and re.fullmatch(r'[a-f0-9]{64}', item['sha256'])
             and item['symbol'] not in symbols and item['file'] not in files,
             'PROGRESS_MEMBER_INVALID')
        symbols.add(item['symbol'])
        files.add(item['file'])
    return root, record, sha


def previous_rows(raw, member, prior, prepared_at):
    observed = instant(raw.get('observedAt'))
    need(observed <= instant(prepared_at), 'ARCHIVE_RECEIPT_FROM_FUTURE')
    need(raw.get('schemaId') == ARCHIVE and raw.get('symbol') == member['symbol']
         and raw.get('period') == '1M' and raw.get('sourceFunction') == 'RssChart'
         and raw.get('evidenceMode') == 'OBSERVED_READ_ONLY'
         and raw.get('productionReady') is False and raw.get('orderTransmission') is False
         and raw.get('privateAccountDataIncluded') is False
         and raw.get('actualHistoricalKnownAtCertified') is False
         and raw.get('vendorLabelCertified') is False
         and raw.get('vendorDecimalTokenCertified') is False
         and raw.get('modelTrainingReady') is False, 'ARCHIVE_CONTRACT_INVALID')
    rows = raw.get('rows')
    need(type(rows) is list and type(raw.get('requestedBars')) is int
         and 20 <= raw['requestedBars'] <= 3000 and len(rows) <= raw['requestedBars']
         and raw.get('validRows') == len(rows) and member.get('rows') == len(rows)
         and member.get('status') == raw.get('status'), 'ARCHIVE_ROW_COUNT_MISMATCH')
    need(raw['status'] == GOOD and raw.get('invalidRows') == 0
         and raw.get('duplicateRows') == 0 and raw.get('numericRows') == len(rows),
         'ARCHIVE_NOT_USABLE')
    selected, seen = [], set()
    for row in rows:
        need(type(row) is dict and type(row.get('label')) is str, 'ARCHIVE_ROW_INVALID')
        label = instant(row['label'])
        need(label <= observed and row['label'] not in seen, 'ARCHIVE_FUTURE_OR_DUPLICATE_LABEL')
        seen.add(row['label'])
        if row['label'][:10] != prior:
            continue
        m = label.hour * 60 + label.minute
        need(label.second == 0 and label.microsecond == 0
             and (540 <= m <= 690 or 750 <= m <= 924 or m == 930),
             'PREVIOUS_BAR_OUTSIDE_ORIGINAL_SCHEDULE')
        need(label + timedelta(minutes=1) <= observed, 'PREVIOUS_BAR_NOT_CLOSED')
        value = {'Date': prior, 'Code': member['symbol'], 'Time': row['label'][11:16],
                 'O': row.get('open'), 'H': row.get('high'), 'L': row.get('low'),
                 'C': row.get('close'), 'Vo': row.get('volume')}
        received.validate_prices(value, require_va=False)
        selected.append(value)
    need(2 <= len(selected) <= 400, 'PREVIOUS_MINUTES_INSUFFICIENT')
    selected.sort(key=lambda row: row['Time'])
    return {'rows': selected, 'archiveObservedAtOriginal': raw['observedAt'],
            'originalArchiveSha256': member['sha256'],
            'vendorLabelCertified': False, 'actualHistoricalKnownAtCertified': False,
            'vendorDecimalTokenCertified': False, 'fullPreviousSessionCoverageCertified': False,
            'sourceRowsIgnoredOutsidePreviousSession': len(rows) - len(selected)}


def stage_archive(info, capture_dir, prepared_at):
    instant(prepared_at)
    root, progress, progress_sha = checkpoint(capture_dir)
    index = {r['symbol']: r for r in progress['files']}
    symbols, omitted = {}, {}
    for code in info['selectedSymbols']:
        member = index.get(code)
        if member is None:
            omitted[code] = 'NOT_IN_CAPTURE_CHECKPOINT'
            continue
        raw, sha = bootstrap.load_json(root / member['file'], 3000000)
        need(sha == member['sha256'], 'ARCHIVE_BYTES_CHANGED')
        try:
            symbols[code] = previous_rows(raw, member, info['previousSession'], prepared_at)
        except (ValueError, KeyError, TypeError) as exc:
            reason = str(exc)
            omitted[code] = reason if re.fullmatch(r'(?:NO11_PREVIOUS_ARCHIVE|P1_RSS)_[A-Z0-9_]+', reason) else 'MALFORMED_ARCHIVE'
    return {'schemaId': SCHEMA, **info, 'preparedAtJst': prepared_at,
            'progressSha256': progress_sha, 'symbols': symbols, 'omittedSymbols': omitted,
            'priceBasisCertified': False, 'corporateActionsCertified': False,
            'previousVaGenerated': False, 'liveReady': False,
            'productionReady': False, 'orderTransmission': False}


def assemble(stage, plan_file, mask_file, master_file, output_root, prepared_at):
    session = stage['sessionDate']
    need(prepared_at[:10] == session, 'FINAL_CONTEXT_REQUIRES_ACTUAL_SESSION_DAY')
    master, master_sha = bootstrap.load_json(master_file)
    selected = bootstrap.validate_scope(session, plan_file, mask_file, master_file, prepared_at)
    info = scope(plan_file, mask_file)
    need(info['chartPlanSha256'] == stage['chartPlanSha256'] and selected == stage['selectedSymbols'],
         'SELECTED_PLAN_CHANGED')
    by = {row['symbol']: row for row in master['rows']}
    result = {'schemaId': received.PREVIOUS_SCHEMA, 'sessionDate': session,
              'previousSession': stage['previousSession'], 'symbols': {},
              'archiveProgressSha256': stage['progressSha256'], 'chartPlanSha256': stage['chartPlanSha256'],
              'masterSha256': master_sha, 'productionReady': False, 'orderTransmission': False}
    for code, source in stage['symbols'].items():
        need(instant(source['archiveObservedAtOriginal']) <= instant(prepared_at), 'ARCHIVE_RECEIPT_FROM_FUTURE')
        metadata = by[code]
        need(metadata['corporateActionsCleared'] is True and metadata['priceBasisVerified'] is True,
             'EXISTING_MASTER_PRICE_EVIDENCE_REQUIRED')
        result['symbols'][code] = {**deepcopy(source), 'previousSession': stage['previousSession'],
            'priceBasis': 'COMPARABLE_RAW', 'corporateActionsCleared': metadata['corporateActionsCleared'],
            'knownAtJst': prepared_at, 'basisSource': 'EXISTING_DATED_MASTER_NOT_CREATED_BY_ARCHIVE_ADAPTER'}
    runtime = bootstrap.service.features.load_feature_runtime(ROOT)
    usable, rejected = bootstrap.previous_coverage(result, selected, session, stage['previousSession'], runtime)
    omitted = dict(stage['omittedSymbols'])
    omitted.update({code: reason for code, reason in rejected.items() if code not in omitted})
    report = {'schemaId': 'ARK_NO11_PREVIOUS_ARCHIVE_BUILD_REPORT_V1', 'sessionDate': session,
              'selectedCount': len(selected), 'usablePreviousCount': len(usable), 'omittedSymbols': omitted,
              'originalState9NormalizationExecuted': True, 'actualRssTested': False,
              'productionReady': False, 'orderTransmission': False}
    report_file = bootstrap.immutable(output_root, 'previous-archive-report', report)
    need(bool(usable), 'NO_USABLE_PREVIOUS_CONTEXT')
    result['symbols'] = {code: result['symbols'][code] for code in usable}
    return bootstrap.immutable(output_root, 'previous-context', result), report_file


def updated_config(config_file, context_file, master_file, info, output_root):
    original, _ = bootstrap.load_json(config_file, 100000)
    need(original.get('sessionDate') == info['sessionDate']
         and original.get('productionReady') is False and original.get('orderTransmission') is False,
         'CONFIG_SESSION_OR_MODE_INVALID')
    need(bootstrap.private(original.get('datedMaster')) == bootstrap.private(master_file), 'CONFIG_MASTER_DIFFERS')
    result = deepcopy(original)
    result.pop('previousCaptureFiles', None)
    result['previousContext'] = str(context_file)
    bootstrap.validate_config(result)
    # Preserve the remaining config, including model and source paths exactly.
    return bootstrap.immutable(output_root, 'bootstrap-with-previous', result)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', required=True, type=Path)
    parser.add_argument('--mask', required=True, type=Path)
    parser.add_argument('--output-root', required=True, type=Path)
    parser.add_argument('--symbols-only', action='store_true')
    parser.add_argument('--capture-dir', type=Path)
    parser.add_argument('--dated-master', type=Path)
    parser.add_argument('--bootstrap-config', type=Path)
    args = parser.parse_args(argv)
    info = scope(args.plan, args.mask)
    root = bootstrap.private(args.output_root, True)
    if args.symbols_only:
        need(args.capture_dir is None and args.dated_master is None and args.bootstrap_config is None, 'CLI_MODE_CONFLICT')
        file, _ = write_symbols(args.plan, args.mask, root)
        print('NO11_PREVIOUS_SYMBOLS_FILE=' + str(file))
        print('NO11_PREVIOUS_SYMBOLS_COUNT=' + str(len(info['selectedSymbols'])))
    else:
        need(args.capture_dir is not None, 'CAPTURE_DIR_REQUIRED')
        stage = stage_archive(info, args.capture_dir, now_jst())
        stage_file = bootstrap.immutable(root, 'previous-archive-stage', stage)
        print('NO11_PREVIOUS_ARCHIVE_STAGE=' + str(stage_file))
        print('NO11_PREVIOUS_ARCHIVE_USABLE=' + str(len(stage['symbols'])))
        print('NO11_PREVIOUS_ARCHIVE_MISSING=' + str(len(stage['omittedSymbols'])))
        need(bool(stage['symbols']), 'NO_USABLE_ARCHIVE_ROWS')
        if args.dated_master is not None:
            context, report = assemble(stage, args.plan, args.mask, args.dated_master, root, now_jst())
            print('NO11_PREVIOUS_CONTEXT=' + str(context))
            print('NO11_PREVIOUS_CONTEXT_REPORT=' + str(report))
            if args.bootstrap_config is not None:
                config = updated_config(args.bootstrap_config, context, args.dated_master, info, root)
                print('NO11_PREVIOUS_BOOTSTRAP_CONFIG=' + str(config))
        else:
            need(args.bootstrap_config is None, 'MASTER_REQUIRED_FOR_CONFIG')
            print('NO11_PREVIOUS_CONTEXT_NOT_CREATED=DATED_MASTER_REQUIRED_ON_SESSION_DAY')
    print('ORDER_TRANSMISSION=False')


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, TypeError, KeyError, RuntimeError, subprocess.SubprocessError) as exc:
        message = str(exc)
        print(message if re.fullmatch(r'(?:NO11|P1_RSS)_[A-Z0-9_]+', message)
              else 'NO11_PREVIOUS_ARCHIVE_PRIVATE_SOURCE_FAILED', file=sys.stderr)
        raise SystemExit(2)
