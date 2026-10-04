"""Fixed outcome-blind four-head quality arithmetic and rank admission."""
import math
from allocation import band
PROFILES=['QUALITY_V3_MAX3','S_ONLY_MAX3','A_PLUS_MAX3','B_PLUS_MAX3']
RANKS={'QUALITY_V3_MAX3':{'S','A','B','C'},'S_ONLY_MAX3':{'S'},'A_PLUS_MAX3':{'S','A'},'B_PLUS_MAX3':{'S','A','B'}}
def materialize(row,p5,base5,p3,base3,pf,basef,pl,basel):
 assert all(0<p<1 for p in (p5,p3,pf,pl)) and all(0<b<1 for b in (base5,base3,basef,basel))
 l5=p5/base5;l3=p3/base3;lf=pf/basef;ls=(1-pl)/(1-basel)
 q=(l5*lf*ls)**(1/3);assert math.isfinite(q) and q>0
 passed=l3>=1 and lf>=1 and ls>=1;rank=band(q)
 return {**row,'p5':p5,'base5':base5,'p3':p3,'base3':base3,'p_floor1':pf,'base_floor1':basef,'p_loss0':pl,'base_loss0':basel,'L5':l5,'L3':l3,'LF1':lf,'LSAFE':ls,'Q':q,'capital_score':q,'rank':rank,'capacity_band':rank,'quality_gate_pass':passed,'qualified_C':passed and rank=='C','gate_failures':[k for k,v in [('L3',l3),('LF1',lf),('LSAFE',ls)] if v<1]}
def profile_eligible(row,profile):return row['quality_gate_pass'] and row['rank'] in RANKS[profile]
def candidate_order(r):return (-r['Q'],-r['L5'],-r['L3'],r['entry_timestamp'],r['symbol'])
