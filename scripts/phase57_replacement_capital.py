"""Precommitted Replacement Capital. Frozen R50-A, Entry and accounting adapters.

No future evaluator value enters fitting prediction or cash replay.
"""
from __future__ import annotations
import collections, copy, datetime as dt, gzip, hashlib, json, math, statistics
from decimal import Decimal
from pathlib import Path
import numpy as np
from scripts import phase57_capital_exit_integrated as integ
from scripts import phase57_capital_v3 as v3
from scripts import phase57_capital_rank_v2 as old
from scripts import phase57_development_integrated_v0 as v0
from scripts import phase57_development_integrated_v1 as v1
from scripts import phase57_cash_capital_r34 as cash
from scripts import phase57_cash_portfolio_r37 as sized
from scripts import phase57_exit_execution_contract_v1 as execution
from scripts.phase57_development_integrated_v1 import AsOfCensoredCashBook, segment, observed_mark, core_mark, mark_or_reason
ROOT=Path(__file__).resolve().parents[1]
EVIDENCE=ROOT/'docs/evidence/phase57-replacement-capital'
PROTOCOL=EVIDENCE/'PRECOMMIT.json'
PROTOCOL_SHA256='9ccf9b1a4673f0b63c38c44bdccf9f4096ec3760d461190d26b6c24e4d465d80'
AUDIT=EVIDENCE/'FEATURE_AUDIT.json'
AUDIT_SHA256='166bd79694632a25ef93bca89549414d40f57bffaabb9c0b4f2bed7da704c195'
SAFETY=v0.SAFETY

def contract():
    v0.require(v0.digest(PROTOCOL)==PROTOCOL_SHA256 and v0.digest(AUDIT)==AUDIT_SHA256,
               'REPLACEMENT_PROTOCOL_OR_AUDIT_CHANGED')
    p=json.loads(PROTOCOL.read_text())
    v0.require(p['featureAuditSha256']==AUDIT_SHA256 and p['status']==
               'FROZEN_BEFORE_NEW_REPLACEMENT_FITS_AND_FUNDED_REPLAY' and
               p['candidateIds']==['RC_MAG_FLOOR','RC_PROB3_FLOOR'] and
               p['learning']['fitCount']==16 and p['safety']==SAFETY and
               not any(SAFETY.values()),'REPLACEMENT_CONTRACT_CHANGED')
    for path,digest in p['inputSha256'].items():
        v0.require(v0.digest(ROOT/path)==digest,'REPLACEMENT_PIN_DRIFT:'+path)
    integ.contract()
    return p

def ranked_quality(group, policy, context, saved_scores, predictions):
    """Only frozen Entry fields and OOF scores; exit calendar and evaluator excluded."""
    v0.require(policy in ('RC_MAG_FLOOR','RC_PROB3_FLOOR'),'UNPRECOMMITTED_POLICY')
    replacement=context['isReplacement']
    eligible, denied=[],[]
    for row in group:
        eid=row['entryId']
        v0.require(eid in saved_scores and eid in predictions['magnitude'] and
                   eid in predictions['prob3'],'OOF_SCORE_MISSING')
        score=predictions['magnitude'][eid] if replacement and policy=='RC_MAG_FLOOR' else (
            predictions['prob3'][eid] if replacement else saved_scores[eid])
        v0.require(math.isfinite(score) and math.isfinite(predictions['prob3'][eid]),
                   'NONFINITE_OOF_SCORE')
        detail={'entryId':eid,'score':score,'predictedMagnitude':predictions['magnitude'][eid],
                'predictedProb3':predictions['prob3'][eid], 'decisionContext':
                'replacement' if replacement else 'initial'}
        if replacement and predictions['prob3'][eid] < 0.50:
            denied.append(detail)
        else:
            eligible.append((row,detail))
    eligible.sort(key=lambda pair:(-pair[1]['score'],
        -pair[1]['predictedMagnitude'] if replacement and policy=='RC_PROB3_FLOOR' else 0,
        *v0.event_priority(pair[0])))
    ranked=[]
    for index,(row,detail) in enumerate(eligible,1):
        ranked.append({**row,'newEligibleRank':index,'rankKnownAt':row['timestamp']})
        detail['selectedRank']=index
    return ranked,denied,[x for _,x in eligible]+denied

