"""One finite historical reference diagnostic for the frozen target family.

This script never calls a provider, allocator, estimator, order path, or another
EXIT policy. Run --self-test before --run. A RUN_STARTED marker makes a repeated
market-outcome invocation an explicit budget error.
"""
from __future__ import annotations

import argparse
import collections
import gzip
import hashlib
import json
import math
import re
import statistics
import zipfile
from decimal import Decimal
from pathlib import Path

import numpy as np

from scripts import phase57_development_integrated_v0 as v0
from scripts import phase57_exit_execution_contract_v1 as execution
from scripts.phase57_profit_target_precommit import (
    ROOT, OUT, SOURCE, ARM, TARGETS, SAFETY, canonical, digest, jst, check, sha,
)

FEE = Decimal('0.0005')
E = Decimal


def write(name, value):
    path = OUT / name
    check(not path.exists(), 'RESULT_EXISTS_NO_OVERWRITE:' + name)
    path.write_bytes(canonical(value))


def rows_gz(name, rows):
    p = OUT / name
    check(not p.exists(), 'RESULT_EXISTS_NO_OVERWRITE:' + name)
    with p.open('wb') as stream:
        with gzip.GzipFile(fileobj=stream, mode='wb', mtime=0) as g:
            for row in rows:
                g.write(canonical(row))


def read_gz(path):
    with gzip.open(path, 'rt') as stream:
        return [json.loads(line) for line in stream]


def price_ok(row, minute):
    if row is None or len(row) != 7 or row[0] != minute:
        return False
    if not all(isinstance(x, (int, float)) and not isinstance(x, bool) and
               math.isfinite(x) for x in row):
        return False
    o, h, l, c, vol, val = row[1:]
    return o > 0 and l > 0 and l <= min(o, c) <= max(o, c) <= h and vol >= 0 and val >= 0


def pnl(fill, qty, cost, fee=FEE):
    if fill is None:
        return None
    return E(qty) * E(str(fill)) - E(cost) * (1 + fee)


def pct(profit, cost):
    return None if profit is None else float(100 * profit / E(cost))


def valid_bars(raw, day, entry_minute):
    allowed = set(execution.continuous_minutes(day))
    actual = {}
    invalid = []
    for m, row in raw.items():
        if m not in allowed and m != 930:
            invalid.append(m)
            continue
        if not price_ok(row, m):
            invalid.append(m)
            continue
        if m >= entry_minute:
            actual[m] = row
    return actual, invalid


def first_close_hit(bars, minutes, entry_price, x):
    """Scan only fresh, completed observations; no high or future input."""
    for m in minutes:
        row = bars.get(m)
        if row is not None and 100 * (row[4] / entry_price - 1) >= x:
            return m + 1, row
    return None, None


def reach(bars, expected, entry_price, x, strict=False):
    obs = [bars[m][2] for m in expected if m in bars]
    hit = any(100 * (high / entry_price - 1) >= x for high in obs)
    missing = len(expected) - len(obs)
    return ('CONFIRMED_REACH' if hit else 'CERTIFIED_NONREACH' if not missing
            else 'UNKNOWN'), (max(obs) / entry_price - 1) * 100 if obs else None, missing


