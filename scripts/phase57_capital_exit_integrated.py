"""Experimental Development-only frozen Capital × R50-A chronological cash replay.

The cash/valuation loop is a source-preserving copy of v1.replay with a single
conditional change: held confirmed R50-A model EXITs join the timestamp queue.
No new rank, EXIT decision, fill, mark or eligibility rule is introduced.
"""
from __future__ import annotations
import argparse, collections, csv, datetime as dt, gzip, hashlib, json, math, re, statistics
from decimal import Decimal
from pathlib import Path
from scripts import phase57_capital_v3 as v3
from scripts import phase57_capital_rank_v2 as old
from scripts import phase57_development_integrated_v0 as v0
from scripts import phase57_development_integrated_v1 as v1
from scripts import phase57_cash_capital_r34 as cash
from scripts import phase57_cash_portfolio_r37 as sized
from scripts import phase57_exit_execution_contract_v1 as execution
from scripts import phase57_exit_winner_lifecycle_r50 as r50
from scripts.phase57_development_integrated_v1 import (AsOfCensoredCashBook, segment, observed_mark, core_mark, mark_or_reason)
ROOT=Path(__file__).resolve().parents[1]
EVIDENCE=ROOT/'docs/evidence/phase57-capital-exit-integrated'
PRECOMMIT=EVIDENCE/'INTEGRATION_PRECOMMIT.json'
PRECOMMIT_SHA256='93d9ddb8e45a473947430fb67f013e56f28d079614625f534ef769c3434990f9'
SAFETY=v0.SAFETY

def contract():
    v0.require(v0.digest(PRECOMMIT)==PRECOMMIT_SHA256,'INTEGRATION_PRECOMMIT_HASH')
    p=json.loads(PRECOMMIT.read_text())
    v0.require(p['status']=='FROZEN_BEFORE_INTEGRATED_REPLAY_PERFORMANCE' and
               p['initialCashJpy']==1000000 and p['lotShares']==100 and p['capacity']==3 and
               len(p['sessions'])==24 and p['safety']==SAFETY and not any(SAFETY.values()),
               'INTEGRATION_CONTRACT')
    for path, expected in p['sources'].items():
        v0.require(v0.digest(ROOT/path)==expected,'INTEGRATION_INPUT_HASH:'+path)
    v0.require(r50.PROTOCOL_SHA256==p['upstreamExit']['protocolSha256'] and
               r50.protocol()['candidates'][0]['candidateId']=='R50_A_LIFECYCLE',
               'R50_A_FROZEN_IDENTITY')
    return p

def replay(arm, capacity, cohort, intents, raw, exit_calendar):
    """No evaluator reference in decisions, marks, allocation or ledger."""
    v0.require(arm in v0.ARMS and capacity in v0.CAPACITIES, "VARIANT_ALLOWLIST")
    portfolio = sized.SizedCashPortfolio(capacity)
    portfolio.book = AsOfCensoredCashBook(capacity)
    by_event = collections.defaultdict(list)
    for intent in intents:
        when = cash.stamp(intent["timestamp"])
        by_event[(when.date().isoformat(), when.hour*60+when.minute)].append(intent)
    for group in by_event.values():
        group.sort(key=v0.event_priority)
    events, snapshots, funded, closed, unresolved, missing = [], [], {}, [], set(), []
    positions_meta, last_observed = {}, {}
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
            batch = portfolio.step(
                stamp, entry_intents=by_event.get((session, minute), ()),
                exits=outgoing, marks={eid: core_mark(x) for eid, x in marks.items()})
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
            for x in batch["sizing"]:
                if x["status"] != "SIZED":
                    continue
                intent = next(i for i in by_event[(session, minute)] if i["entryId"] == x["entryId"])
                meta = {"entryId": x["entryId"], "symbol": x["symbol"],
                        "session": session, "entryTimestamp": stamp,
                        "entryMinute": minute,
                        "effectiveEntryPrice": str(intent["effectiveEntryPrice"]),
                        "rank": x["rank"], "quantity": x["quantity"],
                        "notionalJpy": str(x["costJpy"])}
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
                           "postEventEquityJpy": snap["equityJpy"]})
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


