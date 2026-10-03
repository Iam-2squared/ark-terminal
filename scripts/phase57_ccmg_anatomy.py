"""Evaluator-only stratification of the immutable CCMG readiness dry trace."""
from __future__ import annotations
import collections
import gzip
import hashlib
import json
import statistics
from pathlib import Path

from scripts import phase57_exit_checkpoints_v1 as clock

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT/'docs/evidence/phase57-checkpoint-certified-guard-exit'
OLD = ROOT/'docs/evidence/phase57-milestone-guard-exit'
BUCKETS = ('<1','1-3','3-5','5-10','>=10')


def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()


def rows(p):
    with gzip.open(p, 'rt') as f:
        for line in f: yield json.loads(line)


def bucket(x):
    return '<1' if x < 1 else '1-3' if x < 3 else '3-5' if x < 5 else '5-10' if x < 10 else '>=10'


def median(xs): return statistics.median(xs) if xs else None


def run():
    pre = json.loads((BASE/'CYCLE_PRECOMMIT.json').read_text())
    ready = json.loads((BASE/'CHECKPOINT_READINESS.json').read_text())
    assert all(v == 'PASS' for v in ready['gates'].values())
    old_labels = {(r['arm'],r['entryId']):r['upsidePct'] for r in rows(OLD/'PHASE0_B_ENTRY_ROWS.jsonl.gz')}
    summaries = {(r['arm'],r['entryId']):r for r in rows(BASE/'CHECKPOINT_ENTRY_SUMMARY.jsonl.gz')}
    assert len(old_labels) == len(summaries) == 1614 and set(old_labels) == set(summaries)
    events = collections.defaultdict(dict)
    for x in rows(BASE/'CHECKPOINT_DRY_TRACE.jsonl.gz'):
        key=(x['arm'],x['entryId'])
        if x['event'] == 'BREACH_1' and 'alert' not in events[key]:events[key]['alert']=x
        if x['event'] == 'BREACH_2':events[key]['sell']=x
    out = {'schema':'phase57-ccmg-checkpoint-anatomy-v1',
           'precommitSha256':digest(BASE/'CYCLE_PRECOMMIT.json'),
           'readinessSha256':digest(BASE/'CHECKPOINT_READINESS.json'),
           'oldEvaluatorRowsSha256':digest(OLD/'PHASE0_B_ENTRY_ROWS.jsonl.gz'),
           'runtimeUsesUpside':False, 'byArmBucket':{},
           'newEstimatorFits':0,'integratedReplayInvocations':0,
           'safety':pre['safety']}
    for arm in ('IM','R1'):
        out['byArmBucket'][arm]={}
        for b in BUCKETS:
            picked=[(key,s) for key,s in summaries.items() if key[0]==arm and
                    old_labels[key] is not None and bucket(old_labels[key])==b]
            alerts=[events[key]['alert'] for key,_ in picked if 'alert' in events[key]]
            sells=[events[key]['sell'] for key,_ in picked if 'sell' in events[key]]
            cert_dist=collections.Counter(str(x['highestCertifiedMilestone']) for x in sells)
            elapsed=[]
            for key,s in picked:
                if 'sell' not in events[key]:continue
                sell=events[key]['sell'];m=sell['highestCertifiedMilestone']
                certified=s['certifiedAt'].get(str(m))
                if certified is not None:elapsed.append(clock.active_elapsed(s['session'],certified,sell['now']))
            out['byArmBucket'][arm][b]={
                'entries':len(picked), 'certified':{str(m):sum(str(m) in s['certifiedAt'] for _,s in picked)
                                                  for m in (1,2,3,5,10)},
                'withAlert':sum(s['alerts']>0 for _,s in picked),
                'twoCheckpointSellIntent':sum(s['firstSellIntent'] is not None for _,s in picked),
                'candidateFirst':sum(s['terminal']=='CANDIDATE_FIRST' for _,s in picked),
                'controlFirstOrTerminal':sum(s['terminal'] in ('CONTROL_FIRST','CONTROL_TERMINAL_WITHOUT_CANDIDATE') for _,s in picked),
                'bothSame':sum(s['terminal']=='BOTH_TRIGGER_SAME_CHECKPOINT' for _,s in picked),
                'missingResets':sum(s['dataGapReset'] for _,s in picked),
                'medianReturnAtFirstAlertPct':median([x['currentReturnPct'] for x in alerts]),
                'medianReturnAtSellIntentPct':median([x['currentReturnPct'] for x in sells]),
                'medianDistanceToNextAtSellPp':median([x['distanceToNextMilestonePp'] for x in sells if x['distanceToNextMilestonePp'] is not None]),
                'medianFloorMarginAtSellPp':median([x['floorMarginPp'] for x in sells if x['floorMarginPp'] is not None]),
                'medianActiveMinutesCertifiedToSell':median(elapsed),
                'highestCertifiedAtSell':dict(cert_dist)}
    path=BASE/'CHECKPOINT_ANATOMY.json'
    path.write_text(json.dumps(out,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n')
    print(json.dumps({a:{b:{k:v for k,v in q.items() if k in ('entries','withAlert','twoCheckpointSellIntent','candidateFirst')}
                       for b,q in data.items()} for a,data in out['byArmBucket'].items()},ensure_ascii=False))


if __name__=='__main__':run()
