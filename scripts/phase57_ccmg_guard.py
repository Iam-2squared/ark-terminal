"""CCMG Guard v1: research-only causal checkpoint exit policy.

The frozen R50 Control is a hard decision ceiling. Potential and any prior
forecast/Damage model are absent from this policy's inputs.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from scripts import phase57_exit_checkpoints_v1 as cp
from scripts import phase57_exit_execution_contract_v1 as execution

NAME = 'CCMG_GUARD_V1'
LADDER = (1, 2, 3, 5, 10)
FLOOR = {1: 0, 2: 1, 3: 2, 5: 3, 10: 5}
SAFETY = dict.fromkeys(('executionAllowed','brokerWriteAllowed',
    'excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed',
    'paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed',
    'transmitted'), False)


@dataclass
class State:
    entry: dict
    grid: tuple[int, ...]
    highest: int = 0
    breach_streak: int = 0
    index: int = 0
    terminal: bool = False
    intent_now: int | None = None

    @classmethod
    def create(cls, entry):
        envelope = cp.entry_envelope(entry)
        return cls(envelope, cp.checkpoint_grid(envelope['session'], envelope['entryMinute']))

    def checkpoint(self, now, prefix, *, control_now):
        if self.terminal:
            raise ValueError('INTENT_ALREADY_TERMINAL')
        if self.index >= len(self.grid) or now != self.grid[self.index]:
            raise ValueError('NONCANONICAL_SCHEDULED_ORDER')
        if control_now not in self.grid[self.index:]:
            raise ValueError('CONTROL_CEILING_EARLIER_OR_NOT_ON_GRID')
        position = cp.position_features(self.entry, now, prefix)
        fresh = position['freshClosedPrice']
        current = position['currentReturnPct']
        prev = self.highest
        event = None
        if not fresh:
            if current is not None:
                raise ValueError('STALE_CLOSE_AS_CURRENT')
            event = 'DATA_GAP_RESET' if self.breach_streak else 'DATA_GAP'
            self.breach_streak = 0
            state = 'DATA_GAP'
        else:
            certified = max((m for m in LADDER if current >= m), default=0)
            if certified > self.highest:
                self.highest = certified
                self.breach_streak = 0
                event = 'PROMOTION'
            if not self.highest:
                state = 'BASELINE'
            elif current >= FLOOR[self.highest] or self.highest > prev:
                if self.breach_streak and event is None:
                    event = 'RECOVERY'
                self.breach_streak = 0
                state = 'ACTIVE'
            else:
                self.breach_streak += 1
                if self.breach_streak == 2:
                    event, state = 'BREACH_2', 'SELL_INTENT'
                elif self.breach_streak == 1:
                    event, state = 'BREACH_1', 'ALERT_1'
                else:
                    raise ValueError('BREACH_STREAK_OVER_TWO')
        candidate = state == 'SELL_INTENT'
        control = now == control_now
        reason = ('BOTH_TRIGGER_SAME_CHECKPOINT' if candidate and control else
                  'CANDIDATE_FIRST' if candidate else 'CONTROL_FIRST' if control else None)
        if reason is not None:
            self.terminal = True
            self.intent_now = now
            state = 'TERMINAL'
        self.index += 1
        return {'candidate': NAME, 'entryId': self.entry['entryId'], 'session': self.entry['session'],
                'now': now, 'freshClosedPrice': fresh, 'currentReturnPct': current,
                'highestCertifiedMilestone': self.highest or None,
                'floorPct': FLOOR[self.highest] if self.highest else None,
                'breachStreak': self.breach_streak, 'state': state,
                'event': event, 'controlIntent': control, 'candidateIntent': candidate,
                'reason': reason, 'position': position,
                'safety': SAFETY.copy()}


def run_entry(entry, control, path):
    """Run only through the earliest decision, then resolve its exact fill."""
    envelope = {'opportunity':entry['opportunity'],'session':entry['session'],
        'symbol':entry['symbol'],'entryId':entry['entryId'],
        'entryMinute':entry['entryMinute'],'price':float(entry['effectiveEntryPrice'])}
    s = State.create(envelope)
    prefix = ()
    trace = []
    for now in s.grid:
        if now > control['decisionNow']:
            raise ValueError('CONTROL_CEILING_VIOLATION')
        raw = path.get(now-1)
        if raw is not None:
            new = cp.closed_prefix(entry['session'],now,(raw,))
            if len(new)!=1:raise ValueError('CURRENT_BAR_NOT_CLOSED')
            prefix += new
        event = s.checkpoint(now,prefix,control_now=control['decisionNow'])
        trace.append(event)
        if s.terminal:break
    if not s.terminal:raise ValueError('NO_TERMINAL_CLASSIFICATION')
    last=trace[-1]
    reason=last['reason']
    if reason in ('CONTROL_FIRST','BOTH_TRIGGER_SAME_CHECKPOINT'):
        fill={'referenceMinute':control['exitMinute'], 'price':control['exitPrice'],
              'status':'CONTROL_CONFIRMED' if control['exitPrice'] is not None else 'CONTROL_NULL'}
    elif last['now'] == 925:
        fill=execution.terminal_execution_reference([path[t] for t in sorted(path)])
    else:
        fill=execution.ordinary_execution_reference(entry['session'],last['now'],
                [path[t] for t in sorted(path)])
    price=fill['price']
    exit_minute=fill.get('referenceStart',fill.get('referenceMinute'))
    if reason in ('CONTROL_FIRST','BOTH_TRIGGER_SAME_CHECKPOINT'):
        exit_minute=control['exitMinute']
    if price is None:exit_minute=None
    return {'candidate':NAME,'entryId':entry['entryId'],'session':entry['session'],
            'decisionNow':last['now'],'terminalReason':reason,
            'controlCeilingNow':control['decisionNow'],
            'exitMinute':exit_minute,'exitPrice':price,'fillStatus':fill['status'],
            'fillNullReason':None if price is not None else fill['status'],
            'highestCertifiedMilestone':s.highest or None,'checkpointTrace':trace,
            'safety':SAFETY.copy()}


def corrected_pnl_jpy(entry_funded, exit_price, *, sell_cost_pp=0.05):
    if exit_price is None:return None
    if sell_cost_pp < 0:raise ValueError('NEGATIVE_SELL_COST')
    return Decimal(str(exit_price))*Decimal(str(entry_funded['quantity']))*\
        (Decimal(1)-Decimal(str(sell_cost_pp))/Decimal(100))-\
        Decimal(str(entry_funded['notionalJpy']))