def load_inputs():
    """Project pinned inputs; future evaluations never enter the replay interface."""
    p=contract()
    source=p['sources']
    terminal_path=ROOT/'docs/evidence/phase57-capital-v3/INPUTS/R50-terminal-ledger.jsonl.gz'
    r1_path=ROOT/'docs/evidence/phase57-capital-v3/INPUTS/R1-entry-records.json.gz'
    raw_path=ROOT/'docs/evidence/phase57-entry-pattern-v2/ci-result/substrate/raw-paths-evaluator-only.json.gz'
    data=old.load_inputs(terminal_path,r1_path,raw_path)
    _,_,cohort,intents,evaluation,terminal,raw,_,_,labels=data
    chosen=set(p['sessions'])
    v0.require(set(p['sessions'])<=set(cohort['sessions']) and
               sorted({x['session'] for a in v0.ARMS for x in evaluation[a].values()
                       if x['session'] in chosen})==p['sessions'],
               'INTEGRATED_24_SESSION_IDENTITY')
    score_path=ROOT/'docs/evidence/phase57-capital-v3/RESULT/scores.json'
    score=json.loads(score_path.read_text())
    v0.require(set(score)=={'CAPITAL_V3_A','CAPITAL_V3_B'},'PINNED_V3_SCORE_CANDIDATES')
    score=score['CAPITAL_V3_B']
    v0.require(set(score)==set(v0.ARMS) and all(
        set(score[a])=={x['entryId'] for x in intents[a]
                        if x['timestamp'][:10] in chosen} and
        all(type(z) is float and math.isfinite(z) for z in score[a].values())
        for a in v0.ARMS),'CI_OOF_SCORE_COVERAGE')

    # The R50 archive covers 34 source sessions. Decode only exact frozen
    # 24-session Entry IDs; skip other JSONL payloads before json.loads.
    target={a:{eid for eid,x in evaluation[a].items() if x['session'] in chosen}
            for a in v0.ARMS}
    model={a:{} for a in v0.ARMS}
    path=EVIDENCE/'INPUTS/R50_A_LIFECYCLE-run-a.jsonl.gz'
    arm_re=re.compile(r'"entryArm":"([^"]+)"')
    id_re=re.compile(r'"entryId":"([^"]+)"')
    with gzip.open(path,'rt') as stream:
        for line in stream:
            ma=arm_re.search(line); mi=id_re.search(line)
            v0.require(ma is not None and mi is not None,'R50_A_JSONL_IDENTITY')
            arm,eid=ma.group(1),mi.group(1)
            if arm not in target or eid not in target[arm]:
                continue
            row=json.loads(line)
            v0.require(row['candidateId']=='R50_A_LIFECYCLE' and
                       row['entryArm']==arm and row['entryId']==eid and
                       eid not in model[arm],'R50_A_DUPLICATE_OR_CHANGED_IDENTITY')
            ref=evaluation[arm][eid]
            original=next(x for x in intents[arm] if x['entryId']==eid)
            v0.require(row['session']==ref['session'] and
                       row['opportunity']==ref['opportunity'] and
                       row['entryMinute']==ref['entryMinute'] and
                       math.isclose(float(row['entryPrice']),float(original['effectiveEntryPrice']),
                                    abs_tol=1e-7,rel_tol=0),'R50_A_ENTRY_DIFFERENCE')
            exit_minute,price=row['exitMinute'],row['exitPrice']
            facts=row['decisionFacts'];decision=row['decisionNow']
            v0.require(facts['now']==decision and facts['maxKnownAt']<=decision and
                       facts['maxBarEnd']<=decision and
                       set(facts['values'])==set(r50.FACTS),'R50_A_FUTURE_FACT')
            observed=raw[row['opportunity']]
            control=terminal[arm][eid]
            if row['exitKind']=='MODEL_EXIT':
                v0.require(row['authority']=='WINNER_HARVEST' and
                           isinstance(exit_minute,int) and exit_minute>=decision and
                           exit_minute==execution.next_execution_start(row['session'],decision) and
                           exit_minute in observed and price is not None and
                           float(price)==float(observed[exit_minute][1]),
                           'R50_A_MODEL_FILL_NOT_EXACT_NEXT_OPEN')
            else:
                v0.require(row['exitKind']=='FORCED_TERMINAL' and
                           row['authority']=='FORCE_TERMINAL' and decision==925 and
                           exit_minute==control['exitMinute'] and
                           price==control['exitPrice'],'R50_A_TERMINAL_IDENTITY')
            model[arm][eid]={'session':row['session'],'exitMinute':exit_minute,
                              'exitPrice':price,'exitKind':row['exitKind']}
    v0.require(all(set(model[a])==target[a] for a in v0.ARMS),'R50_A_SCOPE_INCOMPLETE')
    return p,data,score,model


