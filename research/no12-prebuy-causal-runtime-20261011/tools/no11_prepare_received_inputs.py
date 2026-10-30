#!/usr/bin/env python3
"""Actual RSS session reference + existing security evidence + prior archive.

Assembles the existing dated-master/context/bootstrap contracts in one run.
Corporate-action/price-basis review is an external input, never inferred from
price equality or manufactured here. No Excel or brokerage transport.
"""
from copy import deepcopy
from decimal import Decimal
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

import no11_previous_archive_context as archive
import no11_received_session_bootstrap as bootstrap

REFERENCE = 'ARK_NO11_RSS_SESSION_REFERENCE_CAPTURE_V1'
EVIDENCE = 'ARK_NO11_SESSION_SECURITY_EVIDENCE_V1'
MASTER = 'ARK_NO11_DATED_MASTER_RECEIPT_V1'
# Exact observed RSS labels (halfwidth/fullwidth Latin P,S,G); raw values remain unchanged.
# No broad Unicode normalization: unknown market strings are rejected.
SECTIONS = {'東証P': 'PRIME', '東証Ｐ': 'PRIME',
            '東証S': 'STANDARD', '東証Ｓ': 'STANDARD',
            '東証G': 'GROWTH', '東証Ｇ': 'GROWTH'}
SYMBOL = re.compile(r'[0-9A-Z]{4}\.T')


def need(ok, code):
    if not ok:
        raise ValueError('NO11_INPUT_PREP_' + code)


def number(value):
    need(type(value) in (int, float) and value > 0, 'PREVIOUS_CLOSE_INVALID')
    result = Decimal(str(value))
    need(result.is_finite() and result <= Decimal('1000000000'), 'PREVIOUS_CLOSE_INVALID')
    return result


def indexed(rows, maximum):
    need(type(rows) is list and 0 < len(rows) <= maximum, 'ROW_COUNT_INVALID')
    result = {}
    for row in rows:
        need(type(row) is dict and type(row.get('symbol')) is str and SYMBOL.fullmatch(row['symbol'])
             and row['symbol'] not in result, 'ROW_IDENTITY_OR_DUPLICATE')
        result[row['symbol']] = row
    return result


def build_master(info, reference, evidence, *, reference_sha, evidence_sha, prepared_at):
    """Only join supported facts; never turn absent review or blank RSS into true."""
    session, prior = info['sessionDate'], info['previousSession']
    now = archive.instant(prepared_at)
    need(prepared_at[:10] == session, 'ACTUAL_SESSION_REQUIRED')
    need(reference.get('schemaId') == REFERENCE and reference.get('sessionDate') == session
         and reference.get('source') == 'RssMarket_SELECTED_REFERENCE_READONLY'
         and reference.get('orderTransmission') is False and reference.get('productionReady') is False
         and reference.get('readOnly') is True
         and reference.get('chartPlanSha256') == info['chartPlanSha256']
         and reference.get('selectedSymbols') == info['selectedSymbols'], 'REFERENCE_CONTRACT')
    start, end = archive.instant(reference.get('capturedAtJst')), archive.instant(reference.get('completedAtJst'))
    need(start <= end <= now and 0 <= (end - start).total_seconds() < 30
         and reference['capturedAtJst'][:10] == session and reference['completedAtJst'][:10] == session,
         'REFERENCE_CLOCK')
    need(evidence.get('schemaId') == EVIDENCE and evidence.get('validForSession') == session
         and evidence.get('reviewStatus') == 'EXTERNALLY_REVIEWED'
         and evidence.get('productionReady') is False and evidence.get('orderTransmission') is False
         and archive.instant(evidence.get('knownAtJst')) <= now, 'SECURITY_EVIDENCE_REQUIRED')
    prices = indexed(reference.get('rows'), 50)
    metadata = indexed(evidence.get('rows'), 5000)
    need(set(prices) == set(info['selectedSymbols']), 'REFERENCE_SCOPE_MISMATCH')
    rows = []
    for symbol in info['selectedSymbols']:
        price, meta = prices[symbol], metadata.get(symbol)
        need(meta is not None, 'SECURITY_EVIDENCE_MISSING')
        need(meta.get('commonEquity') is True and meta.get('corporateActionsCleared') is True
             and meta.get('priceBasisVerified') is True
             and meta.get('segment') in ('PRIME', 'STANDARD', 'GROWTH')
             and type(meta.get('sector')) is str and 0 < len(meta['sector']) <= 100,
             'SECURITY_EVIDENCE_NOT_CONFIRMED')
        refs = meta.get('sourceDocumentSha256')
        need(type(refs) is list and 1 <= len(refs) <= 20
             and all(type(s) is str and re.fullmatch(r'[a-f0-9]{64}', s) for s in refs),
             'REVIEW_SOURCE_REFERENCE_REQUIRED')
        need(price.get('marketCode') == 'T' and price.get('marketDate') == session
             and price.get('previousDate') == prior and price.get('lotShares') == 100
             and SECTIONS.get(price.get('marketSection')) == meta['segment'], 'RSS_IDENTITY_DATE_OR_CLASS_MISMATCH')
        previous = number(price.get('previousClose'))
        # A review must bind the actually observed reference price. A boolean
        # copied from another day or a price mismatch cannot certify this one.
        need(previous == number(meta.get('reviewedPreviousClose')), 'REVIEWED_PRICE_MISMATCH')
        need(type(price.get('dayBasePrice')) in (int, float) and number(price['dayBasePrice']) > 0,
             'RSS_BASE_PRICE_UNAVAILABLE')
        rows.append({'symbol': symbol, 'asOfSession': session, 'segment': meta['segment'],
                     'sector': meta['sector'], 'rawPreviousClose': price['previousClose'],
                     'commonEquity': meta['commonEquity'],
                     'corporateActionsCleared': meta['corporateActionsCleared'],
                     'priceBasisVerified': meta['priceBasisVerified']})
    return {'schemaId': MASTER, 'sessionDate': session, 'knownAtJst': prepared_at,
            'rows': rows, 'referenceSourceSha256': reference_sha,
            'securityEvidenceSha256': evidence_sha,
            'corporateActionReviewSource': 'EXISTING_EXTERNAL_REVIEW_NOT_INFERRED_BY_ADAPTER',
            'rssFieldTimestampCertified': False, 'productionReady': False, 'orderTransmission': False}


