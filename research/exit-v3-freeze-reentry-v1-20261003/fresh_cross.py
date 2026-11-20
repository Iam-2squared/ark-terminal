"""One fresh-cross machine. Only eligible flat-time immutable score rows enter."""
from dataclasses import dataclass

@dataclass
class FreshCross:
    sell_fill_minute: int
    state: str='WAIT_FOR_RESET'
    reset: dict | None=None
    previous: dict | None=None
    intent: dict | None=None
    decision_N: int=0

    def observe(self,s):
        if self.intent is not None:raise RuntimeError('POST_BUY_INTENT_ENTRY_DECISION_PROHIBITED')
        if s['minute']<=self.sell_fill_minute:raise RuntimeError('BLOCKED_REENTRY_CAUSALITY: must follow sell fill raw minute')
        if self.previous is not None and s['minute']<=self.previous['minute']:raise RuntimeError('BLOCKED_REENTRY_CAUSALITY: score chronology')
        if s['feature_max_timestamp']>s['timestamp']:raise RuntimeError('BLOCKED_REENTRY_CAUSALITY: feature cutoff')
        before=self.state;self.decision_N+=1
        if self.state=='WAIT_FOR_RESET':
            if s['score']<s['threshold']:
                self.state='ARMED_FOR_FRESH_CROSS';self.reset=dict(s)
        elif self.previous is not None and self.previous['score']<self.previous['threshold'] and s['score']>=s['threshold']:
            self.intent=dict(s);self.state='REENTRY_BUY_INTENT'
        self.previous=dict(s)
        return self.intent,{'minute':s['minute'],'row_id':s['row_id'],'score':s['score'],'threshold':s['threshold'],'state_before':before,'state_after':self.state,'reset_observed':before=='WAIT_FOR_RESET' and self.reset is not None,'fresh_cross':self.intent is not None}
