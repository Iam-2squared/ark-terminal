#!/usr/bin/env python3
"""Selected-source preparation and native same-day master/context assembly.

No all-market scan, historical RSS recollection, model fitting, account adoption,
shadow run, order permission or trading process is performed. Public-source
observations are NOT an externally reviewed security-evidence receipt.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

JST = timezone(timedelta(hours=9))
SCHEMA = 'ARK_NO11_MORNING_MASTER_HANDOFF_V1'
HELPER_BLOB = '18fa90ab91b0a75fae90184ddc5a1d470d623bdf'
SYMBOL = re.compile(r'^[0-9A-Z]{4}\.T$')
PATHS = ('engineRoot', 'chartReceipt', 'passMask', 'previousStage',
         'previousCaptureDir', 'runtimeRoot', 'h235ModelRoot',
         'weeklySourceRun', 'settingsFile', 'outputRoot')
DIRS = {'engineRoot', 'previousCaptureDir', 'runtimeRoot', 'h235ModelRoot',
        'weeklySourceRun', 'outputRoot'}


def need(ok, code):
    if not ok:
        raise ValueError('NO11_MORNING_' + code)


def clock():
    return datetime.now(JST).isoformat(timespec='milliseconds')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def blob(raw):
    return hashlib.sha1(b'blob ' + str(len(raw)).encode('ascii') + b'\0' + raw).hexdigest()


def safe(path, *, directory=False, maximum=20_000_000):
    p = Path(path)
    need(p.is_absolute(), 'ABSOLUTE_PATH_REQUIRED')
    for q in (p, *p.parents):
        if q.exists() or q.is_symlink():
            st = q.lstat()
            need(not q.is_symlink() and not (getattr(st, 'st_file_attributes', 0) & 1024),
                 'REPARSE_PATH_BLOCKED')
    need(p.is_dir() if directory else p.is_file(), 'PATH_MISSING')
    if not directory:
        need(0 < p.stat().st_size <= maximum, 'FILE_SIZE')
    return p


def unique(pairs):
    result = {}
    for key, value in pairs:
        need(key not in result, 'DUPLICATE_JSON_FIELD')
        result[key] = value
    return result


def read(path, maximum=20_000_000):
    raw = safe(path, maximum=maximum).read_bytes()
    obj = json.loads(raw.decode('utf-8-sig'), object_pairs_hook=unique,
                     parse_constant=lambda value: need(False, 'NONFINITE_JSON'))
    need(type(obj) is dict, 'JSON_OBJECT_REQUIRED')
    return obj, raw


def immutable(root, prefix, obj):
    root = safe(root, directory=True)
    raw = (json.dumps(obj, ensure_ascii=False, separators=(',', ':'),
                      allow_nan=False) + '\n').encode('utf-8')
    dest = root / (prefix + '-' + sha(raw) + '.json')
    need(not dest.is_symlink(), 'OUTPUT_SYMLINK')
    if dest.exists():
        need(dest.read_bytes() == raw, 'IMMUTABLE_OUTPUT_CHANGED')
    else:
        with dest.open('xb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
    return dest


def verify_receipt(path, raw, prefix, digits):
    need(Path(path).name == prefix + '-' + sha(raw)[:digits] + '.json',
         'SOURCE_RECEIPT_HASH_MISMATCH')


def validate_scope(spec, chart, mask, stage):
    session = spec['sessionDate']
    date.fromisoformat(session)
    p = chart.get('chartPlan', {})
    selected = p.get('selectorInputSymbols')
    prior = p.get('asOfSession')
    need(type(prior) is str and date.fromisoformat(prior) < date.fromisoformat(session),
         'PREVIOUS_SESSION')
    for obj, schema in ((chart, 'ARK_NO11_CHART50_PRIVATE_EXPORT_RECEIPT_V1'),
                        (mask, 'ARK_NO11_DAILY_OBSERVED_PASS_ONLY_SHADOW_V1'),
                        (stage, 'ARK_NO11_PREVIOUS_ARCHIVE_STAGE_V1')):
        need(obj.get('schemaId') == schema and obj.get('orderTransmission') is False
             and obj.get('productionReady') is False, 'SOURCE_SCHEMA_OR_MODE')
    need(p.get('sessionDate') == session and p.get('orderTransmission') is False
         and p.get('productionReady') is False and type(selected) is list
         and 1 <= len(selected) <= 47 and len(set(selected)) == len(selected)
         and all(type(s) is str and SYMBOL.fullmatch(s) for s in selected),
         'SELECTED_SCOPE')
    passed = mask.get('observedPassSymbols', [])
    need(mask.get('asOfSession') == prior and mask.get('planId') == p.get('sourcePlanId')
         and mask.get('observedPassCount') == len(passed)
         and all(s in passed for s in selected), 'MASK_SCOPE')
    need(stage.get('sessionDate') == session and stage.get('previousSession') == prior
         and stage.get('chartPlanSha256') == p.get('planSha256')
         and stage.get('selectedSymbols') == selected
         and type(stage.get('symbols')) is dict
         and all(s in stage['symbols'] for s in selected), 'SAVED_PREVIOUS_SCOPE')
    return selected, prior


def run(argv, label, *, input_text=None, timeout=180):
    result = subprocess.run(argv, input=input_text, capture_output=True, text=True,
                            encoding='utf-8', errors='replace', timeout=timeout,
                            env={**os.environ, 'PYTHONUTF8': '1', 'PYTHONDONTWRITEBYTECODE': '1'})
    if result.returncode:
        # Emit original diagnostic codes, never raw private file contents.
        for line in (result.stdout + '\n' + result.stderr).splitlines():
            if re.fullmatch(r'(?:NO11|P1_RSS|P1_FORWARD)_[A-Z0-9_=|:.-]+', line):
                print(line, flush=True)
        raise ValueError('NO11_MORNING_' + label + '_FAILED')
    return result.stdout


def native_scope(engine, chart_path, mask_path):
    # stdin is passed directly by Python, not through PowerShell -c quoting.
    module = safe(Path(engine) / 'runtime/no11_rss_chart_50_prescreen.mjs')
    script = '''import fs from 'node:fs';import {pathToFileURL} from 'node:url';
const [module,c,m]=process.argv.slice(2);
const {validateNo11Chart50Plan}=await import(pathToFileURL(module).href);
const read=p=>JSON.parse(fs.readFileSync(p,'utf8').replace(/^\\uFEFF/,''));
const p=read(c).chartPlan;
console.log(JSON.stringify(validateNo11Chart50Plan({chartPlan:p,mask:read(m),sessionDate:p.sessionDate})));'''
    return json.loads(run(['node', '--input-type=module', '-', str(module),
                           str(chart_path), str(mask_path)], 'NATIVE_SCOPE', input_text=script))


def helper_module():
    file = safe(Path(__file__).with_name('no11_auto_master_sources.py'), maximum=100_000)
    need(blob(file.read_bytes()) == HELPER_BLOB, 'PUBLIC_HELPER_HASH')
    spec = importlib.util.spec_from_file_location('ark_morning_public_sources', file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def safe_reason(error):
    message = str(error)
    if re.fullmatch(r'(?:NO11|P1_RSS|P1_FORWARD)_[A-Z0-9_]+', message):
        return message
    return 'NO11_MORNING_SOURCE_OR_RUNTIME_ERROR'


def collect_public(helper, selected, prior, session, root):
    documents, rows, blockers = [], [], []
    rights, publication = None, None
    print('MASTER_PUBLIC_SOURCES=START', flush=True)
    try:
        raw, receipt = helper.fetch(helper.INDEX, root)
        documents.append(receipt)
        publication, url = helper.rights_link(raw.decode('utf-8-sig'), prior, session, clock()[:10])
        raw, receipt = helper.fetch(url, root)
        documents.append(receipt)
        rights = set(helper.parse_rights(raw))
        print('MASTER_RIGHTS_PUBLICATION=' + publication, flush=True)
    except Exception as error:
        blockers.append(safe_reason(error))
        print('MASTER_RIGHTS_SOURCE=UNRESOLVED', flush=True)
    for index, symbol in enumerate(selected, 1):
        try:
            raw, receipt = helper.fetch(helper.SEARCH + symbol[:4], root)
            documents.append(receipt)
            row = helper.parse_company(raw.decode('utf-8-sig'), symbol)
            row['listingSourceSha256'] = receipt['sha256']
            row['observedAtJst'] = receipt['capturedAtJst']
            row['nearTermRightsEventListed'] = None if rights is None else symbol in rights
        except Exception as error:
            row = {'symbol': symbol, 'eligible': False, 'reason': safe_reason(error),
                   'nearTermRightsEventListed': None}
        # Preserve the existing source interpretation, but NEVER convert it to
        # commonEquity/corporateActionsCleared/priceBasisVerified certification.
        row['reviewStatus'] = 'NOT_REVIEWED'
        rows.append(row)
        print('MASTER_LISTING_PROGRESS=' + str(index) + '/' + str(len(selected)), flush=True)
        time.sleep(0.15)
    return {'schemaId': 'ARK_NO11_MORNING_PUBLIC_SOURCE_BASIS_V1',
            'sessionDate': session, 'previousSession': prior, 'observedAtJst': clock(),
            'selectedSymbols': selected, 'rows': rows, 'documents': documents,
            'rightsPublishedOn': publication, 'rightsSourceParsed': rights is not None,
            'sourceBlockers': blockers, 'reviewStatus': 'NOT_REVIEWED',
            'corporateActionReviewPerformed': False, 'priceBasisCertified': False,
            'datedMasterCreated': False, 'productionReady': False, 'orderTransmission': False}


def prepare(spec_file):
    spec, _ = read(spec_file, 100_000)
    need(set(spec) == {'sessionDate', *PATHS}, 'SPEC_FIELDS')
    for name in PATHS:
        safe(spec[name], directory=name in DIRS)
    engine, out = Path(spec['engineRoot']), Path(spec['outputRoot'])
    need(engine != out and engine not in out.parents, 'OUTPUT_INSIDE_ENGINE')
    need(clock()[:10] <= spec['sessionDate'], 'TARGET_SESSION_PASSED')
    chart, cb = read(spec['chartReceipt'])
    mask, mb = read(spec['passMask'])
    stage, ab = read(spec['previousStage'])
    verify_receipt(spec['chartReceipt'], cb, 'no11-chart50-private', 16)
    verify_receipt(spec['passMask'], mb, 'no11-observed-pass-watch', 16)
    verify_receipt(spec['previousStage'], ab, 'previous-archive-stage', 64)
    selected, prior = validate_scope(spec, chart, mask, stage)
    need(native_scope(engine, spec['chartReceipt'], spec['passMask']) == selected,
         'NATIVE_SELECTED_SCOPE_DIFFERS')
    settings, _ = read(spec['settingsFile'], 100_000)
    need(settings.get('schemaId') == 'ARK_NO11_UNIFIED_LAUNCHER_SETTINGS_V1'
         and settings.get('automaticOrderAuthorization') is False
         and settings.get('orderTransmission') is False, 'LAUNCHER_SETTINGS_MODE')
    safe(settings['orderIdWorkbookPath'], maximum=100_000_000)
    # Check the saved stage's checkpoint link; no historical RSS recapture.
    checkpoints = sorted(Path(spec['previousCaptureDir']).glob('progress-*.json'))
    need(bool(checkpoints), 'PREVIOUS_CHECKPOINT_MISSING')
    progress, pb = read(checkpoints[-1])
    need(sha(pb) == stage['progressSha256'] and progress.get('completed') == len(selected)
         and progress.get('requested') == len(selected), 'PREVIOUS_CAPTURE_LINK')
    docs = out / 'public-source-documents'
    docs.mkdir(exist_ok=True)
    safe(docs, directory=True)
    basis = collect_public(helper_module(), selected, prior, spec['sessionDate'], docs)
    basis_path = immutable(out, 'public-master-basis', basis)
    handoff = {'schemaId': SCHEMA, 'sessionDate': spec['sessionDate'],
               'previousSession': prior, 'selectedSymbols': selected, 'spec': spec,
               'sourcePins': {'chartReceipt': sha(cb), 'passMask': sha(mb),
                              'previousStage': sha(ab)},
               'publicSourceBasis': str(basis_path), 'publicSourceBasisSha256': sha(basis_path.read_bytes()),
               'orderIdWorkbookPath': settings['orderIdWorkbookPath'],
               'historicalRecaptureRequired': False, 'fullUniverseRescanRequired': False,
               'reviewStatus': 'NOT_REVIEWED', 'datedMasterCreated': False,
               'productionReady': False, 'orderTransmission': False}
    path = immutable(out, 'morning-handoff', handoff)
    listed = sum('listingSourceSha256' in row for row in basis['rows'])
    print('MASTER_LISTING_SOURCES=' + str(listed) + '/' + str(len(selected)))
    print('MASTER_RIGHTS_SOURCE_PARSED=' + str(basis['rightsSourceParsed']))
    print('MASTER_SOURCE_BASIS=' + str(basis_path))
    print('MORNING_HANDOFF=' + str(path))
    print('MASTER_SOURCE_PREP=' + ('COMPLETE_UNREVIEWED' if listed == len(selected)
                                  and basis['rightsSourceParsed'] else 'PARTIAL_UNREVIEWED'))
    print('DATED_MASTER_CREATED=False\nHISTORICAL_DATA_RECAPTURED=False\nORDER_TRANSMISSION=False')
    return path


def validate_day_and_evidence(handoff, evidence, now):
    need(handoff.get('schemaId') == SCHEMA and handoff.get('orderTransmission') is False,
         'HANDOFF_SCHEMA')
    day = handoff['sessionDate']
    need(now[:10] == day, 'ACTUAL_SESSION_DAY_REQUIRED')
    need(evidence.get('schemaId') == 'ARK_NO11_SESSION_SECURITY_EVIDENCE_V1'
         and evidence.get('validForSession') == day
         and evidence.get('reviewStatus') == 'EXTERNALLY_REVIEWED'
         and evidence.get('productionReady') is False
         and evidence.get('orderTransmission') is False, 'GENUINE_REVIEWED_EVIDENCE_REQUIRED')
    rows = evidence.get('rows')
    need(type(rows) is list and all(type(row) is dict for row in rows), 'EVIDENCE_ROWS')
    codes = [row.get('symbol') for row in rows]
    need(len(codes) == len(set(codes)) and set(handoff['selectedSymbols']) <= set(codes),
         'EVIDENCE_SELECTED_SCOPE')


def capture_reference(engine, selected, chart, root):
    symbols = root / ('reference-symbols-' + sha(('\n'.join(selected) + '\n').encode()) + '.txt')
    content = ('\n'.join(selected) + '\n').encode('utf-8')
    if symbols.exists():
        need(symbols.read_bytes() == content, 'SYMBOL_FILE_CHANGED')
    else:
        with symbols.open('xb') as stream:
            stream.write(content)
    collector = safe(Path(engine) / 'windows/Capture-No11SessionReferenceReadOnly.ps1')
    print('MORNING_STAGE=ACTUAL_DAY_RSS_REFERENCE', flush=True)
    output = run(['powershell.exe', '-NoProfile', '-NonInteractive', '-ExecutionPolicy',
                  'Bypass', '-File', str(collector), '-SymbolsFile', str(symbols),
                  '-ChartPlanFile', str(chart), '-OutputRoot', str(root), '-WarmupSeconds', '20'],
                 'REFERENCE_CAPTURE', timeout=240)
    lines = [x.split('=', 1)[1] for x in output.splitlines()
             if x.startswith('NO11_SESSION_REFERENCE_FILE=')]
    need(len(lines) == 1, 'REFERENCE_RECEIPT_NOT_UNIQUE')
    return safe(lines[0])


def finalize(handoff_file, evidence_file, evidence_documents, reference_file=None):
    handoff, hb = read(handoff_file)
    verify_receipt(handoff_file, hb, 'morning-handoff', 64)
    evidence, _ = read(evidence_file)
    validate_day_and_evidence(handoff, evidence, clock())
    spec = handoff['spec']
    for key, digest in handoff['sourcePins'].items():
        need(sha(safe(spec[key]).read_bytes()) == digest, 'SAVED_SOURCE_CHANGED')
    root = safe(spec['outputRoot'], directory=True) / 'actual-session'
    root.mkdir(exist_ok=True)
    safe(root, directory=True)
    tools = safe(Path(spec['engineRoot']) / 'tools', directory=True)
    sys.path.insert(0, str(tools))
    import no11_prepare_received_inputs as native
    # Preserve the exact existing external-document contract; source observations
    # from prepare() cannot be relabelled as reviewed clearance.
    native.verify_documents(evidence, Path(evidence_documents))
    reference = safe(reference_file) if reference_file else capture_reference(
        spec['engineRoot'], handoff['selectedSymbols'], spec['chartReceipt'], root)
    template = {'schemaId': 'ARK_NO11_READONLY_BOOTSTRAP_CONFIG_V1',
                'sessionDate': handoff['sessionDate'], 'dailyRun': str(Path(spec['chartReceipt']).parent),
                'runtimeRoot': spec['runtimeRoot'], 'h235ModelRoot': spec['h235ModelRoot'],
                'privateRoot': str(root), 'orderIdWorkbookPath': handoff['orderIdWorkbookPath'],
                'precomputedChartReceipt': spec['chartReceipt'], 'precomputedG1Mask': spec['passMask'],
                'weeklySourceRun': spec['weeklySourceRun'],
                'productionReady': False, 'orderTransmission': False}
    template_file = immutable(root, 'input-template-not-runnable', template)
    print('MORNING_STAGE=NATIVE_MASTER_AND_PREVIOUS_CONTEXT', flush=True)
    config, report = native.prepare(
        plan_file=Path(spec['chartReceipt']), mask_file=Path(spec['passMask']),
        reference_file=reference, evidence_file=Path(evidence_file),
        evidence_documents=Path(evidence_documents), capture_dir=Path(spec['previousCaptureDir']),
        config_file=template_file, output_root=root, prepared_at=clock())
    summary, _ = read(report)
    need(summary.get('selectedCount') == len(handoff['selectedSymbols'])
         and summary.get('masterRows') == len(handoff['selectedSymbols']), 'PREPARED_SCOPE_INCOMPLETE')
    context, _ = read(summary['previousContext'])
    need(type(context.get('symbols')) is dict and
         set(handoff['selectedSymbols']) <= set(context['symbols']), 'CONTEXT_PARTIAL_NOT_READY')
    print('MORNING_PREPARED_BOOTSTRAP=' + str(config))
    print('MORNING_DATED_MASTER=' + str(summary['master']))
    print('MORNING_PREVIOUS_CONTEXT=' + str(summary['previousContext']))
    print('MORNING_INPUT_CHAIN=COMPLETE_NOT_LIVE_STARTED')
    print('LAUNCHER_REGISTERED=False\nTRADE_LAUNCHED=False\nORDER_TRANSMISSION=False')
    return config


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    commands = p.add_subparsers(dest='command', required=True)
    before = commands.add_parser('prepare')
    before.add_argument('--spec', type=Path, required=True)
    after = commands.add_parser('finalize')
    after.add_argument('--handoff', type=Path, required=True)
    after.add_argument('--security-evidence', type=Path, required=True)
    after.add_argument('--evidence-documents', type=Path, required=True)
    after.add_argument('--reference-file', type=Path)
    a = p.parse_args(argv)
    if a.command == 'prepare':
        prepare(a.spec)
    else:
        finalize(a.handoff, a.security_evidence, a.evidence_documents, a.reference_file)


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print('MORNING_MASTER=BLOCKED|' + safe_reason(error), file=sys.stderr)
        print('TRADE_LAUNCHED=False\nORDER_TRANSMISSION=False', file=sys.stderr)
        raise SystemExit(2)
