"""Read saved decision evidence without engine imports, orders, or DB writes.

Uses SQLite mode=ro + query_only with one read transaction. Never immutable=1
for a changing WAL database, never copies only its main file, never checkpoints
or changes journal mode. SQLite may use existing WAL/shared-memory machinery;
this is a logical read-only query, not a claim of zero filesystem activity.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sqlite3


class AuditError(ValueError):
    pass


def need(ok, code):
    if not ok:
        raise AuditError('NO11_READONLY_AUDIT_' + code)


def safe(path, directory=False):
    p = Path(path)
    need(p.is_absolute(), 'ABSOLUTE_PATH_REQUIRED')
    for item in (p, *p.parents):
        if item.exists() or item.is_symlink():
            need(not item.is_symlink() and not (getattr(item.lstat(), 'st_file_attributes', 0) & 1024), 'UNSAFE_PATH')
    need(p.is_dir() if directory else p.is_file(), 'SOURCE_MISSING')
    return p


def parse(raw):
    need(0 < len(raw) <= 25000000, 'SOURCE_SIZE')
    def unique(pairs):
        result = {}
        for key, value in pairs:
            need(key not in result, 'DUPLICATE_KEY')
            result[key] = value
        return result
    try:
        obj = json.loads(raw.decode('utf-8-sig'), object_pairs_hook=unique,
                         parse_constant=lambda value: (_ for _ in ()).throw(AuditError('NO11_READONLY_AUDIT_NONFINITE')))
    except (UnicodeError, json.JSONDecodeError):
        raise AuditError('NO11_READONLY_AUDIT_JSON_INVALID') from None
    need(type(obj) is dict, 'OBJECT_REQUIRED')
    return obj


def read(path):
    return parse(safe(path).read_bytes())


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     allow_nan=False, separators=(',', ':')).encode('utf-8')).hexdigest()


def database_summary(path, session):
    db = safe(path)
    con = sqlite3.connect(db.resolve().as_uri() + '?mode=ro', uri=True, timeout=3)
    try:
        con.execute('PRAGMA query_only=ON')
        con.execute('BEGIN')
        saved = con.execute('SELECT body,sha FROM broker_state WHERE singleton=1').fetchone()
        need(saved is not None, 'STATE_MISSING')
        state = parse(saved[0].encode('utf-8'))
        need(state.get('sessionDate') == session and digest(state) == saved[1], 'STATE_IDENTITY_OR_HASH')
        count = con.execute('SELECT COUNT(*) FROM broker_events').fetchone()[0]
        need(type(count) is int and 0 <= count <= 50000, 'EVENT_LIMIT')
        records = []
        explained = set()
        for payload, in con.execute('SELECT payload FROM broker_events ORDER BY seq'):
            event = parse(payload.encode('utf-8'))
            value = event.get('value')
            if not (event.get('name', '').startswith('capital.decision.') and
                    type(value) is dict and value.get('schemaId') == 'ARK_NO11_CAPITAL_DECISION_AUDIT_V1'):
                continue
            need(value.get('sessionDate') == session and value.get('orderTransmission') is False,
                 'DECISION_CONTRACT')
            need(type(value.get('candidates')) is list, 'DECISION_ROWS')
            for row in value['candidates']:
                need(type(row) is dict and type(row.get('candidateId')) is str and
                     re.fullmatch('[a-f0-9]{64}', row['candidateId']) is not None, 'CANDIDATE_ID')
                code = row.get('disposition')
                need(type(code) is str and re.fullmatch('[A-Z0-9_]{1,100}', code), 'DISPOSITION')
                explained.add(row['candidateId'])
                records.append({'candidateToken': row['candidateId'][:12],
                                'decisionAtJst': row.get('decisionAtJst'),
                                'evaluatedAtJst': row.get('capitalEvaluatedAtJst'),
                                'h235Admitted': row.get('h235Admitted'),
                                'disposition': code})
        points = state.get('sourceCheckpoints', {})
        consumed = points.get('capital.consumed', {}).get('value', {})
        need(type(consumed) is dict, 'CONSUMED_SHAPE')
        unknown = len(set(consumed) - explained)
        orders = state.get('orders', {})
        commands = state.get('commands', {})
        need(type(orders) is dict and type(commands) is dict, 'LEDGER_SHAPE')
        return {'schemaId': 'ARK_NO11_DECISION_AUDIT_SUMMARY_V1', 'sessionDate': session,
                'ledgerClock': state.get('clock'), 'consumedCount': len(consumed),
                'legacyConsumedWithoutReason': unknown,
                'historicalReasonsReconstructed': False,
                'decisionCounts': dict(Counter(r['disposition'] for r in records)),
                'decisionRecords': records, 'ordersCount': len(orders),
                'commandsCount': len(commands),
                'dispatchStarted': any(c.get('begunAtJst') is not None for c in commands.values()),
                'readOnly': True, 'databaseWriteRequested': False,
                'orderTransmissionByThisAudit': False}
    finally:
        con.close()


def inspect(store, session):
    need(type(session) is str and re.fullmatch(r'20\d\d-\d\d-\d\d', session), 'SESSION')
    store = safe(store, True)
    settings = read(store / 'settings.json')
    config = read(settings['bootstrapConfigFile'])
    root = safe(config['privateRoot'], True)
    pointer = read(root / ('received-session-' + session + '.active.json'))
    run = safe(pointer['runRoot'], True)
    need(pointer.get('schemaId') == 'ARK_NO11_RECEIVED_ACTIVE_RUN_V1'
         and pointer.get('sessionDate') == session and run.parent == root
         and re.fullmatch('session-' + session + '-[a-f0-9]{32}', run.name), 'RUN_IDENTITY')
    infer = safe(run / 'inference', True)
    result = database_summary(infer / ('broker-execution-' + session + '.sqlite'), session)
    # One captured report supplies inference and its embedded broker result;
    # never present two independently updated reports as an atomic snapshot.
    report = read(infer / 'pipeline-latest-report.json')
    need(report.get('schemaId') == 'ARK_NO11_CONTINUOUS_RECEIVED_SHADOW_V1', 'PIPELINE_SCHEMA')
    source = report.get('source', {})
    inf = report.get('inference', {})
    need(source.get('sessionDate') == session and inf.get('sessionDate', session) == session,
         'REPORT_SESSION')
    result['pipelineReportAtJst'] = report.get('actualCompletedAtJst')
    result['pipelineAndLedgerAtomicSnapshotCertified'] = False
    result['p1Candidates'] = inf.get('p1Session', {}).get('firstEntryCandidates')
    result['h235StateExcluded'] = inf.get('counts', {}).get('h235BlockedUnavailableOrExcludedState')
    sha = inf.get('h235PrivateResultSha256')
    if type(sha) is str and re.fullmatch('[a-f0-9]{64}', sha):
        raw = safe(infer / ('h235-asof-' + sha[:16] + '.json')).read_bytes()
        need(hashlib.sha256(raw).hexdigest() == sha, 'H235_HASH')
        rows = parse(raw).get('results')
        need(type(rows) is list, 'H235_ROWS')
        result['h235Evaluated'] = len(rows)
        result['h235Admitted'] = sum(r.get('admission') is True for r in rows)
    return result


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--store', type=Path, required=True)
    p.add_argument('--session', required=True)
    args = p.parse_args(argv)
    try:
        print(json.dumps(inspect(args.store, args.session), ensure_ascii=True, allow_nan=False))
        return 0
    except Exception as error:
        code = str(error) if isinstance(error, AuditError) else 'NO11_READONLY_AUDIT_SOURCE_OR_IO_UNVERIFIED'
        print(json.dumps({'status': 'BLOCKED', 'reason': code, 'readOnly': True,
                          'orderTransmissionByThisAudit': False}, ensure_ascii=True))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
