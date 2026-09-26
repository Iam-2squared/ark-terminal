"""Causal R45 decision facts. Raw suffix/labels are never accepted here.

The caller passes only <=NOW completed bars. Sequence memory is per Entry arm.
"""
from __future__ import annotations
from bisect import bisect_left
from scripts.phase57_exit_execution_contract_v1 import continuous_minutes
from scripts.phase57_exit_gen3_runtime_r45 import (
    STATES, SIGNALS, EPOCH, adjacent, finite, require, load_protocol, validate_facts)


def calendar(day, now):
    require(type(now) is int and now in EPOCH,'R45_CALENDAR_NOW')
    schedule = continuous_minutes(day)
    remaining = len(schedule)-bisect_left(schedule,now)
    return [remaining,min(15,remaining)]


def past_five(day, now, closed_rows):
    """Caller must project away all unfinished bars, including execution candle."""
    require(type(now) is int and now in EPOCH,'R45_PRICE_NOW')
    index = {}
    for row in closed_rows:
        require(len(row)==7 and type(row[0]) in (int,float) and int(row[0])==row[0], 'R45_BAR_FORMAT')
        start=int(row[0])
        require(start+1 <= now and start in continuous_minutes(day),'R45_UNCLOSED_OR_UNSCHEDULED_BAR')
        require(start not in index,'R45_DUPLICATE_BAR')
        index[start]=row
    starts = [s for s in continuous_minutes(day) if s+1<=now][-5:]
    prices=lambda r: r is not None and all(finite(x) and x>0 for x in r[1:5]) and r[2]>=max(r[1],r[3],r[4]) and r[3]<=min(r[1],r[2],r[4])
    selected=[index.get(s) for s in starts]
    out=dict.fromkeys(('momentum5Pct','range5Pct','volume5','higherHigh','higherLow','lowerHigh','lowerLow'))
    if len(selected)==5 and all(prices(r) for r in selected):
        out['momentum5Pct']=100*(selected[-1][4]/selected[0][4]-1)
        out['range5Pct']=100*(max(r[2] for r in selected)/min(r[3] for r in selected)-1)
    if len(selected)==5 and all(r is not None and finite(r[5]) and r[5]>=0 for r in selected):
        out['volume5']=sum(r[5] for r in selected)
    if len(selected)>=2 and all(prices(r) for r in selected[-2:]):
        a,b=selected[-2:]
        out.update(higherHigh=int(b[2]>a[2]),higherLow=int(b[3]>a[3]),
                   lowerHigh=int(b[2]<a[2]),lowerLow=int(b[3]<a[3]))
    return out


class FactMemo:
    def __init__(self):
        self.identity=None; self.last=None; self.states=[]; self.signals=None; self.weak=0; self.peak=None
        self.p=load_protocol()

    def update(self, day, row, price_facts):
        require(set(row)=={'session','identity','fresh','categorical','numeric'},'R45_CORE_ALLOWLIST')
        arm,eid,now=row['identity']
        require(self.identity is None or self.identity==(arm,eid),'R45_FACT_ENTRY_IDENTITY')
        self.identity=(arm,eid)
        require(type(now) is int and now in EPOCH and row['session']==day,'R45_CORE_TIME')
        require(type(row['fresh']) is bool,'R45_CORE_FRESH')
        require(len(row['categorical'])==21 and len(row['numeric'])==83,'R45_CORE_WIDTH')
        require(self.last is None or now>self.last,'R45_FACT_NONMONOTONIC')
        p=self.p['policy']; columns=self.p['features']
        cat=dict(zip(columns['categorical'],row['categorical']))
        nums=dict(zip(columns['baseNumeric'],row['numeric']))
        get=lambda k: nums['position.'+k]
        for k in ('lastObservedClosedAt','peakConfirmedAt'):
            t=get(k); require(t is None or (finite(t) and t<=now),'R45_FUTURE_'+k)
        fresh=row['fresh']; complete=get('fullOwnedPrefix')==1
        require(not fresh or get('lastObservedClosedAt')==now,'R45_FRESH_TIME')
        require(fresh or get('currentReturnPct') is None,'R45_STALE_RETURN')
        if not complete:
            require(get('completePrefixMfePct') is None and get('completePrefixMaePct') is None,'R45_INCOMPLETE_CERTIFICATE')
        reset=not fresh or not adjacent(self.last,now)
        if reset:
            self.states=[]; self.signals=None; self.weak=0; self.peak=None
        state=cat['currentState.state']; state=state if state in STATES else None
        sig=[cat[f'signal.{s}.currentTriState'] for s in SIGNALS]
        require(all(s in ('TRUE','FALSE','UNKNOWN') for s in sig),'R45_TRISTATE')
        old=self.states[-1] if self.states else None
        recovery=int(fresh and old in p['recoveryFromStates'] and state in p['recoveryToStates'])
        if fresh and state:
            self.states=(self.states+[state])[-3:]
            self.weak=min(p['weakRunCap'],self.weak+1) if state in p['weakStates'] else 0
        else:
            self.states=[];self.weak=0
        failed=0
        if len(self.states)==3:
            a,b,c=self.states
            failed=int((a in p['weakStates'] and b in p['recoveryToStates'] and c in p['weakStates']) or
                       (a in ('RISE','SHARP_RISE') and b in p['weakStates'] and c in p['weakStates']))
        losses=sum(a=='TRUE' and b=='FALSE' for a,b in zip(self.signals,sig)) if self.signals and fresh else 0
        gains=sum(a=='FALSE' and b=='TRUE' for a,b in zip(self.signals,sig)) if self.signals and fresh else 0
        certified=get('completePrefixMfePct') if complete and fresh else None
        new=int(finite(certified) and self.peak is not None and certified>self.peak)
        self.peak=certified if finite(certified) else None
        self.signals=sig if fresh else None;self.last=now
        require(set(price_facts)=={'momentum5Pct','range5Pct','volume5','higherHigh','higherLow','lowerHigh','lowerLow'},'R45_PRICE_FACT_ALLOWLIST')
        values=dict(currentReturnPct=get('currentReturnPct') if fresh else None,
                    certifiedMfePct=certified,certifiedGivebackPp=get('observedPeakGivebackPp') if complete and fresh else None,
                    barsHeld=get('activeMinutesHeld'),timeSincePeak=get('activeMinutesSincePeakConfirmation'),
                    weakRun=self.weak,signalTrueN=sig.count('TRUE'),signalFalseN=sig.count('FALSE'),signalUnknownN=sig.count('UNKNOWN'),
                    signalLossN=losses,signalRecoveryN=gains,stateRecovery=recovery,failedRecovery=failed,
                    newPeak=new,**price_facts)
        values={k: values[k] for k in columns['decisionFactFields']}
        envelope=dict(now=now,maxKnownAt=now,maxBarEnd=now,fresh=fresh,values=values)
        validate_facts(envelope)
        return envelope
