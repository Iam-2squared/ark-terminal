"""LONG Development research policies. No analog, model, symbol rule or I/O.

Completed-close decisions/returns are reference-price marks, not guaranteed fills.
The caller supplies only the next observed completed bar and a calendar-known cap.
"""
import math

MODES=('FIXED12','BAR5_FIXED12','BAR5_CLOSE_PEAK_HALF','BAR5_TWO_LOWER_CLOSES')

def new_state(mode,remaining_regular_slots,direction='LONG'):
 if direction!='LONG':raise ValueError('LONG_ONLY')
 if mode not in MODES:raise ValueError('UNKNOWN_POLICY')
 if not isinstance(remaining_regular_slots,int) or remaining_regular_slots<0:raise ValueError('INVALID_CALENDAR_CAP')
 return {'mode':mode,'cap':min(12,remaining_regular_slots),'seen':0,'state':'INITIAL','peakClose':0.0,'lastClose':None,'declines':0,'defensive':False,'recovered':False,'transitions':[],'done':False}

def on_completed_bar(s,b):
 if s['done']:raise ValueError('TERMINAL_POSITION')
 if b.get('slot')!=s['seen']+1:raise ValueError('NON_CONTIGUOUS_BAR')
 if b.get('missing'):
  s['done']=True;return {'status':'CENSORED','reason':'MISSING_BEFORE_EXIT','netPct':None}
 c=b.get('c')
 if not isinstance(c,(int,float)) or not math.isfinite(c):raise ValueError('INVALID_CLOSE')
 s['seen']+=1;n=s['seen'];reason=None
 if s['mode']!='FIXED12':
  if n==1:
   s['defensive']=c<0;s['state']='DEFENSIVE' if c<0 else 'CONTINUATION'
   s['peakClose']=max(0,c);s['transitions'].append({'bar':n,'state':s['state']})
  elif s['state']=='DEFENSIVE':
   if c>=0:
    s['state']='CONTINUATION';s['recovered']=True;s['declines']=0;s['peakClose']=c
    s['transitions'].append({'bar':n,'state':'RECOVERED'})
   elif n==5:reason='BAR5_NO_RECLAIM'
  else:
   s['peakClose']=max(s['peakClose'],c)
   s['declines']=s['declines']+1 if c<s['lastClose'] else 0
   if s['mode']=='BAR5_CLOSE_PEAK_HALF' and s['peakClose']>0 and c<=s['peakClose']/2:reason='HALF_OBSERVED_CLOSE_PEAK_GIVEBACK'
   if s['mode']=='BAR5_TWO_LOWER_CLOSES' and s['declines']>=2:reason='TWO_LOWER_COMPLETED_CLOSES'
 s['lastClose']=c
 if reason is None and n==s['cap']:reason='FIXED12_CAP' if s['cap']==12 else 'CALENDAR_SESSION_CAP'
 if reason:
  s['done']=True
  return {'status':'EXIT_REFERENCE','reason':reason,'grossPct':c,'netPct':c-.05,'exitBar':n,'exitTimestamp':b['end'],'holdingClockMinutes':b['minutes'],'defensive':s['defensive'],'recovered':s['recovered'],'transitions':list(s['transitions'])}
 return {'status':'HOLD_RESEARCH_STATE'}

def replay(event,mode):
 if event.get('direction')!='LONG':raise ValueError('LONG_ONLY')
 s=new_state(mode,event['expectedBars'],event['direction'])
 if s['cap']==0:return {'status':'CENSORED','reason':'NO_REMAINING_REGULAR_BAR','netPct':None}
 for b in event['future']:
  r=on_completed_bar(s,b)
  if r['status']!='HOLD_RESEARCH_STATE':return r
 return {'status':'CENSORED','reason':'INCOMPLETE_TO_CALENDAR_CAP','netPct':None}