def replay(arm, capacity, cohort, intents, raw, exit_calendar, policy, saved_scores, predictions):
    """No evaluator reference in decisions, marks, allocation or ledger."""
    v0.require(arm in v0.ARMS and capacity in v0.CAPACITIES, "VARIANT_ALLOWLIST")
    portfolio = sized.SizedCashPortfolio(capacity)
    portfolio.book = AsOfCensoredCashBook(capacity)
    by_event = collections.defaultdict(list)
    for intent in intents:
        when = cash.stamp(intent["timestamp"])
        identity=intent['entryId'].split('|')
        v0.require(len(identity)==3 and identity[0]==when.date().isoformat() and
                   identity[1]==intent['symbol'] and
                   identity[2]==str(when.hour*60+when.minute),
                   'ENTRY_ID_TIME_OR_SYMBOL_DRIFT')
        by_event[(when.date().isoformat(), when.hour*60+when.minute)].append(intent)
    for group in by_event.values():
        group.sort(key=v0.event_priority)
    events, snapshots, funded, closed, unresolved, missing = [], [], {}, [], set(), []
    positions_meta, last_observed = {}, {}
    early_releases=collections.defaultdict(list)
    for session in cohort["sessions"]:
        # Potential exit timestamps are traversed only while the source position is held.
        minutes = sorted({540, 930} | {m for d, m in by_event if d == session} |
                         {x['exitMinute'] for x in exit_calendar.values()
                          if x['session'] == session and x['exitMinute'] is not None})
        for minute in minutes:
            if (minute not in (540, 930) and (session, minute) not in by_event and
                not any(exit_calendar.get(eid, {}).get('exitMinute') == minute and
                        exit_calendar[eid]['session'] == session
                        for eid in portfolio.book.positions)):
                continue
            stamp = v0.minute_stamp(session, minute)
            outgoing = []
            for eid in sorted(portfolio.book.positions):
                t = exit_calendar.get(eid)
                if t is None or t['session'] != session:
                    continue
                if (t['exitMinute'] if t['exitMinute'] is not None else 930) != minute:
                    continue
                outgoing.append({'entryId': eid, 'timestamp': stamp,
                                 'knownAt': stamp, 'price': t['exitPrice'],
                                 'confirmed': t['exitPrice'] is not None})
            departing = {x["entryId"] for x in outgoing if x["confirmed"]}
            marks, missing_reasons = {}, {}
            for eid, position in sorted(portfolio.book.positions.items()):
                if eid in departing:
                    continue
                mark, reason = mark_or_reason(raw, session, minute, eid,
                                              position, positions_meta)
                if mark is not None:
                    marks[eid] = mark
                    last_observed[eid] = mark
                else:
                    missing_reasons[eid] = reason
            # Preview confirmed exits; only the R37 batch below mutates cash.
            raw_candidates=by_event.get((session,minute),())
            earlier=early_releases[session]
            same_time=[eid for eid in departing if exit_calendar[eid]['exitKind']=='MODEL_EXIT'
                       and minute<930]
            preview=copy.deepcopy(portfolio.book)
            preview.step(stamp,exits=outgoing)
            pre_snapshot=preview.snapshot(stamp,{eid:core_mark(x) for eid,x in marks.items()})
            is_replacement=bool(earlier or same_time)
            context={'isReplacement':is_replacement,'cashAvailableJpy':str(preview.cash),
                'freeSlots':capacity-len(preview.positions),'slotOccupancy':len(preview.positions),
                'currentValidMarkedUtilization':pre_snapshot['grossExposureRatio'],
                'confirmedSameDayModelExits':len(earlier)+len(same_time),
                'fundedEntriesToday':sum(x['session']==session for x in funded.values()),
                'minutesSinceLastConfirmedEarlyRelease':(
                    minute-max([*earlier,*(minute for _ in same_time)]) if is_replacement else None),
                'entryCandidateCount':len(raw_candidates)}
            ranked,quality_rejected,order=ranked_quality(raw_candidates,policy,context,
                                                         saved_scores,predictions)
            batch = portfolio.step(
                stamp, entry_intents=ranked,
                exits=outgoing, marks={eid: core_mark(x) for eid, x in marks.items()})
            portfolio.seen_intents.update(x['entryId'] for x in quality_rejected)
            batch['sizing'].extend({'entryId':x['entryId'],'symbol':next(
                i['symbol'] for i in raw_candidates if i['entryId']==x['entryId']),
                'status':'REJECTED','reason':'QUALITY_FLOOR','rank':None,'quantity':0,
                'cashBeforeSizingJpy':str(preview.cash),'cashAfterSizingJpy':str(preview.cash)}
                for x in quality_rejected)
            for event in batch["ledger"]["events"]:
                if event["kind"] != "EXIT":
                    continue
                eid = event["entryId"]
                if event["status"] == "CLOSED":
                    meta = positions_meta[eid]
                    pnl, cost = Decimal(event["realizedPnlJpy"]), Decimal(meta["notionalJpy"])
                    closed.append({**meta, "exitTimestamp": stamp,
                                   "realizedPnlJpy": str(pnl),
                                   "netReturnPct": str(pnl / cost * 100),
                                   "sellCostJpy": str(event["sellCostJpy"]),
                                   "holdingWallMinutes": int(
                                       (cash.stamp(stamp)-cash.stamp(meta["entryTimestamp"]))
                                       .total_seconds()/60)})
                elif event["status"] == "UNRESOLVED_NO_CASH_RELEASE":
                    unresolved.add(eid)
                if (event['status']=='CLOSED' and exit_calendar[eid]['exitKind']=='MODEL_EXIT'
                        and minute<930):
                    early_releases[session].append(minute)
            for x in batch["sizing"]:
                if x["status"] != "SIZED":
                    continue
                intent = next(i for i in by_event[(session, minute)] if i["entryId"] == x["entryId"])
                meta = {"entryId": x["entryId"], "symbol": x["symbol"],
                        "session": session, "entryTimestamp": stamp,
                        "entryMinute": minute,
                        "effectiveEntryPrice": str(intent["effectiveEntryPrice"]),
                        "rank": x["rank"], "quantity": x["quantity"],
                        "notionalJpy": str(x["costJpy"]),
                        "capitalContext":'replacement' if is_replacement else 'initial'}
                positions_meta[x["entryId"]] = meta
                funded[x["entryId"]] = meta
                mark = observed_mark(raw, session, x["symbol"], minute, minute, session)
                if mark is not None:
                    marks[x["entryId"]] = mark
                    last_observed[x["entryId"]] = mark
                else:
                    missing_reasons[x["entryId"]] = "ENTRY_RAW_OPEN_NOT_OBSERVED"
            core = {eid: core_mark(x) for eid, x in marks.items()}
            snap = portfolio.book.snapshot(stamp, core)
            open_details = []
            for eid, position in sorted(portfolio.book.positions.items()):
                item = marks.get(eid)
                market = None if item is None else str(
                    cash.number(item["price"], positive=True)*position["quantity"])
                unreal = None if market is None else str(Decimal(market)-position["cost"])
                open_details.append({
                    "entryId": eid, "symbol": position["symbol"],
                    "entryTimestamp": position["entryTimestamp"],
                    "quantity": position["quantity"], "costBasisJpy": str(position["cost"]),
                    "unresolvedExit": position["unresolved"],
                    "markPrice": None if item is None else item["price"],
                    "markSource": None if item is None else item["source"],
                    "markTimestamp": None if item is None else item["timestamp"],
                    "markKnownAt": None if item is None else item["knownAt"],
                    "sourceBarMinute": None if item is None else item["sourceMinute"],
                    "staleMinutes": None if item is None else item["staleMinutes"],
                    "markedNotionalJpy": market, "unrealizedPnlJpy": unreal,
                    "missingReason": missing_reasons.get(eid)})
                if item is None:
                    missing.append({
                        "variant": arm + "_MAX" + str(capacity),
                        "timestamp": stamp, "entryId": eid, "symbol": position["symbol"],
                        "quantity": position["quantity"], "costBasisJpy": str(position["cost"]),
                        "entryTimestamp": position["entryTimestamp"],
                        "rawReferenceKey": session + "|" + position["symbol"],
                        "rawKeyAllowlisted": session + "|" + position["symbol"] in raw,
                        "requiredSegment": segment(minute),
                        "lastObservedKnownAt": (last_observed[eid]["knownAt"]
                                                if eid in last_observed else None),
                        "lastObservedSource": (last_observed[eid]["source"]
                                               if eid in last_observed else None),
                        "reason": missing_reasons[eid],
                        "unresolvedExit": position["unresolved"]})
            snapshots.append({
                "session": session, "minute": minute, "timestamp": stamp,
                "cashJpy": snap["cashJpy"], "realizedPnlJpy": snap["realizedPnlJpy"],
                "unrealizedPnlJpy": snap["unrealizedPnlJpy"],
                "equityJpy": snap["equityJpy"],
                "equityValid": snap["equityJpy"] is not None,
                "grossExposureJpy": snap["grossExposureJpy"],
                "utilization": snap["grossExposureRatio"],
                "openCount": len(portfolio.book.positions),
                "unresolvedCount": sum(p["unresolved"] for p in portfolio.book.positions.values()),
                "capacity": capacity, "positions": open_details})
            events.append({"session": session, "minute": minute, "sizing": batch["sizing"],
                           "exitEvents": [e for e in batch["ledger"]["events"] if e["kind"] == "EXIT"],
                           "cashJpy": batch["ledger"]["cashJpy"],
                           "postEventEquityJpy": snap["equityJpy"],
                           "context":context,"ranking":order})
    v0.require(all(Decimal(x["cashJpy"]) >= 0 and x["openCount"] <= capacity
                   for x in snapshots), "CASH_OR_CAPACITY_INVARIANT")
    v0.require(len(unresolved) == len(portfolio.book.positions) and
               all(x["unresolved"] for x in portfolio.book.positions.values()),
               "OPEN_NOT_CENSORED_AT_END")
    return {"arm": arm, "capacity": capacity, "events": events, "snapshots": snapshots,
            "missingReferences": missing, "funded": funded, "closed": closed,
            "unresolvedEntryIds": sorted(unresolved),
            "endOpenEntryIds": sorted(portfolio.book.positions),
            "finalCashJpy": str(portfolio.book.cash), "safety": SAFETY}


