"""Paired evaluation only. Frozen Entry opportunity and v2 outcomes are read-only."""
import collections,csv,gzip,json,math,statistics
from settings import *

METRICS=['realized_return_pct','MFE_realization_pct','pre_sell_observed_peak_giveback_pp','peak_giveback_pp','later_missed_upside_pct','holding_active_minutes','exit_to_later_high_active_minutes','observed_entry_to_high_pct','entry_to_high_active_minutes','entry_to_arm_active_minutes','arm_to_exit_active_minutes','peak_price_giveback_pct','later_missed_upside_entry_basis_pp']
BUCKETS=['<1%','1–<2%','2–<3%','3–<4%','4–<5%','>=5%','UNKNOWN']
OPPORTUNITY=['observed_entry_to_high_pct','observed_high','final_observed_high_minute','latest_tied_observed_high_minute','remaining_source_complete','entry_to_high_active_minutes','observed_High_unknown']

def bucket(value):
    if value is None:return 'UNKNOWN'
    for upper,label in [(1,'<1%'),(2,'1–<2%'),(3,'2–<3%'),(4,'3–<4%'),(5,'4–<5%')]:
        if value<upper:return label
    return '>=5%'

def stats(values):
    v=[x for x in values if x is not None and math.isfinite(x)]
    return {'N':len(v),'mean':statistics.fmean(v) if v else None,'median':statistics.median(v) if v else None}

def economics(replay,baseline,raw):
    out=dict(replay);out.update({k:baseline[k] for k in OPPORTUNITY})
    fp=replay['entry_fill_price'];fm=replay['entry_minute'];day=replay['session'];sell=replay['sell_price'];sm=replay['sell_minute'];filled=replay['sell_status']=='FILLED'
    good=[a for a in raw if valid_raw(a) and fm<int(a[0])<=session_close(day)]
    later=[a for a in good if filled and int(a[0])>sm]
    held=[a for a in good if filled and int(a[0])<sm]
    later_high=max((a[2] for a in later),default=None);later_time=min((int(a[0]) for a in later if a[2]==later_high),default=None)
    held_high=max((a[2] for a in held),default=None)
    ret=100*(sell/fp-1) if filled else None;mfe=baseline['observed_entry_to_high_pct'];high=baseline['observed_high'];peak=baseline['final_observed_high_minute']
    intent=replay['exit_intent']['minute'] if replay['exit_intent'] else replay['planned_close_intent_minute']
    oldintent=baseline['exit_intent']['minute'] if baseline['exit_intent'] else baseline['planned_close_intent_minute']
    arm=replay['first_arm_minute']
    out.update(exclusive_bucket=bucket(mfe),realized_return_pct=ret,MFE_realization_pct=100*ret/mfe if filled and mfe is not None and mfe>0 else None,peak_giveback_pp=mfe-ret if filled and mfe is not None else None,peak_price_giveback_pct=100*(high-sell)/high if filled and high is not None else None,pre_sell_observed_peak_giveback_pp=100*(held_high/fp-1)-ret if filled and held_high is not None else None,later_observed_high=later_high,later_observed_high_minute=later_time,later_missed_upside_pct=max(0,100*(later_high/sell-1)) if later_high is not None else None,later_missed_upside_entry_basis_pp=max(0,100*(later_high-sell)/fp) if later_high is not None else None,exit_before_final_observed_high=sm<peak if filled and peak is not None else None,holding_active_minutes=active_minutes(day,fm,sm) if filled else None,exit_to_later_high_active_minutes=active_minutes(day,sm,later_time) if later_time is not None else None,entry_to_arm_active_minutes=active_minutes(day,fm,arm) if arm is not None else None,arm_to_exit_active_minutes=active_minutes(day,arm,intent) if arm is not None else None,v2_saved_intent_reason=baseline['exit_intent']['reason'] if baseline['exit_intent'] else 'SESSION_CLOSE',v2_saved_exit_reason=baseline['exit_reason'],v2_saved_sell_status=baseline['sell_status'],v2_saved_intent_minute=oldintent,intent_advance_vs_v2_active_minutes=active_minutes(day,fm,oldintent)-active_minutes(day,fm,intent),sell_advance_vs_v2_active_minutes=baseline['holding_active_minutes']-active_minutes(day,fm,sm) if filled and baseline['sell_status']=='FILLED' else None)
    return out