def run_replays(data,score,model):
    """Exactly three frozen arms, with no evaluator object or future label input."""
    _,_,cohort,intents,_,terminal,raw,_,_,_=data
    chosen=set(json.loads(PRECOMMIT.read_text())['sessions'])
    subset={**cohort,'sessions':sorted(chosen)}
    out={}
    for arm in v0.ARMS:
        eligible=[x for x in intents[arm] if x['timestamp'][:10] in chosen]
        exits={eid:x for eid,x in terminal[arm].items() if x['session'] in chosen}
        base=v3.ranked_intents(eligible,score[arm])
        out[(arm,'V3_B_TERMINAL')]=replay(arm,3,subset,base,raw,exits)
        out[(arm,'V3_B_R50_A')]=replay(arm,3,subset,base,raw,model[arm])
        out[(arm,'CAUSAL_RANK_R50_A')]=replay(arm,3,subset,eligible,raw,model[arm])
    return out


BUCKETS=('<0%','0–1%','1–2%','2–3%','3–4%','4–5%',
         '5–7.5%','7.5–10%','>=10%','UNKNOWN/CENSORED')


def upside_bucket(value):
    if value is None or not math.isfinite(float(value)):
        return BUCKETS[-1]
    value=float(value)
    if value<0: return BUCKETS[0]
    for bound,name in zip((1,2,3,4,5,7.5,10),BUCKETS[1:8]):
        if value<bound:return name
    return BUCKETS[8]


def distribution(ledger,evaluation):
    closed={x['entryId']:x for x in ledger['closed']}
    grouped=collections.defaultdict(list)
    for eid,entry in ledger['funded'].items():
        grouped[upside_bucket(evaluation[eid]['postUpsidePct'])].append((eid,entry))
    total=len(ledger['funded'])
    total_cap=sum((Decimal(x['notionalJpy']) for x in ledger['funded'].values()),Decimal(0))
    out=[]
    for name in BUCKETS:
        rows=grouped[name]
        upside=[float(evaluation[eid]['postUpsidePct']) for eid,_ in rows
                if evaluation[eid]['postUpsidePct'] is not None]
        nets=[float(closed[eid]['netReturnPct']) for eid,_ in rows if eid in closed]
        cap=sum((Decimal(x['notionalJpy']) for _,x in rows),Decimal(0))
        out.append({'bucket':name,'count':len(rows),'share':len(rows)/total if total else None,
                    'meanUpsidePct':statistics.fmean(upside) if upside else None,
                    'medianUpsidePct':statistics.median(upside) if upside else None,
                    'realizedNetMeanPct':statistics.fmean(nets) if nets else None,
                    'realizedNetMedianPct':statistics.median(nets) if nets else None,
                    'netEvaluableCount':len(nets),'capitalAllocatedJpy':str(cap),
                    'capitalShare':float(cap/total_cap) if total_cap else None})
    assert sum(x['count'] for x in out)==total
    return out


