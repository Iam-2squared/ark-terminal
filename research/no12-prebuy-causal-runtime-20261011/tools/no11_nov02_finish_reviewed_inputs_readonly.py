#!/usr/bin/env python3
"""Nov 2 actual RSS + independent 24-equity review -> dated master/previous.

Only orchestrates the EXISTING pinned no11_prepare_received_inputs validator.
The 2026-09-30 JPX monthly list is NOT same-day clearance. Without actual
2026-11-02 RSS and independent evidence for ALL 24, fail closed. No Excel,
account data, order transport, broker configuration, approvals or fitting.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
import tempfile

SESSION = '2026-11-02'
EXPECTED = frozenset((
 '3753.T','4478.T','2002.T','8163.T','5273.T','2810.T',
 '1914.T','7678.T','9245.T','2705.T','9900.T','7581.T',
 '4733.T','8070.T','2004.T','4502.T','4565.T','4544.T',
 '7083.T','6532.T','7821.T','219A.T','8923.T','3023.T',
))


def need(ok, why):
    if not ok:
        raise ValueError('NO11_NOV02_FINISH_' + why)


def safe(p, directory=False):
    need(isinstance(p, Path) and p.is_absolute(), 'ABSOLUTE_PRIVATE_PATH_REQUIRED')
    need(not p.is_symlink() and not any(x.is_symlink() for x in p.parents),
         'PATH_SYMLINK_FORBIDDEN')
    need(p.is_dir() if directory else p.is_file(), 'PATH_MISSING')
    if not directory:
        need(0 < p.stat().st_size <= 12_000_000, 'SOURCE_BYTES')
    return p.resolve(strict=True)


def load(p, prefix=None):
    p = safe(p)
    raw = p.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    if prefix:
        need(p.name == prefix + '-' + sha + '.json', 'SOURCE_HASH_NOT_IMMUTABLE')
    value = json.loads(raw.decode('utf-8-sig'))
    need(type(value) is dict, 'SOURCE_JSON_OBJECT')
    return value


def jst():
    return datetime.now(timezone(timedelta(hours=9))).isoformat(timespec='milliseconds')


def verify(bridge, rss, evidence, now):
    need(now[:10] == SESSION, 'ONLY_ACTUAL_SESSION_DATE')
    need(bridge.get('schemaId') == 'ARK_NO11_NOV02_24_BOOTSTRAP_SOURCE_BRIDGE_V1'
         and bridge.get('sourceMode') == 'VERIFIED_STATIC_INPUTS_ONLY_NO_DATED_MASTER'
         and bridge.get('selectedCount') == 24
         and bridge.get('executableBootstrapCreated') is False
         and bridge.get('tradePermissionChanged') is False
         and bridge.get('orderTransmission') is False,
         'VERIFIED_STATIC_SOURCE_BRIDGE_REQUIRED')
    selected = bridge.get('selectedSymbols')
    need(type(selected) is list and len(selected) == 24 and
         len(set(selected)) == 24 and set(selected) == EXPECTED,
         'EXACT_24_REQUIRED')
    fields = bridge.get('knownBootstrapFields')
    need(type(fields) is dict and
         fields.get('schemaId') == 'ARK_NO11_READONLY_BOOTSTRAP_CONFIG_V1'
         and fields.get('sessionDate') == SESSION
         and fields.get('orderTransmission') is False
         and fields.get('productionReady') is False
         and 'brokerExecutionConfig' not in fields,
         'ORDER_OFF_FIELDS_REQUIRED')
    need(rss.get('schemaId') == 'ARK_NO11_RSS_SESSION_REFERENCE_CAPTURE_V1'
         and rss.get('source') == 'RssMarket_SELECTED_REFERENCE_READONLY'
         and rss.get('sessionDate') == SESSION
         and rss.get('selectedSymbols') == selected
         and type(rss.get('rows')) is list and len(rss['rows']) == 24
         and type(rss.get('chartPlanSha256')) is str
         and re.fullmatch(r'[a-f0-9]{64}',rss['chartPlanSha256']) is not None
         and rss.get('readOnly') is True
         and rss.get('productionReady') is False
         and rss.get('orderTransmission') is False,
         'OBSERVED_24_RSS_REFERENCE_REQUIRED')
    need(evidence.get('schemaId') == 'ARK_NO11_SESSION_SECURITY_EVIDENCE_V1'
         and evidence.get('validForSession') == SESSION
         and evidence.get('reviewStatus') == 'EXTERNALLY_REVIEWED'
         and type(evidence.get('rows')) is list
         and evidence.get('productionReady') is False
         and evidence.get('orderTransmission') is False,
         'INDEPENDENT_EXTERNAL_REVIEW_REQUIRED')
    members = [r.get('symbol') for r in evidence['rows'] if type(r) is dict]
    need(len(members) == len(evidence['rows']) and
         len(set(members)) == len(members) and EXPECTED <= set(members),
         'EXTERNAL_REVIEW_MISSING_24')
    # The original adapter validates issuer-document SHA256, corporate actions,
    # ordinary equity, actual RSS session/date, price basis and previous close.
    return fields


def complete(a):
    now = jst()
    need(now[:10] == SESSION, 'ONLY_ACTUAL_SESSION_DATE')
    engine = safe(a.engine, True)
    private = safe(a.private_root, True)
    output = safe(a.output, True)
    docs = safe(a.evidence_documents, True)
    minutes = safe(a.previous_capture, True)
    need(private == output or private in output.parents,
         'OUTPUT_OUTSIDE_PRIVATE_ROOT')
    need(private not in engine.parents and engine not in private.parents,
         'PRIVATE_PUBLIC_ROOT_OVERLAP')
    bridge = load(a.bridge, 'bootstrap-source-only')
    rss = load(a.reference, 'session-reference')
    evidence = load(a.security_evidence)
    known = verify(bridge, rss, evidence, now)
    sys.path.insert(0, str(engine / 'tools'))
    import no11_previous_archive_context as archive
    import no11_prepare_received_inputs as original
    import no11_received_session_bootstrap as bootstrap

    receipt = safe(Path(known['precomputedChartReceipt']))
    mask = safe(Path(known['precomputedG1Mask']))
    info = archive.scope(receipt, mask)
    need(info['sessionDate'] == SESSION and
         info['selectedSymbols'] == bridge['selectedSymbols'],
         'PINNED_CHART_SCOPE_CHANGED')
    runtime = private / 'nov02-24-received-session'
    need(not runtime.is_symlink(), 'PRIVATE_RUNTIME_SYMLINK')
    runtime.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='unresolved-master-',dir=output) as t:
        # Intentionally invalid temp config: impossible to use before
        # the existing original adapter supplies a real master/context.
        template = dict(known)
        template.update({
         'privateRoot':str(runtime),
         'datedMaster':str(Path(t)/'DOES_NOT_EXIST_DATED_MASTER'),
         'previousContext':str(Path(t)/'DOES_NOT_EXIST_CONTEXT'),
         'samples':390,'historyBars':120,'warmupSeconds':20,
        })
        filename = Path(t)/'NOT_A_LIVE_BOOTSTRAP.json'
        filename.write_text(json.dumps(template,ensure_ascii=False),encoding='utf-8')
        config, report = original.prepare(
            plan_file=receipt,mask_file=mask,reference_file=a.reference,
            evidence_file=a.security_evidence,evidence_documents=docs,
            capture_dir=minutes,config_file=filename,output_root=output,
            prepared_at=now,
        )
    cfg, _ = bootstrap.load_json(config)
    detail, _ = bootstrap.load_json(report)
    master, _ = bootstrap.load_json(detail['master'])
    previous, _ = bootstrap.load_json(detail['previousContext'])
    need(detail['selectedCount'] == 24 and detail['masterRows'] == 24 and
         detail['stagedPreviousSymbols'] == 24 and
         set(previous.get('symbols', {})) == EXPECTED and
         set(x['symbol'] for x in master['rows']) == EXPECTED and
         cfg['orderTransmission'] is False and
         cfg['productionReady'] is False and
         'brokerExecutionConfig' not in cfg,
         '24_READONLY_COMPLETION_NOT_VERIFIED')
    return config,report,detail['master'],detail['previousContext']


def offline():
    bridge={
      'schemaId':'ARK_NO11_NOV02_24_BOOTSTRAP_SOURCE_BRIDGE_V1',
      'sourceMode':'VERIFIED_STATIC_INPUTS_ONLY_NO_DATED_MASTER',
      'selectedCount':24,'selectedSymbols':sorted(EXPECTED),
      'knownBootstrapFields':{'schemaId':'ARK_NO11_READONLY_BOOTSTRAP_CONFIG_V1',
          'sessionDate':SESSION,'orderTransmission':False,'productionReady':False},
      'executableBootstrapCreated':False,'tradePermissionChanged':False,
      'orderTransmission':False,
    }
    not_reviewed={'schemaId':'ARK_NO11_SESSION_SECURITY_EVIDENCE_V1',
      'validForSession':SESSION,'reviewStatus':'NOT_REVIEWED',
      'productionReady':False,'orderTransmission':False,'rows':[]}
    no_rss={'schemaId':'ARK_NO11_RSS_SESSION_REFERENCE_CAPTURE_V1',
      'sessionDate':SESSION,'source':'RssMarket_SELECTED_REFERENCE_READONLY',
      'selectedSymbols':sorted(EXPECTED),'rows':[{}]*24,
      'chartPlanSha256':'0'*64,'readOnly':True,
      'productionReady':False,'orderTransmission':False}
    denied = False
    try:verify(bridge,no_rss,not_reviewed,SESSION+'T09:01:00.000+09:00')
    except ValueError as exc:
        denied = str(exc) == 'NO11_NOV02_FINISH_INDEPENDENT_EXTERNAL_REVIEW_REQUIRED'
    need(denied and len(EXPECTED)==24, 'UNREVIEWED_REJECTED_OFFLINE')
    print('NO11_NOV02_FINISH_OFFLINE_SELFTEST=PASS_MISSING_REVIEW_BLOCKED')
    print('ORDER_TRANSMISSION=False')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--offline-selftest',action='store_true')
    for key in ('bridge','reference','security-evidence','evidence-documents',
                'previous-capture','engine','private-root','output'):
        parser.add_argument('--'+key,type=Path)
    a=parser.parse_args()
    if a.offline_selftest:
        offline()
        return
    need(all(getattr(a,k) is not None for k in (
        'bridge','reference','security_evidence','evidence_documents',
        'previous_capture','engine','private_root','output')),
         'MISSING_REVIEW_DOCUMENTS_OR_RSS')
    config,report,master,previous=complete(a)
    print('NO11_NOV02_MASTER='+str(master))
    print('NO11_NOV02_PREVIOUS_CONTEXT='+str(previous))
    print('NO11_NOV02_READONLY_BOOTSTRAP='+str(config))
    print('NO11_NOV02_REVIEW_REPORT='+str(report))
    print('NO11_NOV02_BROKER_LIVE_CONFIG=NOT_CREATED')
    print('ORDER_TRANSMISSION=False')


if __name__=='__main__':
    try:main()
    except (OSError,ValueError,KeyError,TypeError,RuntimeError,ImportError) as exc:
        err=str(exc)
        if not re.fullmatch(r'(?:NO11_NOV02_FINISH|NO11_INPUT_PREP|NO11_PREVIOUS_ARCHIVE|P1_RSS|NO11_BOOTSTRAP|NO11_PIPELINE)_[A-Z0-9_]+',err):
            err='NO11_NOV02_FINISH_UNVERIFIED_PRIVATE_SOURCE'
        print('NO11_NOV02_FINISH=BLOCKED|'+err,file=sys.stderr)
        print('ORDER_TRANSMISSION=False')
        raise SystemExit(2)
