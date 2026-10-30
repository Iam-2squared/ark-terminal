#!/usr/bin/env python3
"""Prevalidate existing input/model dependencies before any Excel collection.

Called by Prepare-No11ReceivedInputsReadOnly.ps1. Can run the day before the
session; it does NOT produce a future-dated master or certify tomorrow's RSS.
No orders, network, fitting, account-value reads or model-weight changes.
"""
from copy import deepcopy
from pathlib import Path
import argparse
import re
import sys

import no11_prepare_received_inputs as prep
import no11_previous_archive_context as archive
import no11_received_session_bootstrap as bootstrap
import no11_p1_forward_shadow as forward
import no11_h235_asof_forward_shadow as h235
import no11_observed_execution_shadow as execution
import no11_original_exit_shadow as exits


def need(ok, code):
    if not ok:
        raise ValueError('NO11_INPUT_PRECHECK_' + code)


def validate_review(info, evidence, known_at):
    now = archive.instant(known_at)
    need(known_at[:10] <= info['sessionDate'], 'TARGET_SESSION_ALREADY_PASSED')
    need(evidence.get('schemaId') == prep.EVIDENCE
         and evidence.get('validForSession') == info['sessionDate']
         and evidence.get('reviewStatus') == 'EXTERNALLY_REVIEWED'
         and evidence.get('productionReady') is False
         and evidence.get('orderTransmission') is False
         and archive.instant(evidence.get('knownAtJst')) <= now,
         'EXISTING_SECURITY_REVIEW_REQUIRED')
    rows = prep.indexed(evidence.get('rows'), 5000)
    for code in info['selectedSymbols']:
        row = rows.get(code)
        need(row is not None, 'SELECTED_SYMBOL_REVIEW_MISSING')
        need(row.get('commonEquity') is True and row.get('priceBasisVerified') is True
             and row.get('corporateActionsCleared') is True
             and row.get('segment') in ('PRIME', 'STANDARD', 'GROWTH')
             and type(row.get('sector')) is str and 0 < len(row['sector']) <= 100,
             'REVIEW_NOT_CONFIRMED')
        prep.number(row.get('reviewedPreviousClose'))
        refs = row.get('sourceDocumentSha256')
        need(type(refs) is list and 1 <= len(refs) <= 20
             and all(type(v) is str and re.fullmatch(r'[a-f0-9]{64}', v) for v in refs),
             'REVIEW_DOCUMENT_REFERENCES_REQUIRED')


