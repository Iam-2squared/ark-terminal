"""Single frozen policy replay. Evaluator is in a separate module."""
import gzip, json
from decimal import Decimal
from settings import *
from lifecycle import Lifecycle, POLICY

def fill_from_source(entry,intent,raw):
    day = entry['session']; first_am = min((int(x[0]) for x in raw if int(x[0])<690),default=None)
    first_pm = min((int(x[0]) for x in raw if 750 <= int(x[0]) < regular_end(day)),default=None)
    mixed = {540,750,first_am,first_pm}
    if intent:
        eligible = [x for x in raw if valid_raw(x) and int(x[0]) in regular_starts(day) and int(x[0]) not in mixed and int(x[0]) >= intent['minute'] and int(x[0]) > entry['fill_minute']]
        if eligible:
            a = min(eligible,key=lambda x:x[0]); minute = int(a[0]); price = Decimal(str(a[1])) * Decimal('0.9995')
            return {'sell_status':'FILLED','sell_minute':minute,'sell_timestamp':stamp(day,minute),'sell_price':float(price),'sell_price_decimal':str(price),'sell_raw_price':a[1],'sell_source':'NEXT_ELIGIBLE_REGULAR_RAW_OPEN','sell_source_start':minute,'sell_source_assumed_available_at':stamp(day,minute+1),'sell_adjustment_bps':5,'commission':0,'exit_reason':intent['reason'],'closing_fallback_for_locked_intent':False}
    closing = [x for x in raw if int(x[0]) == session_close(day) and valid_raw(x)]
    if len(closing) == 1:
        a = closing[0]; minute = int(a[0]); price = Decimal(str(a[4])) * Decimal('0.9995')
        return {'sell_status':'FILLED','sell_minute':minute,'sell_timestamp':stamp(day,minute),'sell_price':float(price),'sell_price_decimal':str(price),'sell_raw_price':a[4],'sell_source':'PLANNED_TERMINAL_AUCTION_CLOSE','sell_source_start':minute,'sell_source_assumed_available_at':stamp(day,minute+1),'sell_adjustment_bps':5,'commission':0,'exit_reason':intent['reason'] if intent else 'SESSION_CLOSE','closing_fallback_for_locked_intent':intent is not None}
    return {'sell_status':'UNRESOLVED','sell_minute':None,'sell_timestamp':None,'sell_price':None,'sell_price_decimal':None,'sell_raw_price':None,'sell_source':None,'sell_source_start':None,'sell_source_assumed_available_at':None,'sell_adjustment_bps':5,'commission':0,'exit_reason':'UNRESOLVED','unfilled_intent_reason':intent['reason'] if intent else None,'closing_fallback_for_locked_intent':False,'unresolved_reason':'NO_ELIGIBLE_REGULAR_OPEN_AND_NO_VALID_EXACT_SESSION_CLOSE_SOURCE'}

def run():
    receipt = load(HERE/'FULL_TRACE_RECONSTRUCTION_RECEIPT.json')
    assert receipt['status'] == 'FULL_STATE9_PATH_TRACE_PARITY_PASS' and receipt['entry_N'] == 1600
    assert load(HERE/'CONTRACT_FREEZE_RECEIPT.json')['contract_sha256'] == sha(HERE/'CONTRACT.md')
    raw = load(INPUT/'base/raw_paths_selected.json.gz'); results = []
    for entry in entries():
        key = entry['watch_key']; life = Lifecycle(entry['fill_minute']); entry_snapshot = None
        trace = PRIVATE/'FULL_TRACE'/(key.replace('|','_')+'.jsonl.gz')
        for row in rows(trace):
            m = row['bar_end_minute']
            if m < entry['fill_minute']:
                continue
            if m > regular_end(entry['session']):
                break
            if entry_snapshot is None:
                assert m == entry['fill_minute'], 'ENTRY_TIME_STATE_SLOT_ABSENT'
                entry_snapshot = {'primary':row['path']['Primary_or_null'],'display_primary':row['state']['primary'],'observed':row['state']['current_semantics_observed'],'context':row['state']['context'],'local_direction':row['state']['leg_direction'],'source_status':row['source_status'],'source_unavailable_reason':row['source_unavailable_reason'],'segment':row['path']['causal_segment_id']}
            intent = life.observe(row)
            if intent is not None:
                break
        assert entry_snapshot is not None
        fill = fill_from_source(entry,life.intent,raw[key]['today'])
        result = {'policy':POLICY,'watch_key':key,'session':entry['session'],'symbol':entry['symbol'],'entry_minute':entry['fill_minute'],'entry_timestamp':entry['fill_timestamp'],'entry_fill_price':entry['fill_price'],'entry_snapshot':entry_snapshot,'UP_STRUCTURE_ARMED_AT':stamp(entry['session'],life.first_arm_minute) if life.first_arm_minute is not None else None,'first_arm_minute':life.first_arm_minute,'arm_at_entry':life.arm_at_entry,'armed_ever':life.first_arm_minute is not None,'arm_events':life.arm_events,'observations_suspended':life.suspensions,'observation_suspended_ever':bool(life.suspensions),'phase_at_last_decision':life.phase,'suspended_at_last_decision':life.suspended,'exit_intent':life.intent,'planned_close_intent_minute':regular_end(entry['session']) if life.intent is None else None,'last_decision_snapshot':life.last_snapshot,'decision_N':life.decisions,'post_exit_decision_N':0,'protected_tighten_N':len(life.tighten_events),'protected_tighten_events':life.tighten_events,'PULLBACK_run_N':len(life.pullback_runs),'RISE_STOP_run_N':len(life.rise_stop_runs),'exit_last3_distinct_primary':list(life.primary_sequence),**fill}
        results.append(result)
    dest = PRIVATE/'REPLAY_ROWS.jsonl.gz'
    with dest.open('wb') as f,gzip.GzipFile(fileobj=f,mode='wb',mtime=0) as gz:
        for r in results:gz.write(jsonline(r))
    summary = {'saved_at_jst':now(),'status':'STATE9_STRUCTURAL_EXIT_V2_REPLAY_COMPLETE','Entry_N':len(results),'sell_filled_N':sum(r['sell_status']=='FILLED' for r in results),'unresolved_N':sum(r['sell_status']=='UNRESOLVED' for r in results),'armed_N':sum(r['armed_ever'] for r in results),'never_armed_N':sum(not r['armed_ever'] for r in results),'exit_reason_N':dict(__import__('collections').Counter(r['exit_reason'] for r in results)),'intent_reason_N':dict(__import__('collections').Counter(r['exit_intent']['reason'] if r['exit_intent'] else 'SESSION_CLOSE' for r in results)),'sell_source_N':dict(__import__('collections').Counter(r['sell_source'] for r in results)),'post_exit_decision_N':sum(r['post_exit_decision_N'] for r in results),'replay_rows_sha256':sha(dest),'safety':SAFETY,'model_fits':0,'teacher':0,'new_EXIT_policies':1}
    save(HERE/'REPLAY_RECEIPT.json',summary);print(json.dumps(summary,ensure_ascii=False))

if __name__ == '__main__':run()
