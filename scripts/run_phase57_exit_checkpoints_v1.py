"""R20 full-2155 observation census; no candidate fit, signal selection or EXIT replay."""
from __future__ import annotations
import argparse
import collections
from concurrent.futures import ProcessPoolExecutor
import gzip
import hashlib
import json
import os
from pathlib import Path
import socket
from scripts import phase57_exit_checkpoints_v1 as s

ROOT = Path(__file__).resolve().parents[1]
BASE = 'docs/evidence/phase57-entry-pattern-v2/ci-result/substrate/'
IMM = 'docs/evidence/phase57-state-conditioned-signal-entry-v1/measurement/baseline-immediate-records.json.gz'
COHORT = 'docs/evidence/phase57-entry-timing-signal-census-v1/protocol.json'
FREEZE = 'docs/evidence/phase57-entry-all-material-v1/ENTRY_DUAL_FREEZE_R10.json'
PINS = {
    IMM: '4522bea9ac94f597affc8518c4cb25354e27f9e64141152cde8b8a4b9e09df9c',
    BASE+'raw-paths-evaluator-only.json.gz': '37853e73799544be6fd6eb955de514073dd13671692426291a9fdb6d80056c6b',
    COHORT: '6b02b3088dd8ea7f8ce53112bc276df442bae3ce0716b8139c92733be4de2994',
    FREEZE: '5d7b619694a2d830d366d21429c2465f7214739f3e94a222a3844f6c0f41820a',
}
R1_SHA = '15ddb5cfc5169024878ee72d9dbecc6e1d9dec24e78afa2dcdf8dea891117fa6'
PRODUCER_BLOBS = {
    'scripts/phase57_state_v3_9pattern_entry_v1.py': '8164e48ef3d92d7c516e8134ad2f0fddb2fab7f6',
    'scripts/phase57_entry_timing_signals.py': '18b17e9974540ddb793bff3da77a200148839998',
    'scripts/phase57_entry_pattern_v2.py': '9361500191985e379928dca001fd1f6bc80034bc',
}


def no_network(*args, **kwargs):
    raise RuntimeError('NETWORK_FORBIDDEN_IN_OFFLINE_CHECKPOINT_CENSUS')


def sources():
    pins = dict(PINS)
    for path, expected in pins.items():
        s.require(s.digest(ROOT/path) == expected, 'INPUT_SHA_MISMATCH:'+path)
    for path, expected in PRODUCER_BLOBS.items():
        b = (ROOT/path).read_bytes()
        blob = hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
        s.require(blob == expected, 'CANONICAL_PRODUCER_CHANGED:'+path)
        pins[path] = hashlib.sha256(b).hexdigest()
    return pins


def flatten(value, path=''):
    if isinstance(value, dict):
        for k, v in sorted(value.items()):
            yield from flatten(v, path+'/'+k)
    elif not isinstance(value, (list, tuple)):
        yield path, value


def new_panel():
    return {'population': 0, 'fills': 0, 'noEntry': 0, 'checkpoints': 0,
            'freshClose': 0, 'missingCurrentClose': 0, 'completeOwnedPrefix': 0,
            'stateAtEntry': collections.Counter(), 'stateAtEntryQuality': collections.Counter(),
            'stateNow': collections.Counter(), 'stateQuality': collections.Counter(),
            'signalStateCounts': {f: collections.Counter() for f in s.FAMILIES},
            'fieldKnown': collections.Counter(), 'fieldMissing': collections.Counter()}


