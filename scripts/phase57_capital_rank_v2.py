"""Precommitted Development-only Capital Rank v2; labels never enter rank input."""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import gzip
import hashlib
import json
import math
import statistics
from functools import lru_cache
from pathlib import Path

import numpy as np

from scripts import phase57_development_integrated_v0 as v0
from scripts import phase57_development_integrated_v1 as v1
from scripts import phase57_entry_pattern_v2 as pattern
from scripts import phase57_entry_timing_signals as timing
from scripts import phase57_state_v3_9pattern_entry_v1 as state
from scripts import phase57_exit_execution_contract_v1 as execution
from scripts import phase57_exit_feature_contract_v1 as registry
from scripts import phase57_exit_gen3_facts_r45 as facts

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'docs/evidence/phase57-comprehensive-exit-v1'
PROTOCOL = EVIDENCE / 'CAPITAL_RANK_V2_PRECOMMIT.json'
AUDIT = EVIDENCE / 'CAPITAL_RANK_V2_FEATURE_AUDIT.json'
PROTOCOL_SHA256 = '8b5f9eb1753a2967edd4991fc90bbff6e21898764d1fb13d3693572c72d335de'
AUDIT_SHA256 = '556d5f29e0a54f8878ffb4ae6f87ddd4e79d03a047a5581907c123707501a053'
WINDOW = EVIDENCE / 'CAPITAL_RANK_V2_SCORING_WINDOW_ADDENDUM.json'
WINDOW_SHA256 = '235de6fe8dd893410a134b1b48ba88ea563f66c30c73d75972dedd674f5d010b'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def contract():
    require(v0.digest(PROTOCOL) == PROTOCOL_SHA256 and v0.digest(AUDIT) == AUDIT_SHA256 and
            v0.digest(WINDOW) == WINDOW_SHA256,
            'RANK_V2_PRE_FIT_FREEZE_IDENTITY')
    p = json.loads(PROTOCOL.read_text())
    a = json.loads(AUDIT.read_text())
    w = json.loads(WINDOW.read_text())
    require(p['status'] == 'FROZEN_BEFORE_V2_FITTING_PREDICTION_ENRICHMENT_AND_PORTFOLIO_PERFORMANCE',
            'RANK_V2_NOT_FROZEN')
    for name, expected in p['inputs']['sha256ByPath'].items():
        require(v0.digest(ROOT / name) == expected, 'RANK_V2_SOURCE_HASH:' + name)
    require(p['features']['sets'] == a['admittedNamesByCandidate'] and
            len(a['pattern187']) == 187 and
            p['selection']['candidateIds'] == [f'CAPITAL_RANK_V2_{c}' for c in 'ABC'] and
            p['selection']['expectedFits'] == 24, 'RANK_V2_FINITE_SPACE')
    require(p['safety'] == v0.SAFETY and not any(v0.SAFETY.values()), 'RANK_V2_SAFETY9')
    require(w['basisPrecommitSha256']==PROTOCOL_SHA256 and w['sessionCount']==24 and
            w['portfolioSessions']==sorted({s for f in p['split']['folds'] for s in f['testSessions']}),
            'RANK_V2_OOF_WINDOW_IDENTITY')
    return p, a


def allowlisted_path_details(path, allowed):
    """Skip out-of-scope JSON values structurally before decode, like v0."""
    require(v0.digest(path) == v0.RAW_HASH, 'RANK_V2_RAW_PIN')
    text = gzip.decompress(Path(path).read_bytes()).decode()
    decoder = json.JSONDecoder()
    n = len(text)
    def ws(i):
        while i < n and text[i].isspace(): i += 1
        return i
    i = ws(0)
    require(text[i] == '{', 'RAW_NOT_OBJECT')
    i += 1
    result, seen, skipped = {}, set(), 0
    while True:
        i = ws(i)
        if text[i] == '}':
            require(ws(i+1) == n, 'RAW_TRAILING_CONTENT')
            break
        key, i = decoder.raw_decode(text, i)
        require(key not in seen, 'RAW_DUPLICATE_KEY')
        seen.add(key)
        i = ws(i)
        require(text[i] == ':', 'RAW_MISSING_COLON')
        i = ws(i+1)
        if key in allowed:
            row, i = decoder.raw_decode(text, i)
            require(set(row) >= {'today','previous','previousSession'} and
                    key.split('|')[0] > row['previousSession'], 'RAW_PRIOR_IDENTITY')
            result[key] = {k:row[k] for k in ('today','previous','previousSession')}
        else:
            skipped += 1
            i = v0.structural_value_end(text, i)
        i = ws(i)
        require(text[i] in ',}', 'RAW_SEPARATOR')
        if text[i] == ',': i += 1
    require(set(result) == allowed and len(seen) == 5375, 'RAW_ALLOWLIST_SCOPE')
    return result, skipped


