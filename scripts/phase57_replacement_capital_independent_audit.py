"""Independent, read-only audit of finite Replacement Capital Action artifacts.

The frozen Gate is read verbatim; this script never modifies funding or refits.
"""
from __future__ import annotations
import argparse
import collections
import gzip
import hashlib
import json
import math
from pathlib import Path

from scripts import phase57_replacement_capital as capital
from scripts import phase57_capital_exit_integrated as integrated
from scripts import phase57_development_integrated_v0 as v0


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(root,name):return json.loads((root/name).read_bytes())
def ledger(root,arm,candidate):
    prefix=('IM' if arm==v0.IM else 'R1')+'_'+candidate
    return json.loads(gzip.decompress((root/(prefix+'_ledger.json.gz')).read_bytes()))


def inspect(root,protocol,data):
    manifest=read(root,'manifest.json')
    predictions=read(root,'predictions.json')
    folds=read(root,'fold-manifests.json')
    report=read(root,'scorecard.json')
    verdict=read(root,'selection.json')
    assert manifest['protocolSha256']==capital.PROTOCOL_SHA256
    assert manifest['featureAuditSha256']==capital.AUDIT_SHA256
    assert digest(root/'predictions.json')==manifest['predictionSha256']
    assert all(digest(root/name)==h for name,h in manifest['filesSha256'].items())
    assert len(folds)==16 and len(protocol['sessions'])==24
    assert report['protocolSha256']==capital.PROTOCOL_SHA256
    assert all(not x for x in manifest['safety'].values())
    expected={(arm,target,f['id']) for arm in v0.ARMS
              for target in ('magnitude','prob3') for f in protocol['learning']['split']}
    assert {(x['arm'],x['target'],x['fold']) for x in folds}==expected
    for f in folds:
        fixed=next(x for x in protocol['learning']['split'] if x['id']==f['fold'])
        assert max(fixed['trainSessions'])==f['trainMax']<f['scoreMin']==min(fixed['testSessions'])
        assert not set(fixed['purgeSessions'])&set(fixed['trainSessions']+fixed['testSessions'])
        scored=[x['entryId'] for x in data[3][f['arm']]
                if x['timestamp'][:10] in fixed['testSessions']]
        assert f['testPredictionSha256']==hashlib.sha256(v0.canonical([
            (eid,predictions[f['arm']][f['target']][eid]) for eid in scored])).hexdigest()
    ledgers={}
    for arm in v0.ARMS:
        frozen={x['entryId'] for x in data[3][arm]
                if x['timestamp'][:10] in protocol['sessions']}
        assert all(set(predictions[arm][t])==frozen for t in ('magnitude','prob3'))
        for candidate in protocol['candidateIds']:
            result=ledger(root,arm,candidate)
            ledgers[arm,candidate]=result
            assert all(float(x['cashJpy'])>=0 and x['openCount']<=3 for x in result['snapshots'])
            assert all(x['quantity']>0 and x['quantity']%100==0 for x in result['funded'].values())
            releases=collections.defaultdict(list)
            for event in result['events']:
                for exit in event['exitEvents']:
                    if exit['status']=='CLOSED' and event['minute']<930:
                        releases[event['session']].append(event['minute'])
            for x in result['funded'].values():
                assert x['capitalContext']==('replacement' if any(m<=x['entryMinute']
                    for m in releases[x['session']]) else 'initial')
            name='IM' if arm==v0.IM else 'R1'
            card=report['arms'][name][candidate]
            assert card['cohorts']['initial']['N']+card['cohorts']['replacement']['N']==len(result['funded'])
            for quality in card['cohorts'].values():
                assert sum(z['count'] for z in quality['buckets'])==quality['N']
            assert card['fundedGe5']+len(card['missRows'])==card['availableGe5']
            assert sum(card['missReasons'].values())==len(card['missRows'])
            assert (card['utilization']['validUtilizationMinutes']+
                    card['utilization']['invalidUtilizationMinutes']==
                    card['utilization']['scheduledMinutes'])
            assert sum(card['utilization']['idleClassificationMinutes'].values())==card['utilization']['idleCashMinutes']
            assert all(x['dailyReturn'] is None for x in card['daily'] if not x['certified'])
            assert all(z in predictions[arm]['magnitude'] and z in predictions[arm]['prob3']
                       for z in result['funded'])
    return manifest,predictions,folds,report,verdict,ledgers


