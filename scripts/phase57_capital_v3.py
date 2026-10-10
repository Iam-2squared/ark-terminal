"""Frozen Capital v3: temporal predictions followed by chronological cash allocation.

Research only. The frozen Entry/EXIT and existing cash/valuation implementations
are called without modifying their contracts. Future labels enter attribution
only after the portfolio replay has returned its immutable funding decisions.
"""
from __future__ import annotations

import argparse
import collections
import copy
import gzip
import hashlib
import json
import math
import statistics
from decimal import Decimal
from pathlib import Path

import numpy as np

from scripts import phase57_capital_rank_v2 as old
from scripts import phase57_capital_v3_geometry as geometry
from scripts import phase57_development_integrated_v0 as v0
from scripts import phase57_development_integrated_v1 as v1

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'docs/evidence/phase57-comprehensive-exit-v1'
PRECOMMIT = EVIDENCE / 'CAPITAL_V3_PREGEOMETRY_PRECOMMIT.json'
GEOMETRY = EVIDENCE / 'CAPITAL_V3_GEOMETRY.json'
AUDIT = EVIDENCE / 'CAPITAL_V3_FEATURE_AUDIT.json'
GATE = EVIDENCE / 'CAPITAL_V3_SELECTION_GATE.json'
PINS = {'precommit':'3007e284ae346b4d4d01122c3b08473188bea625b7ab4a8c01e4bb9bfd0edc29',
        'geometry':'5da6e62a60c51325bd73ee2deece6e119f248211793918bbdb407d55180b6150',
        'audit':'343ec6905d731ca45dff884ef3b7308209bcf97f8fbe68ad3ee019e053fbfcb1',
        'gate':'ac2a88d5ec6c6cbf83a5ac66f68f799761c4dc6438f74c367d5d60cceef1689c'}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def contract():
    paths = {'precommit':PRECOMMIT,'geometry':GEOMETRY,'audit':AUDIT,'gate':GATE}
    v0.require(all(sha(path)==PINS[key] for key,path in paths.items()), 'V3_PREPERFORMANCE_PINS')
    pre,geo,audit,gate = [json.loads(paths[k].read_text()) for k in paths]
    v0.require(gate['precommitSha256']==PINS['precommit'] and
               gate['geometrySha256']==PINS['geometry'] and
               gate['featureAuditSha256']==PINS['audit'], 'V3_DEPENDENCY_CHAIN')
    v0.require(gate['status']=='FROZEN_AFTER_GEOMETRY_BEFORE_V3_FITS_AND_FUNDED_PERFORMANCE',
               'V3_GATE_NOT_FROZEN')
    v0.require(geo['newPredictionsInspected']==geo['newFundedPerformanceInspected']==0 and
               geometry.geometry()==geo, 'V3_GEOMETRY_CHANGED')
    names=old.contract()[0]['features']['sets']['C']
    v0.require([x['name'] for x in audit['features']]==names and len(names)==254 and
               all(x['decision']=='ALLOWED' for x in audit['features']), 'V3_FEATURE_AUDIT')
    v0.require(pre['safety']==gate['safety']==audit['safety']==v0.SAFETY and
               not any(v0.SAFETY.values()) and len(gate['candidateIds'])==2 and
               gate['modelFitsExpected']==16, 'V3_SAFETY_OR_FINITE_SPACE')
    return pre,geo,audit,gate,names


def preflight(ledger_path,r1_path,raw_path,features=False):
    pre,geo,audit,gate,names=contract()
    data=old.load_inputs(ledger_path,r1_path,raw_path)
    support=old.support_only(data)
    receipt={'schema':'phase57-capital-v3-prefit-v1','pins':PINS,
             'supports':support['support'],'geometry':{a:{'fundedControl':v['fundedControl'],
             'trueRankingContestEvents':v['trueRankingContestEvents']} for a,v in geo['arms'].items()},
             'candidateCount':2,'modelFits':0,'fundedPerformanceInspected':0,
             'portfolioReplays':0,'protectedOpened':0,'providerRequests':0,'safety':v0.SAFETY}
    if features:
        table=old.feature_table(data,names)
        receipt['featureMatrixSha256']=hashlib.sha256(v0.canonical(table)).hexdigest()
        receipt['featureRowsByArm']={a:len(v) for a,v in table.items()}
    return data,receipt


