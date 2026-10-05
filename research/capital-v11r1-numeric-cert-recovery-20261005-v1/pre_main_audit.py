"""Independent raw-source MRET/I2 inference and Fraction cap/quantity audit."""
from independent_engine import *
from independent_policy import build,accept,predicted
from control import save,gzsave,checkpoint,now,SAFETY
def main():
    assert not (O/'PRE_MAIN_INDEPENDENT_CAP_AUDIT.json').exists(),'COMPLETED_OR_DECIDED_AUDIT_NO_REPEAT'
    if (P/'PRE_MAIN_CAP_AUDIT_STARTED.json').exists():
        interrupted=read(P/'PRE_MAIN_CAP_AUDIT_INTERRUPTION_RECEIPT.json')
        assert interrupted['resume_first_incomplete'] and not interrupted['pre_main_audit_completed'] and not interrupted['result_decision_written'] and not interrupted['Main_started']
        assert not (P/'INDEPENDENT_CURRENT_MRET_CAP_RUNTIME.jsonl.gz').exists(),'COMPLETED_RAW_PREPARATION_NO_REPEAT'
    else:save(P/'PRE_MAIN_CAP_AUDIT_STARTED.json',{'exact_jst':now(),'raw_build':True,'primary_runtime_imports':0})
    audit=Audit();stream,tables,training=build(audit);rt={r['entry_id']:r for r in stream};saved={r['entry_id']:r for r in rows(P/'CURRENT_MRET_CAP_RUNTIME.jsonl.gz')};ptrain={(r['block'],r['entry_id']):r for r in rows(W/'authority/v9/private/QUALITY_TRAIN_SCORE_TABLE.jsonl.gz')}
    for r in stream:
        s=saved[r['entry_id']]
        for f in ('pP','r','q2','q3','mP','rM'):audit.num(r['entry_id']+'/'+f,r[f],s[f])
        audit.check(r['entry_id']+'/strict_MRET_percentile_count',r['rM']==s['rM'] and r['MRET_train_N']==s['MRET_train_N'])
    for r in training:
        s=ptrain[r['block'],r['entry_id']]
        for f in ('entry_id','block','session','entry_minute','r','band'):audit.check(str(r['block'])+'/'+r['entry_id']+'/train/'+f,r[f]==s[f])
        for f in ('q2','q3'):audit.num(str(r['block'])+'/'+r['entry_id']+'/train/'+f,r[f],s[f])
    states=rows(P/'FROZEN_I2_ACTION_SUPPORT.jsonl.gz')
    for s in states:
        r=rt[s['entry_id']];ok,why,count,n=accept(ARMS[0],r,s['occupancy'],r['entry_minute'],tables[str(r['block'])]);audit.check(r['entry_id']+'/same_state_I2',ok==s['action'] and why==s['reason']);audit.check(r['entry_id']+'/pressure_count',count==s['audit']['future_pressure_session_N'] and n==s['audit']['training_session_N'])
        if s['occupancy']<3:
            h,d=predicted(r,tables[str(r['block'])]);audit.check(r['entry_id']+'/horizon',h==s['audit']['predicted_release_minute'] and d==s['audit']['predicted_active_duration'])
    cases=rows(P/'CAP_PRE_MAIN_CASES.jsonl.gz')
    for c in cases:
        picked=[]
        for x in c['picked']:
            r=dict(rt[x['entry_id']],band=x['band'],raw_reference=x['raw_reference'],cap_policy=c['arm'])
            # Synthetic ranks are explicit boundary inputs; real saved-batch
            # ranks are independently inferred from raw source and frozen train.
            if c['kind']=='SYNTHETIC':r['rM']=x['rM']
            picked.append(r)
        result=lot_allocate(picked,F(c['equity']),F(c['cash']),c['held_bands'])
        for i,(a,z) in enumerate(zip(result,c['assigned'])):
            name=c['case_id']+'/'+c['arm']+'/'+str(i)
            for f in ('quantity','first_pass_quantity','water_fill_lots','water_fill_rounds','cap_hit','cap_policy'):audit.check(name+'/'+f,a[f]==z[f])
            for f in ('debit','lot_debit','equity_cap','effective_cap','frozen_equity_cap','batch_equity','batch_budget','target_utilization','budget_unspent'):audit.money(name+'/'+f,a[f],z[f])
            audit.num(name+'/desired',float(a['desired']),float(z['desired']))
            for f in ('mP','rM'):audit.num(name+'/'+f,a[f],z[f])
            audit.check(name+'/rM_exact',a['rM']==z['rM'])
    gzsave(P/'INDEPENDENT_CURRENT_MRET_CAP_RUNTIME.jsonl.gz',stream);gzsave(P/'INDEPENDENT_QUALITY_TRAIN_TABLE.jsonl.gz',training);save(P/'INDEPENDENT_I2_PAST_TABLES.json',tables)
    result={'exact_jst':now(),'status':'PASS' if not audit.mismatches else 'CONTRACT_FAIL','checks':audit.checks,'mismatch_N':len(audit.mismatches),'mismatches':audit.mismatches,'max_float_delta':audit.max_float_delta,'float_tolerance':1e-12,'preprocessing_identity':'previously completed FIT_NUMERIC_OPERATOR_V1 bit certification, read-only','money_quantity':'EXACT','effective_cap_financial_operator':'frozen Decimal precision28; actual cash accounting Fraction','primary_runtime_replay_evaluator_imports':0,'current_score_N':len(stream),'quality_train_score_N':len(training),'MRET_train_score_N':8057,'action_state_N':len(states),'cap_case_N':len(cases),'synthetic_case_N':sum(c['kind']=='SYNTHETIC' for c in cases),'saved_batch_case_N':sum(c['kind']=='SAVED_PRE_MAIN_BATCH' for c in cases),'independent_preparation_single_complete_build':True,'incomplete_input_projection_exception_receipt':str((P/'PRE_MAIN_CAP_AUDIT_INTERRUPTION_RECEIPT.json').relative_to(W)),'completed_certificates_reexecuted':0,'Primary_Main_replays':0,'Safety':SAFETY}
    save(O/'PRE_MAIN_INDEPENDENT_CAP_AUDIT.json',result);print(json.dumps(result),flush=True);assert not audit.mismatches,'PRE_MAIN_INDEPENDENT_CONTRACT_FAIL_STOP'
    checkpoint('N11_PRE_MAIN_INDEPENDENT_CAP_AUDIT',{'checks':audit.checks,'mismatch_N':0,'cap_case_N':len(cases)},'Single execution Main claim -> commit -> actual GET -> M1/M2 exactly once')
if __name__=='__main__':main()