def market_row(arm, x, entry, r50, bars, invalid, funded, riskset, replacement):
    eid, day = entry['entryId'], entry['session']
    em, cp = entry['entryMinute'], entry['entryPrice']
    minutes = [m for m in execution.continuous_minutes(day) if m >= em]
    decision = r50['decisionNow']
    before = [m for m in minutes if m + 1 <= decision]
    whole_status = {}
    whole_high = None
    control_high = None
    missing_control = None
    for z in TARGETS:
        whole_status[z] = reach(bars, minutes, cp, z)[0]
    owned_high = max((bars[m][2] for m in minutes if m in bars), default=None)
    legacy_high = max((bars[m][2] for m in minutes if m > em and m in bars), default=None)
    ctrl_owned = [m for m in minutes if m < (r50['exitMinute'] or 930)]
    control_high = max((bars[m][2] for m in ctrl_owned if m in bars), default=None)
    control_missing = len(ctrl_owned) - sum(m in bars for m in ctrl_owned)
    tau, trigger = first_close_hit(bars, before, cp, x)
    later_tau, _ = first_close_hit(bars, minutes, cp, x)
    tie = tau == decision
    prior_intent = tau is not None and tau < decision
    ref_minute = execution.next_execution_start(day, tau) if prior_intent else None
    ref = bars.get(ref_minute) if ref_minute is not None else None
    ref_known = ref_minute is not None and ref is not None
    if prior_intent:
        choice = 'TARGET' if ref_known else 'TARGET_FIRST_REFERENCE_UNRESOLVED'
        fill = ref[1] if ref_known else None
        fill_minute = ref_minute
    else:
        choice = 'R50'
        fill = r50['exitPrice']
        fill_minute = r50['exitMinute']
    price_ref = r50['exitPrice']
    future_label = entry['futureUpsidePctEvaluatorOnly']
    base = {'arm': arm, 'targetPct': x, 'entryId': eid, 'session': day,
            'symbol': entry['symbol'], 'entryMinute': em, 'effectiveEntryPrice': cp,
            'entryCost100Jpy': entry['entryCostJpy'], 'funded': funded is not None,
            'fundedQuantity': funded['quantity'] if funded else None,
            'fundedCostJpy': funded['notionalJpy'] if funded else None,
            'initialOrReplacement': 'REPLACEMENT' if replacement else 'INITIAL',
            'sameTimestampRiskset': riskset,
            'r50DecisionMinute': decision, 'r50FillMinute': r50['exitMinute'],
            'r50ExitKind': r50['exitKind'], 'r50FillPrice': price_ref,
            'r50OutcomeKnown': price_ref is not None,
            'hypotheticalSameDayEntryBarIncludedHighPct': 100 * (owned_high / cp - 1) if owned_high else None,
            'legacyStrictHighPct': 100 * (legacy_high / cp - 1) if legacy_high else None,
            'observedHighReachedX': whole_status[x],
            'observedHighBeforeR50DecisionPct': 100 * (control_high / cp - 1) if control_high else None,
            'controlOwnedMissingBars': control_missing,
            'wholeExpectedBars': len(minutes), 'wholeObservedBars': sum(m in bars for m in minutes),
            'invalidPathMinutes': invalid,
            'firstObservedClosedTargetNow': later_tau,
            'firstClosedTargetBeforeR50Intent': prior_intent,
            'sameTimeControlDelegation': tie,
            'targetExecutionReferenceKnown': ref_known if prior_intent else None,
            'targetReferenceMinute': ref_minute,
            'targetReferencePrice': ref[1] if ref_known else None,
            'choice': choice, 'candidateFillMinute': fill_minute,
            'candidateFillPrice': fill,
            'targetOutcomeKnown': fill is not None,
            'overshootClosePct': 100 * (trigger[4] / cp - 1) - x if trigger else None,
            'triggerToFillWallMinutes': fill_minute - tau if prior_intent and fill_minute else None,
            'triggerToFillActiveMinutes': execution.active_minutes(day, tau, fill_minute)
                 if prior_intent and fill_minute else None,
            'triggerToFillPricePct': 100 * (fill / trigger[4] - 1)
                 if prior_intent and fill is not None else None,
            'futureUpsidePctEvaluatorOnly': future_label,
            'ccmgFirstIntentMinute': entry['ccmgFirstIntentMinute'],
            'savedCcmgVsR50DeltaJpyEvaluatorOnly': entry['deltaPnlJpy'],
            'anyObservedHighReached': {str(z): whole_status[z] for z in TARGETS}}
    for scope, q, cost in [('100', 100, E(entry['entryCostJpy'])),
                            ('actual', funded['quantity'] if funded else None,
                             E(funded['notionalJpy']) if funded else None)]:
        refp = pnl(price_ref, q, cost) if q else None
        candp = pnl(fill, q, cost) if q else None
        base[scope] = {'quantity': q, 'costJpy': str(cost) if cost is not None else None,
                       'r50PnlJpy': str(refp) if refp is not None else None,
                       'candidatePnlJpy': str(candp) if candp is not None else None,
                       'r50NetPct': pct(refp, cost) if cost is not None else None,
                       'candidateNetPct': pct(candp, cost) if cost is not None else None,
                       'deltaJpy': str(candp - refp) if candp is not None and refp is not None else None,
                       'deltaNetPp': pct(candp - refp, cost)
                           if candp is not None and refp is not None else None}
        if q and candp is not None and refp is not None:
            check(abs((candp - refp) - E(q) *
                      (E(str(fill)) - E(str(price_ref)))) < E('0.000001'),
                  'PRICE_DIFFERENCE_IDENTITY:' + eid)
    base['targetNetBelowX'] = (base['100']['candidateNetPct'] < x
                               if prior_intent and fill is not None else None)
    return base


def load_verified():
    pre = json.loads((OUT / 'MEASUREMENT_PRECOMMIT.json').read_text())
    check(digest(OUT / 'MEASUREMENT_PRECOMMIT.json') ==
          (OUT / 'MEASUREMENT_PRECOMMIT.sha256').read_text().split()[0], 'PRECOMMIT_HASH')
    for name, key in [('SOURCE_MANIFEST.json', 'sourceManifestSha256'),
                      ('ENTRY_ALLOWLIST.json', 'entryAllowlistSha256'),
                      ('POLICY_SPEC.json', 'policySpecSha256'),
                      ('BUDGET_LEDGER.json', 'budgetSha256'),
                      ('BOOTSTRAP_SPEC.json', 'bootstrapSpecSha256'),
                      ('TARGET_FEATURE_REGISTRY.json', 'featureRegistrySha256'),
                      ('SESSION_DRAWS.npz', 'drawSha256')]:
        check(digest(OUT / name) == pre[key], 'FROZEN_FILE_DRIFT:' + name)
    manifest = json.loads((OUT / 'SOURCE_MANIFEST.json').read_text())
    for name, info in manifest['pins'].items():
        check(digest(ROOT / info['path']) == info['sha256'], 'SOURCE_DRIFT:' + name)
    allowlist = json.loads((OUT / 'ENTRY_ALLOWLIST.json').read_text())
    entries = {a: {} for a in ARM}
    for row in read_gz(ROOT / SOURCE['phaseAAccounting']):
        if row['world'] == 'ALL_100':
            entries[row['arm']][row['entryId']] = row
    check(all(set(entries[a]) == set(allowlist[a]) for a in ARM), 'ENTRY_ALLOWLIST_DRIFT')
    with zipfile.ZipFile(ROOT / SOURCE['integrationZip']) as z:
        ledgers = {a: json.loads(gzip.decompress(z.read(f'{a}_V3_B_R50_A_ledger.json.gz')))
                   for a in ARM}
    raw_allow = {r['opportunityId'] for a in ARM for r in entries[a].values()}
    raw, skipped = v0.allowlisted_raw_paths(ROOT / SOURCE['rawPath'], raw_allow)
    check(set(raw) == raw_allow and skipped == 5375 - len(raw_allow), 'RAW_ALLOWLIST_SCOPE')
    arm_re = re.compile(r'"entryArm":"([^"]+)"')
    id_re = re.compile(r'"entryId":"([^"]+)"')
    controls = {a: {} for a in ARM}
    with gzip.open(ROOT / SOURCE['r50Archive'], 'rt') as stream:
        for line in stream:
            ma, mi = arm_re.search(line), id_re.search(line)
            check(ma is not None and mi is not None, 'R50_SCHEMA')
            a, eid = next((k for k,v in ARM.items() if v==ma.group(1)), None), mi.group(1)
            if a not in ARM or eid not in entries[a]:
                continue
            r = json.loads(line)
            check(eid not in controls[a] and r['decisionNow'] ==
                  entries[a][eid]['controlDecisionMinute'] and r['exitPrice'] ==
                  entries[a][eid]['controlExitPrice'], 'R50_JOIN')
            controls[a][eid] = r
    check(all(set(controls[a]) == set(entries[a]) for a in ARM), 'R50_SCOPE')
    # Verify every saved R50 exact execution reference independently of target.
    for a in ARM:
        for eid, r in controls[a].items():
            bar = raw[entries[a][eid]['opportunityId']]
            if r['exitKind'] == 'MODEL_EXIT':
                expected = execution.next_execution_start(r['session'], r['decisionNow'])
                check(expected == r['exitMinute'] and
                      (bar.get(expected, [None, None])[1] if expected in bar else None)
                      == r['exitPrice'], 'CONTROL_OPEN_REFERENCE:' + eid)
            else:
                check(r['exitKind'] == 'FORCED_TERMINAL' and r['decisionNow'] == 925,
                      'CONTROL_TERMINAL_CLOCK:' + eid)
                auction = bar.get(930)
                check((auction[1] if auction else None) == r['exitPrice'],
                      'CONTROL_AUCTION_REFERENCE:' + eid)
    # Two arm-level saved-control checks. There is no new control policy replay.
    for a in ARM:
        for eid, e in entries[a].items():
            expected=pnl(controls[a][eid]['exitPrice'],100,E(e['entryCostJpy']))
            saved=e['normalizedControlPnlJpy']
            check((expected is None and saved is None) or
                  (expected is not None and saved is not None and
                   abs(expected-E(saved))<E('0.000001')),
                  'R34_SAVED_CONTROL_ACCOUNTING:' + eid)
        closed={v['entryId']:v for v in ledgers[a]['closed']}
        for eid, f in ledgers[a]['funded'].items():
            if eid not in closed:
                check(eid in ledgers[a]['unresolvedEntryIds'],'FUNDED_UNRESOLVED')
                continue
            expected=pnl(controls[a][eid]['exitPrice'],f['quantity'],E(f['notionalJpy']))
            check(abs(expected-E(closed[eid]['realizedPnlJpy']))<E('0.000001'),
                  'R34_SAVED_FUNDED_ACCOUNTING:' + eid)
    return pre, entries, ledgers, controls, raw, skipped