def temporal_oof(data,names,pre,gate):
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LogisticRegression, Ridge
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    _,_,_,intents,evaluation,_,_,_,_,labels=data
    table=old.feature_table(data,names)
    scores={c:{arm:{} for arm in v0.ARMS} for c in gate['candidateIds']}
    manifests=[]
    for candidate in pre['learning']['candidates']:
        cid=candidate['id']
        for arm in v0.ARMS:
            for fold in data[0]['split']['folds']:
                train=[x for x in intents[arm] if x['timestamp'][:10] in fold['trainSessions']
                       and labels[arm][x['entryId']] is not None]
                test=[x for x in intents[arm] if x['timestamp'][:10] in fold['testSessions']]
                v0.require(max(fold['trainSessions'])<min(fold['testSessions']) and
                           not set(fold['purgeSessions']) & set(fold['trainSessions']+fold['testSessions']),
                           'V3_TIME_OR_PURGE_LEAK')
                matrix=lambda rows:np.asarray([[np.nan if y is None else y
                    for y in table[arm][row['entryId']]] for row in rows],dtype=float)
                X,Z=matrix(train),matrix(test)
                if cid=='CAPITAL_V3_A':
                    y=np.asarray([labels[arm][row['entryId']] for row in train],dtype=int)
                    estimator=LogisticRegression(**candidate['parameters'])
                else:
                    y=np.asarray([min(20.0,max(0.0,evaluation[arm][row['entryId']]['postUpsidePct']))
                                  for row in train],dtype=float)
                    estimator=Ridge(**candidate['parameters'])
                model=make_pipeline(SimpleImputer(strategy='constant',fill_value=0,
                                   add_indicator=True,keep_empty_features=True),
                                   StandardScaler(),estimator)
                model.fit(X,y)
                pred=model.predict_proba(Z)[:,1] if cid=='CAPITAL_V3_A' else model.predict(Z)
                v0.require(len(pred)==len(test) and np.isfinite(pred).all(),'V3_BAD_PREDICTION')
                for row,value in zip(test,pred):
                    eid=row['entryId']
                    v0.require(eid not in scores[cid][arm],'V3_DUPLICATE_OOF')
                    scores[cid][arm][eid]=float(value)
                manifests.append({'candidate':cid,'arm':arm,'fold':fold['id'],
                                  'train':len(train),'test':len(test),
                                  'trainMaxSession':max(fold['trainSessions']),
                                  'scoreMinSession':min(fold['testSessions']),
                                  'predictionSha256':hashlib.sha256(v0.canonical(
                                      [(x['entryId'],scores[cid][arm][x['entryId']]) for x in test])).hexdigest()})
    v0.require(len(manifests)==gate['modelFitsExpected'],'V3_FIT_COUNT')
    return scores,manifests,hashlib.sha256(v0.canonical(table)).hexdigest()


def ranked_intents(intents,score):
    rows=[dict(x) for x in intents]
    if score is None:
        return rows
    groups=collections.defaultdict(list)
    for row in rows:
        v0.require(row['entryId'] in score,'V3_MISSING_OOF_SCORE')
        groups[row['timestamp']].append(row)
    for timestamp,items in groups.items():
        order=sorted(items,key=lambda x:(-score[x['entryId']],)+v0.event_priority(x))
        for rank,row in enumerate(order,1):
            row['newEligibleRank']=rank
            row['rankKnownAt']=timestamp
    return rows


def replay_primary(data,arm,score=None):
    _,_,cohort,intents,_,terminal,raw,_,_,_=data
    sessions=json.loads(old.WINDOW.read_text())['portfolioSessions']
    selected=set(sessions)
    rows=ranked_intents([x for x in intents[arm] if x['timestamp'][:10] in selected],score)
    exits={eid:x for eid,x in terminal[arm].items() if x['session'] in selected}
    v0.require(len(rows)==len(exits),'V3_EXIT_COHORT')
    result=v1.replay(arm,3,{**cohort,'sessions':sessions},rows,exits,raw)
    v0.require(result['safety']==v0.SAFETY and not any(result['safety'].values()),'V3_REPLAY_SAFETY')
    return result