def allowlisted_origin_details(path, allowed, expected):
    """Decode only frozen cohort origins; never import origin outcome payload."""
    require(v0.digest(path) == expected, 'RANK_ORIGIN_HASH')
    text = gzip.decompress(Path(path).read_bytes()).decode()
    dec = json.JSONDecoder()
    i = text.index('[') + 1
    result, seen = {}, set()
    while True:
        while text[i].isspace(): i += 1
        if text[i] == ']': break
        end = v0.structural_value_end(text, i)
        chunk = text[i:end]
        j = 1
        oid, projected = None, None
        while j < len(chunk)-1:
            while chunk[j].isspace() or chunk[j] == ',': j += 1
            key, j = dec.raw_decode(chunk, j)
            while chunk[j].isspace(): j += 1
            require(chunk[j] == ':', 'ORIGIN_COLON')
            j += 1
            while chunk[j].isspace(): j += 1
            stop = v0.structural_value_end(chunk, j)
            if key == 'id':
                oid = dec.raw_decode(chunk,j)[0]
                require(oid not in seen, 'ORIGIN_DUPLICATE')
                seen.add(oid)
            elif key == 'origin' and oid in allowed:
                raw = dec.raw_decode(chunk,j)[0]
                projected = {k:raw[k] for k in ('decisionPrice','decisionTimestamp','savedV1Score','newEligibleRank')}
            j = stop
        if oid in allowed:
            require(projected is not None and projected['decisionPrice'] > 0, 'ORIGIN_ALLOWED_MISSING')
            result[oid] = projected
        i = end
        while text[i].isspace(): i += 1
        require(text[i] in ',]', 'ORIGIN_SEPARATOR')
        if text[i] == ',': i += 1
    require(len(seen) == 5375 and set(result) == allowed, 'ORIGIN_ALLOWLIST_SCOPE')
    return result


def previous_active(day, now):
    minutes = execution.continuous_minutes(day)
    earlier = [m for m in minutes if m < now]
    return earlier[-1] if earlier else None


