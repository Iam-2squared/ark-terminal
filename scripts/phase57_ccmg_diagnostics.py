"""Mechanism, retention, fill and missing-data diagnostics after Layer A Gate."""
from __future__ import annotations

import collections
import gzip
import json
import statistics

from scripts import phase57_ccmg_layer_a as layer
from scripts import phase57_ccmg_readiness as readiness
from scripts import phase57_ccmg_guard as guard
from scripts import phase57_development_integrated_v0 as v0
from scripts import phase57_exit_continuation_r52 as r52
from scripts import phase57_exit_checkpoints_v1 as cp


def dist(xs):return layer.distr([x for x in xs if x is not None])


def pct(a,b):return None if not b else a/b


def compute():
    with gzip.open(layer.OUT/'LAYER_A_ENTRY_ROWS.jsonl.gz','rt') as f:
        records=[json.loads(line) for line in f]
    primary={(x['arm'],x['entryId']):x for x in records if x['primary']}
    traces=collections.defaultdict(list)
    with gzip.open(layer.OUT/'CHECKPOINT_DRY_TRACE.jsonl.gz','rt') as f:
        for line in f:
            x=json.loads(line);key=(x['arm'],x['entryId'])
            if key in primary:traces[key].append(x)
    layer.require(len(traces)==111,'PRIMARY_TRACE_MISSING')
    raw,skipped=v0.allowlisted_raw_paths(r52.RAW,{x['entryId'].rsplit('|',1)[0] for x in primary.values()})
    layer.require(len(raw)<=111,'PRIMARY_PATH_ALLOWLIST')
    rows=[]
    for key,x in sorted(primary.items()):
        t=traces[key];path=raw[x['entryId'].rsplit('|',1)[0]]
        layer.require(t[-1]['now']==x['candidateDecisionNow'],'DECISION_TRACE_DRIFT')
        candidate_vals=[v['currentReturnPct'] for v in t if v['freshClosedPrice']]
        hwm=max(candidate_vals,default=None)
        last=t[-1]
        first_alert=next((z for z in t if z['event']=='BREACH_1'),None)
        return_at=lambda price:None if price is None else 100*(price/x['entryPrice']-1)
        fill_return=return_at(x['candidateExitPrice'])
        ctrl_return=return_at(x['controlExitPrice'])
        r54_return=return_at(x['r54ExitPrice'])
        def hwm_before(minute):
            if minute is None:return None
            vals=[return_at(path[m][4]) for m in sorted(path)
                  if m>=x['entryMinute'] and m in cp.regular_minutes(x['session']) and m+1<=minute]
            return max(vals,default=None)
        ctrl_hwm=hwm_before(x['controlExitMinute'])
        r54_hwm=hwm_before(x['r54ExitMinute'])
        floor=guard.FLOOR.get(x['highestCertifiedMilestone'])
        r={'arm':x['arm'],'entryId':x['entryId'],'session':x['session'],
          'bucket':x['bucket'],'upsidePct':x['postEntryUpsidePct'],
          'terminalReason':x['terminalReason'],'entryMinute':x['entryMinute'],
          'highestCertified':x['highestCertifiedMilestone'],
          'certifiedCloseHwmPct':hwm,'r54CloseHwmPct':r54_hwm,'controlCloseHwmPct':ctrl_hwm,
          'firstAlertNow':None if first_alert is None else first_alert['now'],
          'firstAlertReturnPct':None if first_alert is None else first_alert['currentReturnPct'],
          'sellIntentNow':x['twoCheckpointSellIntentNow'],
          'sellIntentReturnPct':last['currentReturnPct'] if x['twoCheckpointSellIntentNow'] is not None else None,
          'floorAtDecisionPct':floor,
          'candidateFillGrossReturnPct':fill_return,'controlFillGrossReturnPct':ctrl_return,
          'r54FillGrossReturnPct':r54_return,
          'candidateDecisionGivebackPp':None if hwm is None or x['twoCheckpointSellIntentNow'] is None or last['currentReturnPct'] is None else hwm-last['currentReturnPct'],
          'candidateFillGivebackPp':None if hwm is None or fill_return is None else hwm-fill_return,
          'controlFillGivebackPp':None if ctrl_hwm is None or ctrl_return is None else ctrl_hwm-ctrl_return,
          'r54FillGivebackPp':None if r54_hwm is None or r54_return is None else r54_hwm-r54_return,
          'candidateFillBelowFloor':None if fill_return is None or floor is None else fill_return<floor,
          'candidateFloorOverrunPp':None if fill_return is None or floor is None else floor-fill_return,
          'alertToSellActiveMinutes':None if first_alert is None or x['twoCheckpointSellIntentNow'] is None else cp.active_elapsed(x['session'],first_alert['now'],x['twoCheckpointSellIntentNow']),
          'candidatePnlJpy':x['candidatePnlJpy'],'controlPnlJpy':x['controlPnlJpy'],
          'r54PnlJpy':x['r54PnlJpy'],'fillStatus':x['fillStatus'],
          'certifiedAt':x['certifiedAt']}
        rows.append(r)
    by_winner={}
    for arm in ('IM','R1','combined'):
        for th in (5,10):
            selected=[x for x in rows if (arm=='combined' or x['arm']==arm) and x['upsidePct'] is not None and x['upsidePct']>=th]
            by_winner[f'{arm}>={th}']={'N':len(selected),'certifiedHwm':dist(x['certifiedCloseHwmPct'] for x in selected),
                'candidateDecisionGiveback':dist(x['candidateDecisionGivebackPp'] for x in selected),
                'candidateFillGiveback':dist(x['candidateFillGivebackPp'] for x in selected),
                'controlFillGiveback':dist(x['controlFillGivebackPp'] for x in selected),
                'r54FillGiveback':dist(x['r54FillGivebackPp'] for x in selected),
                'candidateFillBelowFloorN':sum(x['candidateFillBelowFloor'] is True for x in selected),
                'candidateNullFillN':sum(x['candidateFillGrossReturnPct'] is None for x in selected),
                'candidateFirstN':sum(x['terminalReason']=='CANDIDATE_FIRST' for x in selected),
                'medianAlertToSellActiveMinutes':statistics.median([x['alertToSellActiveMinutes'] for x in selected if x['alertToSellActiveMinutes'] is not None]) if any(x['alertToSellActiveMinutes'] is not None for x in selected) else None}
    retention={}
    for arm in ('IM','R1','combined'):
        for m in guard.LADDER:
            selected=[x for x in rows if (arm=='combined' or x['arm']==arm) and str(m) in x['certifiedAt']]
            floor=guard.FLOOR[m]
            known=[x for x in selected if x['candidateFillGrossReturnPct'] is not None]
            ctrl=[x for x in selected if x['controlFillGrossReturnPct'] is not None]
            retention[f'{arm}:{m}']={'certifiedN':len(selected),'candidateKnownN':len(known),
                'candidateNullN':len(selected)-len(known),'floorPct':floor,
                'candidateRetainedN':sum(x['candidateFillGrossReturnPct']>=floor for x in known),
                'candidateRetention':pct(sum(x['candidateFillGrossReturnPct']>=floor for x in known),len(known)),
                'controlKnownN':len(ctrl),'controlRetainedN':sum(x['controlFillGrossReturnPct']>=floor for x in ctrl),
                'controlRetention':pct(sum(x['controlFillGrossReturnPct']>=floor for x in ctrl),len(ctrl)),
                'candidateRealizedMinusFloor':dist(x['candidateFillGrossReturnPct']-floor for x in known),
                'candidateGapBelowFloorN':sum(x['candidateFillGrossReturnPct']<floor for x in known)}
    by_arm={}
    for arm in ('IM','R1','combined'):
        sub=[x for x in rows if arm=='combined' or x['arm']==arm]
        by_arm[arm]={'N':len(sub),'candidateFirstN':sum(x['terminalReason']=='CANDIDATE_FIRST' for x in sub),
          'nullN':sum(x['candidateFillGrossReturnPct'] is None for x in sub),
          'grossFillReturn':dist(x['candidateFillGrossReturnPct'] for x in sub),
          'fillStatus':dict(sorted(collections.Counter(x['fillStatus'] for x in sub).items()))}
    result={'schema':'phase57-ccmg-mechanism-diagnostics-v1','winner':by_winner,'retention':retention,
        'byArm':by_arm,'entryRows':len(rows),'integratedReplayInvocations':0,
        'providerRequests':0,'restrictedPartitionsOpened':0,'safety':guard.SAFETY}
    raw_rows=b''.join(layer.encoded(x) for x in rows)
    zipped=gzip.compress(raw_rows,mtime=0)
    (layer.OUT/'WINNER_MECHANISM_ROWS.jsonl.gz').write_bytes(zipped)
    result['rowsSha256']=layer.sha(zipped)
    (layer.OUT/'MECHANISM_DIAGNOSTICS.json').write_bytes(layer.encoded(result))
    print(json.dumps({'byArm':by_arm,'winner':{k:{p:v[p] for p in ('N','candidateFirstN','candidateNullFillN')} for k,v in by_winner.items()},
                      'retentionCombined':{k:v for k,v in retention.items() if k.startswith('combined:')}},indent=2))


if __name__=='__main__':compute()
