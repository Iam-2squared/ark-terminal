#!/usr/bin/env python3
"""Bind an already-authorized 1m projection to Frozen LONG Selector anchors.
Only explicit local inputs. No downloads, credentials, decryption, or 5m upsampling.
"""
from __future__ import annotations
import argparse
import datetime as dt
import gzip
import hashlib
import json
import math
from pathlib import Path
import zipfile

SOURCE_SHA = '043dc99ad42ac3036ff280cb139de3fa6740f5386d0829a4cbaf13e360507505'
HEAD = '7599df41199a8c4d1ea86d5f3cb595edd599dd21'
ANCHOR_SHA = '985218fd1520bde127a72e9b049dd5a1840d42a928e7e850ea4e3e4d7ed82121'
EVENTS = 'docs/evidence/phase57-msh-entry-long-v1-preimplementation-feasibility-events.ndjson.gz'
PATHS = 'docs/evidence/phase57-msh-entry-long-v2-development/paths.json.gz'
JST = dt.timezone(dt.timedelta(hours=9))

def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def numeric(x: object) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)

def ms(date: str, minute: int) -> int:
    return int((dt.datetime.fromisoformat(date).replace(tzinfo=JST) + dt.timedelta(minutes=minute)).timestamp()*1000)

def load_json(path: Path) -> object:
    b = path.read_bytes()
    return json.loads(gzip.decompress(b) if path.suffix == '.gz' else b)

def write_new(path: Path, obj: object) -> None:
    with path.open('x', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, sort_keys=True, allow_nan=False, separators=(',', ':'))
        f.write('\n')

