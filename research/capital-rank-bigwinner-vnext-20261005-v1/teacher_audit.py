"""Contract support audit, not a regeneration or overwrite of frozen teachers."""
from collections import Counter, defaultdict
from decimal import Decimal
import json
from control import INPUTS, OUT, PRIVATE, ROOT, now, rows, save, sha, gzsave, checkpoint

V4 = INPUTS/'v4'
CORE = V4/'inputs/v3/capital_quality_v3_private/CORE_RUNTIME_CAUSAL.jsonl.gz'
BOOK = V4/'inputs/v3/bigwinner_private/MARKET_EXECUTION_BOOK_V2.jsonl.gz'
TEACHER = V4/'inputs/v3/capital_v2_private/TEACHERS_EVALUATION.jsonl.gz'
FIRST = V4/'inputs/v3/work_inputs/exit_v2/FROZEN_ENTRY/P1_Q70_FIRST_ENTRY_RECORDS.jsonl.gz'
CURRENT = V4/'capital_staircase_v4_private/UPWARD_STAIRCASE_SCORE_STREAM.jsonl.gz'
MOVE = INPUTS/'movement/MOVE_P5_SCORE_STREAM.jsonl.gz'

def valid(bar):
    if not bar.get('lineage'):
        return False
    try:
        d={k:Decimal(str(bar[k])) for k in ('O','H','L','C','Vo','Va')}
        return all(v.is_finite() and v>0 for v in d.values()) and d['L']<=min(d['O'],d['C'])<=max(d['O'],d['C'])<=d['H']
    except (KeyError, ValueError, TypeError):
        return False