def one_day(task):
    day, envelopes, raw, out = task
    socket.create_connection = no_network
    socket.socket.connect = no_network
    panels = {a: new_panel() for a in s.ARMS}
    by_arm = {a: {e['opportunity']: e for e in envelopes[a]} for a in s.ARMS}
    keys = sorted(by_arm[s.ARMS[0]])
    file = Path(out)/'checkpoints'/f'{day}.jsonl.gz'
    with file.open('xb') as bf, gzip.GzipFile(fileobj=bf, filename='', mode='wb', mtime=0) as gz:
        for oid in keys:
            path = raw[oid]
            today = path['today']
            pd = path['previousSession']
            s.require(pd is None or pd < day, 'PREVIOUS_SESSION_NOT_PAST')
            previous = s.closed_prefix(pd, 1440, path['previous']) if pd else ()
            s.require(pd is not None or not path['previous'], 'PREVIOUS_IDENTITY_MISSING')
            observers = {}
            for arm in s.ARMS:
                e = by_arm[arm][oid]
                panels[arm]['population'] += 1
                if e['entryId'] is None:
                    panels[arm]['noEntry'] += 1
                    continue
                panels[arm]['fills'] += 1
                opens = [r for r in today if r[0] == e['entryMinute']]
                s.require(len(opens) == 1 and abs(opens[0][1]*1.0005/e['price']-1) < 1e-12,
                          'FROZEN_ENTRY_VS_RAW_OPEN')
                p0 = s.closed_prefix(day, e['entryMinute'], today)
                init = s.market_snapshot(day, e['entryMinute'], p0, pd, previous)
                panels[arm]['stateAtEntry'][str(init['state']['state'])] += 1
                panels[arm]['stateAtEntryQuality'][init['state']['dataQuality']] += 1
                observers[arm] = s.PositionObserver(e, init['state'])
            if not observers:
                continue
            start = min(o.entry['entryMinute'] for o in observers.values())
            for now in s.checkpoint_grid(day, start):
                prefix = s.closed_prefix(day, now, today)
                recognition = s.market_snapshot(day, now, prefix, pd, previous)
                for arm, obs in observers.items():
                    if now <= obs.entry['entryMinute']:
                        continue
                    row = obs.step(now, prefix, recognition)
                    row['entryPolicy'] = arm
                    s.require(row['inputMaxKnownAt'] is None or row['inputMaxKnownAt'] <= now, 'KNOWLEDGE_LEAK')
                    gz.write(s.encoded(row))
                    panel = panels[arm]
                    panel['checkpoints'] += 1
                    fresh = row['position']['freshClosedPrice']
                    panel['freshClose' if fresh else 'missingCurrentClose'] += 1
                    panel['completeOwnedPrefix'] += int(row['position']['fullOwnedPrefix'])
                    panel['stateNow'][str(recognition['state']['state'])] += 1
                    panel['stateQuality'][recognition['state']['dataQuality']] += 1
                    for f in s.FAMILIES:
                        v = recognition['signals'][f]['state'] if fresh else None
                        panel['signalStateCounts'][f]['UNKNOWN' if v is None else 'TRUE' if v else 'FALSE'] += 1
                    # Availability only: never average current PnL or select a rule.
                    for key, value in flatten(row):
                        panel['fieldMissing' if value is None else 'fieldKnown'][key] += 1
    return {'day': day, 'panels': panels, 'checkpointSHA256': s.digest(file)}


def merge_counts(dst, src):
    for k, v in src.items():
        if isinstance(v, dict):
            if k not in dst: dst[k] = {}
            merge_counts(dst[k], v)
        else:
            dst[k] = dst.get(k, 0) + v


def registry_inventory():
    names = s.read(ROOT/(BASE+'names.json'))
    s.require(len(names) == len(set(names)) == 476, 'PATTERN_REGISTRY_NOT_476')
    inventory = []
    for name in names:
        if name.startswith('RECENT/') or name.startswith(('SIGNAL/PDH','SIGNAL/PDL')):
            status = 'PRIOR_DAILY_LINEAGE_AND_EXIT_RECOMPUTATION_PENDING'
        elif name.startswith('SEL/'):
            status = 'FROZEN_SELECTOR_CONTEXT_JOIN_PENDING'
        else:
            status = 'CANONICAL_INTRADAY_PREFIX_PRODUCER_FOUND_EXIT_RECOMPUTATION_PENDING'
        inventory.append({'feature':name,'family':name.split('/')[0],
                          'producer':'scripts/phase57_entry_pattern_v2.py::features',
                          'status':status,'modelAdmitted':False})
    return {'columns':len(names),'familyCounts':dict(collections.Counter(n.split('/')[0] for n in names)),
            'statusCounts':dict(collections.Counter(r['status'] for r in inventory)),
            'registrySHA256':s.digest(ROOT/(BASE+'names.json')),'rows':inventory,
            'notThe3800EventInformationExporter':True,'performanceInspected':False}