def make_features(intent, path, origin, feature_names, pattern_names):
    """Pure Entry-time facts. A future raw suffix cannot change this vector."""
    stamp = dt.datetime.fromisoformat(intent['timestamp'])
    day, now = stamp.date().isoformat(), stamp.hour*60+stamp.minute
    selector = dt.datetime.fromisoformat(origin['decisionTimestamp'])
    require(selector.date().isoformat() == day and selector <= stamp and
            intent['rankKnownAt'] == origin['decisionTimestamp'] and
            intent['entryKnownAt'] == intent['timestamp'], 'RANK_KNOWN_AFTER_ENTRY')
    require(set(intent) == {'entryId','symbol','timestamp','entryKnownAt',
                           'effectiveEntryPrice','newEligibleRank','savedV1Score',
                           'rankKnownAt','side','account'} and
            not set(intent) & set(_denylist()), 'OUTCOME_IN_RANK_INTENT')
    today = [row for row in path['today'] if row[0] + 1 <= now]
    require(all(r[0] + 1 <= now for r in today) and
            path['previousSession'] < day, 'FUTURE_SOURCE')
    previous = path['previous']
    price = float(intent['effectiveEntryPrice'])
    origin_price = float(origin['decisionPrice'])
    require(price > 0 and origin_price > 0, 'ENTRY_OR_SELECTOR_PRICE')
    out = {'selectorRank':float(intent['newEligibleRank']),
           'selectorScore':float(intent['savedV1Score']),
           'selectorPriceLog':math.log(origin_price), 'entryPriceLog':math.log(price),
           'entryVsSelectorPct':100*(price/origin_price-1),
           'activeDelay':float(state.active_elapsed(selector.hour*60+selector.minute,now)),
           'rankAge':float((stamp-selector).total_seconds()/60),
           'entryMinuteFraction':now/1440}
    if any(x not in out for x in feature_names):
        prev_now = previous_active(day,now)
        prior = [r for r in today if prev_now is not None and r[0]+1<=prev_now]
        present_state = state.classify_state_v3(day,now,today,previous,path['previousSession'])
        prior_state = (state.classify_state_v3(day,prev_now,prior,previous,path['previousSession'])
                       if prev_now is not None else None)
        a = present_state['state'] if present_state['dataQuality'] != 'INVALID' else None
        b = prior_state['state'] if prior_state and prior_state['dataQuality'] != 'INVALID' else None
        for label,value in (('stateNow',a),('statePrior',b)):
            for name in ('RISE','SHARP_RISE','REBOUND','DROP','PULLBACK','RANGE','SHARP_DROP','DROP_STOP','RISE_STOP'):
                out[f'{label}.{name}'] = None if value is None else float(value == name)
        out.update(stateValid=float(a is not None),statePriorValid=float(b is not None),
                   stateDwell=None if a is None or b is None else float(a == b),
                   stateChanged=None if a is None or b is None else float(a != b))
        history = {}
        recent_minutes = [m for m in execution.continuous_minutes(day) if m <= now][-5:]
        for minute in recent_minutes:
            prefix = [r for r in today if r[0]+1 <= minute]
            observed = timing.detect(day,minute,origin_price,
                                     np.asarray(prefix,dtype=float).reshape(-1,7),
                                     np.asarray(previous,dtype=float).reshape(-1,7),
                                     path['previousSession'])
            history[minute] = {name:observed['signals'][name]['trigger']
                               for name in registry.SIGNAL_FAMILIES}
        for name in registry.SIGNAL_FAMILIES:
            value = history[now][name]
            prior_value = history.get(prev_now,{}).get(name)
            tri = 'UNKNOWN' if value is None else ('TRUE' if value else 'FALSE')
            for category in ('TRUE','FALSE','UNKNOWN'):
                out[f'signal.{name}.{category}'] = float(tri == category)
            out[f'signal.{name}.recovery'] = (None if value is None or prior_value is None
                                               else float(prior_value is False and value is True))
            h = [row[name] for row in history.values()]
            out[f'signal.{name}.trueCount5'] = (float(sum(x is True for x in h))
                                                   if len(h)==5 and all(x is not None for x in h)
                                                   else None)
        out.update(facts.price_facts(day,now,today))
    if pattern_names:
        # Pattern-v2 original Entry producer supports selector==Entry; R23 EXIT
        # adapter's stricter selector<EXIT_NOW precondition does not apply here.
        recent = {name.split('/',1)[1]:None for name in registry_names()
                  if name.startswith('RECENT/')}
        values,_ = pattern.features(day,now,selector.hour*60+selector.minute,origin,
                                    np.asarray(today,dtype=float).reshape(-1,7),
                                    np.asarray(previous,dtype=float).reshape(-1,7),None,recent)
        out.update({'pattern.'+name:values[name] for name in pattern_names})
    require(set(feature_names) <= set(out), 'MISSING_PRECOMMITTED_FEATURE')
    result = [None if out[name] is None or
              isinstance(out[name],(float,np.floating)) and not math.isfinite(out[name])
              else out[name] for name in feature_names]
    require(all(x is None or isinstance(x,(int,float,np.integer,np.floating)) and math.isfinite(x)
                for x in result), 'NONNUMERIC_CAUSAL_FEATURE')
    result = [None if x is None else float(x) for x in result]
    return result


@lru_cache(maxsize=1)
def registry_names():
    return [x['feature'] for x in registry.pattern_rows()]


@lru_cache(maxsize=1)
def _denylist():
    return tuple(json.loads(PROTOCOL.read_text())['features']['deny'])


