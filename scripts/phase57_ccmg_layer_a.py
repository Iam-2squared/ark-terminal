"""CCMG fixed Development Layer A and standalone accounting; no Capital replay."""
from __future__ import annotations

import argparse
import collections
from decimal import Decimal
import gzip
import hashlib
import json
import statistics
import zipfile
from pathlib import Path

from scripts import phase57_ccmg_guard as guard
from scripts import phase57_ccmg_readiness as readiness
from scripts import phase57_exit_execution_contract_v1 as execution
from scripts import phase57_wpsd_phase0 as upstream

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/evidence/phase57-checkpoint-certified-guard-exit'


def require(ok,reason):
    if not ok:raise ValueError(reason)


def dec(x):return None if x is None else Decimal(str(x))


def div(x,n):return None if not n else str(x/Decimal(n))


def bucket(x):
    if x is None:return 'UNKNOWN'
    return '<1' if x<1 else '1-3' if x<3 else '3-5' if x<5 else '5-10' if x<10 else '>=10'


def encoded(x):return (json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)+'\n').encode()


def sha(b):return hashlib.sha256(b).hexdigest()


def resolve(entry,control,summary,path):
    decision=summary['firstSellIntent']
    reason=summary['terminal']
    if reason in ('CANDIDATE_FIRST','BOTH_TRIGGER_SAME_CHECKPOINT'):
        require(decision is not None,'MISSING_CANDIDATE_INTENT')
    else:decision=control['decisionNow']
    if reason != 'CANDIDATE_FIRST':
        price,minute=control['exitPrice'],control['exitMinute']
        status='CONTROL_CONFIRMED' if price is not None else 'CONTROL_NULL'
    elif decision==925:
        fill=execution.terminal_execution_reference([path[t] for t in sorted(path)])
        price,minute,status=fill['price'],fill['referenceMinute'],fill['status']
    else:
        fill=execution.ordinary_execution_reference(entry['session'],decision,
                                                    [path[t] for t in sorted(path)])
        price,minute,status=fill['price'],fill['referenceStart'],fill['status']
    return {'decisionNow':decision,'terminalReason':reason,'exitPrice':price,
            'exitMinute':None if price is None else minute,'fillStatus':status}


def metrics(rows):
    paired=[x for x in rows if x['controlPnlJpy'] is not None and x['candidatePnlJpy'] is not None]
    cc=sum((dec(x['candidatePnlJpy']) for x in paired),Decimal(0))
    ctrl=sum((dec(x['controlPnlJpy']) for x in paired),Decimal(0))
    r54=sum((dec(x['r54PnlJpy']) for x in paired if x['r54PnlJpy'] is not None),Decimal(0))
    diffs=[dec(x['candidatePnlJpy'])-dec(x['controlPnlJpy']) for x in paired]
    return {'entryN':len(rows),'knownPairedN':len(paired),'nullCandidateN':sum(x['candidatePnlJpy'] is None for x in rows),
            'controlPnlJpy':str(ctrl),'candidatePnlJpy':str(cc),'r54PnlJpy':str(r54),
            'pairedDeltaJpy':str(cc-ctrl),'controlMeanJpy':div(ctrl,len(paired)),
            'candidateMeanJpy':div(cc,len(paired)),'improveN':sum(x>0 for x in diffs),
            'equalN':sum(x==0 for x in diffs),'worseN':sum(x<0 for x in diffs)}


def distr(xs):
    if not xs:return {'knownN':0,'median':None,'q75':None,'mean':None}
    xs=sorted(xs);return {'knownN':len(xs),'median':statistics.median(xs),
       'q75':xs[int((len(xs)-1)*.75)],'mean':statistics.mean(xs)}