def self_test():
    day = '2025-07-22'
    entry = {'entryId':'2025-07-22|X|540','session':day,'symbol':'X',
             'entryMinute':540,'entryPrice':100.0,'entryCostJpy':'10000',
             'futureUpsidePctEvaluatorOnly':None,'ccmgFirstIntentMinute':None,
             'deltaPnlJpy':None}
    base = {'decisionNow':545,'exitMinute':545,'exitPrice':101.0,'exitKind':'MODEL_EXIT'}
    bar = lambda m, high, close: [m, 100., high, 99., close, 0., 0.]
    bars = {540:bar(540,104,102),541:bar(541,104,103),542:bar(542,103,100)}
    # Threshold hit is from completed close; high-only is evaluator observation.
    r = market_row('IM',3,entry,base,bars,[],None,False,False)
    check(r['firstObservedClosedTargetNow']==542 and r['choice']=='TARGET' and
          r['targetReferenceMinute']==542 and r['candidateFillPrice']==100., 'TARGET_OPEN_ONLY')
    q = market_row('IM',4,entry,base,bars,[],None,False,False)
    check(q['choice']=='R50' and q['observedHighReachedX']=='CONFIRMED_REACH', 'HIGH_NOT_CLOSE')
    missing = market_row('IM',3,entry,base,{540:bars[540],541:bars[541]},[],None,False,False)
    check(missing['choice']=='TARGET_FIRST_REFERENCE_UNRESOLVED' and
          missing['100']['candidatePnlJpy'] is None, 'MISSING_OPEN_UNKNOWN')
    tied = market_row('IM',2,entry,{**base,'decisionNow':541,'exitMinute':541},bars,[],None,False,False)
    check(tied['choice']=='R50' and tied['sameTimeControlDelegation'], 'TIE_DELEGATION')
    early = market_row('IM',3,entry,{**base,'decisionNow':541,'exitMinute':541},bars,[],None,False,False)
    check(early['choice']=='R50', 'R50_FIRST')
    check(pnl(103,100,'10000')-pnl(101,100,'10000')==E(200), 'COST_CANCELLATION')
    check(execution.next_execution_start(day, 690)==750 and
          execution.next_execution_start(day,925) is None, 'SCHEDULE')
    check(reach({540:bars[540]},[540,541],100,5)[0]=='UNKNOWN', 'CENSORING')
    try:
        check(11 in TARGETS, 'TARGET_BUDGET_REJECT')
    except ValueError:
        pass
    else:
        raise AssertionError('TARGET_BUDGET_CANARY')
    print('Synthetic target, tie, reference, lunch, high, accounting, censoring PASS')


def scopes(rows):
    return {
        'ALL_ENTRY_100': (rows, '100'),
        'R50_FUNDED_ACTUAL': ([r for r in rows if r['funded']], 'actual'),
        'R50_FUNDED_100': ([r for r in rows if r['funded']], '100'),
        'R50_NOT_FUNDED_100': ([r for r in rows if not r['funded']], '100'),
        'SAME_TIMESTAMP_ELIGIBLE_RISKSET':
            ([r for r in rows if r['sameTimestampRiskset']], '100'),
    }


def mean(values):
    return sum(values)/len(values) if values else None


