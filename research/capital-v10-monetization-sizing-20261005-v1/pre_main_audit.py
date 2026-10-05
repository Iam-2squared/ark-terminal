"""Independent raw-source inference and Fraction sizing. Primary imports=0."""
from independent_engine import *
from independent_policy import build,accept,predicted
from control import save,gzsave,checkpoint,now,SAFETY
def main():
    audit=Audit();stream,tables,training=build(audit);rt={r['entry_id']:r for r in stream};saved={r['entry_id']:r for r in rows(P/'CURRENT_SIZING_RUNTIME.jsonl.gz')};ptrain={(r['block'],r['entry_id']):r for r in rows(P/'SIZING_TRAIN_SCORE_TABLE.jsonl.gz')}
    for r in stream:
        s=saved[r['entry_id']]
        for f in ('pP','r','q2','q3','rp','r2','r3','consensus_weight'):audit.num(r['entry_id']+'/'+f,r[f],s[f])
        for f in ('rp','r2','r3','consensus_weight'):audit.check(r['entry_id']+'/strict_percentile_count/'+f,r[f]==s[f])
    for r in training:
        s=ptrain[r['block'],r['entry_id']]
        for f in ('entry_id','block','session','entry_minute','pP','r','band'):audit.check(str(r['block'])+'/'+r['entry_id']+'/train/'+f,r[f]==s[f])
        for f in ('q2','q3'):audit.num(str(r['block'])+'/'+r['entry_id']+'/train/'+f,r[f],s[f])
    states=rows(P/'FROZEN_I2_ACTION_SUPPORT.jsonl.gz')
    for s in states:
        r=rt[s['entry_id']];ok,why,count,n=accept(ARMS[0],r,s['occupancy'],r['entry_minute'],tables[str(r['block'])]);audit.check(r['entry_id']+'/same_state_I2',ok==s['action'] and why==s['reason']);audit.check(r['entry_id']+'/pressure_count',count==s['audit']['future_pressure_session_N'] and n==s['audit']['training_session_N'])
        if s['occupancy']<3:
            h,d=predicted(r,tables[str(r['block'])]);audit.check(r['entry_id']+'/horizon',h==s['audit']['predicted_release_minute'] and d==s['audit']['predicted_active_duration'])
    cases=rows(P/'SIZING_PRE_MAIN_CASES.jsonl.gz')
    for c in cases:
        picked=[]
        for x in c['picked']:
            # Reconstruct scores/ranks from raw sources, not Primary case fields.
            r=dict(rt[x['entry_id']],band=x['band'],raw_reference=x['raw_reference']);r['sizing_weight']=1 if c['arm']==ARMS[0] else r['consensus_weight'];picked.append(r)
        result=lot_allocate(picked,F(c['equity']),F(c['cash']),c['held_bands'])
        for i,(a,z) in enumerate(zip(result,c['assigned'])):
            name=c['case_id']+'/'+c['arm']+'/'+str(i)
            for f in ('quantity','first_pass_quantity','water_fill_lots','water_fill_rounds'):audit.check(name+'/'+f,a[f]==z[f])
            for f in ('debit','lot_debit','equity_cap','batch_equity','batch_budget','target_utilization','budget_unspent','sizing_weight'):audit.money(name+'/'+f,a[f],z[f])
            audit.num(name+'/desired',float(a['desired']),float(z['desired']))
            for f in ('rp','r2','r3'):audit.num(name+'/'+f,a[f],z[f])
    gzsave(P/'INDEPENDENT_CURRENT_SIZING_RUNTIME.jsonl.gz',stream);gzsave(P/'INDEPENDENT_TRAIN_SCORE_TABLE.jsonl.gz',training);save(P/'INDEPENDENT_PAST_TABLES.json',tables)
    result={'exact_jst':now(),'status':'PASS' if not audit.mismatches else 'CONTRACT_FAIL','checks':audit.checks,'mismatch_N':len(audit.mismatches),'mismatches':audit.mismatches,'max_float_delta':audit.max_float_delta,'float_tolerance':1e-12,'money_quantity':'EXACT','primary_sizing_replay_evaluator_imports':0,'current_score_N':len(stream),'train_score_N':len(training),'action_state_N':len(states),'sizing_case_N':len(cases),'synthetic_case_N':sum(c['kind']=='SYNTHETIC' for c in cases),'saved_batch_case_N':sum(c['kind']=='SAVED_PRE_MAIN_BATCH' for c in cases),'independent_preparation_single_build':True,'Primary_Main_replays':0,'Safety':SAFETY}
    save(O/'PRE_MAIN_INDEPENDENT_SIZING_AUDIT.json',result);print(json.dumps(result),flush=True);assert not audit.mismatches,'PRE_MAIN_INDEPENDENT_CONTRACT_FAIL_STOP'
    checkpoint('M8_PRE_MAIN_INDEPENDENT_SIZING_AUDIT',{'checks':audit.checks,'mismatch_N':0,'sizing_case_N':len(cases)},'Commit single-execution Main claim, actual GET, then S1/S2 exactly once')
if __name__=='__main__':main()