def run(r1_records, outdir, head, workers=2):
    socket.create_connection = no_network
    socket.socket.connect = no_network
    pins = sources()
    s.require(s.digest(r1_records) == R1_SHA, 'R1_RECORDS_SHA')
    freeze = s.read(ROOT/FREEZE)
    s.require(freeze['decision']['retain'] == list(s.ARMS) and freeze['decision']['noFurtherEntryOptimization'], 'ENTRY_FREEZE_CHANGED')
    protocol = s.read(ROOT/COHORT)
    allowed = set(protocol['opportunityIds'])
    s.require(len(allowed) == len(protocol['opportunityIds']) == 2155, 'COHORT_NOT_2155')
    records = {s.ARMS[0]:s.read(ROOT/IMM),s.ARMS[1]:s.read(r1_records)}
    envelopes = {a:sorted([s.entry_envelope(r) for r in rr],key=lambda e:e['opportunity']) for a,rr in records.items()}
    del records
    for a, rows in envelopes.items():
        s.require(len(rows) == 2155 and {r['opportunity'] for r in rows} == allowed, 'COHORT_MISMATCH:'+a)
    paths = s.read_allowlisted_paths(ROOT/(BASE+'raw-paths-evaluator-only.json.gz'),allowed)
    days = sorted(set(e['session'] for e in envelopes[s.ARMS[0]]))
    s.require(len(days) == 58 and set(days) <= set(protocol['evaluationSessions']), 'SESSION_MISMATCH')
    out = Path(outdir);out.mkdir(parents=True,exist_ok=False);(out/'checkpoints').mkdir()
    tasks = [(day,{a:[e for e in es if e['session'] == day] for a,es in envelopes.items()},
              {k:v for k,v in paths.items() if k.split('|')[0] == day}, str(out)) for day in days]
    total = {a:{} for a in s.ARMS}; receipts = []
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for result in pool.map(one_day,tasks):
            for a in s.ARMS:merge_counts(total[a],result['panels'][a])
            receipts.append(result)
            print(json.dumps({'day':result['day'],'checkpoints':{a:result['panels'][a]['checkpoints'] for a in s.ARMS}}),flush=True)
    for arm,n in zip(s.ARMS,(1963,1885)):
        s.require(total[arm]['population'] == 2155 and total[arm]['fills'] == n, 'FROZEN_FILLS_CHANGED')
        s.require(total[arm]['freshClose']+total[arm]['missingCurrentClose'] == total[arm]['checkpoints'], 'CHECKPOINT_ACCOUNTING')
        expected = sum(len(s.checkpoint_grid(e['session'],e['entryMinute'])) for e in envelopes[arm] if e['entryId'])
        s.require(total[arm]['checkpoints'] == expected, 'SCHEDULED_CHECKPOINTS_LOST')
    s.require(sources() == pins and s.digest(r1_records) == R1_SHA,'INPUT_MUTATION')
    summary = {'schemaVersion':'phase57-exit-observation-census-r20','executionHead':head,
        'status':'OBSERVATION_SUBSTRATE_ONLY_NOT_AN_EXIT_POLICY_OR_PERFORMANCE_PASS',
        'populationPerEntry':2155,'opportunityBearingSessions':len(days),
        'availabilitySemantics':s.AVAILABILITY,'byEntry':total,
        'sourcePins':pins,'r1RecordsSHA256':R1_SHA,'sessions':receipts,
        'providerRequests':0,'newProtectedPartitionsOpened':0,
        'modelFits':0,'candidatePoliciesEvaluated':0,'legacyExitPoliciesInvoked':0,
        'safety':s.SAFETY}
    s.write_new(out/'coverage.json',summary)
    s.write_new(out/'entry-envelopes.json.gz',envelopes)
    s.write_new(out/'pattern-registry-inventory.json',registry_inventory())
    files = {p.relative_to(out).as_posix():s.digest(p) for p in sorted(out.rglob('*')) if p.is_file()}
    s.write_new(out/'manifest.json',files)


if __name__ == '__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--r1-records',required=True)
    parser.add_argument('--out',required=True);parser.add_argument('--head',required=True)
    parser.add_argument('--workers',type=int,default=2)
    args=parser.parse_args();s.require(1 <= args.workers <= 4,'WORKER_BUDGET')
    run(args.r1_records,args.out,args.head,args.workers)
