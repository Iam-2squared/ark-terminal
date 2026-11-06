"""Independent, zero-fit artifact and full chronological replay audit for R52.

Run after the finite Action; the verdict produced inside it is provisional until
this auditor verifies its immutable predictions and every funded cash ledger.
"""
from __future__ import annotations
import argparse, collections, gzip, json, math, statistics
from decimal import Decimal
from pathlib import Path
import numpy as np
from scripts import phase57_exit_continuation_r52 as r
from scripts import phase57_capital_exit_integrated as integrated
from scripts import phase57_capital_v3 as v3
from scripts import phase57_development_integrated_v0 as v0

def supplemental(ledger,evaluation,sessions):
    """Additional deterministic measures from certified trades and valid spans."""
    funded=ledger['funded'];closed=ledger['closed'];closes={x['entryId']:x for x in closed}
    count=collections.Counter(x['session'] for x in funded.values());daily=[count[s] for s in sessions]
    active=[];wall=[]
    for x in closed:
        minute=int(x['exitTimestamp'][11:13])*60+int(x['exitTimestamp'][14:16])
        active.append(r.execution.active_minutes(x['session'],x['entryMinute'],minute))
        wall.append(x['holdingWallMinutes'])
    snaps=collections.defaultdict(list)
    for x in ledger['snapshots']:snaps[x['session']].append(x)
    minutes=valid=invalid=idle_valid=at80=slots_full=0
    idle_cash_jpy_minutes=Decimal(0)
    for s in sessions:
        rows=sorted(snaps[s],key=lambda x:x['minute'])
        for before,after in zip(rows,rows[1:]):
            span=sum(before['minute']<=minute<after['minute'] for minute in r.execution.continuous_minutes(s))
            minutes+=span;slots_full+=(before['openCount']==3)*span
            if before['equityValid'] and before['utilization'] is not None:
                valid+=span;at80+=(float(before['utilization'])>=.8)*span
                cash=Decimal(before['cashJpy']);idle_valid+=(cash>0)*span
                idle_cash_jpy_minutes+=cash*span
            else:invalid+=span
    require=lambda b,m:v0.require(b,m)
    require(minutes==len(sessions)*325 and valid+invalid==minutes,'TIME_DENOMINATOR')
    pnl=[Decimal(x['realizedPnlJpy']) for x in closed]
    profits=sum((x for x in pnl if x>0),Decimal(0));losers=sum((x for x in pnl if x<0),Decimal(0))
    costs=sum((Decimal(x['sellCostJpy']) for x in closed),Decimal(0))
    symbols=collections.Counter();days=collections.Counter()
    for x in funded.values():
        symbols[x['symbol']]+=Decimal(x['notionalJpy']);days[x['session']]+=Decimal(x['notionalJpy'])
    total=sum((Decimal(x['notionalJpy']) for x in funded.values()),Decimal(0))
    reach={}
    for threshold in (3,4,5,7.5,10):
        available=sum(x['postUpsidePct'] is not None and x['postUpsidePct']>=threshold for x in evaluation.values()
                      if x['session'] in sessions)
        got=sum(evaluation[e]['postUpsidePct'] is not None and
                evaluation[e]['postUpsidePct']>=threshold for e in funded)
        reach[str(threshold)]={'available':available,'funded':got,
                               'reach':got/available if available else None}
    return {'funded':len(funded),'closed':len(closed),'unresolved':len(ledger['endOpenEntryIds']),
        'entriesPerDay':{'mean':statistics.fmean(daily),'median':statistics.median(daily),
                         'p75':float(np.percentile(daily,75)),'max':max(daily)},
        'holdingActiveMinutesMean':statistics.fmean(active) if active else None,
        'holdingWallMinutesMean':statistics.fmean(wall) if wall else None,
        'activeTradingMinutes':minutes,'validMarkMinutes':valid,'invalidMarkMinutes':invalid,
        'validMarkCoverage':valid/minutes,'idleCashValidMinutes':idle_valid,
        'idleCashAmountJpyMinuteIntegral':str(idle_cash_jpy_minutes),
        'ge80ValidMinutes':at80,'timeAtMax3Minutes':slots_full,
        'winnerPnlJpy':str(profits),'loserDragJpy':str(losers),
        'sellCostsJpy':str(costs),'topSymbolNotionalShare':float(max(symbols.values())/total) if total else None,
        'topSessionNotionalShare':float(max(days.values())/total) if total else None,
        'evaluatorOnlyThresholdReach':reach,
        'qualityAvailability':'Fixed Capital v3-B has no quality floor; one-shot Entry cannot persist as idle eligible time.'}

