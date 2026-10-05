"""Separate implementation, no Primary policy/runtime/replay/evaluator imports."""
from independent_engine import *
from independent_policy import build,accept,predicted
from datetime import datetime
from zoneinfo import ZoneInfo
def save(p,o):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x') as f:json.dump(o,f,sort_keys=True,indent=2,ensure_ascii=False);f.write('\n')
def gzsave(p,rr):
    raw=('\n'.join(json.dumps(r,sort_keys=True,separators=(',',':'),ensure_ascii=False) for r in rr)+'\n').encode()
    with Path(p).open('xb') as f:f.write(gzip.compress(raw,mtime=0))
def main():
    a=Audit();stream,tables,training=build(a)
    primary={r['entry_id']:r for r in rows(P/'CURRENT_CAUSAL_QUALITY_RUNTIME.jsonl.gz')};ptrain={(r['block'],r['entry_id']):r for r in rows(P/'QUALITY_TRAIN_SCORE_TABLE.jsonl.gz')};indtrain={(r['block'],r['entry_id']):r for r in training};indcurrent={r['entry_id']:r for r in stream}
    for r in stream:
        for f in ['q2','q3']:a.num(r['entry_id']+'/'+f,r[f],primary[r['entry_id']][f])
    for r in training:
        z=ptrain[r['block'],r['entry_id']];a.check(r['entry_id']+'/projection',set(z)==set(r))
        for f in ['q2','q3']:a.num(r['entry_id']+'/'+f,r[f],z[f])
        for f in set(z)-{'q2','q3'}:a.check(r['entry_id']+'/'+f,r[f]==z[f])
    support=rows(P/'I1_I2_PRESSURE_SUPPORT_STATES.jsonl.gz');cases=[];boundary=0;pairs=0;near=0
    for r in stream:
        if r['band']=='P_BELOW' or r['entry_minute']>=920:continue
        tab=tables[str(r['block'])];h,d=predicted(r,tab);pr=primary[r['entry_id']]
        for day in tab['training_sessions']:
            for f in tab['sessions'][day]:
                if not r['entry_minute']<f['entry_minute']<h or not f['r']>r['r']:continue
                pf=ptrain[f['block'],f['entry_id']]
                for field in ['q2']+(['q3'] if pf['q2']>=pr['q2'] else []):
                    pairs+=1;near+=abs(pf[field]-pr[field])<=1e-12
                    disagree=(pf[field]>=pr[field])!=(f[field]>=r[field]);boundary+=disagree;a.check(r['entry_id']+'/'+f['entry_id']+'/'+field+'/boundary',not disagree)
    bystate={(z['entry_id'],z['occupancy']):z for z in support}
    for r in stream:
        if r['band']=='P_BELOW' or r['entry_minute']>=920:continue
        for occ in range(4):
            z=bystate[r['entry_id'],occ]
            for j,arm in enumerate(ARMS):
                ok,reason,hits,n=accept(arm,r,occ,r['entry_minute'],tables[str(r['block'])]);p=z['I'+str(j+1)]
                a.check(r['entry_id']+f'/{occ}/{j}/action',ok==p['action'] and reason==p['reason'] and hits==p['future_pressure_session_N'] and n==p['training_session_N'])
                if occ<3:
                    h,d=predicted(r,tables[str(r['block'])]);a.check(r['entry_id']+f'/{occ}/{j}/horizon',h==p['predicted_release_minute'] and d==p['predicted_active_duration']);a.num(r['entry_id']+'/pressure',hits/n,p['P_future_capacity_pressure'])
                cases.append({'entry_id':r['entry_id'],'occupancy':occ,'policy':arm,'action':ok,'reason':reason,'hits':hits,'session_N':n})
    gzsave(P/'INDEPENDENT_CURRENT_RUNTIME.jsonl.gz',stream);gzsave(P/'INDEPENDENT_TRAIN_SCORES.jsonl.gz',training);gzsave(P/'INDEPENDENT_ACTION_CASES.jsonl.gz',cases)
    save(P/'INDEPENDENT_PAST_TABLES.json',tables)
    save(O/'NUMERIC_DOMINANCE_BOUNDARY_AUDIT.json',{'status':'PASS' if boundary==0 and not a.mismatches else 'NUMERIC_DOMINANCE_AMBIGUOUS','all_compared_pair_N':pairs,'near_tie_N':near,'near_tie_pairs_sha256':digest(P/'NUMERIC_NEAR_TIE_PAIRS.jsonl.gz'),'independent_boundary_disagreement_N':boundary,'max_abs_float_difference':a.max_float_delta,'float_tolerance':1e-12,'exact_equal_ge':True,'rounded_score':False})
    report={'exact_jst':datetime.now(ZoneInfo('Asia/Tokyo')).isoformat(),'status':'PASS' if not a.mismatches and boundary==0 else 'CONTRACT_FAIL','mismatch_N':len(a.mismatches),'mismatches':a.mismatches,'checks_N':a.checks,'action_cases_N':len(cases),'max_abs_float_difference':a.max_float_delta,'numeric_boundary_disagreement_N':boundary,'Primary_policy_runtime_replay_evaluator_imports':0,'independent_raw_score_table_builds':1,'newFits':0,'prepared_hashes':{n:digest(P/n) for n in ['INDEPENDENT_CURRENT_RUNTIME.jsonl.gz','INDEPENDENT_TRAIN_SCORES.jsonl.gz','INDEPENDENT_ACTION_CASES.jsonl.gz','INDEPENDENT_PAST_TABLES.json']},'implementation_independence':True,'market_source_independence':False,'upstream_actual_arrival_unknown':'inherited bar-end as-of boundary only; no actual-arrival claim'}
    save(O/'PRE_MAIN_INDEPENDENT_POLICY_AUDIT.json',report)
    print(json.dumps({k:report[k] for k in ['status','mismatch_N','checks_N','action_cases_N','max_abs_float_difference','numeric_boundary_disagreement_N']}),flush=True)
if __name__=='__main__':main()