def temporal_oof(data, protocol):
    """Four expanding whole-session folds. Targets are prior-session labels only."""
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LogisticRegression, Ridge
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    _,_,_,intents,evaluation,_,_,_,_,_=data
    names=protocol['learning']['featureNames']
    v0.require(names[:-1]==old.contract()[0]['features']['sets']['C'] and
               names[-1]=='minutesToClose','FEATURE_ORDER_CHANGED')
    base=old.feature_table(data,names[:-1])
    table={arm:{x['entryId']:base[arm][x['entryId']]+[
        float(930-(cash.stamp(x['timestamp']).hour*60+cash.stamp(x['timestamp']).minute))]
        for x in intents[arm]} for arm in v0.ARMS}
    table_sha=hashlib.sha256(v0.canonical(table)).hexdigest()
    predictions={arm:{'magnitude':{},'prob3':{}} for arm in v0.ARMS}
    manifests=[]
    for arm in v0.ARMS:
        for fold in protocol['learning']['split']:
            train=[x for x in intents[arm] if x['timestamp'][:10] in fold['trainSessions']]
            test=[x for x in intents[arm] if x['timestamp'][:10] in fold['testSessions']]
            v0.require(bool(train) and bool(test) and
                max(fold['trainSessions'])<min(fold['testSessions']) and
                not set(fold['trainSessions']) & set(fold['purgeSessions']) and
                not set(fold['testSessions']) & set(fold['purgeSessions']),
                'REPLACEMENT_TEMPORAL_FOLD_OR_PURGE')
            matrix=lambda rows:np.asarray([[np.nan if n is None else n
                for n in table[arm][row['entryId']]] for row in rows],dtype=float)
            X,Z=matrix(train),matrix(test)
            raw=[evaluation[arm][x['entryId']]['postUpsidePct'] for x in train]
            v0.require(all(y is not None and math.isfinite(float(y)) for y in raw),
                       'UNOBSERVED_TRAIN_SUFFIX')
            for target in ('magnitude','prob3'):
                if target=='magnitude':
                    y=np.asarray([min(20.0,max(-10.0,float(z))) for z in raw])
                    model=Ridge(**protocol['learning']['models'][target]['parameters'])
                else:
                    y=np.asarray([float(z)>=3.0 for z in raw],dtype=int)
                    v0.require(0<int(y.sum())<len(y),'ONE_CLASS_TRAIN')
                    model=LogisticRegression(**protocol['learning']['models'][target]['parameters'])
                pipeline=make_pipeline(SimpleImputer(**protocol['learning']['imputer']),
                    StandardScaler(),model)
                pipeline.fit(X,y)
                score=(pipeline.predict(Z) if target=='magnitude' else
                       pipeline.predict_proba(Z)[:,1])
                v0.require(len(score)==len(test) and np.isfinite(score).all(),
                           'REPLACEMENT_PREDICTION_INVALID')
                for x,z in zip(test,score):
                    eid=x['entryId'];v0.require(eid not in predictions[arm][target],
                        'REPLACEMENT_DUPLICATE_OOF')
                    predictions[arm][target][eid]=float(z)
                manifests.append({'arm':arm,'target':target,'fold':fold['id'],
                    'trainRows':len(train),'scoreRows':len(test),
                    'trainMax':max(fold['trainSessions']),'scoreMin':min(fold['testSessions']),
                    'testPredictionSha256':hashlib.sha256(v0.canonical([
                        (x['entryId'],predictions[arm][target][x['entryId']]) for x in test])).hexdigest()})
    v0.require(len(manifests)==16,'REPLACEMENT_FIT_COUNT_CHANGED')
    for arm in v0.ARMS:
        expected={x['entryId'] for x in intents[arm] if x['timestamp'][:10] in protocol['sessions']}
        v0.require(all(set(predictions[arm][target])==expected
                       for target in ('magnitude','prob3')),'OOF_COVERAGE_CHANGED')
    return predictions,manifests,table_sha