def single(rr):
    ret=[r['realized_return_pct'] for r in rr if r['realized_return_pct'] is not None];negative=[r for r in ret if r<0]
    before=[r['exit_before_final_observed_high'] for r in rr if r['exit_before_final_observed_high'] is not None]
    return {'sell_filled_N':sum(r['sell_status']=='FILLED' for r in rr),'unresolved_N':sum(r['sell_status']=='UNRESOLVED' for r in rr),'positive_N':sum(r>0 for r in ret),'positive_rate_pct':100*sum(r>0 for r in ret)/len(ret) if ret else None,'negative_N':len(negative),'negative_return':stats(negative),'worst_return_pct':min(ret) if ret else None,'below_minus1_N':sum(r<-1 for r in ret),'below_minus2_N':sum(r<-2 for r in ret),'EXIT_before_final_High_N':sum(before),'EXIT_before_final_High_denominator_N':len(before),'EXIT_before_final_High_rate_pct':100*sum(before)/len(before) if before else None,'metrics':{m:stats(r[m] for r in rr) for m in METRICS}}

def group(label,pairs):
    old=[r['v2'] for r in pairs];new=[r['v3'] for r in pairs]
    a=single(old);b=single(new)
    delta={m:stats(r['v3'][m]-r['v2'][m] for r in pairs if r['v3'][m] is not None and r['v2'][m] is not None) for m in METRICS}
    group_diff={m:{k:b['metrics'][m][k]-a['metrics'][m][k] if a['metrics'][m][k] is not None and b['metrics'][m][k] is not None else None for k in ['mean','median']} for m in METRICS}
    return {'group':label,'denominator_N':len(pairs),'v2':a,'v3':b,'paired_delta':delta,'group_difference':group_diff,'EXIT_C_N':sum(r['v3']['exit_intent'] is not None and r['v3']['exit_intent']['reason']=='LOCAL_UP_STRUCTURE_GUARD_BROKEN' for r in pairs),'intent_advance_vs_v2_active_minutes':stats(r['v3']['intent_advance_vs_v2_active_minutes'] for r in pairs),'sell_advance_vs_v2_active_minutes':stats(r['v3']['sell_advance_vs_v2_active_minutes'] for r in pairs)}

def flat(value,prefix=''):
    result={}
    for key,item in value.items():
        name=prefix+key
        if isinstance(item,dict):result.update(flat(item,name+'_'))
        elif not isinstance(item,(list,tuple)):result[name]=item
    return result

def write_table(name,values):
    save(HERE/(name+'.json'),values)
    rr=[flat(x) for x in values];fields=list(dict.fromkeys(k for r in rr for k in r))
    with (HERE/(name+'.csv')).open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader();writer.writerows(rr)