def check(*, plan_file, mask_file, config_file, evidence_file, documents,
          output_root, checked_at, capture_dir=None, require_full_shadow=False):
    info = archive.scope(plan_file, mask_file)
    root = bootstrap.private(output_root, True)
    cfg, config_hash = bootstrap.load_json(config_file, 100000)
    evidence, evidence_hash = bootstrap.load_json(evidence_file, 5000000)
    need(type(cfg) is dict and bootstrap.REQUIRED <= set(cfg) <= bootstrap.REQUIRED | bootstrap.OPTIONAL
         and cfg.get('schemaId') == bootstrap.CONFIG
         and cfg.get('sessionDate') == info['sessionDate']
         and cfg.get('productionReady') is False and cfg.get('orderTransmission') is False,
         'BOOTSTRAP_TEMPLATE_INVALID')
    need(('previousContext' in cfg) != ('previousCaptureFiles' in cfg), 'PREVIOUS_SOURCE_CHOICE')
    # Do not require not-yet-generated datedMaster/previousContext paths. The
    # real assembly validator checks their content after actual RSS collection.
    for key in ('dailyRun', 'privateRoot', 'runtimeRoot'):
        bootstrap.private(cfg[key], True)
    if 'pinsFile' in cfg:
        bootstrap.private(cfg['pinsFile'])
    for name, low, high in (('samples', 2, 390), ('historyBars', 50, 150), ('warmupSeconds', 5, 60)):
        if name in cfg:
            need(type(cfg[name]) is int and low <= cfg[name] <= high, 'COLLECTOR_OPTION_INVALID')
    need(not require_full_shadow or ('h235ModelRoot' in cfg and 'shadowAccountConfig' in cfg),
         'FULL_SHADOW_MODEL_AND_ACCOUNT_CONFIG_REQUIRED')
    need('shadowAccountConfig' not in cfg or 'h235ModelRoot' in cfg,
         'H235_REQUIRED_FOR_PORTFOLIO')
    validate_review(info, evidence, checked_at)
    prep.verify_documents(evidence, documents)
    prior_count = None
    if capture_dir is not None:
        stage = archive.stage_archive(info, capture_dir, checked_at)
        prior_count = len(stage['symbols'])
        need(prior_count > 0, 'NO_USABLE_PREVIOUS_ARCHIVE')
    # Load the same pinned artifacts as the real consumer before spending time
    # in Excel. This is loading/verification, not scoring or future market data.
    scorer = forward.FrozenP1Scorer(bootstrap.private(cfg['runtimeRoot'], True),
                                    bootstrap.ROOT, info['sessionDate'])
    model_count = 0
    if 'h235ModelRoot' in cfg:
        engine = h235.FrozenH235AsOf(bootstrap.private(cfg['h235ModelRoot'], True), info['sessionDate'])
        model_count = engine.original_model_count
        need(model_count == 24, 'ORIGINAL_H235_MEMBER_COUNT')
    portfolio_checked = False
    if 'shadowAccountConfig' in cfg:
        execution.settings(bootstrap.private(cfg['shadowAccountConfig']), info['sessionDate'])
        exits.load_original_exit()
        portfolio_checked = True
    report = {'schemaId': 'ARK_NO11_INPUT_PREREQUISITES_REPORT_V1',
              'sessionDate': info['sessionDate'], 'checkedAtJst': checked_at,
              'selectedCount': len(info['selectedSymbols']),
              'configSha256': config_hash, 'securityEvidenceSha256': evidence_hash,
              'p1AssetsLoaded': True, 'h235ModelMembersVerified': model_count,
              'shadowPortfolioAssetsChecked': portfolio_checked,
              'suppliedPreviousUsableSymbols': prior_count,
              'previousCollectionStillRequired': capture_dir is None,
              'actualSessionReferenceStillRequired': True,
              'actualRssVerified': False, 'modelsScored': False,
              'independentSecurityReviewPerformed': False,
              'excelStarted': False, 'shadowReady': False,
              'productionReady': False, 'orderTransmission': False}
    result = bootstrap.immutable(root, 'input-prerequisites', report)
    return deepcopy(report), result


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('plan', 'mask', 'bootstrap-config', 'security-evidence', 'evidence-documents', 'output-root'):
        p.add_argument('--' + name, required=True, type=Path)
    p.add_argument('--previous-capture-dir', type=Path)
    p.add_argument('--require-full-shadow', action='store_true')
    a = p.parse_args(argv)
    report, file = check(plan_file=a.plan, mask_file=a.mask, config_file=a.bootstrap_config,
                        evidence_file=a.security_evidence, documents=a.evidence_documents,
                        output_root=a.output_root, checked_at=archive.now_jst(),
                        capture_dir=a.previous_capture_dir, require_full_shadow=a.require_full_shadow)
    print('NO11_INPUTS_PREREQUISITES_REPORT=' + str(file))
    print('NO11_INPUTS_PREREQUISITES=ASSETS_CHECKED_NOT_MARKET_VERIFIED')
    print('ORDER_TRANSMISSION=False')


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, TypeError, KeyError, RuntimeError, ImportError) as exc:
        message = str(exc)
        print(message if re.fullmatch(r'(?:NO11|P1_RSS|P1_FORWARD)_[A-Z0-9_]+', message)
              else 'NO11_INPUT_PRECHECK_PRIVATE_DEPENDENCY_UNAVAILABLE', file=sys.stderr)
        raise SystemExit(2)