def run_replays(protocol,data,saved_scores,exit_calendar,predictions):
    """No evaluator argument: outcome labels cannot alter purchases."""
    _,_,cohort,intents,_,_,raw,_,_,_=data
    selected=set(protocol['sessions'])
    subset={**cohort,'sessions':protocol['sessions']}
    result={}
    for arm in v0.ARMS:
        rows=[x for x in intents[arm] if x['timestamp'][:10] in selected]
        for candidate in protocol['candidateIds']:
            result[(arm,candidate)]=replay(arm,3,subset,rows,raw,
                exit_calendar[arm],candidate,saved_scores[arm],predictions[arm])
    return result


def group_quality(ledger,evaluation,kind):
    entries={eid:x for eid,x in ledger['funded'].items()
             if kind=='combined' or x['capitalContext']==kind}
    sample={**ledger,'funded':entries}
    buckets=integ.distribution(sample,evaluation)
    closed={x['entryId']:x for x in ledger['closed']}
    known=[float(evaluation[eid]['postUpsidePct']) for eid in entries
           if evaluation[eid]['postUpsidePct'] is not None]
    pnls=[float(closed[eid]['realizedPnlJpy']) for eid in entries if eid in closed]
    nets=[float(closed[eid]['netReturnPct']) for eid in entries if eid in closed]
    notional=sum((Decimal(x['notionalJpy']) for x in entries.values()),Decimal(0))
    total_cap=sum((Decimal(x['notionalJpy']) for x in ledger['funded'].values()),Decimal(0))
    ge=lambda bound:sum(z>=bound for z in known)
    share=lambda test:sum(test(z) for z in known)/len(known) if known else None
    return {'N':len(entries),'knownN':len(known),'meanUpsidePct':statistics.fmean(known) if known else None,
        'medianUpsidePct':statistics.median(known) if known else None,
        'lt1Share':share(lambda z:z<1),'ge3Share':share(lambda z:z>=3),
        'ge4Share':share(lambda z:z>=4),'ge5Count':ge(5),
        'ge5Share':share(lambda z:z>=5),'ge7_5Count':ge(7.5),
        'ge7_5Share':share(lambda z:z>=7.5),'ge10Count':ge(10),
        'ge10Share':share(lambda z:z>=10),
        'netMeanPct':statistics.fmean(nets) if nets else None,
        'netMedianPct':statistics.median(nets) if nets else None,
        'holdingMeanWallMinutes':statistics.fmean(closed[eid]['holdingWallMinutes']
            for eid in entries if eid in closed) if nets else None,
        'realizedPnlJpy':str(sum((Decimal(closed[eid]['realizedPnlJpy'])
            for eid in entries if eid in closed),Decimal(0))),
        'allocatedCapitalJpy':str(notional),'allocatedCapitalShare':float(notional/total_cap) if total_cap else None,
        'winRate':sum(z>0 for z in pnls)/len(pnls) if pnls else None,'buckets':buckets}


