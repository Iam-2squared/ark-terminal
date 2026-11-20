"""Read-only audit of the one frozen Capital v3 finite result archive."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
from decimal import Decimal
from pathlib import Path

from scripts import phase57_capital_v3 as v3
from scripts import phase57_development_integrated_v0 as v0


def audit(root,ledger_path,r1_path):
    root=Path(root)
    report=json.loads((root/'report.json').read_text())
    scores=json.loads((root/'scores.json').read_text())
    assert report['pins']==v3.PINS and report['modelFits']==16 and len(report['fitManifest'])==16
    assert report['scoresSha256']==hashlib.sha256(v0.canonical(scores)).hexdigest()
    assert report['safety']==v0.SAFETY and not any(report['safety'].values())
    assert report['providerRequests']==report['protectedOpened']==0
    source=v3.ROOT/'docs/evidence/phase57-entry-pattern-v2/ci-result/substrate/raw-paths-evaluator-only.json.gz'
    data,_=v3.preflight(ledger_path,r1_path,source)
    _,_,_,intents,evaluation,_,_,_,_,labels=data
    target_days=set(json.loads(v3.old.WINDOW.read_text())['portfolioSessions'])
    findings={'schema':'phase57-capital-v3-independent-post-run-audit-v1',
              'reportSha256':v3.sha(root/'report.json'),
              'scoresSha256':v3.sha(root/'scores.json'),
              'decision':report['selection']['status'],'variants':{},
              'protectedOpened':0,'providerRequests':0,'safety':v0.SAFETY}
    for candidate in v3.contract()[3]['candidateIds']:
        for arm,short in ((v0.IM,'IM'),(v0.R1,'R1')):
            expected={x['entryId'] for x in intents[arm] if x['timestamp'][:10] in target_days}
            assert set(scores[candidate][arm])==expected
            assert all(math.isfinite(v) for v in scores[candidate][arm].values())
            p=root/(candidate+'-'+short+'-MAX3-ledger.json.gz')
            ledger=json.loads(gzip.decompress(p.read_bytes()))
            assert ledger['arm']==arm and ledger['capacity']==3 and ledger['safety']==v0.SAFETY
            assert all(Decimal(str(s['cashJpy']))>=0 and s['openCount']<=3 for s in ledger['snapshots'])
            assert all(row['quantity']>0 and row['quantity']%100==0 for row in ledger['funded'].values())
            funded=set(ledger['funded'])
            accepted={x['entryId'] for ev in ledger['events'] for x in ev['sizing'] if x['status']=='SIZED'}
            assert funded==accepted and funded<=expected
            known={x for x in expected if labels[arm][x] is not None}
            positive={x for x in known if labels[arm][x]==1}
            known_funded=funded & known
            hits=known_funded & positive
            card=report['candidates'][candidate][arm]
            assert card['candidateN']==len(expected) and card['knownN']==len(known)
            assert card['positiveN']==len(positive) and card['fundedN']==len(funded)
            assert card['fundedKnownN']==len(known_funded) and card['hitN']==len(hits)
            assert math.isclose(card['reach'],len(hits)/len(positive),abs_tol=1e-15)
            assert math.isclose(card['hitRate'],len(hits)/len(known_funded),abs_tol=1e-15)
            missed=positive-funded
            assert {x['entryId'] for x in card['missRows']}==missed
            assert card['missN']==len(missed) and sum(card['missReasons'].values())==len(missed)
            assert set(card['missReasons'])<=set(v3.contract()[0]['evaluation']['missPriority'])
            findings['variants'][candidate+'_'+short]={
                'ledgerSha256':v3.sha(p),'candidates':len(expected),'funded':len(funded),
                'knownFunded':len(known_funded),'hits':len(hits),'misses':len(missed),
                'unresolved':len(ledger['unresolvedEntryIds'])}
    if report['selection']['status']=='SELECT':
        assert report['selection']['selected'] in scores
        assert len(report['certifiedEod'])==6
        for key,series in report['certifiedEod'].items():
            assert len(series['daily'])==len(target_days)==24
            assert series['certifiedEodSessions']+series['nullSessions']==24
            if series['nullSessions']:
                assert series['statistics']['geometric'] is None
    else:
        assert report['selection']['selected'] is None
        assert 'certifiedEod' not in report and 'portfolio' not in report
    return findings


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--source',required=True)
    p.add_argument('--benchmark-ledger',required=True)
    p.add_argument('--r1-records',required=True)
    p.add_argument('--out',required=True)
    args=p.parse_args()
    result=audit(args.source,args.benchmark_ledger,args.r1_records)
    Path(args.out).write_bytes(v0.canonical(result))
    print(json.dumps({'status':'PASS','decision':result['decision'],
                      'variants':len(result['variants'])},sort_keys=True))


if __name__=='__main__':main()
