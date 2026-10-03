"""Independent exact-byte replay, archived control and accounting audit.

Run only after the one finite Development Action has produced its immutable ZIP.
No models are fit and no new Entry/EXIT decisions are introduced.
"""
from __future__ import annotations
import argparse, collections, gzip, json
from decimal import Decimal
from pathlib import Path
from scripts import phase57_capital_exit_integrated as run
from scripts import phase57_development_integrated_v0 as v0


def require(ok,reason):
    if not ok: raise ValueError(reason)


def audit(result_path, out):
    report=json.loads((result_path/'report.json').read_text())
    manifest=json.loads((result_path/'manifest.json').read_text())
    require(report['status']=='EXPERIMENTAL_DEVELOPMENT_INTEGRATED_REPLAY' and
            not report['rankSelected'] and not report['finalExitSelected'] and
            not any(report['safety'].values()),'EXPERIMENTAL_ONLY')
    require(manifest['precommitSha256']==run.PRECOMMIT_SHA256 and
            manifest['sourceSha256']==v0.digest(run.ROOT/'scripts/phase57_capital_exit_integrated.py'),
            'IMPLEMENTATION_DRIFT')
    for path,digest in manifest['filesSha256'].items():
        require(v0.digest(result_path/path)==digest,'RESULT_FILE_HASH:'+path)
    p,data,score,model=run.load_inputs()
    _,_,cohort,intents,evaluation,terminal,raw,_,_,labels=data
    replays=run.run_replays(data,score,model)
    controls={}
    for (arm,method),rep in replays.items():
        name='IM' if arm==v0.IM else 'R1'
        path=result_path/(name+'_'+method+'_ledger.json.gz')
        require(gzip.decompress(path.read_bytes())==v0.canonical(rep),
                'INDEPENDENT_REPLAY_BYTES:'+name+'_'+method)
        saved=report['arms'][name][method]
        require(len(rep['funded'])==saved['turnover']['fundedEntries'] and
                len(rep['closed'])==saved['turnover']['confirmedExits'] and
                sum(x['count'] for x in saved['fundedUpsideBuckets'])==len(rep['funded']) and
                saved['dailySummary']['tradingSessions']==24,'SUMMARY_DENOMINATORS')
        require(saved['upside']['positiveN']==saved['upside']['hitN']+saved['upside']['missN'] and
                sum(saved['upside']['missReasons'].values())==saved['upside']['missN'],
                'MISS_PARTITION')
        require(all(Decimal(x['cashJpy'])>=0 and x['openCount']<=3 for x in rep['snapshots']) and
                all(x['quantity']%100==0 for x in rep['funded'].values()),'CASH_CAPACITY_LOT')
        for event in rep['events']:
            source=terminal[arm] if method=='V3_B_TERMINAL' else model[arm]
            for x in event['exitEvents']:
                eid=x['entryId'];t=source[eid]
                require(event['minute']==(t['exitMinute'] if t['exitMinute'] is not None else 930)
                        and t['session']==event['session'],'EXIT_TIMESTAMP_CHANGED')
                require((x['status']=='CLOSED')==(t['exitPrice'] is not None),
                        'UNCONFIRMED_CASH_RELEASE')
                if x['status']=='CLOSED':
                    qty=rep['funded'][eid]['quantity']
                    require(Decimal(x['proceedsJpy'])==Decimal(str(t['exitPrice']))*qty,
                            'EXIT_PROCEEDS_CHANGED')
            ranked=[x['rank'] for x in event['sizing']]
            require(ranked==sorted(ranked),'FUNDED_ORDER_DIFFERENCE')
        final=rep['snapshots'][-1]
        cost=sum((Decimal(x['costBasisJpy']) for x in final['positions']),Decimal(0))
        require(Decimal(final['cashJpy'])+cost==1000000+Decimal(final['realizedPnlJpy']),
                'FINAL_CASH_COST_RECONCILIATION')
        d,stat=run.daily(rep,p['sessions'])
        require(v0.canonical(d)==v0.canonical(saved['daily']) and
                v0.canonical(stat)==v0.canonical(saved['dailySummary']),
                'EOD_REPORT_DIFFERS')
        if method=='V3_B_TERMINAL':
            archived=run.ROOT/'docs/evidence/phase57-capital-v3/RESULT'/(
                'CAPITAL_V3_B-'+name+'-MAX3-ledger.json.gz')
            require(gzip.decompress(archived.read_bytes())==v0.canonical(rep),
                    'V3_CI_TERMINAL_CONTROL_BYTES')
            controls[name]=v0.digest(archived)
    for arm in v0.ARMS:
        short='IM' if arm==v0.IM else 'R1'
        integ=replays[arm,'V3_B_R50_A'];base=replays[arm,'V3_B_TERMINAL']
        recycled=report['arms'][short]['recycling']
        identities=set(integ['funded'])-set(base['funded'])
        require(identities==set(recycled['recyclingFundedIds']) and
                len(identities)==recycled['recyclingFundedPositions'] and
                recycled['recyclingHighUpsideGe5']==sum(
                    evaluation[arm][eid]['postUpsidePct'] is not None and
                    evaluation[arm][eid]['postUpsidePct']>=5 for eid in identities),
                'RECYCLING_IDENTITY')
        confirmed={x['entryId']:x for x in recycled['earlyReleaseRows']}
        for item in recycled['recyclingRows']:
            require(item['precedingConfirmedEarlyExitIds'] and
                    all(confirmed[eid]['timestamp']<=item['entryTimestamp']
                        for eid in item['precedingConfirmedEarlyExitIds']),
                    'RECYCLING_WITHOUT_PRIOR_CONFIRMED_EXIT')
    receipt={'schema':'phase57-integrated-post-result-independent-audit-v1',
             'executionSha':manifest['executionSha'],
             'sourceSha256':manifest['sourceSha256'],
             'precommitSha256':manifest['precommitSha256'],
             'resultFiles':manifest['filesSha256'],
             'archivedV3BTerminalLedgerSha256':controls,
             'independentExactByteReplays':6,
             'tests':['six exact-byte replays','archived CI terminal controls exact',
                      'pinned exit reference and cash proceeds','cash/slot/100-lot invariants',
                      'exclusive misses','identity recycling and earlier exit witness',
                      'daily contiguous EOD and null preservation'],
             'result':'PASS','modelFits':0,'protectedOpened':0,'providerRequests':0,
             'safety':v0.SAFETY}
    out.write_bytes(v0.canonical(receipt))
    return receipt


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--result',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    x=audit(args.result,args.out)
    print(json.dumps({'result':x['result'],'exactReplays':x['independentExactByteReplays']},sort_keys=True))
