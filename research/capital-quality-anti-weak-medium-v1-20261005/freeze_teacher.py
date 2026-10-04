"""Q2 source-supported teachers and existing common OOF identity; evaluation only."""
from collections import Counter
from decimal import Decimal
from control import *

def valid(bar):
    if not bar.get('lineage'):return False
    try:
        d={k:Decimal(str(bar[k])) for k in ('O','H','L','C','Vo','Va')}
        return all(v.is_finite() and v>0 for v in d.values()) and d['L']<=min(d['O'],d['C'])<=max(d['O'],d['C'])<=d['H']
    except (KeyError,ValueError,TypeError):return False

def main():
    runtime=rows(INPUTS/'RUNTIME_CAUSAL.jsonl.gz')
    core={r['entry_id']:r for r in rows(INPUTS/'CORE_RUNTIME_CAUSAL.jsonl.gz')}
    teacher={r['entry_id']:r for r in rows(INPUTS/'TEACHERS_EVALUATION.jsonl.gz')}
    ledger={r['entry_id']:r for r in rows(INPUTS/'TEACHER_SUPPORT_LEDGER.jsonl.gz')}
    book={r['entry_id']:r for r in rows(INPUTS/'MARKET_TEACHER_BOOK.jsonl.gz')}
    first={r['watch_key']:r for r in rows(INPUTS/'FROZEN_ENTRY.jsonl.gz') if r['entry_status']=='FIRST_ENTRY'}
    current=rows(INPUTS/'UPWARD_STAIRCASE_SCORE_STREAM.jsonl.gz')
    move={r['entry_id']:r for r in rows(INPUTS/'MOVE_P5_SCORE_STREAM.jsonl.gz')}
    mask=rows(INPUTS/'COMMON_EVAL_MASK.jsonl.gz')
    allowed={r['entry_id'] for r in mask if r['included']}
    split=read(ROOT/'docs/evidence/capital-max3-upward-staircase-v4-20261004-v1/SESSION_SPLIT.json')
    assert len(runtime)==len(core)==len(teacher)==len(ledger)==len(book)==len(first)==1600
    assert set(core)==set(teacher)==set(ledger)==set(book)==set(first)=={r['entry_id'] for r in runtime}
    assert len(current)==len(move)==len(mask)==1039 and len(allowed)==1028
    labels=[];empty=0;boundary_counts=Counter()
    for r in runtime:
        key=r['entry_id'];c=core[key];b=book[key];t=teacher[key];l=ledger[key];f=first[key]
        identity=(r['session'],r['symbol'],r['entry_minute'],r['entry_timestamp'])
        assert identity==(c['session'],c['symbol'],c['entry_minute'],c['entry_timestamp'])
        assert identity==(f['session'],f['symbol'],f['fill_minute'],f['fill_timestamp'])
        assert abs(Decimal(r['raw_reference'])*Decimal('1.0005')-Decimal(str(f['fill_price'])))<=Decimal('1e-8')
        assert b['entry_actual_source']['O']==r['raw_reference']
        assert all(r['numeric'][k]==v for k,v in c['numeric'].items()) and r['categorical']==c['categorical']
        mp=r['movement_provenance'];cp=r['provenance']
        assert cp['max_known_minute'] is None or cp['max_known_minute']<=r['entry_minute']
        assert mp['current_max_source_minute'] is None or mp['current_max_source_minute']<r['entry_minute']
        assert all(d<r['session'] for d in mp['prior20_calendar_dates']+mp['prior5_calendar_dates'])
        src=b.get('source') or {}
        complete=bool(b['capture_complete'] and src.get('date_scope_complete') and src.get('terminal_pagination_proven'))
        assert complete==l['capture_complete']==t['capture_complete']
        future=[z for z in b['market'] if r['entry_minute']<z['minute']<920 and valid(z)]
        p=max(Decimal(z['H']) for z in future)/Decimal(r['raw_reference'])-1 if future else Decimal(0) if complete else None
        empty+=not future
        if p is not None:assert abs(float(p)-t['potential_return'])<=1e-12
        mature=r['entry_minute']<920
        status='SUPPORTED_COMPLETE_CAPTURE' if mature and complete else 'NOT_MATURE' if not mature else 'UNKNOWN_INCOMPLETE'
        ys={f'U{u}':int(p>=Decimal(u)/100) if status=='SUPPORTED_COMPLETE_CAPTURE' else None for u in [2,3,5,10]}
        assert ys['U5']==l['label_U5'] and ys['U10']==l['label_U10']
        if ys['U3'] is not None:assert ys['U3']==t['label_bigwinner3']
        bucket=('Q4_MEGA' if ys['U10'] else 'Q3_BIG' if ys['U5'] else 'Q2_MEDIUM' if ys['U3'] else 'Q1_LOW' if ys['U2'] else 'Q0_WEAK') if ys['U2'] is not None else None
        boundary_counts[status]+=1
        labels.append({'entry_id':key,'session':r['session'],'entry_timestamp':r['entry_timestamp'],
            'raw_reference':r['raw_reference'],'entry_minute':r['entry_minute'],'potential_decimal':str(p) if p is not None else None,
            'potential_return':float(p) if p is not None else None,'capture_complete':complete,'strict_later_valid_high_N':len(future),
            'status':status,**ys,'WEAK2':1-ys['U2'] if ys['U2'] is not None else None,'bucket':bucket,
            'realized_net_return_diagnostic_only':t['realized_net_return'],'included_common_OOF':key in allowed})
    lm={r['entry_id']:r for r in labels}
    common=[]
    for c in current:
        k=c['entry_id'];m=move[k]
        assert all(c[n]==m[n] for n in ['session','symbol','entry_timestamp','entry_minute','raw_reference','block'])
        assert c['session'] in split['blocks'][c['block']-1]['test']
        if k in allowed:
            assert lm[k]['status']=='SUPPORTED_COMPLETE_CAPTURE'
            common.append({'entry_id':k,'session':c['session'],'symbol':c['symbol'],'entry_timestamp':c['entry_timestamp'],
                'block':c['block'],'CORE_H2':c['p2'],'CORE_H3':c['p3'],'pP':m['pP'],'legacy_ML':c['ML'],
                'legacy_m5':c['m5'],'legacy_m3':c['m3'],'legacy_m2':c['m2']})
    identity_hash=hashlib.sha256(('\n'.join(r['entry_id'] for r in common)+'\n').encode()).hexdigest()
    prior=read(ROOT/'docs/evidence/capital-rank-bigwinner-vnext-20261005-v1/COMMON_EVAL_MASK_FREEZE.json')
    assert identity_hash==prior['ordered_identity_sha256']
    census=Counter(lm[r['entry_id']]['bucket'] for r in common)
    assert census=={'Q0_WEAK':596,'Q1_LOW':135,'Q2_MEDIUM':127,'Q3_BIG':103,'Q4_MEGA':67}
    assert [sum(lm[r['entry_id']]['U'+str(u)] for r in common) for u in [2,3,5,10]]==[432,297,170,67]
    gzsave(PRIVATE/'QUALITY_TEACHERS_EVAL.jsonl.gz',labels)
    gzsave(PRIVATE/'COMMON_SAVED_SCORES.jsonl.gz',common)
    train_pins=[]
    for bl in split['blocks']:
        train=[r for r in runtime if r['session'] in bl['train'] and lm[r['entry_id']]['status']=='SUPPORTED_COMPLETE_CAPTURE']
        original=read(INPUTS/'models'/f"MOVE_P_BLOCK_{bl['block']:02d}.json")
        assert [r['entry_id'] for r in train]==original['train_entry_ids']
        assert max(r['session'] for r in train)<min(bl['test'])
        data=[{'entry_id':r['entry_id'],'session':r['session'],'U2':lm[r['entry_id']]['U2'],'U3':lm[r['entry_id']]['U3']} for r in train]
        p=PRIVATE/'training'/f"BLOCK_{bl['block']:02d}_PAST_ONLY.jsonl.gz"
        gzsave(p,data)
        train_pins.append({'block':bl['block'],'train_N':len(data),'U2_N':sum(r['U2'] for r in data),'U3_N':sum(r['U3'] for r in data),
            'training_payload_sha256':sha(p),'test_label_N':0,'same_train_identity_as_MOVE_P5':True})
    report={'exact_jst':now(),'teacher':'strictly after frozen raw Entry minute and before15:20; complete source capture required',
        'potential_only_targets':True,'WEAK2':'exact U2 complement; separate Weak fit0','cutoff_minute':920,
        'All1600_status_counts':dict(boundary_counts),'empty_future_N':empty,
        'empty_complete_capture_convention':'Original Rank support contract retained; no-trade complete capture is known negative; not unknown imputation',
        'primary_N':1028,'bucket_counts':dict(census),'U2_N':432,'U3_N':297,'U5_N':170,'U10_N':67,
        'ordered_identity_sha256':identity_hash,'original_mask_sha256':sha(INPUTS/'COMMON_EVAL_MASK.jsonl.gz'),
        'teacher_eval_sha256':sha(PRIVATE/'QUALITY_TEACHERS_EVAL.jsonl.gz'),'saved_score_sha256':sha(PRIVATE/'COMMON_SAVED_SCORES.jsonl.gz'),
        'runtime_sha256':sha(INPUTS/'RUNTIME_CAUSAL.jsonl.gz'),'training_payloads':train_pins,
        'historical_actual_arrival':'UNKNOWN; inherited bar-end availability assumption retained',
        'decision_boundary':'frozen Entry timestamp, not earlier first intent',
        'realized_PnL_training_use':0,'future_High_in_X':0,'unknown_negative_imputation':0,'identity_mismatch_N':0,'label_mismatch_N':0,
        'Protected_Holdout_Fresh_Validation_OOS_Prospective_open':0}
    save(OUT/'TEACHER_MASK_FREEZE.json',report)
    checkpoint('Q2_TEACHER_MASK_FREEZE','COMPLETE',['Original raw Entry and complete capture independently checked',
        'Common1028 identity and five bucket counts matched','Training labels exported only for completed past blocks'],
        {'primary_N':1028,'buckets':dict(census),'unknown_imputation':0,'test_label_export_to_training':0},'Q3 exact features/model/split and evaluation precommit')
    print({'N':len(common),'buckets':dict(census),'past_only_payloads':8})

if __name__=='__main__':main()