def reason_for_miss(item,event,snapshot,by_id):
    """One causal reason; no evaluator fields are read by this classifier."""
    if event is None or item is None: return 'ENTRY_NOT_ELIGIBLE'
    reason=item.get('reason')
    if snapshot['unresolvedCount']>0: return 'UNRESOLVED_CASH_LOCK'
    initial_open=snapshot['openCount']-sum(x['status']=='SIZED' for x in event['sizing'])
    if reason=='MAX_CONCURRENT_SYMBOLS':
        return 'CAPACITY_FULL' if initial_open>=3 else 'RANK_LOSS'
    if reason=='NO_100_SHARE_LOT_WITHIN_TARGET_AND_CASH':
        price=Decimal(str(by_id[item['entryId']]['effectiveEntryPrice']))
        cash=Decimal(str(item['cashBeforeSizingJpy']))
        if cash < price*100: return 'INSUFFICIENT_CASH'
        if any(x['status']=='SIZED' for x in event['sizing']):
            ordered=[x['entryId'] for x in event['sizing']]
            if any(x['status']=='SIZED' and ordered.index(x['entryId'])<ordered.index(item['entryId'])
                   for x in event['sizing']): return 'RANK_LOSS'
        return 'LOT_INFEASIBLE'
    return 'OTHER_CAUSAL'


