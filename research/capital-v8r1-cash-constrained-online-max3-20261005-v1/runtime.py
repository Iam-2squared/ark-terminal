"""Outcome-blind B1/B2 gates; v7 allocation source is reused unchanged."""
from decimal import Decimal as D
from pathlib import Path
import importlib.util
ARMS=['CAPACITY_ORDERSTAT_MAX3_V1','TENURE_AWARE_CAPACITY_ORDERSTAT_MAX3_V1']
BUCKETS=[(540,570),(570,600),(600,630),(630,660),(660,690),(750,780),(780,810),(810,840),(840,870),(870,900),(900,920)]
def active_clock(t):return t-540-min(60,max(0,t-690))
def wall_clock(a):return 540+a+(60 if a>150 else 0)
def bucket(t):
 for low,high in BUCKETS:
  if low<=t<high:return f'{low}-{high}'
 raise ValueError('ENTRY_OUTSIDE_FROZEN_BUCKETS')
def predicted_release(r,table):
 duration=table['tenure']['cells'][r['band']][bucket(r['entry_minute'])]['median_active_duration']
 return min(920,wall_clock(active_clock(r['entry_minute'])+duration)),duration
def order(r):return (-r['pP'],r['entry_timestamp'],r['symbol'])
def gate(arm,r,occupancy,minute,table):
 assert arm in ARMS and 0<=occupancy<=3
 base={'occupancy':occupancy,'free_slots':3-occupancy,'future_pressure_session_N':None,'training_session_N':None,'P_future_capacity_pressure':None,'predicted_release_minute':None,'predicted_active_duration':None}
 if occupancy==3:return False,'MAX3_FULL',base
 assert table['train_N']==r['train_N']
 horizon=920
 if arm==ARMS[1]:horizon,duration=predicted_release(r,table);base.update(predicted_release_minute=horizon,predicted_active_duration=duration)
 c=3-occupancy;counts=[sum(minute<e<horizon and u>r['rank_units'] for e,u in table['sessions'][day]) for day in table['training_sessions']];n=len(counts);pressured=sum(x>=c for x in counts);allowed=pressured*2<n
 base.update(future_pressure_session_N=pressured,training_session_N=n,P_future_capacity_pressure=pressured/n,horizon_minute=horizon)
 return allowed,'ACCEPT_CAPACITY' if allowed else 'CAPACITY_RESERVE_REJECT',base
# This imported immutable helper changes no sizing operations or semantics.
PATH=Path(__file__).resolve().parents[2]/'research/capital-v7-rank-native-max3-20261005-v1/runtime.py'
SPEC=importlib.util.spec_from_file_location('immutable_v7_sizing',PATH)
FROZEN_SIZING=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(FROZEN_SIZING)
allocation=FROZEN_SIZING.allocation