def load_inputs(ledger_path, r1_path, raw_path):
    p,a = contract()
    cohort,intents,evaluation,terminal,raw = v0.load_sources(ledger_path,r1_path,raw_path)
    allowed = {e['opportunity'] for arm in v0.ARMS for e in evaluation[arm].values()}
    paths,skipped = allowlisted_path_details(raw_path,allowed)
    require(skipped == 5375-len(allowed) and
            all({int(row[0]):row for row in paths[key]['today']}==raw[key] for key in allowed),
            'RAW_PROJECTION_PARITY')
    origins = allowlisted_origin_details(ROOT/'docs/evidence/phase57-entry-pattern-v2/ci-result/substrate/opportunities.json.gz',
                                         allowed,p['inputs']['sha256ByPath']['docs/evidence/phase57-entry-pattern-v2/ci-result/substrate/opportunities.json.gz'])
    labels = {}
    for arm in v0.ARMS:
        labels[arm] = {}
        for item in intents[arm]:
            eid = item['entryId']
            e = evaluation[arm][eid]
            # The frozen R50 evaluator excludes the Entry candle itself.
            future = [row[2] for row in paths[e['opportunity']]['today']
                      if int(row[0]) > e['entryMinute']]
            require(bool(future) and math.isclose(100*(max(future)/item['effectiveEntryPrice']-1),
                      e['postUpsidePct'],rel_tol=0,abs_tol=1e-7), 'FROZEN_HIGH_LABEL_PARITY')
            positive = e['postUpsidePct'] >= 5
            available = positive or terminal[arm][eid]['exitPrice'] is not None
            labels[arm][eid] = int(positive) if available else None
    return (p,a,cohort,intents,evaluation,terminal,raw,paths,origins,labels)


def support_only(data):
    p,_,cohort,intents,_,_,_,_,_,labels = data
    support = {}
    for arm in v0.ARMS:
        support[arm] = []
        for f in p['split']['folds']:
            tr = [labels[arm][x['entryId']] for x in intents[arm]
                  if x['timestamp'][:10] in f['trainSessions'] and labels[arm][x['entryId']] is not None]
            te = [labels[arm][x['entryId']] for x in intents[arm]
                  if x['timestamp'][:10] in f['testSessions']]
            require(len(tr)>=200 and sum(tr)>=20 and len(tr)-sum(tr)>=20 and
                    sum(x is not None for x in te)/len(te)>=0.97,
                    'PREFIT_SUPPORT:'+arm+':'+str(f['id']))
            support[arm].append({'fold':f['id'],'train':len(tr),'positive':sum(tr),
                                 'negative':len(tr)-sum(tr),'test':len(te),
                                 'testKnown':sum(x is not None for x in te)})
    return {'protocolSha256':PROTOCOL_SHA256,'featureAuditSha256':AUDIT_SHA256,
            'support':support,'sourceAllowlistedRaw':len(data[7]),
            'rawSkippedBeforeDecode':5375-len(data[7]),
            'modelFits':0,'portfolioReplays':0,'candidatePerformanceInspected':0,
            'protectedOpened':0,'providerRequests':0,'safety':p['safety']}


def feature_table(data, names):
    p,a,_,intents,evaluation,_,_,paths,origins,_ = data
    pattern_names = a['pattern187'] if any(n.startswith('pattern.') for n in names) else []
    rows = {}
    for arm in v0.ARMS:
        rows[arm] = {x['entryId']:make_features(x,paths[evaluation[arm][x['entryId']]['opportunity']],
                           origins[evaluation[arm][x['entryId']]['opportunity']],
                           names,pattern_names) for x in intents[arm]}
    return rows


def finite_oof(data):
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    p,a,cohort,intents,evaluation,terminal,raw,paths,origins,labels = data
    support = support_only(data)
    all_names = p['features']['sets']['C']
    table = feature_table(data,all_names)
    require(all(len(table[arm])==len(intents[arm]) for arm in v0.ARMS), 'FEATURE_COVERAGE')
    scores = {name:{arm:{} for arm in v0.ARMS} for name in p['selection']['candidateIds']}
    manifests = []
    for ci,(candidate,feature_set) in enumerate(zip(p['selection']['candidateIds'],p['selection']['candidateSets'])):
        names = p['features']['sets'][feature_set]
        columns = [all_names.index(name) for name in names]
        for arm in v0.ARMS:
            for f in p['split']['folds']:
                train = [x for x in intents[arm] if x['timestamp'][:10] in f['trainSessions']
                         and labels[arm][x['entryId']] is not None]
                test = [x for x in intents[arm] if x['timestamp'][:10] in f['testSessions']]
                X = np.asarray([[np.nan if table[arm][x['entryId']][j] is None else table[arm][x['entryId']][j]
                                 for j in columns] for x in train],dtype=float)
                Z = np.asarray([[np.nan if table[arm][x['entryId']][j] is None else table[arm][x['entryId']][j]
                                 for j in columns] for x in test],dtype=float)
                y = np.asarray([labels[arm][x['entryId']] for x in train],dtype=int)
                model = make_pipeline(SimpleImputer(strategy='constant',fill_value=0,add_indicator=True,
                                                    keep_empty_features=True),StandardScaler(),
                                      LogisticRegression(**p['model']['parameters']))
                model.fit(X,y)
                pred = model.predict_proba(Z)[:,1]
                require(len(pred)==len(test) and np.isfinite(pred).all(), 'PREDICTION_INVALID')
                for row,prob in zip(test,pred):
                    require(row['entryId'] not in scores[candidate][arm], 'DUPLICATE_OOF_ENTRY')
                    scores[candidate][arm][row['entryId']]=float(prob)
                manifests.append({'candidate':candidate,'arm':arm,'fold':f['id'],
                                  'train':len(train),'test':len(test),'positive':int(y.sum())})
    require(len(manifests)==24,'FIT_COUNT')
    return scores,manifests,support


