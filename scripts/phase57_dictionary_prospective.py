#!/usr/bin/env python3
"""Offline prospective intake. No provider, broker, scheduler or model client.
SQLite transactions retain immutable receipts and correction versions. Local receipt
is conservative availability, NOT historical publication certification.
"""
import argparse
import datetime as dt
import hashlib
import json
import math
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'docs/evidence/phase57-dictionary-procurement-v1'
KINDS = {'raw1m', 'raw5m', 'master', 'identity', 'corporate_action', 'trading_state', 'daily_l2', 'future_l3_input'}
REASONS = {'NO_TRADE', 'DATA_MISSING', 'HALT', 'SPECIAL_QUOTE', 'NOT_LISTED', 'OUTSIDE_SESSION', 'UNKNOWN'}
FORBIDDEN = {'symbolId', 'symbolEmbedding', 'oneHot', 'entryPnL', 'exitPnL', 'winnerOutcome', 'top5Outcome'}

def canonical(x):
    return json.dumps(x, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()

def sha(x):
    return hashlib.sha256(x).hexdigest()

def instant(x):
    t = dt.datetime.fromisoformat(x.replace('Z', '+00:00'))
    if t.tzinfo is None:
        raise ValueError('TIMEZONE_REQUIRED')
    return t

def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()

def contract():
    raw = (BASE / 'protocol.json').read_bytes()
    if sha(raw) != json.loads((BASE / 'protocol-lock.json').read_text())['sha256']:
        raise ValueError('PROTOCOL_CHANGED')
    return json.loads(raw)

def forbidden(x):
    if isinstance(x, dict):
        return bool(FORBIDDEN.intersection(x)) or any(forbidden(v) for v in x.values())
    if isinstance(x, list):
        return any(forbidden(v) for v in x)
    return False

class Store:
    def __init__(self, path):
        self.db = sqlite3.connect(path, isolation_level=None)
        self.db.execute('PRAGMA foreign_keys=ON')
        self.db.execute('PRAGMA synchronous=FULL')
        self.db.executescript('''
        CREATE TABLE IF NOT EXISTS receipts (
          seq INTEGER PRIMARY KEY, digest TEXT UNIQUE NOT NULL,
          previous TEXT NOT NULL, envelope BLOB NOT NULL, payload BLOB NOT NULL);
        CREATE TRIGGER IF NOT EXISTS immutable_update BEFORE UPDATE ON receipts
          BEGIN SELECT RAISE(ABORT,'APPEND_ONLY'); END;
        CREATE TRIGGER IF NOT EXISTS immutable_delete BEFORE DELETE ON receipts
          BEGIN SELECT RAISE(ABORT,'APPEND_ONLY'); END;
        ''')

    def close(self):
        self.db.close()

    def audit(self):
        previous = '0' * 64
        n = 0
        for seq, digest, prev, envelope, payload in self.db.execute('SELECT * FROM receipts ORDER BY seq'):
            e = json.loads(envelope)
            if seq != n + 1 or prev != previous or e['previous'] != prev or e['payloadSHA256'] != sha(payload) or digest != sha(envelope):
                raise ValueError('CHAIN_OR_PAYLOAD_TAMPER')
            n += 1
            previous = digest
        return {'records': n, 'head': previous}

    def append(self, kind, session, payload, source, budget, source_version=None, publication=None, parents=()):
        p = contract()
        day = dt.date.fromisoformat(session)
        if kind not in KINDS or not isinstance(payload, dict) or forbidden(payload):
            raise ValueError('SCHEMA_OR_OUTCOME_FORBIDDEN')
        if day < dt.date.fromisoformat(p['prospective']['startNotBefore']):
            raise ValueError('NO_HISTORICAL_BACKFILL')
        if budget.get('purpose') != 'DICTIONARY_ONLY' or session not in budget.get('sessions', []) or budget.get('protectedOverlap') is not False:
            raise ValueError('DEDICATED_BUDGET_REQUIRED')
        if not budget.get('calendarSourceHash') or session not in budget.get('exchangeSessions', []):
            raise ValueError('VERIFIED_EXCHANGE_CALENDAR_REQUIRED')
        if not source or not isinstance(source, str):
            raise ValueError('SOURCE_REQUIRED')
        acquired = now()
        if day > instant(acquired).astimezone(dt.timezone(dt.timedelta(hours=9))).date():
            raise ValueError('FUTURE_SESSION')
        if publication and instant(publication) > instant(acquired):
            raise ValueError('FUTURE_PUBLICATION')
        if kind == 'identity':
            for field in ('securityId', 'code', 'effectiveFrom', 'effectiveTo', 'evidenceHash'):
                if not payload.get(field):
                    raise ValueError('IDENTITY_EVIDENCE_REQUIRED')
            if payload['effectiveFrom'] >= payload['effectiveTo']:
                raise ValueError('INVALID_IDENTITY_INTERVAL')
        if kind == 'corporate_action':
            for field in ('announcementKnownAt', 'effectiveDate', 'type', 'terms', 'evidenceHash'):
                if not payload.get(field):
                    raise ValueError('ACTION_EVIDENCE_REQUIRED')
            if instant(payload['announcementKnownAt']) > instant(acquired):
                raise ValueError('FUTURE_ANNOUNCEMENT')
        if kind == 'trading_state':
            reason = payload.get('missingReason', 'UNKNOWN')
            if reason not in REASONS:
                raise ValueError('INVALID_MISSING_REASON')
            if reason != 'UNKNOWN' and not payload.get('evidenceHash'):
                raise ValueError('MISSING_REASON_EVIDENCE_REQUIRED')
        if kind in {'daily_l2', 'future_l3_input', 'raw5m'} and not parents:
            raise ValueError('DERIVED_LINEAGE_REQUIRED')
        data = canonical(payload)
        self.db.execute('BEGIN IMMEDIATE')
        try:
            self.audit()
            for parent in parents:
                row = self.db.execute('SELECT envelope FROM receipts WHERE digest=?', (parent,)).fetchone()
                if row is None:
                    raise ValueError('UNKNOWN_PARENT')
                if json.loads(row[0])['session'] != session:
                    raise ValueError('CROSS_SESSION_PARENT')
            for _, e in self.as_of(acquired, inside_transaction=True):
                if kind == 'identity' and e['kind'] == 'identity':
                    old = json.loads(self.db.execute('SELECT payload FROM receipts WHERE digest=?', (_,)).fetchone()[0])
                    if old['code'] == payload['code'] and old['securityId'] != payload['securityId'] and max(old['effectiveFrom'], payload['effectiveFrom']) < min(old['effectiveTo'], payload['effectiveTo']):
                        raise ValueError('AMBIGUOUS_CODE_REUSE')
            latest = self.db.execute('SELECT envelope FROM receipts ORDER BY seq DESC LIMIT 1').fetchone()
            if latest and instant(acquired) < instant(json.loads(latest[0])['acquiredAt']):
                raise ValueError('CLOCK_REGRESSION')
            last = self.db.execute('SELECT digest FROM receipts ORDER BY seq DESC LIMIT 1').fetchone()
            envelope = {'kind': kind, 'session': session, 'source': source, 'sourceVersion': source_version,
                        'acquiredAt': acquired, 'knownAt': acquired, 'publicationClaim': publication,
                        'publicationClaimVerified': False, 'sourceVersionStatus': 'PROVIDED_UNVERIFIED' if source_version else 'NOT_PROVIDED',
                        'payloadSHA256': sha(data), 'parents': list(parents), 'previous': last[0] if last else '0'*64,
                        'budgetSHA256': sha(canonical(budget)), 'protocolSHA256': sha((BASE/'protocol.json').read_bytes()),
                        'exposure': 'E1', 'profileStatus': 'INPUT_ONLY_UNVERIFIED'}
            b = canonical(envelope)
            digest = sha(b)
            self.db.execute('INSERT INTO receipts(digest,previous,envelope,payload) VALUES(?,?,?,?)', (digest, envelope['previous'], b, data))
            self.db.execute('COMMIT')
            return digest
        except BaseException:
            self.db.execute('ROLLBACK')
            raise

    def as_of(self, cutoff, inside_transaction=False):
        instant(cutoff)
        if not inside_transaction:
            self.audit()
        return [(d, json.loads(e)) for d,e in self.db.execute('SELECT digest,envelope FROM receipts ORDER BY seq') if instant(json.loads(e)['knownAt']) <= instant(cutoff)]

    def export(self):
        self.audit()
        return b'\n'.join(canonical({'digest': d, 'envelope': json.loads(e), 'payload': json.loads(p)}) for d,e,p in self.db.execute('SELECT digest,envelope,payload FROM receipts ORDER BY seq')) + b'\n'


def summarize_minute_rows(session, rows):
    """Deterministic unadjusted draft L1/L2, with holes explicit. Never a profile."""
    close = 925 if session >= '2024-11-05' else 900
    expected = set(range(540, 690)) | set(range(750, close))
    observed = {}
    codes = {row.get('Code') for row in rows}
    if len(codes) > 1:
        raise ValueError('MIXED_SECURITY_BARS')
    for row in rows:
        if row.get('Date') != session:
            raise ValueError('CROSS_SESSION_BAR')
        h, m = map(int, row['Time'].split(':'))
        if not 0 <= h < 24 or not 0 <= m < 60:
            raise ValueError('INVALID_TIME')
        t = h*60+m
        if t not in expected:
            continue  # Auctions and lunch excluded, no price filling.
        values = [row[k] for k in ('O','H','L','C','Vo','Va')]
        if not all(isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v) for v in values):
            raise ValueError('INVALID_BAR')
        o,hi,lo,c,v,a = values
        if min(o,hi,lo,c) <= 0 or hi < max(o,lo,c) or lo > min(o,hi,c) or min(v,a) < 0:
            raise ValueError('INVALID_BAR')
        if t in observed:
            raise ValueError('DUPLICATE_MINUTE')
        observed[t] = row
    buckets = []
    for t in sorted(x for x in expected if x % 5 == 0):
        rs = [observed.get(i) for i in range(t,t+5)]
        if any(r is None for r in rs):
            buckets.append({'minute':t,'status':'UNKNOWN','O':None,'H':None,'L':None,'C':None})
        else:
            buckets.append({'minute':t,'status':'OBSERVED_UNVERIFIED','O':rs[0]['O'],
                            'H':max(r['H'] for r in rs),'L':min(r['L'] for r in rs),'C':rs[-1]['C'],
                            'Vo':sum(r['Vo'] for r in rs),'Va':sum(r['Va'] for r in rs)})
    return {'session':session,'status':'DRAFT_INPUT_ONLY','knownAt':None,
            'expectedSlots':len(expected),'observedSlots':len(observed),
            'missingReason':'UNKNOWN','missingMinutes':sorted(expected-set(observed)),
            'raw1mSHA256':sha(canonical(rows)), 'normalized5mSHA256':sha(canonical(buckets)),
            'bars5m':buckets,'profileEligible':False}