def attribute(result,intents,evaluation,labels,folds):
    """Only called after replay. Future labels never enter funded decisions."""
    funded=result['funded']
    candidates={x['entryId']:x for x in intents}
    eval_rows=[x for x in intents if x['entryId'] in evaluation]
    known=[x for x in eval_rows if labels[x['entryId']] is not None]
    positives=[x for x in known if labels[x['entryId']]==1]
    funded_known=[x for x in known if x['entryId'] in funded]
    hits=[x for x in funded_known if labels[x['entryId']]==1]
    event_by_id={x['entryId']:event for event in result['events'] for x in event['sizing']}
    snapshot_by_stamp={x['timestamp']:x for x in result['snapshots']}
    misses=collections.Counter()
    miss_rows=[]
    for x in positives:
        eid=x['entryId']
        if eid in funded:continue
        event=event_by_id.get(eid)
        row=next((q for q in event['sizing'] if q['entryId']==eid),None) if event else None
        snap=snapshot_by_stamp.get(x['timestamp'])
        reason=reason_for_miss(row,event,snap,candidates) if row and snap else 'ENTRY_NOT_ELIGIBLE'
        misses[reason]+=1
        miss_rows.append({'entryId':eid,'reason':reason})
    assert len(miss_rows)+len(hits)==len(positives)
    upsides=[evaluation[x['entryId']]['postUpsidePct'] for x in funded_known]
    positive_cap=sum(Decimal(str(funded[x['entryId']]['notionalJpy'])) for x in hits)
    known_cap=sum(Decimal(str(funded[x['entryId']]['notionalJpy'])) for x in funded_known)
    symbol=collections.Counter(x['symbol'] for x in funded.values())
    session=collections.Counter(x['session'] for x in funded.values())
    snapshots=result['snapshots']
    valid=[float(x['utilization']) for x in snapshots if x['utilization'] is not None]
    notional=sum(Decimal(str(x['notionalJpy'])) for x in funded.values())
    proceeds=sum(Decimal(str(x['notionalJpy']))+Decimal(str(x['realizedPnlJpy'])) for x in result['closed'])
    by_fold=[]
    for f in folds:
        subset=set(f['testSessions'])
        k=[x for x in funded_known if x['timestamp'][:10] in subset]
        by_fold.append({'fold':f['id'],'knownFunded':len(k),
                        'hit':sum(labels[x['entryId']]==1 for x in k),
                        'hitRate':sum(labels[x['entryId']]==1 for x in k)/len(k) if k else None})
    ge=lambda threshold:sum(x>=threshold for x in upsides)
    return {'candidateN':len(eval_rows),'knownN':len(known),'positiveN':len(positives),
            'fundedN':len(funded),'fundedKnownN':len(funded_known),'fundedUnknownN':len(funded)-len(funded_known),
            'hitN':len(hits),'hitRate':len(hits)/len(funded_known) if funded_known else None,
            'baselineHitRate':len(positives)/len(known),
            'enrichment':(len(hits)/len(funded_known))/(len(positives)/len(known)) if funded_known else None,
            'reach':len(hits)/len(positives),'missN':len(miss_rows),
            'missReasons':dict(sorted(misses.items())),'missRows':miss_rows,
            'highUpsideCapitalShare':float(positive_cap/known_cap) if known_cap else None,
            'ge7_5Rate':ge(7.5)/len(funded_known) if funded_known else None,
            'ge7_5Reach':ge(7.5)/sum(evaluation[x['entryId']]['postUpsidePct']>=7.5 for x in known),
            'ge10Rate':ge(10)/len(funded_known) if funded_known else None,
            'ge10Reach':ge(10)/sum(evaluation[x['entryId']]['postUpsidePct']>=10 for x in known),
            'upsideMeanPct':statistics.fmean(upsides) if upsides else None,
            'upsideMedianPct':statistics.median(upsides) if upsides else None,
            'upsideP05Pct':v0.percentile(upsides,.05),'upsideP10Pct':v0.percentile(upsides,.10),
            'upsideP90Pct':v0.percentile(upsides,.90),
            'canonicalL2HGe5Funded':sum(evaluation[x['entryId']]['canonicalBucket']=='>=5%' for x in funded_known),
            'entryNotionalJpy':str(notional),'turnoverClosedJpy':str(proceeds+sum(Decimal(str(x['notionalJpy'])) for x in result['closed'])),
            'utilizationValidOnlyMean':statistics.fmean(valid) if valid else None,
            'utilizationValidObservations':len(valid),'snapshots':len(snapshots),
            'symbolTopShare':max(symbol.values())/len(funded) if funded else None,
            'sessionTopShare':max(session.values())/len(funded) if funded else None,
            'unresolvedCount':len(result['unresolvedEntryIds']),'folds':by_fold}


def decision(cards,control,gate):
    rules=gate['requirementsPerArm']
    votes={}
    for candidate,arms in cards.items():
        errors=[]
        for arm in v0.ARMS:
            a,b=arms[arm],control[arm]
            metrics={'hit_delta':a['hitRate'] is not None and b['hitRate'] is not None and
                     a['hitRate']-b['hitRate']>=rules['fundedHitRateAbsoluteDeltaMin'],
                     'enrichment':a['enrichment'] is not None and
                     a['enrichment']>=rules['fundedEnrichmentAbsoluteMin'] and
                     a['enrichment']-b['enrichment']>=rules['fundedEnrichmentVsControlDeltaMin'],
                     'reach':a['reach']-b['reach']>=rules['highUpsideReachVsControlDeltaMin'],
                     'capital_share':a['highUpsideCapitalShare'] is not None and
                     a['highUpsideCapitalShare']-b['highUpsideCapitalShare']>=rules['highUpsideCapitalShareVsControlDeltaMin'],
                     'ge7_5':a['ge7_5Rate'] is not None and
                     a['ge7_5Rate']-b['ge7_5Rate']>=rules['ge7_5FundedRateVsControlDeltaMin'],
                     'ge10':a['ge10Rate'] is not None and
                     a['ge10Rate']-b['ge10Rate']>=rules['ge10FundedRateVsControlDeltaMin'],
                     'symbol':a['symbolTopShare'] is not None and
                     a['symbolTopShare']<=b['symbolTopShare']+rules['symbolTopShareMaxControlPlus'],
                     'session':a['sessionTopShare'] is not None and
                     a['sessionTopShare']<=b['sessionTopShare']+rules['sessionTopShareMaxControlPlus'],
                     'label_coverage':a['knownN']/a['candidateN']>=gate['knownLabelCoverageMin']}
            fs=gate['foldStability'][arm]
            pairs=[(x,y) for x,y in zip(a['folds'],b['folds']) if y['hitRate'] is not None]
            metrics['informative_folds']=len(pairs)==fs['controlInformativeFolds']
            metrics['fold_noninferior']=sum(x['hitRate'] is not None and
                x['hitRate']>=y['hitRate'] for x,y in pairs)>=fs['noninferiorMin']
            metrics['fold_strict']=sum(x['hitRate'] is not None and
                x['hitRate']>y['hitRate'] for x,y in pairs)>=fs['strictImproveMin']
            errors.extend(arm+':'+k for k,ok in metrics.items() if not ok)
        votes[candidate]={'pass':not errors,'failures':errors}
    passing=[c for c,v in votes.items() if v['pass']]
    selected=None
    if len(passing)==1:selected=passing[0]
    elif len(passing)>1:
        values={c:min(cards[c][a]['hitRate']-control[a]['hitRate'] for a in v0.ARMS) for c in passing}
        highest=max(values.values())
        winners=[c for c,v in values.items() if v==highest]
        selected=winners[0] if len(winners)==1 else None
    return {'votes':votes,'selected':selected,'status':'SELECT' if selected else 'NO_SELECTION_STOP'}


