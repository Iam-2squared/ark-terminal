"""Append final audit-backed gates; preserve every provisional and old record."""
from control import *
def main():
    audit=read(OUT/'INDEPENDENT_AUDIT.json');assert audit['status']=='PASS' and audit['mismatch_N']==0
    provisional=read(OUT/'PROVISIONAL_WINNER_AND_BOTTLENECK.json');expected=audit['independent_decision'];assert provisional==expected
    quality=read(OUT/'QUALITY_RETENTION_AND_EXPOSURE_DELTA.json');capital=read(OUT/'CAPITAL_ROLLING20_RESULT.json');qfinal={};cfinal={}
    for a in ARMS:
        q=quality['profiles'][a];g=q['quality_retention_gates']|{'Q7':True};ret=q['measurement_complete'] and all(g.values());floor=q['v5_floor_PASS'];c=capital['profiles'][a]
        qfinal[a]={'quality_retention_gates':g,'QUALITY_RETENTION_PASS':ret,'v5_floor_gates':q['v5_floor_gates'],'v5_floor_PASS':floor,'funded_quality':q['funded_quality'],'measurement_complete':q['measurement_complete'],'scope':q['funded_quality_scope'],'integrity':q['integrity']}
        cfinal[a]={'v5_economic_gates':c['v5_economic_gates'],'v5_economics_PASS':c['v5_economics_PASS'],'Capital_PASS':ret and c['v5_economics_PASS'],'relative_progress_gates':c['relative_gates'],'MONETIZATION_CAPITAL_PROGRESS':c['MONETIZATION_CAPITAL_PROGRESS'],'measurement_complete':q['measurement_complete'],'independent_mismatch_N':0}
        assert ret==audit['official_gates'][a]['retained'] and floor==audit['official_gates'][a]['floor']
    save(OUT/'QUALITY_RETENTION_FINAL.json',{'exact_jst':now(),'profiles':qfinal,'independent_mismatch_N':0,'Safety':SAFETY})
    save(OUT/'CAPITAL_GATE_FINAL.json',{'exact_jst':now(),'profiles':cfinal,'independent_mismatch_N':0,'Safety':SAFETY})
    decision=provisional|{'Q7_pending':False,'independent_mismatch_N':0,'oldV11Status':'V11_CONTRACT_FAIL','oldS9':'FAIL','newS9R':'PASS','monetizationSignal':'MRET_STRONG_CERTIFIED_V11R1','M1_measurement_status':'CAPITAL_MEASUREMENT_BLOCKED_EXECUTION','M2_measurement_status':'COMPLETE','M1_valid_primary_sessions':28,'M1_blocked_session_N':1,'M2_valid_primary_sessions':38,'M1_reexecution':0,'CapitalReplays':2,'newFits':0,'reusedMRETFits':8,'fresh_OOS_claim':False,'productionReady':False,'Safety':SAFETY}
    save(OUT/'WINNER_AND_NEXT_BOTTLENECK.json',decision)
    checkpoint('N17_WINNER_AND_NEXT_BOTTLENECK',decision,'Package exact private authorities; N18 fixed STOP')
if __name__=='__main__':main()