def ranked_enrichment(arm, intents, evaluation, labels, subset, score=None):
    events = collections.defaultdict(list)
    for x in intents:
        if x['timestamp'][:10] in subset:
            events[x['timestamp']].append(x)
    chosen = {n:[] for n in (1,3,5)}
    for event,items in sorted(events.items()):
        if score is None: items.sort(key=v0.event_priority)
        else: items.sort(key=lambda x:(-score[x['entryId']],)+v0.event_priority(x))
        for n in chosen: chosen[n].extend(items[:n])
    available = [x for x in intents if x['timestamp'][:10] in subset and
                 labels[x['entryId']] is not None]
    baseline = sum(labels[x['entryId']] for x in available)/len(available)
    result = {'totalKnown':len(available),'totalCandidates':sum(map(len,events.values())),
              'baselineHitRate':baseline,'top':{}}
    for n,items in chosen.items():
        known=[x for x in items if labels[x['entryId']] is not None]
        hit=sum(labels[x['entryId']] for x in known)
        total_hit=sum(labels[x['entryId']] for x in available)
        upsides=[evaluation[x['entryId']]['postUpsidePct'] for x in known]
        symbol=collections.Counter(x['symbol'] for x in items)
        session=collections.Counter(x['timestamp'][:10] for x in items)
        result['top'][str(n)]={'selected':len(items),'knownSelected':len(known),
                'hit':hit,'hitRate':hit/len(known) if known else None,
                'baseline':baseline,'enrichment':hit/len(known)/baseline if known else None,
                'reach':hit/total_hit if total_hit else None,'miss':total_hit-hit,
                'canonicalHits':sum(evaluation[x['entryId']]['canonicalBucket']=='>=5%' for x in items),
                'upsideMeanPct':statistics.fmean(upsides) if upsides else None,
                'upsideMedianPct':statistics.median(upsides) if upsides else None,
                'upsideP25Pct':v0.percentile(upsides,.25),'upsideP75Pct':v0.percentile(upsides,.75),
                'upsideP90Pct':v0.percentile(upsides,.9),
                'upsideGe7_5Rate':sum(z>=7.5 for z in upsides)/len(known) if known else None,
                'upsideGe10Rate':sum(z>=10 for z in upsides)/len(known) if known else None,
                'symbolTopShare':max(symbol.values())/len(items) if items else None,
                'sessionTopShare':max(session.values())/len(items) if items else None}
    return result