def daily(ledger,sessions):
    eod={s['session']:s for s in ledger['snapshots'] if s['minute']==930}
    rows=[];previous=Decimal('1000000');prev_valid=True
    for day in sessions:
        s=eod.get(day)
        valid=(s is not None and s['equityValid'] and
               s['openCount']==s['unresolvedCount']==0 and
               Decimal(s['cashJpy'])==Decimal(s['equityJpy']))
        equity=Decimal(s['equityJpy']) if valid else None
        rate=float(equity/previous-1) if valid and prev_valid else None
        rows.append({'session':day,'cashJpy':s['cashJpy'] if s else None,
                     'equityJpy':str(equity) if valid else None,'certified':bool(valid),
                     'dailyReturn':rate})
        previous=equity if valid else None
        prev_valid=bool(valid)
    values=[x['dailyReturn'] for x in rows]
    full=all(x is not None for x in values)
    summary={'first':sessions[0],'last':sessions[-1],
             'calendarSpanDays':(dt.date.fromisoformat(sessions[-1])-dt.date.fromisoformat(sessions[0])).days+1,
             'tradingSessions':len(sessions),'validSessions':sum(x['certified'] for x in rows),
             'nullSessions':sum(not x['certified'] for x in rows),
             'validContiguousReturnDays':sum(x is not None for x in values),
             'arithmeticMean':statistics.fmean(values) if full else None,
             'median':statistics.median(values) if full else None,
             'geometric':float((previous/Decimal('1000000'))**(Decimal(1)/Decimal(len(rows)))-1) if full else None,
             'positiveDayRate':sum(x>0 for x in values)/len(rows) if full else None,
             'best':max(values) if full else None,'worst':min(values) if full else None,
             'cumulativeReturn':float(previous/Decimal('1000000')-1) if full else None}
    return rows,summary


def turnover(ledger,sessions):
    entries=collections.Counter(x['session'] for x in ledger['funded'].values())
    exits=collections.Counter(x['session'] for x in ledger['closed'])
    values=[entries[x] for x in sessions]
    exit_values=[exits[x] for x in sessions]
    byday=collections.defaultdict(list)
    for x in ledger['snapshots']:
        byday[x['session']].append(x)
    active_minutes=0; slots=0; max3=0; valid_util=0; util_weight=0.0; util_ge80=0
    for session in sessions:
        rows=sorted(byday[session],key=lambda x:x['minute'])
        for row,next_row in zip(rows,rows[1:]):
            # A state persists to the next event only during scheduled trading.
            span=sum(row['minute']<=minute<next_row['minute']
                     for minute in execution.continuous_minutes(session))
            active_minutes+=span;slots+=row['openCount']*span
            max3+=(row['openCount']==3)*span
            if row['utilization'] is not None:
                valid_util+=span
                util_weight+=float(row['utilization'])*span
                util_ge80+=(float(row['utilization'])>=.8)*span
    holds=[x['holdingWallMinutes'] for x in ledger['closed']]
    buy=sum((Decimal(x['notionalJpy']) for x in ledger['funded'].values()),Decimal(0))
    sold=sum((Decimal(x['notionalJpy'])+Decimal(x['realizedPnlJpy'])
              for x in ledger['closed']),Decimal(0))
    return {'fundedEntries':len(ledger['funded']),'confirmedExits':len(ledger['closed']),
            'entriesPerTradingDayMean':statistics.fmean(values),
            'entriesPerTradingDayMedian':statistics.median(values),
            'entriesPerTradingDayMax':max(values),
            'exitsPerTradingDayMean':statistics.fmean(exit_values),
            'exitsPerTradingDayMedian':statistics.median(exit_values),
            'exitsPerTradingDayMax':max(exit_values),
            'daily':[{'session':s,'entries':entries[s],'exits':exits[s],
                      'distinctPositions':entries[s],
                      'slotTurnover':entries[s]/3} for s in sessions],
            'slotTurnoverPerDayMean':statistics.fmean(x/3 for x in values),
            'buyNotionalJpy':str(buy),'confirmedSellCashJpy':str(sold),
            'cashTurnoverJpy':str(buy+sold),'cashTurnoverInitialEquityTimes':float((buy+sold)/1000000),
            'averageHoldingWallMinutes':statistics.fmean(holds) if holds else None,
            'medianHoldingWallMinutes':statistics.median(holds) if holds else None,
            'scheduledActiveMinutes':active_minutes,
            'averageConcurrentPositions':slots/active_minutes if active_minutes else None,
            'timeAtMax3Share':max3/active_minutes if active_minutes else None,
            'timeWeightedUtilizationValidOnly':util_weight/valid_util if valid_util else None,
            'utilizationValidActiveMinutes':valid_util,
            'utilizationCoverage':valid_util/active_minutes if active_minutes else None,
            'utilizationGe80TimeShareValidOnly':util_ge80/valid_util if valid_util else None}