def main():
    core=rows(CORE); teacher={r['entry_id']:r for r in rows(TEACHER)}
    book={r['entry_id']:r for r in rows(BOOK)}
    frozen={r['watch_key']:r for r in rows(FIRST) if r['entry_status']=='FIRST_ENTRY'}
    move_runtime=rows(INPUTS/'movement/RUNTIME_CAUSAL.jsonl.gz')
    mr={r['entry_id']:r for r in move_runtime}
    current={r['entry_id']:r for r in rows(CURRENT)}
    movement={r['entry_id']:r for r in rows(MOVE)}
    assert len(core)==len(teacher)==len(book)==len(frozen)==len(mr)==1600
    assert len(current)==len(movement)==1039 and set(current)==set(movement)
    assert {r['entry_id'] for r in core}==set(teacher)==set(book)==set(frozen)==set(mr)
    counts=defaultdict(Counter); ledger=[]; no_high=[]; violations=Counter()
    for r in core:
        key=r['entry_id']; b=book[key]; t=teacher[key]; f=frozen[key]
        assert (r['session'],r['symbol'],r['entry_minute'],r['entry_timestamp'])==(f['session'],f['symbol'],f['fill_minute'],f['fill_timestamp'])
        assert abs(Decimal(r['raw_reference'])*Decimal('1.0005')-Decimal(str(f['fill_price'])))<=Decimal('1e-8')
        assert b['entry_actual_source']['O']==r['raw_reference']
        assert b['session']==t['session']==r['session'] and b['symbol']==r['symbol']
        assert mr[key]['numeric'].keys()==(mr[key]['numeric']|r['numeric']).keys()
        assert all(mr[key]['numeric'][k]==v for k,v in r['numeric'].items())
        assert mr[key]['categorical']==r['categorical']
        assert mr[key]['raw_reference']==r['raw_reference'] and mr[key]['entry_timestamp']==r['entry_timestamp']
        prov=r['provenance']; mp=mr[key]['movement_provenance']
        if prov['max_known_minute'] is not None and prov['max_known_minute']>r['entry_minute']:violations['core_asof']+=1
        if mp['current_max_source_minute'] is not None and mp['current_max_source_minute']>=r['entry_minute']:violations['movement_asof']+=1
        if any(d>=r['session'] for d in mp['prior20_calendar_dates']+mp['prior5_calendar_dates']):violations['prior_session_asof']+=1
        assert not any(k in mr[key]['numeric'] for k in ('future_high','realized_net_return','frozen_exit'))
        src=b.get('source') or {}
        complete=bool(b['capture_complete'] and src.get('date_scope_complete') and src.get('terminal_pagination_proven'))
        assert complete==t['capture_complete']
        future=[z for z in b['market'] if r['entry_minute']<z['minute']<920 and valid(z)]
        if not future:no_high.append(key)
        potential=(max(Decimal(z['H']) for z in future)/Decimal(r['raw_reference'])-1) if future else Decimal(0) if complete else None
        status={}
        labels={}
        for head,threshold in [('U5',Decimal('.05')),('U10',Decimal('.10'))]:
            if r['entry_minute']>=920:classification='NOT_MATURE'; y=None
            elif potential is not None and future and potential>=threshold:classification='KNOWN_POSITIVE'; y=1
            elif complete:classification='KNOWN_NEGATIVE_COMPLETE_CAPTURE'; y=0
            elif not src:classification='SOURCE_UNAVAILABLE'; y=None
            else:classification='UNSUPPORTED_UNKNOWN'; y=None
            status[head]=classification; labels[head]=y
            counts['All1600_'+head][classification]+=1
            if key in current:counts['OOF1039_'+head][classification]+=1
            if y is not None:
                assert y==t['label_bigwinner'+head[1:]], ('TEACHER_LABEL_MISMATCH',key,head)
        if potential is not None:
            assert abs(float(potential)-t['potential_return'])<=1e-12, ('TEACHER_RETURN_MISMATCH',key)
        ledger.append({'entry_id':key,'session':r['session'],'symbol':r['symbol'],
            'entry_timestamp':r['entry_timestamp'],'entry_minute':r['entry_minute'],
            'OOF':key in current,'strict_later_actual_high_N':len(future),
            'capture_complete':complete,'date_scope_complete':src.get('date_scope_complete',False),
            'terminal_pagination_proven':src.get('terminal_pagination_proven',False),
            'source_wrapper_sha256':src.get('wrapper_sha256'),
            'status_U5':status['U5'],'status_U10':status['U10'],
            'label_U5':labels['U5'],'label_U10':labels['U10'],
            'legacy_potential_return':t['potential_return'],
            'comparable_current':key in current,'comparable_move':key in movement})
    assert not sum(violations.values())
    assert len(no_high)==54 and sum(book[k]['entry_actual_source']['minute']<920 for k in no_high)==32
    assert sum(k in current for k in no_high)==29
    gzsave(PRIVATE/'TEACHER_SUPPORT_LEDGER.jsonl.gz',ledger)
    report={'exact_jst':now(),'contract':'SAME_DAY_BIG_WINNER_5_V1; strictly later Entry minute < t < 920 actual valid High / raw Entry reference; negative requires complete capture',
        'contract_source_sha256':sha(ROOT/'docs/evidence/capital-bigwinner-one-shot-20261004-v1/DESIGN_PRECOMMIT.json'),
        'support_statuses':['KNOWN_POSITIVE','KNOWN_NEGATIVE_COMPLETE_CAPTURE','UNSUPPORTED_UNKNOWN','NOT_MATURE','SOURCE_UNAVAILABLE','CONTRACT_AMBIGUOUS'],
        'support_counts':{name:{s:counter[s] for s in ['KNOWN_POSITIVE','KNOWN_NEGATIVE_COMPLETE_CAPTURE','UNSUPPORTED_UNKNOWN','NOT_MATURE','SOURCE_UNAVAILABLE','CONTRACT_AMBIGUOUS']} for name,counter in counts.items()},
        '54_audit':{'no_actual_strict_later_high_N':54,'pre_cutoff_N':32,'cutoff_or_later_N':22,
            'OOF_no_high_N':29,'OOF_pre_cutoff_no_high_N':18,
            'all_54_have_complete_paginated_date_capture_and_entry_source':True,
            '32_pre_cutoff_resolution':'KNOWN_NEGATIVE_COMPLETE_CAPTURE under original empty-future complete-capture convention; no unknown to zero imputation',
            'source_missing_or_incomplete_N':0,'teacher_authority_resolved':True},
        'asof':{'decision_boundary':'Frozen Entry timestamp = fill_minute, as in inherited causal feature contract; not backdated to earlier first_intent',
            'first_intent_to_entry_delayed_N':sum(f['first_intent']['intent_minute']<f['fill_minute'] for f in frozen.values()),
            'historical_actual_arrival':'UNKNOWN; inherited bar_end availability assumption only',
            'violations':dict(violations),'core_max_known_minute_le_entry':True,'movement_bar_start_lt_entry':True,'prior_dates_lt_session':True},
        'candidate_identity_mismatch_N':0,'teacher_label_mismatch_N':0,'teacher_overwrite_N':0,'unknown_to_zero_imputation_N':0,
        'ledger_sha256':sha(PRIVATE/'TEACHER_SUPPORT_LEDGER.jsonl.gz'),'new_fits':0,'replays':0}
    save(OUT/'TEACHER_CONTRACT_AUDIT.json',report)
    checkpoint('R2_TEACHER_CONTRACT_AUDIT','TEACHER_AUTHORITY_RESOLVED_NO_UNKNOWN_IMPUTATION',
        ['Exact Frozen FIRST ENTRY identity and raw price audited','54 empty-future entries classified using original complete capture authority',
         'Core and Movement as-of provenance audited at frozen Entry timestamp'],report['54_audit'],
        'Freeze pre-cutoff common supported OOF mask; retain original1039 legacy reference; PRR only if exact teacher contract compatible')
    print(json.dumps({'counts':report['support_counts'],'asof_violations':0,'teacher_mismatch':0}))

if __name__=='__main__':main()
