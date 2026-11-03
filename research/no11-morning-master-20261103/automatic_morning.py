#!/usr/bin/env python3
"""Automatic operational input policy, NOT an independent corporate-action audit.

No manual evidence file, price entry, daily ZIP upload or review confirmation.
Reuses selected symbols and saved history. Does not change strategy/model maths,
funding, holdings, execution permission, launcher settings or send any order.

Legacy master booleans are adapter admission flags under the NAMED policy below,
not claims of human review or exhaustive absence of corporate actions. The policy
requires actual same-day source observations, no flagged near-term rights event,
and exact unadjusted daily/RSS previous-close/base-price consistency. An unknown
or mismatch cannot be made true by a user confirmation. Diagnostics stay local.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys

POLICY = 'AUTO_SELECTED_JPX_RSS_UNADJUSTED_PRICE_CONSISTENCY_V1'
RUNNER_BLOB = '4887918a01751f5107b6d6f56c4d838d75107ed2'
SECTIONS = {'東証P': 'PRIME', '東証Ｐ': 'PRIME', '東証S': 'STANDARD',
            '東証Ｓ': 'STANDARD', '東証G': 'GROWTH', '東証Ｇ': 'GROWTH'}
SHA = re.compile(r'^[a-f0-9]{64}$')
SYMBOL = re.compile(r'^[0-9A-Z]{4}\.T$')


def need(ok, code):
    if not ok:
        raise ValueError('NO11_AUTO_INPUT_' + code)


def instant(value):
    need(type(value) is str and re.fullmatch(
        r'20\d\d-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d{1,7})?\+09:00', value), 'CLOCK')
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        raise ValueError('NO11_AUTO_INPUT_CLOCK') from None


def number(value):
    need(type(value) in (str, int, float), 'PRICE_TYPE')
    try:
        n = Decimal(str(value))
    except InvalidOperation:
        raise ValueError('NO11_AUTO_INPUT_PRICE') from None
    need(n.is_finite() and 0 < n <= Decimal('1000000000'), 'PRICE')
    return n


def indexed(rows, selected):
    need(type(rows) is list and len(rows) == len(selected), 'ROW_COUNT')
    need(all(type(r) is dict and type(r.get('symbol')) is str for r in rows), 'ROW_TYPE')
    codes = [r['symbol'] for r in rows]
    need(len(set(codes)) == len(codes) and set(codes) == set(selected), 'ROW_SCOPE')
    return {r['symbol']: r for r in rows}


def event_date(raw):
    # Blank is merely "no RSS event flag" under this operational policy.
    # It is explicitly not evidence that no corporate event exists.
    need(type(raw) is str, 'EVENT_FIELD_TYPE')
    token = raw.strip()
    if not token:
        return None
    token = token.replace('/', '-')
    need(re.fullmatch(r'\d{4}-\d{2}-\d{2}', token) is not None, 'EVENT_DATE_FORMAT')
    try:
        return date.fromisoformat(token).isoformat()
    except ValueError:
        raise ValueError('NO11_AUTO_INPUT_EVENT_DATE_FORMAT') from None


def build_master(info, public, reference, daily_closes, now, public_sha, reference_sha):
    """Pure automatic admission checks. No review flags or prices from a person."""
    current = instant(now)
    session, prior, selected = info['sessionDate'], info['previousSession'], info['selectedSymbols']
    need(type(selected) is list and 1 <= len(selected) <= 47
         and all(type(s) is str and SYMBOL.fullmatch(s) for s in selected)
         and len(set(selected)) == len(selected), 'SELECTED_SCOPE')
    need(now[:10] == session and date.fromisoformat(prior) < date.fromisoformat(session), 'SESSION')
    need(SHA.fullmatch(public_sha) and SHA.fullmatch(reference_sha), 'SOURCE_DIGEST')
    need(public.get('schemaId') == 'ARK_NO11_AUTOMATIC_SELECTED_PUBLIC_SOURCES_V1'
         and public.get('sessionDate') == session and public.get('previousSession') == prior
         and public.get('selectedSymbols') == selected
         and public.get('policy') == 'JPX_CURRENT_COMMON_EQUITY_AND_NEAR_TERM_RIGHTS_EXCLUSION_V1'
         and public.get('orderTransmission') is False and public.get('productionReady') is False,
         'PUBLIC_SOURCE_CONTRACT')
    observed = instant(public.get('observedAtJst'))
    need(public['observedAtJst'][:10] == session and 0 <= (current - observed).total_seconds() <= 900,
         'PUBLIC_SOURCE_NOT_CURRENT')
    published = public.get('rightsPublishedOn')
    need(type(published) is str and prior <= published <= session
         and date.fromisoformat(session) <= date.fromisoformat(published) + timedelta(days=12),
         'RIGHTS_SOURCE_STALE')
    need(reference.get('schemaId') == 'ARK_NO11_RSS_SESSION_REFERENCE_CAPTURE_V1'
         and reference.get('sessionDate') == session
         and reference.get('source') == 'RssMarket_SELECTED_REFERENCE_READONLY'
         and reference.get('chartPlanSha256') == info['chartPlanSha256']
         and reference.get('selectedSymbols') == selected and reference.get('readOnly') is True
         and reference.get('orderTransmission') is False and reference.get('productionReady') is False,
         'RSS_REFERENCE_CONTRACT')
    started, ended = instant(reference.get('capturedAtJst')), instant(reference.get('completedAtJst'))
    need(started <= ended <= current and (ended - started).total_seconds() < 30
         and 0 <= (current - ended).total_seconds() <= 180
         and reference['capturedAtJst'][:10] == session
         and reference['completedAtJst'][:10] == session, 'RSS_REFERENCE_STALE')
    meta, prices = indexed(public.get('rows'), selected), indexed(reference.get('rows'), selected)
    need(type(daily_closes) is dict and set(daily_closes) == set(selected), 'DAILY_SCOPE')
    rows, blocked = [], []
    for symbol in selected:
        p, r = meta[symbol], prices[symbol]
        try:
            need(p.get('eligible') is True and p.get('nearTermRightsEventListed') is False,
                 'PRODUCT_OR_FLAGGED_RIGHTS')
            need(p.get('segment') in ('PRIME', 'STANDARD', 'GROWTH')
                 and type(p.get('sector')) is str and 0 < len(p['sector']) <= 100,
                 'METADATA')
            need(r.get('marketCode') == 'T' and r.get('marketDate') == session
                 and r.get('previousDate') == prior and r.get('lotShares') == 100
                 and SECTIONS.get(r.get('marketSection')) == p['segment'], 'RSS_IDENTITY')
            previous = number(r.get('previousClose'))
            need(previous == number(daily_closes[symbol]) == number(r.get('dayBasePrice')),
                 'UNADJUSTED_PRICE_MISMATCH')
            for key in ('exRightsDateRaw', 'exDividendDateRaw', 'interimExDividendDateRaw'):
                event = event_date(r.get(key))
                need(event is None or not (prior < event <= session), 'RSS_FLAGGED_EVENT')
            rows.append({'symbol': symbol, 'asOfSession': session,
                         'segment': p['segment'], 'sector': p['sector'],
                         'rawPreviousClose': r['previousClose'], 'commonEquity': True,
                         # Compatibility admission flags for the existing runtime.
                         # Their bounded machine-policy meaning is retained in the
                         # master, rather than forging an external-review receipt.
                         'corporateActionsCleared': True, 'priceBasisVerified': True})
        except (ValueError, TypeError, KeyError) as error:
            reason = str(error)
            blocked.append({'symbol': symbol, 'reason': reason if reason.startswith('NO11_AUTO_INPUT_')
                            else 'NO11_AUTO_INPUT_MALFORMED_ROW'})
    report = {'schemaId': 'ARK_NO11_AUTOMATIC_OPERATIONAL_INPUT_RESULT_V1',
              'sessionDate': session, 'inputPolicy': POLICY, 'selectedCount': len(selected),
              'passedCount': len(rows), 'blockedSymbols': blocked, 'humanReviewPerformed': False,
              'exhaustiveCorporateActionsCertified': False, 'manualEvidenceRequired': False,
              'manualPriceInputRequired': False, 'productionReady': False, 'orderTransmission': False}
    if blocked:
        return None, report
    master = {'schemaId': 'ARK_NO11_DATED_MASTER_RECEIPT_V1', 'sessionDate': session,
              'knownAtJst': now, 'rows': rows, 'referenceSourceSha256': reference_sha,
              'automaticSourceSha256': public_sha, 'inputPolicy': POLICY,
              'corporateActionReviewSource': 'AUTOMATIC_FLAGGED_EVENT_AND_UNADJUSTED_PRICE_POLICY',
              'admissionFlagsMeaning': 'NAMED_MACHINE_POLICY_PASSED_NOT_EXHAUSTIVE_CA_CLEARANCE',
              'humanReviewPerformed': False, 'exhaustiveCorporateActionsCertified': False,
              'rssFieldTimestampCertified': False, 'productionReady': False, 'orderTransmission': False}
    return master, report


DAILY_NODE = r'''import fs from 'node:fs';import {pathToFileURL} from 'node:url';
import path from 'node:path';
const [engine,run,seed,chart,mask,session]=process.argv.slice(2);
const mod=p=>import(pathToFileURL(path.join(engine,'tools',p)).href);
const {verifyWeeklyShadowScope}=await mod('no11_verified_weekly_shadow_scope.mjs');
verifyWeeklyShadowScope({runDir:run,seedDir:seed,chartFile:chart,maskFile:mask,sessionDate:session});
const {loadCaptures}=await mod('no11_rss_daily_trend_census.mjs');
const read=p=>JSON.parse(fs.readFileSync(p,'utf8').replace(/^\uFEFF/,''));
const cp=read(chart).chartPlan,plan=read(path.join(run,'plan.json'));
const selected=new Set(cp.selectorInputSymbols),out={};
for(const c of loadCaptures(run,plan))if(selected.has(c.symbol)){
 const rows=c.rows.filter(r=>r.session===cp.asOfSession);
 if(rows.length!==1)throw Error('NO11_AUTO_INPUT_DAILY_PREVIOUS_CLOSE');
 out[c.symbol]=rows[0].close;
}
console.log(JSON.stringify(out));'''


def load_runner(path):
    p = Path(path)
    need(p.is_absolute() and p.is_file(), 'RUNNER_MISSING')
    for q in (p, *p.parents):
        need(not q.is_symlink() and not (getattr(q.lstat(), 'st_file_attributes', 0) & 1024), 'RUNNER_REPARSE')
    raw = p.read_bytes()
    need(hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == RUNNER_BLOB,
         'RUNNER_CHANGED')
    spec = importlib.util.spec_from_file_location('no11_existing_morning', p)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def execute(m, handoff_file):
    handoff, hb = m.read(handoff_file)
    m.verify_receipt(handoff_file, hb, 'morning-handoff', 64)
    need(handoff.get('schemaId') == m.SCHEMA and handoff.get('orderTransmission') is False
         and handoff.get('productionReady') is False and handoff.get('datedMasterCreated') is False,
         'HANDOFF')
    need(m.clock()[:10] == handoff['sessionDate'], 'ACTUAL_SESSION_DAY')
    spec = handoff['spec']
    need(set(handoff['sourcePins']) == {'chartReceipt', 'passMask', 'previousStage'}, 'SOURCE_PINS')
    values = {}
    for key, digest in handoff['sourcePins'].items():
        value, raw = m.read(spec[key])
        need(m.sha(raw) == digest, 'SOURCE_CHANGED')
        values[key] = value
    selected, prior = m.validate_scope(spec, values['chartReceipt'], values['passMask'], values['previousStage'])
    need(selected == handoff['selectedSymbols'] and prior == handoff['previousSession'], 'HANDOFF_SCOPE')
    engine = m.safe(spec['engineRoot'], directory=True)
    daily_closes = json.loads(m.run(['node', '--input-type=module', '-', str(engine),
        str(Path(spec['chartReceipt']).parent), spec['weeklySourceRun'], spec['chartReceipt'],
        spec['passMask'], handoff['sessionDate']], 'AUTOMATIC_DAILY_SOURCE', input_text=DAILY_NODE))
    root = m.safe(spec['outputRoot'], directory=True) / 'automatic-session'
    root.mkdir(exist_ok=True)
    m.safe(root, directory=True)
    docs = root / 'public-source-documents'
    docs.mkdir(exist_ok=True)
    m.safe(docs, directory=True)
    # The prior installer put xlrd here, not into the fixed model environment.
    reader = Path(m.__file__).parent / 'xls-reader'
    old_path = list(sys.path)
    try:
        if reader.is_dir():
            sys.path.insert(0, str(m.safe(reader, directory=True)))
        public = m.helper_module().collect(selected, prior, handoff['sessionDate'], docs)
    finally:
        sys.path[:] = old_path
    public_file = m.immutable(root, 'automatic-public-source', public)
    # Actual reference collection is automatic; the operator never enters prices.
    reference_file = m.capture_reference(engine, selected, spec['chartReceipt'], root)
    reference, rb = m.read(reference_file)
    info = {'sessionDate': handoff['sessionDate'], 'previousSession': prior,
            'selectedSymbols': selected,
            'chartPlanSha256': values['chartReceipt']['chartPlan']['planSha256']}
    master, report = build_master(info, public, reference, daily_closes, m.clock(),
                                 m.sha(public_file.read_bytes()), m.sha(rb))
    report_file = m.immutable(root, 'automatic-input-result', report)
    print('AUTOMATIC_INPUT_REPORT=' + str(report_file), flush=True)
    if master is None:
        print('AUTOMATIC_INPUTS=DATA_UNAVAILABLE_OR_INCONSISTENT')
        print('BLOCKED_SYMBOL_COUNT=' + str(len(report['blockedSymbols'])))
        print('MANUAL_EVIDENCE_REQUIRED=False\nMANUAL_PRICE_INPUT_REQUIRED=False')
        print('TRADE_LAUNCHED=False\nORDER_TRANSMISSION=False')
        return None
    master_file = m.immutable(root, 'dated-master', master)
    old_path = list(sys.path)
    try:
        sys.path.insert(0, str(engine / 'tools'))
        import no11_received_session_bootstrap as b
        import no11_previous_archive_context as archive
        now = m.clock()
        need(archive.scope(Path(spec['chartReceipt']), Path(spec['passMask'])) == info, 'NATIVE_SCOPE')
        b.validate_scope(info['sessionDate'], Path(spec['chartReceipt']), Path(spec['passMask']), master_file, now)
        # Local disk replay/normalization of existing 47-symbol receipts only.
        stage = archive.stage_archive(info, Path(spec['previousCaptureDir']), now)
        stage_file = b.immutable(root, 'previous-archive-stage', stage)
        context, context_report = archive.assemble(stage, Path(spec['chartReceipt']),
            Path(spec['passMask']), master_file, root, now)
        ctx, _ = m.read(context)
        need(set(ctx.get('symbols', {})) == set(selected), 'PREVIOUS_CONTEXT_INCOMPLETE')
        config = {'schemaId': b.CONFIG, 'sessionDate': info['sessionDate'],
                  'dailyRun': str(Path(spec['chartReceipt']).parent),
                  'datedMaster': str(master_file), 'previousContext': str(context),
                  'runtimeRoot': spec['runtimeRoot'], 'h235ModelRoot': spec['h235ModelRoot'],
                  'privateRoot': str(root), 'orderIdWorkbookPath': handoff['orderIdWorkbookPath'],
                  'precomputedChartReceipt': spec['chartReceipt'], 'precomputedG1Mask': spec['passMask'],
                  'weeklySourceRun': spec['weeklySourceRun'],
                  'productionReady': False, 'orderTransmission': False}
        b.validate_config(config)
        config_file = b.immutable(root, 'bootstrap-ready-inputs', config)
    finally:
        sys.path[:] = old_path
    print('MORNING_PREPARED_BOOTSTRAP=' + str(config_file))
    print('MORNING_DATED_MASTER=' + str(master_file))
    print('MORNING_PREVIOUS_CONTEXT=' + str(context))
    print('AUTOMATIC_INPUTS=COMPLETE_NOT_LIVE_STARTED')
    print('MANUAL_EVIDENCE_REQUIRED=False\nMANUAL_PRICE_INPUT_REQUIRED=False')
    print('TRADE_LAUNCHED=False\nORDER_TRANSMISSION=False')
    return config_file


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--runner', required=True, type=Path)
    p.add_argument('--handoff', required=True, type=Path)
    a = p.parse_args(argv)
    return execute(load_runner(a.runner), a.handoff)


if __name__ == '__main__':
    try:
        if main() is None:
            raise SystemExit(2)
    except Exception as error:
        msg = str(error)
        if not re.fullmatch(r'(?:NO11|P1_RSS)_[A-Z0-9_]+', msg):
            msg = 'NO11_AUTO_INPUT_SOURCE_OR_RUNTIME_UNAVAILABLE'
        print('AUTOMATIC_INPUTS=BLOCKED|' + msg, file=sys.stderr)
        print('MANUAL_EVIDENCE_REQUIRED=False\nMANUAL_PRICE_INPUT_REQUIRED=False', file=sys.stderr)
        print('TRADE_LAUNCHED=False\nORDER_TRANSMISSION=False', file=sys.stderr)
        raise SystemExit(2)