def score_and_select(data, scores):
    p,_,_,intents,evaluation,_,_,_,_,labels=data
    sessions={s for f in p['split']['folds'] for s in f['testSessions']}
    control={arm:ranked_enrichment(arm,intents[arm],evaluation[arm],labels[arm],sessions)
             for arm in v0.ARMS}
    cards={}
    for candidate in p['selection']['candidateIds']:
        cards[candidate]={}
        for arm in v0.ARMS:
            card=ranked_enrichment(arm,intents[arm],evaluation[arm],labels[arm],sessions,scores[candidate][arm])
            folds=[]
            for f in p['split']['folds']:
                test=set(f['testSessions'])
                control_fold=ranked_enrichment(arm,intents[arm],evaluation[arm],labels[arm],test)['top']['3']['hitRate']
                model_fold=ranked_enrichment(arm,intents[arm],evaluation[arm],labels[arm],test,scores[candidate][arm])['top']['3']['hitRate']
                folds.append({'fold':f['id'],'control':control_fold,'candidate':model_fold})
            card['foldComparison']=folds
            cards[candidate][arm]=card
    gate=p['selection']['gate']
    verdict={}
    for candidate,by_arm in cards.items():
        failures=[]
        for arm in v0.ARMS:
            c=by_arm[arm];ref=control[arm]
            top=c['top']['3'];rtop=ref['top']['3'];top1=c['top']['1'];r1=ref['top']['1']
            criteria={
              'top3_absolute':top['enrichment']>=gate['top3EnrichmentBothArmsMin'],
              'top3_control_delta':top['enrichment']-rtop['enrichment']>=gate['top3VsControlBothArmsMinDelta'],
              'top3_reach':top['reach']>=rtop['reach']-gate['top3ReachMinControlMinus'],
              'top1_control':top1['enrichment']>=r1['enrichment']-gate['top1EnrichmentMinControlMinus'],
              'fold_noninferior':sum(f['candidate']>=f['control'] for f in c['foldComparison'])>=gate['nonInferiorFoldTop3HitRateMinOf4'],
              'fold_strict':sum(f['candidate']>f['control'] for f in c['foldComparison'])>=gate['strictImproveFoldTop3HitRateMinOf4'],
              'symbol_concentration':top['symbolTopShare']<=rtop['symbolTopShare']+gate['symbolTopShareMaxControlPlus'],
              'session_concentration':top['sessionTopShare']<=rtop['sessionTopShare']+gate['sessionTopShareMaxControlPlus'],
              'label_coverage':c['totalKnown']/c['totalCandidates']>=gate['labelCoverageMin'],
              'all_predictions':len(scores[candidate][arm])==c['totalCandidates']}
            failures.extend(arm+':'+name for name,ok in criteria.items() if not ok)
        verdict[candidate]={'pass':not failures,'failed':failures}
    selected=select_from_gate(verdict,cards)
    return {'control':control,'candidates':cards,'gate':verdict,'selected':selected,
            'status':'SELECT' if selected else 'NO_SELECTION_STOP',
            'evaluationOnly':True,'sessions':sorted(sessions)}


def select_from_gate(verdict, cards):
    passing=[k for k,v in verdict.items() if v['pass']]
    if len(passing)==1:return passing[0]
    if len(passing)<2:return None
    values={k:min(cards[k][arm]['top']['3']['enrichment'] for arm in v0.ARMS)
            for k in passing}
    best=max(values.values())
    winners=[k for k,v in values.items() if v==best]
    return winners[0] if len(winners)==1 else None


def daily_reporting(ledger):
    """Refuse a continuous daily/compound return if any equity point is null."""
    curves=v1.curve(ledger)
    groups=collections.defaultdict(list)
    for row in curves:groups[row['timestamp'][:10]].append(row)
    daily=[]
    previous_end='1000000'
    for day,rows in sorted(groups.items()):
        valid=all(r['equityValid'] and r['equityJpy'] is not None for r in rows)
        start=previous_end
        end=rows[-1]['equityJpy']
        if not valid or start is None or end is None:
            daily.append({'session':day,'startEquityJpy':None if start is None else str(start),
                          'endEquityJpy':None if end is None else str(end),
                          'dailyReturnPct':None,'valid':False})
            previous_end=None
            continue
        daily.append({'session':day,'startEquityJpy':str(start),'endEquityJpy':str(end),
                      'dailyReturnPct':100*(float(end)/float(start)-1),'valid':True})
        previous_end=end
    if not all(r['valid'] for r in daily) or ledger['endOpenEntryIds']:
        return {'daily':daily,'meanPct':None,'medianPct':None,'geometricPct':None,
                'portfolioReturnPct':None,'mechanicalCompoundingPct':None,
                'reason':'NULL_EQUITY_OR_UNRESOLVED_END_POSITION'}
    rates=[r['dailyReturnPct'] for r in daily]
    geometric=100*((float(daily[-1]['endEquityJpy'])/1000000)**(1/len(daily))-1)
    return {'daily':daily,'meanPct':statistics.fmean(rates),
            'medianPct':statistics.median(rates),'geometricPct':geometric,
            'stdPct':statistics.stdev(rates) if len(rates)>1 else None,
            'positiveDayRate':sum(x>0 for x in rates)/len(rates),
            'negativeDayRate':sum(x<0 for x in rates)/len(rates),
            'bestDayPct':max(rates),'worstDayPct':min(rates),
            'p05DailyPct':v0.percentile(rates,.05),'p10DailyPct':v0.percentile(rates,.10),
            'portfolioReturnPct':100*(float(daily[-1]['endEquityJpy'])/1000000-1),
            'mechanicalCompoundingPct':{str(n):100*((1+geometric/100)**n-1) for n in (20,60,120,240)}}