def portfolio_card(ledger,daily_summary):
    snaps=ledger['snapshots'];closed=ledger['closed']
    pnl=[float(x['realizedPnlJpy']) for x in closed]
    profit=sum(x for x in pnl if x>0);loss=-sum(x for x in pnl if x<0)
    nets=[float(x['netReturnPct']) for x in closed]
    complete=all(x['equityValid'] for x in snaps)
    curve=v1.curve(ledger)
    full=complete and daily_summary['nullSessions']==0 and not ledger['endOpenEntryIds']
    final=snaps[-1]['equityJpy'] if daily_summary['nullSessions']==0 and not ledger['endOpenEntryIds'] else None
    return {'initialEquityJpy':'1000000','finalEquityJpy':final,
            'portfolioReturnPct':100*(float(final)/1000000-1) if final is not None else None,
            'realizedPnlJpy':snaps[-1]['realizedPnlJpy'],
            'unrealizedPnlJpy':snaps[-1]['unrealizedPnlJpy'],
            'fullPeriodIntradayMaxDrawdownPct':min(x['drawdownPct'] for x in curve) if full else None,
            'pricedSegmentDrawdownPct':min((x['drawdownPct'] for x in curve
                                          if x['drawdownPct'] is not None),default=None),
            'profitFactor':profit/loss if loss else None,
            'winRate':sum(x>0 for x in pnl)/len(pnl) if pnl else None,
            'averageWinJpy':statistics.fmean(x for x in pnl if x>0) if profit else None,
            'averageLossJpy':statistics.fmean(x for x in pnl if x<0) if loss else None,
            'netReturnP05Pct':v0.percentile(nets,.05),
            'netReturnP10Pct':v0.percentile(nets,.10),
            'worstNetReturnPct':min(nets) if nets else None,
            'fundedEntries':len(ledger['funded']),'confirmedExits':len(closed),
            'validEventSnapshots':sum(x['equityValid'] for x in snaps),
            'allEventSnapshots':len(snaps),
            'valuationEventCoverage':sum(x['equityValid'] for x in snaps)/len(snaps),
            'endOpenPositions':len(ledger['endOpenEntryIds']),
            'unresolvedPositions':len(ledger['unresolvedEntryIds']),
            'finalExitSelected':False,'formalCapitalSelected':False}


