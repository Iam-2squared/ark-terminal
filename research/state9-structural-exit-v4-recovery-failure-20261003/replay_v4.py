"""Only V4 position replay. Exact original full trace and V3 fallback code."""
import gzip,json
from settings import *
from recovery_floor import RecoveryLifecycle
from reused_fill import fill_from_source

def run():
    freeze=load(HERE/'CONTRACT_FREEZE_RECEIPT.json')
    assert sha(HERE/'CONTRACT.md')==freeze['contract_sha256']
    for name,digest in freeze['decision_code_hashes'].items():assert sha(HERE/name)==digest,name
    receipt=load(HERE/'V3_TRACE_REUSE_RECEIPT.json');assert receipt['status']=='V3_FROZEN_TRACE_EXACT_REUSE_AVAILABLE'
    original=load(V2/'MANIFEST.json')['components']
    raw=load(V2/'SAVED_INPUTS/raw_paths_selected.json.gz')
    PRIVATE.mkdir(parents=True,exist_ok=True)
    once=PRIVATE/'RUN_ONCE.json'
    with once.open('x') as f:json.dump({'started_at_jst':now(),'policy':POLICY,'primary_replay_invocation_N':1,'status':'RUNNING'},f)
    result=[];decision_receipts=[]
    for entry in entries():
        key=entry['watch_key'];source=trace_path(key)
        assert sha(source)==original['FULL_TRACE/'+source.name]['sha256'],'BLOCKED_V4_FROZEN_TRACE_NOT_AVAILABLE'
        life=RecoveryLifecycle(entry['fill_minute'],regular_end(entry['session']));entry_snapshot=None
        target=PRIVATE/'DECISION_TRACE'/source.name;target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('wb') as out,gzip.GzipFile(fileobj=out,mode='wb',mtime=0) as gz:
            for row in rows(source):
                minute=row['bar_end_minute']
                if minute<entry['fill_minute']:life.prefix(row);continue
                if minute>regular_end(entry['session']):break
                if entry_snapshot is None:
                    assert minute==entry['fill_minute']
                    entry_snapshot={'primary':row['path']['Primary_or_null'],'display_primary':row['state']['primary'],'observed':row['state']['current_semantics_observed'],'context':row['state']['context'],'local_direction':row['state']['leg_direction'],'source_status':row['source_status'],'source_unavailable_reason':row['source_unavailable_reason'],'segment':row['path']['causal_segment_id']}
                intent,metadata=life.observe(row);gz.write(line(metadata))
                if intent is not None:break
        assert entry_snapshot is not None
        base=life.base;guard=life.guard;floor=life.floor;fill=fill_from_source(entry,base.intent,raw[key]['today'])
        record={'policy':POLICY,'watch_key':key,'session':entry['session'],'symbol':entry['symbol'],'entry_minute':entry['fill_minute'],'entry_timestamp':entry['fill_timestamp'],'entry_fill_price':entry['fill_price'],'entry_snapshot':entry_snapshot,'UP_STRUCTURE_ARMED_AT':stamp(entry['session'],base.first_arm_minute) if base.first_arm_minute is not None else None,'first_arm_minute':base.first_arm_minute,'arm_at_entry':base.arm_at_entry,'armed_ever':base.first_arm_minute is not None,'arm_events':base.arm_events,'observations_suspended':base.suspensions,'observation_suspended_ever':bool(base.suspensions),'phase_at_last_decision':base.phase,'suspended_at_last_decision':base.suspended,'exit_intent':base.intent,'planned_close_intent_minute':regular_end(entry['session']) if base.intent is None else None,'last_decision_snapshot':base.last_snapshot,'decision_N':base.decisions,'post_exit_decision_N':0,'protected_tighten_N':len(base.tighten_events),'PULLBACK_run_N':len(base.pullback_runs),'RISE_STOP_run_N':len(base.rise_stop_runs),'exit_last3_distinct_primary':list(base.primary_sequence),'recovery_floor_established_ever':floor.established_ever,'recovery_floor_creation_N':sum(e['type']=='RECOVERY_FLOOR_CREATED' for e in floor.events),'recovery_floor_tighten_N':sum(e['type']=='RECOVERY_FLOOR_TIGHTENED' for e in floor.events),'recovery_floor_reset_with_level_N':floor.reset_with_level_N,'recovery_floor_events':floor.events,'recovery_local_L_evaluated_exact':floor.observed_L,'local_guard_established_ever':guard.established_ever,'local_guard_creation_N':sum(e['type']=='LOCAL_GUARD_CREATED' for e in guard.events),'local_guard_tighten_N':sum(e['type']=='LOCAL_GUARD_TIGHTENED' for e in guard.events),'local_guard_reset_with_level_N':guard.reset_with_guard_N,'local_guard_events':guard.events,'local_pivot_observed_N':len(guard.observed_pivots),'local_pivot_observed_exact':guard.observed_pivots,'prefix_local_pivot_N':guard.prefix_pivot_N,'LHL_eligible_sequence_N':len(guard.eligible_sequences),'LHL_higher_low_sequence_N':len(guard.higher_low_sequences),'local_guard_candidate_bar_N':guard.candidate_bar_N,**fill}
        result.append(record);decision_receipts.append({'watch_key':key,'sha256':sha(target),'bytes':target.stat().st_size,'decision_N':base.decisions,'source_trace_sha256':original['FULL_TRACE/'+source.name]['sha256']})
    target=PRIVATE/'REPLAY_ROWS.jsonl.gz'
    with target.open('wb') as out,gzip.GzipFile(fileobj=out,mode='wb',mtime=0) as gz:
        for r in result:gz.write(line(r))
    save(PRIVATE/'DECISION_TRACE_RECEIPTS.json',decision_receipts)
    summary={'saved_at_jst':now(),'status':'V4_RECOVERY_FAILURE_REPLAY_COMPLETE','Entry_N':1600,'sell_filled_N':sum(r['sell_status']=='FILLED' for r in result),'unresolved_N':sum(r['sell_status']=='UNRESOLVED' for r in result),'exit_reason_N':dict(__import__('collections').Counter(r['exit_reason'] for r in result)),'EXIT_D_intent_N':sum(r['exit_intent'] is not None and r['exit_intent']['reason']=='LOCAL_RECOVERY_FAILED' for r in result),'floor_positions_N':sum(r['recovery_floor_established_ever'] for r in result),'EXIT_C_intent_N':sum(r['exit_intent'] is not None and r['exit_intent']['reason']=='LOCAL_UP_STRUCTURE_GUARD_BROKEN' for r in result),'guard_positions_N':sum(r['local_guard_established_ever'] for r in result),'replay_rows_sha256':sha(target),'decision_trace_files_N':len(decision_receipts),'decision_N':sum(r['decision_N'] for r in result),'post_exit_decision_N':0,'V3_replay':0,'v2_replay':0,'State9_Path_reconstruction':0,'budget':BUDGET,'safety':SAFETY}
    save(once,{'started_at_jst':load(once)['started_at_jst'],'completed_at_jst':now(),'policy':POLICY,'primary_replay_invocation_N':1,'status':'COMPLETE'});save(HERE/'REPLAY_RECEIPT.json',summary);print(json.dumps(summary))

if __name__=='__main__':run()
