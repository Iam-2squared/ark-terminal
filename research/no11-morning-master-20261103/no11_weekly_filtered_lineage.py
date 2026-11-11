"""Repair weekly shadow source validation after legitimate automatic ENTRY exclusions.

Original 16-hex weekly receipts are verified by the *unchanged* native JS
validator. A 64-hex filtered receipt is accepted only if it exactly replays the
already-pinned exclusion report against that verified original, without changing
other source/plan fields. No data correction, retry, order permission or Excel IO.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import re

MARK = "NO11_BOOTSTRAP_PINNED_FILTERED_WEEKLY_SOURCE_V1"

OLD = """        output = command_output(['node', str(HERE / 'no11_verified_weekly_shadow_scope.mjs'),
                                 '--run-dir', config['dailyRun'],
                                 '--weekly-source-run', config['weeklySourceRun'],
                                 '--mask', config['precomputedG1Mask'],
                                 '--chart', config['precomputedChartReceipt'],
                                 '--session', config['sessionDate']])"""

NEW = """        original_chart = verified_weekly_original(config)
        output = command_output(['node', str(HERE / 'no11_verified_weekly_shadow_scope.mjs'),
                                 '--run-dir', config['dailyRun'],
                                 '--weekly-source-run', config['weeklySourceRun'],
                                 '--mask', config['precomputedG1Mask'],
                                 '--chart', str(original_chart),
                                 '--session', config['sessionDate']])"""

HELPER = r'''
def verified_weekly_original(config):
    """Verify exact machine-exclusion lineage; return original chart for native check.

    The unchanged native weekly source validator ONLY recognizes original
    16-hex chart receipts. An exclusion derived from it uses a full 64-hex
    immutable name; never feed that derived name to the original source gate.
    Recheck both origins, the original admission report and exact narrowing.
    The caller STILL returns the filtered chart to the Frozen pipeline, where
    native validate_scope verifies its plan hash and matching dated master.
    """
    # NO11_BOOTSTRAP_PINNED_FILTERED_WEEKLY_SOURCE_V1
    run = private(config['dailyRun'], True)
    derived_file = private(config['precomputedChartReceipt'])
    need(derived_file.parent == run, 'FILTERED_CHART_RUN_MISMATCH')
    if re.fullmatch(r'no11-chart50-private-[a-f0-9]{16}\.json',
                    derived_file.name):
        return derived_file  # Unfiltered exact-original path unchanged.

    need(re.fullmatch(r'no11-chart50-private-[a-f0-9]{64}\.json',
                      derived_file.name) is not None, 'FILTERED_CHART_NAME')
    derived, derived_sha = load_json(derived_file)
    need(derived_file.name == 'no11-chart50-private-' + derived_sha + '.json',
         'FILTERED_CHART_HASH')
    scope = derived.get('automaticVerifiedExclusion')
    need(type(scope) is dict and
         scope.get('schemaId') == 'ARK_NO11_VERIFIED_INVALID_SYMBOL_EXCLUSION_V1' and
         scope.get('sessionDate') == config['sessionDate'] and
         scope.get('previousSelectionPreserved') is False and
         scope.get('originalChartReceiptModified') is False and
         scope.get('orderTransmission') is False,
         'FILTERED_PROVENANCE_CONTRACT')
    source_sha = scope.get('originalChartReceiptSha256')
    report_sha = scope.get('automaticResultReportSha256')
    need(type(source_sha) is str and
         re.fullmatch(r'[a-f0-9]{64}', source_sha) is not None and
         type(report_sha) is str and
         re.fullmatch(r'[a-f0-9]{64}', report_sha) is not None,
         'FILTERED_PROVENANCE_HASHES')

    original_file = private(run / ('no11-chart50-private-' +
                                   source_sha[:16] + '.json'))
    original, actual_source_sha = load_json(original_file)
    need(actual_source_sha == source_sha and
         'automaticVerifiedExclusion' not in original,
         'FILTERED_ORIGINAL_RECEIPT_CHANGED')
    need(original.get('schemaId') == 'ARK_NO11_CHART50_PRIVATE_EXPORT_RECEIPT_V1' and
         original.get('orderTransmission') is False and
         original.get('productionReady') is False,
         'FILTERED_ORIGINAL_RECEIPT_SCHEMA')

    master_file = private(config['datedMaster'])
    master, _ = load_json(master_file)
    report_file = private(master_file.parent /
                          ('automatic-input-result-' + report_sha + '.json'))
    report, actual_report_sha = load_json(report_file)
    need(actual_report_sha == report_sha and
         report.get('schemaId') == 'ARK_NO11_AUTOMATIC_OPERATIONAL_INPUT_RESULT_V1' and
         report.get('inputPolicy') ==
             'AUTO_SELECTED_JPX_RSS_UNADJUSTED_PRICE_CONSISTENCY_V1' and
         report.get('sessionDate') == config['sessionDate'] and
         report.get('productionReady') is False and
         report.get('orderTransmission') is False and
         report.get('humanReviewPerformed') is False,
         'FILTERED_REPORT_NOT_PINNED')
    blocked = scope.get('blockedSymbols')
    old_plan = original.get('chartPlan')
    plan = derived.get('chartPlan')
    need(type(blocked) is list and 1 <= len(blocked) <= 46 and
         all(type(symbol) is str and
             re.fullmatch(r'[0-9A-Z]{4}\.T', symbol) for symbol in blocked) and
         len(set(blocked)) == len(blocked) and
         type(old_plan) is dict and type(plan) is dict,
         'FILTERED_BLOCKED_SYMBOL_SCOPE')
    old_selected = old_plan.get('selectorInputSymbols')
    need(type(old_selected) is list and 1 <= len(old_selected) <= 47 and
         len(set(old_selected)) == len(old_selected) and
         set(blocked) <= set(old_selected), 'FILTERED_ORIGINAL_SELECTION')
    admitted = [symbol for symbol in old_selected if symbol not in set(blocked)]
    need(admitted and
         scope.get('passedSymbols') == admitted and
         report.get('selectedCount') == len(old_selected) and
         report.get('passedCount') == len(admitted) and
         type(report.get('blockedSymbols')) is list and
         [row.get('symbol') if type(row) is dict else None
          for row in report['blockedSymbols']] == blocked,
         'FILTERED_REPORT_SCOPE_MISMATCH')

    need(master.get('schemaId') == 'ARK_NO11_DATED_MASTER_RECEIPT_V1' and
         master.get('sessionDate') == config['sessionDate'] and
         master.get('productionReady') is False and
         master.get('orderTransmission') is False and
         master.get('inputPolicy') == report['inputPolicy'] and
         type(master.get('rows')) is list and
         [row.get('symbol') if type(row) is dict else None
          for row in master['rows']] == admitted,
         'FILTERED_MASTER_SCOPE_MISMATCH')

    # Replay the exact deterministic mutations in automatic_morning.FILTER_NODE.
    denied = set(blocked)
    protected = old_plan.get('protectedChartSymbols')
    scans = old_plan.get('scanChartSymbols')
    requested = old_plan.get('allRequestedChartSymbols')
    need(type(protected) is list and type(scans) is list and
         type(requested) is list and
         type(old_plan.get('g1UnscannedCount')) is int and
         type(old_plan.get('occupiedByOtherChartFunctions')) is int,
         'FILTERED_CHART_STRUCTURE')
    expected = dict(old_plan)
    expected['selectorInputSymbols'] = admitted
    expected['scanChartSymbols'] = [s for s in scans if s not in denied]
    expected['allRequestedChartSymbols'] = [
        s for s in requested if s not in denied or s in set(protected)]
    expected['g1UnscannedCount'] = old_plan['g1UnscannedCount'] + len(blocked)
    expected['arkChartsUsed'] = len(expected['allRequestedChartSymbols'])
    expected['totalChartFunctionsBudgeted'] = (
        expected['arkChartsUsed'] + expected['occupiedByOtherChartFunctions'])
    if 'entryUniverseMode' in old_plan:
        need(type(old_plan.get('reviewedEntrySymbols')) is list,
             'FILTERED_REVIEWED_SYMBOL_SCOPE')
        expected['reviewedEntrySymbols'] = [
            s for s in old_plan['reviewedEntrySymbols'] if s not in denied]
        mask, _ = load_json(config['precomputedG1Mask'])
        need(type(mask.get('observedPassCount')) is int,
             'FILTERED_MASK_PASS_COUNT')
        expected['unreviewedG1SymbolsExcludedFromEntry'] = (
            mask['observedPassCount'] - len(expected['reviewedEntrySymbols']))

    # The plan digest is checked by the native JS validator in validate_scope
    # after this helper returns. All *other* fields must match exactly now.
    expected.pop('planSha256', None)
    actual = dict(plan)
    actual.pop('planSha256', None)
    need(actual == expected and
         type(plan.get('planSha256')) is str and
         re.fullmatch(r'[a-f0-9]{64}', plan['planSha256']) is not None,
         'FILTERED_CHART_NOT_EXACT_SUBSET')
    rebuilt = dict(original, chartPlan=plan,
                   automaticVerifiedExclusion=scope)
    need(derived == rebuilt, 'FILTERED_OTHER_RECEIPT_FIELDS_CHANGED')
    return original_file

'''

def need(condition, error):
    if not condition:
        raise ValueError('NO11_WEEKLY_FILTERED_LINEAGE_' + error)

def norm(raw: bytes):
    bom = b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b''
    text = raw[len(bom):].decode('utf-8')
    line = '\r\n' if '\r\n' in text else '\n'
    text = text.replace('\r\n', '\n')
    need('\r' not in text, 'SOURCE_MIXED_LINE_ENDINGS')
    return bom, text, line

def transform(raw: bytes) -> bytes:
    bom, text, line = norm(raw)
    if MARK in text:
        need(text.count(MARK) == 1 and
             text.count('def verified_weekly_original(config):') == 1 and
             NEW in text and OLD not in text, 'INSTALLED_SOURCE_CHANGED')
        return raw
    need(text.count("def export_scope(config):\n") == 1 and
         text.count(OLD) == 1 and
         'def verified_weekly_original(config):' not in text,
         'SOURCE_ANCHOR_CHANGED')
    # Do not touch trade/collector/service functions or the original native
    # weekly validator; narrow this change to a source-file selection boundary.
    changed = text.replace('def export_scope(config):\n',
                           HELPER + 'def export_scope(config):\n', 1)
    changed = changed.replace(OLD, NEW, 1)
    need(changed.count(MARK) == 1 and
         changed.count("def verified_weekly_original(config):") == 1 and
         changed.count("return (private(config['precomputedChartReceipt']),") == 1 and
         changed.count("if 'precomputedChartReceipt' in config:") == 1 and
         "def validate_scope(session, plan_file, mask_file, master_file, now):" in changed,
         'TRANSFORM_SCOPE_UNVERIFIED')
    return bom + changed.replace('\n', line).encode('utf-8')