def recycling(integrated,terminal,model,terminal_outcomes,evaluation,raw):
    """Identity delta and earlier release witnesses, all after the immutable replay."""
    new=sorted(set(integrated['funded'])-set(terminal['funded']))
    lost=sorted(set(terminal['funded'])-set(integrated['funded']))
    closed={r['entryId']:r for r in integrated['closed']}
    early=[]
    for row in integrated['events']:
        for exit_event in row['exitEvents']:
            eid=exit_event['entryId']
            if (exit_event['status']=='CLOSED' and
                model[eid]['exitKind']=='MODEL_EXIT'):
                early.append({'entryId':eid,'timestamp':v0.minute_stamp(row['session'],row['minute']),
                              'session':row['session'],'minute':row['minute'],
                              'grossProceedsJpy':str(exit_event['proceedsJpy']),
                              'netFreedCashJpy':str(Decimal(exit_event['proceedsJpy'])-
                                                     Decimal(exit_event['sellCostJpy'])),
                              'freedSlots':1,'minutesBeforeTerminal':930-row['minute']})
    witnesses=[]
    for eid in new:
        session=integrated['funded'][eid]['session']
        when=integrated['funded'][eid]['entryTimestamp']
        prior=[x for x in early if x['timestamp']<=when]
        v0.require(bool(prior),'RECYCLING_ENTRY_WITHOUT_CONFIRMED_EARLY_RELEASE')
        trade=closed.get(eid)
        value=evaluation[eid]['postUpsidePct']
        witnesses.append({'entryId':eid,'entryTimestamp':when,
                          'precedingConfirmedEarlyExitIds':[x['entryId'] for x in prior],
                          'latestPrecedingRelease':prior[-1]['timestamp'],
                          'sameDayReleaseWitness':any(x['session']==session for x in prior),
                          'upsidePct':value,'postEntryUpsideGe5':value is not None and value>=5,
                          'postEntryUpsideGe7_5':value is not None and value>=7.5,
                          'postEntryUpsideGe10':value is not None and value>=10,
                          'realizedPnlJpy':trade['realizedPnlJpy'] if trade else None,
                          'quantity':integrated['funded'][eid]['quantity']})
    changed=[]
    for x in early:
        eid=x['entryId'];meta=integrated['funded'][eid];t=terminal['funded'].get(eid)
        terminal_price=terminal_outcomes[eid]['exitPrice']
        observed=raw.get(meta['session']+'|'+meta['symbol'],{})
        later=[float(bar[2]) for minute,bar in observed.items() if x['minute']<minute<=930]
        price=(Decimal(x['grossProceedsJpy'])/meta['quantity'])
        post_high=max(later) if later else None
        own_terminal_delta=((price-Decimal(str(terminal_price)))*meta['quantity']
                            if terminal_price is not None else None)
        # If portfolio sizing diverged, hold the actual funded quantity fixed
        # for the per-position counterfactual; no proceeds are added to cash.
        changed.append({**x,'terminalControlAlsoFunded':t is not None,
                        'postExitObservedBestHigh':post_high,
                        'missedPostExitUpsidePctVsExit':
                        max(0.,100*(post_high/float(price)-1)) if post_high is not None else None,
                        'ownPnlDeltaVsTerminalSameQuantityJpy':
                        str(own_terminal_delta) if own_terminal_delta is not None else None,
                        'captureLossVsTerminalPp':
                        float(own_terminal_delta/Decimal(meta['notionalJpy'])*100)
                        if own_terminal_delta is not None else None,
                        'witnessedRecyclingIds':[y['entryId'] for y in witnesses
                                                 if x['entryId'] in y['precedingConfirmedEarlyExitIds']]})
    inc_realized=sum((Decimal(closed[eid]['realizedPnlJpy']) for eid in new if eid in closed),Decimal(0))
    return {'recyclingFundedPositions':len(new),'terminalOnlyFundedPositions':len(lost),
            'netEntryCountGain':len(integrated['funded'])-len(terminal['funded']),
            'recyclingHighUpsideGe5':sum(x['postEntryUpsideGe5'] for x in witnesses),
            'recyclingGe7_5':sum(x['postEntryUpsideGe7_5'] for x in witnesses),
            'recyclingGe10':sum(x['postEntryUpsideGe10'] for x in witnesses),
            'recyclingClosedRealizedPnlJpy':str(inc_realized),
            'recyclingFundedIds':new,'terminalOnlyFundedIds':lost,
            'recyclingRows':witnesses,'earlyReleaseRows':changed,
            'earlyReleasedCashTotalJpy':str(sum((Decimal(x['netFreedCashJpy']) for x in early),Decimal(0))),
            'earlyReleasedSlots':len(early),
            'releaseWitnessScope':'same-session preceding confirmed exits; shared witnesses do not imply unique attribution'}