def prepare(source: Path, minute_file: Path | None, audit_file: Path | None) -> tuple[dict, dict | None]:
    if sha(source.read_bytes()) != SOURCE_SHA:
        raise ValueError('SOURCE_ZIP_SHA_MISMATCH')
    with zipfile.ZipFile(source) as z:
        manifest = json.loads(z.read('export-manifest.json'))
        if manifest['sourceHead'] != HEAD or manifest['missing']:
            raise ValueError('SOURCE_MANIFEST_MISMATCH')
        for name, meta in manifest['sourceFiles'].items():
            if sha(z.read(name)) != meta['sha256']:
                raise ValueError('SOURCE_PIN_MISMATCH:' + name)
        events = [json.loads(line) for line in gzip.decompress(z.read(EVENTS)).splitlines() if line]
        paths = json.loads(gzip.decompress(z.read(PATHS)))
    if len(events) != 3800 or len({r['selectorEventId'] for r in events}) != 3800:
        raise ValueError('SOURCE_EVENT_IDENTITY')
    first = {}
    for r in sorted(events, key=lambda x:(x['decisionTimestamp'],x['symbol'])):
        first.setdefault((r['sessionDate'],r['symbol']),r)
    anchors = sorted(first.values(), key=lambda x:(x['decisionTimestamp'],x['symbol']))
    ids = {r['selectorEventId'] for r in anchors}
    if len(ids) != 2743 or sha(('\n'.join(sorted(ids))+'\n').encode()) != ANCHOR_SHA:
        raise ValueError('FIRST_ANCHOR_IDENTITY')
    dates = sorted({r['sessionDate'] for r in anchors})
    if len(dates) != 76:
        raise ValueError('DEVELOPMENT_SESSION_COUNT')
    pathmap = {r['selectorEventId']:r for r in paths['events']}
    baseline = []
    for a in anchors:
        t = dt.datetime.fromisoformat(a['decisionTimestamp'].replace('Z','+00:00')).astimezone(JST)
        dm = t.hour*60+t.minute
        if t.date().isoformat()!=a['sessionDate'] or t.second or t.microsecond:
            raise ValueError('ANCHOR_TIMESTAMP')
        end = 690 if dm < 690 else pathmap[a['selectorEventId']]['sessionEndMinute']
        baseline.append({'eventId':a['selectorEventId'],'symbol':a['symbol'],'sessionDate':a['sessionDate'],
                         'selectedAt':int(t.timestamp()*1000),'referencePrice':a['decisionPrice'],
                         'segmentEnd':ms(a['sessionDate'],end),'direction':'LONG'})
    report = {'status':'ANCHORS_VERIFIED_MINUTE_INPUT_MISSING','sourceHead':HEAD,'sourceZipSHA256':SOURCE_SHA,
              'sourcePinsVerified':len(manifest['sourceFiles']),'sourceEvents':3800,'anchors':2743,
              'anchorIdentitySHA256':ANCHOR_SHA,'sessions':dates,'existingGranularitySeconds':300,
              'realMinutePerformanceMeasured':False,'providerRequests':0,'freshAccess':0,'oosAccess':0,
              'credentialsRead':False,'decryptionPerformed':False,'upsamplingPerformed':False}
    if minute_file is None:
        return report, None
    if audit_file is None:
        raise ValueError('EXPLICIT_PROJECTION_AUDIT_REQUIRED')
    audit = load_json(audit_file)
    if audit.get('payloadSHA256') != sha(minute_file.read_bytes()) or audit.get('sourceHead') != HEAD:
        raise ValueError('MINUTE_PROJECTION_IDENTITY')
    if audit.get('id') != 'PHASE57_NEW_LONG_ENTRY_MINUTE_EXPORT_V1':
        raise ValueError('UNSUPPORTED_PROJECTION_NO_IMPLICIT_5M_CONVERSION')
    if audit.get('providerRequests') != 0 or audit.get('freshAccess') != 0 or audit.get('oosAccess') != 0:
        raise ValueError('UNAUTHORIZED_DATA_SCOPE')
    original_sources = {s['sessionDate']:s for s in paths['sources']}
    if len(audit.get('sources', []))!=76 or {s['sessionDate'] for s in audit['sources']} != set(dates):
        raise ValueError('MINUTE_SOURCE_SESSION_SCOPE')
    for s in audit['sources']:
        if s.get('rawPagesSHA') != original_sources[s['sessionDate']]['rawPagesSHA']:
            raise ValueError('MINUTE_RAW_LINEAGE_MISMATCH')
    projections = load_json(minute_file)
    if not isinstance(projections,list) or len(projections)!=2743 or {p.get('eventId') for p in projections} != ids:
        raise ValueError('PROJECTION_ANCHOR_IDENTITY')
    pm = {p['eventId']:p for p in projections}
    candidates = []
    observed = 0
    for a in baseline:
        p = pm[a['eventId']]
        if p['symbol']!=a['symbol'] or p['sessionDate']!=a['sessionDate'] or p['decisionPrice']!=a['referencePrice']:
            raise ValueError('PROJECTION_ANCHOR_JOIN')
        if int(dt.datetime.fromisoformat(p['decisionTimestamp'].replace('Z','+00:00')).timestamp()*1000)!=a['selectedAt']:
            raise ValueError('PROJECTION_TIME_JOIN')
        bars,seen = [],set()
        if not isinstance(p.get('minutePath'),list):
            raise ValueError('ONE_MINUTE_PATH_REQUIRED')
        for row in p['minutePath']:
            m = row.get('m')
            if not isinstance(m,int) or isinstance(m,bool) or not 0<=m<1440 or m in seen:
                raise ValueError('DUPLICATE_OR_INVALID_MINUTE')
            seen.add(m)
            if row.get('missing') is True:
                continue
            if row.get('missing') is not False or not all(numeric(row.get(k)) and row[k]>-100 for k in 'ohlc'):
                raise ValueError('INVALID_NORMALIZED_MINUTE')
            o,h,l,c = [a['referencePrice']*(1+row[k]/100) for k in 'ohlc']
            if h < max(o,c,l)-1e-8 or l > min(o,c,h)+1e-8:
                raise ValueError('INVALID_OHLC')
            start=ms(a['sessionDate'],m)
            # Keep only the current continuous session segment. No lunch-bar synthesis.
            if start<a['selectedAt'] or start>=a['segmentEnd']:
                continue
            bars.append({'symbol':a['symbol'],'startAt':start,'endAt':start+60000,
                         'availableAt':start+60000,'open':o,'high':h,'low':l,'close':c})
        candidates.append({'anchor':a,'bars':sorted(bars,key=lambda b:b['startAt'])})
        observed+=len(bars)
    report.update(status='AUTHORIZED_PROJECTION_BOUND_NOT_MEASURED',minutePayloadSHA256=sha(minute_file.read_bytes()),
                  minuteProjectionAuditSHA256=sha(audit_file.read_bytes()),observedProjectedMinutes=observed)
    payload={'schema':'ARK_NEW_LONG_ENTRY_1M_REPLAY_INPUT_V1','dataKind':'HISTORICAL_DEVELOPMENT',
             'barIntervalSeconds':60,'sourceHead':HEAD,'anchorIdentitySHA256':ANCHOR_SHA,
             'availabilitySemantics':'BAR_END_RECONSTRUCTED_NOT_ACTUAL_ARRIVAL',
             'lineage':report,'candidates':candidates}
    return report,payload

def main() -> None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True)
    p.add_argument('--minutes',type=Path)
    p.add_argument('--audit',type=Path)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    if a.output.exists():
        raise SystemExit('NEW_OUTPUT_DIRECTORY_REQUIRED')
    report,payload=prepare(a.source,a.minutes,a.audit)
    a.output.mkdir(parents=True)
    write_new(a.output/'input-status.json',report)
    if payload is not None:
        write_new(a.output/'replay-input.json',payload)
    print(json.dumps({'status':report['status'],'anchors':report['anchors'],'oneMinuteDataBound':payload is not None}))

if __name__=='__main__':
    main()