def miss_reason(item,event,by_intent):
    """Exclusive causal precedence; evaluation chooses which rows to inspect."""
    if event is None or item is None:return 'ENTRY_NOT_ELIGIBLE'
    if item['status']=='SIZED':return None
    reason=item['reason'];context=event['context']
    if any(x['status']=='UNRESOLVED_NO_CASH_RELEASE' for x in event['exitEvents']):
        return 'UNRESOLVED_CASH_LOCK'
    if reason=='QUALITY_FLOOR':return 'QUALITY_FLOOR'
    if reason=='MAX_CONCURRENT_SYMBOLS':
        return 'CAPACITY_FULL' if context['slotOccupancy']>=3 else 'RANK_LOSS'
    if reason=='NO_100_SHARE_LOT_WITHIN_TARGET_AND_CASH':
        price=Decimal(str(by_intent[item['entryId']]['effectiveEntryPrice']))
        cash_before=Decimal(str(item['cashBeforeSizingJpy']))
        if cash_before<100*price:return 'INSUFFICIENT_CASH'
        if any(x['status']=='SIZED' for x in event['sizing']):return 'RANK_LOSS'
        return 'LOT_INFEASIBLE'
    return 'OTHER_CAUSAL'


def capacity_and_idle(ledger,sessions):
    """Integrate only actual continuous minutes; invalid marks stay null."""
    byday=collections.defaultdict(list)
    for row in ledger['snapshots']:byday[row['session']].append(row)
    events={(x['session'],x['minute']):x for x in ledger['events']}
    counts=collections.Counter(); cash_time=Decimal(0);equity_time=Decimal(0)
    idle_durations=collections.Counter();valid=0; ge80=0;util=0.0
    for day in sessions:
        rows=sorted(byday[day],key=lambda x:x['minute'])
        for row,nxt in zip(rows,rows[1:]):
            span=sum(row['minute']<=m<nxt['minute'] for m in execution.continuous_minutes(day))
            counts['scheduledMinutes']+=span
            if row['utilization'] is None:
                counts['invalidUtilizationMinutes']+=span;continue
            valid+=span;rate=float(row['utilization']);util+=rate*span
            ge80+=(rate>=.80)*span
            cash_amount=Decimal(row['cashJpy']);equity=Decimal(row['equityJpy'])
            cash_time+=cash_amount*span;equity_time+=equity*span
            if cash_amount>0:
                counts['idleCashMinutes']+=span
                event=events[(day,row['minute'])]
                unsized=[x for x in event['sizing'] if x['status']=='REJECTED']
                if any(x['reason'] not in ('QUALITY_FLOOR',) for x in unsized):
                    idle_durations['HIGH_QUALITY_ELIGIBLE_UNFUNDED']+=span
                elif any(x['reason']=='QUALITY_FLOOR' for x in unsized):
                    idle_durations['ENTRY_BELOW_QUALITY_FLOOR']+=span
                else:idle_durations['NO_FROZEN_ENTRY_AT_TIMESTAMP']+=span
    return {'scheduledMinutes':counts['scheduledMinutes'],'validUtilizationMinutes':valid,
        'invalidUtilizationMinutes':counts['invalidUtilizationMinutes'],
        'timeWeightedUtilization':util/valid if valid else None,
        'ge80TimeShare':ge80/valid if valid else None,
        'idleCashMinutes':counts['idleCashMinutes'],
        'meanIdleCashJpy':str(cash_time/valid) if valid else None,
        'idleCashShareOfEquityTime':float(cash_time/equity_time) if equity_time else None,
        'idleClassificationMinutes':dict(sorted(idle_durations.items()))}