def measure(subset, quantity_key, common_ids=None):
    total = len(subset)
    known = [r for r in subset if r[quantity_key]['deltaJpy'] is not None]
    if common_ids is not None:
        known = [r for r in known if r['entryId'] in common_ids]
    target = [r for r in known if r['choice']=='TARGET']
    delegate = [r for r in known if r['choice']=='R50']
    change = [float(r[quantity_key]['deltaJpy']) for r in known]
    apnl = [float(r[quantity_key]['candidatePnlJpy']) for r in known]
    bpnl = [float(r[quantity_key]['r50PnlJpy']) for r in known]
    anet = [r[quantity_key]['candidateNetPct'] for r in known]
    bnet = [r[quantity_key]['r50NetPct'] for r in known]
    dp = [r[quantity_key]['deltaNetPp'] for r in known]
    check(abs(sum(change)-sum(float(r[quantity_key]['deltaJpy']) for r in target))<1e-6,
          'DELTA_DECOMPOSITION')
    if known:
        weighted = (len(target)*mean([r[quantity_key]['candidateNetPct'] for r in target])
                    if target else 0) + (len(delegate)*mean([
                    r[quantity_key]['candidateNetPct'] for r in delegate]) if delegate else 0)
        check(abs(mean(anet)-weighted/len(known))<1e-9, 'ABSOLUTE_DECOMPOSITION')
    other=[r for r in known if r['choice']=='R50']
    negatives=[float(r[quantity_key]['candidatePnlJpy']) for r in other
               if float(r[quantity_key]['candidatePnlJpy'])<0]
    return {'totalN':total,'pairedKnownN':len(known),
            'unknownN':total-len(known),
            'targetIntentN':sum(r['choice']!='R50' for r in subset),
            'targetResolvedN':sum(r['choice']=='TARGET' for r in subset),
            'targetFirstReferenceUnresolvedN':sum(r['choice']=='TARGET_FIRST_REFERENCE_UNRESOLVED' for r in subset),
            'r50DelegationN':sum(r['choice']=='R50' for r in subset),
            'sameTimeControlDelegationN':sum(r['sameTimeControlDelegation'] for r in subset),
            'r50UnknownN':sum(not r['r50OutcomeKnown'] for r in subset),
            'candidatePnlJpySameMask':sum(apnl),'r50PnlJpySameMask':sum(bpnl),
            'candidateMeanNetPct':mean(anet),'r50MeanNetPct':mean(bnet),
            'deltaJpySameMask':sum(change),'deltaMeanNetPp':mean(dp),
            'deltaMedianJpy':statistics.median(change) if change else None,
            'deltaMedianNetPp':statistics.median(dp) if dp else None,
            'improvedN':sum(z>0 for z in change),'equalN':sum(z==0 for z in change),
            'worseN':sum(z<0 for z in change),
            'changedKnownN':len(target),'changedUnknownN':sum(r['choice']!='R50' and
                         r[quantity_key]['deltaJpy'] is None for r in subset),
            'targetEarlierDeltaJpy':sum(float(r[quantity_key]['deltaJpy']) for r in target),
            'nonAdvancedR50AbsolutePnlJpy':sum(float(r[quantity_key]['candidatePnlJpy']) for r in other),
            'nonAdvancedLossTotalJpy':sum(negatives),
            'nonAdvancedWorstLossJpy':min(negatives) if negatives else None,
            'targetNetBelowNominalXN':sum(r['targetNetBelowX'] is True for r in subset),
            'overshootClosePctMean':mean([r['overshootClosePct'] for r in subset
                                          if r['choice']=='TARGET']),
            'referenceLagWallMinutesMean':mean([r['triggerToFillWallMinutes'] for r in subset
                                                if r['choice']=='TARGET']),
            'referenceLagActiveMinutesMean':mean([r['triggerToFillActiveMinutes'] for r in subset
                                                  if r['choice']=='TARGET']),
            'triggerToFillPricePctMean':mean([r['triggerToFillPricePct'] for r in subset
                                              if r['choice']=='TARGET'])}


def reach_metrics(subset):
    n=len(subset)
    status=collections.Counter(r['observedHighReachedX'] for r in subset)
    hit=status['CONFIRMED_REACH']; unknown=status['UNKNOWN']
    close=sum(r['firstObservedClosedTargetNow'] is not None for r in subset)
    return {'totalN':n,'observedHighReachN':hit,
            'certifiedHighNonreachN':status['CERTIFIED_NONREACH'],
            'highReachUnknownN':unknown,
            'lowerPct':100*hit/n if n else None,
            'upperPct':100*(hit+unknown)/n if n else None,
            'knownSubsetPct':100*hit/(n-unknown) if n>unknown else None,
            'closedTargetObservedN':close,
            'closedBeforeR50N':sum(r['firstClosedTargetBeforeR50Intent'] for r in subset),
            'completeContinuousPathN':sum(r['wholeExpectedBars']==r['wholeObservedBars']
                                          for r in subset)}


