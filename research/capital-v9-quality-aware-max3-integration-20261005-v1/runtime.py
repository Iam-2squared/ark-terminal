"""Only Reserve dominance changes; frozen B2 tenure and v7 sizing are reused."""
from control import ROOT,ARMS
import importlib.util
PATH=ROOT/'research/capital-v8r1-cash-constrained-online-max3-20261005-v1/runtime.py'
SPEC=importlib.util.spec_from_file_location('v9_frozen_B2_tenure_sizing',PATH)
FROZEN=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(FROZEN)
allocation=FROZEN.allocation
predicted_release=FROZEN.predicted_release
def order(r):return (-r['pP'],r['entry_timestamp'],r['symbol'],r['entry_id'])
def counts_by_session(r,table,arm):
    assert arm in ARMS
    horizon,duration=predicted_release(r,table)
    counts=[]
    for day in table['training_sessions']:
        counts.append(sum(r['entry_minute']<f['entry_minute']<horizon and f['r']>r['r'] and f['q2']>=r['q2'] and (arm==ARMS[0] or f['q3']>=r['q3']) for f in table['sessions'][day]))
    return counts,horizon,duration
def gate(arm,r,occupancy,minute,table):
    assert arm in ARMS and 0<=occupancy<=3 and minute==r['entry_minute']
    base={'occupancy':occupancy,'free_slots':3-occupancy,'future_pressure_session_N':None,'training_session_N':None,'P_future_capacity_pressure':None,'predicted_release_minute':None,'predicted_active_duration':None}
    if occupancy==3:return False,'MAX3_FULL',base
    counts,horizon,duration=counts_by_session(r,table,arm);n=len(counts);hits=sum(z>=3-occupancy for z in counts);ok=2*hits<n
    base.update(future_pressure_session_N=hits,training_session_N=n,P_future_capacity_pressure=hits/n,predicted_release_minute=horizon,predicted_active_duration=duration,horizon_minute=horizon)
    return ok,'ACCEPT_CAPACITY' if ok else 'CAPACITY_RESERVE_REJECT',base
