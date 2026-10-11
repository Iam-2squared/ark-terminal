"""Pure past-only one-shot gate. No teachers, books, suffixes, or oracle import."""
def gate(row,occupancy,minute,table):
 assert occupancy in (0,1,2,3) and row['ML']>=1
 counts=table['minute_counts'][str(minute)];n=table['training_session_N']
 prob=counts[0]/n;expected=counts[2]/n
 audit={'pre_decision_occupancy':occupancy,'training_B_median':table['B_median'],'training_B_p75':table['B_p75'],'remaining_Aplus_probability':prob,'remaining_Aplus_ge2_probability':counts[1]/n,'expected_remaining_Aplus':expected,'arrival_bucket':table['minute_bucket'][str(minute)],'training_block':row['block']}
 if occupancy==3:return False,'MAX_POSITION_CAP',audit
 if occupancy==0:return True,'SLOT1_NO_RESERVE',audit
 if row['rank'] in ('S','A'):return True,'SA_ALWAYS_ADMIT',audit
 assert row['rank']=='B'
 if occupancy==1:
  allowed=minute>=840 or (row['ML']>=table['B_median'] and prob<.50)
  reason='SLOT2_B_LATE_RELEASE' if minute>=840 else 'SLOT2_B_QUALITY_AND_ARRIVAL_PASS' if allowed else 'SLOT2_RESERVE_FOR_FUTURE_QUALITY'
 else:
  quality=row['ML']>=table['B_p75']
  allowed=quality and (minute>=870 or (prob<.35 and expected<.75))
  reason='SLOT3_B_LATE_RELEASE' if allowed and minute>=870 else 'SLOT3_B_QUALITY_AND_ARRIVAL_PASS' if allowed else 'SLOT3_RESERVE_FOR_FUTURE_QUALITY'
 return allowed,reason,audit