def portfolio_window(data, scores, selected, output_dir):
    """Only OOF test sessions; six frozen cash variants; labels stay evaluator-only."""
    _,_,cohort,intents,evaluation,terminal,raw,_,_,_=data
    window=json.loads(WINDOW.read_text())['portfolioSessions']
    chosen=set(window)
    require(len(chosen)==24 and sorted(chosen)==window,'PORTFOLIO_OOF_WINDOW')
    subset_cohort={**cohort,'sessions':window}
    cards={}
    all_missing=[]
    for arm in v0.ARMS:
        entry_rows=[dict(x) for x in intents[arm] if x['timestamp'][:10] in chosen]
        for row in entry_rows:
            require(row['timestamp']==row['entryKnownAt'] and
                    dt.datetime.fromisoformat(row['rankKnownAt']) <=
                    dt.datetime.fromisoformat(row['timestamp']), 'RANK_KNOWN_AFTER_ENTRY')
        if selected is not None:
            score=scores[selected][arm]
            by_timestamp=collections.defaultdict(list)
            for row in entry_rows:
                require(row['entryId'] in score,'NO_OOF_PREDICTION_FOR_ENTRY')
                by_timestamp[row['timestamp']].append(row)
            for stamp,group in by_timestamp.items():
                for index,row in enumerate(sorted(group,key=lambda x:
                                                  (-score[x['entryId']],)+v0.event_priority(x)),1):
                    row['newEligibleRank']=index
                    row['rankKnownAt']=stamp  # this OOF prediction exists at Entry NOW
        eval24={eid:x for eid,x in evaluation[arm].items() if x['session'] in chosen}
        exits24={eid:x for eid,x in terminal[arm].items() if eid in eval24}
        require(len(eval24)==len(entry_rows)==len(exits24),'PORTFOLIO_ENTRY_COHORT')
        for cap in (3,4,5):
            key=('IM' if arm==v0.IM else 'R1')+'_MAX'+str(cap)
            ledger=v1.replay(arm,cap,subset_cohort,entry_rows,exits24,raw)
            card=v1.card(ledger,eval24,subset_cohort)
            curve=v1.curve(ledger)
            daily=daily_reporting(ledger)
            dates=sorted({r['session'] for r in ledger['snapshots']})
            funded_days=sorted({r['session'] for r in ledger['funded'].values()})
            valid_days=sorted({r['session'] for r in ledger['snapshots']
                               if all(s['equityValid'] for s in ledger['snapshots']
                                      if s['session']==r['session'])})
            card['timeCoverage']={'firstEvaluationTimestamp':curve[0]['timestamp'],
                'lastEvaluationTimestamp':curve[-1]['timestamp'],
                'calendarSpanDays':(dt.date.fromisoformat(dates[-1])-
                                    dt.date.fromisoformat(dates[0])).days+1,
                'tradingSessions':len(dates),'fundedSessions':len(funded_days),
                'validEquitySessions':len(valid_days),
                'excludedOrNullSessions':len(dates)-len(valid_days),
                'intradayObservation':'09:00 and Entry event marks through 15:30 auction; lunch and auction only where event grid includes them',
                'distinctDates':dates}
            card['rankSource']=selected or 'EXISTING_R35_CAUSAL_CONTROL'
            card['exitStatus']='TERMINAL_HOLD_BENCHMARK_FINAL_EXIT_NOT_SELECTED'
            card['developmentOutcomeExposed']=True
            card['notFreshOosOrLiveEstimate']=True
            cards[key]={'scorecard':card,'daily':daily}
            folder=output_dir/key
            folder.mkdir(parents=True,exist_ok=True)
            (folder/'ledger.json.gz').write_bytes(gzip.compress(v0.canonical(ledger),mtime=0))
            (folder/'curve.json').write_bytes(v0.canonical(curve))
            (folder/'daily.json').write_bytes(v0.canonical(daily))
            all_missing.extend({'variant':key,**item} for item in ledger['missingReferences'])
    (output_dir/'portfolio-scorecards.json').write_bytes(v0.canonical(cards))
    (output_dir/'all-missing-references.json.gz').write_bytes(
        gzip.compress(v0.canonical(all_missing),mtime=0))
    plot_curves(output_dir)
    return {'status':'SIX_VARIANT_PORTFOLIO_REPLAY_FINISHED',
            'rank':selected or 'EXISTING_R35_CAUSAL_CONTROL',
            'sessions':window,'sessionCount':len(window),
            'scorecardPath':'portfolio-scorecards.json',
            'missingReferenceCount':len(all_missing),
            'fullPeriodDailyReturnsValidVariants':sum(x['daily']['geometricPct'] is not None
                                                       for x in cards.values()),
            'cardSummary':{name:{'portfolioReturnPct':x['scorecard']['portfolioReturnPct'],
                                 'valuationCoverage':x['scorecard']['valuationEventCoverage'],
                                 'nullSessions':x['scorecard']['timeCoverage']['excludedOrNullSessions'],
                                 'dailyGeoPct':x['daily']['geometricPct']} for name,x in cards.items()}}