def ci(draws, subset, qkey):
    sessions=json.loads((OUT/'BOOTSTRAP_SPEC.json').read_text())['sessions']
    counts=np.zeros(24,dtype=float)
    cand=np.zeros(24,dtype=float)
    base=np.zeros(24,dtype=float)
    delta=np.zeros(24,dtype=float)
    npp=np.zeros(24,dtype=float)
    index={d:i for i,d in enumerate(sessions)}
    for r in subset:
        s=index[r['session']]; v=r[qkey]
        if v['deltaJpy'] is None:
            continue
        counts[s]+=1
        cand[s]+=float(v['candidatePnlJpy'])
        base[s]+=float(v['r50PnlJpy'])
        delta[s]+=float(v['deltaJpy'])
        npp[s]+=v['deltaNetPp']
    sampled=counts[draws].sum(axis=1)
    invalid=int(np.sum(sampled==0))
    valid=sampled>0
    if invalid>1000:
        status='CI_NOT_RELIABLE'
    else:
        status='DESCRIPTIVE_CLUSTER_CI'
    def quant(a):
        v=a[valid]
        return (np.quantile(v,[.025,.975],method='linear').tolist()
                if len(v) and status!='CI_NOT_RELIABLE' else None)
    return {'status':status,'invalidReplicates':invalid,'validReplicates':int(sum(valid)),
            'pairedKnownN':int(sum(counts)),
            'deltaTotalJpyCI95':quant(delta[draws].sum(axis=1)),
            'deltaMeanNetPpCI95':quant(np.divide(npp[draws].sum(axis=1),sampled,
                                             out=np.full(len(sampled),np.nan),where=valid)),
            'candidateMeanPnlJpyCI95':quant(np.divide(cand[draws].sum(axis=1),sampled,
                                             out=np.full(len(sampled),np.nan),where=valid)),
            'r50MeanPnlJpyCI95':quant(np.divide(base[draws].sum(axis=1),sampled,
                                             out=np.full(len(sampled),np.nan),where=valid))}


def tails(subset, qkey):
    paired=[r for r in subset if r[qkey]['deltaJpy'] is not None]
    def group(rows, field):
        grouped=collections.defaultdict(float)
        for r in rows:
            grouped[r[field]]+=float(r[qkey]['deltaJpy'])
        return grouped
    def side(values, positive):
        v=sorted(((key,abs(num)) for key,num in values.items()
                  if (num>0 if positive else num<0)),key=lambda z:-z[1])
        total=sum(x for _,x in v)
        cumulative=[];n50=None;run=0
        for i,(key,value) in enumerate(v,1):
            run+=value
            cumulative.append({'rank':i,'key':str(key),'absoluteJpy':value,
                               'cumulativePct':100*run/total if total else None})
            if n50 is None and run>=total/2:n50=i
        return {'grossAbsoluteJpy':total,'contributorsN':len(v),'to50PctN':n50,
                'topSharesPct':{str(n):100*sum(x for _,x in v[:n])/total
                                if total else None for n in (1,3,5,10)},
                'cumulative':cumulative}
    grouped={f:group(paired,f) for f in ('entryId','session','symbol')}
    gross={f:{'positive':side(g,True),'negative':side(g,False)} for f,g in grouped.items()}
    total=sum(float(r[qkey]['deltaJpy']) for r in paired)
    abs_total=sum(float(r[qkey]['candidatePnlJpy']) for r in paired)
    loo={f:{str(key):{'deltaJpy':total-sum(float(r[qkey]['deltaJpy'])
                       for r in paired if r[f]==key),
                    'candidateAbsolutePnlJpy':abs_total-sum(float(r[qkey]['candidatePnlJpy'])
                       for r in paired if r[f]==key)}
            for key in {r[f] for r in paired}} for f in ('session','symbol')}
    return {'grossDelta':gross,'loo':loo,'candidateLossTail':{
        'lossTotalJpy':sum(min(0,float(r[qkey]['candidatePnlJpy'])) for r in paired),
        'worstJpy':min((float(r[qkey]['candidatePnlJpy']) for r in paired),default=None)},
        'deltaNetJpy':total}


def cost_stress(subset,qkey):
    paired=[r for r in subset if r[qkey]['deltaJpy'] is not None]
    result={}
    for rate in ('0.0005','0.0010','0.0020'):
        c=E(rate)
        cands=[];base=[];diff=[]
        for r in paired:
            v=r[qkey]; q=v['quantity']; b=E(v['costJpy'])
            ca=pnl(r['candidateFillPrice'],q,b,c)
            co=pnl(r['r50FillPrice'],q,b,c)
            cands.append(float(ca));base.append(float(co));diff.append(float(ca-co))
            check(abs(float(ca-co)-float(v['deltaJpy']))<1e-6,
                  'COST_STRESS_DELTA_INVARIANT')
        result[rate]={'sellCostTotalPp':float(c)*100,'sameMaskN':len(paired),
                      'candidateAbsolutePnlJpy':sum(cands),
                      'r50AbsolutePnlJpy':sum(base),'deltaJpy':sum(diff)}
    return result


def hazard(result,market,raw):
    detail=[]
    summary={}
    source={(a,e['entryId']):e for a,e,c,b,bad,f,r,s in market}
    for arm in ARM:
        for x in TARGETS:
            subset=[r for r in result if r['arm']==arm and r['targetPct']==x]
            c=collections.Counter()
            for r in subset:
                guard=r['ccmgFirstIntentMinute'];t=r['firstObservedClosedTargetNow']
                if guard is not None and t is not None:
                    category=('CCMG_INTENT_BEFORE_TARGET_OBSERVATION' if guard<t else
                              'TARGET_OBSERVATION_BEFORE_CCMG_INTENT' if t<guard else 'SAME_TIME')
                elif guard is not None:
                    category=('ORDER_OR_PATH_UNKNOWN' if r['observedHighReachedX']=='UNKNOWN'
                              else 'CCMG_ONLY')
                elif t is not None:category='TARGET_ONLY'
                else:category=('ORDER_OR_PATH_UNKNOWN' if r['observedHighReachedX']=='UNKNOWN'
                               else 'NEITHER')
                c[category]+=1
                if guard is not None:
                    c['CCMG_INTENTS']+=1
                if category=='CCMG_INTENT_BEFORE_TARGET_OBSERVATION':
                    e=source[arm,r['entryId']]
                    after=[q[2] for m,q in raw[e['opportunityId']].items()
                           if m>=guard and price_ok(q,m)]
                    for z in (x,5,10):
                        c[f'BEFORE_LATER_OBSERVED_HIGH_GE{z}']+=any(
                          100*(high/e['entryPrice']-1)>=z for high in after)
                detail.append({'arm':arm,'targetPct':x,'entryId':r['entryId'],
                  'session':r['session'],'ccmgFirstIntentMinute':guard,
                  'firstObservedTargetCloseNow':t,'category':category,
                  'futureHighReached5':r['anyObservedHighReached']['5'],
                  'futureHighReached10':r['anyObservedHighReached']['10'],
                  'r50DecisionMinute':r['r50DecisionMinute'],
                  'savedCcmgVsR50DeltaJpyEvaluatorOnly':
                       r['savedCcmgVsR50DeltaJpyEvaluatorOnly'],
                  'ccmgOutcomeReplayed':False})
            summary[f'{arm}:{x}']={'n':len(subset),'categoryCounts':dict(c),
                                   'disposition':'CCMG_OPTIONAL_UNPROVEN'}
    rows_gz('PRETARGET_CCMG_HAZARD_ROWS.jsonl.gz',detail)
    write('PRETARGET_CCMG_HAZARD.json',summary)


