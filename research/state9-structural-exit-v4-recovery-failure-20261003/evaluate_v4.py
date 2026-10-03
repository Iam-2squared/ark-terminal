"""Paired evaluation only. Saved V3 opportunity, buckets and outcomes are read-only."""
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
    out.update(exclusive_bucket=baseline['exclusive_bucket'],realized_return_pct=ret,MFE_realization_pct=100*ret/mfe if filled and mfe is not None and mfe>0 else None,peak_giveback_pp=mfe-ret if filled and mfe is not None else None,peak_price_giveback_pct=100*(high-sell)/high if filled and high is not None else None,pre_sell_observed_peak_giveback_pp=100*(held_high/fp-1)-ret if filled and held_high is not None else None,later_observed_high=later_high,later_observed_high_minute=later_time,later_missed_upside_pct=max(0,100*(later_high/sell-1)) if later_high is not None else None,later_missed_upside_entry_basis_pp=max(0,100*(later_high-sell)/fp) if later_high is not None else None,exit_before_final_observed_high=sm<peak if filled and peak is not None else None,holding_active_minutes=active_minutes(day,fm,sm) if filled else None,exit_to_later_high_active_minutes=active_minutes(day,sm,later_time) if later_time is not None else None,entry_to_arm_active_minutes=active_minutes(day,fm,arm) if arm is not None else None,arm_to_exit_active_minutes=active_minutes(day,arm,intent) if arm is not None else None,V3_saved_intent_reason=baseline['exit_intent']['reason'] if baseline['exit_intent'] else 'SESSION_CLOSE',V3_saved_exit_reason=baseline['exit_reason'],V3_saved_sell_status=baseline['sell_status'],V3_saved_intent_minute=oldintent,intent_advance_vs_V3_active_minutes=active_minutes(day,fm,oldintent)-active_minutes(day,fm,intent),sell_advance_vs_V3_active_minutes=baseline['holding_active_minutes']-active_minutes(day,fm,sm) if filled and baseline['sell_status']=='FILLED' else None)
    return out

def single(rr):
    ret=[r['realized_return_pct'] for r in rr if r['realized_return_pct'] is not None];negative=[r for r in ret if r<0]
    before=[r['exit_before_final_observed_high'] for r in rr if r['exit_before_final_observed_high'] is not None]
    return {'sell_filled_N':sum(r['sell_status']=='FILLED' for r in rr),'unresolved_N':sum(r['sell_status']=='UNRESOLVED' for r in rr),'positive_N':sum(r>0 for r in ret),'positive_rate_pct':100*sum(r>0 for r in ret)/len(ret) if ret else None,'negative_N':len(negative),'negative_return':stats(negative),'worst_return_pct':min(ret) if ret else None,'below_minus1_N':sum(r<-1 for r in ret),'below_minus2_N':sum(r<-2 for r in ret),'EXIT_before_final_High_N':sum(before),'EXIT_before_final_High_denominator_N':len(before),'EXIT_before_final_High_rate_pct':100*sum(before)/len(before) if before else None,'metrics':{m:stats(r[m] for r in rr) for m in METRICS}}

