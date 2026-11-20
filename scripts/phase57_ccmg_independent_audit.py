"""Independent arithmetic, state and lineage audit of a closed CCMG cycle."""
from __future__ import annotations

import argparse
import collections
from decimal import Decimal
import gzip
import hashlib
import json
from pathlib import Path
import zipfile

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/evidence/phase57-checkpoint-certified-guard-exit'
LADDER=(1,2,3,5,10)
FLOOR={1:0,2:1,3:2,5:3,10:5}


def digest(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for part in iter(lambda:f.read(1<<20),b''):h.update(part)
    return h.hexdigest()


def lines(path):
    with gzip.open(path,'rt') as f:return [json.loads(line) for line in f]


def main(audit_zip):
    pre=json.loads((OUT/'CYCLE_PRECOMMIT.json').read_text())
    pre_sha=digest(OUT/'CYCLE_PRECOMMIT.json')
    assert pre_sha=='679cbe81bdaf483c7c68dbd290a520cdb6289ea1573519816e421b4c563cd079'
    readiness=json.loads((OUT/'CHECKPOINT_READINESS.json').read_text())
    result=json.loads((OUT/'LAYER_A_RESULT.json').read_text())
    potential=json.loads((OUT/'POTENTIAL_RESULT.json').read_text())
    rows=lines(OUT/'LAYER_A_ENTRY_ROWS.jsonl.gz')
    oof=lines(OUT/'POTENTIAL_OOF.jsonl.gz')
    assert len(rows)==len(oof)==1614
    assert len({(x['arm'],x['entryId']) for x in rows})==1614
    assert {(x['arm'],x['entryId']) for x in rows}=={(x['arm'],x['entryId']) for x in oof}
    assert digest(OUT/'LAYER_A_ENTRY_ROWS.jsonl.gz')==result['entryRowsSha256']
    assert digest(OUT/'POTENTIAL_OOF.jsonl.gz')==potential['oofRowsSha256']
    assert potential['outerFitsActual']==6<=2*potential['canonicalOuterFoldCount']==10
    assert result['integratedReplayInvocations']==0 and potential['innerFits']==0
    with zipfile.ZipFile(audit_zip) as z:
        paired=json.loads(z.read('paired-layer-a-r34.json'))
    paired_index={(arm,x['entryId']):x for arm in ('IM','R1') for x in paired[arm]['FULL_MH_WAIT15']}
    primary=[x for x in rows if x['primary']]
    assert len(primary)==len(paired_index)==111
    for x in primary:
        p=paired_index[x['arm'],x['entryId']]
        assert p['quantity']==x['quantity'] and p['controlPnlJpy']==x['controlPnlJpy']
        assert p['evaluatorOnlyUpsidePct']==x['postEntryUpsidePct']
        if x['terminalReason']!='CANDIDATE_FIRST' and x['candidatePnlJpy'] is not None:
            assert x['candidatePnlJpy']==x['controlPnlJpy']
        if x['candidatePnlJpy'] is not None:
            assert Decimal(x['candidatePnlJpy'])-Decimal(x['controlPnlJpy'])==Decimal(x['pairedDeltaJpy'])
    # Independently parse every checkpoint and recompute the fixed state from
    # only the fresh close and the previous checkpoint state.
    grouped=collections.defaultdict(list)
    with gzip.open(OUT/'CHECKPOINT_DRY_TRACE.jsonl.gz','rt') as f:
        for line in f:
            x=json.loads(line);grouped[x['arm'],x['entryId']].append(x)
    assert len(grouped)==1614
    event_count=collections.Counter()
    for key,seq in grouped.items():
        highest=streak=0
        for x in seq:
            previous=highest
            if x['freshClosedPrice']:
                current=x['currentReturnPct'];assert current is not None
                highest=max(highest,max((m for m in LADDER if current>=m),default=0))
                if highest==0 or highest>previous or current>=FLOOR[highest]:streak=0
                else:streak+=1
            else:
                assert x['currentReturnPct'] is None
                streak=0
            assert x['highestCertifiedMilestone']==(highest or None)
            assert x['floorPct']==(FLOOR[highest] if highest and x['freshClosedPrice'] else None)
            assert x['breachStreak']==streak
            assert streak<=2
            if streak==2:event_count['sell']+=1
            if x['event']=='DATA_GAP_RESET':event_count['gapReset']+=1
        assert seq[-1]['controlTerminalAtThisCheckpoint'] or seq[-1]['state']=='SELL_INTENT'
    independent_winners={}
    for arm in ('IM','R1'):
        for th in (5,10):
            cohort=[r for r in primary if r['arm']==arm and r['postEntryUpsidePct'] is not None and r['postEntryUpsidePct']>=th]
            known=[r for r in cohort if r['candidatePnlJpy'] is not None and r['controlPnlJpy'] is not None]
            delta=sum((Decimal(r['candidatePnlJpy'])-Decimal(r['controlPnlJpy']) for r in known),Decimal(0))
            saved=result['winner'][f'{arm}>={th}']
            assert len(cohort)==saved['entryN'] and len(known)==saved['knownPairedN']
            assert delta==Decimal(saved['pairedDeltaJpy']) and delta<0
            independent_winners[f'{arm}>={th}']={'N':len(cohort),'knownN':len(known),'deltaJpy':str(delta)}
    assert result['winnerGate']=='WINNER_PRESERVATION_FAIL' and not result['capitalEligibility']
    assert all(x['status']=='POTENTIAL_SKILL_FAIL' for x in potential['heads'].values())
    for item in oof:
        expected=next(r['postEntryUpsidePct'] for r in rows if r['arm']==item['arm'] and r['entryId']==item['entryId'])
        assert abs(item['teacherUpsidePct']-expected)<=1e-12
        assert item['pinnedTest'] and all(0<=item['probability'+str(h)]<=1 for h in (5,10))
    safety=pre['safety'];assert len(safety)==9 and not any(safety.values())
    for doc in (readiness,result,potential):assert doc['safety']==safety
    evidence={'schema':'phase57-ccmg-independent-audit-v1','status':'PASS',
        'precommitSha256':pre_sha,'layerASha256':digest(OUT/'LAYER_A_RESULT.json'),
        'readinessSha256':digest(OUT/'CHECKPOINT_READINESS.json'),
        'potentialSha256':digest(OUT/'POTENTIAL_RESULT.json'),
        'checkpointRows':sum(map(len,grouped.values())),'entryRows':len(rows),
        'stateSellEvents':event_count['sell'],'dataGapResets':event_count['gapReset'],
        'winner':independent_winners,'winnerGate':'WINNER_PRESERVATION_FAIL',
        'potentialFits':potential['outerFitsActual'],'integratedReplayInvocations':0,
        'selected':None,'productionReady':False,'safety':safety,
        'providerRequests':0,'restrictedPartitionsOpened':0}
    (OUT/'INDEPENDENT_AUDIT.json').write_text(json.dumps(evidence,sort_keys=True,separators=(',',':'),ensure_ascii=False)+'\n')
    print(json.dumps(evidence,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--audit',required=True,type=Path)
    args=parser.parse_args()
    main(args.audit)