def evaluate(p,data,replays,model):
    """All future target and PnL attribution begins after six completed replays."""
    _,_,cohort,intents,evaluation,terminal,raw,_,_,labels=data
    folds=data[0]['split']['folds']
    result={'schema':'phase57-experimental-development-capital-exit-integrated-v1',
            'status':'EXPERIMENTAL_DEVELOPMENT_INTEGRATED_REPLAY',
            'contractSha256':PRECOMMIT_SHA256,'rankSelected':False,
            'finalExitSelected':False,'modelFits':0,'providerRequests':0,
            'protectedPartitionsOpened':0,'safety':SAFETY,'arms':{}}
    for arm in v0.ARMS:
        name='IM' if arm==v0.IM else 'R1'
        arm_out={}
        scope=[x for x in intents[arm] if x['timestamp'][:10] in p['sessions']]
        scoped_eval={eid:x for eid,x in evaluation[arm].items()
                     if x['session'] in p['sessions']}
        for method in ('V3_B_TERMINAL','V3_B_R50_A','CAUSAL_RANK_R50_A'):
            ledger=replays[arm,method]
            dr,stats=daily(ledger,p['sessions'])
            rank_rows=(scope if method=='CAUSAL_RANK_R50_A'
                       else v3.ranked_intents(scope,load_pinned_score(arm)))
            stats_v3=v3.attribute(ledger,rank_rows,scoped_eval,labels[arm],folds)
            upside=[evaluation[arm][eid]['postUpsidePct'] for eid in ledger['funded']]
            arm_out[method]={
                'fundedUpsideBuckets':distribution(ledger,evaluation[arm]),
                'upside':stats_v3,
                'fundedGe7_5Count':sum(x is not None and x>=7.5 for x in upside),
                'fundedGe10Count':sum(x is not None and x>=10 for x in upside),
                'availableGe7_5Count':sum(x['postUpsidePct'] is not None and
                                         x['postUpsidePct']>=7.5 for x in scoped_eval.values()),
                'availableGe10Count':sum(x['postUpsidePct'] is not None and
                                        x['postUpsidePct']>=10 for x in scoped_eval.values()),
                'turnover':turnover(ledger,p['sessions']),
                'portfolio':portfolio_card(ledger,stats),
                'dailySummary':stats,'daily':dr}
        integrated=replays[arm,'V3_B_R50_A']
        control=replays[arm,'V3_B_TERMINAL']
        arm_out['recycling']=recycling(integrated,control,model[arm],terminal[arm],
                                     evaluation[arm],raw)
        arm_out['capacityFullMissReduction']=(
            arm_out['V3_B_TERMINAL']['upside']['missReasons'].get('CAPACITY_FULL',0)-
            arm_out['V3_B_R50_A']['upside']['missReasons'].get('CAPACITY_FULL',0))
        arm_out['rankDeltaSameExit']={
            'fundedEntries':arm_out['V3_B_R50_A']['turnover']['fundedEntries']-
                            arm_out['CAUSAL_RANK_R50_A']['turnover']['fundedEntries'],
            'fundedGe5':arm_out['V3_B_R50_A']['upside']['hitN']-
                         arm_out['CAUSAL_RANK_R50_A']['upside']['hitN']}
        result['arms'][name]=arm_out
    return result


def load_pinned_score(arm):
    # Exact CI prediction bytes are re-read for attribution sorting only;
    # run_replays received the same pinned projection before any evaluator.
    return json.loads((ROOT/'docs/evidence/phase57-capital-v3/RESULT/scores.json').read_text())['CAPITAL_V3_B'][arm]