def verify_documents(evidence, folder):
    """Integrity only, not independent certification of the supplied review."""
    root = bootstrap.private(folder, True)
    references = {sha for row in evidence.get('rows', []) for sha in row.get('sourceDocumentSha256', [])}
    need(0 < len(references) <= 100, 'REVIEW_DOCUMENTS_REQUIRED')
    for sha in references:
        need(type(sha) is str and re.fullmatch(r'[a-f0-9]{64}', sha), 'DOCUMENT_HASH_INVALID')
        file = bootstrap.private(root / (sha + '.source'))
        need(0 < file.stat().st_size <= 25000000
             and hashlib.sha256(file.read_bytes()).hexdigest() == sha, 'DOCUMENT_BYTES_CHANGED')


def prepare(*, plan_file, mask_file, reference_file, evidence_file, evidence_documents,
            capture_dir, config_file, output_root, prepared_at):
    info = archive.scope(plan_file, mask_file)
    root = bootstrap.private(output_root, True)
    reference, reference_sha = bootstrap.load_json(reference_file, 5000000)
    evidence, evidence_sha = bootstrap.load_json(evidence_file, 5000000)
    master = build_master(info, reference, evidence, reference_sha=reference_sha,
                          evidence_sha=evidence_sha, prepared_at=prepared_at)
    verify_documents(evidence, evidence_documents)
    # All rows above validated before creating any usable master artifact.
    master_file = bootstrap.immutable(root, 'dated-master', master)
    bootstrap.validate_scope(info['sessionDate'], plan_file, mask_file, master_file, prepared_at)
    stage = archive.stage_archive(info, capture_dir, prepared_at)
    stage_file = bootstrap.immutable(root, 'previous-archive-stage', stage)
    context_file, context_report = archive.assemble(stage, plan_file, mask_file, master_file, root, prepared_at)
    original, _ = bootstrap.load_json(config_file, 100000)
    need(original.get('schemaId') == bootstrap.CONFIG and original.get('sessionDate') == info['sessionDate']
         and original.get('productionReady') is False and original.get('orderTransmission') is False,
         'BOOTSTRAP_TEMPLATE_INVALID')
    copied = deepcopy(original)
    copied.pop('previousCaptureFiles', None)
    copied.update(datedMaster=str(master_file), previousContext=str(context_file))
    bootstrap.validate_config(copied)
    config_copy = bootstrap.immutable(root, 'bootstrap-ready-inputs', copied)
    report = {'schemaId': 'ARK_NO11_RECEIVED_INPUT_PREPARATION_REPORT_V1',
              'sessionDate': info['sessionDate'], 'selectedCount': len(info['selectedSymbols']),
              'masterRows': len(master['rows']), 'stagedPreviousSymbols': len(stage['symbols']),
              'master': str(master_file), 'previousContext': str(context_file),
              'previousContextReport': str(context_report), 'previousStage': str(stage_file),
              'bootstrapConfig': str(config_copy), 'sourceIntegrityChecked': True,
              'independentCorporateActionReviewPerformed': False,
              'collectorStarted': False, 'modelsExecuted': False,
              'productionReady': False, 'orderTransmission': False}
    result = bootstrap.immutable(root, 'input-preparation-report', report)
    return config_copy, result


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    for flag in ('plan', 'mask', 'reference-file', 'security-evidence', 'evidence-documents',
                 'previous-capture-dir', 'bootstrap-config', 'output-root'):
        p.add_argument('--' + flag, required=True, type=Path)
    a = p.parse_args(argv)
    config, report = prepare(plan_file=a.plan, mask_file=a.mask, reference_file=a.reference_file,
        evidence_file=a.security_evidence, evidence_documents=a.evidence_documents,
        capture_dir=a.previous_capture_dir, config_file=a.bootstrap_config,
        output_root=a.output_root, prepared_at=archive.now_jst())
    print('NO11_INPUTS_PREPARED_CONFIG=' + str(config))
    print('NO11_INPUTS_PREPARED_REPORT=' + str(report))
    print('ORDER_TRANSMISSION=False')


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError, TypeError, RuntimeError) as exc:
        s = str(exc)
        print(s if re.fullmatch(r'(?:NO11|P1_RSS)_[A-Z0-9_]+', s)
              else 'NO11_INPUT_PREP_PRIVATE_SOURCE_FAILED', file=sys.stderr)
        raise SystemExit(2)
