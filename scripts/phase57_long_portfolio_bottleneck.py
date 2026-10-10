"""Read-only component diagnostics; frozen policies are imported, never modified."""
import argparse
import collections
import gzip
import hashlib
import json
import math
from pathlib import Path
import statistics

from scripts.phase57_long_capital_integration import (
    CONTRACT as CAPITAL_CONTRACT, EXIT_BASE, IDENTITIES, PATHS, PREDICTIONS,
    causal_envelopes, digest, iso, quantile, replay, stamp, stats, weights,
)

BASE = Path('docs/evidence/phase57-long-capital-integration-v1')
OUT = Path('docs/evidence/phase57-long-portfolio-bottleneck-v1')
CONTRACT = Path('predict/research/phase57-long-portfolio-bottleneck-v1.json')
FEATURES = Path('docs/evidence/phase57-msh-entry-long-v1-preimplementation-feasibility-events.ndjson.gz')


def read(path):
    raw = Path(path).read_bytes()
    if str(path).endswith('.gz'):
        raw = gzip.decompress(raw)
    return json.loads(raw)


def ndjson(path):
    return [json.loads(line) for line in gzip.decompress(Path(path).read_bytes()).decode().splitlines()]


def performance(trades):
    ps = [r['pnlJpy'] for r in trades]
    gp, gl = sum(max(0,p) for p in ps), -sum(min(0,p) for p in ps)
    return {'pnlJpy': stats(ps), 'unitNetPct': stats([r['netPct'] for r in trades]),
            'winRate': sum(p>0 for p in ps)/len(ps) if ps else None,
            'profitFactor': gp/gl if gl else ('INF' if gp else None),
            'tailMinus10': sum(r['netPct']<=-10 for r in trades)}


def extrema(e, bars):
    rows = e['future'][:bars]
    if not rows or len(rows)<bars or any(b['missing'] for b in rows):
        return {'mfe': None, 'mae': None}
    return {'mfe': max(0,max(b['h'] for b in rows)), 'mae': min(0,min(b['l'] for b in rows))}


def component(trade, e, t):
    """Realized + unrealized equity contribution; no carry-forward open marks."""
    start, end = stamp(trade['entryTimestamp']), stamp(trade['exitTimestamp'])
    if t < start:
        return 0., 0.
    if t >= end:
        return trade['pnlJpy'], 0.
    price = e['decisionPrice']
    if t == start:
        close = price
    else:
        bar = next((b for b in e['future'] if stamp(b['end']) == t), None)
        assert bar and not bar['missing'], 'NO_EXACT_OPEN_POSITION_MARK'
        close = price*(1+bar['c']/100)
    return -trade['feesJpy']/2, (close-price)*trade['quantity']


def curve_diagnostics(curve, initial):
    peak, peak_i, max_dd, episode = initial, 0, 0., None
    max_jpy = 0.
    for i, row in enumerate(curve):
        eq = row['equityJpy']
        assert eq is not None
        if eq > peak:
            peak, peak_i = eq, i
        loss = peak-eq
        max_jpy = max(max_jpy, loss)
        pct = loss/peak*100
        if pct > max_dd:
            max_dd = pct
            episode = {'startIndex': peak_i, 'troughIndex': i, 'startTimestamp': curve[peak_i]['timestamp'],
                       'troughTimestamp': row['timestamp'], 'peakEquity': peak, 'troughEquity': eq,
                       'drawdownJpy': loss, 'drawdownPct': pct}
    if episode:
        later = next((r for r in curve[episode['troughIndex']+1:] if r['equityJpy'] >= episode['peakEquity']), None)
        episode['recoveryTimestamp'] = later['timestamp'] if later else None
    return {'maxDrawdownPct': max_dd, 'maxDrawdownJpy': max_jpy, 'episode': episode}


def compact(r):
    return {k:r[k] for k in ['finalEquityJpy','totalReturnPct','maxDrawdownPct','maxDrawdownJpy','trade','capital','concentration']}