def audit(out:Path,source:Path,target:Path):
    p=r.protocol();manifest=json.loads((out/'manifest.json').read_text())
    v0.require(manifest['protocolSha256']==v0.digest(r.PRECOMMIT) and
               len(manifest['filesSha256'])>20 and manifest['modelFits']==16 and
               not any(manifest['safety'].values()),'FINITE_MANIFEST')
    for name,sha in manifest['filesSha256'].items():
        v0.require(v0.digest(out/name)==sha,'FINITE_FILE_DIGEST:'+name)
    fit=json.loads((out/'fit-manifest.json').read_text());v0.require(len(fit)==16,'FINITE_FIT_COUNT')
    for row in fit:
        v0.require(row['trainMax']<row['scoreMin'] and row['estimatorFits']==1 and
                   row['imputerFits']==row['scalerFits']==1 and
                   v0.digest(out/'models'/row['modelFile'])==row['modelSha256'],
                   'FINITE_FIT_TEMPORAL_IDENTITY')
    receipt,arrays,identities,groups=r.load_checkpoints(source)
    entries=r.all_frozen_entries();raw=r.projected_raw(entries)
    with np.load(out/'oof-predictions.npz',allow_pickle=False) as z:
        v0.require(set(z.files)==set(r.CANDIDATES),'PREDICTION_CANDIDATES')
        preds={c:z[c] for c in r.CANDIDATES}
    v0.require(all(len(preds[c])==len(identities) for c in r.CANDIDATES),
               'PREDICTION_ROW_IDENTITY')
    _,data,score,model=integrated.load_inputs()
    calendars,traces=r.exit_calendars(p,receipt,arrays,identities,groups,entries,raw,preds,model)
    _,_,cohort,intents,evaluation,terminal,joined_raw,_,_,_=data
    card=json.loads((out/'scorecard.json').read_text());selection=json.loads((out/'selection.json').read_text())
    matched={};audit_cards={};cash_checks={};extra={}
    for arm in v0.ARMS:
        short='IM' if arm==v0.IM else 'R1';ranked=v3.ranked_intents(
          [x for x in intents[arm] if x['timestamp'][:10] in p['sessions']],score[arm])
        subset={**cohort,'sessions':p['sessions']}
        for candidate in ('R50_A_CONTROL',)+r.CANDIDATES:
            calendar=model[arm] if candidate=='R50_A_CONTROL' else calendars[candidate][arm]
            reconstructed=integrated.replay(arm,3,subset,ranked,joined_raw,calendar)
            with gzip.open(out/(short+'_'+candidate+'_ledger.json.gz'),'rt') as f:saved=json.load(f)
            v0.require(v0.canonical(saved)==v0.canonical(reconstructed),
                       'SAVED_PREDICTION_REPLAY_NOT_IDENTICAL:'+short+candidate)
            v0.require(all(Decimal(x['cashJpy'])>=0 and x['openCount']<=3 for x in saved['snapshots'])
                       and all(int(x['quantity'])>0 and int(x['quantity'])%100==0 for x in saved['funded'].values()),
                       'CASH_OR_LOT_OR_SLOT')
            v0.require(set(saved['funded'])<=set(score[arm]) and len(saved['closed'])+len(saved['endOpenEntryIds'])
                       ==len(saved['funded']),'FUNDING_SCOPE_AND_RESOLUTION')
            identified=r.classify(saved)
            v0.require(sum(x['n'] for key,x in card[short][candidate]['quality'].items() if key!='Combined')
                       ==len(saved['funded'])==card[short][candidate]['quality']['Combined']['n'],
                       'COHORT_RECONCILIATION')
            for key in ('Initial','Replacement','Combined'):
                expected=sum(identified[e]==key or key=='Combined' for e in identified)
                buckets=card[short][candidate]['buckets'][key]
                v0.require(sum(x['count'] for x in buckets)==expected and
                     sum((Decimal(x['capitalAllocatedJpy']) for x in buckets),Decimal(0))==
                     sum((Decimal(saved['funded'][eid]['notionalJpy']) for eid in identified
                          if key=='Combined' or identified[eid]==key),Decimal(0)),
                     'BUCKET_CAPITAL_RECONCILIATION')
            daily=card[short][candidate]['daily']
            v0.require(len(daily)==24 and [x['session'] for x in daily]==p['sessions'] and
                sum(x['certified'] for x in daily)==card[short][candidate]['dailySummary']['validSessions'],
                'DAILY_SESSION_CENSUS')
            v0.require(all(x['dailyReturn'] is None for x in daily if not x['certified']),
                'NULL_RETURN_FABRICATION')
            if card[short][candidate]['dailySummary']['validSessions']<24:
                v0.require(card[short][candidate]['dailySummary']['geometric'] is None,
                           'PARTIAL_GEOMETRIC_FABRICATION')
            elif saved['snapshots'][-1]['equityJpy'] is not None:
                final=Decimal(saved['snapshots'][-1]['equityJpy'])
                geometric=float((final/Decimal('1000000'))**(Decimal(1)/Decimal(24))-1)
                v0.require(abs(geometric-card[short][candidate]['dailySummary']['geometric'])<1e-12,
                           'DAILY_GEOMETRIC_IDENTITY')
            matched[short+'_'+candidate]=True
            extra[short+'_'+candidate]=supplemental(saved,evaluation[arm],p['sessions'])
            cash_checks[short+'_'+candidate]={'funded':len(saved['funded']),'closed':len(saved['closed']),
                'cashMinJpy':min(x['cashJpy'] for x in saved['snapshots']),
                'maxOpen':max(x['openCount'] for x in saved['snapshots']),
                'validEod':sum(x['certified'] for x in daily)}
        baseline=r.archive_control(arm)
        with gzip.open(out/(short+'_R50_A_CONTROL_ledger.json.gz'),'rt') as f:stored=json.load(f)
        v0.require(v0.canonical(stored)==v0.canonical(baseline),'ARCHIVED_CONTROL_CHANGED')
        for candidate in r.CANDIDATES:
            with gzip.open(out/(short+'_'+candidate+'_ledger.json.gz'),'rt') as f:new=json.load(f)
            attribution=r.pnl_delta(baseline,new)
            v0.require(attribution==card[short][candidate]['currencyAttributionVsControl'],
                       'CLOSED_CURRENCY_ATTRIBUTION')
            with (out/(short+'_'+candidate+'_layerA.json')).open() as f:layer=json.load(f)
            v0.require(len(layer)==len(baseline['funded']) and
                       set(x['entryId'] for x in layer)==set(baseline['funded']),
                       'LAYER_A_BASELINE_QUANTITY_SCOPE')
            audit_cards[short+'_'+candidate]=attribution
    v0.require(selection['selection'] is None or selection['votes'][selection['selection']]['passed'],
               'SELECTED_FAILED_GATE')
    result={'schema':'phase57-r52-independent-zero-fit-audit-v1','status':'PASS',
            'protocolSha256':v0.digest(r.PRECOMMIT),'executionSha':manifest['executionSha'],
            'predictionSha256':manifest['predictionSha256'],'predictionRefits':0,
            'sameSavedPredictionsAllReplays':True,'controlArchivedByteIdentity':True,
            'savedLedgerByteIdentity':matched,'cashAndEod':cash_checks,'currencyAttribution':audit_cards,
            'provisionalVerdict':selection['status'],'candidateCount':2,'modelFitsInArtifact':16,
            'providerRequests':0,'protectedPartitionsOpened':0,'safety':v0.SAFETY}
    target.write_bytes(v0.canonical(result))
    target.with_name('SUPPLEMENTAL_SCORECARD.json').write_bytes(v0.canonical(extra))
    print(json.dumps({'status':'PASS','ledgers':len(matched),
                                                               'verdict':selection['status']}))

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--source',type=Path,required=True);parser.add_argument('--receipt',type=Path,required=True)
    a=parser.parse_args();audit(a.out,a.source,a.receipt)
if __name__=='__main__':main()