def evaluate(protocol,data,replays,archived_control):
    """Evaluator-only future High and PnL accessed after all funding decisions."""
    _,_,_,intents,evaluation,_,_,_,_,_=data
    result={'schema':'phase57-replacement-capital-finite-result-v1',
        'status':'EXPERIMENTAL_OUTCOME_EXPOSED_DEVELOPMENT','protocolSha256':PROTOCOL_SHA256,
        'finalExitSelected':False,'providerRequests':0,'protectedPartitionsOpened':0,
        'safety':SAFETY,'arms':{}}
    for arm in v0.ARMS:
        name='IM' if arm==v0.IM else 'R1';result['arms'][name]={}
        scoped={eid:x for eid,x in evaluation[arm].items() if x['session'] in protocol['sessions']}
        by_id={x['entryId']:x for x in intents[arm]
               if x['timestamp'][:10] in protocol['sessions']}
        for cid in protocol['candidateIds']:
            led=replays[(arm,cid)]
            day_rows,day_summary=integ.daily(led,protocol['sessions'])
            turn=integ.turnover(led,protocol['sessions'])
            quality={kind:group_quality(led,scoped,kind) for kind in
                     ('initial','replacement','combined')}
            item_by_id={x['entryId']:(x,event) for event in led['events'] for x in event['sizing']}
            misses=[]
            positives=[eid for eid,x in scoped.items()
                       if x['postUpsidePct'] is not None and x['postUpsidePct']>=5]
            for eid in sorted(set(positives)-set(led['funded'])):
                item,event=item_by_id.get(eid,(None,None))
                misses.append({'entryId':eid,'reason':miss_reason(item,event,by_id),
                               'postUpsidePct':scoped[eid]['postUpsidePct']})
            v0.require(len(misses)+quality['combined']['ge5Count']==len(positives),
                       'HIGH_UPSIDE_MISS_RECONCILIATION')
            eod=[Decimal(x['equityJpy']) for x in day_rows if x['equityJpy'] is not None]
            peak=Decimal(1000000);worst=Decimal(0)
            for x in eod:
                peak=max(peak,x);worst=min(worst,(x/peak-1)*100)
            portfolio=integ.portfolio_card(led,day_summary)
            portfolio['EODMaxDDPct']=float(worst) if len(eod)==len(protocol['sessions']) else None
            original=archived_control[arm]
            new_ids=sorted(set(led['funded'])-set(original['funded']))
            closed={x['entryId']:x for x in led['closed']}
            added=[{'entryId':eid,'capitalContext':led['funded'][eid]['capitalContext'],
                    'upsidePct':scoped[eid]['postUpsidePct'],
                    'realizedPnlJpy':closed[eid]['realizedPnlJpy'] if eid in closed else None}
                   for eid in new_ids]
            symbol=collections.Counter(x['symbol'] for x in led['funded'].values())
            session=collections.Counter(x['session'] for x in led['funded'].values())
            realized=[float(x['netReturnPct']) for x in led['closed']]
            result['arms'][name][cid]={
                'cohorts':quality,'turnover':turn,'utilization':capacity_and_idle(led,protocol['sessions']),
                'portfolio':portfolio,'daily':day_rows,'dailySummary':day_summary,
                'availableGe5':len(positives),'fundedGe5':quality['combined']['ge5Count'],
                'highUpsideReach':quality['combined']['ge5Count']/len(positives) if positives else None,
                'availableGe7_5':sum(x['postUpsidePct'] is not None and x['postUpsidePct']>=7.5 for x in scoped.values()),
                'availableGe10':sum(x['postUpsidePct'] is not None and x['postUpsidePct']>=10 for x in scoped.values()),
                'missReasons':dict(collections.Counter(x['reason'] for x in misses)),
                'missRows':misses,'recyclingAdded':added,
                'concentration':{'symbolTopShare':max(symbol.values())/len(led['funded']) if symbol else None,
                                 'sessionTopShare':max(session.values())/len(led['funded']) if session else None},
                'waterfall':{'fundedPotentialMeanPct':quality['combined']['meanUpsidePct'],
                   'realizedExitMeanNetPct':statistics.fmean(realized) if realized else None,
                   'potentialMinusRealizedMeanPp':quality['combined']['meanUpsidePct']-
                        statistics.fmean(realized) if realized and quality['combined']['meanUpsidePct'] is not None else None,
                   'replacementRealizedContributionJpy':quality['replacement']['realizedPnlJpy'],
                   'loserDragJpy':str(sum((Decimal(x['realizedPnlJpy']) for x in led['closed']
                                        if Decimal(x['realizedPnlJpy'])<0),Decimal(0))),
                   'sellCostsJpy':str(sum((Decimal(x['sellCostJpy']) for x in led['closed']),Decimal(0))),
                   'buySideCosts':'embedded in frozen effective Entry price; no separate double charge',
                   'capitalTurnoverInitialEquityTimes':turn['cashTurnoverInitialEquityTimes'],
                   'timeWeightedUtilization':capacity_and_idle(led,protocol['sessions'])['timeWeightedUtilization'],
                   'portfolioReturnPct':portfolio['portfolioReturnPct']}}
    return result


def archived_ledger(arm):
    import zipfile
    name=('IM' if arm==v0.IM else 'R1')+'_V3_B_R50_A_ledger.json.gz'
    source=ROOT/'docs/evidence/phase57-capital-exit-integrated/RESULT/phase57-integrated-result.zip'
    with zipfile.ZipFile(source) as z:
        ledger=json.loads(gzip.decompress(z.read(name)))
    # Context attribution is post-replay; never enters the saved control's decisions.
    exit_by_day=collections.defaultdict(list)
    for event in ledger['events']:
        for row in event['exitEvents']:
            if row['status']=='CLOSED' and event['minute']<930:
                exit_by_day[event['session']].append(event['minute'])
    for row in ledger['funded'].values():
        row['capitalContext']=('replacement' if any(m<=row['entryMinute']
            for m in exit_by_day[row['session']]) else 'initial')
    return ledger