def availability(result, market, raw):
    from scripts import phase57_entry_timing_signals as signal
    source={(a,e['entryId']):(b,e) for a,e,c,b,bad,f,r,s in market}
    feature=[]; counts=collections.defaultdict(collections.Counter)
    for r in result:
        a,x=r['arm'],r['targetPct']
        if x!=3:continue
        now=r['firstObservedClosedTargetNow']
        if now is None or not r['firstClosedTargetBeforeR50Intent']:
            continue
        bars,e=source[(a,r['entryId'])]
        bar=bars.get(now-1)
        check(bar is not None,'FOCAL_FRESH_BAR')
        # VWAP must include the entire current-day causal prefix, not just
        # the post-Entry portion of a position.
        all_day=raw[e['opportunityId']]
        prefix=np.array([all_day[m] for m in sorted(all_day) if m<now and
                        m!=930 and price_ok(all_day[m],m)],dtype=float).reshape(-1,7)
        vw,cov=signal.observed_vwap(e['session'],signal.regular(e['session'],prefix),now)
        values={'currentReturnPct':100*(bar[4]/e['entryPrice']-1),
                'activeMinutesHeld':execution.active_minutes(e['session'],e['entryMinute'],now),
                'existingState':None,
                **{'signal.'+f:None for f in signal.FAMILIES},
                'currentBarVolume':bar[5], 'currentBarValue':bar[6],
                'observedVWAPDistancePct':100*(bar[4]/vw-1) if vw else None}
        check(len(values)==12 and all(m<now for m in prefix[:,0]) and
              (bar[0]+1)<=now,'FEATURE_FUTURE_CANARY')
        for key,value in values.items():
            counts[a][key]+=value is not None
        # Preserve as-of coverage without adding raw market volume/value
        # observations to the public research result.
        published={**values,'currentBarVolume':None,'currentBarValue':None}
        feature.append({'arm':a,'targetPct':3,'entryId':r['entryId'],'now':now,
                        'values':published,'volumePresent':True,'barValuePresent':True,
                        'volumeZero':bar[5]==0,
                        'volumeMissing':False,'valueZero':bar[6]==0,
                        'vwapCoverage':cov,
                        'marketStateSignalStatus':'C_SOURCE_PREVIOUS_SESSION_OR_SNAPSHOT_NOT_JOINED',
                        'barValueUnit':'SOURCE_NOMINAL_VALUE_UNIT_UNVERIFIED',
                        'knownAtProxy':now,
                        'futureUpsidePctEvaluatorOnly':r['futureUpsidePctEvaluatorOnly'],
                        'extensionDeltaNetPp':(r['100']['r50NetPct']-r['100']['candidateNetPct']
                              if r['100']['deltaJpy'] is not None else None)})
    rows_gz('TARGET_ASOF_FEATURE_ROWS.jsonl.gz',feature)
    status={'focalRows':len(feature),'countsByArm':{a:dict(counts[a]) for a in ARM},
            'primaryColumns':json.loads((OUT/'TARGET_FEATURE_REGISTRY.json').read_text())['primaryColumns'],
            'stateSignal':'C_SOURCE_PREVIOUS_SESSION_OR_SNAPSHOT_NOT_JOINED',
            'volume':'B_BAR_LEVEL; unit and producer lineage partial',
            'vwap':'B_ASOF_PRODUCER_FORMULA_IF_COVERAGE; no later denominator',
            'rawVolume':'per-bar, not cumulative according to source detector activity(); exact exchange unit pending',
            'missingVolumeIsZero':False,
            'historicalPublicationProxyOnly':True,'deployableExtensionInputs':False}
    write('STATE_SIGNAL_VOLUME_AVAILABILITY.json',status)
    assoc={}
    for a in ARM:
        data=[r for r in feature if r['arm']==a and r['extensionDeltaNetPp'] is not None]
        assoc[a]={'focalTriggeredN':sum(r['arm']==a for r in feature),
                  'pairedContinuationN':len(data),
                  'descriptiveOnly':True,
                  'noThresholdOrFeatureSelection':True,
                  'meanExtensionDeltaNetPp':mean([r['extensionDeltaNetPp'] for r in data]),
                  'availableColumnsN':{k:sum((r['volumePresent'] if k=='currentBarVolume'
                      else r['barValuePresent'] if k=='currentBarValue'
                      else r['values'][k] is not None) for r in data)
                      for k in status['countsByArm'].get(a,{})},
                  'rawBarVolumeAndValuePublished':False}
    write('FOCAL_TARGET_ASSOCIATION.json',assoc)
    write('CAUSALITY_TESTS.json',{'prefixFeatureKnownAtNotAfterNow':True,
          'suffixIndependenceSynthetic':True,'futureLabelInputCanary':'REJECTED_BY_EXPLICIT_INPUT_NAMESPACE',
          'savedStateSignalSourceJoin':'BLOCKED_SOURCE',
          'volumeMissingVsZero':'DISTINCT',
          'previousSessionCausality':'UNVERIFIED; not deployed'})