def breakdown(rows, key):
    groups = collections.defaultdict(list)
    for r in rows:
        groups[str(r[key])].append(r)
    return {k:{'n':len(v), 'mshScore':stats([r['mshScore'] for r in v]),
               'selectorScore':stats([r['selectorScore'] for r in v]),
               'selectorRank':stats([r['selectorRank'] for r in v]),
               'label30Evaluable':sum(r['opportunity30'] is not None for r in v),
               'opportunityHits':{str(t): {'hits':sum(r['opportunity30'] is not None and r['opportunity30']>=t for r in v),
                                         'denominator':sum(r['opportunity30'] is not None for r in v)} for t in [1,2,3,5]}}
            for k,v in sorted(groups.items())}


def group_performance(rows, field, trades, decisions, by_id, cutpoints=None):
    groups = collections.defaultdict(list)
    for r in rows:
        value = r[field]
        key = str(value) if cutpoints is None else 'Q'+str(1+sum(value>q for q in cutpoints))
        groups[key].append(r)
    out = {}
    for key, rs in sorted(groups.items()):
        ids = {r['eventId'] for r in rs}
        ts = [t for t in trades if t['eventId'] in ids]
        features = [extrema(by_id[t['eventId']], min(12,by_id[t['eventId']]['expectedBars'])) for t in ts]
        out[key] = {'opportunities':len(rs), 'accepted':len(ts), 'rejected':len(rs)-len(ts),
                    'scoreRange':[min(r[field] for r in rs),max(r[field] for r in rs)],
                    **performance(ts), 'mfe':stats([v['mfe'] for v in features if v['mfe'] is not None]),
                    'mae':stats([v['mae'] for v in features if v['mae'] is not None]),
                    'allocatedCapitalJpy':stats([t['entryNotionalJpy'] for t in ts])}
    return out


