"""Exact v2 canonical execution function; no v2 Replay runner."""
from decimal import Decimal
from reused_clock import *

def fill_from_source(entry,intent,raw):
    day = entry['session']; first_am = min((int(x[0]) for x in raw if int(x[0])<690),default=None)
    first_pm = min((int(x[0]) for x in raw if 750 <= int(x[0]) < regular_end(day)),default=None)
    mixed = {540,750,first_am,first_pm}
    if intent:
        eligible = [x for x in raw if valid_raw(x) and int(x[0]) in regular_starts(day) and int(x[0]) not in mixed and int(x[0]) >= intent['minute'] and int(x[0]) > entry['fill_minute']]
        if eligible:
            a = min(eligible,key=lambda x:x[0]); minute = int(a[0]); price = Decimal(str(a[1])) * Decimal('0.9995')
            return {'sell_status':'FILLED','sell_minute':minute,'sell_timestamp':stamp(day,minute),'sell_price':float(price),'sell_price_decimal':str(price),'sell_raw_price':a[1],'sell_source':'NEXT_ELIGIBLE_REGULAR_RAW_OPEN','sell_source_start':minute,'sell_source_assumed_available_at':stamp(day,minute+1),'sell_adjustment_bps':5,'commission':0,'exit_reason':intent['reason'],'closing_fallback_for_locked_intent':False}
    closing = [x for x in raw if int(x[0]) == session_close(day) and valid_raw(x)]
    if len(closing) == 1:
        a = closing[0]; minute = int(a[0]); price = Decimal(str(a[4])) * Decimal('0.9995')
        return {'sell_status':'FILLED','sell_minute':minute,'sell_timestamp':stamp(day,minute),'sell_price':float(price),'sell_price_decimal':str(price),'sell_raw_price':a[4],'sell_source':'PLANNED_TERMINAL_AUCTION_CLOSE','sell_source_start':minute,'sell_source_assumed_available_at':stamp(day,minute+1),'sell_adjustment_bps':5,'commission':0,'exit_reason':intent['reason'] if intent else 'SESSION_CLOSE','closing_fallback_for_locked_intent':intent is not None}
    return {'sell_status':'UNRESOLVED','sell_minute':None,'sell_timestamp':None,'sell_price':None,'sell_price_decimal':None,'sell_raw_price':None,'sell_source':None,'sell_source_start':None,'sell_source_assumed_available_at':None,'sell_adjustment_bps':5,'commission':0,'exit_reason':'UNRESOLVED','unfilled_intent_reason':intent['reason'] if intent else None,'closing_fallback_for_locked_intent':False,'unresolved_reason':'NO_ELIGIBLE_REGULAR_OPEN_AND_NO_VALID_EXACT_SESSION_CLOSE_SOURCE'}