def analyze(result,market,ledgers,raw,skipped,pre):
    draws=np.load(OUT/'SESSION_DRAWS.npz')['drawIndices']
    check(draws.shape==(10000,24) and draws.min()>=0 and draws.max()<24,'DRAW_MATRIX')
    summary={}; reach_table={}; ci_table={}; tail_table={}; cost_table={};gate={}
    common={}
    for a in ARM:
        r=[x for x in result if x['arm']==a]
        id_sets=[{x['entryId'] for x in r if x['targetPct']==t and
                  x['100']['deltaJpy'] is not None} for t in TARGETS]
        common[a]=set.intersection(*id_sets)
    for a in ARM:
        for x in TARGETS:
            key=f'{a}:{x}'
            sample=[r for r in result if r['arm']==a and r['targetPct']==x]
            summary[key]={};reach_table[key]={};ci_table[key]={};tail_table[key]={};cost_table[key]={}
            for scope,(sub,qkey) in scopes(sample).items():
                summary[key][scope]={'targetSpecific':measure(sub,qkey),
                     'allTargetCommonMask':measure(sub,qkey,common[a]),
                     'commonMaskBasis':'all seven target + R50 known within arm'}
                reach_table[key][scope]=reach_metrics(sub)
                if scope in ('ALL_ENTRY_100','R50_FUNDED_ACTUAL'):
                    ci_table[key][scope]={'targetSpecific':ci(draws,sub,qkey),
                        'allTargetCommonMask':ci(draws,[r for r in sub if r['entryId'] in common[a]],qkey)}
                    tail_table[key][scope]=tails(sub,qkey)
                    cost_table[key][scope]=cost_stress(sub,qkey)
            gate[key]={}
            for label, pred in [('5-10',lambda v:5<=v<10),('>=10',lambda v:v>=10),
                                ('>=5',lambda v:v>=5)]:
                s=[r for r in sample if r['futureUpsidePctEvaluatorOnly'] is not None and
                   pred(r['futureUpsidePctEvaluatorOnly'])]
                m=measure(s,'100')
                gate[key][label]={'evaluatedN':len(s),'sameMaskN':m['pairedKnownN'],
                                  'deltaJpy':m['deltaJpySameMask'],
                                  'deltaMeanNetPp':m['deltaMeanNetPp'],
                                  'oldGateReference': 'nondegradation, retained without amendment',
                                  'nondegradedOnSameMask':m['deltaJpySameMask']>=0 and
                                     (m['deltaMeanNetPp'] is None or m['deltaMeanNetPp']>=0)}
    rows_gz('TARGET_REACH_ROWS.jsonl.gz', [{k:v for k,v in r.items() if k not in
                 ('100','actual','candidateFillPrice','r50FillPrice','targetReferencePrice',
                  'ccmgFirstIntentMinute','futureUpsidePctEvaluatorOnly',
                  'savedCcmgVsR50DeltaJpyEvaluatorOnly')}
                 for r in result])
    write('TARGET_REACH_SUMMARY.json',reach_table)
    write('TARGET_EVENT_CENSUS.json',{k:{scope:{field:v['targetSpecific'][field]
                for field in ('targetIntentN','targetResolvedN','r50DelegationN',
                              'sameTimeControlDelegationN','targetFirstReferenceUnresolvedN')}
                  for scope,v in d.items()} for k,d in summary.items()})
    write('EXECUTION_COVERAGE.json',{k:{scope:{field:v['targetSpecific'][field]
                for field in ('totalN','pairedKnownN','unknownN','r50UnknownN','changedUnknownN')}
                  for scope,v in d.items()} for k,d in summary.items()})
    write('FIXED_TARGET_RESULTS.json',summary)
    write('ABSOLUTE_AND_DELTA_METRICS.json',{k:{scope:{field:v['targetSpecific'][field]
                for field in ('pairedKnownN','candidatePnlJpySameMask','r50PnlJpySameMask',
                              'candidateMeanNetPct','r50MeanNetPct','deltaJpySameMask',
                              'deltaMeanNetPp','nonAdvancedLossTotalJpy','targetEarlierDeltaJpy')}
                  for scope,v in d.items()} for k,d in summary.items()})
    write('CLUSTER_CI_RESULTS.json',ci_table)
    write('TAIL_AND_LOO.json',tail_table)
    write('COST_REPRICE_RESULTS.json',cost_table)
    write('LEGACY_WINNER_GATE_AUDIT.json',gate)
    hazard(result,market,raw)
    availability(result,market,raw)
    funded_rows=[]
    for a,e,c,b,bad,f,r,s in market:
        funded_rows.append({'arm':a,'entryId':e['entryId'],'session':e['session'],
                            'symbol':e['symbol'],'entryMinute':e['entryMinute'],
                            'funded':f is not None,'fundedQuantity':f['quantity'] if f else None,
                            'sameTimestampRiskset':r,'initialOrReplacement':
                                  'REPLACEMENT' if s else 'INITIAL',
                            'savedScoreSource':'CAPITAL_V3_B saved OOF; not PRR score',
                            'r50DecisionMinute':c['decisionNow']})
    rows_gz('FUNDING_UNIVERSE_ROWS.jsonl.gz',funded_rows)
    report=json.loads((ROOT/SOURCE['integrationReport']).read_text())
    write('CAPITAL_CONTRACT_AUDIT.json',{'status':'PASS_SAVED_SCORE_AND_FUNDING_IDENTITY',
          'funded':{a:len(ledgers[a]['funded']) for a in ARM},
          'sourceScoresSha256':digest(ROOT/SOURCE['capitalScores']),
          'rankCode':'scripts/phase57_capital_v3.py:ranked_intents',
          'rankInputs':'saved CAPITAL_V3_B temporal OOF ridge predictions; same timestamp only',
          'fitTarget':'train-only clipped [0,20] observed post-Entry upside; score is not a CI lower bound',
          'upstreamFeatures':254,'imputerScaler':'train fold SimpleImputer + StandardScaler',
          'sizing':'R37 one-third as-of equity, cash, 100-share lot, MAX3 concurrent',
          'oldExitAffectsFundedIds':True,'savedScorePredictionByteDiscrepancyUnresolved':True,
          'portfolioReplaysThisCycle':0,'scoreModelRefitsThisCycle':0,
          'fundingRecomputedThisCycle':False,
          'riskset':'same-timestamp saved sizing candidates, not the entire nonfunded population'})
    write('CAPITAL_ENRICHMENT.json',{k:{scope:reach_table[k][scope] for scope in
          ('R50_FUNDED_ACTUAL','R50_NOT_FUNDED_100','SAME_TIMESTAMP_ELIGIBLE_RISKSET')}
          for k in reach_table})
    legacy=[]
    for a,e,c,b,bad,f,r,s in market:
        strict=max((b[m][2] for m in b if m>e['entryMinute'] and m!=930),default=None)
        old=e['futureUpsidePctEvaluatorOnly']
        calc=100*(strict/e['entryPrice']-1) if strict else None
        legacy.append({'arm':a,'entryId':e['entryId'],'sourceValue':old,
                       'recomputedContinuousStrictValue':calc,
                       'different':old is not None and calc is not None and abs(old-calc)>1e-6})
    write('HIGH_DEFINITION_RECONCILIATION.json',{
        a:{'totalN':sum(v['arm']==a for v in legacy),
           'strictContinuousVsOldSourceMismatchN':sum(v['different'] for v in legacy if v['arm']==a),
           'interpretation':'old source may include auction or own evaluator endpoint; do not substitute into policy'}
        for a in ARM})
    write('SOURCE_AND_SCHEMA_GATE.json',{'precommitSha256':digest(OUT/'MEASUREMENT_PRECOMMIT.json'),
           'sourceHashesPass':True,'allowlistedRawKeysDecoded':len(raw),
           'outOfScopeRawValuesSkippedBeforeJsonDecode':skipped,
           'r50OriginalDecisionFillChecked':True,
           'fundedLedgerSource':'original zipped manifest verified',
           'newPolicyArmCount':14,'status':'PASS_WITH_ROW_LEVEL_CENSORING'})
    print(json.dumps({'status':'MAIN_14_POLICY_ARMS_COMPLETE',
          'focalFunded':{a:summary[f'{a}:3']['R50_FUNDED_ACTUAL']['targetSpecific']
                         for a in ARM}},ensure_ascii=False))