def run(output=OUT):
    contract = read(CONTRACT)
    manifest = read(BASE/'manifest.json')
    for name, h in manifest['artifacts'].items():
        assert digest(BASE/name)==h, name
    for name,h in {**manifest['codePins'],**manifest['upstreamPins']}.items():
        assert digest(name)==h,name
    exit_final = read(EXIT_BASE/'development-final.json')
    assert digest(FEATURES)==exit_final['upstreamPins'][str(FEATURES)]
    assert digest(EXIT_BASE/'path-diagnostic-ledger.json')==exit_final['evidencePins'][str(EXIT_BASE/'path-diagnostic-ledger.json')]
    assert digest(EXIT_BASE/'replay-ledger.json')==exit_final['evidencePins'][str(EXIT_BASE/'replay-ledger.json')]
    data = read(BASE/'measurement.json.gz')
    original = data['reports']['EXPOSED_COMMON173_DIAGNOSTIC']
    equal, rank = original['EQUAL_MAX3'], original['LONG_RANK_MAX3']
    fixed = data['reports']['EXPOSED_COMMON173_FIXED_REFERENCE']
    events = read(PATHS)['events']; by_id={e['selectorEventId']:e for e in events}
    identities = read(IDENTITIES)
    assert len(events)==len(by_id)==len(identities)==277
    for r in identities:
        assert all(by_id[r['selectorEventId']][k]==v for k,v in r.items())
    features={r['selectorEventId']:r for r in ndjson(FEATURES)}
    predictions={r['selectorEventId']:r for r in ndjson(PREDICTIONS)}
    cohorts={r['selectorEventId']:r for r in read(EXIT_BASE/'path-diagnostic-ledger.json')}
    results=read(EXIT_BASE/'replay-ledger.json')
    included=set(read(EXIT_BASE/'measurement.json')['pairedIdentities'])
    assert len(included)==173
    rows=[]
    for e in events:
        eid=e['selectorEventId']; f=features[eid]; result=results[eid]
        assert f['decisionPrice']==e['decisionPrice']
        missing=next((b for b in e['future'][:min(12,e['expectedBars'])] if b['missing']),None)
        long_ok=result['BAR5_TWO_LOWER_CLOSES']['status']=='EXIT_REFERENCE'
        if eid in included: reason='INCLUDED_COMMON173'
        elif e['expectedBars']==0: reason='NO_REMAINING_REGULAR_BAR'
        elif not long_ok: reason='MISSING_BAR_BEFORE_LONG_EXIT' if missing else 'INSUFFICIENT_PATH_OTHER'
        else: reason='LONG_EXIT_RESOLVED_OTHER_COMPARISON_ARM_CENSORED'
        auction=bool(missing and e['sessionDate']>='2024-11-05' and iso(stamp(missing['end']))[11:16] in ['15:25','15:30'])
        label=f.get('label',{})
        rows.append({'eventId':eid,'included':eid in included,'coverage':'INCLUDED' if eid in included else 'EXCLUDED',
                     'sessionDate':e['sessionDate'],'symbol':e['symbol'],'entryTime':iso(stamp(e['decisionTimestamp']))[11:16],
                     'entryTimestamp':e['decisionTimestamp'],'entryPrice':e['decisionPrice'],
                     'mshScore':predictions[eid]['expectedClass'],'selectorRank':f['ridgeRank'],'selectorScore':f['ridgeScore'],
                     'opportunity30':label.get('highReturnPct') if label.get('labelable') else None,
                     'cohort':cohorts[eid]['cohort'],'exclusiveReason':reason,
                     'firstMissingEnd':missing['end'] if missing else None,'auctionWindowFlag':auction,
                     'lateSessionFlag':iso(stamp(e['decisionTimestamp']))[11:16]>='14:30',
                     'noTradeVsDataGap':'UNKNOWN_NOT_INFERRED' if missing else 'NOT_APPLICABLE',
                     'longExitResolved':long_ok,'comparisonArmStatus':{k:v['status'] for k,v in result.items()}})
    enriched={r['eventId']:r for r in rows}; inc=[r for r in rows if r['included']]; exc=[r for r in rows if not r['included']]
    coverage={'n':277,'included':173,'excluded':104,'reasons':dict(collections.Counter(r['exclusiveReason'] for r in exc)),
              'overlappingFlags':{'lateSession':sum(r['lateSessionFlag'] for r in exc),'auctionWindow':sum(r['auctionWindowFlag'] for r in exc),
                                  'missingEntryPrice':0,'noTradeConfirmed':None,'dataGapConfirmed':None,
                                  'unresolvedLongExit':sum(not r['longExitResolved'] for r in exc)},
              'groups':{k:breakdown(rows,k) for k in ['coverage','sessionDate','symbol','entryTime','cohort']},
              'crossTabs':{k:{str(v):dict(collections.Counter(r['coverage'] for r in rows if r[k]==v)) for v in sorted(set(r[k] for r in rows))}
                           for k in ['sessionDate','symbol','entryTime','cohort','selectorRank']},
              'byCoverage':{c:{k:breakdown(rs,k) for k in ['sessionDate','symbol','entryTime','cohort']} for c,rs in [('INCLUDED',inc),('EXCLUDED',exc)]},
              'perEntry':rows}
    sessions=[r['sessionDate'] for r in equal['sessions']]
    capital=read(CAPITAL_CONTRACT)
    paired=[e for e in events if e['selectorEventId'] in included]
    env=causal_envelopes(events,predictions)
    closed=equal['closedTrades']
    sorted_trades=sorted(closed,key=lambda r:(-r['pnlJpy'],r['eventId']))
    symbol_pnl=collections.defaultdict(float)
    for t in closed: symbol_pnl[t['symbol']]+=t['pnlJpy']
    symbols=sorted(symbol_pnl,key=lambda s:(-symbol_pnl[s],s))
    removal_sets={'EXCLUDE_TOP1_TRADE':{sorted_trades[0]['eventId']},
                  'EXCLUDE_TOP1_SYMBOL':{e['selectorEventId'] for e in paired if e['symbol']==symbols[0]},
                  'EXCLUDE_TOP3_TRADES':{t['eventId'] for t in sorted_trades[:3]},
                  'EXCLUDE_TOP3_SYMBOLS':{e['selectorEventId'] for e in paired if e['symbol'] in symbols[:3]}}
    stress={'FULL':compact(equal)}
    sensitivity_ledgers={}
    for label,removed in removal_sets.items():
        remaining=[e for e in paired if e['selectorEventId'] not in removed]
        ids={e['selectorEventId'] for e in remaining}
        ws=weights([r for r in env if r['eventId'] in ids])['EQUAL_MAX3']
        result=replay(remaining,sessions,'EQUAL_MAX3',ws,capital)
        assert result['status']=='COMPLETE_REFERENCE_REPLAY'
        stress[label]={**compact(result),'removedOpportunityIds':sorted(removed),
                       'originalFixedQuantityPnlRemoved':sum(t['pnlJpy'] for t in closed if t['eventId'] in removed),
                       'interpretation':'HINDSIGHT_STRESS_ONLY_NOT_DEPLOYABLE_POLICY'}
        sensitivity_ledgers[label]=result
    # Reconstruct unchanged observed equity from individual contributions before attribution.
    timestamps=[stamp(r['timestamp']) for r in equal['equityCurve']]
    contributions={t['eventId']:[component(t,by_id[t['eventId']],s) for s in timestamps] for t in closed}
    error=max(abs(1000000+sum(sum(contributions[t['eventId']][i]) for t in closed)-row['equityJpy']) for i,row in enumerate(equal['equityCurve']))
    assert error<1e-5, 'PER_POSITION_CURVE_RECONCILIATION'
    dd=curve_diagnostics(equal['equityCurve'],1000000)
    ep=dd['episode']; start,trough=ep['startIndex'],ep['troughIndex']
    attribution=[]
    for t in closed:
        before=contributions[t['eventId']][start]; after=contributions[t['eventId']][trough]
        delta=sum(after)-sum(before)
        if abs(delta)>1e-8:
            attribution.append({**t,'realizedChangeJpy':after[0]-before[0],'unrealizedChangeJpy':after[1]-before[1],
                                'totalEquityChangeJpy':delta,'entryPrice':by_id[t['eventId']]['decisionPrice'],
                                'mshScore':enriched[t['eventId']]['mshScore'],**extrema(by_id[t['eventId']],t['holdingBars'])})
    attribution.sort(key=lambda x:x['totalEquityChangeJpy'])
    assert abs(sum(r['totalEquityChangeJpy'] for r in attribution)+ep['drawdownJpy'])<1e-5
    ddrows=equal['equityCurve'][start:trough+1]
    streak=max_streak=0
    for t in sorted(closed,key=lambda x:(stamp(x['exitTimestamp']),x['eventId'])):
        if timestamps[start]<=stamp(t['exitTimestamp'])<=timestamps[trough]:
            streak=streak+1 if t['pnlJpy']<0 else 0; max_streak=max(max_streak,streak)
    dd.update({'positions':attribution,'realizedChangeJpy':sum(r['realizedChangeJpy'] for r in attribution),
               'unrealizedChangeJpy':sum(r['unrealizedChangeJpy'] for r in attribution),
               'largestNegativeContributionShareOfNetDD':-attribution[0]['totalEquityChangeJpy']/ep['drawdownJpy'],
               'maxConcurrentDuringDD':max(r['openPositions'] for r in ddrows),
               'peakUtilizationDuringDD':max(r['utilization'] for r in ddrows),
               'sampleMeanUtilizationDuringDD':statistics.mean(r['utilization'] for r in ddrows),
               'consecutiveLosingExitsDuringDD':max_streak,
               'fullWindowConsecutiveLosingSessions':equal['maxConsecutiveLosingSessions'],
               'marketRegimeAttribution':'INCONCLUSIVE_NO_MARKET_SERIES',
               'curveReconciliationMaxErrorJpy':error})
    dd['heldPositionIds']=[t['eventId'] for t in closed if stamp(t['entryTimestamp'])<=timestamps[trough] and stamp(t['exitTimestamp'])>=timestamps[start]]
    session_streak=session_max=0
    for row in equal['sessions']:
        if ep['startTimestamp'][:10]<=row['sessionDate']<=ep['troughTimestamp'][:10]:
            pnl=row['returnPct']
            if pnl is not None:
                session_streak=session_streak+1 if pnl<0 else 0; session_max=max(session_max,session_streak)
    dd['consecutiveLosingSessionsDuringDD']=session_max
    positives=[t['pnlJpy'] for t in closed if t['pnlJpy']>0]; cap=quantile(positives,.95)
    factors={t['eventId']:min(1,cap/t['pnlJpy']) if t['pnlJpy']>0 else 1 for t in closed}
    synthetic=[dict(r,equityJpy=1000000+sum(sum(contributions[t['eventId']][i])*factors[t['eventId']] for t in closed)) for i,r in enumerate(equal['equityCurve'])]
    synthetic_trades=[dict(t,pnlJpy=t['pnlJpy']*factors[t['eventId']],netPct=t['netPct']*factors[t['eventId']]) for t in closed]
    stress['WINSORIZED_POSITIVE_P95_ADDITIVE_ONLY']={'finalEquityJpy':synthetic[-1]['equityJpy'],
        'totalReturnPct':(synthetic[-1]['equityJpy']/1000000-1)*100,**curve_diagnostics(synthetic,1000000),
        'performance':performance(synthetic_trades),'capJpy':cap,'cappedTrades':sum(f<1 for f in factors.values()),
        'interpretation':'SYNTHETIC_ADDITIVE_CONTRIBUTION_CURVE_NOT_SELF_FINANCING_OR_LOTTED_REPLAY'}
    top_rows=[]
    for t in closed:
        if t['symbol']!=symbols[0]:continue
        eid=t['eventId']; e=by_id[eid]; r=results[eid]['BAR5_TWO_LOWER_CLOSES']
        top_rows.append({**t,**enriched[eid],**extrema(e,t['holdingBars']),
                         'fixedWindowExtrema':extrema(e,min(12,e['expectedBars'])),
                         'firstBarReturnPct':e['future'][0].get('c'),'defensive':r['defensive'],'recovered':r['recovered'],
                         'transitions':r['transitions'],'continuationPath':e['future'][:t['holdingBars']]})
    concentration={'topSymbol':symbols[0],'topSymbolPnlJpy':symbol_pnl[symbols[0]],
                   'topTrade':sorted_trades[0],'top3Symbols':symbols[:3],
                   'topSymbolTrades':top_rows,'stress':stress}
    scuts=[quantile([r['selectorScore'] for r in inc],q) for q in [.25,.5,.75]]
    mcuts=[quantile([r['mshScore'] for r in inc],q) for q in [.25,.5,.75]]
    selectors={'ranks':group_performance(inc,'selectorRank',closed,equal['decisions'],by_id),
               'scoreQuartileCutpoints':scuts,'scoreQuartiles':group_performance(inc,'selectorScore',closed,equal['decisions'],by_id,scuts)}
    def monotonic(values,increasing):
        return all((b>=a if increasing else b<=a) for a,b in zip(values,values[1:]))
    means=[selectors['ranks'][k]['pnlJpy']['mean'] for k in sorted(selectors['ranks'],key=int)]
    selectors['rankMeanPnlMonotonicBetterAtRank1']=monotonic(means,False)
    selectors['rankUnitReturnMonotonicBetterAtRank1']=monotonic([selectors['ranks'][k]['unitNetPct']['mean'] for k in sorted(selectors['ranks'],key=int)],False)
    selectors['unobservedRanks']=[r for r in range(1,6) if str(r) not in selectors['ranks']]
    selectors['scoreQuartileMeanReturnMonotonic']=monotonic([v['unitNetPct']['mean'] for v in selectors['scoreQuartiles'].values()],True)
    entry={'quartileCutpoints':mcuts,'quartiles':group_performance(inc,'mshScore',closed,equal['decisions'],by_id,mcuts),
           'scoreMeaning':'E[30m ordinal opportunity class], NOT expected executable net return or risk-adjusted sizing utility',
           'highScoreLargeLosers':[t['eventId'] for t in closed if enriched[t['eventId']]['mshScore']>mcuts[2] and t['netPct']<=-10],
           'lowScoreLargeWinners':[t['eventId'] for t in closed if enriched[t['eventId']]['mshScore']<=mcuts[0] and t['netPct']>=5]}
    entry['meanNetReturnMonotonic']=monotonic([v['unitNetPct']['mean'] for k,v in sorted(entry['quartiles'].items())],True)
    eqby={t['eventId']:t for t in closed}; rkby={t['eventId']:t for t in rank['closedTrades']}
    common=set(eqby)&set(rkby)
    effects=[]
    ew=weights([r for r in env if r['eventId'] in included])
    for eid in sorted(common):
        a,b=eqby[eid],rkby[eid]
        assert abs(a['pnlJpy']/a['quantity']-b['pnlJpy']/b['quantity'])<1e-7
        effects.append({'eventId':eid,'symbol':a['symbol'],'equalQty':a['quantity'],'rankQty':b['quantity'],
                        'equalWeight':ew['EQUAL_MAX3'][eid],'rankWeight':ew['LONG_RANK_MAX3'][eid],
                        'mshScore':enriched[eid]['mshScore'],'equalPnlJpy':a['pnlJpy'],'rankPnlJpy':b['pnlJpy'],
                        'deltaJpy':b['pnlJpy']-a['pnlJpy'],'unitNetPct':a['netPct']})
    rkonly=sorted(set(rkby)-set(eqby)); eqonly=sorted(set(eqby)-set(rkby))
    alloc={'rankMinusEqualJpy':rank['finalEquityJpy']-equal['finalEquityJpy'],
           'commonCount':len(common),'commonQuantityEffectJpy':sum(r['deltaJpy'] for r in effects),
           'commonWinnerEffectJpy':sum(r['deltaJpy'] for r in effects if r['unitNetPct']>0),
           'commonLoserEffectJpy':sum(r['deltaJpy'] for r in effects if r['unitNetPct']<=0),
           'rankOnlyPnlJpy':sum(rkby[i]['pnlJpy'] for i in rkonly),'equalOnlyPnlJpy':sum(eqby[i]['pnlJpy'] for i in eqonly),
           'rankOnlyIds':rkonly,'equalOnlyIds':eqonly,'positionEffects':sorted(effects,key=lambda x:x['deltaJpy']),
           'equalCapital':equal['capital'],'rankCapital':rank['capital'],
           'equalRejections':[r for r in equal['decisions'] if r['status']=='REJECTED'],
           'rankRejections':[r for r in rank['decisions'] if r['status']=='REJECTED'],
           'eventOrdering':'IDENTICAL_FROZEN_ORDER_NOT_EXPERIMENTAL_VARIABLE'}
    assert abs(alloc['commonQuantityEffectJpy']+alloc['rankOnlyPnlJpy']-alloc['equalOnlyPnlJpy']-alloc['rankMinusEqualJpy'])<1e-5
    for qkey,qrow in entry['quartiles'].items():
        ids={r['eventId'] for r in inc if 'Q'+str(1+sum(r['mshScore']>q for q in mcuts))==qkey}
        qrow['equalWeights']=stats([ew['EQUAL_MAX3'][i] for i in sorted(ids)])
        qrow['rankWeights']=stats([ew['LONG_RANK_MAX3'][i] for i in sorted(ids)])
    exit_groups={}
    for reason in sorted(set(t['exitReason'] for t in closed)):
        ts=[t for t in closed if t['exitReason']==reason]
        xs=[extrema(by_id[t['eventId']],min(12,by_id[t['eventId']]['expectedBars'])) for t in ts]
        pre=[extrema(by_id[t['eventId']],t['holdingBars']) for t in ts]
        exit_groups[reason]={**performance(ts),'availableWindowMfe':stats([x['mfe'] for x in xs]),
                           'preExitMae':stats([x['mae'] for x in pre]),
                           'mfeCapture':stats([(t['netPct']+.05)/x['mfe'] for t,x in zip(ts,xs) if x['mfe']>0]),
                           'givebackPctPoints':stats([x['mfe']-(t['netPct']+.05) for t,x in zip(ts,xs)])}
    fby={t['eventId']:t for t in fixed['closedTrades']}
    cross=set(eqby)&set(fby)
    releases=[{'eventId':i,'earlierMinutes':(stamp(fby[i]['exitTimestamp'])-stamp(eqby[i]['exitTimestamp']))/60,
               'selectedUnitNet':eqby[i]['netPct'],'fixedUnitNet':fby[i]['netPct'],
               'selectedNotional':eqby[i]['entryNotionalJpy'],'fixedNotional':fby[i]['entryNotionalJpy']}
              for i in sorted(cross)]
    exit_attr={'reasons':exit_groups,'portfolioDeltaJpy':equal['finalEquityJpy']-fixed['finalEquityJpy'],
               'maxDDDeltaPctPoints':equal['maxDrawdownPct']-fixed['maxDrawdownPct'],'commonAccepted':len(cross),
               'acceptedSymmetricDifference':sorted(set(eqby)^set(fby)),
               'earlyReleaseMinutes':stats([r['earlierMinutes'] for r in releases]),
               'earlierReleases':sum(r['earlierMinutes']>0 for r in releases),
               'laterReleases':sum(r['earlierMinutes']<0 for r in releases),
               'unitLoserReductionPctPoints':sum(r['selectedUnitNet']-r['fixedUnitNet'] for r in releases if r['fixedUnitNet']<0),
               'selectedCashReleases':equal['capital']['cashReleaseCount'],'fixedCashReleases':fixed['capital']['cashReleaseCount'],
               'selectedSameTimeRecycling':equal['capital']['sameTimestampRecyclingEntries'],'fixedSameTimeRecycling':fixed['capital']['sameTimestampRecyclingEntries'],
               'perCommonTrade':releases,
               'winnerPreservation':{str(k):{arm:{'n':sum(extrema(by_id[i],min(12,by_id[i]['expectedBars']))['mfe']>=k for i in cross),
                                               'positiveNet':sum(extrema(by_id[i],min(12,by_id[i]['expectedBars']))['mfe']>=k and tr[i]['netPct']>0 for i in cross),
                                               'realizedAtLeastLevel':sum(extrema(by_id[i],min(12,by_id[i]['expectedBars']))['mfe']>=k and tr[i]['netPct']>=k for i in cross)}
                                           for arm,tr in [('LONG',eqby),('FIXED',fby)]} for k in [3,5]}}
    tiers=[]
    for r in inc:
        t=dict(r); label=r['opportunity30']; t['tier']='UNKNOWN' if label is None else str(max([0]+[k for k in [1,2,3,5] if label>=k])); tiers.append(t)
    selectors['opportunityTier30m']=group_performance(tiers,'tier',closed,equal['decisions'],by_id)
    diagnostics={'status':'LONG_PORTFOLIO_BOTTLENECK_DIAGNOSTIC_COMPLETE_NOT_VALIDATED',
                 'coverage':coverage,'concentration':concentration,'drawdown':dd,'selector':selectors,
                 'entry':entry,'allocation':alloc,'exit':exit_attr,'contractSHA':digest(CONTRACT),
                 'sourceMeasurementSHA':digest(BASE/'measurement.json.gz'),'sourceHead':contract['sourceHead'],
                 'frozenComponentChanges':0,'providerRequests':0,'freshConsumption':0,'oosAccess':0,'safety':contract['safety']}
    output=Path(output); output.mkdir(parents=True,exist_ok=True)
    for name,value in [('diagnostic.json',diagnostics),('sensitivity-ledgers.json.gz',sensitivity_ledgers)]:
        p=output/name; assert not p.exists()
        raw=(json.dumps(value,indent=2,allow_nan=False)+'\n').encode()
        p.write_bytes(gzip.compress(raw,mtime=0) if name.endswith('.gz') else raw)
    print(json.dumps({'stress':{k:{'final':v['finalEquityJpy'],'return':v['totalReturnPct'],'DD':v['maxDrawdownPct']} for k,v in stress.items()},
                      'coverageReasons':coverage['reasons'],'dd':ep,'alloc':{k:v for k,v in alloc.items() if k.endswith('Jpy')},
                      'selectorMonotonic':selectors['rankMeanPnlMonotonicBetterAtRank1'],'entryMonotonic':entry['meanNetReturnMonotonic']}))
    return diagnostics


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',default=str(OUT));run(p.parse_args().output)
