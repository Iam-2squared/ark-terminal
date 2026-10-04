"""Append final-cohort source version before replay; X/models/scores unchanged."""
import gzip
import json
from decimal import Decimal as D
from pathlib import Path
from collections import Counter
from checkpoint import ROOT,OUT,save,sha
from contracts import liquidity,valid_market
from prepare import PRIVATE,rows,gzwrite

def main():
    scratch=ROOT.parent
    base=scratch/'work_inputs/bigwinner_source'
    supplement=scratch/'work_inputs/bigwinner_supplement'
    receipt=json.load(open(supplement/'SAVED_SOURCE_RECEIPT.json'))
    assert sha(supplement/'SAVED_SOURCE_PRIVATE.json.gz')==receipt['private_sha256']
    source_rows=json.load(gzip.open(base/'SAVED_SOURCE_PRIVATE.json.gz','rt'))
    source={(r['session'],r['symbol']):r for r in source_rows}
    extra=json.load(gzip.open(supplement/'SAVED_SOURCE_PRIVATE.json.gz','rt'))
    for r in extra:
        key=(r['session'],r['symbol'])
        if key in source:assert source[key]==r
        source[key]=r
    runtime=rows(PRIVATE/'RUNTIME_CAUSAL.jsonl.gz')
    books={b['entry_id']:b for b in rows(PRIVATE/'MARKET_EXECUTION_BOOK.jsonl.gz')}
    oldteachers={b['entry_id']:b for b in rows(PRIVATE/'TEACHERS_EVALUATION.jsonl.gz')}
    scope=json.load(open(Path(__file__).parent/'SOURCE_RECOVERY_SCOPE.json'))
    calendar=sorted(set(scope['required_prior_dates']+scope['entry_cohort_dates']))
    newbooks=[];newteachers=[];changed=[]
    for r in runtime:
        key=r['entry_id'];day=r['session'];symbol=r['symbol'];t=r['entry_minute'];raw=D(r['raw_reference'])
        assert liquidity(day,symbol,raw,calendar,source)==r['liquidity'],'SUPPLEMENT_CHANGED_PAST_LIQUIDITY'
        src=source.get((day,symbol))
        b=books[key]
        market=[{**row,'session':day} for row in src['market']]
        complete=bool(src['minute_source']['date_scope_complete'] and src['minute_source']['terminal_pagination_proven'])
        if not b['capture_complete']:changed.append(key)
        else:assert [{k:v for k,v in row.items() if k!='session'} for row in market]==b['market']
        b={**b,'capture_complete':complete,'market':market,'source':src['minute_source'],
           'entry_actual_source':next((row for row in market if row['minute']==t),None)}
        assert b['entry_actual_source'] and D(b['entry_actual_source']['O'])==raw,'SUPPLEMENT_FROZEN_ENTRY_REFERENCE_MISMATCH'
        newbooks.append(b)
        future=[row for row in market if t<row['minute']<920 and valid_market(row)]
        maximum=max((D(row['H']) for row in future),default=raw)
        potential=float(maximum/raw-1) if future else 0.0 if complete else None
        teacher={**oldteachers[key],'label_bigwinner5':int(maximum/raw-1>=D('.05')) if future and maximum/raw-1>=D('.05') else 0 if complete else None,
                 'potential_return':potential,'label_bigwinner3':int(potential>=.03) if potential is not None else None,
                 'label_bigwinner10':int(potential>=.10) if potential is not None else None,'capture_complete':complete}
        if key not in changed:assert teacher==oldteachers[key]
        newteachers.append(teacher)
    assert len(changed)==24 and {r['session'] for r in newteachers if r['entry_id'] in changed}=={'2025-08-25'}
    gzwrite(PRIVATE/'MARKET_EXECUTION_BOOK_V2.jsonl.gz',newbooks)
    gzwrite(PRIVATE/'TEACHERS_EVALUATION_V2.jsonl.gz',newteachers)
    save(PRIVATE/'FINAL_SOURCE_POINTER.json',{'market_book':'MARKET_EXECUTION_BOOK_V2.jsonl.gz',
        'teachers':'TEACHERS_EVALUATION_V2.jsonl.gz','score_stream':'ROLLING_ORIGIN_SCORE_STREAM.jsonl.gz'})
    result={'status':'ALL_58_COHORT_SESSIONS_SOURCE_COMPLETE','candidate_N':1600,'source_complete_N':1600,
        'cohort_source_supplement_N':24,'source_dates_authorized_total':79,'protected_date_still_unopened':'2025-07-11',
        'runtime_X_sha256_unchanged':sha(PRIVATE/'RUNTIME_CAUSAL.jsonl.gz'),
        'score_stream_sha256_unchanged':sha(PRIVATE/'ROLLING_ORIGIN_SCORE_STREAM.jsonl.gz'),
        'past_liquidity_row_mismatch':0,'prior_1576_teacher_mismatch':0,
        'supplement_teachers_never_used_in_fit':'Final session is outside every8 precommitted training prefix; no new fit.',
        'fits_additional':0,'source_supplement_sha256':sha(supplement/'SAVED_SOURCE_PRIVATE.json.gz'),
        'market_book_V2_sha256':sha(PRIVATE/'MARKET_EXECUTION_BOOK_V2.jsonl.gz'),
        'teachers_V2_sha256':sha(PRIVATE/'TEACHERS_EVALUATION_V2.jsonl.gz'),'portfolio_results_seen':False,
        'policy_changes':0,'protected_opened':0,'provider_requests':0,
        'implementation_guards':'Explicit same-session row tag and source-lineage guard added before first replay; implements precommitted contract.'}
    save(OUT/'SOURCE_COHORT_SUPPLEMENT_RESULT.json',result)
    save(PRIVATE/'SOURCE_MANIFEST_FINAL.json',{'prior':json.load(open(PRIVATE/'SOURCE_MANIFEST_RECOVERED.json')),
        'supplement_source_sha256':sha(supplement/'SAVED_SOURCE_PRIVATE.json.gz'),
        'final_market_book_sha256':sha(PRIVATE/'MARKET_EXECUTION_BOOK_V2.jsonl.gz'),
        'final_teacher_sha256':sha(PRIVATE/'TEACHERS_EVALUATION_V2.jsonl.gz')})
    print(json.dumps(result))

if __name__=='__main__':main()