def main():
    marker = OUT / 'RUN_STARTED.json'
    check(not marker.exists(), 'REAL_DATA_BUDGET_ALREADY_STARTED')
    pre, entries, ledgers, controls, raw, skipped = load_verified()
    # All identity/execution gates above complete before this marker or outcome.
    write('RUN_STARTED.json', {'atJst': jst(), 'precommitSha256':
          digest(OUT/'MEASUREMENT_PRECOMMIT.json'), 'invocations': 1,
          'plannedPolicyArms': 14, 'newCapitalReplays': 0})
    market = []
    risksets = {}
    replacement = {}
    for a, ledger in ledgers.items():
        group = collections.defaultdict(list)
        for event in ledger['events']:
            ids = [s['entryId'] for s in event['sizing']]
            if len(ids) > 1:
                group[(event['session'], event['minute'])] = ids
        closed = ledger['closed']
        for eid, f in ledger['funded'].items():
            risksets[a,eid] = eid in group.get((f['session'],f['entryMinute']), [])
            replacement[a,eid] = any(c['session']==f['session'] and
                c['exitTimestamp'] <= f['entryTimestamp'] for c in closed)
    # Candidate risksets also include the nonfunded contenders at those stamps.
    for a, ledger in ledgers.items():
        for event in ledger['events']:
            ids = [s['entryId'] for s in event['sizing']]
            if len(ids)>1:
                for eid in ids:
                    risksets[a,eid]=True
    for a in ARM:
        for eid in sorted(entries[a]):
            entry = entries[a][eid]
            filtered, invalid = valid_bars(raw[entry['opportunityId']], entry['session'],
                                           entry['entryMinute'])
            market.append((a,entry,controls[a][eid],filtered,invalid,
                           ledgers[a]['funded'].get(eid),risksets.get((a,eid),False),
                           replacement.get((a,eid),False)))
    # This is one batch invocation: fourteen unique (arm, target) policy identities.
    result = [market_row(a,x,e,c,b,bad,f,r,s)
              for a,e,c,b,bad,f,r,s in market for x in TARGETS]
    check(len(result)==(819+795)*7 and
          len({(r['arm'],r['targetPct']) for r in result})==14, 'POLICY_ARM_BUDGET')
    rows_gz('FIXED_TARGET_OUTCOME_ROWS.jsonl.gz', result)
    analyze(result, market, ledgers, raw, skipped, pre)
    write('RUN_COMPLETED.json', {'atJst':jst(), 'invocations':1,
          'mainPolicyArmEvaluations':14,'newFits':0,'newCapitalReplays':0,
          'newProviderRequests':0,'protectedPartitionOpenings':0,
          'externalLlmRequests':0,'orders':0})


if __name__ == '__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('--self-test',action='store_true')
    ap.add_argument('--run',action='store_true')
    args=ap.parse_args()
    check(args.self_test != args.run, 'CHOOSE_ONE_MODE')
    self_test() if args.self_test else main()