def compare(ci,repeat,protocol):
    left,right=ci[1],repeat[1]
    numbers={};funded={}
    for arm in v0.ARMS:
        for target in ('magnitude','prob3'):
            one,two=left[arm][target],right[arm][target]
            assert one.keys()==two.keys()
            key=('IM' if arm==v0.IM else 'R1')+'_'+target
            numbers[key]={'maxAbsDelta':max(abs(one[e]-two[e]) for e in one),
                          'differentCount':sum(one[e]!=two[e] for e in one)}
        for cid in protocol['candidateIds']:
            l,r=ci[5][arm,cid],repeat[5][arm,cid]
            key=('IM' if arm==v0.IM else 'R1')+'_'+cid
            funded[key]={'fundedIdsEqual':set(l['funded'])==set(r['funded']),
                         'fundedDetailsByteEqual':v0.canonical(l['funded'])==v0.canonical(r['funded']),
                         'closedTradesByteEqual':v0.canonical(l['closed'])==v0.canonical(r['closed']),
                         'fundedLedgerEqual':v0.canonical(l)==v0.canonical(r),
                         'rankingChangedEvents':sum([x['entryId'] for x in a['ranking']]!=
                             [x['entryId'] for x in b['ranking']]
                             for a,b in zip(l['events'],r['events']))
                             if len(l['events'])==len(r['events']) else None,
                         'qualityMembershipChangedEvents':sum({x['entryId'] for x in a['sizing']
                             if x['reason']=='QUALITY_FLOOR'}!={x['entryId'] for x in b['sizing']
                             if x['reason']=='QUALITY_FLOOR'}
                             for a,b in zip(l['events'],r['events']))
                             if len(l['events'])==len(r['events']) else None}
    return {'predictionBytesEqual':ci[0]['predictionSha256']==repeat[0]['predictionSha256'],
            'featureMatrixBytesEqual':ci[0]['featureMatrixSha256']==repeat[0]['featureMatrixSha256'],
            'numericalDelta':numbers,'funded':funded,
            'allFundedIdsEqual':all(x['fundedIdsEqual'] for x in funded.values()),
            'allFundedDetailsByteEqual':all(x['fundedDetailsByteEqual'] for x in funded.values()),
            'allClosedTradesByteEqual':all(x['closedTradesByteEqual'] for x in funded.values()),
            'allScorecardsByteEqual':v0.canonical(ci[3])==v0.canonical(repeat[3]),
            'allLedgersEqual':all(x['fundedLedgerEqual'] for x in funded.values()),
            'environments':{'action':ci[0]['versions'],'repeat':repeat[0]['versions']}}


def corrected_misses(report,ledgers,protocol):
    """Apply the frozen unresolved-first priority to post-replay attribution.

    The original report mislabeled older unresolved cash locks OTHER_CAUSAL.
    This addendum changes no funding, prediction, Gate or portfolio result.
    """
    corrected={}
    for arm in v0.ARMS:
        name='IM' if arm==v0.IM else 'R1'
        corrected[name]={}
        for cid in protocol['candidateIds']:
            card=report['arms'][name][cid]
            shots={(x['session'],x['minute']):x for x in ledgers[arm,cid]['snapshots']}
            rows=[]
            for x in card['missRows']:
                day,_,minute=x['entryId'].split('|')
                snap=shots.get((day,int(minute)))
                actual='UNRESOLVED_CASH_LOCK' if snap and snap['unresolvedCount']>0 else x['reason']
                rows.append({'entryId':x['entryId'],'archivedReason':x['reason'],
                             'frozenPriorityReason':actual,'postUpsidePct':x['postUpsidePct']})
            counts=dict(sorted(collections.Counter(x['frozenPriorityReason'] for x in rows).items()))
            assert sum(counts.values())==card['availableGe5']-card['fundedGe5']
            corrected[name][cid]={'counts':counts,'changed':sum(x['archivedReason']!=x['frozenPriorityReason']
                                                                for x in rows),'rows':rows}
    return corrected


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--ci',type=Path,required=True)
    ap.add_argument('--repeat',type=Path,required=True)
    ap.add_argument('--same-env-repeat',type=Path)
    ap.add_argument('--out',type=Path,required=True)
    args=ap.parse_args()
    protocol=capital.contract()
    _,data,_,_=integrated.load_inputs()
    a=inspect(args.ci,protocol,data);b=inspect(args.repeat,protocol,data)
    repro=compare(a,b,protocol)
    same_env=None
    if args.same_env_repeat:
        c=inspect(args.same_env_repeat,protocol,data)
        same_env=compare(b,c,protocol)
        assert b[0]['executionSha']==c[0]['executionSha']
        assert b[0]['versions']==c[0]['versions']
    corrected=corrected_misses(a[3],a[5],protocol)
    # Each candidate failed several frozen quality and reach Gates even before
    # reproducibility. Therefore final NO_SELECTION is independent of tie rules.
    votes=a[4]['votes']
    assert all(x['passBeforeIndependentAudit'] is False for x in votes.values())
    assert all(x['checks']['replacement_ge5'] is False for x in votes.values())
    same_pass=(same_env is not None and same_env['predictionBytesEqual'] and
               same_env['featureMatrixBytesEqual'] and same_env['allLedgersEqual'])
    result={'schema':'phase57-replacement-capital-independent-audit-v1',
        'status':'PASS_WITH_ATTRIBUTION_ADDENDUM' if repro['allFundedIdsEqual'] and same_pass
                 else 'REPRODUCIBILITY_FAIL_NO_SELECTION',
        'selection':'NO_SELECTION_STOP','protocolSha256':capital.PROTOCOL_SHA256,
        'actionExecutionSha':a[0]['executionSha'],'repeatExecutionSha':b[0]['executionSha'],
        'sourceSha256':digest(capital.ROOT/'scripts/phase57_replacement_capital.py'),
        'predictionAndLedgerReproducibility':repro,'frozenGateVotes':votes,
        'sameEnvironmentRepeat':same_env,
        'frozenUnresolvedMissPriorityAddendum':corrected,
        'fundedDecisionChangedByAddendum':False,'providerRequests':0,
        'protectedPartitionsOpened':0,'finalExitSelected':False,'safety':v0.SAFETY}
    args.out.write_bytes(v0.canonical(result))
    print(json.dumps({'status':result['status'],'selection':result['selection'],
                      'predictionEqual':repro['predictionBytesEqual'],
                      'fundedEqual':repro['allFundedIdsEqual'],
                      'R1MissCorrections':corrected['R1']['RC_MAG_FLOOR']['changed']}))

if __name__=='__main__':main()