def plot_curves(output_dir):
    """Gap-preserving diagnostic figures, never interpolate null valuation."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    views=[('IM_MAX345',['IM_MAX3','IM_MAX4','IM_MAX5']),
           ('R1_MAX345',['R1_MAX3','R1_MAX4','R1_MAX5']),
           ('MAX3_IM_VS_R1',['IM_MAX3','R1_MAX3'])]
    for name,variants in views:
        fig,ax=plt.subplots(figsize=(12,4))
        for variant in variants:
            curve=json.loads((output_dir/variant/'curve.json').read_text())
            ys=[float(x['equityJpy']) if x['equityJpy'] is not None else float('nan')
                for x in curve]
            ax.plot(range(len(curve)),ys,label=variant,linewidth=1.3)
        ax.set(xlabel='Event observation (null gaps retained)',ylabel='Equity JPY',
               title='Development 24 OOF trading sessions — terminal benchmark; not Final EXIT')
        ax.legend()
        fig.tight_layout()
        fig.savefig(output_dir/(name+'.png'),dpi=130)
        plt.close(fig)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--r1-records',required=True)
    parser.add_argument('--benchmark-ledger',required=True)
    parser.add_argument('--mode',choices=('preflight','finite'),required=True)
    parser.add_argument('--out',required=True)
    args=parser.parse_args()
    raw=ROOT/'docs/evidence/phase57-entry-pattern-v2/ci-result/substrate/raw-paths-evaluator-only.json.gz'
    data=load_inputs(args.benchmark_ledger,args.r1_records,raw)
    report=support_only(data)
    if args.mode=='preflight':
        features=feature_table(data,data[0]['features']['sets']['C'])
        report['fullFeatureRowsByArm']={arm:len(features[arm]) for arm in v0.ARMS}
        report['featureDimensions']=len(data[0]['features']['sets']['C'])
        report['featureMatrixSha256']=hashlib.sha256(v0.canonical(features)).hexdigest()
    if args.mode=='finite':
        scores,manifest,_=finite_oof(data)
        result=score_and_select(data,scores)
        report.update(result=result,modelFits=len(manifest),fitManifest=manifest,
                      scoreSha256=hashlib.sha256(v0.canonical(scores)).hexdigest())
        require(report['modelFits']==24,'MODEL_FIT_COUNT')
        target=Path(args.out).parent
        target.mkdir(parents=True,exist_ok=True)
        (target/'rank-scores.json').write_bytes(v0.canonical(scores))
        report['portfolio']=portfolio_window(data,scores,result['selected'],target)
    path=Path(args.out)
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_bytes(v0.canonical(report))
    print(json.dumps({'protocolSha256':PROTOCOL_SHA256,'modelFits':report['modelFits'],
                      'status':report.get('result',{}).get('status','PREFLIGHT_ONLY'),
                      'out':str(path)},sort_keys=True))


if __name__=='__main__':main()
