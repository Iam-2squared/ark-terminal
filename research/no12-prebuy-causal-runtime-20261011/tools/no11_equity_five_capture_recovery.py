#!/usr/bin/env python3
"""Verify an already collected five-symbol RSS 1m backfill without Excel.

Recovers source evidence after a wrapper's post-collection failure. This does
not create a Chart50 plan, datedMaster, independent product review, positions,
orders, broker permissions, price certification or model readiness.
All validation is against immutable private receipts and the existing original
No.1.1 previous-archive source validator. Nothing recollects or modifies RSS.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

import no11_previous_archive_context as archive
import no11_received_session_bootstrap as bootstrap

SESSION = '2026-10-30'
PRIOR = '2026-10-29'
AUDIT = 'ARK_NO11_PROVISIONAL_EQUITY_TYPE_PRESCREEN_V1'
STAGE = 'ARK_NO11_PREVIOUS_ARCHIVE_STAGE_V1'
REQUEST = 'ARK_NO11_PROVISIONAL_FIVE_CAPTURE_REQUEST_V1'
CHART = 'ARK_NO11_CHART50_PRIVATE_EXPORT_RECEIPT_V1'
EXCLUDED = frozenset({'1671.T', '1690.T', '1699.T', '2014.T', '2038.T'})
ERROR = 'NO11_EQUITY_FIVE_RECOVERY_'
# Production CLI is pinned to the exact private audit receipt reported by
# the user. Tests patch this *module-only* constant with a synthetic digest.
EXPECTED_AUDIT_SHA_PREFIX = '304f08b2eed20c63'


def need(ok, code):
    if not ok:
        raise ValueError(ERROR + code)


def sha_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def exact_symbols(value, expected, code):
    need(type(value) is list and len(value) == expected and
         all(type(s) is str and re.fullmatch(r'[0-9A-Z]{4}\.T', s) for s in value)
         and len(set(value)) == expected, code)
    return set(value)


def recover(*, audit_file, stage_file, chart_file, request_file,
            capture_dir, output_dir, checked_at=None):
    out = bootstrap.private(output_dir, True)
    capture = bootstrap.private(capture_dir, True)
    need(capture.parent == out and
         re.fullmatch(r'rss-[a-f0-9]{32}', capture.name), 'CAPTURE_DIRECTORY_IDENTITY')
    audit_file, stage_file, chart_file, request_file = [
        bootstrap.private(p) for p in (audit_file, stage_file, chart_file, request_file)]
    need(request_file.parent == out and
         request_file.name == 'capture-started-304f08b2eed20c63.json',
         'ORIGINAL_ATTEMPT_MARKER_REQUIRED')
    review, review_sha = bootstrap.load_json(audit_file, 5_000_000)
    stage, stage_sha = bootstrap.load_json(stage_file, 5_000_000)
    chart, _ = bootstrap.load_json(chart_file, 5_000_000)
    marker, _ = bootstrap.load_json(request_file, 100_000)
    need(re.fullmatch(r'equity-type-provisional-([a-f0-9]{16})\.json', audit_file.name)
         and review_sha.startswith(EXPECTED_AUDIT_SHA_PREFIX)
         and audit_file.name.endswith(review_sha[:16] + '.json'),
         'AUDIT_FILE_HASH_NAME')
    need(type(review) is dict and review.get('schemaId') == AUDIT
         and review.get('status') == 'PROVISIONAL_REVIEW_REQUIRED_NOT_A_TRADING_PLAN'
         and review.get('sessionDate') == SESSION and review.get('previousSession') == PRIOR
         and review.get('originalG1PassCount') == 78
         and review.get('originalSelectedCount') == 47
         and review.get('provisionalSelectedCount') == 47
         and review.get('actualCommonEquityIndependentlyReviewed') is False
         and review.get('corporateActionsCleared') is False
         and review.get('priceBasisVerified') is False
         and review.get('executableChartPlanProduced') is False
         and review.get('permitsBuy') is False
         and review.get('productionReady') is False
         and review.get('orderTransmission') is False
         and review.get('originalChartPlanUnmodified') is True
         and review.get('previousArchiveUnmodified') is True,
         'AUDIT_PROVISIONAL_ONLY_REQUIRED')
    need(review.get('sourceStageSha256') == stage_sha
         and review.get('sourceChartPlanSha256') == stage.get('chartPlanSha256'),
         'AUDIT_STAGE_BYTES_CHANGED')
    plan = chart.get('chartPlan') if type(chart) is dict else None
    need(type(plan) is dict and chart.get('schemaId') == CHART
         and chart.get('productionReady') is False and chart.get('orderTransmission') is False
         and plan.get('sessionDate') == SESSION and plan.get('asOfSession') == PRIOR
         and plan.get('planSha256') == review['sourceChartPlanSha256']
         and plan.get('productionReady') is False and plan.get('orderTransmission') is False,
         'CHART_LINEAGE_CHANGED')
    selected = exact_symbols(plan.get('selectorInputSymbols'), 47, 'ORIGINAL_CHART_SELECTED')
    need(type(stage) is dict and stage.get('schemaId') == STAGE
         and stage.get('sessionDate') == SESSION and stage.get('previousSession') == PRIOR
         and stage.get('chartPlanSha256') == plan['planSha256']
         and stage.get('productionReady') is False and stage.get('orderTransmission') is False
         and stage.get('selectedSymbols') == plan['selectorInputSymbols']
         and type(stage.get('symbols')) is dict and set(stage['symbols']) == selected
         and stage.get('omittedSymbols') == {},
         'EXISTING_47_ARCHIVE_CHANGED')
    blocked = exact_symbols(review.get('knownExcludedFromG1'), 5, 'JPX_EXCLUSIONS_SCOPE')
    need(blocked == EXCLUDED and
         exact_symbols(review.get('knownExcludedFromOriginal'), 5,
                       'ORIGINAL_EXCLUDED_SCOPE') == blocked, 'EXCLUSIONS_UNCHANGED')
    extras = exact_symbols(review.get('replacementPriorArchiveMissing'), 5,
                           'EXTRA_FIVE_REQUIRED')
    need(extras == exact_symbols(review.get('provisionalReplacementCandidates'), 5,
                                'REPLACEMENT_SCOPE')
         and not extras.intersection(selected | EXCLUDED), 'REPLACEMENTS_CHANGED')
    provisional = exact_symbols(review.get('provisionalSelectedAfterKnownExclusions'),
                                47, 'PROVISIONAL_SCOPE')
    need(provisional == ((selected - EXCLUDED) | extras)
         and not provisional.intersection(EXCLUDED),
         'PROVISIONAL_SELECTION_CHANGED')
    need(type(marker) is dict and marker.get('schemaId') == REQUEST
         and marker.get('expected') == 5
         and marker.get('sourceReportSha256') == review_sha
         and marker.get('sourceStageSha256') == stage_sha
         and marker.get('productionReady') is False
         and marker.get('orderTransmission') is False
         and type(marker.get('startedAtJst')) is str
         and marker['startedAtJst'][:10] == SESSION, 'ATTEMPT_MARKER_CHANGED')
    stamp = checked_at or archive.now_jst()
    need(stamp[:10] >= SESSION and
         archive.instant(marker['startedAtJst']) <= archive.instant(stamp),
         'RECOVERY_CLOCK_INVALID')
    root, progress, progress_sha = archive.checkpoint(capture)
    need(root == capture and
         progress.get('requested') == 5 and progress.get('completed') == 5
         and progress.get('observedSymbols') == 5 and progress.get('unavailableSymbols') == 0
         and progress.get('productionReady') is False
         and progress.get('orderTransmission') is False,
         'FIVE_CAPTURE_CHECKPOINT_INCOMPLETE')
    members = progress['files']
    need({m['symbol'] for m in members} == extras
         and all(m.get('status') == archive.GOOD for m in members),
         'FIVE_CAPTURE_SOURCE_MEMBERSHIP')
    total = 0
    previous = 0
    per_symbol = []
    for member in sorted(members, key=lambda m: m['symbol']):
        raw, digest = bootstrap.load_json(capture / member['file'], 3_000_000)
        need(digest == member['sha256'], 'FIVE_CAPTURE_MEMBER_HASH_CHANGED')
        need(raw.get('observedAt', '')[:10] == SESSION, 'FIVE_CAPTURE_OBSERVED_DAY')
        selection = archive.previous_rows(raw, member, PRIOR, stamp)
        total += member['rows']
        count = len(selection['rows'])
        previous += count
        per_symbol.append({
            'symbol': member['symbol'],
            'archiveSha256': digest,
            'allReceivedRows': member['rows'],
            'originalPreviousSessionRows': count,
            'fullPreviousSessionCoverageCertified': False
        })
    need(type(progress.get('rows')) is int and progress['rows'] == total
         and total >= previous >= 10, 'FIVE_CAPTURE_ROW_COUNT_CHANGED')
    proof = {
        'schemaId': 'ARK_NO11_PROVISIONAL_FIVE_CAPTURE_RECOVERY_SOURCE_ONLY_V1',
        'status': 'FIVE_CAPTURE_SOURCE_VERIFIED_NOT_TRADEABLE',
        'sessionDate': SESSION, 'previousSession': PRIOR,
        'sourceAuditSha256': review_sha, 'sourcePreviousStageSha256': stage_sha,
        'originalChartPlanSha256': plan['planSha256'],
        'originalAttemptMarkerSha256': sha_file(request_file),
        'originalFiveCaptureProgressSha256': progress_sha,
        'actualRssCaptureFolder': str(capture),
        'observedNewSymbols': 5, 'observedAllDatesMinuteRows': total,
        'observedPreviousSessionMinuteRows': previous,
        'symbols': per_symbol,
        'original47ArchiveUnchanged': True,
        'originalCollectorUnchanged': True,
        'rssRecollectionPerformed': False,
        'verifiedUsingOriginalPreviousArchiveValidator': True,
        'commonEquityIndependentlyReviewed': False,
        'corporateActionsCleared': False,
        'priceBasisVerified': False,
        'fullPreviousSessionCoverageCertified': False,
        'datedMasterCreated': False,
        'executableChartPlanProduced': False,
        'shadowPreflightPassed': False,
        'liveOrderAuthorized': False,
        'productionReady': False,
        'orderTransmission': False
    }
    file = bootstrap.immutable(out, 'equity-five-recovered-source-only', proof)
    return proof, file


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ('audit', 'stage', 'chart', 'request', 'capture', 'output'):
        parser.add_argument('--' + flag, type=Path, required=True)
    a = parser.parse_args(argv)
    data, result = recover(audit_file=a.audit, stage_file=a.stage,
                           chart_file=a.chart, request_file=a.request,
                           capture_dir=a.capture, output_dir=a.output)
    print('NO11_EQUITY_FIVE_RECOVERY=PASS_SOURCE_ONLY_NO_RSS')
    print('NO11_EQUITY_FIVE_OBSERVED_SYMBOLS=' + str(data['observedNewSymbols']))
    print('NO11_EQUITY_FIVE_OBSERVED_ALL_DATES_ROWS=' +
          str(data['observedAllDatesMinuteRows']))
    print('NO11_EQUITY_FIVE_PREVIOUS_SESSION_ROWS=' +
          str(data['observedPreviousSessionMinuteRows']))
    print('NO11_EQUITY_FIVE_RECOVERY_RECEIPT=' + str(result))
    print('NO11_EQUITY_FIVE_PROVISIONAL_NOT_TRADEABLE=True')
    print('NO11_EQUITY_FIVE_OLD_47_RECOLLECTED=False')
    print('EXCEL_TOUCHED=False')
    print('ORDER_TRANSMISSION=False')


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError, TypeError, RuntimeError,
            json.JSONDecodeError) as exc:
        detail = str(exc)
        allowed = r'^(?:NO11_EQUITY_FIVE_RECOVERY|NO11_PREVIOUS_ARCHIVE|NO11_BOOTSTRAP|P1_RSS)_[A-Z0-9_]+$'
        reason = detail if re.fullmatch(allowed, detail) else ERROR + 'PRIVATE_SOURCE_INVALID'
        print('NO11_EQUITY_FIVE_RECOVERY=BLOCKED|' + reason)
        print('EXCEL_TOUCHED=False')
        print('ORDER_TRANSMISSION=False')
        sys.exit(2)