def certified_eod(ledger,sessions):
    byday={x['session']:x for x in ledger['snapshots'] if x['minute']==930}
    rows=[]
    previous=Decimal('1000000')
    valid_run=True
    for day in sessions:
        snap=byday.get(day)
        valid=(snap is not None and snap['openCount']==snap['unresolvedCount']==0 and
               snap['equityValid'] and
               Decimal(str(snap['equityJpy']))==Decimal(str(snap['cashJpy'])))
        equity=Decimal(str(snap['cashJpy'])) if valid else None
        rate=float(equity/previous-1) if valid and valid_run else None
        rows.append({'session':day,'cashJpy':snap['cashJpy'] if snap else None,
                     'equityJpy':str(equity) if equity is not None else None,
                     'dailyReturn':rate,'certified':bool(valid)})
        if not valid: valid_run=False
        elif valid_run:previous=equity
    rates=[x['dailyReturn'] for x in rows]
    if all(x is not None for x in rates):
        geo=(previous/Decimal('1000000'))**(Decimal(1)/Decimal(len(rows)))-1
        summary={'arithmeticMean':statistics.fmean(rates),'median':statistics.median(rates),
                 'geometric':float(geo),'positiveDayRate':sum(x>0 for x in rates)/len(rates),
                 'negativeDayRate':sum(x<0 for x in rates)/len(rates),
                 'best':max(rates),'worst':min(rates),'p05':v0.percentile(rates,.05),
                 'p10':v0.percentile(rates,.10),'cumulativeReturn':float(previous/Decimal('1000000')-1)}
    else:summary={k:None for k in ('arithmeticMean','median','geometric','positiveDayRate',
                                    'negativeDayRate','best','worst','p05','p10','cumulativeReturn')}
    return {'first':sessions[0],'last':sessions[-1], 'scheduledSessions':len(sessions),
            'fundedSessions':len({x['session'] for x in ledger['funded'].values()}),
            'certifiedEodSessions':sum(x['certified'] for x in rows),
            'nullSessions':sum(not x['certified'] for x in rows),
            'intradayWindow':'09:00 to 15:30 JST event observation, null as-of segments retained',
            'daily':rows,'statistics':summary}


