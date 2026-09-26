"""Shared research-only Entry/EXIT context; no decisions, broker or outcome labels."""
import math
import numpy as np
from scripts import phase57_research_dictionary_v0 as v0

def context(day,asof,minute_rows,previous,history,personality=None):
 if not 540<=asof<=931:raise ValueError('ASOF_SESSION_TIME')
 if any(h['session']>=day for h in history):raise ValueError('FUTURE_HISTORY')
 if not previous or previous['Date']>=day:raise ValueError('PREVIOUS_SESSION_REQUIRED')
 if personality and personality['computed_through']>=day:raise ValueError('FUTURE_DICTIONARY')
 # Minute timestamp is the start; only completed minute payloads are validated/read.
 observed=[r for r in minute_rows if r['Date']==day and v0.minute_time(r)<asof]
 if not all(v0.valid(r) for r in observed):raise ValueError('INVALID_OBSERVED_BAR')
 scale=v0.scale(history);bars=v0.bars5(day,observed)
 out={'schema':'RESEARCH_CHART_CONTEXT_V1','session':day,'asOfMinute':asof,'evidence_class':'HISTORICAL_RECONSTRUCTION','labels':v0.LABELS,'missingReason':'UNKNOWN','status':'INSUFFICIENT','features':{},'events':[],'productionAllowed':False}
 if not scale or not bars:return out
 unit=previous['C']*scale;last=bars[-1];c=last['C'];vw=last['VWAP'];f=out['features'];events=out['events']
 f.update(close_vwap_s=(c-vw)/unit if vw else None,close_pdh_s=(c-previous['H'])/unit,close_pdl_s=(c-previous['L'])/unit,body_s=(c-last['O'])/unit,upper_wick_s=(last['H']-max(last['O'],c))/unit,lower_wick_s=(min(last['O'],c)-last['L'])/unit,range_s=(last['H']-last['L'])/unit,time_fraction=(last['t']-540)/(390 if day>='2024-11-05' else 360))
 contiguous=[last]
 for b in reversed(bars[:-1]):
  if contiguous[0]['t']-b['t']!=5 or not v0.same_phase(b['t'],contiguous[0]['t']):break
  contiguous.insert(0,b)
 recent=contiguous[-6:]
 if len(recent)>=3:
  f['slope_s_per5m']=float(np.polyfit(np.arange(len(recent)),[x['C']/unit for x in recent],1)[0])
  peak=max(x['C'] for x in contiguous);trough=min(x['C'] for x in contiguous)
  f.update(pullback_s=(peak-c)/unit,rally_from_trough_s=(c-trough)/unit,compression_ratio=(last['H']-last['L'])/np.mean([x['H']-x['L'] for x in recent[:-1]]) if np.mean([x['H']-x['L'] for x in recent[:-1]])>0 else None)
  if len(recent)>=6:
   a=(recent[-1]['C']-recent[-3]['C'])/unit;b=(recent[-4]['C']-recent[-6]['C'])/unit
   f.update(deceleration_s=a-b)
 swings=v0.swings(bars,unit);out['confirmedSwings']=swings[-4:]
 prices={b['t']:b['C'] for b in bars}
 for direction,label in [(1,'higher_high'),(-1,'higher_low')]:
  confirmed=[x for x in swings if x['direction']==direction]
  f[label]=float(prices[confirmed[-1]['extremeAt']]>prices[confirmed[-2]['extremeAt']]) if len(confirmed)>=2 else None
 for i,b in enumerate(contiguous[1:],1):
  prev=contiguous[i-1]
  if b['VWAP'] and prev['VWAP']:
   if prev['C']<prev['VWAP']-.25*unit and b['C']>b['VWAP']+.25*unit:events.append({'atom':'VWAP_RECLAIM','confirmedAt':b['t']})
   if prev['C']>prev['VWAP']+.25*unit and b['C']<b['VWAP']-.25*unit:events.append({'atom':'VWAP_LOSS','confirmedAt':b['t']})
 if len(swings)>=3:
  # The swing extreme is usable only at its later reversal confirmation.
  same=[x for x in swings if x['direction']==swings[-1]['direction']]
  f['same_direction_swing_amplitude_change']=same[-1]['amplitude']-same[-2]['amplitude'] if len(same)>=2 else None
 orbars=[b for b in bars if 540<b['t']<=570]
 levels={'PDH':previous['H'],'PDL':previous['L']}
 if len(orbars)==6 and asof>=570:levels.update(ORH=max(b['H'] for b in orbars),ORL=min(b['L'] for b in orbars))
 for name,level in levels.items():
  f['distance_'+name+'_s']=(c-level)/unit
  eligible=[b for b in contiguous if name not in ['ORH','ORL'] or b['t']>570]
  for sign,label in [(1,'BREAK'),(-1,'BREAKDOWN')]:
   broken=next((b for b in eligible if sign*(b['C']-level)>.25*unit),None)
   if broken:
    events.append({'atom':name+'_'+label,'confirmedAt':broken['t']})
    reclaim=next((b for b in eligible if broken['t']<b['t']<=broken['t']+30 and sign*(b['C']-level)<-.25*unit),None)
    if reclaim:events.append({'atom':name+'_RECLAIM' if sign<0 else name+'_FAIL','confirmedAt':reclaim['t']})
 past=[h.get('barValues',{}).get(str(last['t'])) for h in history[-10:]];past=[x for x in past if v0.num(x) and x>0]
 f['rvol_value']=last['Va']/float(np.median(past)) if len(past)>=5 else None
 if personality:
  for name,stat in personality.get('features',{}).items():
   if name in f and v0.num(f[name]) and v0.num(stat.get('mean')) and v0.num(stat.get('sd')) and stat['sd']>0:f['deviation_'+name]=(f[name]-stat['mean'])/stat['sd']
 out.update(status='RESEARCH_CONTEXT_AVAILABLE',lastCompletedBar=last['t'],scaleS=scale)
 return v0.clean(out)