def selection(protocol,report,control,data,replays):
    """Evaluate exactly the gates frozen before any replacement fits."""
    evaluation=data[4];scope={eid:x for eid,x in evaluation[v0.IM].items()
                              if x['session'] in protocol['sessions']}
    prior=control[v0.IM]
    baseline={kind:group_quality(prior,scope,kind) for kind in
              ('initial','replacement','combined')}
    baseline_util=capacity_and_idle(prior,protocol['sessions'])
    baseline_daily,baseline_daily_summary=integ.daily(prior,protocol['sessions'])
    baseline_portfolio=integ.portfolio_card(prior,baseline_daily_summary)
    baseline_symbol=collections.Counter(x['symbol'] for x in prior['funded'].values())
    baseline_session=collections.Counter(x['session'] for x in prior['funded'].values())
    base_symbol=max(baseline_symbol.values())/len(prior['funded'])
    base_session=max(baseline_session.values())/len(prior['funded'])
    eod=[Decimal(x['equityJpy']) for x in baseline_daily]
    peak=Decimal(1000000);worst=Decimal(0)
    for row in eod:
        peak=max(peak,row);worst=min(worst,(row/peak-1)*100)
    g=protocol['gate'];votes={}
    for cid in protocol['candidateIds']:
        x=report['arms']['IM'][cid]
        i,r,c=(x['cohorts'][k] for k in ('initial','replacement','combined'))
        a=x['utilization'];p=x['portfolio'];conc=x['concentration']
        added=x['recyclingAdded']
        extra_known=[z for z in added if z['upsidePct'] is not None]
        extra_rate=sum(z['upsidePct']>=5 for z in extra_known)/len(extra_known) if extra_known else None
        checks={
         'replacement_count':r['N']>=g['replacementMinN'],
         'replacement_ge5':r['ge5Count']>=g['replacementGe5MinCount'] and
             r['ge5Share'] is not None and r['ge5Share']>=g['replacementGe5RateMin'],
         'replacement_median_vs_initial':r['medianUpsidePct'] is not None and
             i['medianUpsidePct'] is not None and
             r['medianUpsidePct']-i['medianUpsidePct']>=g['replacementMedianVsInitialMinPp'],
         'replacement_lt1_vs_initial':r['lt1Share'] is not None and i['lt1Share'] is not None and
             r['lt1Share']-i['lt1Share']<=g['replacementLt1ShareVsInitialMax'],
         'combined_ge5':c['ge5Share'] is not None and c['ge5Share']-
             baseline['combined']['ge5Share']>=g['combinedGe5RateVsPriorMin'],
         'combined_ge10':c['ge10Share'] is not None and c['ge10Share']-
             baseline['combined']['ge10Share']>=g['combinedGe10RateVsPriorMin'],
         'combined_lt1':c['lt1Share'] is not None and c['lt1Share']-
             baseline['combined']['lt1Share']<=g['combinedLt1ShareVsPriorMax'],
         'high_upside_reach':c['ge5Count']-baseline['combined']['ge5Count']>=
             g['highUpsideReachVsPriorMinCount'],
         'utilization':a['timeWeightedUtilization'] is not None and
             a['timeWeightedUtilization']-baseline_util['timeWeightedUtilization']>=
             g['utilizationTimeWeightedVsPriorMin'],
         'ge80_share':a['ge80TimeShare'] is not None and
             a['ge80TimeShare']-baseline_util['ge80TimeShare']>=g['ge80TimeShareVsPriorMin'],
         'concentration':conc['symbolTopShare']<=base_symbol+g['symbolTopShareVsPriorMax'] and
             conc['sessionTopShare']<=base_session+g['sessionTopShareVsPriorMax'],
         'portfolio':p['finalEquityJpy'] is not None and
             Decimal(p['finalEquityJpy'])-Decimal(baseline_portfolio['finalEquityJpy'])>=
             g['finalEquityVsPriorMinJpy'] and p['EODMaxDDPct'] is not None and
             p['EODMaxDDPct']-float(worst)>=g['EODMaxDDVsPriorMinPp'],
         'extra_trades_quality':extra_rate is not None and
             extra_rate-baseline['combined']['ge5Share']>=g['extraTradeGe5RateVsPriorCombinedMin'],
         'reproducibility':'PENDING_INDEPENDENT_SAME_SHA_REPLAY'}
        votes[cid]={'checks':checks,'passBeforeIndependentAudit':all(
            v is True for k,v in checks.items() if k!='reproducibility'),
            'addedGe5Rate':extra_rate}
    return {'baseline':{'cohorts':baseline,'utilization':baseline_util,
             'portfolio':baseline_portfolio,'daily':baseline_daily_summary},
            'votes':votes,'status':'PENDING_INDEPENDENT_SAME_SHA_REPRODUCIBILITY'}