def maturity(admitted_sessions, neff, independent_securities, gates):
    """Diagnostic only; caller admission claims cannot create a frozen profile."""
    if not math.isfinite(neff) or neff < 0:
        raise ValueError('INVALID_NEFF')
    n = len(set(admitted_sessions))
    p = contract()['prospective']
    eligibility = n >= p['tier1MinimumSessions'] and neff >= 12 and independent_securities >= 300 and all(gates.get('G'+str(i)) == 'PASS' for i in range(9))
    return {'admittedSessions': n, 'basicRemaining': max(0,20-n), 'tier1Remaining': max(0,60-n),
            'windowRemaining': {str(w): max(0,w-n) for w in [20,60,250]},
            'freezeReviewEligible': eligibility, 'frozen': False,
            'status': 'REQUIRES_EVIDENCE_BOUND_FREEZE_REVIEW' if eligibility else 'INSUFFICIENT'}


def main():
    a = argparse.ArgumentParser(description=__doc__)
    a.add_argument('command', choices=['init','append','audit','export','status','summarize'])
    a.add_argument('--store', required=True)
    a.add_argument('--input', type=Path)
    args = a.parse_args()
    s = Store(args.store)
    try:
        if args.command == 'summarize':
            x=json.loads(args.input.read_text())
            print(json.dumps(summarize_minute_rows(x['session'], x['rows'])))
        elif args.command == 'append':
            print(s.append(**json.loads(args.input.read_text())))
        elif args.command == 'export':
            print(s.export().decode(), end='')
        elif args.command == 'status':
            print(json.dumps({'foundation': 'JPX_STOCK_BEHAVIOR_DICTIONARY_PROSPECTIVE_FOUNDATION_V1', 'capture': s.audit(), 'admittedSessions': 0, 'frozen': False, 'reason':'No implemented production admission certifier; raw receipts never count as verified sessions'}))
        else:
            print(json.dumps(s.audit()))
    finally:
        s.close()

if __name__ == '__main__':
    main()