def finite(data,out):
    pre,geo,audit,gate,names=contract()
    scores,manifest,feature_hash=temporal_oof(data,names,pre,gate)
    _,_,cohort,intents,evaluation,terminal,raw,_,_,labels=data
    sessions=json.loads(old.WINDOW.read_text())['portfolioSessions']
    chosen=set(sessions)
    control, cards, ledgers={}, {c:{} for c in gate['candidateIds']}, {}
    for arm in v0.ARMS:
        rows=[x for x in intents[arm] if x['timestamp'][:10] in chosen]
        e={eid:v for eid,v in evaluation[arm].items() if v['session'] in chosen}
        lab={eid:x for eid,x in labels[arm].items() if eid in e}
        frozen=replay_primary(data,arm)
        short='IM' if arm==v0.IM else 'R1'
        control_bytes=gzip.compress(v0.canonical(frozen),mtime=0)
        v0.require(hashlib.sha256(control_bytes).hexdigest()==geo['controlLedgerSha256'][short],
                   'V3_CONTROL_REPLAY_NOT_IDENTICAL')
        control[arm]=attribute(frozen,rows,e,lab,data[0]['split']['folds'])
        for candidate in gate['candidateIds']:
            predicted=replay_primary(data,arm,scores[candidate][arm])
            cards[candidate][arm]=attribute(predicted,rows,e,lab,data[0]['split']['folds'])
            ledgers[candidate,arm]=predicted
    verdict=decision(cards,control,gate)
    out.mkdir(parents=True,exist_ok=True)
    (out/'scores.json').write_bytes(v0.canonical(scores))
    for (candidate,arm),ledger in ledgers.items():
        (out/(candidate+'-'+('IM' if arm==v0.IM else 'R1')+'-MAX3-ledger.json.gz')).write_bytes(
            gzip.compress(v0.canonical(ledger),mtime=0))
    report={'schema':'phase57-capital-v3-finite-v1','pins':PINS,
            'modelFits':len(manifest),'fitManifest':manifest,'featureMatrixSha256':feature_hash,
            'scoresSha256':hashlib.sha256(v0.canonical(scores)).hexdigest(),
            'control':control,'candidates':cards,'selection':verdict,
            'primary':'MAX3_FUNDED_POST_ENTRY_UPSIDE_GE5',
            'exit':'TERMINAL_HOLD_BENCHMARK_FINAL_EXIT_NOT_SELECTED',
            'developmentOutcomeExposed':2155,'protectedOpened':0,'providerRequests':0,'safety':v0.SAFETY}
    if verdict['selected']:
        chosen_id=verdict['selected']
        report['portfolio']=old.portfolio_window(data,scores,chosen_id,out/'portfolio')
        report['certifiedEod']={}
        for arm in v0.ARMS:
            for cap in (3,4,5):
                key=('IM' if arm==v0.IM else 'R1')+'_MAX'+str(cap)
                p=out/'portfolio'/key/'ledger.json.gz'
                ledger=json.loads(gzip.decompress(p.read_bytes()))
                report['certifiedEod'][key]=certified_eod(ledger,sessions)
        report['fundedExitAnatomy']={'status':'R50_TERMINAL_ONLY_R49_INDEPENDENT_JOIN_REQUIRED',
            'fundedMax3EntryIds':{arm:sorted(ledgers[chosen_id,arm]['funded']) for arm in v0.ARMS}}
    (out/'report.json').write_bytes(v0.canonical(report))
    return report


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--r1-records',required=True)
    parser.add_argument('--benchmark-ledger',required=True)
    parser.add_argument('--mode',choices=('preflight','finite'),required=True)
    parser.add_argument('--out',required=True)
    args=parser.parse_args()
    raw=ROOT/'docs/evidence/phase57-entry-pattern-v2/ci-result/substrate/raw-paths-evaluator-only.json.gz'
    data,receipt=preflight(args.benchmark_ledger,args.r1_records,raw,args.mode=='preflight')
    if args.mode=='finite':
        out=Path(args.out)
        report=finite(data,out)
        print(json.dumps({'status':report['selection']['status'], 'modelFits':report['modelFits'],
                          'scoresSha256':report['scoresSha256'],'out':str(out)},sort_keys=True))
    else:
        path=Path(args.out)
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(v0.canonical(receipt))
        print(json.dumps({'status':'PREFLIGHT_ONLY','modelFits':0,'out':str(path)},sort_keys=True))


if __name__=='__main__':main()
