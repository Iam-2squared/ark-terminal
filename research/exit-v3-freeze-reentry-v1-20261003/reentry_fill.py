"""Frozen FIRST ENTRY next-open eligibility bridge; no teacher/model import."""
from reused_clock import regular_starts,valid_raw,stamp

FROZEN_ENTRY_NEXT_FILL_SLICE='''def next_fill(day,a,intent):
 eligible=a[np.isin(a[:,0],regular_starts(day))&(a[:,0]>=intent)&~np.isin(a[:,0],[540,750])]
 if not len(eligible):return None
 x=eligible[0];return int(x[0]),float(x[1]*1.0005)
'''

def buy_fill(day,intent,raw):
    # Exact same eligibility and binary float multiplication as Frozen FIRST ENTRY.
    candidates=[r for r in raw if valid_raw(r) and int(r[0]) in regular_starts(day) and int(r[0])>=intent['minute'] and int(r[0]) not in (540,750)]
    if not candidates:return {'buy_status':'NO_REENTRY_NO_NEXT_REGULAR_OPEN','buy_minute':None,'buy_timestamp':None,'buy_price':None,'buy_raw_price':None,'commission':0}
    r=min(candidates,key=lambda x:x[0]);m=int(r[0])
    return {'buy_status':'FILLED','buy_minute':m,'buy_timestamp':stamp(day,m),'buy_price':float(r[1]*1.0005),'buy_raw_price':r[1],'buy_source':'NEXT_ELIGIBLE_REGULAR_RAW_OPEN','buy_source_start':m,'buy_source_assumed_available_at':stamp(day,m+1),'buy_adjustment_bps':5,'commission':0}