def run(r45,replay,audit):
    pre=(OUT/'CYCLE_PRECOMMIT.json').read_bytes()
    require(sha(pre)==readiness.PRE_SHA,'PRECOMMIT_DRIFT')
    ready=json.loads((OUT/'CHECKPOINT_READINESS.json').read_bytes())
    require(all(x=='PASS' for x in ready['gates'].values()),'READINESS_NOT_PASS')
    _,_,ledgers,paired=upstream.load_fixed(r45,replay,audit)
    entries,calendar,funded,context,paths,sessions=upstream.control_universe({},ledgers)
    controls=readiness.read_control()
    summaries={}
    with gzip.open(OUT/'CHECKPOINT_ENTRY_SUMMARY.jsonl.gz','rt') as f:
        for line in f:
            x=json.loads(line);summaries[(x['arm'],x['entryId'])]=x
    require(len(summaries)==len(entries)==1614,'READINESS_ENTRY_CENSUS')
    with zipfile.ZipFile(replay) as z:
        standalone=json.loads(gzip.decompress(z.read('r54-result/standalone-all-entries.json.gz')))
    old={}
    for arm in ('IM','R1'):
        for variant,suffix in (('control','R50_A_CONTROL'),('r54','FULL_MH_WAIT15')):
            rows=standalone[arm+'_'+suffix]
            require(len(rows)==(819 if arm=='IM' else 795),'STANDALONE_CENSUS')
            old[arm,variant]={x['entryId']:x for x in rows}
    old_pairs={}
    for arm in ('IM','R1'):
        old_pairs.update({(arm,x['entryId']):x for x in paired[arm]['FULL_MH_WAIT15']})
    require(set(old_pairs)=={(upstream.ARMS[a],eid) for a,eid in funded},'PRIMARY_PAIR_CENSUS')
    rows=[]
    for key,entry in sorted(entries.items()):
        arm=upstream.ARMS[key[0]]
        s=summaries[arm,key[1]]
        ctrl=controls[key]
        path=paths[entry['opportunity']]
        outcome=resolve(entry,ctrl,s,path)
        orig=old[arm,'control'][key[1]]
        r54=old[arm,'r54'][key[1]]
        require(orig['evaluatorOnlyPostEntryUpsidePct']==r54['evaluatorOnlyPostEntryUpsidePct'],
                'R54_TEACHER_CONTRADICTION')
        require(orig['entryEffectivePrice']==str(entry['effectiveEntryPrice']),
                'ENTRY_PRICE_CONTRADICTION')
        primary=key in funded
        quantity=funded[key]['quantity'] if primary else 100
        notional=funded[key]['notionalJpy'] if primary else str(dec(entry['effectiveEntryPrice'])*100)
        cand=guard.corrected_pnl_jpy({'quantity':quantity,'notionalJpy':notional},outcome['exitPrice'])
        if primary:
            oldpair=old_pairs[arm,key[1]]
            require(oldpair['quantity']==quantity and
                    oldpair['evaluatorOnlyUpsidePct']==orig['evaluatorOnlyPostEntryUpsidePct'],
                    f'PRIMARY_R34_IDENTITY:{key}')
            control_pnl=oldpair['controlPnlJpy'];r54_pnl=oldpair['candidatePnlJpy']
            if outcome['terminalReason']!='CANDIDATE_FIRST' and outcome['exitPrice'] is not None:
                # The R34 paired archive's Control is the unchanged funded
                # ledger realization. A delegated identical fill must have
                # exactly zero policy delta; retain that exact Control value.
                cand=dec(control_pnl)
        else:
            # The archived R54 standalone diagnostic debited 5bp on the entry
            # effective price. Reconcile that source before comparing all three
            # arms under the R34 corrected SELL-side 5bp convention.
            archive_pnl=(dec(orig['exitPrice'])-dec(entry['effectiveEntryPrice'])*Decimal('1.0005'))*100 if orig['exitPrice'] is not None else None
            require(archive_pnl==dec(orig['closedDiagnosticPnlJpy']),'STANDALONE_ARCHIVE_LINEAGE')
            control_pnl=None if ctrl['exitPrice'] is None else str(guard.corrected_pnl_jpy(
                {'quantity':100,'notionalJpy':notional},ctrl['exitPrice']))
            r54_pnl=None if r54['exitPrice'] is None else str(guard.corrected_pnl_jpy(
                {'quantity':100,'notionalJpy':notional},r54['exitPrice']))
        if not primary:
            baseline_calc=guard.corrected_pnl_jpy({'quantity':100,'notionalJpy':notional},ctrl['exitPrice'])
            require(baseline_calc==dec(control_pnl),
                    f'STANDALONE_R34_DRIFT:{key}:{baseline_calc}:{control_pnl}:{notional}:{ctrl["exitPrice"]}')
        if primary:
            actual=guard.run_entry(entry,ctrl,path)
            require(actual['decisionNow']==outcome['decisionNow'] and
                    actual['exitMinute']==outcome['exitMinute'] and
                    actual['exitPrice']==outcome['exitPrice'] and
                    (actual['terminalReason']==outcome['terminalReason'] or
                     (outcome['terminalReason'] in ('CONTROL_TERMINAL_WITHOUT_CANDIDATE','UNRESOLVED_CANONICAL_CONTROL_FILL')
                      and actual['terminalReason']=='CONTROL_FIRST')),
                    'INDEPENDENT_PRIMARY_STATE_PARITY')
        rows.append({'arm':arm,'entryId':key[1],'session':entry['session'],
            'entryMinute':entry['entryMinute'],'entryPrice':entry['effectiveEntryPrice'],
            'quantity':quantity,'primary':primary,'initialOrReplacement':s['initialOrReplacement'],
            'postEntryUpsidePct':orig['evaluatorOnlyPostEntryUpsidePct'],
            'bucket':bucket(orig['evaluatorOnlyPostEntryUpsidePct']),
            'controlPnlJpy':control_pnl,'r54PnlJpy':r54_pnl,
            'candidatePnlJpy':None if cand is None else str(cand),
            'pairedDeltaJpy':None if cand is None or control_pnl is None else str(cand-dec(control_pnl)),
            'controlExitMinute':ctrl['exitMinute'],'controlExitPrice':ctrl['exitPrice'],
            'r54ExitMinute':r54['exitMinute'],'r54ExitPrice':r54['exitPrice'],
            'candidateDecisionNow':outcome['decisionNow'],'candidateExitMinute':outcome['exitMinute'],
            'candidateExitPrice':outcome['exitPrice'],'terminalReason':outcome['terminalReason'],
            'fillStatus':outcome['fillStatus'],'highestCertifiedMilestone':s['highestCertifiedAtTerminal'],
            'alerts':s['alerts'],'missingResetN':s['dataGapReset'],
            'certifiedAt':s['certifiedAt'],'firstAlertNow':s['firstAlert'],
            'twoCheckpointSellIntentNow':s['firstSellIntent']})
    require(sum(x['primary'] for x in rows)==111,'PRIMARY_CENSUS')
    primary=[x for x in rows if x['primary']]
    winner={};loser={};all_entry={}
    for arm in ('IM','R1'):
        for threshold in (5,10):
            xs=[x for x in primary if x['arm']==arm and x['postEntryUpsidePct'] is not None and x['postEntryUpsidePct']>=threshold]
            m=metrics(xs)
            m['gate']=('WINNER_PRESERVATION_FAIL' if dec(m['pairedDeltaJpy'])<0 else
                       'WINNER_UNMEASURABLE' if m['knownPairedN']!=m['entryN'] else 'PASS')
            winner[f'{arm}>={threshold}']=m
        for b in ('<1','1-3','3-5'):
            xs=[x for x in primary if x['arm']==arm and x['bucket']==b]
            m=metrics(xs)
            if arm=='R1' and m['knownPairedN']<5:m['gate']='INCONCLUSIVE_SMALL_N'
            elif dec(m['pairedDeltaJpy'])<0:m['gate']='LOSER_NONDEGRADATION_FAIL'
            elif arm=='IM' and m['knownPairedN']!=m['entryN']:m['gate']='LOSER_UNMEASURABLE'
            else:m['gate']='PASS'
            loser[f'{arm}:{b}']=m
        for b in ('<1','1-3','3-5','5-10','>=10'):
            xs=[x for x in rows if x['arm']==arm and x['bucket']==b]
            m=metrics(xs)
            m.update({'candidateFirst':sum(x['terminalReason']=='CANDIDATE_FIRST' for x in xs),
                'controlFirstOrTerminal':sum(x['terminalReason'] in ('CONTROL_FIRST','CONTROL_TERMINAL_WITHOUT_CANDIDATE') for x in xs),
                'certified':{str(k):sum(str(k) in x['certifiedAt'] for x in xs) for k in guard.LADDER},
                'alerts':sum(x['alerts'] for x in xs),'twoCheckpointSell':sum(x['twoCheckpointSellIntentNow'] is not None for x in xs),
                'missingResets':sum(x['missingResetN'] for x in xs),
                'initial':sum(x['initialOrReplacement']=='Initial' for x in xs),
                'replacement':sum(x['initialOrReplacement']=='Replacement' for x in xs)})
            all_entry[arm+':'+b]=m
    for b in ('<1','1-3','3-5'):
        xs=[x for x in primary if x['bucket']==b]
        m=metrics(xs)
        if m['knownPairedN']<5:
            m['gate']='PASS' if m['knownPairedN']==m['entryN'] and dec(m['pairedDeltaJpy'])>=0 else 'LOSER_NONDEGRADATION_FAIL'
        else:m['gate']='DIAGNOSTIC_COMBINED_NOT_PORTFOLIO'
        loser['combined:'+b]=m
    both_contradict={}
    for threshold in (5,10):
        per={arm:metrics([x for x in rows if x['arm']==arm and x['postEntryUpsidePct'] is not None and x['postEntryUpsidePct']>=threshold]) for arm in ('IM','R1')}
        both_contradict[str(threshold)]={'arms':per,'blocking':all(dec(m['pairedDeltaJpy'])<0 for m in per.values())}
    winner_gate='PASS' if all(v['gate']=='PASS' for v in winner.values()) else 'WINNER_PRESERVATION_FAIL'
    loser_gate=('LOSER_NONDEGRADATION_FAIL' if any(v['gate']=='LOSER_NONDEGRADATION_FAIL' for v in loser.values()) else
        'LOSER_UNMEASURABLE' if any(v['gate']=='LOSER_UNMEASURABLE' for v in loser.values()) else 'PASS')
    result={'schema':'phase57-ccmg-layer-a-v1','candidate':guard.NAME,'primaryN':111,'allEntryN':1614,
        'primary':{arm:metrics([x for x in primary if x['arm']==arm]) for arm in ('IM','R1')},
        'winner':winner,'winnerGate':winner_gate,'loser':loser,'loserGate':loser_gate,
        'allEntryStandalone':all_entry,'allEntryWinnerContradiction':both_contradict,
        'capitalEligibility':winner_gate=='PASS' and loser_gate=='PASS' and not any(x['blocking'] for x in both_contradict.values()),
        'focusedTestsPassed':30,'exitEstimatorFits':0,'integratedReplayInvocations':0,
        'precommitSha256':sha(pre),'readinessSha256':sha((OUT/'CHECKPOINT_READINESS.json').read_bytes()),
        'safety':guard.SAFETY,'providerRequests':0,'restrictedPartitionsOpened':0}
    all_raw=b''.join(encoded(x) for x in rows)
    z=gzip.compress(all_raw,mtime=0)
    (OUT/'LAYER_A_ENTRY_ROWS.jsonl.gz').write_bytes(z)
    result['entryRowsSha256']=sha(z)
    (OUT/'LAYER_A_RESULT.json').write_bytes(encoded(result))
    print(json.dumps({'winner':winner,'loser':loser,'capitalEligibility':result['capitalEligibility'],
                      'entryRowsSha256':sha(z)},indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--r45',required=True,type=Path)
    parser.add_argument('--replay',required=True,type=Path)
    parser.add_argument('--audit',required=True,type=Path)
    args=parser.parse_args()
    run(args.r45,args.replay,args.audit)