def save_artifacts(out,protocol,data,predictions,manifests,table_sha,replays,report,verdict):
    import csv, zipfile, subprocess
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    v0.require(not out.exists(),'REPLACEMENT_OUTPUT_EXISTS')
    out.mkdir(parents=True)
    (out/'predictions.json').write_bytes(v0.canonical(predictions))
    (out/'fold-manifests.json').write_bytes(v0.canonical(manifests))
    (out/'scorecard.json').write_bytes(v0.canonical(report))
    (out/'selection.json').write_bytes(v0.canonical(verdict))
    for (arm,cid),led in replays.items():
        label=('IM' if arm==v0.IM else 'R1')+'_'+cid
        (out/(label+'_ledger.json.gz')).write_bytes(gzip.compress(v0.canonical(led),mtime=0))
        curve=v1.curve(led)
        (out/(label+'_curve.json')).write_bytes(v0.canonical(curve))
        with (out/(label+'_curve.csv')).open('w',newline='') as stream:
            fields=['timestamp','equityJpy','cashJpy','grossExposureJpy','utilization','drawdownPct','equityValid']
            writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader();writer.writerows(curve)
        card=report['arms']['IM' if arm==v0.IM else 'R1'][cid]
        with (out/(label+'_buckets.csv')).open('w',newline='') as stream:
            writer=csv.DictWriter(stream,fieldnames=['context','bucket','count','share','meanUpsidePct',
                 'medianUpsidePct','realizedNetMeanPct','realizedNetMedianPct','netEvaluableCount',
                 'capitalAllocatedJpy','capitalShare']);writer.writeheader()
            for context,quality in card['cohorts'].items():
                for row in quality['buckets']:writer.writerow({'context':context,**row})
        (out/(label+'_misses.json')).write_bytes(v0.canonical(card['missRows']))
        (out/(label+'_utilization.json')).write_bytes(v0.canonical(card['utilization']))
        with (out/(label+'_daily.csv')).open('w',newline='') as stream:
            writer=csv.DictWriter(stream,fieldnames=['session','cashJpy','equityJpy','certified','dailyReturn']);writer.writeheader();writer.writerows(card['daily'])
        fig,ax=plt.subplots(figsize=(10,3.5))
        for name,series in [('previous V3-B R50-A',archived_ledger(arm)),
                            (cid,led)]:
            source=v1.curve(series)
            ax.plot([dt.datetime.fromisoformat(q['timestamp']) for q in source],
                    [float(q['equityJpy']) if q['equityJpy'] is not None else math.nan for q in source],
                    label=name,linewidth=1.2)
        ax.set_title(label+' experimental Development as-of equity')
        ax.set_ylabel('JPY; null gaps shown');ax.grid(alpha=.25);ax.legend(fontsize=8)
        fig.autofmt_xdate();fig.tight_layout();fig.savefig(out/(label+'.png'),dpi=130);plt.close(fig)
    sha=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    manifest={'schema':'phase57-replacement-capital-manifest-v1',
       'protocolSha256':PROTOCOL_SHA256,'featureAuditSha256':AUDIT_SHA256,
       'executionSha':sha,'featureMatrixSha256':table_sha,
       'predictionSha256':v0.digest(out/'predictions.json'),
       'filesSha256':{x.name:v0.digest(x) for x in sorted(out.iterdir()) if x.is_file()},
       'versions':{'python':__import__('sys').version,'numpy':np.__version__,
                   'sklearn':__import__('sklearn').__version__},
       'providerRequests':0,'protectedPartitionsOpened':0,'safety':SAFETY}
    (out/'manifest.json').write_bytes(v0.canonical(manifest))


def main():
    import argparse
    ap=argparse.ArgumentParser();ap.add_argument('--mode',choices=['preflight','finite'],required=True)
    ap.add_argument('--out',type=Path,required=True);args=ap.parse_args()
    p=contract();_,data,score,model=integ.load_inputs()
    if args.mode=='preflight':
        receipt={'schema':'phase57-replacement-prefit-receipt-v1',
            'protocolSha256':PROTOCOL_SHA256,'featureAuditSha256':AUDIT_SHA256,
            'scoredSessions':len(p['sessions']),'candidateIds':p['candidateIds'],
            'savedControlScores':{arm:len(score[arm]) for arm in v0.ARMS},
            'savedExitDecisions':{arm:len(model[arm]) for arm in v0.ARMS},
            'fits':0,'newFundedPerformanceRead':False,'safety':SAFETY}
        args.out.write_bytes(v0.canonical(receipt));print(json.dumps(receipt));return
    pred,folds,feature_sha=temporal_oof(data,p)
    ledgers=run_replays(p,data,score,model,pred)
    archived={arm:archived_ledger(arm) for arm in v0.ARMS}
    report=evaluate(p,data,ledgers,archived)
    verdict=selection(p,report,archived,data,ledgers)
    save_artifacts(args.out,p,data,pred,folds,feature_sha,ledgers,report,verdict)
    print(json.dumps({'protocolSha256':PROTOCOL_SHA256,'out':str(args.out),
                      'candidateIds':p['candidateIds'],'fits':len(folds),
                      'preAuditVotes':verdict['votes']},sort_keys=True))

if __name__=='__main__':main()