def save_artifacts(out,p,data,replays,report):
    v0.require(not out.exists(),'INTEGRATION_OUTPUT_ALREADY_EXISTS')
    out.mkdir(parents=True)
    for (arm,method),ledger in replays.items():
        prefix=('IM' if arm==v0.IM else 'R1')+'_'+method
        (out/(prefix+'_ledger.json.gz')).write_bytes(gzip.compress(v0.canonical(ledger),mtime=0))
        curve=v1.curve(ledger)
        (out/(prefix+'_curve.json')).write_bytes(v0.canonical(curve))
        with (out/(prefix+'_curve.csv')).open('w',newline='') as f:
            fields=['timestamp','equityJpy','cashJpy','grossExposureJpy',
                    'utilization','drawdownPct','equityValid']
            w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(curve)
    (out/'report.json').write_bytes(v0.canonical(report))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    for label,series in {
        'IM_v3B_terminal_vs_R50A':[(v0.IM,'V3_B_TERMINAL'),(v0.IM,'V3_B_R50_A')],
        'R1_v3B_terminal_vs_R50A':[(v0.R1,'V3_B_TERMINAL'),(v0.R1,'V3_B_R50_A')],
        'R50A_IM_vs_R1':[(v0.IM,'V3_B_R50_A'),(v0.R1,'V3_B_R50_A')],
    }.items():
        fig,ax=plt.subplots(figsize=(10,3.5))
        for arm,method in series:
            source=v1.curve(replays[arm,method])
            x=[dt.datetime.fromisoformat(q['timestamp']) for q in source]
            y=[float(q['equityJpy']) if q['equityJpy'] is not None else math.nan
               for q in source]
            ax.plot(x,y,label=('IM' if arm==v0.IM else 'R1')+' '+method,
                    linewidth=1.2)
        ax.set_title('Experimental Development — '+label)
        ax.set_ylabel('valid as-of equity (JPY); gaps are null')
        ax.grid(alpha=.25);ax.legend(fontsize=8);fig.autofmt_xdate()
        fig.tight_layout();fig.savefig(out/(label+'.png'),dpi=130);plt.close(fig)
    (out/'manifest.json').write_bytes(v0.canonical({
        'schema':'phase57-integrated-finite-result-manifest-v1',
        'precommitSha256':PRECOMMIT_SHA256,
        'executionSha':__import__('subprocess').check_output(['git','rev-parse','HEAD'],text=True).strip(),
        'sourceSha256':v0.digest(ROOT/'scripts/phase57_capital_exit_integrated.py'),
        'filesSha256':{x.name:v0.digest(x) for x in sorted(out.iterdir()) if x.is_file()},
        'providerRequests':0,'protectedPartitionsOpened':0,'safety':SAFETY}))


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--mode',choices=['preflight','finite'],required=True)
    ap.add_argument('--out',type=Path,required=True)
    args=ap.parse_args()
    p,data,score,model=load_inputs()
    if args.mode=='preflight':
        receipt={'schema':'phase57-integrated-preperformance-preflight-v1',
                 'contractSha256':PRECOMMIT_SHA256,'sessions':len(p['sessions']),
                 'rankScores':{a:len(score[a]) for a in v0.ARMS},
                 'R50AScope':{a:len(model[a]) for a in v0.ARMS},
                 'modelFits':0,'allocationReplays':0,'fundedPerformanceRead':False,
                 'providerRequests':0,'protectedPartitionsOpened':0,'safety':SAFETY}
        args.out.write_bytes(v0.canonical(receipt))
        print(json.dumps(receipt,sort_keys=True))
        return
    replays=run_replays(data,score,model)
    report=evaluate(p,data,replays,model)
    save_artifacts(args.out,p,data,replays,report)
    print(json.dumps({'status':report['status'],'out':str(args.out),
                      'funded':{a:report['arms'][a]['V3_B_R50_A']['turnover']['fundedEntries']
                                for a in ('IM','R1')},'fits':0},sort_keys=True))


if __name__=='__main__': main()