def group(label,pairs):
    old=[r['v3'] for r in pairs];new=[r['v4'] for r in pairs]
    a=single(old);b=single(new)
    delta={m:stats(r['v4'][m]-r['v3'][m] for r in pairs if r['v4'][m] is not None and r['v3'][m] is not None) for m in METRICS}
    group_diff={m:{k:b['metrics'][m][k]-a['metrics'][m][k] if a['metrics'][m][k] is not None and b['metrics'][m][k] is not None else None for k in ['mean','median']} for m in METRICS}
    common=[r for r in pairs if r['v3']['sell_status']=='FILLED' and r['v4']['sell_status']=='FILLED']
    common_stats={v:stats(r[v]['realized_return_pct'] for r in common) for v in ['v3','v4']}
    return {'return_common_filled_N':len(common),'return_common_filled':common_stats,'return_common_group_difference':{k:common_stats['v4'][k]-common_stats['v3'][k] if common else None for k in ['mean','median']},'exclusive_bucket_N':dict(collections.Counter(r['exclusive_bucket'] for r in pairs)),'negative_to_positive_N':sum(r['v3']['realized_return_pct']<0<r['v4']['realized_return_pct'] for r in common),'positive_to_negative_N':sum(r['v4']['realized_return_pct']<0<r['v3']['realized_return_pct'] for r in common),'group':label,'denominator_N':len(pairs),'v3':a,'v4':b,'paired_delta':delta,'group_difference':group_diff,'EXIT_D_N':sum(r['v4']['exit_intent'] is not None and r['v4']['exit_intent']['reason']=='LOCAL_RECOVERY_FAILED' for r in pairs),'intent_advance_vs_V3_active_minutes':stats(r['v4']['intent_advance_vs_V3_active_minutes'] for r in pairs),'sell_advance_vs_V3_active_minutes':stats(r['v4']['sell_advance_vs_V3_active_minutes'] for r in pairs)}

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
    from selection_gate import selection
    reuse=load(HERE/'V3_TRACE_REUSE_RECEIPT.json')
    assert sha(V3_PRIVATE/'ECONOMICS_ROWS.jsonl.gz')==reuse['V3_economics_sha256'],'BLOCKED_V4_LINEAGE_MISMATCH'
    old={r['watch_key']:r for r in rows(V3_PRIVATE/'ECONOMICS_ROWS.jsonl.gz')}
    replay=list(rows(PRIVATE/'REPLAY_ROWS.jsonl.gz'));raw=load(V2/'SAVED_INPUTS/raw_paths_selected.json.gz')
    assert len(old)==len(replay)==1600 and set(old)=={r['watch_key'] for r in replay}
    pairs=[]
    for r in replay:
        base=old[r['watch_key']]
        assert (r['entry_minute'],r['entry_fill_price'],r['entry_timestamp'])==(base['entry_minute'],base['entry_fill_price'],base['entry_timestamp'])
        new=economics(r,base,raw[r['watch_key']]['today'])
        assert all(new[k]==base[k] for k in OPPORTUNITY) and new['exclusive_bucket']==base['exclusive_bucket']
        pairs.append({'watch_key':r['watch_key'],'exclusive_bucket':base['exclusive_bucket'],'v3':base,'v4':new})
    for name,values in [('ECONOMICS_ROWS.jsonl.gz',[r['v4'] for r in pairs]),('PAIRED_ROWS.jsonl.gz',pairs)]:
        with (PRIVATE/name).open('wb') as out,gzip.GzipFile(fileobj=out,mode='wb',mtime=0) as gz:
            for r in values:gz.write(line(r))
    targets={'2–<3%','3–<4%','4–<5%'}
    target=[p for p in pairs if p['exclusive_bucket'] in targets]
    d=[p for p in pairs if p['v4']['exit_intent'] is not None and p['v4']['exit_intent']['reason']=='LOCAL_RECOVERY_FAILED']
    big=[p for p in pairs if p['exclusive_bucket']=='>=5%'];d5=[p for p in d if p['exclusive_bucket']=='>=5%']
    primary=[group(b,[p for p in pairs if p['exclusive_bucket']==b]) for b in ['2–<3%','3–<4%','4–<5%']]+[group('2–<5%_COMBINED',target),group('>=5%_PROTECTION',big)]
    write_table('PRIMARY_2_TO_5',primary)
    write_table('EXCLUSIVE_ENTRY_HIGH_ALL',[group(b,[p for p in pairs if p['exclusive_bucket']==b]) for b in BUCKETS])
    write_table('WINNER_GE5_PROTECTION',[group('>=5%_ALL',big)])
    write_table('ALL_ENTRY_ECONOMICS',[group('ALL_1600',pairs)])
    write_table('EXIT_D_PAIRED_DIAGNOSIS',[group('EXIT_D_ALL',d)])
    write_table('EXIT_D_EXCLUSIVE',[group(b,[p for p in d if p['exclusive_bucket']==b]) for b in BUCKETS])
    write_table('WINNER_GE5_EXIT_D',[group('>=5%_EXIT_D',d5)])
    reasons=['UP_STRUCTURE_REVERSED','UP_STRUCTURE_RETIRED_BY_RANGE','LOCAL_UP_STRUCTURE_GUARD_BROKEN','SESSION_CLOSE']
    write_table('EXIT_D_V3_REASON',[group(r,[p for p in d if p['v4']['V3_saved_intent_reason']==r]) for r in reasons])
    vr=reasons[:3]+['LOCAL_RECOVERY_FAILED','SESSION_CLOSE','UNRESOLVED']
    write_table('V4_EXIT_REASON',[group(r,[p for p in pairs if p['v4']['exit_reason']==r]) for r in vr])
    write_table('V4_EXIT_REASON_EXCLUSIVE',[group(r+'/'+b,[p for p in pairs if p['v4']['exit_reason']==r and p['exclusive_bucket']==b]) for r in vr for b in BUCKETS])
    target_a=[p for p in target if p['v3']['exit_intent'] is not None and p['v3']['exit_intent']['reason']=='UP_STRUCTURE_REVERSED']
    assert len(target)==426 and sum(p['v3']['sell_status']=='FILLED' for p in target)==417 and len(target_a)==79
    write_table('TARGET_V3_EXIT_A',[group('2–<5%_V3_EXIT_A_79',target_a)])
    with (PRIVATE/'EXIT_D_ROWS.jsonl.gz').open('wb') as out,gzip.GzipFile(fileobj=out,mode='wb',mtime=0) as gz:
        for p in d:gz.write(line(p))
    rr=[p['v4'] for p in pairs];updates=[e for r in rr for e in r['recovery_floor_events'] if e['type'] in ['RECOVERY_FLOOR_CREATED','RECOVERY_FLOOR_TIGHTENED']]
    mech={'saved_at_jst':now(),'Entry_N':1600,'Recovery_Floor_established_position_N':sum(r['recovery_floor_established_ever'] for r in rr),'floor_never_established_N':sum(not r['recovery_floor_established_ever'] for r in rr),'floor_creation_N':sum(r['recovery_floor_creation_N'] for r in rr),'floor_tighten_N':sum(r['recovery_floor_tighten_N'] for r in rr),'floor_reset_with_level_N':sum(r['recovery_floor_reset_with_level_N'] for r in rr),'local_L_evaluated_before_first_intent_N':sum(len(r['recovery_local_L_evaluated_exact']) for r in rr),'EXIT_D_N':len(d),'EXIT_D_v3_intent_reason_N':dict(collections.Counter(p['v4']['V3_saved_intent_reason'] for p in d)),'V3_EXIT_A_preempted_N':sum(p['v4']['V3_saved_intent_reason']=='UP_STRUCTURE_REVERSED' for p in d),'target_V3_EXIT_A_preempted_N':sum(p['v4']['V3_saved_intent_reason']=='UP_STRUCTURE_REVERSED' and p['exclusive_bucket'] in targets for p in d),'GE5_EXIT_D_N':len(d5),'distance_to_main_u_at_activation':stats(e['floor_to_main_distance_before_u'] for e in updates),'floor_age_since_creation_bars_at_break':stats(p['v4']['exit_intent']['floor_age_since_creation_bars'] for p in d),'floor_age_since_update_bars_at_break':stats(p['v4']['exit_intent']['floor_age_since_update_bars'] for p in d),'break_Primary_context_N':dict(collections.Counter(str(p['v4']['exit_intent']['primary'])+'/'+str(p['v4']['exit_intent']['context']) for p in d)),'break_preceding3_distinct_Primary_N':dict(collections.Counter('>'.join(p['v4']['exit_last3_distinct_primary']) for p in d)),'V3_fallback_changes':0,'safety':SAFETY}
    save(HERE/'RECOVERY_FLOOR_MECHANICS.json',mech)
    common=[p for p in target if p['v3']['sell_status']=='FILLED' and p['v4']['sell_status']=='FILLED']
    gains=sorted([{'watch_key':p['watch_key'],'bucket':p['exclusive_bucket'],'delta_pp':p['v4']['realized_return_pct']-p['v3']['realized_return_pct']} for p in common],key=lambda x:x['delta_pp'],reverse=True)
    net=sum(x['delta_pp'] for x in gains);largest=max(0,gains[0]['delta_pp']) if gains else 0
    concentration={'target_common_filled_N':len(common),'target_D_N':sum(p['v4']['exit_intent'] is not None and p['v4']['exit_intent']['reason']=='LOCAL_RECOVERY_FAILED' for p in common),'positive_delta_N':sum(x['delta_pp']>0 for x in gains),'negative_delta_N':sum(x['delta_pp']<0 for x in gains),'zero_delta_N':sum(x['delta_pp']==0 for x in gains),'net_delta_sum_pp':net,'largest_positive_delta_pp':largest,'mean_delta_pp':net/len(common),'mean_delta_without_largest_positive_case_pp':(net-largest)/(len(common)-1),'no_new_numerical_cutoff':True,'target_bucket_D_N':{b:sum(p['exclusive_bucket']==b for p in d) for b in targets},'per_target_bucket_mean_delta_pp':{g['group']:g['return_common_group_difference']['mean'] for g in primary[:3]}}
    save(HERE/'TARGET_CONCENTRATION_DIAGNOSTIC.json',concentration)
    save(HERE/'SELECTION_PREAUDIT.json',selection(primary))
    receipt={'saved_at_jst':now(),'status':'V4_PAIRED_EVALUATION_COMPLETE','Entry_N':1600,'paired_join_mismatch_N':0,'V3_economics_rows_sha256':sha(V3_PRIVATE/'ECONOMICS_ROWS.jsonl.gz'),'V4_economics_rows_sha256':sha(PRIVATE/'ECONOMICS_ROWS.jsonl.gz'),'paired_rows_sha256':sha(PRIVATE/'PAIRED_ROWS.jsonl.gz'),'exclusive_denominator_sum':1600,'target_watch_N':426,'target_V3_filled_N':417,'target_common_filled_N':len(common),'GE5_watch_N':253,'EXIT_D_N':len(d),'GE5_EXIT_D_N':len(d5),'observed_High_unknown_N':sum(p['v3']['observed_High_unknown'] for p in pairs),'remaining_source_complete_N':sum(p['v3']['remaining_source_complete'] for p in pairs),'V3_replay':0,'Frozen_Entry_High_evaluator_rerun':0,'Frozen_opportunity_and_bucket_value_changes':0,'safety':SAFETY}
    save(HERE/'EVALUATION_RECEIPT.json',receipt)
    print(json.dumps({'receipt':receipt,'primary':[{ 'group':g['group'],'N':g['denominator_N'],'filled':g['return_common_filled_N'],'v3':g['return_common_filled']['v3'],'v4':g['return_common_filled']['v4'],'difference':g['return_common_group_difference']} for g in primary],'selection_provisional':selection(primary),'mechanics':mech}))

if __name__=='__main__':run()
