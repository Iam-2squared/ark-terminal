"""Read-only R52 decision coverage of the immutable R50-A funded baseline.

Development outcomes are kept in an evaluator section and never passed to a policy.
"""
from __future__ import annotations
import argparse, collections, gzip, json, math, zipfile
from decimal import Decimal
from pathlib import Path
import numpy as np
from scripts import phase57_capital_exit_integrated as integ
from scripts import phase57_exit_winner_lifecycle_r50 as r50
from scripts import phase57_development_integrated_v0 as v0

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT/'docs/evidence/phase57-capital-exit-integrated/RESULT/phase57-integrated-result.zip'

def load_ledger(z, name):
    with z.open(name) as stream:
        return json.loads(gzip.decompress(stream.read()))

def audit(source: Path, output: Path):
    p, data, score, model = integ.load_inputs()
    receipt=json.loads((source/'data/data-receipt.json').read_text())
    for name, expected in [('decision-features.npz','45b91faed0ee7ac3dd46d5fa9bdb4f9f5940cfa2c4a9292af468427d551f5b3e'),
                           ('row-identities.jsonl.gz','41d875a3c7d8d8ebcb6fe6ef2022277143b6b34f9ba34c163395f81f2873ac47')]:
        v0.require(v0.digest(source/'data'/name)==expected,'GEN3_CHECKPOINT_PIN:'+name)
    with np.load(source/'data/decision-features.npz',allow_pickle=False) as z:
        numeric=z['numeric']; fresh=z['fresh']; cats=z['categorical']
    names=receipt['numericColumns']; name_index={n:i for i,n in enumerate(names)}
    groups=collections.defaultdict(list)
    with gzip.open(source/'data/row-identities.jsonl.gz','rt') as stream:
        for line in stream:
            x=json.loads(line); groups[(x['arm'],x['entryId'])].append((x['index'],x['now']))
    v0.require(sum(map(len,groups.values()))==len(numeric)==656247,'GEN3_ROW_COVERAGE')
    _,_,cohort,intents,evaluation,terminal,raw,_,_,_=data
    with zipfile.ZipFile(ARCHIVE) as z:
        report=json.loads(z.read('report.json'))
        ledgers={arm:load_ledger(z,arm+'_V3_B_R50_A_ledger.json.gz') for arm in ('IM','R1')}
    im=ledgers['IM']; v0.require(len(im['funded'])==len(im['closed'])==79,'R50_IM_79')
    v0.require(Decimal(im['snapshots'][-1]['equityJpy'])==Decimal('887131.0091250009994995'),'CONTROL_EQUITY')
    items=[]; tally=collections.Counter(); reason_money=collections.defaultdict(Decimal)
    all_scope={}
    for arm in v0.ARMS:
        key='IM' if arm==v0.IM else 'R1'; ledger=ledgers[key]
        funded=ledger['funded']; closed={r['entryId']:r for r in ledger['closed']}
        all_scope[key]={'frozenEntryCandidates':sum(x['timestamp'][:10] in p['sessions'] for x in intents[arm]),
                        'checkpointEntriesPresent':sum((arm,x['entryId']) in groups for x in intents[arm] if x['timestamp'][:10] in p['sessions']),
                        'funded':len(funded),'closed':len(closed),'unresolved':len(ledger['unresolvedEntryIds'])}
        releases=sorted((x['exitTimestamp'],x['entryId']) for x in ledger['closed'] if x['exitTimestamp'][:10] in p['sessions'])
        for eid, entry in sorted(funded.items()):
            path=groups.get((arm,eid));v0.require(bool(path),'FUNDED_CHECKPOINT_MISSING')
            state=r50.initial_state(); row_model=model[arm][eid]
            replacement=any(t<entry['entryTimestamp'] and t[:10]==entry['session'] for t,_ in releases)
            for idx,now in path:
                if now>row_model['exitMinute'] if row_model['exitMinute'] is not None else now>925: break
                values={n:(float(numeric[idx,name_index['facts.'+n]])
                           if math.isfinite(float(numeric[idx,name_index['facts.'+n]])) else None)
                        for n in r50.FACTS}
                envelope={'now':now,'maxKnownAt':now,'maxBarEnd':now,'fresh':bool(fresh[idx]),'values':values}
                decision=r50.intent(envelope,state,'R50_A_LIFECYCLE',terminal=now==925)
                state=decision['state'];reason=decision['authority'];tally[(key,'Replacement' if replacement else 'Initial',reason)]+=1
                pnl=Decimal(closed[eid]['realizedPnlJpy']) if eid in closed else None
                # The position PnL is repeated for diagnosis only; never sum checkpoint PnL.
                items.append({'arm':key,'entryId':eid,'quantity':entry['quantity'],'entryTimestamp':entry['entryTimestamp'],
                    'context':'Replacement' if replacement else 'Initial','now':now,'fresh':bool(fresh[idx]),
                    'profitState':('UNKNOWN' if values['currentReturnPct'] is None else
                        '<0' if values['currentReturnPct']<0 else '0–3' if values['currentReturnPct']<3 else
                        '3–5' if values['currentReturnPct']<5 else '>=5'),
                    'completeOwnedPrefix':bool(numeric[idx,name_index['position.fullOwnedPrefix']]==1),
                    'factEnvelope':envelope,'state':int(cats[idx,3]),'reason':reason,
                    'actionIntent':decision['action'],'actualExitMinute':row_model['exitMinute'],
                    'actualExitPrice':row_model['exitPrice'],
                    'evaluatorOnly':{'remainingUpsidePct':evaluation[arm][eid]['postUpsidePct'],
                                     'realizedPnlJpy':None if pnl is None else str(pnl)}})
            if eid in closed:
                # Each position contributes its currency PnL once, by terminal decision reason.
                reason_money[(key,'Replacement' if replacement else 'Initial',items[-1]['reason'])]+=Decimal(closed[eid]['realizedPnlJpy'])
    summary={'schema':'phase57-r52-baseline-decision-coverage-audit-v1','basisHead':'73a13164f449cdff41ca925411b647a42be6a898',
             'sourceArchiveSha256':v0.digest(ARCHIVE),'gen3ArchiveSha256':'d3936171002e7579e431568b9900ee5fa1fc8ade3dae0bf6de92870c8dbe4b38',
             'sourceFeatureSha256':v0.digest(source/'data/decision-features.npz'),
             'controlFinalEquityJpy':im['snapshots'][-1]['equityJpy'],
             'controlR50PrecommitSha256':r50.PROTOCOL_SHA256,'scope':all_scope,
             'reasonCheckpointCounts':{'|'.join(k):v for k,v in sorted(tally.items())},
             'reasonPositionPnLJpy':{'|'.join(k):str(v) for k,v in sorted(reason_money.items())},
             'checkpoints':len(items),'providerRequests':0,'protectedPartitionsOpened':0,'safety':v0.SAFETY}
    output.mkdir(parents=True,exist_ok=False)
    (output/'BASELINE_DECISION_COVERAGE_AUDIT.json').write_bytes(v0.canonical(summary))
    with gzip.open(output/'BASELINE_DECISION_COVERAGE_CHECKPOINTS.jsonl.gz','wt') as f:
        for row in items:f.write(v0.canonical(row).decode())
    print(json.dumps({'scope':all_scope,'checkpoints':len(items),
                      'reasonCounts':{'|'.join(k):v for k,v in tally.items()}},default=str))

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--source',type=Path,required=True);a.add_argument('--out',type=Path,required=True)
    x=a.parse_args();audit(x.source,x.out)