def run():
    old={r['watch_key']:r for r in rows(V2/'ECONOMICS_ROWS.jsonl.gz')};replay=list(rows(PRIVATE/'REPLAY_ROWS.jsonl.gz'));raw=load(V2/'SAVED_INPUTS/raw_paths_selected.json.gz')
    assert len(old)==len(replay)==1600 and set(old)=={r['watch_key'] for r in replay}
    pairs=[]
    for r in replay:
        base=old[r['watch_key']]
        assert (r['entry_minute'],r['entry_fill_price'],r['entry_timestamp'])==(base['entry_minute'],base['entry_fill_price'],base['entry_timestamp'])
        new=economics(r,base,raw[r['watch_key']]['today']);pairs.append({'watch_key':r['watch_key'],'exclusive_bucket':new['exclusive_bucket'],'v2':base,'v3':new})
    for name,values in [('ECONOMICS_ROWS.jsonl.gz',[r['v3'] for r in pairs]),('PAIRED_ROWS.jsonl.gz',pairs)]:
        with (PRIVATE/name).open('wb') as out,gzip.GzipFile(fileobj=out,mode='wb',mtime=0) as gz:
            for r in values:gz.write(line(r))
    c=[r for r in pairs if r['v3']['exit_intent'] is not None and r['v3']['exit_intent']['reason']=='LOCAL_UP_STRUCTURE_GUARD_BROKEN']
    ge5=[r for r in pairs if r['exclusive_bucket']=='>=5%'];c5=[r for r in c if r['exclusive_bucket']=='>=5%']
    exclusive=[group(b,[r for r in pairs if r['exclusive_bucket']==b]) for b in BUCKETS]
    write_table('EXCLUSIVE_ENTRY_HIGH_PRIMARY',exclusive)
    write_table('WINNER_GE5_PROTECTION',[group('>=5%_ALL',ge5)])
    write_table('ALL_ENTRY_ECONOMICS',[group('ALL_1600',pairs)])
    write_table('EXIT_C_PAIRED_DIAGNOSIS',[group('EXIT_C_ALL',c)])
    write_table('EXIT_C_EXCLUSIVE',[group(b,[r for r in c if r['exclusive_bucket']==b]) for b in BUCKETS])
    write_table('WINNER_GE5_EXIT_C',[group('>=5%_EXIT_C',c5)])
    write_table('EXIT_C_V2_REASON',[group(reason,[r for r in c if r['v3']['v2_saved_intent_reason']==reason]) for reason in ['UP_STRUCTURE_REVERSED','UP_STRUCTURE_RETIRED_BY_RANGE','SESSION_CLOSE']])
    write_table('V3_EXIT_REASON',[group(reason,[r for r in pairs if r['v3']['exit_reason']==reason]) for reason in ['UP_STRUCTURE_REVERSED','UP_STRUCTURE_RETIRED_BY_RANGE','LOCAL_UP_STRUCTURE_GUARD_BROKEN','SESSION_CLOSE','UNRESOLVED']])
    with (PRIVATE/'EXIT_C_ROWS.jsonl.gz').open('wb') as out,gzip.GzipFile(fileobj=out,mode='wb',mtime=0) as gz:
        for r in c:gz.write(line(r))
    rr=[r['v3'] for r in pairs];updates=[e for r in rr for e in r['local_guard_events'] if e['type'] in ['LOCAL_GUARD_CREATED','LOCAL_GUARD_TIGHTENED']]
    mechanics={'saved_at_jst':now(),'Entry_N':1600,'local_pivot_observed_after_Entry_N':sum(r['local_pivot_observed_N'] for r in rr),'prefix_local_pivot_observed_N':sum(r['prefix_local_pivot_N'] for r in rr),'LHL_eligible_unique_sequence_N':sum(r['LHL_eligible_sequence_N'] for r in rr),'LHL_higher_low_unique_sequence_N':sum(r['LHL_higher_low_sequence_N'] for r in rr),'guard_candidate_bar_N':sum(r['local_guard_candidate_bar_N'] for r in rr),'local_guard_creation_N':sum(r['local_guard_creation_N'] for r in rr),'local_guard_tighten_N':sum(r['local_guard_tighten_N'] for r in rr),'unique_positions_with_guard_N':sum(r['local_guard_established_ever'] for r in rr),'guard_never_established_N':sum(not r['local_guard_established_ever'] for r in rr),'guard_reset_with_level_N':sum(r['local_guard_reset_with_level_N'] for r in rr),'guard_break_N':len(c),'guard_to_main_distance_u_at_activation':stats(e['guard_to_main_distance_u'] for e in updates),'guard_age_since_creation_bars_at_break':stats(r['v3']['exit_intent']['guard_age_since_creation_bars'] for r in c),'guard_age_since_last_update_bars_at_break':stats(r['v3']['exit_intent']['guard_age_since_last_update_bars'] for r in c),'break_Primary_context_N':dict(collections.Counter(str(r['v3']['exit_intent']['primary'])+'/'+str(r['v3']['exit_intent']['context']) for r in c)),'break_preceding3_distinct_Primary_N':dict(collections.Counter('>'.join(r['v3']['exit_last3_distinct_primary']) for r in c)),'EXIT_C_v2_saved_intent_reason_N':dict(collections.Counter(r['v3']['v2_saved_intent_reason'] for r in c)),'EXIT_C_v2_saved_sell_status_N':dict(collections.Counter(r['v3']['v2_saved_sell_status'] for r in c)),'>=5_Winner_EXIT_C_N':len(c5),'eligible_sequence_definition':'unique same-segment previous-bar LHL suffix; higher-low qualifying suffixes shown separately; creation also requires H0 progress and monotonicity','state_semantic_changes':0,'safety':SAFETY}
    save(HERE/'LOCAL_GUARD_MECHANICS.json',mechanics)
    receipt={'saved_at_jst':now(),'status':'V3_PAIRED_EVALUATION_COMPLETE','Entry_N':1600,'paired_join_mismatch_N':0,'Frozen_Entry_High_evaluator_rerun':0,'Frozen_Entry_opportunity_value_changes':0,'exclusive_denominator_sum':sum(g['denominator_N'] for g in exclusive),'v2_economics_rows_sha256':sha(V2/'ECONOMICS_ROWS.jsonl.gz'),'v3_economics_rows_sha256':sha(PRIVATE/'ECONOMICS_ROWS.jsonl.gz'),'paired_rows_sha256':sha(PRIVATE/'PAIRED_ROWS.jsonl.gz'),'EXIT_C_N':len(c),'Winner_GE5_EXIT_C_N':len(c5),'safety':SAFETY}
    save(HERE/'EVALUATION_RECEIPT.json',receipt)
    print(json.dumps({'receipt':receipt,'primary_return':[{ 'bucket':g['group'],'N':g['denominator_N'],'v2':g['v2']['metrics']['realized_return_pct'],'v3':g['v3']['metrics']['realized_return_pct'],'difference':g['group_difference']['realized_return_pct'],'paired_delta':g['paired_delta']['realized_return_pct']} for g in exclusive],'EXIT_C':group('EXIT_C',c),'mechanics':mechanics}))

if __name__=='__main__':run()
